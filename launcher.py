import importlib.util
import sys
from pathlib import Path


def _load_monitor_gui_class():
    try:
        from gui import MonitorGUI
        return MonitorGUI
    except ModuleNotFoundError:
        pass

    try:
        from launcher_gui import MonitorGUI
        return MonitorGUI
    except ModuleNotFoundError:
        pass

    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "gui.py")
        candidates.append(Path(meipass) / "launcher_gui.py")

    candidates.append(Path(__file__).resolve().with_name("gui.py"))
    candidates.append(Path(__file__).resolve().with_name("launcher_gui.py"))
    candidates.append(Path(sys.executable).resolve().parent / "gui.py")
    candidates.append(Path(sys.executable).resolve().parent / "launcher_gui.py")

    for module_name, gui_path in [("gui", c) for c in candidates]:
        if not gui_path.exists():
            continue

        spec = importlib.util.spec_from_file_location(module_name, gui_path)
        if not spec or not spec.loader:
            continue

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "MonitorGUI"):
            return module.MonitorGUI

    raise ModuleNotFoundError("No module named 'gui' or 'launcher_gui' at runtime")


if __name__ == "__main__":
    MonitorGUI = _load_monitor_gui_class()
    app = MonitorGUI(auto_start=False)
    app.run()
