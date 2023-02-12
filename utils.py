import spotipy
from yt_dlp import YoutubeDL
import os
from spotipy.oauth2 import SpotifyClientCredentials
import lyricsgenius
from zipfile import ZipFile
import subprocess


# Create API objects using the auth keys
def auth_handler():
    genius_auth = lyricsgenius.Genius(
        "5dRV7gMtFLgnlF632ZzqZutSsvPC0IWyFUJ1W8pWHj185RAMFgR4FtX76ckFDjFZ", verbose=False)

    client_id = "ff55dcadd44e4cb0819ebe5be80ab687"
    client_secret = '5539f7392ae94dd5b3dfc1d57381303a'
    auth_manager = SpotifyClientCredentials(
        client_id=client_id, client_secret=client_secret)
    spotify_auth = spotipy.Spotify(auth_manager=auth_manager)

    return {'genius': genius_auth, 'spotify': spotify_auth}


# Setup ffmpeg if not present
def first_time_setup():

    if os.name == 'nt':
        # Windows
        if not os.path.exists('./ffmpeg.exe'):

            while True:

                setup_response = input(
                    "Perform Fist Time Setup? Y/N \n").lower()

                if setup_response == "y":
                    break

                elif setup_response == "n":
                    print("Setup Canceled. Exiting...")

                else:
                    print("Invalid Input")

            with ZipFile('ffmpeg.zip', 'r') as archive:
                archive.extractall()

    elif os.name == 'posix':
        # Unix
        # Check if ffmpeg is installed
        p = str(subprocess.Popen("which ffmpeg", shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0])
        if p == "b''":
            print(
                "Install ffmpeg by running:\n sudo apt-get install ffmpeg, then restart this program.")
            exit()


def create_folder(folder_path):

    if not os.path.isdir(folder_path + '/Songs'):
        os.mkdir(folder_path + '/Songs')


def create_audio_downloader():
    audio_downloader = YoutubeDL({'format': 'bestaudio', 'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }], 'quiet': 'true',
        'no_warnings': 'true', 'noprogress': 'true'})
    return audio_downloader