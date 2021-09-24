import spotipy
from youtube_dl import YoutubeDL
import os
import glob
from youtubesearchpython import VideosSearch
from spotipy.oauth2 import SpotifyClientCredentials
import eyed3
import requests
import shutil
import lyricsgenius
import random
import tkinter.filedialog
import threading
import time
from tkinter import ttk
from zipfile import ZipFile
from tkinter import *
from ctypes import windll


#   BIG 'https://open.spotify.com/playlist/3O7qs0truT99VZBP6iFiaS?si=8d35f6e96fbe4cca'
#   Small https://open.spotify.com/playlist/4Yp12s7QSNItjrY3kmiEhh?si=9e9aad3e7ee94346'

def create_folder():
    global folder_path
    if not os.path.isdir(folder_path + './Songs'):
        os.mkdir(folder_path + './Songs')
    else:
        os.rename(folder_path + './Songs', folder_path + './OldSongs' + str(random.randrange(100)))
        os.mkdir(folder_path + './Songs')


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
    os.remove('./cover_photo.jpg')


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
        if abs(duration_int - song_info['duration']) < min_difference:
            min_difference = abs(duration_int - song_info['duration'])
            best_link = searchItem['link']
    print(song_info['name'], song_info['artist'], song_info['album'], song_info['year'], best_link)
    return best_link


def get_youtube(given_link, song_info, downloader):
    attempts = 0
    while attempts <= 5:
        try:
            downloader.extract_info(given_link)
            list_of_files = glob.glob('./*.mp3')  # * means all if need specific format then *.csv
            latest_file = max(list_of_files, key=os.path.getctime)
            print(latest_file)
            os.rename(latest_file, song_info['name'] + ".mp3")
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
            return 0
        except Exception:
            print("Couldn\'t download the audio,trying again...")
            attempts += 1
            continue
        raise Exception("Could not Download")


def download_playlist(playlist_url, dir_to_save='./'):
    audio_downloader = YoutubeDL({'format': 'bestaudio', 'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }]})
    if dir_to_save == '':
        dir_to_save = '.'
    # Set up the folder for the songs
    create_folder()
    global progress
    i = 0
    # TODO Make this a function
    results = sp.playlist_tracks(playlist_url)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    playlist_to_get = sp.playlist(playlist_url)

    for item in tracks:
        # Format the song data
        song = item['track']
        cover_art = song['album']['images'][0]['url']
        year = song['album']['release_date'].replace("-", " ").split()[0]
        name = song['name']
        artist = format_artists(song['artists'])
        album = song['album']['name']
        duration = int(song['duration_ms'])
        songInfo = {'name': name, 'artist': artist, 'album': album, 'year': year, 'duration': duration,
                    'url': cover_art}
        print("Searching for Name: ", name)

        # Search for the best candidate
        link = get_best_link(songInfo)

        # Try to download the song
        try:
            get_youtube(link, songInfo, audio_downloader)
            # Edit the ID3 Tags
            set_tags(songInfo, genius)

            # Move to the designated folder
            start_pos = './' + name + '.mp3'
            end_pos = dir_to_save + '/Songs/' + name + '.mp3'
            print(start_pos)
            print(end_pos)
            shutil.move('./' + name + '.mp3', dir_to_save + '/Songs/' + name + '.mp3')
            i += 1
            progress = i / len(playlist_to_get['tracks']['items']) * 100
        except Exception:
            continue
    i += 1
    progress = i / len(playlist_to_get['tracks']['items']) * 100


def browse_button():
    global folder_path
    filename = tkinter.filedialog.askdirectory()
    print(filename)
    folder_path = filename


def download_button_click(url_entry):
    global folder_path
    global progress
    given_url = url_entry.get()
    process_thread = threading.Thread(target=download_playlist, args=(given_url, folder_path,))
    process_thread.start()


def auth_handler():
    # Set the Lyrics Genius API Keys
    genius_auth = lyricsgenius.Genius("5dRV7gMtFLgnlF632ZzqZutSsvPC0IWyFUJ1W8pWHj185RAMFgR4FtX76ckFDjFZ")

    # Auth with the Spotify Framework
    client_id = "ff55dcadd44e4cb0819ebe5be80ab687"
    client_secret = '5539f7392ae94dd5b3dfc1d57381303a'
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    spotify_auth = spotipy.Spotify(auth_manager=auth_manager)
    return {'genius': genius_auth, 'spotify': spotify_auth}


def first_time_setup():
    # Unzip ffmpeg if not present
    if not os.path.exists('./ffmpeg.exe'):
        with ZipFile('ffmpeg.zip', 'r') as zipObj:
            # Extract all the contents of zip file in current directory
            zipObj.extractall()


def set_app_window(root):
    GWL_EXSTYLE = -20
    WS_EX_APPWINDOW = 0x00040000
    WS_EX_TOOLWINDOW = 0x00000080
    hwnd = windll.user32.GetParent(root.winfo_id())
    style = windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    style = style & ~WS_EX_TOOLWINDOW
    style = style | WS_EX_APPWINDOW
    res = windll.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)
    # re-assert the new window style
    root.withdraw()
    root.after(10, root.deiconify)


def save_last_click_pos(event):
    global lastClickX, lastClickY
    lastClickX = event.x
    lastClickY = event.y


def open_folder():
    global folder_path
    if folder_path == "":
        if os.path.exists('./Songs'):
            folder_path = './Songs'
    else:
        if os.path.exists(folder_path + '/Songs'):
            folder_path = folder_path + '/Songs'

    path = os.path.realpath(folder_path)
    os.startfile(path)


class UI:
    def __init__(self, master):
        self.master = master
        master.overrideredirect(True)  # turns off title bar, geometry
        master.geometry('500x190+700+400')  # set new geometry
        master.attributes('-topmost', False)
        master.call("source", "forest-dark.tcl")
        ttk.Style().theme_use('forest-dark')
        self.custom_title_bar()
        self.spawn_widgets()

        self.master.after(10, set_app_window, self.master)

    def custom_title_bar(self):
        # Create the title bar and Close-Button
        self.title_bar = Frame(self.master, bg='#242424', relief='groove', bd=2, highlightthickness=0)
        self.title_bar.config(borderwidth=0, highlightthickness=0)
        self.close_button = Button(self.title_bar, text='X', command=self.master.destroy, bg="#242424", padx=2, pady=2,
                                   activebackground='red',
                                   bd=0, font="bold", fg='white', highlightthickness=0)
        # Create a window
        self.window = Canvas(self.master, bg='#2e2e2e', highlightthickness=0)

        # Pack the above widgets
        self.title_bar.pack(expand=1, fill=X)
        self.close_button.pack(side=RIGHT)
        self.window.pack(expand=1, fill=BOTH)
        self.title_bar.bind('<Button-1>', save_last_click_pos)
        self.title_bar.bind('<B1-Motion>', self.dragging)

    def spawn_widgets(self):
        self.E1 = ttk.Entry(self.master, width=50)
        self.window.create_window(120, 15, anchor='nw', window=self.E1)
        self.playlist_label = tkinter.Label(self.master, text="Link to Playlist")
        self.window.create_window(10, 20, anchor='nw', window=self.playlist_label)

        self.entryString = self.E1.get()

        self.v = tkinter.StringVar()

        self.select_folder = ttk.Button(self.master, text="Select folder", style='Accent.TButton',
                                        command=browse_button)
        self.window.create_window(170, 60, anchor='nw', window=self.select_folder)

        self.download_button = ttk.Button(self.master, text="Download", style='Accent.TButton',
                                          command=lambda: download_button_click(self.E1))
        self.window.create_window(280, 60, anchor='nw', window=self.download_button)

        self.install_button = ttk.Button(self.master, text="Install", style='Accent.TButton',
                                         command=first_time_setup)
        self.window.create_window(390, 60, anchor='nw', window=self.install_button)

        self.open_folder_button = ttk.Button(self.master, text="Open Folder", style='Accent.TButton',
                                             command=open_folder)
        self.window.create_window(60, 60, anchor='nw', window=self.open_folder_button)

        self.progress_label = ttk.Label(self.master, text="Progress:")
        self.window.create_window(10, 110, anchor='nw', window=self.progress_label)

        self.progress_bar = ttk.Progressbar(self.master, orient='horizontal', length=365, mode='determinate')
        self.window.create_window(120, 110, anchor='nw', window=self.progress_bar)

    def set_progress(self):
        global progress
        self.progress_bar['value'] = progress
        self.master.after(60, self.set_progress)

    def dragging(self, event):
        x, y = event.x - lastClickX + self.master.winfo_x(), event.y - lastClickY + self.master.winfo_y()
        self.master.geometry("+%s+%s" % (x, y))

    def spawn_message(self,given_message,given_title=None):
        self.mesagebox = tkinter.messagebox.showinfo(title=given_title, message=given_message)



# Global Definitions
folder_path = ''

# Set the downloader
tokens = auth_handler()
sp = tokens['spotify']
genius = tokens['genius']

# Set the progress to be used for the progressbar
progress = 0

# Used for the custom window
lastClickX = 0
lastClickY = 0

# Used by tkinter
# TODO fix this?
entryString = ""


def main():
    global entryString
    root = Tk()
    customUI = UI(root)

    entryString = customUI.E1.get()
    if not os.path.exists('./ffmpeg.exe'):
        customUI.spawn_message("This is your first time using Spotube, please click the install button")
    customUI.set_progress()
    root.after(10, set_app_window, root)
    root.mainloop()


if __name__ == "__main__":
    main()
