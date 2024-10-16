import os
import glob
from youtubesearchpython import VideosSearch
import eyed3
import requests
import shutil
from tqdm import tqdm
import spotipy
from yt_dlp import YoutubeDL
from spotipy.oauth2 import SpotifyClientCredentials
import lyricsgenius
from zipfile import ZipFile
import subprocess
import logging

# Setup logging configuration
logging.basicConfig(filename='download_errors.log', level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')

EXIT = "EXIT"
DEFAULT_DIR = "./Songs"


def get_lyrics(name_search, artist_search, genius_obj):
    sep1 = "ft."
    sep2 = "feat"
    sep3 = "(feat"
    sep4 = "(ft."
    sep5 = "(feat."
    name_search = name_search.split(sep1)[0]
    name_search = name_search.split(sep2)[0]
    name_search = name_search.split(sep3)[0]
    name_search = name_search.split(sep4)[0]
    name_search = name_search.split(sep5)[0]
    genius_song = genius_obj.search_song(name_search, artist_search)
    formatted_lyrics = genius_song.lyrics.rsplit(" ", 1)[0].replace("EmbedShare", "")
    formatted_lyrics = formatted_lyrics.rsplit(" ", 1)[0] + "".join(
        [i for i in formatted_lyrics.rsplit(" ", 1)[1] if not i.isdigit()]
    )
    return formatted_lyrics


def set_tags(song_info, genius_obj, directory=DEFAULT_DIR):
    audio_file = eyed3.load(directory + "/" + song_info["name"] + ".mp3")

    if audio_file.tag is None:
        audio_file.initTag()

    audio_file.tag.images.set(3, open("cover_photo.jpg", "rb").read(), "image/jpeg")
    formatted_artist_string = song_info["artist"].replace(",", ";")
    audio_file.tag.artist = formatted_artist_string
    audio_file.tag.title = song_info["name"]
    audio_file.tag.album = song_info["album"]
    audio_file.tag.year = song_info["year"]

    try:
        audio_file.tag.lyrics.set(get_lyrics(song_info["name"], song_info["artist"], genius_obj))
    except Exception:
        pass

    audio_file.tag.save()
    os.remove("./cover_photo.jpg")


def format_artists(artist_list):
    artist_combined = ""

    for artist_in_list in artist_list:
        if artist_combined != "":
            artist_combined += ", "
        artist_combined += artist_in_list["name"]

    return artist_combined


def get_link(song_info):
    try:
        min_difference = song_info["duration"]
        video_search = VideosSearch(song_info["name"] + " " + song_info["artist"], limit=3)
        best_link = None

        for search_result in video_search.result()["result"]:
            duration_str = search_result["duration"].replace(":", " ").split()
            duration_int = int(duration_str[0]) * 60000 + int(duration_str[1]) * 1000

            if abs(duration_int - song_info["duration"]) < min_difference:
                min_difference = abs(duration_int - song_info["duration"])
                best_link = search_result["link"]

        if best_link is None:
            best_link = ""

    except Exception:
        best_link = ""

    return best_link


def download_image(song_info):
    # Get the Cover Art
    image_url = song_info["url"]
    filename = "cover_photo.jpg"
    image_request = requests.get(image_url, stream=True)

    if image_request.status_code == 200:
        image_request.raw.decode_content = True

        with open(filename, "wb") as f:
            shutil.copyfileobj(image_request.raw, f)


def download_song(given_link, song_info, downloader, directory=DEFAULT_DIR):
    attempts = 0

    while attempts <= 3:
        try:
            downloader.extract_info(given_link)
            list_of_files = glob.glob(directory + "/*.mp3")
            latest_file = max(list_of_files, key=os.path.getctime)

            # Overwrite the file, if it exists
            if os.path.exists(directory + "/" + song_info["name"] + ".mp3"):
                os.remove(directory + "/" + song_info["name"] + ".mp3")
            os.rename(latest_file, directory + "/" + song_info["name"] + ".mp3")
            return

        except Exception as e:
            attempts += 1
            continue


def get_songs(playlist_link, spotify_api):
    results = spotify_api.playlist_tracks(playlist_link)
    songs = results["items"]

    while results["next"]:
        results = spotify_api.next(results)
        songs.extend(results["items"])

    return songs


# Handle message delivery in UI mode
def send_message(channel, type, contents):
    if channel is not None:
        channel.put({"type": type, "contents": contents})


def get_elapsed(progressbar):
    elapsed = progressbar.format_dict["elapsed"]
    return elapsed


def get_eta(progressbar):
    rate = progressbar.format_dict["rate"]
    remaining = (progressbar.total - progressbar.n) / rate if rate and progressbar.total else 0
    return remaining


# Return formatted song data in a dictionary
def format_song_data(song):
    song = song["track"]
    cover_art = song["album"]["images"][0]["url"]
    year = song["album"]["release_date"].replace("-", " ").split()[0]
    name = song["name"]
    artist = format_artists(song["artists"])
    album = song["album"]["name"]
    duration = int(song["duration_ms"])
    info_dict = {
        "name": name,
        "artist": artist,
        "album": album,
        "year": year,
        "duration": duration,
        "url": cover_art,
    }

    return info_dict


def download_playlist(playlist_url, tokens, channel, termination_channel, directory=DEFAULT_DIR):
    # Set up the folder for the songs
    if not os.path.isdir(directory):
        os.mkdir(directory)

    audio_downloader = create_audio_downloader(directory)

    songs = get_songs(playlist_url, tokens["spotify"])

    # Set the tqdm progress bar
    playlist_size = len(songs)
    playlist_progress = tqdm(total=playlist_size, desc="Playlist Progress", position=0, leave=False)

    for song in songs:
        # Set song progress bar
        song_progress = tqdm(total=4, desc=song["track"]["name"], position=1, leave=False)

        # Retrieve Formatted Song Data
        song_progress.set_description(song_progress.desc + ": Formatting Information")
        song_progress.update(n=1)
        info_dict = format_song_data(song)

        # Download Cover Art, to preview to UI
        download_image(info_dict)

        # Send Message to UI
        send_message(
            channel,
            type="song_title",
            contents="{} by {}".format(info_dict["name"], info_dict["artist"].split(",")[0]),
        )

        # Search for the best candidate
        song_progress.set_description(info_dict["name"] + ": Selecting Best Link")
        song_progress.update(n=1)
        link = get_link(info_dict)
        if link == "":
            logging.error(f"Failed to download {info_dict['name']} after 3 attempts. Error: Could not find link")
            continue

        # Download the song
        try:
            song_progress.set_description(info_dict["name"] + ": Downloading Song")
            song_progress.update(n=1)
            download_song(link, info_dict, audio_downloader, directory)

            # Edit the ID3 Tags
            song_progress.set_description(info_dict["name"] + ": Setting Tags")
            song_progress.update(n=1)
            set_tags(info_dict, tokens["genius"], directory)

            # Move to the designated folder
            song_progress.set_description(info_dict["name"] + ": Moving to designated folder")
            song_progress.update(n=1)

        except Exception as e:
            logging.error(f"Failed to download {info_dict['name']} after 3 attempts. Error: {str(e)}")
            continue
        song_progress.close()

        # Check for termination message
        if not termination_channel.empty():
            message = termination_channel.get()
            if message == EXIT:
                exit()

        # Update tqdm progress bar
        playlist_progress.update(n=1)
        send_message(channel, type="progress", contents=[playlist_progress.n, playlist_progress.total])

        elapsed = get_elapsed(playlist_progress)
        eta = get_eta(playlist_progress)
        send_message(channel, type="eta_update", contents=[elapsed, eta])

    playlist_progress.close()

    print("Download Complete")
    send_message(channel, type="download_complete", contents=[])


def auth_handler(client_id, client_secret, genius):
    genius_auth = lyricsgenius.Genius(
        genius,
        verbose=False,
    )
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    spotify_auth = spotipy.Spotify(auth_manager=auth_manager)

    return {"genius": genius_auth, "spotify": spotify_auth}


# Create downloader object, pass options
def create_audio_downloader(directory=DEFAULT_DIR):
    audio_downloader = YoutubeDL(
        {
            "format": "bestaudio",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "outtmpl": directory + "/downloaded_song.%(ext)s",
            "quiet": "true",
            "no_warnings": "true",
            "noprogress": "true",
        }
    )
    return audio_downloader


# Setup ffmpeg if not present
def first_time_setup():
    if os.name == "nt":
        # Windows
        if not os.path.exists("./ffmpeg.exe"):
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