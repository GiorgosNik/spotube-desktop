import os
import threading
from unittest.mock import patch

from PIL import Image
from spotube.downloader_utils import FFmpegNotFoundError

from src import app_support
from tests.conftest import FakeThread, pump, visible


def start_and_wait(ui, link, valid=True):
    ui.downloader.validate_playlist_url.return_value = valid
    ui.playlist_link_entry.insert(0, link)
    ui.start()
    assert pump(ui, lambda: ui.start_button.cget("state") == "normal")


def write_cover(folder, color):
    Image.new("RGB", (300, 300), color).save(os.path.join(folder, "cover_photo.jpg"))


class TestStartup:
    def test_only_available_keys_are_passed(self, ui):
        kwargs = ui.manager_class.call_args.kwargs
        assert set(kwargs) == {"directory", "genius_api_key"}
        assert kwargs["genius_api_key"] == "token"
        assert kwargs["directory"] == app_support.default_download_dir()

    def test_starts_idle(self, ui):
        assert all(visible(w) for w in ui.idle_widgets)
        assert not any(visible(w) for w in ui.download_widgets)
        assert ui.normalize_audio_checkbox.get() == 1

    def test_missing_ffmpeg_shows_install_help(self, make_ui):
        app = make_ui(ffmpeg_found=False, keys={})

        assert pump(app, lambda: app.show_message_mock.called)
        assert "winget install ffmpeg" in app.show_message_mock.call_args.args[1]
        assert app.manager_class.call_args.kwargs == {"directory": app_support.default_download_dir()}


class TestStartDownload:
    def test_invalid_link_shows_error(self, ui):
        start_and_wait(ui, "https://example.com", valid=False)

        ui.downloader.start_downloader.assert_not_called()
        assert ui.show_message_mock.call_args.args[0] == "Invalid Playlist URL"
        assert visible(ui.start_button)

    def test_valid_link_starts_download(self, ui):
        start_and_wait(ui, "  https://open.spotify.com/playlist/abc  ")

        ui.downloader.validate_playlist_url.assert_called_once_with("https://open.spotify.com/playlist/abc")
        ui.downloader.start_downloader.assert_called_once_with("https://open.spotify.com/playlist/abc")
        assert ui.running is True
        assert visible(ui.stop_button) and not visible(ui.start_button)

    def test_link_check_runs_off_the_ui_thread(self, ui):
        threads = []
        ui.downloader.validate_playlist_url.side_effect = lambda link: threads.append(threading.current_thread()) or True

        start_and_wait(ui, "https://open.spotify.com/playlist/abc")

        assert threads and threads[0] is not threading.main_thread()

    def test_missing_ffmpeg_at_start(self, ui):
        ui.downloader.start_downloader.side_effect = FFmpegNotFoundError("missing")

        start_and_wait(ui, "https://open.spotify.com/playlist/abc")

        assert ui.show_message_mock.call_args.args[0] == "Missing ffmpeg"
        assert ui.running is False
        assert visible(ui.start_button)


class TestProgress:
    def test_not_finished_while_thread_runs_even_with_zero_totals(self, ui):
        ui.downloader.thread = FakeThread(alive=True)
        ui.downloader.working = True

        assert ui.update_progress() is True
        ui.show_message_mock.assert_not_called()

    def test_download_progress_updates_labels(self, ui):
        ui.downloader.thread = FakeThread(alive=True)
        ui.downloader.working = True
        ui.downloader.progress, ui.downloader.total = 1, 4
        ui.downloader.current_song = "A very long song title that goes on and on by Artist"
        ui.downloader.eta = 90

        ui.update_progress()

        assert ui.percentage_label.cget("text") == "25.0%"
        assert ui.song_label.cget("text").endswith("...")
        assert "0:01:30" in ui.eta_label.cget("text") or "0:01:29" in ui.eta_label.cget("text")

    def test_normalization_progress_and_eta(self, ui):
        ui.downloader.thread = FakeThread(alive=True)
        ui.downloader.normalizing = True
        ui.downloader.normalized_songs, ui.downloader.total = 2, 8
        ui.downloader.eta = 30

        ui.update_progress()

        assert ui.song_label.cget("text") == "Normalizing volume for song #3 of 8"
        assert ui.percentage_label.cget("text") == "25.0%"
        assert "0:00:30" in ui.eta_label.cget("text") or "0:00:29" in ui.eta_label.cget("text")

    def test_completion_shows_counts_and_resets(self, ui):
        ui.running = True
        ui.downloader.thread = FakeThread(alive=False)
        ui.downloader.success_counter, ui.downloader.failure_counter = 3, 1

        assert ui.update_progress() is False

        message = ui.show_message_mock.call_args.args[1]
        assert "Downloaded 3 songs" in message and "Failed to download 1 songs" in message
        assert ui.running is False
        assert visible(ui.start_button)

    def test_completion_can_open_directory(self, ui):
        ui.downloader.thread = FakeThread(alive=False)
        ui.downloader.success_counter = 1
        ui.show_message_mock.return_value = "Open Directory"

        with patch.object(ui, "open_output_directory") as open_directory:
            ui.update_progress()
        open_directory.assert_called_once_with()


class TestCover:
    def test_missing_cover_does_not_block(self, ui):
        ui.refresh_cover()

        assert ui.cover_mtime is None

    def test_cover_loaded_once_per_file_version(self, ui):
        write_cover(ui.selected_folder, "red")
        with patch.object(ui, "set_image", wraps=ui.set_image) as set_image:
            ui.refresh_cover()
            ui.refresh_cover()
        assert set_image.call_count == 1

    def test_broken_cover_is_skipped(self, ui):
        with open(os.path.join(ui.selected_folder, "cover_photo.jpg"), "wb") as f:
            f.write(b"not an image")

        ui.refresh_cover()

        assert ui.cover_mtime is None

    def test_cover_updates_reuse_one_widget(self, ui):
        before = len(ui.root.winfo_children())
        for color in ("red", "green", "blue"):
            write_cover(ui.selected_folder, color)
            ui.cover_mtime = None
            ui.refresh_cover()
        assert len(ui.root.winfo_children()) == before


class TestControls:
    def test_stop_cancels_in_background_and_resets(self, ui):
        ui.running = True
        ui.set_mode("download")

        ui.stop()
        ui.stop_thread.join(timeout=5)

        ui.downloader.cancel_downloader.assert_called_once_with()
        assert ui.running is False
        assert visible(ui.start_button)

    def test_folder_cancel_keeps_previous_folder(self, ui):
        previous = ui.selected_folder
        with patch("src.ui_interface.filedialog.askdirectory", return_value=""):
            ui.folder()
        assert ui.selected_folder == previous
        ui.downloader.set_directory.assert_not_called()

    def test_folder_selection(self, ui, tmp_path):
        with patch("src.ui_interface.filedialog.askdirectory", return_value=str(tmp_path / "Music")):
            ui.folder()
        ui.downloader.set_directory.assert_called_once_with(str(tmp_path / "Music"))

    def test_normalize_checkbox_updates_downloader(self, ui):
        ui.normalize_audio_checkbox.deselect()
        ui.toggle_normalization()
        assert ui.downloader.normalize_sound is False

    def test_open_directory_per_platform(self, ui):
        with patch("src.ui_interface.subprocess.Popen") as popen:
            ui.open_output_directory(platform="linux")
            ui.open_output_directory(platform="darwin")
        assert [c.args[0][0] for c in popen.call_args_list] == ["xdg-open", "open"]

    def test_close_waits_for_cancel(self, ui):
        with patch.object(ui.root, "destroy") as destroy:
            ui.on_close()
        destroy.assert_called_once_with()

        assert ui.closing is True
        ui.downloader.cancel_downloader.assert_called_once_with()
        assert not ui.stop_thread.is_alive()


class TestSignIn:
    def test_success(self, ui):
        ui.sign_in()
        assert pump(ui, lambda: ui.show_message_mock.called)

        ui.downloader.login_exportify.assert_called_once_with()
        assert ui.show_message_mock.call_args.args[0] == "Signed in"
        assert ui.sign_in_button.cget("state") == "normal"

    def test_failure_shows_reason(self, ui):
        ui.downloader.login_exportify.side_effect = RuntimeError("run: pip install spotube[exportify]")

        ui.sign_in()
        assert pump(ui, lambda: ui.show_message_mock.called)

        assert ui.show_message_mock.call_args.args[0] == "Sign-in failed"
        assert "spotube[exportify]" in ui.show_message_mock.call_args.args[1]


def test_completion_message_when_nothing_downloaded():
    downloader = type("D", (), {"success_counter": 0, "failure_counter": 0})()
    assert app_support.completion_message(downloader) == app_support.NOTHING_DOWNLOADED_MESSAGE
