"""Chromecast: поиск устройств и трансляция станции (pychromecast)."""
import os
import sys
import threading

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

PY_DIR = os.path.expanduser("~/.local/share/radio-flac/py")
if os.path.isdir(PY_DIR) and PY_DIR not in sys.path:
    sys.path.append(PY_DIR)

CONTENT_TYPES = {
    "MP3": "audio/mpeg",
    "AAC": "audio/aac",
    "AAC+": "audio/aac",
    "OGG": "audio/ogg",
    "OPUS": "audio/ogg",
    "FLAC": "audio/flac",
}


def content_type(codec):
    return CONTENT_TYPES.get((codec or "").upper().split()[0] if codec else "", "audio/mpeg")


def available():
    try:
        import pychromecast  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


class CastSession:
    """Одна активная трансляция: устройство + медиа-контроллер."""

    def __init__(self):
        self.cast = None
        self.name = ""

    @property
    def active(self):
        return self.cast is not None

    def play(self, station, friendly_name=None):
        import pychromecast

        casts, browser = pychromecast.discovery.discover_chromecasts(timeout=7)
        try:
            if not casts:
                raise RuntimeError("устройства Chromecast не найдены")
            device = None
            for c in casts:
                if friendly_name and c.cast_info.friendly_name == friendly_name:
                    device = c
                    break
            device = device or casts[0]
            device.wait(timeout=15)
            controller = device.media_controller
            controller.play_media(station["url"], content_type(station.get("codec")))
            controller.block_until_active(timeout=20)
            self.cast = device
            self.name = device.cast_info.friendly_name
            return self.name
        finally:
            try:
                browser.stop_discovery()
            except Exception:  # noqa: BLE001
                pass

    def stop(self):
        if self.cast is not None:
            try:
                self.cast.media_controller.stop()
            except Exception:  # noqa: BLE001
                pass
            self.cast = None
            self.name = ""

    def set_volume(self, value):
        if self.cast is None:
            return
        try:
            self.cast.set_volume(max(0.0, min(1.0, value)))
        except Exception:  # noqa: BLE001
            pass


class CastDialog(Adw.Dialog):
    """Окно выбора устройства Chromecast."""

    def __init__(self, station, on_cast):
        super().__init__(title="Трансляция на Chromecast", content_width=420, content_height=420)
        self.station = station
        self.on_cast = on_cast

        view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        view.add_top_bar(header)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                      margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        self.status = Gtk.Label(label="Ищу устройства в сети…", xalign=0,
                                css_classes=["dim-label"])
        self.list = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        self.list.connect("row-activated", self._row_activated)
        self.refresh_button = Gtk.Button(label="Обновить поиск", css_classes=["pill"])
        self.refresh_button.connect("clicked", lambda *_: self.discover())
        hint = Gtk.Label(xalign=0, wrap=True, css_classes=["dim-label", "caption"],
                         label="Если устройств нет: проверьте, что телефон/колонка Chromecast "
                               "в той же сети, что и компьютер.")
        box.append(self.status)
        box.append(Gtk.ScrolledWindow(child=self.list, vexpand=True, has_frame=True))
        box.append(self.refresh_button)
        box.append(hint)
        view.set_content(box)
        self.set_child(view)
        self.discover()

    def discover(self):
        while (row := self.list.get_first_child()) is not None:
            self.list.remove(row)
        self.status.set_text("Ищу устройства в сети…")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        if not available():
            GLib.idle_add(self._failed, "модуль pychromecast не установлен")
            return
        try:
            import pychromecast
            casts, browser = pychromecast.discovery.discover_chromecasts(timeout=7)
            names = [c.cast_info.friendly_name for c in casts]
            browser.stop_discovery()
        except Exception as e:  # noqa: BLE001
            GLib.idle_add(self._failed, str(e))
            return
        GLib.idle_add(self._filled, names)

    def _failed(self, message):
        self.status.set_text(f"Поиск не удался: {message}")
        return False

    def _filled(self, names):
        for name in names:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(spacing=10, margin_top=10, margin_bottom=10,
                          margin_start=12, margin_end=12)
            box.append(Gtk.Image(icon_name="video-display-symbolic"))
            box.append(Gtk.Label(label=name, xalign=0))
            row.set_child(box)
            row.device_name = name
            self.list.append(row)
        self.status.set_text(f"Найдено устройств: {len(names)}" if names
                             else "Устройства не найдены")
        self.refresh_button.set_sensitive(True)
        return False

    def _row_activated(self, _list, row):
        self.close()
        self.on_cast(self.station, row.device_name)
