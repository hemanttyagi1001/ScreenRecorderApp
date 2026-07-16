import cv2
import numpy as np
import pyautogui
import time
import os
import sys
import threading
import wave
import subprocess
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import ctypes

try:
    from pystray import Icon, MenuItem, Menu
    from PIL import Image
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

try:
    import sounddevice as sd
    HAS_AUDIO = True
except Exception:
    HAS_AUDIO = False

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = None

__version__ = "1.0.0"

MUTEX_NAME = "ScreenRecorderApp_SingleInstance_Mutex"

AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 1
AUDIO_SAMPLE_WIDTH = 2  # int16


def _acquire_single_instance():
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:
        hwnd = ctypes.windll.user32.FindWindowW(None, "Screen Recorder")
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        return None
    return mutex


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def get_videos_folder():
    videos_path = os.path.join(os.path.expanduser("~"), "Videos")
    os.makedirs(videos_path, exist_ok=True)
    return videos_path


def _has_default_input_device():
    if not HAS_AUDIO:
        return False
    try:
        sd.check_input_settings(
            samplerate=AUDIO_SAMPLE_RATE, channels=AUDIO_CHANNELS, dtype="int16"
        )
        return True
    except Exception:
        return False


class ScreenRecorderApp:
    def __init__(self):
        self.recording = False
        self.frame_count = 0
        self.start_time = 0
        self.final_output_path = ""
        self.video_temp_path = ""
        self.audio_temp_path = ""
        self.out = None
        self.record_thread = None
        self.audio_thread = None
        self.audio_stream = None
        self.audio_wave = None
        self.audio_lock = threading.Lock()
        self.audio_available = _has_default_input_device() and FFMPEG_EXE is not None
        self.tray_icon = None

        self.root = tk.Tk()
        self.root.title(f"Screen Recorder v{__version__}")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.audio_var = tk.BooleanVar(value=self.audio_available)

        icon_path = resource_path("screen_recorder.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        win_w, win_h = 420, 380
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.root.minsize(win_w, win_h)
        self.root.maxsize(win_w, win_h)

        self._build_ui()

        self.root.bind("<Return>",
                       lambda _: self._start_recording() if not self.recording else None)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # Title
        tk.Label(
            self.root, text="Screen Recorder",
            font=("Segoe UI", 22, "bold"), fg="#cdd6f4", bg="#1e1e2e"
        ).pack(pady=(30, 5))

        # Subtitle
        tk.Label(
            self.root, text="Record your entire screen",
            font=("Segoe UI", 11), fg="#a6adc8", bg="#1e1e2e"
        ).pack(pady=(0, 0))

        # Version
        tk.Label(
            self.root, text=f"v{__version__}",
            font=("Segoe UI", 9), fg="#6c7086", bg="#1e1e2e"
        ).pack(pady=(0, 10))

        # Info frame
        info_frame = tk.Frame(self.root, bg="#313244", highlightbackground="#45475a",
                              highlightthickness=1)
        info_frame.pack(padx=30, pady=10, fill="x")

        info_items = [
            ("Resolution", "1920 x 1080"),
            ("FPS", "20"),
            ("Format", "MP4"),
            ("Save to", "~/Videos"),
        ]
        for label, value in info_items:
            row = tk.Frame(info_frame, bg="#313244")
            row.pack(fill="x", padx=15, pady=4)
            tk.Label(row, text=label, font=("Segoe UI", 10),
                     fg="#a6adc8", bg="#313244", anchor="w").pack(side="left")
            tk.Label(row, text=value, font=("Segoe UI", 10, "bold"),
                     fg="#cdd6f4", bg="#313244", anchor="e").pack(side="right")

        # Microphone toggle row
        mic_row = tk.Frame(info_frame, bg="#313244")
        mic_row.pack(fill="x", padx=15, pady=4)
        tk.Label(mic_row, text="Microphone", font=("Segoe UI", 10),
                 fg="#a6adc8", bg="#313244", anchor="w").pack(side="left")
        self.audio_check = tk.Checkbutton(
            mic_row,
            text="Record audio",
            variable=self.audio_var,
            onvalue=True, offvalue=False,
            font=("Segoe UI", 10, "bold"),
            fg="#cdd6f4", bg="#313244",
            activebackground="#313244", activeforeground="#cdd6f4",
            selectcolor="#1e1e2e",
            disabledforeground="#6c7086",
            cursor="hand2", borderwidth=0, highlightthickness=0,
        )
        if not self.audio_available:
            self.audio_var.set(False)
            self.audio_check.config(state="disabled", text="No mic detected")
        self.audio_check.pack(side="right")

        # Status label (clickable when ready)
        self.status_label = tk.Label(
            self.root, text="Ready to record",
            font=("Segoe UI", 10, "underline"), fg="#a6e3a1", bg="#1e1e2e",
            cursor="hand2"
        )
        self.status_label.pack(pady=(15, 5))
        self.status_label.bind("<Button-1>",
                               lambda _: self._start_recording() if not self.recording else None)

        # Buttons frame
        btn_frame = tk.Frame(self.root, bg="#1e1e2e")
        btn_frame.pack(pady=10)

        self.start_btn = tk.Button(
            btn_frame, text="  Start Recording  ",
            font=("Segoe UI", 12, "bold"), fg="white", bg="#f38ba8",
            activebackground="#eba0ac", activeforeground="white",
            relief="flat", cursor="hand2", command=self._start_recording
        )
        self.start_btn.pack(side="left", padx=8)

        self.stop_btn = tk.Button(
            btn_frame, text="  Stop Recording  ",
            font=("Segoe UI", 12, "bold"), fg="white", bg="#45475a",
            activebackground="#585b70", activeforeground="white",
            relief="flat", cursor="hand2", state="disabled",
            command=self._stop_recording
        )
        self.stop_btn.pack(side="left", padx=8)

    def _start_recording(self):
        screen_size = pyautogui.size()
        width, height = screen_size

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base = os.path.join(get_videos_folder(), f"recording_{timestamp}")
        self.final_output_path = f"{base}.mp4"

        record_audio = self.audio_available and bool(self.audio_var.get())
        if record_audio:
            self.video_temp_path = f"{base}.video.mp4"
            self.audio_temp_path = f"{base}.audio.wav"
        else:
            self.video_temp_path = self.final_output_path
            self.audio_temp_path = ""

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.out = cv2.VideoWriter(self.video_temp_path, fourcc, 20.0, (width, height))

        self.recording = True
        self.frame_count = 0
        self.start_time = time.time()

        if record_audio:
            self._start_audio_capture()

        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal", bg="#f38ba8")
        self.audio_check.config(state="disabled")
        self.status_label.config(text="Recording...", fg="#f38ba8")

        self.record_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.record_thread.start()

        self._update_timer()
        self.root.after(500, self._minimize_to_tray)

    def _start_audio_capture(self):
        try:
            self.audio_wave = wave.open(self.audio_temp_path, "wb")
            self.audio_wave.setnchannels(AUDIO_CHANNELS)
            self.audio_wave.setsampwidth(AUDIO_SAMPLE_WIDTH)
            self.audio_wave.setframerate(AUDIO_SAMPLE_RATE)

            def callback(indata, frames, time_info, status):
                with self.audio_lock:
                    if self.audio_wave is not None:
                        self.audio_wave.writeframes(bytes(indata))

            self.audio_stream = sd.RawInputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype="int16",
                callback=callback,
            )
            self.audio_stream.start()
        except Exception:
            with self.audio_lock:
                if self.audio_wave:
                    try:
                        self.audio_wave.close()
                    except Exception:
                        pass
                    self.audio_wave = None
            self.audio_stream = None
            self.audio_temp_path = ""

    def _stop_audio_capture(self):
        if self.audio_stream is not None:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
            except Exception:
                pass
            self.audio_stream = None
        with self.audio_lock:
            if self.audio_wave is not None:
                try:
                    self.audio_wave.close()
                except Exception:
                    pass
                self.audio_wave = None

    def _mux_audio_video(self):
        if not self.audio_temp_path or not os.path.exists(self.audio_temp_path):
            return False
        if not os.path.exists(self.video_temp_path):
            return False

        cmd = [
            FFMPEG_EXE, "-y",
            "-i", self.video_temp_path,
            "-i", self.audio_temp_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            self.final_output_path,
        ]
        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = 0x08000000  # CREATE_NO_WINDOW
            result = subprocess.run(
                cmd, capture_output=True, creationflags=creationflags
            )
            if result.returncode != 0:
                return False
        except Exception:
            return False

        for path in (self.video_temp_path, self.audio_temp_path):
            try:
                if path and os.path.exists(path) and path != self.final_output_path:
                    os.remove(path)
            except Exception:
                pass
        return True

    def _capture_loop(self):
        while self.recording:
            try:
                screenshot = pyautogui.screenshot()
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                self.out.write(frame)
                self.frame_count += 1
            except Exception:
                break

    def _update_timer(self):
        if self.recording:
            elapsed = time.time() - self.start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            self.status_label.config(text=f"Recording...  {mins:02d}:{secs:02d}")
            self.root.after(1000, self._update_timer)

    def _minimize_to_tray(self):
        if HAS_TRAY:
            self.root.withdraw()
            self._create_tray_icon()
        else:
            self.root.iconify()

    def _create_tray_icon(self):
        icon_path = resource_path("screen_recorder.ico")
        if os.path.exists(icon_path):
            image = Image.open(icon_path)
        else:
            image = Image.new("RGB", (64, 64), color="red")

        menu = Menu(
            MenuItem("Screen Recorder", None, enabled=False),
            Menu.SEPARATOR,
            MenuItem("Show Window", self._show_window),
            MenuItem("Stop Recording", self._stop_from_tray),
            Menu.SEPARATOR,
            MenuItem("Exit", self._exit_from_tray),
        )

        self.tray_icon = Icon(
            "ScreenRecorder", image, "Screen Recorder - Recording...", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _show_window(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.after(0, self.root.deiconify)

    def _stop_from_tray(self, icon=None, item=None):
        self._show_window()
        self.root.after(100, self._stop_recording)

    def _exit_from_tray(self, icon=None, item=None):
        self._stop_from_tray()
        self.root.after(500, self._on_close)

    def _stop_recording(self):
        if not self.recording:
            return

        self.recording = False

        if self.record_thread and self.record_thread.is_alive():
            self.record_thread.join(timeout=2)

        if self.out:
            self.out.release()
            self.out = None

        self._stop_audio_capture()

        if self.audio_temp_path and self.video_temp_path != self.final_output_path:
            self.status_label.config(text="Saving...", fg="#f9e2af")
            self.root.update_idletasks()
            self._mux_audio_video()

        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled", bg="#45475a")
        if self.audio_available:
            self.audio_check.config(state="normal")
        self.status_label.config(text="Ready to record", fg="#a6e3a1")

    def _on_close(self):
        if self.recording:
            answer = messagebox.askyesno(
                "Recording in Progress",
                "Recording is still in progress.\nDo you want to stop and exit?"
            )
            if not answer:
                return
            self._stop_recording_silent()

        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()

    def _stop_recording_silent(self):
        self.recording = False
        if self.record_thread and self.record_thread.is_alive():
            self.record_thread.join(timeout=2)
        if self.out:
            self.out.release()
            self.out = None
        self._stop_audio_capture()
        if self.audio_temp_path and self.video_temp_path != self.final_output_path:
            self._mux_audio_video()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    mutex = _acquire_single_instance()
    if mutex is None:
        sys.exit(0)
    app = ScreenRecorderApp()
    app.run()
