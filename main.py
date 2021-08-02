import spotipy
from youtubesearchpython import VideosSearch
from spotipy.oauth2 import SpotifyClientCredentials

# Set the Spotify API Keys
CLIENT_ID = 'ff55dcadd44e4cb0819ebe5be80ab687'
CLIENT_SECRET = '5539f7392ae94dd5b3dfc1d57381303a'

# Auth with the Spotify Framework
auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)

# Get data for every song in the playlist
playlistToGet = sp.playlist('https://open.spotify.com/playlist/2tUdm8UGbwNQzxOtF2pHiu?si=3e63f30913d24542')
for item in playlistToGet['tracks']['items']:
    song = item['track']
    # print(song['album']['images'][0])
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

    # Search for the best candidate
    minDifference = duration
    videoSearch = VideosSearch(name + " " + artist, limit=5)
    for searchItem in videoSearch.result()['result']:
        durationStr = searchItem['duration'].replace(":", " ").split()
        durationInt = int(durationStr[0]) * 60000 + int(durationStr[1]) * 1000
        if abs(durationInt - duration) < minDifference:
            duration = durationInt
            link = searchItem['link']
            
    print(name, artist, album, year, link)
