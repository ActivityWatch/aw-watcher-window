# aw_watcher_window/nuke_utils.py
import os
import psutil

def get_nuke_script_path(pid: int, fallback_title: str) -> str | None:
    """
    Для процесса Nuke пытается найти открытый .nk-файл.
    Если файл найден, возвращает его абсолютный путь.
    Если нет — пытается склеить текущий рабочий каталог и имя из заголовка.
    """
    try:
        proc = psutil.Process(pid)
        for f in proc.open_files():
            if f.path.lower().endswith(".nk"):
                return f.path
        cwd = proc.cwd()
        if cwd and fallback_title and not os.path.isabs(fallback_title):
            return os.path.join(cwd, fallback_title)
    except Exception:
        pass
    return None
