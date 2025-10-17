import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timezone
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

def load_artist_ids():
    try:
        with open(config.ARTISTS_FILE, 'r') as f:
            return [id.strip() for id in f.read().split(',') if id.strip()]
    except FileNotFoundError:
        print("Artist file not found. Run extract_artists.py first.")
        return []

def load_processed_albums():
    try:
        with open(config.PROCESSED_ALBUMS_FILE, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def save_processed_album(album_id):
    with open(config.PROCESSED_ALBUMS_FILE, 'a') as f:
        f.write(f"{album_id}\n")

def check_new_releases():
    sp = get_spotify_client()
    artist_ids = load_artist_ids()
    if not artist_ids:
        return
    today = datetime.now(timezone.utc).date()
    processed_albums = load_processed_albums()
    new_tracks = []
    newly_processed = []

    for artist_id in artist_ids:
        try:
            albums = sp.artist_albums(artist_id, album_type='album,single', limit=10)
            for album in albums.get('items', []):
                album_id = album['id']
                if album_id in processed_albums:
                    continue
                release_date_str = album['release_date']
                release_date = datetime.fromisoformat(release_date_str).date()
                if release_date == today:
                    tracks = sp.album_tracks(album_id).get('items', [])
                    for t in tracks:
                        if t['uri'] not in new_tracks:
                            new_tracks.append(t['uri'])
                    newly_processed.append(album_id)
        except Exception as e:
            print(f"Error checking artist {artist_id}: {e}")
            continue

    if new_tracks:
        for i in range(0, len(new_tracks), 100):
            sp.playlist_add_items(config.TARGET_PLAYLIST_ID, new_tracks[i:i+100])
        for album_id in newly_processed:
            save_processed_album(album_id)
        print(f"Added {len(new_tracks)} new tracks to playlist.")

if __name__ == '__main__':
    check_new_releases()
