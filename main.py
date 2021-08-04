import spotipy
from pydub import AudioSegment
from youtube_dl import YoutubeDL
import os
import glob
import re
from youtubesearchpython import VideosSearch
from spotipy.oauth2 import SpotifyClientCredentials
import eyed3
import requests
import shutil
import lyricsgenius
import random
import time


def create_folder():
    if not os.path.isdir('./Songs'):
        os.mkdir('./Songs')
    else:
        os.rename('./Songs', './OldSongs' + str(random.randrange(100)))
        os.mkdir('./Songs')


def get_lyrics(nameSearch, artistSearch, genius_obj):
    sep1 = 'ft.'
    sep2 = 'feat'
    sep3 = '(feat'
    sep4 = '(ft.'
    sep5 = '(feat.'
    name_search = nameSearch.split(sep1, 1)[0]
    name_search = name_search.split(sep2, 1)[0]
    name_search = name_search.split(sep3, 1)[0]
    name_search = name_search.split(sep4, 1)[0]
    name_search = name_search.split(sep5, 1)[0]
    genius_song = genius_obj.search_song(name_search, artistSearch)
    formatted_lyrics = genius_song.lyrics.rsplit(' ', 1)[0].replace("EmbedShare", '')
    formatted_lyrics = formatted_lyrics.rsplit(' ', 1)[0] + ''.join(
        [i for i in formatted_lyrics.rsplit(' ', 1)[1] if not i.isdigit()])
    print("Got Lyrics:")
    print(formatted_lyrics)
    return formatted_lyrics


def set_tags(song_info, genius_obj):
    audio_file = eyed3.load(song_info['name'] + '.mp3')
    if audio_file.tag is None:
        audio_file.initTag()
    audio_file.tag.images.set(3, open('cover_photo.jpg', 'rb').read(), 'image/jpeg')
    audio_file.tag.artist = song_info['artist']
    audio_file.tag.title = song_info['name']
    audio_file.tag.album = song_info['album']
    audio_file.tag.year = song_info['year']
    try:
        audio_file.tag.lyrics.set(get_lyrics(song_info['name'], song_info['artist'], genius_obj))
    except Exception:
        pass
    audio_file.tag.save()


def format_artists(artist_list):
    artist_combined = ""
    for artist_in_list in artist_list:
        if artist_combined != "":
            artist_combined += ", "
        artist_combined += (artist_in_list['name'])
    return artist_combined


def get_best_link(song_info):
    min_difference = song_info['duration']
    video_search = VideosSearch(song_info['name'] + " " + song_info['artist'], limit=3)
    for searchItem in video_search.result()['result']:
        duration_str = searchItem['duration'].replace(":", " ").split()
        duration_int = int(duration_str[0]) * 60000 + int(duration_str[1]) * 1000
        if abs(duration_int - duration) < min_difference:
            min_difference = abs(duration_int - duration)
            best_link = searchItem['link']
    print(song_info['name'], song_info['artist'], song_info['album'], song_info['year'], best_link)
    return best_link


def get_youtube(given_link, song_info):
    try:
        audio_downloader.extract_info(given_link)
    except Exception:
        print("Couldn\'t download the audio")
    list_of_files = glob.glob('./*.webm')  # * means all if need specific format then *.csv
    latest_file = max(list_of_files, key=os.path.getctime)
    print(latest_file)
    try:
        os.rename(latest_file, "import.webm")
        webm_audio = AudioSegment.from_file('import.webm', format="webm")
        webm_audio.export(song_info['name'] + ".mp3", format="mp3")
        os.remove('./import.webm')
    except Exception:
        os.rename(latest_file, "import.m4a")
        webm_audio = AudioSegment.from_file('import.webm', format="m4a")
        webm_audio.export(song_info['name'] + ".mp3", format="mp3")
        os.remove('./import.m4a')
    # Get the Cover Art
    image_url = song_info['url']
    filename = 'cover_photo.jpg'
    r = requests.get(image_url, stream=True)
    if r.status_code == 200:
        r.raw.decode_content = True
        with open(filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
        print('Image successfully Downloaded: ', filename)
    else:
        print('Image Couldn\'t be retrieved')


# Set the Spotify API Keys
CLIENT_ID = 'ff55dcadd44e4cb0819ebe5be80ab687'
CLIENT_SECRET = '5539f7392ae94dd5b3dfc1d57381303a'

# Set the Lyrics Genius API Keys
genius = lyricsgenius.Genius('5dRV7gMtFLgnlF632ZzqZutSsvPC0IWyFUJ1W8pWHj185RAMFgR4FtX76ckFDjFZ')

# Set the downloader
audio_downloader = YoutubeDL({'format': 'bestaudio'})

# Auth with the Spotify Framework
auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)

# Set up the folder for the songs
create_folder()

# Get data for every song in the playlist with link:
playlistToGet = sp.playlist('https://open.spotify.com/playlist/0g7eTKPSN1IarlunWjnITk?si=5bf57f257415482c')

for item in playlistToGet['tracks']['items']:
    # Format the song data
    song = item['track']
    cover_art = song['album']['images'][0]['url']
    year = song['album']['release_date'].replace("-", " ").split()[0]
    name = song['name']
    artist = format_artists(song['artists'])
    album = song['album']['name']
    duration = int(song['duration_ms'])
    songInfo = {'name': name, 'artist': artist, 'album': album, 'year': year, 'duration': duration, 'url': cover_art}
    print("Searching for Name: ", name)

    # Search for the best candidate
    link = get_best_link(songInfo)

    # Try to download the song
    get_youtube(link, songInfo)

    # Edit the ID3 Tags
    set_tags(songInfo, genius)

    shutil.move('./' + name + '.mp3', './Songs/' + name + '.mp3')
