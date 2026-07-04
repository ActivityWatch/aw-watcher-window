import pytest

from aw_watcher_window.main import compute_pulsetime
from aw_watcher_window.macos_cli import build_swift_command


def test_build_swift_command_omits_optional_filters():
    command = build_swift_command(
        "/tmp/aw-watcher-window-macos",
        "http://localhost:5600",
        "bucket",
        "host.localdomain",
        "aw-watcher-window",
    )

    assert command == [
        "/tmp/aw-watcher-window-macos",
        "http://localhost:5600",
        "bucket",
        "host.localdomain",
        "aw-watcher-window",
    ]


def test_build_swift_command_passes_title_filters():
    command = build_swift_command(
        "/tmp/aw-watcher-window-macos",
        "http://localhost:5600",
        "bucket",
        "host.localdomain",
        "aw-watcher-window",
        exclude_title=True,
        exclude_titles=["Zoom", "Slack.*huddle"],
    )

    assert command == [
        "/tmp/aw-watcher-window-macos",
        "http://localhost:5600",
        "bucket",
        "host.localdomain",
        "aw-watcher-window",
        "--exclude-title",
        "--exclude-titles",
        "Zoom",
        "--exclude-titles",
        "Slack.*huddle",
    ]


@pytest.mark.parametrize(
    "poll_time,expected_pulsetime",
    [
        (1.0, 2.0),   # max(1.5, 2.0)=2.0 — backward compatible, no change
        (2.0, 3.0),   # max(3.0, 3.0)=3.0 — exact threshold
        (5.0, 7.5),   # max(7.5, 6.0)=7.5 — fix kicks in (was 6.0, caused ~10% loss)
        (10.0, 15.0), # max(15.0, 11.0)=15.0 — fix kicks in (was 11.0, caused ~30% loss)
    ],
)
def test_pulsetime_scales_with_poll_time(poll_time: float, expected_pulsetime: float):
    """pulsetime must scale with poll_time so OS scheduling jitter doesn't break heartbeat chains.

    At poll_time=5s the old formula (poll_time+1=6s) caused ~10% of heartbeat
    gaps to exceed pulsetime, resulting in missing time. The fix: max(poll_time*1.5,
    poll_time+1) keeps backward compat at low poll_time while scaling the jitter
    tolerance at higher values. See: ActivityWatch/activitywatch#1177
    """
    assert compute_pulsetime(poll_time) == expected_pulsetime
