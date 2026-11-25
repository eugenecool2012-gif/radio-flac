# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec для radio-flac (Windows, GTK4 + libadwaita + GStreamer).

Собирается на windows-latest в MSYS2 (MINGW64). Всё дерево GTK копируется
в бандл, поэтому .exe получается «портативным»: рядом не нужны MSYS2/DLL.
"""
import glob
import os
import sys

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# --- PyGObject + typelibs (girepository-1.0) ---
for mod in ("gi",):
    d, b, h = collect_all(mod)
    datas += d
    binaries += b
    hiddenimports += h

hiddenimports += [
    "gi.repository.Gtk",
    "gi.repository.Adw",
    "gi.repository.Gst",
    "gi.repository.GstAudio",
    "gi.repository.GstPbutils",
    "gi.repository.Gdk",
    "gi.repository.GdkPixbuf",
    "gi.repository.Gio",
    "gi.repository.GLib",
    "gi.repository.GObject",
    "gi.repository.Pango",
    "rf_icons",
    "rf_cast",
    "rf_tray",
    "rf_mpris",
]

# --- GTK runtime из MSYS2 (данные: схемы, иконки, локали, css) ---
if os.name == "nt":
    prefix = sys.prefix                      # C:\...\msys64\mingw64
    share = os.path.join(prefix, "share")
    for sub in ("glib-2.0", "gtk-4.0", "icons", "fontconfig", "locale", "themes"):
        p = os.path.join(share, sub)
        if os.path.isdir(p):
            datas.append((p, os.path.join("share", sub)))

    for rel in ("lib/girepository-1.0", "lib/gdk-pixbuf-2.0", "etc/gtk-4.0"):
        p = os.path.join(prefix, rel.replace("/", os.sep))
        if os.path.isdir(p):
            datas.append((p, rel))

    # DLL: берём только те, что лежат в mingw64\bin — UCRT/python DLL не дублируем
    for dll in glob.glob(os.path.join(prefix, "bin", "*.dll")):
        base = os.path.basename(dll).lower()
        if base.startswith(("python", "vcruntime", "ucrtbase", "api-ms-")):
            continue
        binaries.append((dll, "."))

    # плагины GStreamer
    gst = os.path.join(prefix, "lib", "gstreamer-1.0")
    if os.path.isdir(gst):
        binaries += [(f, os.path.join("lib", "gstreamer-1.0"))
                     for f in glob.glob(os.path.join(gst, "*.dll"))]
        datas.append((gst, "lib/gstreamer-1.0"))

icon = "assets/icon.ico" if os.path.exists("assets/icon.ico") else None

a = Analysis(
    ["radio_flac_gui.py"],
    pathex=[os.path.abspath(".")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=["pyi_rth_gtk.py"],
    excludes=["tkinter", "numpy", "pandas", "matplotlib", "PIL", "test", "unittest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="radio-flac-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=["vcruntime140.dll", "python3*.dll"],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
