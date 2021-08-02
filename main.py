import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Set the Spotify API Keys
CLIENT_ID = 'ff55dcadd44e4cb0819ebe5be80ab687'
CLIENT_SECRET = '5539f7392ae94dd5b3dfc1d57381303a'


# Auth with the Spotify Framework
auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)


# Get data for every song in the playlist
playlistToGet = sp.playlist('https://open.spotify.com/playlist/6TGxmQCgNUC3Q4OvmFO3Sd?si=fb0e150fa3ed4378')
for item in playlistToGet['tracks']['items']:
    song = item['track']
    print(song['album']['images'][0])
    artistList = []
    for artist in song['artists']:
        artistList.append(artist['name'])
    print(song['name'], artistList, song['album']['name'])
