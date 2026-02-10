import importlib.util
import sys
from pathlib import Path


def _load_from_module(module_name: str):
    try:
        module = __import__(module_name, fromlist=["MonitorGUI"])
    except ModuleNotFoundError:
        return None
    return getattr(module, "MonitorGUI", None)


def _load_from_file(file_path: Path, module_name: str):
    if not file_path.exists():
        return None

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "MonitorGUI", None)


def _load_monitor_gui_class():
    for module_name in ("launcher_gui", "gui"):
        monitor_gui = _load_from_module(module_name)
        if monitor_gui is not None:
            return monitor_gui

    search_roots = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        search_roots.append(Path(meipass))

    search_roots.append(Path(__file__).resolve().parent)
    search_roots.append(Path(sys.executable).resolve().parent)

    module_counter = 0
    for root in search_roots:
        for filename in ("launcher_gui.py", "gui.py"):
            monitor_gui = _load_from_file(root / filename, f"launcher_fallback_{module_counter}")
            module_counter += 1
            if monitor_gui is not None:
                return monitor_gui

    raise ModuleNotFoundError("No module named 'launcher_gui' or 'gui' at runtime")


if __name__ == "__main__":
    MonitorGUI = _load_monitor_gui_class()
    app = MonitorGUI(auto_start=False)
    app.run()
