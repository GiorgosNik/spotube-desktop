from tkinter import ttk
import tkinter as tk
from datetime import datetime
from tkinter.messagebox import showinfo, showerror
from src.downloader_class import downloader
import src.utils as utils
from tkinter.constants import W
from PIL import ImageTk, Image
from time import sleep
import os
from tkinter.filedialog import askdirectory

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
        self.root = tk.Tk()
        self.root.tk.call("source", "./theme/forest-dark.tcl")
        ttk.Style().theme_use("forest-dark")
        self.root.geometry("320x150")
        self.root.title("Spotube")

        # Disable resizing the window
        self.root.resizable(False, False)

        # Set folder dialog text to black to improve readability
        self.root.option_add("*TkFDialog*foreground", "black")
        self.root.option_add("*TkChooseDir*foreground", "black")

        ttk.Style(self.root)

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
        self.playlist_link_entry = ttk.Entry(self.root, width=35)
        self.playlist_link_entry.grid(column=0, row=1, columnspan=2, rowspan=2)

        # Set Playlist Placeholder URL
        self.playlist_link_entry.insert(0, PLAYLIST_URL_ENTRY_PLACEHOLDER)
        self.playlist_link_entry.configure(state="disabled")

        # Bind methods to remove and reset placeholder when applicable
        self.playlist_link_entry.bind("<Button-1>", lambda x: utils.on_focus_in(self.playlist_link_entry))
        self.playlist_link_entry.bind(
            "<FocusOut>",
            lambda x: utils.on_focus_out(self.playlist_link_entry, PLAYLIST_URL_ENTRY_PLACEHOLDER),
        )

        # Set up the progressbar
        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", mode="determinate", length=300)
        self.progress_bar.grid(column=0, row=0, columnspan=2, padx=10, pady=13)

        # Percentage Label
        self.progress_label = ttk.Label(self.root, text="")
        self.progress_label.grid(
            column=0,
            row=1,
        )
        # Hide the label until the download starts
        self.progress_label.grid_remove()

        # ETA Label
        self.eta_label = ttk.Label(self.root, text="")
        self.eta_label.grid(
            column=1,
            row=1,
        )
        # Hide the label until the download starts
        self.eta_label.grid_remove()

        self.set_image("./images/cover_art.jpg")

        # The name of the song being processed
        self.song_label = ttk.Label(self.root, text="")
        self.song_label.grid(column=0, row=2, columnspan=2, padx=10, pady=8)

        # Start Button
        self.start_button = ttk.Button(self.root, text="Download", command=self.start, style='Accent.TButton')
        self.start_button.grid(column=0, row=3, padx=10, pady=10, sticky=tk.E)

        self.stop_button = ttk.Button(self.root, text="Stop", command=self.stop, style='Accent.TButton')
        self.stop_button.grid(column=1, row=3, padx=10, pady=10, sticky=tk.W)
        self.stop_button.grid_remove()

        self.folder_button = ttk.Button(self.root, text="Folder", command=self.folder, style='Accent.TButton')
        self.folder_button.grid(column=1, row=3, padx=10, pady=10, sticky=tk.W)

        # Perform first time check
        self.first_time_setup_check()


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

    def set_image(self, image):
        cover_art = Image.open(image)
        cover_art = cover_art.resize((150, 150), Image.ANTIALIAS)
        cover_art_element = ImageTk.PhotoImage(cover_art)
        self.label = ttk.Label(self.root, image=cover_art_element)
        self.label.image = cover_art_element
        self.label.grid(column=5, row=0, columnspan=3, rowspan=4, padx=10)

    # Update the progressbar
    def set_progress(self, value):
        self.progress_bar["value"] = value
        self.progress_percentage = self.progress_bar["value"]
        self.update_progress_label()
        if self.progress_bar["value"] >= 100:
            showinfo(message="Download Complete")
            self.progress_bar["value"] = 0
            self.stop()
            # Reset the playlist input field
            self.playlist_link_entry.delete(0,tk.END)
            self.playlist_link_entry.insert(0,"")
            utils.on_focus_out(self.playlist_link_entry, PLAYLIST_URL_ENTRY_PLACEHOLDER)

    def update_progress_label(self):
        percentage = "%.1f" % self.progress_percentage
        self.progress_label["text"] = "{}% ".format(percentage)

    def update_song_label(self):
        self.root.geometry("480x150")

        # Slice song title, if over a certain length
        if len(self.progress_text) > MAX_SONG_NAME_LEN:
            self.progress_text = self.progress_text[:MAX_SONG_NAME_LEN] + "..."

        self.song_label["text"] = "{}".format(self.progress_text)
        while not os.path.exists("./cover_photo.jpg"):
            sleep(0.1)

        self.set_image("./cover_photo.jpg")

    def update_eta_label(self):
        # Only update the ETA label if the download has started
        if self.progress_elapsed != "":
            if self.progress_eta == 0:
                # If no ETA has been received yet, display question marks
                eta_clock = "??:??:??"
            else:
                # If at least one ETA has been received
                # Calculate how many seconds passed since the ETA was received, subtract from the ETA
                seconds_since_last_eta = (datetime.now() - self.eta_received_time).seconds
                actual_eta = self.progress_eta - seconds_since_last_eta
                eta_clock = utils.convert_sec_to_clock(actual_eta)

            self.eta_label["text"] = "[{}<{}]".format(self.progress_elapsed, eta_clock)

    def update_seconds_elapsed(self):
        seconds_elapsed = (datetime.now() - self.time_start).seconds
        self.progress_elapsed = utils.convert_sec_to_clock(seconds_elapsed)

    # Calculate Progress Percentage
    def calculate_progress(self, current, total):
        return (current / total) * 100

    # Convert Elapsed Seconds to ETA Clock Format
    def calculate_eta(self, eta):
        self.eta_received_time = datetime.now()
        self.progress_eta = eta

    # Direct different message types to different methods
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

    # Handle the Start Button, start the download
    def start(self):
        # Save start time to calculate time elapsed later
        self.time_start = datetime.now()

        # Get playlist URL from the Entry widget
        link = self.playlist_link_entry.get()

        # Debugging URL
        if DEBUGGING:
            link = DEBUGGING_LINK_BIG

        if self.downloader.validate_playlist_url(link):
            # If the link is valid, start the download
            self.download = self.downloader.start_downloader(link)

            # Display the progress label
            self.update_progress_label()

            # Hide Entry
            self.playlist_link_entry.grid_remove()

            # Display ETA and Progress Percentage labels
            self.eta_label.grid()
            self.progress_label.grid()
            self.song_label.grid()
            self.stop_button.grid()
            self.folder_button.grid_remove()
        else:
            showerror(message="Invalid Playlist Link")

    # Handle the Stop Button, stop the download
    def stop(self):
        self.progress_bar.stop()
        self.progress_bar["value"] = 0
        self.progress_label["text"] = self.update_progress_label()

        self.progress_label.grid_remove()
        self.eta_label.grid_remove()
        self.song_label.grid_remove()
        self.playlist_link_entry.grid()
        self.stop_button.grid_remove()
        self.folder_button.grid()

        # Restore Window Size
        self.root.geometry("320x150")

        # Zero the progressbar
        self.progress_bar["value"] = 0

        self.reset_values()

        # Stop downloader object
        self.downloader.stop_downloader()

    def folder(self):
        given_folder = askdirectory()
        if type(given_folder) != tuple:
            self.selected_folder = given_folder

        self.selected_folder += "/Songs"
        self.downloader.set_directory(self.selected_folder)

    # Run once in each main loop
    # Get the status of the downloader to update the UI
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

    # Main Loop
    def run(self):
        while True:
            self.update_downloader_status()
            self.update_seconds_elapsed()
            self.update_eta_label()
            self.root.update_idletasks()
            self.root.update()
