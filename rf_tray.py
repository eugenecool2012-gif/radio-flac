"""Индикатор в системном лотке (StatusNotifierItem + DBusMenu)."""
import sys

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

ITEM_XML = """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconPixmap" type="a(iiay)" access="read"/>
    <property name="OverlayIconName" type="s" access="read"/>
    <property name="AttentionIconName" type="s" access="read"/>
    <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <method name="Activate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="ContextMenu">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <signal name="NewIcon"/>
    <signal name="NewStatus">
      <arg name="status" type="s"/>
    </signal>
    <signal name="NewToolTip"/>
  </interface>
</node>
"""

MENU_XML = """
<node>
  <interface name="com.canonical.dbusmenu">
    <property name="Version" type="u" access="read"/>
    <property name="TextDirection" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconThemePath" type="as" access="read"/>
    <method name="GetLayout">
      <arg name="parentId" type="i" direction="in"/>
      <arg name="recursionDepth" type="i" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="revision" type="u" direction="out"/>
      <arg name="layout" type="(ia{sv}av)" direction="out"/>
    </method>
    <method name="GetGroupProperties">
      <arg name="ids" type="ai" direction="in"/>
      <arg name="propertyNames" type="as" direction="in"/>
      <arg name="properties" type="a(ia{sv})" direction="out"/>
    </method>
    <method name="GetProperty">
      <arg name="id" type="i" direction="in"/>
      <arg name="name" type="s" direction="in"/>
      <arg name="value" type="v" direction="out"/>
    </method>
    <method name="Event">
      <arg name="id" type="i" direction="in"/>
      <arg name="eventId" type="s" direction="in"/>
      <arg name="data" type="v" direction="in"/>
      <arg name="timestamp" type="u" direction="in"/>
    </method>
    <method name="EventGroup">
      <arg name="events" type="a(isvu)" direction="in"/>
      <arg name="idErrors" type="ai" direction="out"/>
    </method>
    <method name="AboutToShow">
      <arg name="id" type="i" direction="in"/>
      <arg name="needUpdate" type="b" direction="out"/>
    </method>
    <method name="AboutToShowGroup">
      <arg name="ids" type="ai" direction="in"/>
      <arg name="updatesNeeded" type="ai" direction="out"/>
      <arg name="idErrors" type="ai" direction="out"/>
    </method>
    <signal name="ItemsPropertiesUpdated">
      <arg name="updatedProps" type="a(ia{sv})"/>
      <arg name="removedProps" type="a(ias)"/>
    </signal>
    <signal name="LayoutUpdated">
      <arg name="revision" type="u"/>
      <arg name="parent" type="i"/>
    </signal>
    <signal name="ItemActivationRequested">
      <arg name="id" type="i"/>
      <arg name="timestamp" type="u"/>
    </signal>
  </interface>
</node>
"""

BUS_NAME = "org.kde.StatusNotifierItem-radioflac-1"
MENU_PATH = "/MenuBar"
ITEM_PATH = "/StatusNotifierItem"


class TrayIcon:
    """Иконка в лотке с меню. Все действия — через переданные колбэки.

    callbacks: show, play_pause, record, quit  (вызываются в главном потоке)
    """

    def __init__(self, callbacks):
        self.callbacks = callbacks
        self.state = "stopped"     # stopped | playing | recording
        self.app = Gtk.Application.get_default()
        self.revision = 1
        self._item_id = 0
        self._menu_id = 0
        self.conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self._register_item()
        self._register_menu()
        self._own_name()

    # ---------- регистрация ----------
    def _register_item(self):
        node = Gio.DBusNodeInfo.new_for_xml(ITEM_XML)
        self._item_id = self.conn.register_object(
            ITEM_PATH, node.interfaces[0], self._on_item_call, self._on_get_property, None)

    def _register_menu(self):
        node = Gio.DBusNodeInfo.new_for_xml(MENU_XML)
        self._menu_id = self.conn.register_object(
            MENU_PATH, node.interfaces[0], self._on_menu_call, self._on_menu_get_property, None)

    def _own_name(self):
        """Занимает своё имя в шине и регистрируется у watcher'а лотка."""
        Gio.bus_own_name_on_connection(self.conn, BUS_NAME,
                                       Gio.BusNameOwnerFlags.REPLACE, None, None)
        try:
            self.conn.call_sync(
                "org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher",
                "org.kde.StatusNotifierWatcher", "RegisterStatusNotifierItem",
                GLib.Variant("(s)", (BUS_NAME,)), None,
                Gio.DBusCallFlags.NONE, 2000, None)
        except GLib.Error as e:
            print("лоток: watcher не принял иконку:", e.message, file=sys.stderr)

    # ---------- свойства Item ----------
    def icon_name(self):
        return {
            "recording": "media-record-symbolic",
            "playing": "audio-speakers-symbolic",
        }.get(self.state, "radio-symbolic")

    def tooltip(self):
        return {
            "recording": "Radio FLAC — идёт запись",
            "playing": "Radio FLAC — играет",
        }.get(self.state, "Radio FLAC")

    def _on_get_property(self, _conn, _sender, _path, _iface, name):
        if name == "Category":
            return GLib.Variant("s", "ApplicationStatus")
        if name == "Id":
            return GLib.Variant("s", "radio-flac")
        if name == "Title":
            return GLib.Variant("s", "Radio FLAC")
        if name == "Status":
            return GLib.Variant("s", "Active" if self.state != "stopped" else "Passive")
        if name in ("IconName", "OverlayIconName"):
            return GLib.Variant("s", self.icon_name() if name == "IconName"
                                else "media-record-symbolic")
        if name == "AttentionIconName":
            return GLib.Variant("s", "media-record-symbolic")
        if name == "IconPixmap":
            return GLib.Variant("a(iiay)", [])
        if name == "ToolTip":
            return GLib.Variant("(sa(iiay)ss)", (self.icon_name(), [], "Radio FLAC",
                                                 self.tooltip()))
        if name == "Menu":
            return GLib.Variant("o", MENU_PATH)
        raise KeyError(name)

    def _on_item_call(self, _conn, _sender, _path, _iface, method, params, invocation):
        if method == "Activate":
            GLib.idle_add(self.callbacks["show"])
        elif method == "SecondaryActivate":
            GLib.idle_add(self.callbacks["play_pause"])
        invocation.return_value(None)

    # ---------- меню ----------
    def menu_items(self):
        """Пункты меню: без разделителей — их не все хосты лотка переваривают."""
        playing = self.state == "playing"
        recording = self.state == "recording"
        return [
            (1, {"label": GLib.Variant("s", "Показать окно"), "enabled": GLib.Variant("b", True)}),
            (2, {"label": GLib.Variant("s", "Пауза" if playing else "Слушать"),
                 "enabled": GLib.Variant("b", True)}),
            (3, {"label": GLib.Variant("s", "Остановить запись" if recording else "Записать в FLAC"),
                 "enabled": GLib.Variant("b", True)}),
            (5, {"label": GLib.Variant("s", "Выход"), "enabled": GLib.Variant("b", True)}),
        ]

    def _on_menu_get_property(self, _conn, _sender, _path, _iface, name):
        if name == "Version":
            return GLib.Variant("u", 3)
        if name == "TextDirection":
            return GLib.Variant("s", "ltr")
        if name == "Status":
            return GLib.Variant("s", "normal")
        if name == "IconThemePath":
            return GLib.Variant("as", [])
        raise KeyError(name)

    def _on_menu_call(self, _conn, _sender, _path, _iface, method, params, invocation):
        def reply(value):
            invocation.return_value(value)
            return None

        if method == "GetLayout":
            parent_id, _depth, _props = params.unpack()
            children = []
            if parent_id == 0:
                for item_id, props in self.menu_items():
                    children.append(GLib.Variant("(ia{sv}av)", (item_id, props, [])))
            root = GLib.Variant.new_tuple(
                GLib.Variant("i", 0),
                GLib.Variant("a{sv}", {"children-display": GLib.Variant("s", "submenu")}),
                GLib.Variant("av", children))
            return reply(GLib.Variant.new_tuple(GLib.Variant("u", self.revision), root))
        if method == "GetGroupProperties":
            ids, _names = params.unpack()
            wanted = set(ids)
            out = []
            for item_id, props in self.menu_items():
                if not wanted or item_id in wanted:
                    out.append((item_id, props))
            return reply(GLib.Variant("(a(ia{sv}))", (out,)))
        if method == "GetProperty":
            item_id, prop = params.unpack()
            for ivid, props in self.menu_items():
                if ivid == item_id and prop in props:
                    return reply(GLib.Variant("v", props[prop]))
            return reply(GLib.Variant("v", GLib.Variant("s", "")))
        if method == "Event":
            item_id, event_id, _data, _ts = params.unpack()
            if event_id == "clicked":
                GLib.idle_add(self._activate_item, item_id)
            return reply(None)
        if method == "EventGroup":
            for item_id, event_id, _data, _ts in params.unpack()[0]:
                if event_id == "clicked":
                    GLib.idle_add(self._activate_item, item_id)
            return reply(GLib.Variant("(ai)", ([],)))
        if method == "AboutToShow":
            return reply(GLib.Variant("(b)", (True,)))
        if method == "AboutToShowGroup":
            return reply(GLib.Variant("(aiai)", ([], [])))
        return reply(None)

    def _activate_item(self, item_id):
        if item_id == 1:
            self.callbacks["show"]()
        elif item_id == 2:
            self.callbacks["play_pause"]()
        elif item_id == 3:
            self.callbacks["record"]()
        elif item_id == 5:
            self.callbacks["quit"]()
        return False

    # ---------- состояние ----------
    def set_state(self, state):
        if state == self.state:
            return
        self.state = state
        self.revision += 1
        for path, iface, changes in (
            (ITEM_PATH, "org.kde.StatusNotifierItem",
             {"IconName": GLib.Variant("s", self.icon_name()),
              "Status": GLib.Variant("s", "Active" if state != "stopped" else "Passive"),
              "ToolTip": GLib.Variant("(sa(iiay)ss)",
                                      (self.icon_name(), [], "Radio FLAC", self.tooltip()))}),
            (MENU_PATH, "com.canonical.dbusmenu",
             {"Status": GLib.Variant("s", "normal")}),
        ):
            for prop, value in changes.items():
                GLib.idle_add(self._emit_properties_changed, path, iface, prop, value)
        GLib.idle_add(self._emit_signal, ITEM_PATH, "org.kde.StatusNotifierItem",
                      "NewIcon", None)
        GLib.idle_add(self._emit_signal, ITEM_PATH, "org.kde.StatusNotifierItem",
                      "NewStatus", GLib.Variant("(s)", (self.status_value(),)))
        GLib.idle_add(self._emit_signal, MENU_PATH, "com.canonical.dbusmenu",
                      "LayoutUpdated", GLib.Variant("(ui)", (self.revision, 0)))
        return False

    def status_value(self):
        return "Active" if self.state != "stopped" else "Passive"

    def _emit_properties_changed(self, path, iface, prop, value):
        self.conn.emit_signal(None, path, "org.freedesktop.DBus.Properties",
                              "PropertiesChanged",
                              GLib.Variant("(sa{sv}as)", (iface, {prop: value}, [])))
        return False

    def _emit_signal(self, path, iface, name, variant):
        self.conn.emit_signal(None, path, iface, name, variant)
        return False

    def unregister(self):
        for oid in (self._item_id, self._menu_id):
            if oid:
                try:
                    self.conn.unregister_object(oid)
                except Exception:  # noqa: BLE001
                    pass


def available():
    """Есть ли в сессии хост для иконок лотка."""
    try:
        conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        result = conn.call_sync(
            "org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher",
            "org.freedesktop.DBus.Properties", "Get",
            GLib.Variant("(ss)", ("org.kde.StatusNotifierWatcher", "IsStatusNotifierHostRegistered")),
            None, Gio.DBusCallFlags.NONE, 2000, None)
        return bool(result.unpack()[0])
    except GLib.Error:
        return False


def register(watcher, bus_name=BUS_NAME, path=ITEM_PATH):
    """Регистрация иконки у watcher'а (используется внутри TrayIcon)."""
    conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    conn.call_sync(watcher or "org.kde.StatusNotifierWatcher",
                   "/StatusNotifierWatcher", "org.kde.StatusNotifierWatcher",
                   "RegisterStatusNotifierItem", GLib.Variant("(s)", (bus_name,)),
                   None, Gio.DBusCallFlags.NONE, 2000, None)
    return True
