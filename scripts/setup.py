"""
LIME setup script.
Run once after cloning: python scripts/setup.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def run(cmd: list[str], **kwargs):
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"[ERROR] Command failed: {' '.join(cmd)}")
        sys.exit(result.returncode)


def main():
    print("=== LIME Setup ===\n")

    # 1. Create .env from example
    env_path = ROOT / ".env"
    env_example = ROOT / ".env.example"
    if not env_path.exists():
        import shutil
        shutil.copy(env_example, env_path)
        print(f"[OK] Created .env — fill in your API keys\n")
    else:
        print(f"[--] .env already exists\n")

    # 2. Install dependencies
    print("[1/3] Installing Python dependencies...")
    run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])

    # 3. Initialize database
    print("\n[2/3] Initializing database...")
    sys.path.insert(0, str(ROOT))
    from backend.storage.database import init_db
    init_db()
    print("  Database initialized.")

    # 4. Check ffmpeg
    print("\n[3/3] Checking ffmpeg...")
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    if result.returncode == 0:
        print("  ffmpeg found.")
    else:
        print(
            "  [WARNING] ffmpeg not found on PATH.\n"
            "  Audio compression will be disabled until ffmpeg is installed.\n"
            "  Download: https://ffmpeg.org/download.html"
        )

    print("\n=== Setup complete ===")
    print("Next steps:")
    print("  1. Edit .env — add your HUGGINGFACE_TOKEN (required for diarization)")
    print("  2. Optionally add DEEPGRAM_API_KEY or ASSEMBLYAI_API_KEY for cloud fallback")
    print("  3. Run: python cli.py devices  — to list audio devices")
    print("  4. Run: python cli.py start    — to record your first meeting")


if __name__ == "__main__":
    main()
