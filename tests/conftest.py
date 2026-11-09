import time
from unittest.mock import MagicMock, patch

import customtkinter as ctk
import pytest


class FakeThread:
    def __init__(self, alive):
        self.alive = alive

    def is_alive(self):
        return self.alive


def make_downloader():
    downloader = MagicMock()
    downloader.thread = None
    downloader.working = False
    downloader.normalizing = False
    downloader.normalize_sound = True
    downloader.progress = 0
    downloader.total = 0
    downloader.normalized_songs = 0
    downloader.success_counter = 0
    downloader.failure_counter = 0
    downloader.current_song = None
    downloader.eta = None
    return downloader


@pytest.fixture(scope="session")
def shared_root():
    root = ctk.CTk()
    yield root
    root.destroy()


@pytest.fixture
def make_ui(shared_root, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    apps = []

    def factory(ffmpeg_found=True, keys=None):
        downloader = make_downloader()
        patches = [
            patch("src.ui_interface.ctk.CTk", return_value=shared_root),
            patch("src.ui_interface.DownloadManager", return_value=downloader),
            patch("src.ui_interface.app_support.setup_ffmpeg", return_value=ffmpeg_found),
            patch("src.ui_interface.app_support.load_api_keys", return_value=keys if keys is not None else {"genius_api_key": "token"}),
            patch("src.ui_interface.ui_interface.show_message", return_value="OK"),
        ]
        started = [p.start() for p in patches]
        from src.ui_interface import ui_interface

        app = ui_interface()
        app.manager_class = started[1]
        app.show_message_mock = started[4]
        app.selected_folder = str(tmp_path)
        apps.append((app, patches))
        return app

    yield factory

    for app, patches in apps:
        app.closing = True
        app.running = False
        for child in shared_root.winfo_children():
            child.destroy()
        shared_root.deiconify()
        for p in patches:
            p.stop()


@pytest.fixture
def ui(make_ui):
    return make_ui()


def pump(app, until, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.root.update()
        if until():
            return True
        time.sleep(0.01)
    return False


def visible(widget):
    return bool(widget.winfo_manager())
