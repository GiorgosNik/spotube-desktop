from tkinter import ttk
import tkinter as tk
import queue
from tkinter.messagebox import showinfo
from src.downloader import downloader


class interface:
    def __init__(self):
        # Create the queue
        self.channel = queue.Queue()

        # Create the window
        self.root = tk.Tk()
        self.root.tk.call("source", "./theme/forest-dark.tcl")
        ttk.Style().theme_use("forest-dark")
        self.root.geometry("300x120")
        self.root.title("Spotube")
        self.progress_percentage = "0%"
        self.progress_text = ""

        # Progressbar
        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", mode="determinate", length=280)

        # Set up the progressbar
        self.progress_bar.grid(column=0, row=0, columnspan=2, padx=10, pady=20)

        # Progressbar Label
        self.value_label = ttk.Label(self.root, anchor="w", text="")
        self.value_label.grid(column=0, row=1, columnspan=2)

        # Start Button
        start_button = ttk.Button(self.root, text="Progress", command=self.start)
        start_button.grid(column=0, row=2, padx=10, pady=10, sticky=tk.E)

        stop_button = ttk.Button(self.root, text="Stop", command=self.stop)
        stop_button.grid(column=1, row=2, padx=10, pady=10, sticky=tk.W)

    # Update the progressbar
    def set_progress(self, value):
        self.progress_bar["value"] = value
        self.progress_percentage = self.progress_bar["value"]
        self.update_progress_label()
        if self.progress_bar["value"] >= 100:
            showinfo(message="The progress completed!")

    def update_progress_label(self):
        self.value_label["text"] = "{} - {}".format(self.progress_percentage, self.progress_text)

    def calculate_progress(self, current, total):
        return (current / total) * 100

    def start(self):
        # Debbuging URL
        link = "https://open.spotify.com/playlist/05MWSPxUUWA0d238WFvkKA?si=d663213356a64949"
        downloader.start_downloader(self.channel, link)

    def stop(self):
        self.progress_bar.stop()
        self.value_label["text"] = self.update_progress_label()

    # Direct different message types to different methodss
    def handle_message(self, message):
        contents = message["contents"]

        if message["type"] == "progress":
            progress = self.calculate_progress(contents[0], contents[1])
            self.set_progress(progress)
        elif message["type"] == "song_title":
            self.progress_text = contents
            self.update_progress_label()

    def run(self):
        while True:
            if not self.channel.empty():
                message = self.channel.get()
                self.handle_message(message)

            self.root.update_idletasks()
            self.root.update()
