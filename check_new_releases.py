import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timezone, timedelta
import config

def get_spotify_client():
    sp_oauth = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri="http://127.0.0.1:8888/callback",
        scope="playlist-modify-public playlist-modify-private",
        cache_path=".spotify_cache",
        show_dialog=False
    )

    # Use refresh token from GitHub secrets
    token_info = sp_oauth.refresh_access_token(os.environ["SPOTIFY_REFRESH_TOKEN"])
    sp = spotipy.Spotify(auth=token_info['access_token'])
    return sp

def load_artist_ids():
    try:
        with open(config.ARTISTS_FILE, 'r') as f:
            return [x.strip() for x in f.read().split(',') if x.strip()]
    except FileNotFoundError:
        print("Artist file not found. Run extract_artists first.")
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

    threshold = datetime.now(timezone.utc) - timedelta(days=config.DAYS_THRESHOLD)
    processed_albums = load_processed_albums()
    new_tracks = []

    for artist_id in artist_ids:
        try:
            albums = sp.artist_albums(artist_id, album_type='album,single', limit=10)
            for album in albums['items']:
                if album['id'] in processed_albums:
                    continue
                release_date = datetime.fromisoformat(album['release_date'].replace('Z', '+00:00'))
                if release_date >= threshold:
                    for track in sp.album_tracks(album['id'])['items']:
                        new_tracks.append(track['uri'])
                    save_processed_album(album['id'])
        except Exception as e:
            print(f"Error with artist {artist_id}: {e}")
            continue

    if new_tracks:
        for i in range(0, len(new_tracks), 100):
            sp.playlist_add_items(config.TARGET_PLAYLIST_ID, new_tracks[i:i+100])
        print(f"Added {len(new_tracks)} new tracks to playlist!")
    else:
        print("No new tracks found.")

if __name__ == "__main__":
    check_new_releases()
