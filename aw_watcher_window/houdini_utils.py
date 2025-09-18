# aw_watcher_window/houdini_utils.py
# -*- coding: utf-8 -*-
"""
Извлечение абсолютного пути текущей сцены Houdini (.hip/.hiplc/.hipnc) по PID процесса.
Приоритет источников:
  1) cmdline() — ищем .hip* в аргументах (включая кейс: "dir", "file.hip")
  2) open_files() — иногда сцена видна среди открытых файлов
  3) fallback: аккуратный разбор заголовка окна — берём абсолютный путь до " - Houdini ..."
Возврат: абсолютный нормализованный путь (os.path.realpath) или None.
"""

from __future__ import annotations
import os
import psutil

_HIP_SUFFIXES = (".hip", ".hiplc", ".hipnc")


def _strip_title_suffix(title: str) -> str:
    """
    У Houdini заголовок обычно: "<путь/имя>.hip* - Houdini FX" (или "Houdini Indie/Core").
    Берём левую часть до " - ".
    """
    return title.split(" - ", 1)[0].strip()


def _endswith_hip(path: str) -> bool:
    try:
        return path.lower().endswith(_HIP_SUFFIXES)
    except Exception:
        return False


def _ensure_abs(path: str, proc: psutil.Process) -> str:
    """
    Если путь относительный — пробуем разрешить через cwd процесса.
    Возвращаем os.path.realpath для аккуратной нормализации.
    """
    p = path
    try:
        if not os.path.isabs(p):
            p = os.path.join(proc.cwd(), p)
    except Exception:
        pass
    return os.path.realpath(p)


def get_houdini_scene_path(pid: int, fallback_title: str) -> str | None:
    """
    Возвращает абсолютный путь текущей .hip/.hiplc/.hipnc для данного PID Houdini.
    Приоритет: cmdline() -> open_files() -> аккуратный парсинг заголовка.
    """
    try:
        proc = psutil.Process(pid)

        argv = []
        try:
            argv = proc.cmdline() or []
        except Exception:
            argv = []

        cand = None

        for arg in argv:
            if _endswith_hip(arg):
                cand = arg.strip('\'"')
                break

        if cand is None:
            for i in range(len(argv) - 1):
                a, b = argv[i].strip('\'"'), argv[i + 1].strip('\'"')
                if os.path.isabs(a) and _endswith_hip(b):
                    cand = os.path.join(a, b)
                    break

        if cand:
            return _ensure_abs(cand, proc)

        try:
            for f in proc.open_files():
                path = getattr(f, "path", None)
                if path and _endswith_hip(path):
                    return os.path.realpath(path)
        except Exception:
            pass

        pre = _strip_title_suffix(fallback_title)
        if _endswith_hip(pre) and os.path.isabs(pre):
            return os.path.realpath(pre)

    except Exception:
        pass

    return None
