import importlib
import importlib.util
import socket
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server
import tkinter as tk
from tkinter.scrolledtext import ScrolledText


class MonitorGUI:
    def __init__(self, auto_start: bool = False, port: int = 1080):
        self.auto_start_default = auto_start
        self.port = port
        self.local_ip = self._detect_local_ip()
        self.local_url = f"http://127.0.0.1:{self.port}"
        self.lan_url = f"http://{self.local_ip}:{self.port}"

        self._server = None
        self._server_thread = None
        self._web_module = None

        self.root = tk.Tk()
        self.root.title("MikroTik PPP Monitor")
        self.root.geometry("900x580")
        self.root.minsize(840, 520)
        self.root.configure(bg="#050b2e")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.status_var = tk.StringVar(value="Stopped")
        self.url_var = tk.StringVar(value=self.lan_url)
        self.auto_start_var = tk.BooleanVar(value=self.auto_start_default)
        self.auto_open_var = tk.BooleanVar(value=True)

        self._build_ui()

    def _detect_local_ip(self) -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"
        finally:
            sock.close()

    def _build_ui(self) -> None:
        container = tk.Frame(self.root, bg="#050b2e")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        title = tk.Label(
            container,
            text="⚡ MikroTik PPP Monitor",
            font=("Segoe UI", 22, "bold"),
            fg="#F2F4FF",
            bg="#050b2e",
            anchor="w",
        )
        title.pack(fill="x", pady=(0, 12))

        info = tk.Frame(container, bg="#0d1f66", padx=12, pady=10)
        info.pack(fill="x", pady=(0, 12))

        tk.Label(info, text="Status:", font=("Segoe UI", 14), fg="#DDE5FF", bg="#0d1f66").pack(side="left")
        self.status_label = tk.Label(info, textvariable=self.status_var, font=("Segoe UI", 14, "bold"), fg="#66F18A", bg="#0d1f66")
        self.status_label.pack(side="left", padx=(10, 18))

        tk.Label(info, text="LAN URL:", font=("Segoe UI", 14), fg="#DDE5FF", bg="#0d1f66").pack(side="left")
        link = tk.Label(info, textvariable=self.url_var, font=("Segoe UI", 14, "underline"), fg="#66A3FF", bg="#0d1f66", cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda _e: self.open_browser(use_lan=True))

        button_row = tk.Frame(container, bg="#050b2e")
        button_row.pack(fill="x", pady=(0, 12))

        self.start_btn = tk.Button(button_row, text="▶ Start", font=("Segoe UI", 12, "bold"), bg="#3f66ff", fg="white", activebackground="#3356de", relief="flat", padx=16, pady=10, command=self.start_server)
        self.start_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = tk.Button(button_row, text="■ Stop", font=("Segoe UI", 12, "bold"), bg="#f05a73", fg="white", activebackground="#db4c65", relief="flat", padx=16, pady=10, command=self.stop_server, state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 8))

        tk.Button(button_row, text="🌐 Open Localhost", font=("Segoe UI", 12), bg="#2146c5", fg="white", activebackground="#1b3cab", relief="flat", padx=12, pady=10, command=lambda: self.open_browser(use_lan=False)).pack(side="left", padx=(0, 8))
        tk.Button(button_row, text="🌍 Open LAN IP", font=("Segoe UI", 12), bg="#1e3a9a", fg="white", activebackground="#1a3286", relief="flat", padx=12, pady=10, command=lambda: self.open_browser(use_lan=True)).pack(side="left", padx=(0, 8))

        tk.Checkbutton(button_row, text="Auto-open saat start", variable=self.auto_open_var, font=("Segoe UI", 11), fg="#E4EAFF", bg="#050b2e", activebackground="#050b2e", activeforeground="#E4EAFF", selectcolor="#050b2e").pack(side="left")

        tk.Button(button_row, text="🗑 Clear", font=("Segoe UI", 11), bg="#15296F", fg="#E4EAFF", relief="flat", padx=10, pady=8, command=self.clear_log).pack(side="right")

        log_frame = tk.Frame(container, bg="#0d1f66", padx=10, pady=10)
        log_frame.pack(fill="both", expand=True)

        tk.Label(log_frame, text="📋 System Log", font=("Segoe UI", 15, "bold"), fg="#F2F4FF", bg="#0d1f66").pack(anchor="w", pady=(0, 8))

        self.log_text = ScrolledText(log_frame, wrap="word", height=16, bg="#020715", fg="#00FF8A", insertbackground="#00FF8A", font=("Consolas", 10), relief="flat", padx=10, pady=10)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

    def _append_log(self, message: str, level: str = "INFO") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {message}\n"

        self.log_text.configure(state="normal")
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _append_log_threadsafe(self, message: str, level: str = "INFO") -> None:
        self.root.after(0, self._append_log, message, level)

    def clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _set_running_ui(self, running: bool) -> None:
        if running:
            self.status_var.set("● Running")
            self.status_label.configure(fg="#66F18A")
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
        else:
            self.status_var.set("Stopped")
            self.status_label.configure(fg="#F3656D")
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")

    def _prepare_runtime_paths(self) -> list[Path]:
        roots: list[Path] = []

        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass))

        roots.append(Path(__file__).resolve().parent)
        roots.append(Path(sys.executable).resolve().parent)

        for root in roots:
            root_s = str(root)
            if root.exists() and root_s not in sys.path:
                sys.path.insert(0, root_s)

        return roots

    def _load_module_from_file(self, module_name: str, file_path: Path):
        if not file_path.exists():
            return None

        file_spec = importlib.util.spec_from_file_location(module_name, file_path)
        if file_spec is None or file_spec.loader is None:
            return None

        module = importlib.util.module_from_spec(file_spec)
        sys.modules[module_name] = module
        file_spec.loader.exec_module(module)
        return module

    def _load_web_module(self):
        roots = self._prepare_runtime_paths()

        spec = importlib.util.find_spec("web")
        if spec is not None:
            return importlib.import_module("web")

        for root in roots:
            # Ensure collector is importable before web executes `from collector import ...`.
            if "collector" not in sys.modules:
                self._load_module_from_file("collector", root / "collector.py")

            web_module = self._load_module_from_file("web", root / "web.py")
            if web_module is not None:
                return web_module

        raise ModuleNotFoundError("No module named 'web'")

    def start_server(self) -> None:
        if self._server is not None:
            self._append_log("Server already running")
            return

        try:
            web_module = self._load_web_module()
        except Exception as exc:
            self._append_log(f"Failed to import web server deps: {exc}", "ERROR")
            return

        self._web_module = web_module
        if hasattr(self._web_module, "set_log_callback"):
            self._web_module.set_log_callback(self._append_log_threadsafe)

        self._append_log(f"Starting embedded server on localhost {self.local_url} and LAN {self.lan_url}")

        class GuiRequestHandler(WSGIRequestHandler):
            def log_message(handler_self, fmt: str, *args) -> None:  # noqa: N805
                self._append_log_threadsafe(fmt % args, "WEB")

        try:
            self._server = make_server("0.0.0.0", self.port, web_module.app, handler_class=GuiRequestHandler)
        except Exception as exc:
            self._append_log(f"Failed starting server: {exc}", "ERROR")
            self._server = None
            return

        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()
        self._set_running_ui(True)

        if self.auto_open_var.get():
            threading.Thread(target=self._open_browser_when_ready, daemon=True).start()

    def _open_browser_when_ready(self) -> None:
        if self._wait_server_ready(timeout=12):
            self.root.after(0, lambda: self.open_browser(use_lan=False))
        else:
            self.root.after(0, self._append_log, "Server belum ready, coba klik Open Localhost", "WARN")

    def _wait_server_ready(self, timeout: int = 12) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._server is None:
                return False
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.6):
                    return True
            except OSError:
                time.sleep(0.25)
        return False

    def stop_server(self) -> None:
        if self._server is None:
            self._append_log("Server is not running")
            self._set_running_ui(False)
            return

        self._append_log("Stopping server...")

        try:
            self._server.shutdown()
            self._server.server_close()
        except Exception as exc:
            self._append_log(f"Error while stopping server: {exc}", "WARN")

        if self._web_module and hasattr(self._web_module, "stop_active_collector"):
            try:
                self._web_module.stop_active_collector()
            except Exception as exc:
                self._append_log(f"Collector cleanup warning: {exc}", "WARN")

        self._server = None
        self._server_thread = None
        self._set_running_ui(False)
        self._append_log("Server stopped")

    def open_browser(self, use_lan: bool = False) -> None:
        target = self.lan_url if use_lan else self.local_url

        if self._server is None:
            self._append_log("Server belum jalan. Klik Start dulu.", "WARN")
            return

        if not self._wait_server_ready(timeout=2):
            self._append_log("Server belum ready. Coba lagi beberapa detik.", "WARN")
            return

        webbrowser.open(target)
        self._append_log(f"Opening browser: {target}")

    def _on_close(self) -> None:
        self.stop_server()
        self.root.destroy()

    def run(self) -> None:
        self._append_log("============================================================")
        self._append_log("MikroTik PPP Monitor GUI")
        self._append_log(f"Localhost URL: {self.local_url}")
        self._append_log(f"LAN URL: {self.lan_url}")
        self._append_log("============================================================")
        self._set_running_ui(False)

        if self.auto_start_var.get():
            self._append_log("Auto-start enabled. Starting server...")
            self.start_server()

        self.root.mainloop()


if __name__ == "__main__":
    app = MonitorGUI(auto_start=False)
    app.run()
