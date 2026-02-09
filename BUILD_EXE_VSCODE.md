# Build EXE (Windows + VSCode)

Panduan cepat bikin `.exe` dari project ini.

## 1) Buka project di VSCode
- `File > Open Folder...` lalu pilih folder `ip-vendor-lookup`.
- Buka terminal VSCode: `Terminal > New Terminal`.

## 2) Buat virtual environment
```bash
python -m venv .venv
```

Aktifkan:

**PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**CMD**
```cmd
.venv\Scripts\activate.bat
```

## 3) Install dependency
```bash
pip install --upgrade pip
pip install pyinstaller flask routeros-api
```

## 4) Build EXE dengan spec file
Dari root project:
```bash
pyinstaller --clean launcher.spec
```

Hasil EXE akan ada di:
- `dist/MikroTikMonitor.exe`

## 5) Menjalankan aplikasi EXE
- Jalankan `MikroTikMonitor.exe`.
- Karena launcher berbasis command prompt, gunakan command:
  - `start` untuk start web server
  - `stop` untuk stop web server
  - `quit` untuk keluar

## 6) Jika EXE gagal jalan
Cek hal berikut:
- `config.json` format valid dan IP/user/password router benar.
- Port API MikroTik benar (default API plain: `8728`).
- Firewall Windows / network tidak blok koneksi.
- Build ulang dengan:
```bash
pyinstaller --clean --noconfirm launcher.spec
```

## 7) (Opsional) One-file EXE
Kalau ingin satu file `.exe`, jalankan:
```bash
pyinstaller --clean --onefile launcher.py --name MikroTikMonitor
```

Catatan: mode `--onefile` kadang lebih lambat startup dan lebih sensitif pada file data eksternal.
