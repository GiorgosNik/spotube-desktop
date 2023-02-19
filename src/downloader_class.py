import src.utils as utils
import threading
import queue
import src.downloader_utils as downloader_utils


class downloader:
    def __init__(self):
        # Initialise the tracking values
        self.progress = 0
        self.total = None
        self.current_song = None
        self.eta = None
        self.thread = None

        # Set the channel that will handle the messages from the worker
        self.channel = queue.Queue()

        # Set the channel that will handle the messages from the worker
        self.termination_channel = queue.Queue()

        # Perform authentication for LyricsGenius and Spotify APIs
        self.tokens = utils.auth_handler()

    def start_downloader(self, link):
        # Create a new thread to handle the download
        self.thread = threading.Thread(
            target=downloader_utils.download_playlist,
            args=[link, self.tokens, self.channel, self.termination_channel],
        ).start()

    def stop_downloader(self):
        self.termination_channel.put(downloader_utils.EXIT)

        if self.thread is not None:
            self.thread.join()

    def validate_playlist_url(self, playlist_url):
        try:
            self.tokens["spotify"].playlist_tracks(playlist_url)
        except Exception:
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
