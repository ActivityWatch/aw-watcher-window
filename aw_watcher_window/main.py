import logging
import os
import re
import signal
import subprocess
import sys
from datetime import datetime, timezone
from time import sleep

from aw_client import ActivityWatchClient
from aw_core.log import setup_logging
from aw_core.models import Event

from .config import parse_args
from .exceptions import FatalError
from .lib import get_current_window
from .research_filter import transform as research_transform
from .macos_cli import build_swift_command
from .macos_permissions import background_ensure_permissions

logger = logging.getLogger(__name__)

# run with LOG_LEVEL=DEBUG
log_level = os.environ.get("LOG_LEVEL")
if log_level:
    logger.setLevel(logging.__getattribute__(log_level.upper()))


def compute_pulsetime(poll_time: float) -> float:
    """Scale pulsetime with poll_time so OS scheduling jitter doesn't break heartbeat chains.

    At poll_time=1s, jitter ~0.15s is well within 1s margin (poll_time+1).
    At poll_time=5s, jitter ~0.75s exceeds the 1s margin ~10% of the time,
    causing missing time in the timeline. max(poll_time*1.5, poll_time+1) keeps
    backward compatibility at poll_time≤2s while fixing the problem at higher
    polling intervals. See: https://github.com/ActivityWatch/activitywatch/issues/1177
    """
    return max(poll_time * 1.5, poll_time + 1.0)


def kill_process(pid):
    logger.info("Killing process {}".format(pid))
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        logger.info("Process {} already dead".format(pid))


def swift_helper_exit_status(returncode):
    """Translate Popen.wait() into a process exit status for the module manager.

    A crashed Swift helper is killed by a signal (SIGABRT for uncaught
    NSExceptions). Popen reports that as a negative returncode, but falling
    off main() exits 0, so aw-tauri treats the crash as a clean shutdown and
    does not restart window tracking (ActivityWatch/aw-watcher-window#144,
    #101, #139).
    """
    if not returncode:
        return 0
    if returncode < 0:
        return 128 + (-returncode)
    return returncode


def _is_xconn_error(exc: BaseException) -> bool:
    """Return True if *exc* is an Xlib display-connection or authorisation error."""
    try:
        import Xlib.error

        return isinstance(exc, Xlib.error.DisplayConnectionError)
    except ImportError:
        return False


def _warn_wayland_once() -> None:
    """Log a one-time warning when a Wayland session is detected.

    X11 tracking (via Xlib) only sees XWayland apps; native Wayland windows
    appear as 'unknown'. Users running a pure Wayland compositor should switch
    to aw-watcher-window-wayland instead.
    """
    xdg_session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    wayland_display = os.environ.get("WAYLAND_DISPLAY", "")
    if xdg_session == "wayland" or wayland_display:
        logger.warning(
            "Wayland session detected (XDG_SESSION_TYPE=%r, WAYLAND_DISPLAY=%r). "
            "aw-watcher-window uses X11/Xlib and will only track XWayland apps — "
            "native Wayland windows will show as 'unknown'. "
            "For full Wayland support see aw-watcher-window-wayland: "
            "https://github.com/ActivityWatch/aw-watcher-window-wayland",
            xdg_session or "unset",
            wayland_display or "unset",
        )


def try_compile_title_regex(title):
    try:
        return re.compile(title, re.IGNORECASE)
    except re.error:
        logger.error(f"Invalid regex pattern: {title}")
        exit(1)


def main():
    args = parse_args()

    if sys.platform.startswith("linux") and (
        "DISPLAY" not in os.environ or not os.environ["DISPLAY"]
    ):
        raise Exception("DISPLAY environment variable not set")

    setup_logging(
        name="aw-watcher-window",
        testing=args.testing,
        verbose=args.verbose,
        log_stderr=True,
        log_file=True,
    )

    if sys.platform.startswith("linux"):
        _warn_wayland_once()

    if sys.platform == "darwin":
        background_ensure_permissions()

    client = ActivityWatchClient(
        "aw-watcher-window", host=args.host, port=args.port, testing=args.testing
    )

    bucket_id = f"{client.client_name}_{client.client_hostname}"
    event_type = "currentwindow"

    client.create_bucket(bucket_id, event_type, queued=True)

    logger.info("aw-watcher-window started")
    client.wait_for_start()

    with client:
        research_category_map = (
            args.research_category_map
            if args.research_enabled
            else None
        )
        research_app_category_map = (
            args.research_app_category_map
            if args.research_enabled
            else None
        )
        if sys.platform == "darwin" and args.strategy == "swift":
            logger.info("Using swift strategy, calling out to swift binary")
            binpath = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "aw-watcher-window-macos"
            )

            try:
                p = subprocess.Popen(
                    build_swift_command(
                        binpath,
                        client.server_address,
                        bucket_id,
                        client.client_hostname,
                        client.client_name,
                        exclude_title=args.exclude_title,
                        exclude_titles=args.exclude_titles,
                        research_category_map=research_category_map,
                        research_app_category_map=research_app_category_map,
                    )
                )
                # terminate swift process when this process dies
                signal.signal(signal.SIGTERM, lambda *_: kill_process(p.pid))
                status = swift_helper_exit_status(p.wait())
                if status:
                    logger.error("Swift helper exited with status %s", status)
                    sys.exit(status)
            except KeyboardInterrupt:
                print("KeyboardInterrupt")
                kill_process(p.pid)
        else:
            heartbeat_loop(
                client,
                bucket_id,
                poll_time=args.poll_time,
                strategy=args.strategy,
                exclude_title=args.exclude_title,
                exclude_titles=[
                    try_compile_title_regex(title)
                    for title in args.exclude_titles
                    if title is not None
                ],
                research_category_map=research_category_map,
                research_app_category_map=research_app_category_map,
            )


def heartbeat_loop(
    client,
    bucket_id,
    poll_time,
    strategy,
    exclude_title=False,
    exclude_titles=[],
    research_category_map=None,
    research_app_category_map=None,
):
    # State for X display-connection error backoff (Linux only).
    _xconn_error_logged = False
    _xconn_backoff = poll_time  # grows exponentially up to 60s on repeated failures

    while True:
        if os.getppid() == 1:
            logger.info("window-watcher stopped because parent process died")
            break

        current_window = None
        try:
            current_window = get_current_window(strategy)
            logger.debug(current_window)
            # Reset backoff on a successful poll.
            _xconn_backoff = poll_time
        except (FatalError, OSError):
            # Fatal exceptions should quit the program
            try:
                logger.exception("Fatal error, stopping")
            except OSError:
                pass
            break
        except Exception as exc:
            # Check for X display connection / authorisation failures before
            # falling through to the generic "log full traceback" path.
            if sys.platform.startswith("linux") and _is_xconn_error(exc):
                if not _xconn_error_logged:
                    _xconn_error_logged = True
                    _xauth = os.environ.get("XAUTHORITY", "")
                    logger.error(
                        "Cannot connect to X display: %s. "
                        "Most likely cause: aw-watcher-window is running as a different user "
                        "or with sudo. Fix: run it as the display owner, or point XAUTHORITY "
                        "to the correct .Xauthority file (currently %r). "
                        "See: https://docs.activitywatch.net/en/latest/faq.html",
                        exc,
                        _xauth if _xauth else "unset",
                    )
                sleep(_xconn_backoff)
                _xconn_backoff = min(_xconn_backoff * 2, 60.0)
                continue
            # Non-fatal exceptions should be logged
            try:
                # If stdout has been closed, this exception-print can cause (I think)
                #   OSError: [Errno 5] Input/output error
                # See: https://github.com/ActivityWatch/activitywatch/issues/756#issue-1296352264
                #
                # However, I'm unable to reproduce the OSError in a test (where I close stdout before logging),
                # so I'm in uncharted waters here... but this solution should work.
                logger.exception("Exception thrown while trying to get active window")
            except OSError:
                break

        if current_window is None:
            logger.debug("Unable to fetch window, trying again on next poll")
        else:
            current_window = transform_window(
                current_window,
                exclude_title=exclude_title,
                exclude_titles=exclude_titles,
                research_category_map=research_category_map,
                research_app_category_map=research_app_category_map,
            )

            now = datetime.now(timezone.utc)
            current_window_event = Event(timestamp=now, data=current_window)

            client.heartbeat(
                bucket_id,
                current_window_event,
                pulsetime=compute_pulsetime(poll_time),
                queued=True,
            )

        sleep(poll_time)


def transform_window(
    current_window,
    exclude_title=False,
    exclude_titles=None,
    research_category_map=None,
    research_app_category_map=None,
):
    if research_category_map is not None:
        return research_transform(
            current_window,
            research_category_map,
            app_category_map=research_app_category_map,
        )

    for pattern in exclude_titles or []:
        if pattern.search(current_window["title"]):
            current_window["title"] = "excluded"

    if exclude_title:
        current_window["title"] = "excluded"

    return current_window
