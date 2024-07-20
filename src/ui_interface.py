import tkinter as tk
from datetime import datetime
from tkinter.messagebox import showinfo, showerror
from src.downloader_class import downloader
import src.utils as utils
from PIL import Image
from time import sleep
import os
import customtkinter as ctk
from tkinter import filedialog

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

class ui_interface:
    def __init__(self):
        # Create the window
        self.root = ctk.CTk()
        self.root.geometry("320x170")
        self.root.title("Spotube")

        self.is_download_button_visible = True  # New flag for download button visibility
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
        self.downloader = downloader(SPOTIFY_ID, SPOTIFY_SECRET, GENIUS_TOKEN)
        self.prev_song = ""
        self.selected_folder = "./Songs"

        # Playlist URL input
        self.playlist_link_entry = ctk.CTkEntry(self.root, width=250, placeholder_text=PLAYLIST_URL_ENTRY_PLACEHOLDER)
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
        self.song_label = ctk.CTkLabel(self.root, text="")
        self.song_label.grid(column=0, row=2, columnspan=2, padx=10, pady=8)

        # Start Button
        self.start_button = ctk.CTkButton(self.root, text="Download", command=self.start)
        self.start_button.grid(column=0, row=3, padx=10, pady=10, sticky="e")

        self.stop_button = ctk.CTkButton(self.root, text="Stop", command=self.stop)
        self.stop_button.grid(column=1, row=3, padx=10, pady=10, sticky="w")
        self.stop_button.grid_remove()

        self.folder_button = ctk.CTkButton(self.root, text="Folder", command=self.folder)
        self.folder_button.grid(column=1, row=3, padx=10, pady=10, sticky="w")

        # Perform first time check
        self.first_time_setup_check()

        # Flag to indicate if the application is running
        self.running = True

        # Bind the close event to handle proper shutdown
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.running = False
        self.root.destroy()

    def first_time_setup_check(self):
        if os.name == "nt":
            message = "The ffmpeg utility is missing.\nInstalling now..."
        elif os.name == "posix":
            message =  "The ffmpeg utility is missing.\nTo Fix this:\n1)Install ffmpeg by running:\n\n     $sudo apt-get install ffmpeg      \n\n 2) Restart the program"

        if not self.downloader.ffmpeg_installed():
            showinfo(message=message)

            # If OS is Windows, install extract ffmpeg.exe
            if os.name == "nt":
                self.downloader.first_time_setup()

    def reset_values(self):
        self.progress_percentage = 0
        self.progress_elapsed = ""
        self.progress_text = ""
        self.progress_eta = 0

    def set_image(self, image_path):
        cover_art = Image.open(image_path)
        cover_art = cover_art.resize((150, 150), Image.LANCZOS)
        cover_art_element = ctk.CTkImage(light_image=cover_art, dark_image=cover_art, size=(150, 150))
        self.label = ctk.CTkLabel(self.root, image=cover_art_element, text='')
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
        while not os.path.exists("./cover_photo.jpg"):
            sleep(0.1)

        self.set_image("./cover_photo.jpg")

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

    def calculate_progress(self, current, total):
        return (current / total) * 100

    def calculate_eta(self, eta):
        self.eta_received_time = datetime.now()
        self.progress_eta = eta

    def handle_message(self, message):
        contents = message["contents"]

        if message["type"] == "progress":
            progress = self.calculate_progress(current=contents[0], total=contents[1])
            self.set_progress(progress)

        elif message["type"] == "song_title":
            self.progress_text = contents
            self.update_song_label()

        elif message["type"] == "eta_update":
            self.calculate_eta(eta=contents[1])
            self.update_eta_label()

    def start(self):
        self.time_start = datetime.now()
        link = self.playlist_link_entry.get()

        if DEBUGGING:
            link = DEBUGGING_LINK

        if self.downloader.validate_playlist_url(link):
            self.running = True  # Set running to True here

            # Set up the progress bar
            self.progress_bar = ctk.CTkProgressBar(self.root, orientation="horizontal", mode="determinate", width=300)
            self.progress_bar.grid(column=0, row=0, columnspan=2, padx=10, pady=13)
            self.is_progress_visible = True

            # Set up the Percentage Label
            self.progress_label = ctk.CTkLabel(self.root, text="")
            self.progress_label.grid(column=0, row=1)
            self.is_eta_visible = True

            # Set up the ETA Label
            self.eta_label = ctk.CTkLabel(self.root, text="")
            self.eta_label.grid(column=1, row=1)
            self.is_eta_visible = True

            self.download = self.downloader.start_downloader(link)
            self.update_progress_label()
            self.is_playlist_link_entry_visible = False
            self.is_eta_visible = True
            self.is_song_label_visible = True
            self.is_stop_button_visible = True
            self.is_folder_button_visible = False
            self.is_download_button_visible = False  # Hide the download button
            self.schedule_update()
        else:
            showerror(message="Invalid Playlist Link")
        self.manage_visibility()

    def stop(self):
        self.running = False  # Set running to False here

        if hasattr(self, 'progress_bar') and self.progress_bar:
            self.progress_bar.grid_remove()
            self.is_progress_visible = False
        if hasattr(self, 'progress_label') and self.progress_label:
            self.progress_label.grid_remove()
            self.is_eta_visible = False
        if hasattr(self, 'eta_label') and self.eta_label:
            self.eta_label.grid_remove()
            self.is_eta_visible = False

        self.progress_bar = None
        self.progress_label = None
        self.eta_label = None

        self.is_eta_visible = False
        self.is_song_label_visible = False
        self.is_playlist_link_entry_visible = True
        self.is_stop_button_visible = False
        self.is_folder_button_visible = True
        self.is_download_button_visible = True  # Show the download button again

        self.root.geometry("320x150")
        self.reset_values()
        self.downloader.stop_downloader()
        self.manage_visibility()

    def manage_visibility(self):
        if hasattr(self, 'progress_bar') and self.progress_bar:
            if self.is_progress_visible:
                self.progress_bar.grid()
            else:
                self.progress_bar.grid_remove()

        if hasattr(self, 'progress_label') and self.progress_label:
            if self.is_eta_visible:
                self.progress_label.grid()
                self.eta_label.grid()
            else:
                self.progress_label.grid_remove()
                self.eta_label.grid_remove()

        if hasattr(self, 'song_label') and self.song_label:
            if self.is_song_label_visible:
                self.song_label.grid()
            else:
                self.song_label.grid_remove()

        if self.is_playlist_link_entry_visible:
            self.playlist_link_entry.grid()
        else:
            self.playlist_link_entry.grid_remove()

        if self.is_stop_button_visible:
            self.stop_button.grid()
        else:
            self.stop_button.grid_remove()

        if self.is_folder_button_visible:
            self.folder_button.grid()
        else:
            self.folder_button.grid_remove()

        if self.is_download_button_visible:
            self.start_button.grid()
        else:
            self.start_button.grid_remove()

    def folder(self):
        given_folder = filedialog.askdirectory()
        if not isinstance(given_folder, tuple):
            self.selected_folder = given_folder

        self.selected_folder += "/Songs"
        self.downloader.set_directory(self.selected_folder)

    def update_downloader_status(self):
        progress = self.downloader.get_progress()
        total = self.downloader.get_total()
        current_song = self.downloader.get_current_song()
        eta = self.downloader.get_eta()

        if total is not None:
            progress_percentage = self.calculate_progress(current=progress, total=total)
            self.set_progress(progress_percentage)

        if current_song is not None and self.prev_song != current_song:
            self.prev_song = current_song
            self.progress_text = current_song
            self.update_song_label()

            if eta is not None:
                self.calculate_eta(eta)
                self.update_eta_label()

    def schedule_update(self):
        if self.running:
            if hasattr(self, 'progress_bar') and self.progress_bar:
                self.update_downloader_status()
                self.update_seconds_elapsed()
                if hasattr(self, 'eta_label') and self.eta_label:
                    self.update_eta_label()
            self.manage_visibility()
            self.root.after(100, self.schedule_update)

    def run(self):
        self.schedule_update()
        self.manage_visibility()
        self.root.mainloop()


if __name__ == "__main__":
    ui = ui_interface()
    ui.run()