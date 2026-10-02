import logging
import multiprocessing
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


# Python's multiprocessing re-executes the running binary for its helper
# processes (the resource tracker and spawned children). In a frozen
# PyInstaller build those helper argv shapes are passed straight to this
# watcher's argparse and rejected, which kills the child — and eventually the
# parent, which stops sending heartbeats
# (ActivityWatch/aw-watcher-window#133).
#
# Match the *structure* of those invocations rather than a substring of an
# arbitrary argument value: a user's `--exclude-titles multiprocessing.spawn`
# regex is a legitimate argument and must not be mistaken for a helper.
_MULTIPROCESSING_FORK_FLAG = "--multiprocessing-fork"
_MULTIPROCESSING_C_PREFIXES = (
    "from multiprocessing.resource_tracker import",
    "from multiprocessing.spawn import",
)


def is_multiprocessing_child(argv):
    """Return True if *argv* is a multiprocessing helper re-running this binary."""
    # `spawn` re-executes as `binary --multiprocessing-fork tracker_fd=..`.
    # CPython keys on the flag being argv[1]; only a real helper places it there.
    if len(argv) >= 2 and argv[1] == _MULTIPROCESSING_FORK_FLAG:
        return True
    # The resource tracker (and Windows spawn) re-execute as
    # `binary -c "from multiprocessing.<module> import ..."`.
    return any(
        arg == "-c" and argv[i + 1].lstrip().startswith(_MULTIPROCESSING_C_PREFIXES)
        for i, arg in enumerate(argv[1:], start=1)
        if i + 1 < len(argv)
    )


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


# How many identical consecutive poll errors between one-line summaries.
REPEATED_ERROR_SUMMARY_EVERY = 100
# Maximum distinct error signatures to retain per streak; prevents unbounded
# memory/log growth when the error message varies every poll (e.g. X window IDs
# embedded in exception text).  Errors beyond this cap are treated as recurring.
_MAX_SEEN_ERRORS = 50


def try_compile_title_regex(title):
    try:
        return re.compile(title, re.IGNORECASE)
    except re.error:
        logger.error(f"Invalid regex pattern: {title}")
        exit(1)


def main():
    # Must run before parse_args(): in a frozen build multiprocessing re-executes
    # this binary for helper processes and their argv would be rejected below.
    # In a frozen child freeze_support() runs the bootstrap and does not return.
    multiprocessing.freeze_support()
    if is_multiprocessing_child(sys.argv):
        # Belt and braces: a multiprocessing helper whose bootstrap
        # freeze_support() did not claim must not fall through to argparse.
        return

    args = parse_args()

    setup_logging(
        name="aw-watcher-window",
        testing=args.testing,
        verbose=args.verbose,
        log_stderr=True,
        log_file=True,
    )

    if sys.platform.startswith("linux"):
        # Warn about Wayland *before* the DISPLAY check so pure-Wayland users
        # (no DISPLAY set) still see the actionable message and the link to
        # aw-watcher-window-wayland instead of a bare exception.
        _warn_wayland_once()

    if sys.platform.startswith("linux") and (
        "DISPLAY" not in os.environ or not os.environ["DISPLAY"]
    ):
        raise Exception("DISPLAY environment variable not set")

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
            args.research_category_map if args.research_enabled else None
        )
        research_app_category_map = (
            args.research_app_category_map if args.research_enabled else None
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
    # State for dedup/backoff of any other repeating poll exception, so a
    # persistent error can't write an unbounded log (aw-watcher-window#78).
    _seen_errors: set = set()  # error signatures seen in the current failure streak
    _error_repeats = 0

    while True:
        if os.getppid() == 1:
            logger.info("window-watcher stopped because parent process died")
            break

        current_window = None
        try:
            current_window = get_current_window(strategy)
            logger.debug(current_window)
            # Reset backoff and the one-shot log flag on a successful poll so
            # a new X connection failure episode logs once again.
            _xconn_backoff = poll_time
            _xconn_error_logged = False
            _seen_errors = set()
            _error_repeats = 0
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
                # Sleep in 1-second chunks so parent death is noticed within
                # ~1 s even when the backoff is at its 60 s cap.
                _remaining = _xconn_backoff
                while _remaining > 0:
                    sleep(min(1.0, _remaining))
                    _remaining -= 1.0
                    if os.getppid() == 1:
                        logger.info("window-watcher stopped because parent process died")
                        break
                else:
                    _xconn_backoff = min(_xconn_backoff * 2, 60.0)
                    continue
                break
            # Non-fatal exceptions should be logged
            try:
                # If stdout has been closed, this exception-print can cause (I think)
                #   OSError: [Errno 5] Input/output error
                # See: https://github.com/ActivityWatch/activitywatch/issues/756#issue-1296352264
                #
                # However, I'm unable to reproduce the OSError in a test (where I close stdout before logging),
                # so I'm in uncharted waters here... but this solution should work.
                signature = (type(exc).__name__, str(exc))
                if signature not in _seen_errors and len(_seen_errors) < _MAX_SEEN_ERRORS:
                    # First time we see this error in the current streak (and
                    # the signature cap has not been reached): log a full
                    # traceback, but do not reset the repeat counter so
                    # alternating distinct errors still accumulate backoff.
                    _seen_errors.add(signature)
                    logger.exception(
                        "Exception thrown while trying to get active window"
                    )
                else:
                    # Recurring error (or signature cap reached): suppress the
                    # traceback; periodically emit a one-line summary so the
                    # log stays bounded.
                    if _error_repeats % REPEATED_ERROR_SUMMARY_EVERY == 0:
                        logger.error(
                            "Still failing to get active window (%d repeats): %s: %s",
                            _error_repeats,
                            *signature,
                        )
                _error_repeats += 1
            except OSError:
                break
            # Back off on *sustained* failures (2+ consecutive errors) up to
            # 60s between polls.  Skipping backoff on the very first error
            # avoids adding extra delay for transient glitches, which could
            # otherwise create a gap in recorded activity.
            # max(0.0, ...) guards against poll_time > 60 producing a negative
            # sleep duration when the cap (60s) is smaller than poll_time.
            if _error_repeats > 1:
                sleep(max(0.0, min(poll_time * 2 ** min(_error_repeats, 10), 60.0) - poll_time))

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
