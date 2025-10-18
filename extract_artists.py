import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import config
import os

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
    client_credentials_manager = SpotifyClientCredentials(
        client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
        client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET")
    )
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    artist_ids = set()
    for playlist_url in config.PLAYLIST_URLS:
        playlist_id = extract_playlist_id(playlist_url)
        tracks = get_all_tracks(sp, playlist_id)
        for item in tracks:
            if item['track'] and item['track']['artists']:
                for artist in item['track']['artists']:
                    artist_ids.add(artist['id'])

    with open(config.ARTISTS_FILE, 'w') as f:
        f.write(', '.join(artist_ids))

    print(f"Saved {len(artist_ids)} unique artist IDs to {config.ARTISTS_FILE}")
    return len(artist_ids)
