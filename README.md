# radio-flac

Слушает интернет-радио и пишет **каждую песню отдельным FLAC-файлом**.
Есть консольный рекордер и GUI на GTK4 / libadwaita.

```
radio-flac  <url> [-d ПАПКА] [-n ИМЯ] [--min-duration СЕК] [--split-every СЕК]
                   [--full-tracks] [--max-wait СЕК] [--lead СЕК] [--compression 0-12]
radio-flac-gui
```

## Как это работает

В ICY-потоке радиостанция передаёт `StreamTitle` — «исполнитель — название».
На каждой смене названия текущий FLAC закрывается и открывается новый, уже
с тегами `artist` / `title`. Если станция отдаёт нативный FLAC (например,
Radio Paradise), поток копируется **без перекодирования**, бит в бит.

## Установка (Linux)

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
                 gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-good \
                 gstreamer1.0-plugins-bad gstreamer1.0-libav ffmpeg
install -m755 radio-flac radio-flac-gui radio-flac-trim ~/.local/bin/
install -m644 rf_icons.py rf_cast.py rf_tray.py rf_mpris.py ~/.local/bin/
```

Запуск: `radio-flac-gui` (или поставить `.desktop`-файл).

## Установка (Windows)

Скачайте `radio-flac-portable-windows.zip` из Releases, распакуйте в любую
папку и запустите `radio-flac-gui.exe`. Внутри уже лежат GTK4, libadwaita,
GStreamer и `ffmpeg.exe` — ничего доустанавливать не нужно.

## Флаги

| Флаг | Смысл |
|---|---|
| `-d, --directory` | куда писать (по умолчанию `~/Музыка/Radio`) |
| `-n, --name` | имя станции для тега `stream` |
| `--min-duration` | короче этого файл считается огрызком и удаляется (20 с) |
| `--compression` | уровень FLAC 0–12 (по умолчанию 5) |
| `--split-every N` | резать каждые N секунд — для станций без метаданных |
| `--full-tracks` | не писать трек, начавшийся до запуска: ждать следующего |
| `--max-wait N` | сколько ждать смены названия при `--full-tracks` (900 с) |
| `--lead N` | пропустить первые N секунд трека |

### Зачем `--lead`

Некоторые станции объявляют трек **до** того, как он реально начался
(у Best Deep FM замерено опережение ≈ 5 с), из-за чего в начало файла
попадает хвост предыдущей песни. `--lead 5` срезает эти секунды.
Значение лучше подбирать на слух/per-station — в GUI оно запоминается
для каждой станции отдельно.

### Обрезка уже записанного

```bash
radio-flac-trim 5 "2026-11-25_08-56-47 Artist - Track.flac"
```

FLAC нельзя обрезать копированием потока — `-c:a copy` не меняет
длительность, поэтому файл перекодируется через `atrim` (без потерь,
но с пересжатием).

## GUI

- поиск станций через [radio-browser.info](https://www.radio-browser.info/)
- свои станции, избранное («сердечко»), удаление
- выбор папки записей, журнал
- плеер на GStreamer, громкость, эквалайзер
- MPRIS (`org.mpris.MediaPlayer2.radioflac`), трей, Chromecast
- настройки **per-station**: `--lead` запоминается для каждой станции

Конфиг: `~/.config/radio-flac/gui.json`.

## Сборка Windows-версии

`.github/workflows/build-windows.yml` — MSYS2 (MINGW64) + PyInstaller на
`windows-latest`. Запускается по тегу `v*` или вручную (Actions →
Build Windows portable → Run workflow). Результат —
`radio-flac-portable-windows.zip` в артефактах и в Releases.

## Лицензия

MIT