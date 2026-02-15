import streamlit as st
import cv2
import numpy as np
from deepface import DeepFace
from PIL import Image
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.discovery import build

# ========================
# PAGE CONFIG
# ========================
st.set_page_config(
    page_title="Mood Music Recommender",
    page_icon="🎧",
    layout="centered"
)

# ========================
# SECRETS (STREAMLIT CLOUD)
# ========================
CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]

# Spotify
sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
)

# YouTube
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# ========================
# SETTINGS
# ========================
emotion_genres = {
    "happy": "pop",
    "sad": "acoustic",
    "angry": "metal",
    "fear": "ambient",
    "neutral": "indie",
    "surprise": "electronic",
    "disgust": "classical"
}

emoji_map = {
    "happy": "😄",
    "sad": "😢",
    "angry": "😠",
    "neutral": "😐",
    "fear": "😨",
    "surprise": "😲",
    "disgust": "🤢"
}

# ========================
# UI STYLE
# ========================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
    color:white;
}

div.stButton > button {
    background: rgba(255,255,255,0.08);
    color:white;
    border-radius:14px;
    border:1px solid rgba(255,255,255,0.25);
    font-weight:600;
    height:3em;
    width:100%;
}

div.stButton > button:hover {
    background: rgba(255,255,255,0.15);
    border:1px solid rgba(255,255,255,0.45);
}

.song-card {
    background: rgba(255,255,255,0.08);
    padding:14px;
    margin:8px 0;
    border-radius:14px;
}

.song-card a {
    color:#1DB954;
    text-decoration:none;
    font-weight:600;
}
</style>
""", unsafe_allow_html=True)

# ========================
# IMAGE INPUT (OUTSIDE BUTTON)
# ========================
st.markdown("### 📸 Capture or Upload Photo")

camera_photo = st.camera_input("Take a photo")
uploaded_photo = st.file_uploader("Or upload image", type=["jpg","jpeg","png"])

image = None

if camera_photo:
    image = Image.open(camera_photo).convert("RGB")
elif uploaded_photo:
    image = Image.open(uploaded_photo).convert("RGB")

if image:
    st.image(image, caption="Selected Image", use_container_width=True)

# ========================
# EMOTION DETECTION
# ========================
def detect_emotion(image):
    frame = np.array(image)

    # resize improves detection reliability
    frame = cv2.resize(frame, (640, 480))

    try:
        result = DeepFace.analyze(
            frame,
            actions=['emotion'],
            detector_backend='opencv',   # most stable on cloud
            enforce_detection=False
        )
        return result[0]["dominant_emotion"], frame
    except:
        return None, frame

# ========================
# SPOTIFY (20 SONGS)
# ========================
def get_spotify_recommendations(query, emotion):
    songs = []
    seen = set()

    try:
        # 1️⃣ Artist top tracks
        artist_results = sp.search(q=query, type="artist", limit=1)
        artists = artist_results.get("artists", {}).get("items", [])

        if artists:
            artist_id = artists[0]["id"]
            top_tracks = sp.artist_top_tracks(artist_id, country="IN")

            for track in top_tracks.get("tracks", []):
                if track and track.get("external_urls"):
                    url = track["external_urls"]["spotify"]
                    if url not in seen:
                        songs.append((track["name"], url))
                        seen.add(url)

        # 2️⃣ Playlist search for MORE songs
        playlists = sp.search(q=query, type="playlist", limit=5)

        for playlist in playlists.get("playlists", {}).get("items", []):
            tracks = sp.playlist_tracks(playlist["id"], limit=100)

            for item in tracks.get("items", []):
                track = item.get("track")

                if not track:
                    continue

                if track.get("external_urls") is None:
                    continue

                url = track["external_urls"]["spotify"]

                if url not in seen:
                    songs.append((track["name"], url))
                    seen.add(url)

                if len(songs) >= 20:
                    return songs

        # 3️⃣ Emotion fallback
        if len(songs) < 20:
            mood = emotion_genres.get(emotion, "pop")

            playlists = sp.search(q=mood, type="playlist", limit=2)

            for playlist in playlists.get("playlists", {}).get("items", []):
                tracks = sp.playlist_tracks(playlist["id"], limit=100)

                for item in tracks.get("items", []):
                    track = item.get("track")

                    if not track or not track.get("external_urls"):
                        continue

                    url = track["external_urls"]["spotify"]

                    if url not in seen:
                        songs.append((track["name"], url))
                        seen.add(url)

                    if len(songs) >= 20:
                        return songs

    except Exception as e:
        st.error(f"Spotify error: {e}")

    return songs[:20]


# ========================
# YOUTUBE FALLBACK
# ========================
def get_youtube_videos(query):
    request = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=10
    )
    response = request.execute()

    videos = []
    for item in response["items"]:
        videos.append((
            item["snippet"]["title"],
            f"https://www.youtube.com/watch?v={item['id']['videoId']}"
        ))
    return videos

# ========================
# MAIN UI
# ========================
st.markdown("<h1 style='text-align:center'>🎧 Mood Music Recommender</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center'>Let your face decide your music</p>", unsafe_allow_html=True)

artist = st.text_input("Artist or Genre")

if st.button("Detect Mood & Play Music"):

    if image is None:
        st.warning("Please upload or capture a photo.")
        st.stop()

    if not artist.strip():
        st.warning("Enter an artist or genre.")
        st.stop()

    emotion, frame = detect_emotion(image)

    if emotion is None:
        st.error("Face not detected. Try good lighting & centered face.")
        st.stop()

    emoji = emoji_map.get(emotion, "")
    st.markdown(f"## {emoji} {emotion.capitalize()}")

    with st.spinner("Finding perfect music..."):
        songs = get_spotify_recommendations(artist, emotion)

    if songs:
        st.subheader("🎵 Recommendations")
        for name, url in songs:
            st.markdown(
                f"<div class='song-card'><b>{name}</b><br>"
                f"<a href='{url}' target='_blank'>▶ Open in Spotify</a></div>",
                unsafe_allow_html=True
            )
    else:
        st.warning("Spotify unavailable → YouTube results")
        vids = get_youtube_videos(f"{artist} {emotion} music")
        for name, url in vids:
            st.markdown(
                f"<div class='song-card'><b>{name}</b><br>"
                f"<a href='{url}' target='_blank'>▶ Watch</a></div>",
                unsafe_allow_html=True
            )

st.markdown("<p style='text-align:center;opacity:0.5'>Made with ❤️</p>", unsafe_allow_html=True)
