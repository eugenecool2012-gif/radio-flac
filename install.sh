#!/bin/sh
# Установка radio-flac в ~/.local (Linux)
set -e
BIN="${HOME}/.local/bin"
mkdir -p "$BIN"
install -m755 radio-flac radio-flac-gui radio-flac-trim "$BIN/"
install -m644 rf_icons.py rf_cast.py rf_tray.py rf_mpris.py "$BIN/"
echo "установлено в $BIN"
echo
echo "проверка зависимостей:"
for t in ffmpeg ffprobe; do
  command -v "$t" >/dev/null || echo "  НЕТ: $t (apt install ffmpeg)"
done
python3 -c 'import gi; gi.require_version("Gtk","4.0"); gi.require_version("Adw","1"); gi.require_version("Gst","1.0")' \
  2>/dev/null || echo "  НЕТ: GTK4/libadwaita/GStreamer (apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gst-plugins-base-1.0)"
echo "готово — запускайте: radio-flac-gui"
