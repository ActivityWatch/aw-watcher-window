# aw_watcher_window/nuke_utils.py
import os
import psutil

def _strip_title_suffix(title: str) -> str:
    # У Nuke заголовок вида: "/path/file.nk - NukeX"
    # Берём левую часть до " - "
    return title.split(" - ", 1)[0].strip()

def get_nuke_script_path(pid: int, fallback_title: str) -> str | None:
    """
    Возвращает абсолютный путь текущего .nk-скрипта Nuke.
    Приоритет: cmdline() -> open_files() -> (аккуратный) разбор заголовка.
    Без склейки с cwd, чтобы не получать /cgru/... вместо реального пути.
    """
    try:
        proc = psutil.Process(pid)

        # 1) cmdline: ищем .nk, либо "dir", "file.nk"
        argv = []
        try:
            argv = proc.cmdline() or []
        except Exception:
            argv = []

        cand = None
        # а) точное попадание
        for arg in argv:
            if arg.lower().endswith(".nk"):
                cand = arg
                break
        # б) "dir", "file.nk" (рядом)
        if cand is None:
            for i in range(len(argv) - 1):
                a, b = argv[i], argv[i + 1]
                if a.startswith(os.sep) and b.lower().endswith(".nk"):
                    cand = os.path.join(a, b)
                    break

        if cand:
            if not os.path.isabs(cand):
                # Если вдруг относительный, пробуем разрешить через cwd
                try:
                    cand = os.path.join(proc.cwd(), cand)
                except Exception:
                    pass
            return os.path.realpath(cand)

        # 2) open_files: иногда скрипт виден в открытых файлах
        try:
            for f in proc.open_files():
                if f.path.lower().endswith(".nk"):
                    return os.path.realpath(f.path)
        except Exception:
            pass

        # 3) заголовок: берём только абсолютный путь и только до " - NukeX"
        pre = _strip_title_suffix(fallback_title)
        if pre.lower().endswith(".nk") and os.path.isabs(pre):
            return os.path.realpath(pre)

    except Exception:
        pass

    return None
