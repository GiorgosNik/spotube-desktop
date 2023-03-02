from src.downloader_class import downloader
from tkinter.constants import W
import os
import sys

DOWNLOAD_COMPLETE_MESSAGE = "Download Complete"
FIRST_TIME_SETUP_MESSAGE_WINDOWS = "The ffmpeg utility is missing.\nInstalling now..."
FIRST_TIME_SETUP_MESSAGE_UNIX = "The ffmpeg utility is missing.\nTo Fix this:\n1)Install ffmpeg by running:\n\n     $sudo apt-get install ffmpeg      \n\n 2) Restart the program"
INVALID_URL_MESSAGE = "Invalid Playlist Link"
DEBUGGING_LINK = "https://open.spotify.com/playlist/05MWSPxUUWA0d238WFvkKA?si=d663213356a64949"
DEBUGGING_LINK_BIG = "https://open.spotify.com/playlist/1jgaUl1FGzK76PPEn6i43f?si=f5b622467318460d"
DEBUGGING_LINK_BIG_SONG_NAME = "https://open.spotify.com/playlist/3zdqcFFsbURZ1y8oFbEELc?si=1a7c2641ae08404b"
PLAYLIST_URL_ENTRY_PLACEHOLDER = "Playlist URL"
MAX_SONG_NAME_LEN = 40
DEBUGGING = False

SPOTIFY_ID = "ff55dcadd44e4cb0819ebe5be80ab687"
SPOTIFY_SECRET = "5539f7392ae94dd5b3dfc1d57381303a"
GENIUS_TOKEN = "5dRV7gMtFLgnlF632ZzqZutSsvPC0IWyFUJ1W8pWHj185RAMFgR4FtX76ckFDjFZ"


def first_time_setup_check(given_downloader):
    if os.name == "nt":
        message = FIRST_TIME_SETUP_MESSAGE_WINDOWS
    elif os.name == "posix":
        message = FIRST_TIME_SETUP_MESSAGE_UNIX

    if not given_downloader.ffmpeg_installed():
        given_downloader.first_time_setup()
        print(message)


def use_guide():
    print("Usage: python spotube_ui.py {URL} (Optional){DIRECTORY}")


if __name__ == "__main__":
    dir = "./Songs"

    # Get command line arguments
    arg_len = len(sys.argv)
    if arg_len != 2 and arg_len != 3:
        use_guide()
        exit()

    url = sys.argv[1]

    if arg_len == 3:
        dir = sys.argv[2]

    # Create the destination directory
    if not os.path.isdir(dir):
        os.mkdir(dir)

    # Create downloader object
    downloader_object = downloader(SPOTIFY_ID, SPOTIFY_SECRET, GENIUS_TOKEN, dir)

    # Perform first time checks
    first_time_setup_check(downloader_object)
    downloader_object.first_time_setup()

    if DEBUGGING:
        url = DEBUGGING_LINK

    if downloader_object.validate_playlist_url(url):
        # If the link is valid, start the download
        downloader_object.start_downloader(url)
    else:
        print(INVALID_URL_MESSAGE)
        exit()
