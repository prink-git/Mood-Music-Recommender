import streamlit as st
import cv2
import numpy as np
from deepface import DeepFace
from PIL import Image
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.discovery import build
import os

# ========================
# PAGE CONFIG
# ========================
st.set_page_config(
    page_title="Mood Music Recommender",
    page_icon="🎧",
    layout="centered"
)

# ========================
# ENV VARIABLES (STREAMLIT CLOUD)
# ========================
CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]

# Spotify setup
sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
)

# YouTube setup
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# ========================
# EMOTION SETTINGS
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
# AESTHETIC UI
# ========================
def load_css():
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
        color: white;
    }

    /* BUTTON */
    div.stButton > button {
        background: rgba(255,255,255,0.08);
        color: white;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.2);
        font-weight: 600;
        height: 3em;
        width: 100%;
        backdrop-filter: blur(6px);
        transition: 0.2s;
    }

    div.stButton > button:hover {
        background: rgba(255,255,255,0.15);
        border: 1px solid rgba(255,255,255,0.4);
        transform: scale(1.02);
    }

    /* CARD */
    .song-card {
        background: rgba(255,255,255,0.06);
        padding: 14px;
        margin: 8px 0;
        border-radius: 14px;
        backdrop-filter: blur(8px);
    }

    .song-card a {
        color: #1DB954;
        font-weight: 600;
        text-decoration: none;
    }
    </style>
    """, unsafe_allow_html=True)

load_css()
# load model once (prevents freezing)
@st.cache_resource
def load_emotion_model():
    return DeepFace.build_model("Emotion")

emotion_model = load_emotion_model()

def detect_emotion():
    st.info("📸 Capture or upload photo")

    image_file = st.camera_input("Take photo")

    if image_file is None:
        image_file = st.file_uploader(
            "Or upload image", type=["jpg","jpeg","png"]
        )

    if image_file is None:
        return None, None

    image = Image.open(image_file).convert("RGB")
    st.image(image, caption="Preview", use_container_width=True)

    frame = np.array(image)

    # resize smaller → faster processing
    frame = cv2.resize(frame, (224, 224))

    try:
        result = DeepFace.analyze(
            frame,
            actions=['emotion'],
            enforce_detection=False,
            detector_backend='opencv',
            models={'emotion': emotion_model}
        )

        emotion = result[0]["dominant_emotion"]
        return emotion, frame

    except Exception as e:
        st.error("Detection failed. Try better lighting.")
        return "no face detected", frame

def get_spotify_recommendations(query, emotion):
    songs = []
    seen = set()

    try:
        # 🎤 1️⃣ Artist search (MOST RELIABLE)
        artist_results = sp.search(q=query, type="artist", limit=1)
        artists = artist_results.get("artists", {}).get("items", [])

        if artists:
            artist_id = artists[0]["id"]
            top_tracks = sp.artist_top_tracks(artist_id, country="IN")

            for track in top_tracks["tracks"]:
                url = track["external_urls"]["spotify"]
                if url not in seen:
                    songs.append({
                        "name": f"{track['name']} — {track['artists'][0]['name']}",
                        "url": url
                    })
                    seen.add(url)

        # 🎵 2️⃣ Playlist search for more songs
        playlists = sp.search(q=query, type="playlist", limit=3)

        for playlist in playlists["playlists"]["items"]:
            tracks = sp.playlist_tracks(playlist["id"], limit=50)

            for item in tracks["items"]:
                track = item.get("track")
                if track:
                    url = track["external_urls"]["spotify"]
                    if url not in seen:
                        songs.append({
                            "name": f"{track['name']} — {track['artists'][0]['name']}",
                            "url": url
                        })
                        seen.add(url)

                if len(songs) >= 20:
                    return songs

        # 🎧 3️⃣ Emotion fallback if still low
        if len(songs) < 20:
            mood = emotion_genres.get(emotion, "pop")
            playlists = sp.search(q=mood, type="playlist", limit=1)

            if playlists["playlists"]["items"]:
                pid = playlists["playlists"]["items"][0]["id"]
                tracks = sp.playlist_tracks(pid, limit=50)

                for item in tracks["items"]:
                    track = item.get("track")
                    if track:
                        url = track["external_urls"]["spotify"]
                        if url not in seen:
                            songs.append({
                                "name": f"{track['name']} — {track['artists'][0]['name']}",
                                "url": url
                            })
                            seen.add(url)

                    if len(songs) >= 20:
                        break

    except Exception as e:
        st.error(f"Spotify Error: {e}")

    return songs[:20]

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
        videos.append({
            "name": item["snippet"]["title"],
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
        })

    return videos

# ========================
# MAIN UI
# ========================
st.markdown("<h1 style='text-align:center'>🎧 Mood Music Recommender</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center'>Let your face decide your music</p>", unsafe_allow_html=True)

artist = st.text_input("Artist or Genre")

if st.button("Detect Mood & Play Music"):

    if not artist.strip():
        st.warning("Enter an artist or genre")
        st.stop()

    emotion, frame = detect_emotion()

    if emotion is None:
        st.info("Capture or upload an image")
        st.stop()

    if emotion == "no face detected":
        st.error("No face detected. Try better lighting.")
        st.stop()

    emoji = emoji_map.get(emotion, "")
    st.markdown(f"## {emoji} {emotion.capitalize()}")

    with st.spinner("Finding perfect music..."):
        songs = get_spotify_recommendations(artist, emotion)

    if songs:
        st.subheader("🎵 Recommendations")

        for s in songs:
            st.markdown(
                f"<div class='song-card'><b>{s['name']}</b><br>"
                f"<a href='{s['url']}' target='_blank'>Open in Spotify</a></div>",
                unsafe_allow_html=True
            )

    else:
        st.warning("Spotify unavailable → YouTube results")

        videos = get_youtube_videos(f"{artist} {emotion} music")

        for v in videos:
            st.markdown(
                f"<div class='song-card'><b>{v['name']}</b><br>"
                f"<a href='{v['url']}' target='_blank'>Watch</a></div>",
                unsafe_allow_html=True
            )

st.markdown("<p style='text-align:center;opacity:0.5'>Made with ❤️</p>", unsafe_allow_html=True)
