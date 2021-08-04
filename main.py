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
if not os.path.isdir('./Songs'):
    os.mkdir('./Songs')
else:
    os.rename('./Songs', './OldSongs' + str(random.randrange(100)))
    os.mkdir('./Songs')

# Get data for every song in the playlist
playlistToGet = sp.playlist('https://open.spotify.com/playlist/0g7eTKPSN1IarlunWjnITk?si=5bf57f257415482c')
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
    print("Searching for Name: ", name)
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
    time.sleep(5)
    list_of_files = glob.glob('./*.webm')  # * means all if need specific format then *.csv
    latest_file = max(list_of_files, key=os.path.getctime)
    print(latest_file)
    while True:
        try:
            os.rename(latest_file, "import.webm")
            webm_audio = AudioSegment.from_file('import.webm', format="webm")
            webm_audio.export(name + ".mp3", format="mp3")
            os.remove('./import.webm')
            break
        except Exception:
            os.rename(latest_file, "import.m4a")
            webm_audio = AudioSegment.from_file('import.webm', format="m4a")
            webm_audio.export(name + ".mp3", format="mp3")
            os.remove('./import.m4a')
            break


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

    try:
        nameSearch = re.sub("[\(\[].*?[\)\]]", "", name)
        nameSearch = str(nameSearch)
        sep1 = 'ft.'
        sep2 = 'feat'
        nameSearch = nameSearch.split(sep1, 1)[0]
        nameSearch = nameSearch.split(sep2, 1)[0]
        geniusSong = genius.search_song(nameSearch, artist)
        formatedLyrics = geniusSong.lyrics.rsplit(' ', 1)[0].replace("EmbedShare", '')
        formatedLyrics = formatedLyrics.rsplit(' ', 1)[0] + ''.join(
            [i for i in formatedLyrics.rsplit(' ', 1)[1] if not i.isdigit()])
        print("Got Lyrics:")
        print(formatedLyrics)
        audioFile.tag.lyrics.set(formatedLyrics)
    except Exception:
        continue
    audioFile.tag.save()
    shutil.move('./' + name + '.mp3', './Songs/' + name + '.mp3')
