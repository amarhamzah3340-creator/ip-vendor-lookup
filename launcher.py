import importlib.util
import sys
from pathlib import Path


def _load_monitor_gui_class():
    try:
        from gui import MonitorGUI

        return MonitorGUI
    except ModuleNotFoundError:
        candidates = []

        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "gui.py")

        candidates.append(Path(__file__).resolve().with_name("gui.py"))
        candidates.append(Path(sys.executable).resolve().parent / "gui.py")

        for gui_path in candidates:
            if not gui_path.exists():
                continue

            spec = importlib.util.spec_from_file_location("gui", gui_path)
            if not spec or not spec.loader:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "MonitorGUI"):
                return module.MonitorGUI

        raise


if __name__ == "__main__":
    MonitorGUI = _load_monitor_gui_class()
    app = MonitorGUI(auto_start=False)
    app.run()
