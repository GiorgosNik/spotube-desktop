import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from spotube import downloader_utils

APP_NAME = "Spotube"
SETTINGS_FILE = ".vars"
KEY_ENV_NAMES = {
    "spotify_client_id": ("SPOTIFY_ID", "SPOTIPY_CLIENT_ID"),
    "spotify_client_secret": ("SPOTIFY_SECRET", "SPOTIPY_CLIENT_SECRET"),
    "genius_api_key": ("GENIUS_TOKEN", "GENIUS_ACCESS_TOKEN"),
}
FFMPEG_HELP = (
    "Spotube needs ffmpeg to convert songs to MP3.\n\n"
    "Windows: open a terminal and run\n    winget install ffmpeg\n"
    "macOS: brew install ffmpeg\n"
    "Linux: sudo apt install ffmpeg\n\n"
    "Then restart Spotube."
)
NOTHING_DOWNLOADED_MESSAGE = (
    "Nothing was downloaded.\n\n"
    "Check that the playlist is public. Details are in errors.log."
)


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def app_root():
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def resource_path(*parts):
    return str(app_root().joinpath(*parts))


def settings_path():
    base = Path(sys.executable).parent if is_frozen() else app_root()
    return base / SETTINGS_FILE


def default_download_dir():
    if is_frozen():
        return str(Path.home() / "Music" / APP_NAME)
    return "./Songs"


def load_api_keys(path=None):
    load_dotenv(path or settings_path())
    keys = {}
    for argument, names in KEY_ENV_NAMES.items():
        keys[argument] = next((os.environ[name] for name in names if os.environ.get(name)), None)
    return keys


def executable_name(tool):
    return f"{tool}.exe" if os.name == "nt" else tool


def ffmpeg_search_dirs():
    return [app_root() / "ffmpeg", app_root()]


def setup_ffmpeg():
    if downloader_utils.ffmpeg_installed():
        return True
    for directory in ffmpeg_search_dirs():
        if all((directory / executable_name(tool)).is_file() for tool in ("ffmpeg", "ffprobe")):
            os.environ["PATH"] = str(directory) + os.pathsep + os.environ.get("PATH", "")
            return downloader_utils.ffmpeg_installed()
    return False


def is_download_finished(downloader):
    thread = downloader.thread
    return thread is not None and not thread.is_alive()


def completion_message(downloader):
    if not downloader.success_counter and not downloader.failure_counter:
        return NOTHING_DOWNLOADED_MESSAGE
    return (
        "Download Complete!\n\n"
        f"Downloaded {downloader.success_counter} songs\n"
        f"Failed to download {downloader.failure_counter} songs\n"
    )


def progress_fraction(done, total):
    return min(done / total, 1.0) if total else 0.0


def normalization_text(downloader):
    total = downloader.total or 0
    current = min(downloader.normalized_songs + 1, total)
    return f"Normalizing volume for song #{current} of {total}"
