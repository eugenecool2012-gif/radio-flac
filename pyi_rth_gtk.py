# -*- coding: utf-8 -*-
"""
Runtime hook: сообщаем GTK/GStreamer, где внутри бандла лежат схемы,
иконки, pixbuf-загрузчики и плагины.
"""
import os
import sys

base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
share = os.path.join(base, "share")
lib = os.path.join(base, "lib")


def _set(name, value):
    if os.path.exists(value):
        os.environ.setdefault(name, value)


_set("GSETTINGS_SCHEMA_DIR", os.path.join(share, "glib-2.0", "schemas"))
_set("GDK_PIXBUF_MODULE_FILE",
     os.path.join(lib, "gdk-pixbuf-2.0", "2.10.0", "loaders.cache"))
_set("GST_PLUGIN_PATH_1_0", os.path.join(lib, "gstreamer-1.0"))
_set("GIO_EXTRA_MODULES", os.path.join(lib, "gio", "modules"))
_set("GTK_DATA_PREFIX", base)
_set("GTK_EXE_PREFIX", base)
_set("GTK_PATH", os.path.join(base, "lib", "gtk-4.0"))
_set("XDG_DATA_DIRS", share)
_set("FONTCONFIG_PATH", os.path.join(base, "etc", "fonts"))
