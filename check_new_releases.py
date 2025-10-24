import time
import logging
from datetime import datetime, timezone, timedelta
from spotipy.exceptions import SpotifyException
import config
from auth_setup import get_spotify_client, get_spotify_manager

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

def load_added_track_ids():
    """Load previously added track IDs to prevent duplicates."""
    try:
        with open(config.ADDED_TRACKS_FILE, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def save_added_track_id(track_id):
    """Save a track ID to the tracking file."""
    with open(config.ADDED_TRACKS_FILE, 'a') as f:
        f.write(f"{track_id}\n")

# === Main logic ===
def check_new_releases(batch_size=20, delay_between_batches=30, delay_between_artists=1.5, max_artists=None):
    """
    Check for new releases from artists and add them to playlist.
    Tracks releases from yesterday and today only (0-1 day difference).
    Prevents duplicate additions by tracking individual track IDs.
    
    Optimized for GitHub Actions (6-hour limit) with conservative rate limiting.
    Processes all artists (~3,300) in approximately 3-4 hours safely.
    
    Args:
        batch_size: Number of artists per batch (default: 20 for safety)
        delay_between_batches: Seconds to wait between batches (default: 30)
        delay_between_artists: Seconds to wait between artists (default: 1.5)
        max_artists: Maximum artists to process (default: None = all artists)
    """
    spotify_manager = get_spotify_manager()
    artist_ids = load_artist_ids()
    if not artist_ids:
        log.error("No artist IDs found. Please check artists_id.txt")
        return

    # Process all artists unless max_artists is specified
    total_all_artists = len(artist_ids)
    if max_artists and len(artist_ids) > max_artists:
        log.warning(f"⚠️ You have {total_all_artists} artists. Processing first {max_artists} due to max_artists limit.")
        artist_ids = artist_ids[:max_artists]
    else:
        log.info(f"🎧 Processing ALL {total_all_artists} artists (no limit)")

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    
    log.info(f"📅 Checking for releases from: {yesterday_start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    added_track_ids = load_added_track_ids()
    log.info(f"📝 Loaded {len(added_track_ids)} previously added track IDs")
    
    new_tracks = []
    new_track_ids = []
    total_artists = len(artist_ids)
    
    log.info(f"🎧 Checking {total_artists} artists in batches of {batch_size}...")
    log.info(f"⏱️ Rate limiting: {delay_between_artists}s between artists, {delay_between_batches}s between batches")

    for start in range(0, total_artists, batch_size):
        sp = spotify_manager.get_client()
        
        batch = artist_ids[start:start + batch_size]
        batch_num = start // batch_size + 1
        total_batches = -(-total_artists // batch_size)
        
        log.info(f"\n🔹 Processing batch {batch_num}/{total_batches} ({len(batch)} artists)")

        for idx, artist_id in enumerate(batch):
            try:
                albums = safe_spotify_call(sp.artist_albums, artist_id, album_type='album,single', limit=20)
                time.sleep(0.5)
                
                for album in albums['items']:
                    release_date = parse_spotify_date(
                        album['release_date'],
                        album.get('release_date_precision', 'day')
                    )
                    
                    if release_date < yesterday_start:
                        continue
                    
                    if release_date <= now:
                        days_diff = (now - release_date).days
                        
                        if days_diff <= 1:
                            tracks = safe_spotify_call(sp.album_tracks, album['id'])['items']
                            time.sleep(0.5)
                            
                            for track in tracks:
                                track_id = track['id']
                                
                                if track_id not in added_track_ids and track_id not in new_track_ids:
                                    track_name = track['name']
                                    artists_str = ', '.join(a['name'] for a in track['artists'])
                                    release_date_str = release_date.strftime('%Y-%m-%d')
                                    
                                    log.info(f"🎵 New track ({days_diff}d old): {track_name} — {artists_str} [{release_date_str}]")
                                    
                                    new_tracks.append(track['uri'])
                                    new_track_ids.append(track_id)

                time.sleep(delay_between_artists)
                
            except Exception as e:
                log.error(f"❌ Error with artist {artist_id}: {e}")
                continue
        
        if batch_num < total_batches:
            log.info(f"⏸ Waiting {delay_between_batches}s before next batch...")
            time.sleep(delay_between_batches)

    if new_tracks:
        log.info(f"\n📤 Adding {len(new_tracks)} new tracks to playlist...")
        sp = spotify_manager.get_client()
        
        for i in range(0, len(new_tracks), 100):
            batch_to_add = new_tracks[i:i + 100]
            safe_spotify_call(sp.playlist_add_items, config.TARGET_PLAYLIST_ID, batch_to_add)
            time.sleep(2)
            log.info(f"   Added batch {i // 100 + 1}/{-(-len(new_tracks) // 100)}")
        
        for track_id in new_track_ids:
            save_added_track_id(track_id)
        
        log.info(f"✅ Successfully added {len(new_tracks)} new tracks to playlist!")
    else:
        log.info("\n✨ No new tracks found from yesterday or today.")
