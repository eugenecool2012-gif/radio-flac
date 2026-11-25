"""MPRIS2: управление плеером из панели KDE, медиа-клавиш и блокировки экрана."""
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib  # noqa: E402

XML = """
<node>
  <interface name="org.mpris.MediaPlayer2">
    <method name="Raise"/>
    <method name="Quit"/>
    <property name="CanQuit" type="b" access="read"/>
    <property name="CanRaise" type="b" access="read"/>
    <property name="HasTrackList" type="b" access="read"/>
    <property name="Identity" type="s" access="read"/>
    <property name="DesktopEntry" type="s" access="read"/>
    <property name="SupportedUriSchemes" type="as" access="read"/>
    <property name="SupportedMimeTypes" type="as" access="read"/>
  </interface>
  <interface name="org.mpris.MediaPlayer2.Player">
    <method name="Next"/>
    <method name="Previous"/>
    <method name="Pause"/>
    <method name="PlayPause"/>
    <method name="Stop"/>
    <method name="Play"/>
    <method name="Seek">
      <arg name="Offset" type="x" direction="in"/>
    </method>
    <method name="SetPosition">
      <arg name="TrackId" type="o" direction="in"/>
      <arg name="Position" type="x" direction="in"/>
    </method>
    <method name="OpenUri">
      <arg name="Uri" type="s" direction="in"/>
    </method>
    <signal name="Seeked">
      <arg name="Position" type="x"/>
    </signal>
    <property name="PlaybackStatus" type="s" access="read"/>
    <property name="LoopStatus" type="s" access="readwrite"/>
    <property name="Rate" type="d" access="readwrite"/>
    <property name="Shuffle" type="b" access="readwrite"/>
    <property name="Metadata" type="a{sv}" access="read"/>
    <property name="Volume" type="d" access="readwrite"/>
    <property name="Position" type="x" access="read"/>
    <property name="MinimumRate" type="d" access="read"/>
    <property name="MaximumRate" type="d" access="read"/>
    <property name="CanGoNext" type="b" access="read"/>
    <property name="CanGoPrevious" type="b" access="read"/>
    <property name="CanPlay" type="b" access="read"/>
    <property name="CanPause" type="b" access="read"/>
    <property name="CanSeek" type="b" access="read"/>
    <property name="CanControl" type="b" access="read"/>
  </interface>
</node>
"""

PATH = "/org/mpris/MediaPlayer2"
BUS_NAME = "org.mpris.MediaPlayer2.radioflac"
TRACK_ID = "/org/radioflac/track/1"


class Mpris:
    """callbacks: play_pause, play, pause, stop, raise_window, set_volume(value)"""

    def __init__(self, callbacks):
        self.callbacks = callbacks
        self.conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        node = Gio.DBusNodeInfo.new_for_xml(XML)
        self.root_iface = node.interfaces[0]
        self.player_iface = node.interfaces[1]
        Gio.bus_own_name_on_connection(self.conn, BUS_NAME,
                                       Gio.BusNameOwnerFlags.REPLACE, None, None)
        self.root_id = self.conn.register_object(
            PATH, self.root_iface, self._on_root_call, self._on_root_prop, None)
        self.player_id = self.conn.register_object(
            PATH, self.player_iface, self._on_player_call, self._on_player_prop,
            self._on_player_set)
        self.status = "Stopped"
        self.station = ""
        self.title = ""
        self.volume = 0.8

    # ---------- свойства ----------
    def _on_root_prop(self, _conn, _sender, _path, _iface, name):
        values = {
            "CanQuit": GLib.Variant("b", True),
            "CanRaise": GLib.Variant("b", True),
            "HasTrackList": GLib.Variant("b", False),
            "Identity": GLib.Variant("s", "Radio FLAC"),
            "DesktopEntry": GLib.Variant("s", "radio-flac-gui"),
            "SupportedUriSchemes": GLib.Variant("as", ["http", "https"]),
            "SupportedMimeTypes": GLib.Variant("as", ["audio/mpeg", "audio/aac",
                                                      "audio/ogg", "audio/flac"]),
        }
        return values[name]

    def metadata(self):
        meta = {
            "mpris:trackid": GLib.Variant("o", TRACK_ID),
            "xesam:title": GLib.Variant("s", self.title or self.station or "Radio FLAC"),
            "xesam:album": GLib.Variant("s", self.station or "Интернет-радио"),
            "mpris:length": GLib.Variant("x", 0),
        }
        artist = self.title.split(" - ", 1)[0] if " - " in self.title else ""
        if artist:
            meta["xesam:artist"] = GLib.Variant("as", [artist])
        return meta

    def _on_player_prop(self, _conn, _sender, _path, _iface, name):
        if name == "PlaybackStatus":
            return GLib.Variant("s", self.status)
        if name == "LoopStatus":
            return GLib.Variant("s", "None")
        if name == "Rate" or name == "MinimumRate" or name == "MaximumRate":
            return GLib.Variant("d", 1.0)
        if name == "Shuffle":
            return GLib.Variant("b", False)
        if name == "Metadata":
            return GLib.Variant("a{sv}", self.metadata())
        if name == "Volume":
            return GLib.Variant("d", float(self.volume))
        if name == "Position":
            return GLib.Variant("x", 0)
        if name in ("CanGoNext", "CanGoPrevious", "CanSeek"):
            return GLib.Variant("b", False)
        if name in ("CanPlay", "CanPause", "CanControl"):
            return GLib.Variant("b", True)
        raise KeyError(name)

    def _on_player_set(self, _conn, _sender, _path, _iface, name, value):
        if name == "Volume":
            self.volume = float(value.unpack())
            self.callbacks["set_volume"](self.volume)
            return True
        if name in ("LoopStatus", "Rate", "Shuffle"):
            return True
        return False

    # ---------- методы ----------
    def _on_root_call(self, _conn, _sender, _path, _iface, method, _params, invocation):
        if method == "Raise":
            GLib.idle_add(self.callbacks["raise_window"])
        elif method == "Quit":
            GLib.idle_add(self.callbacks["quit"])
        invocation.return_value(None)

    def _on_player_call(self, _conn, _sender, _path, _iface, method, _params, invocation):
        mapping = {
            "Play": "play",
            "Pause": "pause",
            "PlayPause": "play_pause",
            "Stop": "stop",
        }
        if method in mapping:
            GLib.idle_add(self.callbacks[mapping[method]])
        invocation.return_value(None)

    # ---------- обновление ----------
    def update(self, status=None, station=None, title=None, volume=None):
        changed = {}
        if status is not None and status != self.status:
            self.status = status
            changed["PlaybackStatus"] = GLib.Variant("s", status)
        if station is not None and station != self.station:
            self.station = station
            changed["Metadata"] = GLib.Variant("a{sv}", self.metadata())
        if title is not None and title != self.title:
            self.title = title
            changed["Metadata"] = GLib.Variant("a{sv}", self.metadata())
        if volume is not None:
            self.volume = float(volume)
            changed["Volume"] = GLib.Variant("d", self.volume)
        if changed:
            self.conn.emit_signal(None, PATH, "org.freedesktop.DBus.Properties",
                                  "PropertiesChanged",
                                  GLib.Variant("(sa{sv}as)",
                                               ("org.mpris.MediaPlayer2.Player", changed, [])))

    def unregister(self):
        for oid in (self.root_id, self.player_id):
            if oid:
                try:
                    self.conn.unregister_object(oid)
                except Exception:  # noqa: BLE001
                    pass
