import spotipy
from spotipy.oauth2 import SpotifyOAuth
import config
import os
os.environ['SPOTIPY_CACHE'] = '.spotify_cache'

def get_spotify_client():
    scope = "playlist-modify-public playlist-modify-private"
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=config.SPOTIFY_CLIENT_ID,
        client_secret=config.SPOTIFY_CLIENT_SECRET,
        redirect_uri=config.SPOTIFY_REDIRECT_URI,
        scope=scope,
        cache_path=".spotify_cache",
        open_browser=False
    ))
    return sp

def extract_playlist_id(url):
    if 'playlist/' in url:
        return url.split('playlist/')[1].split('?')[0]
    return url

def get_all_tracks(sp, playlist_id):
    tracks = []
    results = sp.playlist_tracks(playlist_id)
    tracks.extend(results['items'])
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return tracks

def extract_artist_ids():
    sp = get_spotify_client()
    artist_ids = set()
    for url in config.PLAYLIST_URLS:
        playlist_id = extract_playlist_id(url)
        tracks = get_all_tracks(sp, playlist_id)
        for item in tracks:
            if item['track'] and item['track']['artists']:
                for artist in item['track']['artists']:
                    artist_ids.add(artist['id'])
    artist_ids = [aid for aid in artist_ids if aid]
    with open(config.ARTISTS_FILE, 'w') as f:
        f.write(', '.join(artist_ids))
    print(f"Saved {len(artist_ids)} artist IDs to {config.ARTISTS_FILE}")
    return len(artist_ids)

if __name__ == '__main__':
    extract_artist_ids()
