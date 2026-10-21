"""Xauthority matching for Mutter-style records with python-xlib 0.31.

Mutter writes FamilyLocal and FamilyWild records with an empty display number.
Upstream 0.31 only matches exact family, address and number, so these records
are rejected. The compatibility matcher must accept them without accepting
arbitrary records. Cookies are never printed or put into exception messages.
"""

import struct
from types import SimpleNamespace

import pytest

pytest.importorskip("Xlib", reason="python-xlib is a Linux-only dependency")

from Xlib import error
from Xlib import xauth as xlib_xauth
from Xlib.support import unix_connect

from aw_watcher_window import xauth

HOST = b"workstation"
STALE_HOST = b"old-hostname"
COOKIE = b"\x01\x02cookie-bytes-not-for-logs"
OTHER_COOKIE = b"\x09\x09other-cookie-bytes"
MIT = b"MIT-MAGIC-COOKIE-1"
XDM = b"XDM-AUTHORIZATION-1"
LOCAL = xlib_xauth.FamilyLocal
WILD = xauth.FAMILY_WILD


def _pstr(value: bytes) -> bytes:
    return struct.pack(">H", len(value)) + value


def record(family, addr, num, name, data):
    return (
        struct.pack(">H", family) + _pstr(addr) + _pstr(num) + _pstr(name) + _pstr(data)
    )


def write_auth(tmp_path, *records, name="Xauthority"):
    path = tmp_path / name
    path.write_bytes(b"".join(records))
    return str(path)


def lookup(path, family, address, dispno, types=(MIT,)):
    return xauth.CompatXauthority(path).get_best_auth(family, address, dispno, types)


def assert_rejected(path, family, address, dispno, types=(MIT,)):
    with pytest.raises(error.XNoAuthError):
        lookup(path, family, address, dispno, types)


@pytest.fixture
def restore_xauthority():
    original = xlib_xauth.Xauthority
    yield
    xlib_xauth.Xauthority = original


# ---------------------------------------------------------------------------
# Original exact-match behaviour is preserved and takes precedence
# ---------------------------------------------------------------------------


def test_exact_family_address_number_match(tmp_path):
    path = write_auth(tmp_path, record(LOCAL, HOST, b"0", MIT, COOKIE))
    assert lookup(path, LOCAL, HOST, 0) == (MIT, COOKIE)


def test_exact_match_beats_empty_number_fallback(tmp_path):
    path = write_auth(
        tmp_path,
        record(LOCAL, HOST, b"", MIT, OTHER_COOKIE),
        record(LOCAL, HOST, b"0", MIT, COOKIE),
    )
    assert lookup(path, LOCAL, HOST, 0) == (MIT, COOKIE)


def test_exact_match_beats_wildcard_fallback(tmp_path):
    path = write_auth(
        tmp_path,
        record(WILD, HOST, b"0", MIT, OTHER_COOKIE),
        record(LOCAL, HOST, b"0", MIT, COOKIE),
    )
    assert lookup(path, LOCAL, HOST, 0) == (MIT, COOKIE)


def test_exact_record_for_less_preferred_protocol_beats_preferred_fallback(tmp_path):
    # Upstream returns any exact match before looking at fallbacks, so a wildcard
    # record cannot displace an exact record of a different supported protocol.
    path = write_auth(
        tmp_path,
        record(WILD, HOST, b"", MIT, OTHER_COOKIE),
        record(LOCAL, HOST, b"0", XDM, COOKIE),
    )
    assert lookup(path, LOCAL, HOST, 0, types=(MIT, XDM)) == (XDM, COOKIE)


def test_exact_matches_follow_types_preference(tmp_path):
    path = write_auth(
        tmp_path,
        record(LOCAL, HOST, b"0", MIT, OTHER_COOKIE),
        record(LOCAL, HOST, b"0", XDM, COOKIE),
    )
    assert lookup(path, LOCAL, HOST, 0, types=(XDM, MIT)) == (XDM, COOKIE)
    assert lookup(path, LOCAL, HOST, 0, types=(MIT, XDM)) == (MIT, OTHER_COOKIE)


# ---------------------------------------------------------------------------
# Empty display number with the correct, non-wildcard family and address
# ---------------------------------------------------------------------------


def test_local_empty_number_with_correct_hostname_matches(tmp_path):
    path = write_auth(tmp_path, record(LOCAL, HOST, b"", MIT, COOKIE))
    assert lookup(path, LOCAL, HOST, 0) == (MIT, COOKIE)


def test_local_empty_number_with_stale_hostname_is_rejected(tmp_path):
    path = write_auth(tmp_path, record(LOCAL, STALE_HOST, b"", MIT, COOKIE))
    assert_rejected(path, LOCAL, HOST, 0)


def test_non_wildcard_family_mismatch_is_rejected(tmp_path):
    # FamilyInternet is not a wildcard, so it must not satisfy a FamilyLocal lookup.
    path = write_auth(
        tmp_path, record(xlib_xauth.FamilyInternet, HOST, b"", MIT, COOKIE)
    )
    assert_rejected(path, LOCAL, HOST, 0)


def test_non_wildcard_wrong_explicit_number_is_rejected(tmp_path):
    path = write_auth(tmp_path, record(LOCAL, HOST, b"5", MIT, COOKIE))
    assert_rejected(path, LOCAL, HOST, 0)


# ---------------------------------------------------------------------------
# FamilyWild: any address, explicit or empty display number
# ---------------------------------------------------------------------------


def test_wild_explicit_number_matches_any_address(tmp_path):
    path = write_auth(tmp_path, record(WILD, STALE_HOST, b"0", MIT, COOKIE))
    assert lookup(path, LOCAL, HOST, 0) == (MIT, COOKIE)


def test_wild_empty_number_matches_any_address(tmp_path):
    path = write_auth(tmp_path, record(WILD, STALE_HOST, b"", MIT, COOKIE))
    assert lookup(path, LOCAL, HOST, 0) == (MIT, COOKIE)


def test_wild_explicit_different_display_number_is_rejected(tmp_path):
    path = write_auth(tmp_path, record(WILD, HOST, b"5", MIT, COOKIE))
    assert_rejected(path, LOCAL, HOST, 0)


def test_mutter_pair_with_correct_hostname_matches(tmp_path):
    path = write_auth(
        tmp_path,
        record(LOCAL, HOST, b"", MIT, COOKIE),
        record(WILD, HOST, b"", MIT, COOKIE),
    )
    assert lookup(path, LOCAL, HOST, 0) == (MIT, COOKIE)


def test_mutter_pair_with_stale_hostname_matches_via_wild_record(tmp_path):
    path = write_auth(
        tmp_path,
        record(LOCAL, STALE_HOST, b"", MIT, OTHER_COOKIE),
        record(WILD, STALE_HOST, b"", MIT, COOKIE),
    )
    assert lookup(path, LOCAL, HOST, 0) == (MIT, COOKIE)


def test_wild_record_for_other_protocol_is_rejected(tmp_path):
    path = write_auth(tmp_path, record(WILD, HOST, b"", XDM, COOKIE))
    assert_rejected(path, LOCAL, HOST, 0, types=(MIT,))


# ---------------------------------------------------------------------------
# Competing fallback records: deterministic tier and protocol precedence
# ---------------------------------------------------------------------------


def test_local_empty_number_beats_wild_explicit_number(tmp_path):
    path = write_auth(
        tmp_path,
        record(WILD, HOST, b"0", MIT, OTHER_COOKIE),
        record(LOCAL, HOST, b"", MIT, COOKIE),
    )
    assert lookup(path, LOCAL, HOST, 0) == (MIT, COOKIE)


def test_wild_explicit_number_beats_wild_empty_number(tmp_path):
    path = write_auth(
        tmp_path,
        record(WILD, HOST, b"", MIT, OTHER_COOKIE),
        record(WILD, HOST, b"0", MIT, COOKIE),
    )
    assert lookup(path, LOCAL, HOST, 0) == (MIT, COOKIE)


def test_fallback_protocol_preference_follows_types(tmp_path):
    path = write_auth(
        tmp_path,
        record(WILD, HOST, b"", MIT, OTHER_COOKIE),
        record(WILD, HOST, b"", XDM, COOKIE),
    )
    assert lookup(path, LOCAL, HOST, 0, types=(XDM, MIT)) == (XDM, COOKIE)
    assert lookup(path, LOCAL, HOST, 0, types=(MIT, XDM)) == (MIT, OTHER_COOKIE)


# ---------------------------------------------------------------------------
# Malformed and unreadable authority files fail closed
# ---------------------------------------------------------------------------


def test_truncated_trailing_record_is_ignored(tmp_path):
    complete = record(LOCAL, HOST, b"0", MIT, COOKIE)
    truncated = record(WILD, HOST, b"", MIT, OTHER_COOKIE)[:-5]
    path = write_auth(tmp_path, complete, truncated)
    assert lookup(path, LOCAL, HOST, 0) == (MIT, COOKIE)
    # The truncated wildcard record must not be used, even though it matches.
    assert len(xauth.CompatXauthority(path).entries) == 1
    assert_rejected(
        write_auth(tmp_path, truncated, name="truncated-only"), LOCAL, HOST, 0
    )


def test_garbage_file_matches_nothing(tmp_path):
    path = write_auth(tmp_path, b"\xff\xff\x00")
    assert_rejected(path, LOCAL, HOST, 0)


def test_empty_file_matches_nothing(tmp_path):
    path = write_auth(tmp_path)
    assert_rejected(path, LOCAL, HOST, 0)


def test_missing_file_raises_xauth_error(tmp_path):
    with pytest.raises(error.XauthError):
        xauth.CompatXauthority(str(tmp_path / "missing"))


def test_unreadable_file_yields_no_auth_during_connection(
    tmp_path, monkeypatch, restore_xauthority
):
    monkeypatch.setenv("XAUTHORITY", str(tmp_path / "missing"))
    xauth.install()
    # python-xlib turns an unreadable file into empty auth, so the server decides.
    assert unix_connect.new_get_auth(None, ":0", "unix", None, 0) == (b"", b"")


def test_cookie_and_stored_bytes_stay_out_of_diagnostics(tmp_path, capsys):
    path = write_auth(
        tmp_path,
        record(LOCAL, STALE_HOST, b"", MIT, COOKIE),
        record(WILD, HOST, b"5", MIT, OTHER_COOKIE),
        b"\x00",
    )
    with pytest.raises(error.XNoAuthError) as excinfo:
        lookup(path, LOCAL, HOST, 0)
    captured = capsys.readouterr()
    for text in (str(excinfo.value), repr(excinfo.value), captured.out, captured.err):
        for cookie in (COOKIE, OTHER_COOKIE):
            for representation in (cookie.decode("latin1"), repr(cookie), cookie.hex()):
                assert representation not in text


# ---------------------------------------------------------------------------
# Explicit initialisation before the first Display()
# ---------------------------------------------------------------------------


def test_install_routes_python_xlib_auth_through_compat_matcher(
    tmp_path, monkeypatch, restore_xauthority
):
    path = write_auth(tmp_path, record(WILD, STALE_HOST, b"", MIT, COOKIE))
    monkeypatch.setenv("XAUTHORITY", path)
    monkeypatch.setattr(
        unix_connect.socket, "gethostname", lambda: HOST.decode(), raising=True
    )

    # Without the hook, upstream rejects the FamilyWild empty-number record.
    assert unix_connect.new_get_auth(None, ":0", "unix", None, 0) == (b"", b"")

    xauth.install()
    assert xlib_xauth.Xauthority is xauth.CompatXauthority
    assert unix_connect.new_get_auth(None, ":0", "unix", None, 0) == (MIT, COOKIE)


def test_install_is_idempotent(restore_xauthority):
    xauth.install()
    xauth.install()
    assert xlib_xauth.Xauthority is xauth.CompatXauthority


def test_compat_matcher_keeps_upstream_base_class():
    assert issubclass(xauth.CompatXauthority, xlib_xauth.Xauthority)
