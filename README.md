# Screen Recorder

A lightweight Windows screen recorder with a clean dark UI, optional microphone audio, and system tray support. Built in Python with Tkinter.

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)

## Features

- **Full-screen recording** at 1920×1080, 20 FPS, saved as MP4.
- **Optional microphone audio** — automatically detected; toggle on/off in the UI. Audio is muxed into the video with FFmpeg.
- **Minimize to system tray** while recording, with Show / Stop / Exit controls.
- **Single-instance** — launching a second time re-focuses the existing window.
- **Automatic saving** to your `~/Videos` folder with a timestamped filename (`recording_YYYY-MM-DD_HH-MM-SS.mp4`).
- **Standalone executable** — can be packaged into a single `.exe` with no Python required to run.

## Requirements

- Windows
- Python 3.8+ (only needed to run from source or build)

## Installation (from source)

```bash
git clone https://github.com/hemanttyagi1001/ScreenRecorderApp.git
cd ScreenRecorderApp
pip install -r requirements.txt
```

## Usage

Run the app:

```bash
python screen_recorder.py
```

1. (Optional) Toggle **Record audio** to capture microphone input.
2. Click **Start Recording** (or press `Enter`). The window minimizes to the system tray.
3. Click **Stop Recording** — from the window or the tray menu.
4. Your recording is saved to `~/Videos`.

## Building a standalone executable

To produce a single-file `ScreenRecorder.exe`:

```bash
python build_installer.py
```

The build uses PyInstaller (`--onefile --windowed`) and bundles FFmpeg and the audio backend. The result is written to `dist/ScreenRecorder.exe`.

To regenerate the app icon:

```bash
python create_icon.py
```

## Dependencies

| Package | Purpose |
| --- | --- |
| `opencv-python` | Video encoding / frame writing |
| `numpy` | Frame array handling |
| `pyautogui` | Screen capture |
| `pystray` + `Pillow` | System tray icon |
| `sounddevice` | Microphone capture |
| `imageio-ffmpeg` | Bundled FFmpeg for audio/video muxing |
| `pyinstaller` | Packaging into an executable |

## How it works

- Frames are captured in a background thread via `pyautogui.screenshot()` and written with OpenCV's `VideoWriter` (`mp4v`).
- When audio is enabled, microphone input is streamed to a temporary WAV file; on stop, FFmpeg muxes the video and audio into the final MP4.
- The Tkinter UI runs on the main thread; recording and audio each run on their own daemon threads.

## License

No license specified. Add one if you intend to distribute.
