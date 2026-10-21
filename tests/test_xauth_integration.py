"""Real Xlib startup with cookie authentication; optional Xvfb integration."""

import os
import secrets
import select
import shutil
import socket
import struct
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "linux" or not shutil.which("Xvfb"),
    reason="requires Linux and Xvfb",
)


def record(family, address, number, cookie):
    data = struct.pack(">H", family)
    for field in (address, number, b"MIT-MAGIC-COOKIE-1", cookie):
        data += struct.pack(">H", len(field)) + field
    return data


@pytest.fixture
def authenticated_display(tmp_path):
    cookie = secrets.token_bytes(16)
    hostname = socket.gethostname().encode()
    authority = tmp_path / "server.auth"
    authority.write_bytes(record(256, hostname, b"", cookie))
    authority.chmod(0o600)
    read_fd, write_fd = os.pipe()
    try:
        server = subprocess.Popen(
            [
                "Xvfb",
                "-displayfd",
                str(write_fd),
                "-auth",
                str(authority),
                "-screen",
                "0",
                "320x240x24",
                "-nolisten",
                "tcp",
            ],
            pass_fds=(write_fd,),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    finally:
        os.close(write_fd)
    try:
        with os.fdopen(read_fd) as pipe:
            assert select.select([pipe], [], [], 10)[0], "Xvfb startup timed out"
            number = pipe.readline().strip()
        assert number, "Xvfb failed to allocate a display"
        yield number, hostname, cookie
    finally:
        server.terminate()
        server.communicate(timeout=10)


@pytest.mark.parametrize(
    "case",
    [
        "exact",
        "local_empty",
        "wild_exact",
        "wild_empty",
        "mutter_stale",
        "wrong_cookie",
        "wrong_number",
        "wrong_host",
    ],
)
def test_watcher_startup_preserves_authenticated_access(
    case, authenticated_display, tmp_path
):
    number, host, cookie = authenticated_display
    records = {
        "exact": [(256, host, number.encode(), cookie)],
        "local_empty": [(256, host, b"", cookie)],
        "wild_exact": [(65535, b"old-host", number.encode(), cookie)],
        "wild_empty": [(65535, b"old-host", b"", cookie)],
        "mutter_stale": [
            (256, b"old-host", b"", cookie),
            (65535, b"old-host", b"", cookie),
        ],
        "wrong_cookie": [(65535, host, b"", secrets.token_bytes(16))],
        "wrong_number": [(65535, host, b"999999", cookie)],
        "wrong_host": [(256, b"old-host", number.encode(), cookie)],
    }
    authority = tmp_path / "client.auth"
    authority.write_bytes(b"".join(record(*row) for row in records[case]))
    authority.chmod(0o600)
    # Each case imports the actual watcher startup in a fresh process. No
    # pre-installed patch or mocked Display can hide a missing install() call.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from aw_watcher_window import xlib
from aw_watcher_window.lib import get_current_window_linux
connection = xlib.display
for _ in range(20):
    assert isinstance(get_current_window_linux(), dict)
    xlib.display.sync()
    assert xlib.display is connection
xlib.display.close()
""",
        ],
        env=dict(os.environ, DISPLAY=":" + number, XAUTHORITY=str(authority)),
        capture_output=True,
        timeout=15,
    )
    if case.startswith("wrong_"):
        assert result.returncode != 0
        assert b"DisplayConnectionError" in result.stderr
    else:
        assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert cookie.hex().encode() not in result.stdout + result.stderr
