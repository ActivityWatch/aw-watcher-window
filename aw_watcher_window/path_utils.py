"""
Utilities to normalize Windows file paths to studio-unified POSIX paths.

Use case:
    'X:\\KOLOTUN\\work\\2d\\comp\\shot_v0020.nk'
 -> '/studio/proj/KOLOTUN/work/2d/comp/shot_v0020.nk'
"""
from __future__ import annotations

import os
import re
from typing import Optional

_DRIVE_PREFIX_RE = re.compile(r"^[A-Za-z]:/")
_QUOTES = "\"'"


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] in _QUOTES and s[-1] == s[0]:
        return s[1:-1].strip()
    return s


def to_posix_slashes(p: str) -> str:
    """Win backslashes -> POSIX slashes. Keeps other strings intact."""
    return p.replace("\\", "/")


def normalize_project_path(path: Optional[str]) -> Optional[str]:
    """
    Convert Windows paths like 'X:\\PROJ\\...' to '/studio/proj/PROJ/...'.
    For non-drive or already-POSIX paths, returns a POSIX-slash version.

    Rules:
      - Strip wrapping quotes.
      - Backslashes -> forward slashes.
      - If matches '^[A-Za-z]:/' then:
          '/studio/proj/' + <rest after 'X:/' (without leading '/')>

    Examples:
      'X:\\KOLOTUN\\work\\a.nk' -> '/studio/proj/KOLOTUN/work/a.nk'
      'd:/foo/bar.hip'          -> '/studio/proj/foo/bar.hip'
      '/studio/proj/A/B.nk'     -> '/studio/proj/A/B.nk' (unchanged, slashes ensured)
    """
    if not path:
        return path

    p = _strip_quotes(path)
    p = to_posix_slashes(p)

    if _DRIVE_PREFIX_RE.match(p):
        rest = p[3:]
        rest = rest.lstrip("/")
        return "/studio/proj/" + rest

    return p


def remap_unc_to_proj(p: str, shares=("proj",)) -> str:
    """
    Example of future extension:
      '//fileserver/proj/KOLOTUN/work/a.nk' -> '/studio/proj/KOLOTUN/work/a.nk'
    Disabled by default; call explicitly when you want it.
    """
    posix = to_posix_slashes(_strip_quotes(p))
    if posix.startswith("//"):
        parts = posix.split("/")
        # ['', '', server, share, ...]
        if len(parts) >= 5 and parts[3] in shares:
            return "/studio/proj/" + "/".join(parts[4:])
    return posix
