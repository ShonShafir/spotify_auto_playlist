from datetime import datetime, timezone, timedelta
import config
from auth_setup import get_spotify_client  # <-- import the Spotify client
from datetime import datetime, timezone

def parse_spotify_date(date_str, precision):
    """Convert Spotify release_date to UTC-aware datetime"""
    if precision == 'year':
        dt = datetime(int(date_str), 1, 1)
    elif precision == 'month':
        year, month = map(int, date_str.split('-'))
        dt = datetime(year, month, 1)
    else:  # 'day'
        dt = datetime.fromisoformat(date_str)

    # Make timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

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
    sp = get_spotify_client()  # <-- use the auth_setup client
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
                release_date = parse_spotify_date(
                    album['release_date'],
                    album.get('release_date_precision', 'day')
                )
                if release_date >= threshold:
                    tracks = sp.album_tracks(album['id'])['items']
                    for track in tracks:
                        track_name = track['name']
                        artists = ', '.join(a['name'] for a in track['artists'])
                        print(f"🎵 Found new track: {track_name} — {artists}")
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
