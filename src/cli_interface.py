from youtubesearchpython import VideosSearch
import src.utils as utils
import src.downloader as downloader
from tqdm import tqdm


def main_cli():
    # Perform first time setup checks
    utils.first_time_setup()
    # Perform authentication for LyricsGenius and Spotify APIs
    tokens = utils.auth_handler()
    # Main Functionality
    while True:
        response = input("Give the URL of a Spotify Playlist, or type 'EXIT' to close the application \n")
        if response.lower() == "exit":
            print("Exiting")
            exit()
        # For testing
        response = "https://open.spotify.com/playlist/05MWSPxUUWA0d238WFvkKA?si=d663213356a64949"
        downloader.download_playlist(response, tokens)
        print("Playlist Downloaded")
