import importlib.util
import sys
from pathlib import Path


def _import_monitor_gui_from_module():
    for module_name in ("gui", "launcher_gui"):
        try:
            module = __import__(module_name, fromlist=["MonitorGUI"])
            monitor_gui = getattr(module, "MonitorGUI", None)
            if monitor_gui is not None:
                return monitor_gui
        except ModuleNotFoundError:
            continue
    return None


def _import_monitor_gui_from_paths():
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        root = Path(meipass)
        candidates.extend([root / "gui.py", root / "launcher_gui.py"])

    script_dir = Path(__file__).resolve().parent
    exe_dir = Path(sys.executable).resolve().parent
    candidates.extend([
        script_dir / "gui.py",
        script_dir / "launcher_gui.py",
        exe_dir / "gui.py",
        exe_dir / "launcher_gui.py",
    ])

    for idx, file_path in enumerate(candidates):
        if not file_path.exists():
            continue

        spec = importlib.util.spec_from_file_location(f"launcher_gui_fallback_{idx}", file_path)
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        monitor_gui = getattr(module, "MonitorGUI", None)
        if monitor_gui is not None:
            return monitor_gui

    return None


def _load_monitor_gui_class():
    monitor_gui = _import_monitor_gui_from_module()
    if monitor_gui is not None:
        return monitor_gui

    monitor_gui = _import_monitor_gui_from_paths()
    if monitor_gui is not None:
        return monitor_gui

    raise ModuleNotFoundError("No module named 'gui' or 'launcher_gui' at runtime")


if __name__ == "__main__":
    MonitorGUI = _load_monitor_gui_class()
    app = MonitorGUI(auto_start=False)
    app.run()
