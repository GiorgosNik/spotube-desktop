import threading
import tkinter as tk
from datetime import datetime
from tkinter.messagebox import showinfo, showerror
import src.utils as utils
from PIL import Image
from time import sleep
import os
import customtkinter as ctk
from tkinter import filedialog
from spotube.download_manager import DownloadManager
from spotube.dependency_handler import DependencyHandler
from tkinter import TclError

# Fix for high DPI displays
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Small Playlist = "https://open.spotify.com/playlist/1jgaUl1FGzK76PPEn6i43f?si=f5b622467318460d"
# Big Title Playlist = "https://open.spotify.com/playlist/3zdqcFFsbURZ1y8oFbEELc?si=1a7c2641ae08404b"
# Big Playlist = https://open.spotify.com/playlist/05MWSPxUUWA0d238WFvkKA?si=d663213356a64949
# Big Rap Playlist = "https://open.spotify.com/playlist/2j71FgBAzmOjogzpmrf4lG?si=a92af70484fd4b3d"

# Debugging Settings
DEBUGGING = False
DEBUGGING_LINK = "https://open.spotify.com/playlist/05MWSPxUUWA0d238WFvkKA?si=d663213356a64949"

# Credentials and API Keys
SPOTIFY_ID = "ff55dcadd44e4cb0819ebe5be80ab687"
SPOTIFY_SECRET = "5539f7392ae94dd5b3dfc1d57381303a"
GENIUS_TOKEN = "5dRV7gMtFLgnlF632ZzqZutSsvPC0IWyFUJ1W8pWHj185RAMFgR4FtX76ckFDjFZ"

# Global Settings
MAX_SONG_NAME_LEN = 40
PLAYLIST_URL_ENTRY_PLACEHOLDER = "Playlist URL"

# Spotify-like Colors
BG_COLOR = "#191414"
TEXT_COLOR = "#FFFFFF"
ACCENT_COLOR = "#116A2D"
HOVER_COLOR = "#0F5A26"

FONT = ("Arial", 10)

class ui_interface:
    def __init__(self):
        # Initialize the window and UI elements as before
        self.root = ctk.CTk()
        self.root.geometry("320x170")
        self.root.title("Spotube")
        self.root.configure(bg=BG_COLOR)
        self.is_download_button_visible = True
        self.is_progress_visible = False
        self.is_eta_visible = False
        self.is_song_label_visible = False
        self.is_playlist_link_entry_visible = True
        self.is_stop_button_visible = False
        self.is_folder_button_visible = True

        # Disable resizing the window
        self.root.resizable(False, False)

        # Initialize internal counters and label strings
        self.progress_percentage = 0
        self.progress_elapsed = ""
        self.progress_text = ""
        self.progress_eta = 0
        self.time_start = datetime.now()
        self.eta_received_time = datetime.now()
        self.prev_song = ""
        self.selected_folder = "./Songs"

        # Playlist URL input
        self.playlist_link_entry = ctk.CTkEntry(self.root, width=250, placeholder_text=PLAYLIST_URL_ENTRY_PLACEHOLDER, font=FONT)
        self.playlist_link_entry.grid(column=0, row=1, columnspan=2, rowspan=2, padx=10, pady=10)

        # Set Playlist Placeholder URL
        self.playlist_link_entry.configure(state="normal")

        # Bind methods to remove and reset placeholder when applicable
        self.playlist_link_entry.bind("<Button-1>", lambda x: utils.on_focus_in(self.playlist_link_entry))
        self.playlist_link_entry.bind(
            "<FocusOut>",
            lambda x: utils.on_focus_out(self.playlist_link_entry, PLAYLIST_URL_ENTRY_PLACEHOLDER),
        )

        self.set_image("./images/cover_art.jpg")

        # The name of the song being processed
        self.song_label = ctk.CTkLabel(self.root, text="", text_color=TEXT_COLOR, font=FONT)
        self.song_label.grid(column=0, row=2, columnspan=2, padx=10, pady=8)

        # Start Button
        self.start_button = ctk.CTkButton(
            self.root, text="Download", command=self.start, fg_color=ACCENT_COLOR, 
            text_color=TEXT_COLOR, hover_color=HOVER_COLOR, font=FONT
        )
        self.start_button.grid(column=0, row=3, padx=10, pady=10, sticky="e")

        self.stop_button = ctk.CTkButton(
            self.root, text="Stop", command=self.stop, fg_color=ACCENT_COLOR, 
            text_color=TEXT_COLOR, hover_color=HOVER_COLOR, font=FONT
        )
        self.stop_button.grid(column=1, row=3, padx=10, pady=10, sticky="w")
        self.stop_button.grid_remove()

        self.folder_button = ctk.CTkButton(
            self.root, text="Folder", command=self.folder, fg_color=ACCENT_COLOR, 
            text_color=TEXT_COLOR, hover_color=HOVER_COLOR, font=FONT
        )
        self.folder_button.grid(column=1, row=3, padx=10, pady=10, sticky="w")

        # # Perform first time check
        self.first_time_setup_check()

        # Initialize DownloadManager
        self.downloader = DownloadManager(
            spotify_client_id=SPOTIFY_ID,
            spotify_client_secret=SPOTIFY_SECRET,
            genius_api_key=GENIUS_TOKEN,
            directory=self.selected_folder
        )

        # Flag to indicate if the application is running
        self.running = True

        # Bind the close event to handle proper shutdown
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.running = False
        self.root.withdraw()
        self.stop()
        self.root.destroy()

    def first_time_setup_check(self):
        if  not DependencyHandler.ffmpeg_installed():
            if os.name == "nt":
                message = "The ffmpeg utility is missing.\nInstalling now..."
            elif os.name == "posix":
                message =  "The ffmpeg utility is missing.\nTo Fix this:\n1)Install ffmpeg by running:\n\n     $sudo apt-get install ffmpeg      \n\n 2) Restart the program"
            showinfo(message=message)
            if os.name == "nt":
                DependencyHandler.download_ffmpeg(os_type=os.name)

    def reset_values(self):
        self.progress_percentage = 0
        self.progress_elapsed = ""
        self.progress_text = ""
        self.progress_eta = 0

    def set_image(self, image_path):
        cover_art = Image.open(image_path)
        cover_art = cover_art.resize((150, 150), Image.LANCZOS)
        cover_art_element = ctk.CTkImage(light_image=cover_art, dark_image=cover_art, size=(150, 150))
        self.label = ctk.CTkLabel(self.root, image=cover_art_element, text='', bg_color=BG_COLOR)
        self.label.grid(column=5, row=0, columnspan=3, rowspan=4, padx=10)
        self.label.image = cover_art_element

    def set_progress(self, value):
        self.progress_bar.set(value / 100)
        self.progress_percentage = value
        self.update_progress_label()
        if value >= 100:
            showinfo(message="Download Complete")
            self.progress_bar.set(0)
            self.stop()
            self.playlist_link_entry.delete(0, tk.END)
            self.playlist_link_entry.insert(0, "")
            utils.on_focus_out(self.playlist_link_entry, PLAYLIST_URL_ENTRY_PLACEHOLDER)

    def update_progress_label(self):
        percentage = "%.1f" % self.progress_percentage
        self.progress_label.configure(text="{}%".format(percentage))

    def update_song_label(self):
        self.root.geometry("480x150")
        if len(self.progress_text) > MAX_SONG_NAME_LEN:
            self.progress_text = self.progress_text[:MAX_SONG_NAME_LEN] + "..."
        self.song_label.configure(text=self.progress_text)
        while not os.path.exists(self.selected_folder+"/cover_photo.jpg"):
            sleep(0.1)
        self.set_image(self.selected_folder+"/cover_photo.jpg")

    def update_eta_label(self):
        if hasattr(self, 'eta_label') and self.eta_label:
            if self.progress_elapsed != "":
                if self.progress_eta == 0:
                    eta_clock = "??:??:??"
                else:
                    seconds_since_last_eta = (datetime.now() - self.eta_received_time).seconds
                    actual_eta = self.progress_eta - seconds_since_last_eta
                    eta_clock = utils.convert_sec_to_clock(actual_eta)
                self.eta_label.configure(text="[{}<{}]".format(self.progress_elapsed, eta_clock))

    def update_seconds_elapsed(self):
        seconds_elapsed = (datetime.now() - self.time_start).seconds
        self.progress_elapsed = utils.convert_sec_to_clock(seconds_elapsed)

    def start(self):
        self.time_start = datetime.now()
        link = self.playlist_link_entry.get()
        if DEBUGGING:
            link = DEBUGGING_LINK
        if self.downloader.validate_playlist_url(link):
            self.running = True
            self.progress_bar = ctk.CTkProgressBar(self.root, orientation="horizontal", mode="determinate", width=300)
            self.progress_bar.grid(column=0, row=0, columnspan=2, padx=10, pady=13)
            self.progress_bar.set(0)
            self.is_progress_visible = True
            self.progress_label = ctk.CTkLabel(self.root, text="0%")
            self.progress_label.grid(column=0, row=1)
            self.is_eta_visible = True
            self.eta_label = ctk.CTkLabel(self.root, text="")
            self.eta_label.grid(column=1, row=1)
            self.is_eta_visible = True
            self.progress_percentage = 0
            self.downloader.start_downloader(link)
            self.update_progress_label()
            self.is_playlist_link_entry_visible = False
            self.is_eta_visible = True
            self.is_song_label_visible = True
            self.is_stop_button_visible = True
            self.is_folder_button_visible = False
            self.is_download_button_visible = False
            self.schedule_update()
        else:
            showerror(message="Invalid Playlist URL")
        self.manage_visibility()

    def stop(self):
        # Stop the downloader in a thread
        stop_thread = threading.Thread(target=self.downloader.cancel_downloader, daemon=True)
        stop_thread.start()

        # Initialize new DownloadManager
        self.downloader = DownloadManager(
            spotify_client_id=SPOTIFY_ID,
            spotify_client_secret=SPOTIFY_SECRET,
            genius_api_key=GENIUS_TOKEN,
            directory=self.selected_folder
        )

        self.reset_values()

        if hasattr(self, 'progress_bar') and self.progress_bar:
            self.progress_bar.grid_remove()
            self.is_progress_visible = False

        if hasattr(self, 'progress_label') and self.progress_label:
            self.progress_label.grid_remove()

        self.is_eta_visible = False
        if hasattr(self, 'eta_label') and self.eta_label:
            self.is_eta_visible = False
            self.eta_label.grid_remove()
            self.song_label.configure(text="")
            self.is_playlist_link_entry_visible = True
            self.is_eta_visible = False
            self.is_song_label_visible = False
            self.is_stop_button_visible = False
            self.is_folder_button_visible = True
            self.is_download_button_visible = True
            self.root.geometry("320x170")
            self.running = False

        self.manage_visibility()
        self.stop_thread.join()


    def schedule_update(self):
        if self.running:
            self.update_progress()
            self.root.after(1000, self.schedule_update)
            self.manage_visibility()

    def manage_visibility(self):
        try:
            self.manage_progress_bar_visibility()
            self.manage_progress_label_visibility()
            self.manage_song_label_visibility()
            self.manage_playlist_link_entry_visibility()
            self.manage_stop_button_visibility()
            self.manage_folder_button_visibility()
            self.manage_download_button_visibility()
        except TclError:
            # Application has been destroyed; handle accordingly
            pass

    def manage_progress_bar_visibility(self):
        if hasattr(self, 'progress_bar') and self.progress_bar:
            if self.is_progress_visible:
                self.progress_bar.grid()
            else:
                self.progress_bar.grid_remove()

    def manage_progress_label_visibility(self):
        if hasattr(self, 'progress_label') and self.progress_label:
            if self.is_eta_visible:
                self.progress_label.grid()
                self.eta_label.grid()
            else:
                self.progress_label.grid_remove()
                self.eta_label.grid_remove()

    def manage_song_label_visibility(self):
        if hasattr(self, 'song_label') and self.song_label:
            if self.is_song_label_visible:
                self.song_label.grid()
            else:
                self.song_label.grid_remove()

    def manage_playlist_link_entry_visibility(self):
        if self.is_playlist_link_entry_visible:
            self.playlist_link_entry.grid()
        else:
            self.playlist_link_entry.grid_remove()

    def manage_stop_button_visibility(self):
        if self.is_stop_button_visible:
            self.stop_button.grid()
        else:
            self.stop_button.grid_remove()

    def manage_folder_button_visibility(self):
        if self.is_folder_button_visible:
            self.folder_button.grid()
        else:
            self.folder_button.grid_remove()

    def manage_download_button_visibility(self):
        if self.is_download_button_visible:
            self.start_button.grid()
        else:
            self.start_button.grid_remove()

    def update_progress(self):
        # Get total number of songs; avoid division by 0
        total = 1 if self.downloader.get_total() == 0 else self.downloader.get_total()

        # Get current progress as a percentage
        self.progress_percentage = self.downloader.get_progress() / total * 100

        # Get the current song name
        self.progress_text = self.downloader.get_current_song() or ""

        # Get the estimated time of arrival (ETA)
        self.progress_eta = self.downloader.get_eta() or 0

        # Update the elapsed time and labels
        self.update_seconds_elapsed()
        self.update_progress_label()
        self.update_eta_label()
        self.update_song_label()

        # Update the progress bar
        self.progress_bar.set(self.progress_percentage / 100)


    def folder(self):
        self.selected_folder = filedialog.askdirectory()
        self.downloader.set_download_directory(self.selected_folder)

    def run(self):
        self.root.mainloop()
        self.manage_visibility()