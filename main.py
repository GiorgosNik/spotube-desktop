import spotipy
from pydub import AudioSegment
from youtube_dl import YoutubeDL
import os
from youtubesearchpython import VideosSearch
from spotipy.oauth2 import SpotifyClientCredentials
import eyed3
import requests
import shutil
import random

# Set the Spotify API Keys
CLIENT_ID = 'ff55dcadd44e4cb0819ebe5be80ab687'
CLIENT_SECRET = '5539f7392ae94dd5b3dfc1d57381303a'

# Set the downloader
audio_downloader = YoutubeDL({'format': 'bestaudio'})

# Auth with the Spotify Framework
auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)

# Set up the folder for the songs
if not os.path.isdir('./Songs'):
    os.mkdir('./Songs')
else:
    os.rename('./Songs', './OldSongs' + str(random.randrange(100)))
    os.mkdir('./Songs')

# Get data for every song in the playlist
playlistToGet = sp.playlist('https://open.spotify.com/playlist/0g7eTKPSN1IarlunWjnITk?si=25d79d887fa44775')
for item in playlistToGet['tracks']['items']:
    song = item['track']
    cover_art = song['album']['images'][0]['url']
    artistList = ""
    for artist in song['artists']:
        if artistList != "":
            artistList += ", "
        artistList += (artist['name'])
    # print(song.keys())
    # Format the song data
    year = song['album']['release_date'].replace("-", " ").split()[0]
    name = song['name']
    artist = artistList
    album = song['album']['name']
    duration = int(song['duration_ms'])
    print("Searching for Name: ",name)
    # Search for the best candidate
    minDifference = duration
    videoSearch = VideosSearch(name + " " + artist, limit=3)
    for searchItem in videoSearch.result()['result']:
        durationStr = searchItem['duration'].replace(":", " ").split()
        durationInt = int(durationStr[0]) * 60000 + int(durationStr[1]) * 1000
        if abs(durationInt - duration) < minDifference:
            minDifference = abs(durationInt - duration)
            link = searchItem['link']
    print(name, artist, album, year, link)

    # Try to download the song
    try:
        URL = link
        text = audio_downloader.extract_info(URL)
        filename = text['title'] + "-" + text["id"] + ".webm"
    except Exception:
        print("Couldn\'t download the audio")
    filename = filename.replace('"', "'")
    print(filename)
    webm_audio = AudioSegment.from_file(filename, format="webm")
    webm_audio.export(name + ".mp3", format="mp3")
    os.remove(filename)

    # Get the Cover Art
    image_url = cover_art
    filename = 'cover_photo.jpg'
    r = requests.get(image_url, stream=True)
    if r.status_code == 200:
        r.raw.decode_content = True
        with open(filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
        print('Image successfully Downloaded: ', filename)
    else:
        print('Image Couldn\'t be retrieved')

    # Edit the ID3 Tags
    audioFile = eyed3.load(name + '.mp3')
    if audioFile.tag is None:
        audioFile.initTag()

    audioFile.tag.images.set(3, open('cover_photo.jpg', 'rb').read(), 'image/jpeg')
    audioFile.tag.artist = artist
    audioFile.tag.title = name
    audioFile.tag.album = album
    audioFile.tag.year = year
    audioFile.tag.save()

    shutil.move('./' + name + '.mp3', './Songs/' + name + '.mp3')
