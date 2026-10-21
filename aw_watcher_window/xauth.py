"""Xauthority matching compatible with Mutter's Xwayland authority files.

Mutter writes a FamilyLocal record and a FamilyWild record with an empty
display number. python-xlib 0.31 only matches exact family, address and
number, so it rejects these records. Upstream's newer matcher handles empty
numbers and python-xlib/python-xlib#296 proposes FamilyWild support, but the
watcher stays on 0.31 because of CPU stalls (see pyproject.toml).

The compatibility matcher keeps upstream's exact matches first. It then falls
back to two tightly bounded cases, in this order:

1. FamilyLocal with the current address and an empty display number.
2. FamilyWild with the explicit display number, or with an empty number.

FamilyWild ignores the address, as the X authority format defines it. Other
families and addresses are still required to match exactly. The installed
matcher is process-wide, so call install() before the first Display().
"""

from Xlib import error
from Xlib import xauth as xlib_xauth

# Xauth.h FamilyWild. python-xlib 0.31 does not export it.
FAMILY_WILD = 0xFFFF


class CompatXauthority(xlib_xauth.Xauthority):
    def get_best_auth(self, family, address, dispno, types=(b"MIT-MAGIC-COOKIE-1",)):
        try:
            # Exact matches always win, so existing setups behave as before.
            return super().get_best_auth(family, address, dispno, types)
        except error.XNoAuthError:
            pass

        num = str(dispno).encode()
        fallbacks = (
            lambda efam, eaddr, enum: efam == family
            and eaddr == address
            and enum == b"",
            lambda efam, eaddr, enum: efam == FAMILY_WILD and enum == num,
            lambda efam, eaddr, enum: efam == FAMILY_WILD and enum == b"",
        )
        for t in types:
            for matches in fallbacks:
                found = [
                    edata
                    for efam, eaddr, enum, ename, edata in self.entries
                    if ename == t and matches(efam, eaddr, enum)
                ]
                # Like upstream, the last matching record wins.
                if found:
                    return (t, found[-1])

        raise error.XNoAuthError((family, address, dispno))


def install() -> None:
    """Route python-xlib's connection auth lookup through CompatXauthority.

    This changes python-xlib for the whole process, so call it only from the
    watcher's own startup, before the first Display() is created.
    """
    xlib_xauth.Xauthority = CompatXauthority
