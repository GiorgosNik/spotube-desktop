import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from src import app_support, utils
from tests.conftest import FakeThread


@pytest.fixture
def clean_env(monkeypatch):
    for names in app_support.KEY_ENV_NAMES.values():
        for name in names:
            monkeypatch.delenv(name, raising=False)


class TestApiKeys:
    def test_missing_file_gives_no_keys(self, tmp_path, clean_env):
        assert app_support.load_api_keys(tmp_path / ".vars") == {
            "spotify_client_id": None, "spotify_client_secret": None, "genius_api_key": None,
        }

    def test_reads_app_names_and_ignores_blanks(self, tmp_path, clean_env):
        settings = tmp_path / ".vars"
        settings.write_text("SPOTIFY_ID = id\nSPOTIFY_SECRET =\nGENIUS_TOKEN = token\n", encoding="utf-8")

        keys = app_support.load_api_keys(settings)

        assert keys == {"spotify_client_id": "id", "spotify_client_secret": None, "genius_api_key": "token"}

    def test_reads_standard_environment_names(self, tmp_path, clean_env, monkeypatch):
        monkeypatch.setenv("GENIUS_ACCESS_TOKEN", "env-token")
        assert app_support.load_api_keys(tmp_path / ".vars")["genius_api_key"] == "env-token"

    def test_example_file_has_no_values(self):
        example = Path(__file__).resolve().parent.parent / ".vars.example"
        for line in example.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                assert line.split("=", 1)[1].strip() == ""


class TestPaths:
    def test_source_paths(self):
        assert app_support.resource_path("images", "cover_art.jpg").endswith(os.path.join("images", "cover_art.jpg"))
        assert os.path.isfile(app_support.resource_path("images", "cover_art.jpg"))
        assert app_support.default_download_dir() == "./Songs"

    def test_frozen_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

        assert app_support.resource_path("images") == str(tmp_path / "images")
        assert app_support.default_download_dir() == str(Path.home() / "Music" / "Spotube")
        assert app_support.settings_path() == Path(sys.executable).parent / ".vars"


class TestFfmpegSetup:
    def test_already_on_path(self):
        with patch("src.app_support.downloader_utils.ffmpeg_installed", return_value=True):
            assert app_support.setup_ffmpeg() is True

    def test_uses_bundled_folder(self, tmp_path, monkeypatch):
        bundled = tmp_path / "ffmpeg"
        bundled.mkdir()
        for tool in ("ffmpeg", "ffprobe"):
            (bundled / app_support.executable_name(tool)).write_bytes(b"")
        monkeypatch.setattr(app_support, "ffmpeg_search_dirs", lambda: [bundled])
        monkeypatch.setenv("PATH", "original")

        with patch("src.app_support.downloader_utils.ffmpeg_installed", side_effect=[False, True]):
            assert app_support.setup_ffmpeg() is True
        assert os.environ["PATH"].startswith(str(bundled) + os.pathsep)

    def test_needs_both_tools(self, tmp_path, monkeypatch):
        (tmp_path / app_support.executable_name("ffmpeg")).write_bytes(b"")
        monkeypatch.setattr(app_support, "ffmpeg_search_dirs", lambda: [tmp_path])

        with patch("src.app_support.downloader_utils.ffmpeg_installed", return_value=False):
            assert app_support.setup_ffmpeg() is False


class TestProgressHelpers:
    @pytest.mark.parametrize(("thread", "finished"), [(None, False), (FakeThread(True), False), (FakeThread(False), True)])
    def test_is_download_finished(self, thread, finished):
        assert app_support.is_download_finished(type("D", (), {"thread": thread})()) is finished

    def test_completion_counts(self):
        downloader = type("D", (), {"success_counter": 5, "failure_counter": 0})()
        assert "Downloaded 5 songs" in app_support.completion_message(downloader)

    @pytest.mark.parametrize(("done", "total", "fraction"), [(0, 0, 0.0), (1, 4, 0.25), (5, 4, 1.0), (0, None, 0.0)])
    def test_progress_fraction(self, done, total, fraction):
        assert app_support.progress_fraction(done, total) == fraction

    def test_normalization_text_never_exceeds_total(self):
        downloader = type("D", (), {"normalized_songs": 4, "total": 4})()
        assert app_support.normalization_text(downloader) == "Normalizing volume for song #4 of 4"


@pytest.mark.parametrize(("seconds", "clock"), [(0, "0:00:00"), (90, "0:01:30"), (-5, "0:00:00"), (3725.9, "1:02:05")])
def test_convert_sec_to_clock(seconds, clock):
    assert utils.convert_sec_to_clock(seconds) == clock


def test_cli_script_is_gone():
    assert not (Path(__file__).resolve().parent.parent / "spotube_cli.py").exists()


def test_self_test_runs(tmp_path):
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run([sys.executable, str(root / "spotube_ui.py"), "--self-test"], capture_output=True, text=True, cwd=root)
    assert "ok: cover image bundled" in result.stdout
    assert "exportify available" in result.stdout
