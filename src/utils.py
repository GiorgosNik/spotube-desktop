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