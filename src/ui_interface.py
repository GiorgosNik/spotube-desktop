from tkinter import ttk
import tkinter as tk
import queue
from datetime import datetime, time
from tkinter.messagebox import showinfo, showerror
from src.downloader_class import downloader
import src.utils as utils
from tkinter.constants import W
from PIL import ImageTk, Image
from time import sleep
import os

DOWNLOAD_COMPLETE_MESSAGE = "Download Complete"
INVALID_URL_MESSAGE = "Invalid Playlist Link"
DEBUGGING_LINK = "https://open.spotify.com/playlist/05MWSPxUUWA0d238WFvkKA?si=d663213356a64949"
DEBUGGING_LINK_BIG = "https://open.spotify.com/playlist/1jgaUl1FGzK76PPEn6i43f?si=f5b622467318460d"
DEBUGGING_LINK_BIG_SONG_NAME = "https://open.spotify.com/playlist/3zdqcFFsbURZ1y8oFbEELc?si=1a7c2641ae08404b"
PLAYLIST_URL_ENTRY_PLACEHOLDER = "Enter Playlist URL"
MAX_SONG_NAME_LEN = 40
DEBUGGING = True

SPOTIFY_ID = "ff55dcadd44e4cb0819ebe5be80ab687"
SPOTIFY_SECRET = "5539f7392ae94dd5b3dfc1d57381303a"
GENIUS_TOKEN = "5dRV7gMtFLgnlF632ZzqZutSsvPC0IWyFUJ1W8pWHj185RAMFgR4FtX76ckFDjFZ"



class ui_interface:
    def __init__(self):
        # Create the window
        self.root = tk.Tk()
        self.root.tk.call("source", "./theme/forest-dark.tcl")
        ttk.Style().theme_use("forest-dark")
        self.root.geometry("320x150")
        self.root.title("Spotube")

        # Initialize internal counters and label strings
        self.progress_percentage = 0
        self.progress_elapsed = ""
        self.progress_text = ""
        self.progress_eta = 0
        self.time_start = datetime.now()
        self.eta_received_time = datetime.now()
        self.downloader = downloader(SPOTIFY_ID, SPOTIFY_SECRET, GENIUS_TOKEN)
        self.prev_song = ""

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
        start_button = ttk.Button(self.root, text="Download", command=self.start)
        start_button.grid(column=0, row=3, padx=10, pady=10, sticky=tk.E)

        stop_button = ttk.Button(self.root, text="Stop", command=self.stop)
        stop_button.grid(column=1, row=3, padx=10, pady=10, sticky=tk.W)

    def reset_values(self):
        self.progress_percentage = 0
        self.progress_elapsed = ""
        self.progress_text = ""
        self.progress_eta = 0
        # self.time_start = datetime.now()
        # self.eta_received_time = datetime.now()
        # self.prev_song = ""

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
            showinfo(message=DOWNLOAD_COMPLETE_MESSAGE)
            self.progress_bar["value"] = 0
            self.stop()

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
            link = DEBUGGING_LINK

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
        else:
            showerror(message=INVALID_URL_MESSAGE)

    # Handle the Stop Button, stop the download
    def stop(self):
        self.progress_bar.stop()
        self.progress_bar["value"] = 0
        self.progress_label["text"] = self.update_progress_label()

        self.progress_label.grid_remove()
        self.eta_label.grid_remove()
        self.song_label.grid_remove()
        self.playlist_link_entry.grid()

        # Restore Window Size
        self.root.geometry("320x150")

        # Stop downloader object
        self.downloader.stop_downloader()

        # Zero the progressbar
        self.progress_bar["value"] = 0

        self.reset_values()

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
