import spotipy
from yt_dlp import YoutubeDL
import os
from spotipy.oauth2 import SpotifyClientCredentials
import lyricsgenius
from zipfile import ZipFile
import subprocess
import datetime
from tkinter import ttk
import tkinter as tk

def on_focus_in(entry):
    if str(entry.cget('state')) == 'disabled':
        entry.configure(state='normal')
        entry.delete(0, 'end')


def on_focus_out(entry, placeholder):
    if entry.get() == "":
        entry.insert(0, placeholder)
        entry.configure(state='disabled')

def convert_sec_to_clock(seconds):
    seconds = float(int(seconds))
    time = str(datetime.timedelta(seconds=seconds))
    return time

# Setup ffmpeg if not present
def first_time_setup():
    if os.name == "nt":
        # Windows
        if not os.path.exists("./ffmpeg.exe"):
            while True:
                setup_response = input("Perform Fist Time Setup? Y/N \n").lower()

                if setup_response == "y":
                    break

                elif setup_response == "n":
                    print("Setup Canceled. Exiting...")

                else:
                    print("Invalid Input")

            with ZipFile("./static/ffmpeg.zip", "r") as archive:
                archive.extractall()

    elif os.name == "posix":
        # Unix
        # Check if ffmpeg is installed
        p = str(
            subprocess.Popen(
                "which ffmpeg",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).communicate()[0]
        )
        if p == "b''":
            print("Install ffmpeg by running:\n sudo apt-get install ffmpeg, then restart this program.")
            exit()