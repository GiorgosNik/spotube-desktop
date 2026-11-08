import os
import subprocess
import sys
import threading
from datetime import datetime
from tkinter import TclError, filedialog

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from PIL import Image, ImageFile
from spotube.download_manager import DownloadManager
from spotube.downloader_utils import FFmpegNotFoundError

import src.utils as utils
from src import app_support

try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Load partially written cover images instead of failing (https://stackoverflow.com/a/23575424)
ImageFile.LOAD_TRUNCATED_IMAGES = True

DEBUGGING = False
MAX_SONG_NAME_LEN = 40
PLAYLIST_URL_ENTRY_PLACEHOLDER = "Playlist URL"
UPDATE_INTERVAL_MS = 500
POLL_INTERVAL_MS = 100
CLOSE_TIMEOUT_SECONDS = 35
COVER_SIZE = (150, 150)
IDLE_GEOMETRY = "320x215"
DOWNLOAD_GEOMETRY = "480x150"
NORMALIZE_GEOMETRY = "320x170"
COVER_FILE = "cover_photo.jpg"

BG_COLOR = "#191414"
TEXT_COLOR = "#FFFFFF"
ACCENT_COLOR = "#116A2D"
HOVER_COLOR = "#0F5A26"
FONT = ("Arial", 10)

DOWNLOAD_TEXT = "Download"
CHECKING_TEXT = "Checking link..."
SIGN_IN_TEXT = "Sign in to Spotify (100+ tracks)"
SIGNING_IN_TEXT = "Waiting for Spotify sign-in..."


class ui_interface:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.geometry(IDLE_GEOMETRY)
        self.root.title(app_support.APP_NAME)
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)

        self.stop_thread = None
        self.running = False
        self.closing = False
        self.progress_percentage = 0
        self.progress_elapsed = ""
        self.progress_text = ""
        self.progress_eta = 0
        self.time_start = datetime.now()
        self.eta_received_time = datetime.now()
        self.cover_mtime = None
        self.selected_folder = app_support.default_download_dir()
        self.default_cover = app_support.resource_path("images", "cover_art.jpg")

        self.build_widgets()
        self.set_image(self.default_cover)

        keys = app_support.load_api_keys()
        self.downloader = DownloadManager(directory=self.selected_folder, **keys)
        self.normalize_audio_checkbox.select()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.set_mode("idle")
        if not app_support.setup_ffmpeg():
            self.root.after(0, self.show_message, "Missing ffmpeg", app_support.FFMPEG_HELP, "warning")

    def build_widgets(self):
        button_style = {"fg_color": ACCENT_COLOR, "text_color": TEXT_COLOR, "hover_color": HOVER_COLOR, "font": FONT}

        self.playlist_link_entry = ctk.CTkEntry(self.root, width=300, placeholder_text=PLAYLIST_URL_ENTRY_PLACEHOLDER, font=FONT)
        self.playlist_link_entry.grid(column=0, row=0, columnspan=2, rowspan=2, padx=10, pady=10)

        self.cover_label = ctk.CTkLabel(self.root, text="", bg_color=BG_COLOR)
        self.cover_label.grid(column=5, row=0, columnspan=3, rowspan=4, padx=10)

        self.progress_bar = ctk.CTkProgressBar(self.root, orientation="horizontal", mode="determinate", width=300, progress_color=HOVER_COLOR)
        self.progress_bar.grid(column=0, row=0, columnspan=2, padx=10, pady=13)

        self.percentage_label = ctk.CTkLabel(self.root, text="0%")
        self.percentage_label.grid(column=0, row=1)

        self.eta_label = ctk.CTkLabel(self.root, text="")
        self.eta_label.grid(column=1, row=1)

        self.song_label = ctk.CTkLabel(self.root, text="", text_color=TEXT_COLOR, font=FONT)
        self.song_label.grid(column=0, row=2, columnspan=2, padx=10, pady=8)

        self.normalize_audio_checkbox = ctk.CTkCheckBox(
            self.root, text="Normalize Sound", hover_color=HOVER_COLOR, fg_color=ACCENT_COLOR, command=self.toggle_normalization
        )
        self.normalize_audio_checkbox.grid(column=0, row=2, padx=10, pady=10, sticky="e")

        self.folder_button = ctk.CTkButton(self.root, text="Select Folder", command=self.folder, **button_style)
        self.folder_button.grid(column=1, row=2, padx=10, pady=10, sticky="w")

        self.start_button = ctk.CTkButton(self.root, text=DOWNLOAD_TEXT, command=self.start, width=300, **button_style)
        self.start_button.grid(column=0, columnspan=2, row=3, padx=10, pady=10, sticky="e")

        self.stop_button = ctk.CTkButton(self.root, text="Stop", command=self.stop, **button_style)
        self.stop_button.grid(column=1, row=3, padx=10, pady=10, sticky="w")

        self.sign_in_button = ctk.CTkButton(self.root, text=SIGN_IN_TEXT, command=self.sign_in, width=300, **button_style)
        self.sign_in_button.grid(column=0, columnspan=2, row=4, padx=10, pady=(0, 10), sticky="e")

        self.idle_widgets = [
            self.playlist_link_entry, self.normalize_audio_checkbox, self.folder_button, self.start_button, self.sign_in_button,
        ]
        self.download_widgets = [self.progress_bar, self.percentage_label, self.eta_label, self.song_label, self.stop_button]

    def set_mode(self, mode):
        shown, hidden = (self.idle_widgets, self.download_widgets) if mode == "idle" else (self.download_widgets, self.idle_widgets)
        try:
            for widget in hidden:
                widget.grid_remove()
            for widget in shown:
                widget.grid()
            self.root.geometry(IDLE_GEOMETRY if mode == "idle" else NORMALIZE_GEOMETRY)
        except TclError:
            pass

    def show_message(self, title, message, icon="info", **options):
        return CTkMessagebox(
            title=title, message=message, icon=icon, button_color=ACCENT_COLOR, button_hover_color=HOVER_COLOR, **options
        ).get()

    def run_in_background(self, work, on_done):
        outcome = {}

        def target():
            try:
                outcome["value"] = work()
            except Exception as e:
                outcome["error"] = e

        thread = threading.Thread(target=target, daemon=True)
        thread.start()

        def poll():
            if self.closing:
                return
            if thread.is_alive():
                self.root.after(POLL_INTERVAL_MS, poll)
            else:
                on_done(outcome.get("value"), outcome.get("error"))

        self.root.after(POLL_INTERVAL_MS, poll)
        return thread

    def toggle_normalization(self):
        self.downloader.normalize_sound = bool(self.normalize_audio_checkbox.get())

    def on_close(self):
        self.closing = True
        self.running = False
        self.root.withdraw()
        self.stop()
        if self.stop_thread is not None:
            self.stop_thread.join(timeout=CLOSE_TIMEOUT_SECONDS)
        self.root.destroy()

    def reset_values(self):
        self.progress_percentage = 0
        self.progress_elapsed = ""
        self.progress_text = ""
        self.progress_eta = 0
        self.cover_mtime = None

    def set_image(self, image_path):
        try:
            with Image.open(image_path) as image:
                cover_art = image.convert("RGB").resize(COVER_SIZE, Image.LANCZOS)
        except (OSError, ValueError):
            return False
        cover_art_element = ctk.CTkImage(light_image=cover_art, dark_image=cover_art, size=COVER_SIZE)
        self.cover_label.configure(image=cover_art_element)
        self.cover_label.image = cover_art_element
        return True

    def refresh_cover(self):
        path = os.path.join(self.selected_folder, COVER_FILE)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return
        if mtime != self.cover_mtime and self.set_image(path):
            self.cover_mtime = mtime

    def update_percentage_label(self):
        self.percentage_label.configure(text=f"{self.progress_percentage:.1f}%")

    def update_song_label_text(self):
        self.song_label.configure(text=self.progress_text)

    def update_song_info(self):
        self.root.geometry(DOWNLOAD_GEOMETRY)
        if len(self.progress_text) > MAX_SONG_NAME_LEN:
            self.progress_text = self.progress_text[:MAX_SONG_NAME_LEN] + "..."
        self.update_song_label_text()
        self.refresh_cover()

    def update_eta_label(self):
        if self.progress_elapsed == "":
            return
        if self.progress_eta == 0:
            eta_clock = "??:??:??"
        else:
            seconds_since_last_eta = (datetime.now() - self.eta_received_time).seconds
            eta_clock = utils.convert_sec_to_clock(self.progress_eta - seconds_since_last_eta)
        self.eta_label.configure(text=f"[{self.progress_elapsed}<{eta_clock}]")

    def update_seconds_elapsed(self):
        self.progress_elapsed = utils.convert_sec_to_clock((datetime.now() - self.time_start).seconds)

    def update_eta(self):
        self.progress_eta = self.downloader.eta or 0
        self.eta_received_time = datetime.now()
        self.update_seconds_elapsed()
        self.update_eta_label()

    def start(self):
        link = os.getenv("DEBUGGING_LINK", "") if DEBUGGING else self.playlist_link_entry.get().strip()
        self.start_button.configure(state="disabled", text=CHECKING_TEXT)

        def check_link():
            self.wait_for_previous_stop()
            return self.downloader.validate_playlist_url(link)

        self.run_in_background(check_link, lambda valid, error: self.finish_start(link, valid, error))

    def finish_start(self, link, valid, error):
        self.start_button.configure(state="normal", text=DOWNLOAD_TEXT)
        if error is not None or not valid:
            self.show_message("Invalid Playlist URL", "Invalid Playlist URL, please check the URL and try again.", "cancel")
            return
        try:
            self.downloader.start_downloader(link)
        except FFmpegNotFoundError:
            self.show_message("Missing ffmpeg", app_support.FFMPEG_HELP, "warning")
            return

        self.reset_values()
        self.time_start = datetime.now()
        self.progress_bar.set(0)
        self.update_percentage_label()
        self.song_label.configure(text="")
        self.eta_label.configure(text="")
        self.running = True
        self.set_mode("download")
        self.schedule_update()

    def wait_for_previous_stop(self):
        if self.stop_thread is not None:
            self.stop_thread.join()
            self.stop_thread = None

    def stop(self):
        self.stop_thread = threading.Thread(target=self.downloader.cancel_downloader, daemon=True)
        self.stop_thread.start()
        self.running = False
        self.reset_values()
        if not self.closing:
            self.set_image(self.default_cover)
            self.set_mode("idle")

    def schedule_update(self):
        if not self.running:
            return
        if self.update_progress():
            self.root.after(UPDATE_INTERVAL_MS, self.schedule_update)

    def update_progress(self):
        downloader = self.downloader
        if app_support.is_download_finished(downloader):
            self.show_completion()
            return False

        if downloader.normalizing:
            self.root.geometry(NORMALIZE_GEOMETRY)
            self.progress_text = app_support.normalization_text(downloader)
            self.progress_percentage = app_support.progress_fraction(downloader.normalized_songs, downloader.total) * 100
            self.update_song_label_text()
            self.update_eta()
        elif downloader.working:
            self.progress_percentage = app_support.progress_fraction(downloader.progress, downloader.total) * 100
            self.progress_text = downloader.current_song or ""
            self.update_eta()
            self.update_song_info()
        else:
            return True

        self.update_percentage_label()
        self.progress_bar.set(self.progress_percentage / 100)
        return True

    def show_completion(self):
        self.running = False
        option = self.show_message(
            "Operation Completed",
            app_support.completion_message(self.downloader),
            "check",
            option_1="OK",
            option_2="Open Directory",
            width=500,
        )
        if option == "Open Directory":
            self.open_output_directory()
        self.stop()

    def open_output_directory(self, platform=None):
        platform = platform or sys.platform
        directory = os.path.abspath(self.selected_folder)
        if platform.startswith("win"):
            os.startfile(directory)
        elif platform == "darwin":
            subprocess.Popen(["open", directory])
        else:
            subprocess.Popen(["xdg-open", directory])

    def folder(self):
        selected = filedialog.askdirectory()
        if not selected:
            return
        self.selected_folder = selected
        self.downloader.set_directory(selected)

    def sign_in(self):
        self.sign_in_button.configure(state="disabled", text=SIGNING_IN_TEXT)
        self.run_in_background(self.downloader.login_exportify, self.finish_sign_in)

    def finish_sign_in(self, value, error):
        self.sign_in_button.configure(state="normal", text=SIGN_IN_TEXT)
        if error is not None:
            self.show_message("Sign-in failed", str(error), "cancel")
            return
        self.show_message(
            "Signed in",
            "Signed in to Spotify. Playlists over 100 tracks in your library will now download in full.",
            "check",
        )

    def run(self):
        self.root.mainloop()
