"""
Build script to create a Windows installer (.exe) for Screen Recorder.
Run: python build_installer.py
"""

import subprocess
import sys
import os

def main():
    print("=" * 50)
    print("  Building Screen Recorder Installer")
    print("=" * 50)

    # Ensure PyInstaller is installed
    print("\n[1/2] Checking PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Build the executable
    print("\n[2/2] Building executable...")
    icon_path = os.path.join(os.path.dirname(__file__), "screen_recorder.ico")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "ScreenRecorder",
        "--icon", icon_path,
        "--add-data", f"{icon_path};.",
        "--collect-all", "imageio_ffmpeg",
        "--collect-all", "sounddevice",
        "screen_recorder.py",
    ]

    subprocess.check_call(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))

    print("\n" + "=" * 50)
    print("  BUILD COMPLETE!")
    print("=" * 50)
    dist_path = os.path.join(os.path.dirname(__file__), "dist", "ScreenRecorder.exe")
    print(f"  Executable: {dist_path}")
    print(f"\n  You can now run or share ScreenRecorder.exe")
    print("=" * 50)


if __name__ == "__main__":
    main()
