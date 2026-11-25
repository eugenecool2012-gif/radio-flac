"""Иконки (favicon) станций: асинхронная загрузка с дисковым кэшем."""
import hashlib
import os
import threading
import urllib.request

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

CACHE_DIR = os.path.expanduser("~/.cache/radio-flac/icons")
UA = "radio-flac-gui/1.2 (+linux)"
MAX_BYTES = 600 * 1024
SIZE = 64

_waiters = {}
_lock = threading.Lock()


def _path_for(url):
    name = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, name)


def _texture_from_file(path):
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, SIZE, SIZE, True)
    except (GLib.Error, ValueError):
        return None
    if pixbuf is None:
        return None
    return Gdk.Texture.new_for_pixbuf(pixbuf)


def _download(url, path):
    os.makedirs(CACHE_DIR, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=8) as response:
        data = response.read(MAX_BYTES)
    if len(data) < 32:
        raise ValueError("слишком маленький файл")
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def _deliver(url, texture):
    callbacks = _waiters.pop(url, [])
    for cb in callbacks:
        try:
            cb(texture)
        except Exception:  # noqa: BLE001
            pass
    return False


def _worker(url, path):
    texture = None
    try:
        _download(url, path)
        texture = _texture_from_file(path)
    except Exception:  # noqa: BLE001
        texture = None
    GLib.idle_add(_deliver, url, texture)


def load(url, callback):
    """callback(Gdk.Texture | None) — всегда в главном потоке."""
    if not url:
        callback(None)
        return
    path = _path_for(url)
    if os.path.exists(path):
        texture = _texture_from_file(path)
        if texture is not None:
            callback(texture)
            return
        try:
            os.unlink(path)  # битый кэш
        except OSError:
            pass
    with _lock:
        if url in _waiters:
            _waiters[url].append(callback)
            return
        _waiters[url] = [callback]
    threading.Thread(target=_worker, args=(url, path), daemon=True).start()


class StationIcon(Gtk.Picture):
    """Квадратная иконка 32×32 с заглушкой, пока favicon не загрузился."""

    def __init__(self, url="", size=32):
        super().__init__(content_fit=Gtk.ContentFit.CONTAIN,
                         width_request=size, height_request=size,
                         valign=Gtk.Align.CENTER, css_classes=["station-icon"])
        self._size = size
        self.set_fallback()
        if url:
            self.set_url(url)

    def set_fallback(self):
        self.set_paintable(None)
        self.set_css_classes(["station-icon", "dim-label"])

    def set_url(self, url):
        def apply(texture):
            if texture is None:
                return
            self.set_paintable(texture)
            self.set_css_classes(["station-icon"])

        load(url, apply)


def preload(urls, limit=200):
    """Тихо прогревает кэш для первых N адресов."""
    for url in urls[:limit]:
        if url:
            load(url, lambda _t: None)


def cached_count():
    try:
        return len(os.listdir(CACHE_DIR))
    except OSError:
        return 0
