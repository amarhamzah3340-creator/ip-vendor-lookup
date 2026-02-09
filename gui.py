import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter.scrolledtext import ScrolledText


class MonitorGUI:
    def __init__(self, auto_start: bool = False, host: str = "127.0.0.1", port: int = 1080):
        self.auto_start_default = auto_start
        self.host = host
        self.port = port
        self.url = f"http://{self.host}:{self.port}"

        self._proc = None
        self._reader_thread = None
        self._web_path = Path(__file__).with_name("web.py")

        self.root = tk.Tk()
        self.root.title("MikroTik PPP Monitor")
        self.root.geometry("1000x680")
        self.root.configure(bg="#071247")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.status_var = tk.StringVar(value="Stopped")
        self.url_var = tk.StringVar(value=self.url)
        self.auto_start_var = tk.BooleanVar(value=self.auto_start_default)
        self.auto_open_var = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self) -> None:
        container = tk.Frame(self.root, bg="#071247")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        title = tk.Label(
            container,
            text="⚡  MikroTik PPP Monitor",
            font=("Segoe UI", 28, "bold"),
            fg="#F2F4FF",
            bg="#071247",
            anchor="w",
        )
        title.pack(fill="x", pady=(0, 18))

        info = tk.Frame(container, bg="#101F63", padx=16, pady=14)
        info.pack(fill="x", pady=(0, 16))

        tk.Label(info, text="Status:", font=("Segoe UI", 19), fg="#DDE5FF", bg="#101F63").pack(side="left")
        self.status_label = tk.Label(info, textvariable=self.status_var, font=("Segoe UI", 19, "bold"), fg="#66F18A", bg="#101F63")
        self.status_label.pack(side="left", padx=(12, 28))

        tk.Label(info, text="URL:", font=("Segoe UI", 19), fg="#DDE5FF", bg="#101F63").pack(side="left")
        link = tk.Label(info, textvariable=self.url_var, font=("Segoe UI", 19, "underline"), fg="#66A3FF", bg="#101F63", cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda _e: self.open_browser())

        button_row = tk.Frame(container, bg="#071247")
        button_row.pack(fill="x", pady=(0, 16))

        self.start_btn = tk.Button(
            button_row,
            text="▶ Start Server",
            font=("Segoe UI", 16, "bold"),
            bg="#4E75EE",
            fg="white",
            activebackground="#3E63D3",
            relief="flat",
            padx=20,
            pady=14,
            command=self.start_server,
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = tk.Button(
            button_row,
            text="■ Stop Server",
            font=("Segoe UI", 16, "bold"),
            bg="#F3656D",
            fg="white",
            activebackground="#E2525B",
            relief="flat",
            padx=20,
            pady=14,
            command=self.stop_server,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=(0, 10))

        open_btn = tk.Button(
            button_row,
            text="🌐 Open Browser",
            font=("Segoe UI", 16),
            bg="#4E75EE",
            fg="white",
            activebackground="#3E63D3",
            relief="flat",
            padx=20,
            pady=14,
            command=self.open_browser,
        )
        open_btn.pack(side="left", padx=(0, 14))

        auto_open_cb = tk.Checkbutton(
            button_row,
            text="Auto-open browser saat server started",
            variable=self.auto_open_var,
            font=("Segoe UI", 13),
            fg="#E4EAFF",
            bg="#071247",
            activebackground="#071247",
            activeforeground="#E4EAFF",
            selectcolor="#071247",
        )
        auto_open_cb.pack(side="left")

        clear_btn = tk.Button(
            button_row,
            text="🗑 Clear Log",
            font=("Segoe UI", 13),
            bg="#15296F",
            fg="#E4EAFF",
            relief="flat",
            padx=16,
            pady=10,
            command=self.clear_log,
        )
        clear_btn.pack(side="right")

        log_frame = tk.Frame(container, bg="#101F63", padx=14, pady=14)
        log_frame.pack(fill="both", expand=True)

        tk.Label(log_frame, text="📋 System Log", font=("Segoe UI", 20, "bold"), fg="#F2F4FF", bg="#101F63").pack(anchor="w", pady=(0, 12))

        self.log_text = ScrolledText(
            log_frame,
            wrap="word",
            height=20,
            bg="#000000",
            fg="#00FF5A",
            insertbackground="#00FF5A",
            font=("Consolas", 13),
            relief="flat",
            padx=12,
            pady=12,
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

    def _append_log(self, message: str, level: str = "INFO") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {message}\n"

        self.log_text.configure(state="normal")
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

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

    def start_server(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._append_log("Server already running")
            return

        cmd = [
            sys.executable,
            "-u",
            str(self._web_path),
            "--start",
            "--host",
            "0.0.0.0",
            "--port",
            str(self.port),
        ]

        self._append_log(f"Starting MikroTik Monitor on {self.url}")
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._set_running_ui(True)

        self._reader_thread = threading.Thread(target=self._stream_logs, daemon=True)
        self._reader_thread.start()

        if self.auto_open_var.get():
            self.root.after(1200, self.open_browser)

    def _stream_logs(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return

        for line in proc.stdout:
            clean = line.rstrip("\n")
            self.root.after(0, self._append_log, clean, "WEB")

        return_code = proc.poll()
        self.root.after(0, self._append_log, f"Server stopped with code {return_code}", "INFO")
        self.root.after(0, self._set_running_ui, False)

    def stop_server(self) -> None:
        if not self._proc or self._proc.poll() is not None:
            self._append_log("Server is not running")
            self._set_running_ui(False)
            return

        self._append_log("Stopping server...")
        self._proc.terminate()

        deadline = time.time() + 8
        while time.time() < deadline and self._proc.poll() is None:
            time.sleep(0.1)

        if self._proc.poll() is None:
            self._append_log("Force killing server process", "WARN")
            self._proc.kill()

        self._set_running_ui(False)

    def open_browser(self) -> None:
        webbrowser.open(self.url)
        self._append_log(f"Opening browser: {self.url}")

    def _on_close(self) -> None:
        self.stop_server()
        self.root.destroy()

    def run(self) -> None:
        self._append_log("============================================================")
        self._append_log("MikroTik PPP Monitor GUI")
        self._append_log("============================================================")
        self._set_running_ui(False)

        if self.auto_start_var.get():
            self._append_log("Auto-start enabled. Starting server...")
            self.start_server()

        self.root.mainloop()


if __name__ == "__main__":
    app = MonitorGUI(auto_start=False)
    app.run()
