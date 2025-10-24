import time
import logging
from datetime import datetime, timezone, timedelta
from spotipy.exceptions import SpotifyException
import config
from auth_setup import get_spotify_client

# === הגדרת לוגים למסך בלבד ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# === Helper to handle rate limit ===
def safe_spotify_call(func, *args, **kwargs):
    """Wrap Spotify calls to handle 429 errors (Too Many Requests)."""
    while True:
        try:
            return func(*args, **kwargs)
        except SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get("Retry-After", 5))
                log.warning(f"⚠️ Rate limited. Retrying after {retry_after} seconds...")
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
        log.error("Artist file not found.")
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
def check_new_releases(batch_size=20, delay_between_batches=15, delay_between_artists=0.5):
    sp = get_spotify_client()
    artist_ids = load_artist_ids()
    if not artist_ids:
        return

    threshold = datetime.now(timezone.utc) - timedelta(days=config.DAYS_THRESHOLD)
    processed_albums = load_processed_albums()
    new_tracks = []

    total_artists = len(artist_ids)
    log.info(f"🎧 Checking {total_artists} artists in batches of {batch_size}...")

    for start in range(0, total_artists, batch_size):
        batch = artist_ids[start:start + batch_size]
        log.info(f"\n🔹 Processing batch {start // batch_size + 1}/{-(-total_artists // batch_size)} ({len(batch)} artists)")

        for artist_id in batch:
            try:
                albums = safe_spotify_call(sp.artist_albums, artist_id, album_type='album,single', limit=10)
                time.sleep(0.1)  # מנוחה קטנה בין קריאות API
                for album in albums['items']:
                    if album['id'] in processed_albums:
                        continue

                    release_date = parse_spotify_date(
                        album['release_date'],
                        album.get('release_date_precision', 'day')
                    )
                    if release_date >= threshold:
                        tracks = safe_spotify_call(sp.album_tracks, album['id'])['items']
                        time.sleep(0.1)
                        for track in tracks:
                            track_name = track['name']
                            artists = ', '.join(a['name'] for a in track['artists'])
                            log.info(f"🎵 Found new track: {track_name} — {artists}")
                            new_tracks.append(track['uri'])
                        save_processed_album(album['id'])

                time.sleep(delay_between_artists)
            except Exception as e:
                log.error(f"Error with artist {artist_id}: {e}")
                continue

        log.info(f"⏸ Waiting {delay_between_batches}s before next batch...")
        time.sleep(delay_between_batches)

    if new_tracks:
        for i in range(0, len(new_tracks), 100):
            safe_spotify_call(sp.playlist_add_items, config.TARGET_PLAYLIST_ID, new_tracks[i:i + 100])
            time.sleep(0.5)
        log.info(f"\n✅ Added {len(new_tracks)} new tracks to playlist!")
    else:
        log.info("\nNo new tracks found.")
