import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def get_spotify_client():
    """
    Returns a Spotify client authenticated for playlist modification.
    Uses SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REFRESH_TOKEN from environment variables.
    """
    try:
        client_id = os.environ["SPOTIFY_CLIENT_ID"]
        client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
        refresh_token = os.environ["SPOTIFY_REFRESH_TOKEN"]
    except KeyError as e:
        raise ValueError(f"Missing environment variable: {e}")

    # Initialize SpotifyOAuth to handle token refresh
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://127.0.0.1:8888/callback",  # only needed for first auth
        scope="playlist-modify-public playlist-modify-private",
        cache_path=".spotify_cache",
        show_dialog=False
    )

    # Refresh access token automatically
    token_info = sp_oauth.refresh_access_token(refresh_token)
    sp = spotipy.Spotify(auth=token_info['access_token'])
    return sp
