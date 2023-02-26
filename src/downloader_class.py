import threading
import queue
import src.downloader_utils as downloader_utils
import os
import subprocess


class downloader:
    def __init__(self, spotify_id, spotify_secret, genius_token, directory="./Songs"):
        # Initialise the tracking values
        self.progress = 0
        self.total = None
        self.current_song = None
        self.eta = None
        self.thread = None
        self.spotify_id = spotify_id
        self.spotify_secret = spotify_secret
        self.genius_token = genius_token
        self.directory = directory

        # Set the channel that will handle the messages from the worker
        self.channel = queue.Queue()

        # Set the channel that will handle the messages from the worker
        self.termination_channel = queue.Queue()

        # Perform authentication for LyricsGenius and Spotify APIs
        self.tokens = downloader_utils.auth_handler(self.spotify_id, self.spotify_secret, self.genius_token)

    def set_directory(self, directory):
        self.directory = directory

    def start_downloader(self, link):
        # Create a new thread to handle the download
        self.thread = threading.Thread(
            target=downloader_utils.download_playlist,
            args=[link, self.tokens, self.channel, self.termination_channel, self.directory],
        )
        self.thread.start()

    def stop_downloader(self):
        self.termination_channel.put(downloader_utils.EXIT)

        # Wait for thread to exit
        if self.thread is not None:
            self.thread.join()

        self.progress = 0
        self.total = None
        self.current_song = None
        self.eta = None
        self.thread = None
        self.channel = queue.Queue()
        self.termination_channel = queue.Queue()
        self.tokens = downloader_utils.auth_handler(self.spotify_id, self.spotify_secret, self.genius_token)

    def validate_playlist_url(self, playlist_url):
        try:
            self.tokens["spotify"].playlist_tracks(playlist_url)
        except Exception as e:
            print(str(e))
            print("Playlist Link Not Found")
            return False
        return True

    # Save the state of the worker thread based on the message
    def handle_message(self, message):
        contents = message["contents"]

        if message["type"] == "progress":
            self.progress = contents[0]
            self.total = contents[1]

        elif message["type"] == "song_title":
            self.current_song = contents

        elif message["type"] == "eta_update":
            self.eta = contents[1]

    def fetch_messages(self):
        if not self.channel.empty():
            message = self.channel.get()
            self.handle_message(message)

    def get_progress(self):
        self.fetch_messages()
        return self.progress

    def get_total(self):
        self.fetch_messages()
        return self.total

    def get_current_song(self):
        self.fetch_messages()
        return self.current_song

    def get_eta(self):
        self.fetch_messages()
        return self.eta

    # Return True if ffmpeg is installed, False otherwise
    @staticmethod
    def ffmpeg_installed():
        if os.name == "nt":
            # Windows
            if not os.path.exists("./ffmpeg.exe"):
                return False

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
                return False

        return True
