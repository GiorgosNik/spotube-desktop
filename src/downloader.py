import os
import glob
from youtubesearchpython import VideosSearch
import eyed3
import requests
import shutil
import src.utils as utils
from tqdm import tqdm
import threading


class downloader:
    @staticmethod
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

    @staticmethod
    def set_tags(song_info, genius_obj):
        audio_file = eyed3.load(song_info["name"] + ".mp3")

        if audio_file.tag is None:
            audio_file.initTag()

        audio_file.tag.images.set(3, open("cover_photo.jpg", "rb").read(), "image/jpeg")
        audio_file.tag.artist = song_info["artist"]
        audio_file.tag.title = song_info["name"]
        audio_file.tag.album = song_info["album"]
        audio_file.tag.year = song_info["year"]

        try:
            audio_file.tag.lyrics.set(
                downloader.get_lyrics(song_info["name"], song_info["artist"], genius_obj)
            )
        except Exception:
            pass

        audio_file.tag.save()
        os.remove("./cover_photo.jpg")

    @staticmethod
    def format_artists(artist_list):
        artist_combined = ""

        for artist_in_list in artist_list:
            if artist_combined != "":
                artist_combined += ", "
            artist_combined += artist_in_list["name"]

        return artist_combined

    @staticmethod
    def get_link(song_info):
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

        return best_link

    @staticmethod
    def download_image(song_info):
        # Get the Cover Art
        image_url = song_info["url"]
        filename = "cover_photo.jpg"
        image_request = requests.get(image_url, stream=True)

        if image_request.status_code == 200:
            image_request.raw.decode_content = True

            with open(filename, "wb") as f:
                shutil.copyfileobj(image_request.raw, f)

    @staticmethod
    def download_song(given_link, song_info, downloader):
        attempts = 0

        while attempts <= 3:
            try:
                downloader.extract_info(given_link)
                list_of_files = glob.glob("./*.mp3")
                latest_file = max(list_of_files, key=os.path.getctime)
                os.rename(latest_file, song_info["name"] + ".mp3")

                return

            except Exception as e:
                print(str(e))
                attempts += 1
                continue

    @staticmethod
    def get_songs(playlist_link, spotify_api):
        results = spotify_api.playlist_tracks(playlist_link)
        songs = results["items"]

        while results["next"]:
            results = spotify_api.next(results)
            songs.extend(results["items"])

        return songs

    # Handle message delivery in UI mode
    @staticmethod
    def send_message(channel, type, contents):
        if channel is not None:
            channel.put({"type": type, "contents": contents})

    @staticmethod
    def get_elapsed(progressbar):
        elapsed = progressbar.format_dict["elapsed"]
        return elapsed

    @staticmethod
    def get_eta(progressbar):
        rate = progressbar.format_dict["rate"]
        remaining = (progressbar.total - progressbar.n) / rate if rate and progressbar.total else 0
        return remaining

    # Return formatted song data in a dictionary
    @staticmethod
    def format_song_data(song):
        song = song["track"]
        cover_art = song["album"]["images"][0]["url"]
        year = song["album"]["release_date"].replace("-", " ").split()[0]
        name = song["name"]
        artist = downloader.format_artists(song["artists"])
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

    @staticmethod
    def download_playlist(playlist_url, tokens, channel=None, directory="./"):
        audio_downloader = utils.create_audio_downloader()

        # Set up the folder for the songs
        utils.create_folder(directory)

        songs = downloader.get_songs(playlist_url, tokens["spotify"])

        # Set the tqdm progress bar
        playlist_size = len(songs)
        playlist_progress = tqdm(total=playlist_size, desc="Playlist Progress", position=0, leave=False)

        for song in songs:
            # Set song progress bar
            song_progress = tqdm(total=5, desc=song["track"]["name"], position=1, leave=False)

            # Retrieve Formatted Song Data
            song_progress.set_description(song_progress.desc + ": Formatting Information")
            song_progress.update(n=1)
            info_dict = downloader.format_song_data(song)

            # Download Cover Art, to preview to UI
            downloader.download_image(info_dict)

            # Send Message to UI
            downloader.send_message(
                channel,
                type="song_title",
                contents="{} by {}".format(info_dict["name"], info_dict["artist"].split(",")[0]),
            )

            # Search for the best candidate
            song_progress.set_description(info_dict["name"] + ": Selecting Best Link")
            song_progress.update(n=1)
            link = downloader.get_link(info_dict)
            if link == "":
                continue

            # Download the song
            try:
                song_progress.set_description(info_dict["name"] + ": Downloading Song")
                song_progress.update(n=1)
                downloader.download_song(link, info_dict, audio_downloader)

                # Edit the ID3 Tags
                song_progress.set_description(info_dict["name"] + ": Setting Tags")
                song_progress.update(n=1)
                downloader.set_tags(info_dict, tokens["genius"])

                # Move to the designated folder
                song_progress.set_description(info_dict["name"] + ": Moving to designated folder")
                song_progress.update(n=1)
                shutil.move(
                    "./" + info_dict["name"] + ".mp3",
                    directory + "/Songs/" + info_dict["name"] + ".mp3",
                )

            except Exception:
                continue
            song_progress.close()

            # Update tqdm progress bar
            playlist_progress.update(n=1)
            downloader.send_message(
                channel, type="progress", contents=[playlist_progress.n, playlist_progress.total]
            )

            elapsed = downloader.get_elapsed(playlist_progress)
            eta = downloader.get_eta(playlist_progress)
            downloader.send_message(channel, type="eta_update", contents=[elapsed, eta])

        playlist_progress.close()

    @staticmethod
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

    @staticmethod
    def start_downloader(channel, link):
        # Perform authentication for LyricsGenius and Spotify APIs
        tokens = utils.auth_handler()

        # Create a new thread to handle the download
        threading.Thread(target=downloader.download_playlist, args=[link, tokens, channel]).start()
