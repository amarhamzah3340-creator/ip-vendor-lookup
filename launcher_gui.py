import socket
import threading
import time
import webbrowser
from wsgiref.simple_server import make_server

import tkinter as tk


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
        self.root.geometry("520x240")
        self.root.minsize(480, 220)
        self.root.configure(bg="#060f3d")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.status_var = tk.StringVar(value="Stopped")
        self.url_var = tk.StringVar(value=self.lan_url)
        self.auto_start_var = tk.BooleanVar(value=self.auto_start_default)

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
        container = tk.Frame(self.root, bg="#060f3d", padx=18, pady=18)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text="MikroTik PPP Monitor",
            font=("Segoe UI", 22, "bold"),
            fg="#eff4ff",
            bg="#060f3d",
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        status_card = tk.Frame(container, bg="#11266f", padx=12, pady=10)
        status_card.pack(fill="x", pady=(0, 16))

        tk.Label(status_card, text="Status:", font=("Segoe UI", 12), fg="#dbe5ff", bg="#11266f").pack(side="left")
        self.status_label = tk.Label(status_card, textvariable=self.status_var, font=("Segoe UI", 12, "bold"), fg="#f46d7a", bg="#11266f")
        self.status_label.pack(side="left", padx=(8, 20))

        tk.Label(status_card, text="LAN:", font=("Segoe UI", 12), fg="#dbe5ff", bg="#11266f").pack(side="left")
        link = tk.Label(status_card, textvariable=self.url_var, font=("Segoe UI", 12, "underline"), fg="#66a3ff", bg="#11266f", cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda _e: self.open_browser())

        button_row = tk.Frame(container, bg="#060f3d")
        button_row.pack(fill="x")

        self.start_btn = tk.Button(
            button_row,
            text="START",
            font=("Segoe UI", 12, "bold"),
            bg="#4f78ff",
            fg="white",
            activebackground="#3f66e4",
            relief="flat",
            padx=20,
            pady=10,
            command=self.start_server,
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = tk.Button(
            button_row,
            text="STOP",
            font=("Segoe UI", 12, "bold"),
            bg="#f25f75",
            fg="white",
            activebackground="#e64d65",
            relief="flat",
            padx=20,
            pady=10,
            command=self.stop_server,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=(0, 10))

        tk.Button(
            button_row,
            text="QUIT",
            font=("Segoe UI", 12, "bold"),
            bg="#1f2f7a",
            fg="#eff4ff",
            activebackground="#1a2867",
            relief="flat",
            padx=20,
            pady=10,
            command=self._on_close,
        ).pack(side="left")

    def _set_running_ui(self, running: bool) -> None:
        if running:
            self.status_var.set("● Running")
            self.status_label.configure(fg="#66f18a")
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
        else:
            self.status_var.set("Stopped")
            self.status_label.configure(fg="#f46d7a")
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")

    def start_server(self) -> None:
        if self._server is not None:
            return

        try:
            import web as web_module
        except Exception:
            return

        self._web_module = web_module

        try:
            self._server = make_server("0.0.0.0", self.port, web_module.app)
        except Exception:
            self._server = None
            return

        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()
        self._set_running_ui(True)
        threading.Thread(target=self._open_browser_when_ready, daemon=True).start()

    def _open_browser_when_ready(self) -> None:
        if self._wait_server_ready(timeout=12):
            self.root.after(0, self.open_browser)

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
            self._set_running_ui(False)
            return

        try:
            self._server.shutdown()
            self._server.server_close()
        except Exception:
            pass

        if self._web_module and hasattr(self._web_module, "stop_active_collector"):
            try:
                self._web_module.stop_active_collector()
            except Exception:
                pass

        self._server = None
        self._server_thread = None
        self._set_running_ui(False)

    def open_browser(self) -> None:
        if self._server is None:
            return
        if not self._wait_server_ready(timeout=2):
            return
        webbrowser.open(self.local_url)

    def _on_close(self) -> None:
        self.stop_server()
        self.root.destroy()

    def run(self) -> None:
        self._set_running_ui(False)
        if self.auto_start_var.get():
            self.start_server()
        self.root.mainloop()


if __name__ == "__main__":
    app = MonitorGUI(auto_start=False)
    app.run()
