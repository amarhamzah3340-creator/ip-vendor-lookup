import subprocess
import sys
from pathlib import Path


class MonitorGUI:
    def __init__(self, auto_start: bool = False):
        self.auto_start = auto_start
        self._proc = None
        self._web_path = Path(__file__).with_name("web.py")

    def start_server(self) -> None:
        if self._proc and self._proc.poll() is None:
            print("[INFO] Server already running")
            return

        self._proc = subprocess.Popen([sys.executable, str(self._web_path), "--start"])
        print("[INFO] Server started")

    def stop_server(self) -> None:
        if not self._proc or self._proc.poll() is not None:
            print("[INFO] Server is not running")
            return

        self._proc.terminate()
        self._proc.wait(timeout=10)
        print("[INFO] Server stopped")

    def run(self) -> None:
        print("=== PPP Monitor Launcher ===")
        if self.auto_start:
            self.start_server()

        print("Commands: start, stop, quit")
        while True:
            cmd = input("> ").strip().lower()
            if cmd == "start":
                self.start_server()
            elif cmd == "stop":
                self.stop_server()
            elif cmd in {"quit", "exit"}:
                self.stop_server()
                break
            else:
                print("Unknown command")


if __name__ == "__main__":
    app = MonitorGUI(auto_start=False)
    app.run()
