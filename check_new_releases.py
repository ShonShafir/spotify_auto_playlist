import time
from datetime import datetime, timezone, timedelta
from spotipy.exceptions import SpotifyException
import config
from auth_setup import get_spotify_client

# === Helper to handle rate limit ===
def safe_spotify_call(func, *args, **kwargs):
    """Wrap Spotify calls to handle 429 errors (Too Many Requests)."""
    while True:
        try:
            return func(*args, **kwargs)
        except SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get("Retry-After", 5))
                print(f"⚠️ Rate limited. Retrying after {retry_after} seconds...")
                time.sleep(retry_after + 1)
            else:
                raise e

# === Date parser ===
def parse_spotify_date(date_str, precision):
    if precision == 'year':
        dt = datetime(int(date_str), 1, 1)
    elif precision == 'month':
        year, month = map(int, date_str.split('-'))
        dt = datetime(year, month, 1)
    else:
        dt = datetime.fromisoformat(date_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

# === File handling ===
def load_artist_ids():
    try:
        with open(config.ARTISTS_FILE, 'r') as f:
            return [x.strip() for x in f.read().split(',') if x.strip()]
    except FileNotFoundError:
        print("Artist file not found.")
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

# === Main logic ===
def check_new_releases(batch_size=20, delay_between_batches=15):
    """
    batch_size: number of artists to process in one go
    delay_between_batches: wait time (in seconds) after each batch
    """
    sp = get_spotify_client()
    artist_ids = load_artist_ids()
    if not artist_ids:
        return

    threshold = datetime.now(timezone.utc) - timedelta(days=config.DAYS_THRESHOLD)
    processed_albums = load_processed_albums()
    new_tracks = []

    total_artists = len(artist_ids)
    print(f"🎧 Checking {total_artists} artists in batches of {batch_size}...")

    # Split artist IDs into batches
    for start in range(0, total_artists, batch_size):
        batch = artist_ids[start:start + batch_size]
        print(f"\n🔹 Processing batch {start // batch_size + 1}/{-(-total_artists // batch_size)} ({len(batch)} artists)")

        for artist_id in batch:
            try:
                albums = safe_spotify_call(sp.artist_albums, artist_id, album_type='album,single', limit=10)
                for album in albums['items']:
                    if album['id'] in processed_albums:
                        continue

                    release_date = parse_spotify_date(
                        album['release_date'],
                        album.get('release_date_precision', 'day')
                    )
                    if release_date >= threshold:
                        tracks = safe_spotify_call(sp.album_tracks, album['id'])['items']
                        for track in tracks:
                            track_name = track['name']
                            artists = ', '.join(a['name'] for a in track['artists'])
                            print(f"🎵 Found new track: {track_name} — {artists}")
                            new_tracks.append(track['uri'])
                        save_processed_album(album['id'])
            except Exception as e:
                print(f"Error with artist {artist_id}: {e}")
                continue

        print(f"⏸ Waiting {delay_between_batches}s before next batch...")
        time.sleep(delay_between_batches)

    # Add new tracks to playlist in groups of 100
    if new_tracks:
        for i in range(0, len(new_tracks), 100):
            safe_spotify_call(sp.playlist_add_items, config.TARGET_PLAYLIST_ID, new_tracks[i:i + 100])
        print(f"\n✅ Added {len(new_tracks)} new tracks to playlist!")
    else:
        print("\nNo new tracks found.")
        
