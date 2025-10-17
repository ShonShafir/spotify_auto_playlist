import os
from dotenv import load_dotenv
load_dotenv()
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')
PLAYLIST_URLS = [
    'https://open.spotify.com/playlist/47dNMRY60zT6RdqsIxjhLa',
    'https://open.spotify.com/playlist/0G1Vsob3SIc9nTGj12hxfo'
]
TARGET_PLAYLIST_ID = '47dNMRY60zT6RdqsIxjhLa'
ARTISTS_FILE = 'artists_id.txt'
PROCESSED_ALBUMS_FILE = 'processed_albums.txt'
