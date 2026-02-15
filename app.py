import streamlit as st
import cv2
import numpy as np
from deepface import DeepFace
from PIL import Image
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv

# ========================
# ENV SETUP
# ========================
load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

if not CLIENT_ID or not CLIENT_SECRET or not YOUTUBE_API_KEY:
    st.error("API keys missing. Add them in Streamlit secrets.")
    st.stop()

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
# UI STYLE
# ========================
def load_css():
    st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            color: #ffffff;
        }
        h1, h2, h3 { text-align: center; }
        .song-card {
            background-color: rgba(255,255,255,0.08);
            padding: 14px;
            margin: 10px 0;
            border-radius: 14px;
        }
        .song-card a {
            color: #1DB954;
            font-weight: bold;
            text-decoration: none;
        }
    </style>
    """, unsafe_allow_html=True)

# ========================
# EMOTION DETECTION
# ========================
def detect_emotion():
    st.info("📸 Take a photo or upload one")

    image_file = st.camera_input("Take a photo")

    if image_file is None:
        image_file = st.file_uploader("Or upload image", type=["jpg", "jpeg", "png"])

    if image_file is None:
        return None, None

    # open image
    image = Image.open(image_file).convert("RGB")
    frame = np.array(image)

    # show preview so user knows upload worked
    st.image(image, caption="Uploaded Image", use_column_width=True)

    # resize for better detection
    frame = cv2.resize(frame, (640, 480))

    try:
        result = DeepFace.analyze(
            frame,
            actions=['emotion'],
            enforce_detection=False,
            detector_backend='retinaface'   # more reliable
        )

        emotion = result[0]["dominant_emotion"]
        return emotion, frame

    except Exception as e:
        st.warning("Face not detected. Try better lighting & face centered.")
        return "no face detected", frame

# ========================
# SPOTIFY RECOMMENDATIONS
# ========================
def get_spotify_recommendations(query, emotion):
    try:
        songs = []
        seen = set()

        artist_results = sp.search(q=query, type="artist", limit=1)
        artists = artist_results.get("artists", {}).get("items", [])

        if artists:
            artist_id = artists[0]["id"]
            top_tracks = sp.artist_top_tracks(artist_id, country="IN")

            for track in top_tracks.get("tracks", []):
                url = track["external_urls"]["spotify"]
                if url not in seen:
                    songs.append({
                        "name": f"{track['name']} – {track['artists'][0]['name']}",
                        "url": url
                    })
                    seen.add(url)

        if not songs:
            fallback = emotion_genres.get(emotion, "pop")
            playlists = sp.search(q=fallback, type="playlist", limit=1)
            items = playlists.get("playlists", {}).get("items", [])

            if items:
                playlist_id = items[0]["id"]
                tracks = sp.playlist_tracks(playlist_id, limit=10)

                for item in tracks.get("items", []):
                    track = item.get("track")
                    if track:
                        url = track["external_urls"]["spotify"]
                        songs.append({
                            "name": f"{track['name']} – {track['artists'][0]['name']}",
                            "url": url
                        })

        return songs[:10]

    except Exception as e:
        st.error(f"Spotify Error: {e}")
        return []

# ========================
# YOUTUBE FALLBACK
# ========================
def get_youtube_videos(query):
    try:
        request = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=6
        )
        response = request.execute()

        videos = []
        for item in response.get("items", []):
            title = item["snippet"]["title"]
            vid = item["id"]["videoId"]
            videos.append({
                "name": title,
                "url": f"https://www.youtube.com/watch?v={vid}"
            })

        return videos

    except Exception as e:
        st.error(f"YouTube Error: {e}")
        return []

# ========================
# MAIN APP
# ========================
def main():
    st.set_page_config(
        page_title="Mood Music Recommender",
        page_icon="🎧",
        layout="centered"
    )

    load_css()

    st.markdown("<h1>🎧 Mood Music Recommender</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center'>Let your face decide your music 🎶</p>",
        unsafe_allow_html=True
    )

    artist = st.text_input("Artist or Genre", placeholder="Arijit, Adele, Pop…")

    if st.button("🎶 Detect Mood & Play Music"):
        if not artist.strip():
            st.warning("Enter an artist or genre")
            return

        emotion, frame = detect_emotion()

        if emotion is None:
            st.info("Please capture or upload an image")
            return

        if emotion == "no face detected":
            st.error("No face detected. Try again.")
            return

        emoji = emoji_map.get(emotion, "")
        st.markdown(f"## {emoji} Detected Mood: **{emotion.capitalize()}**")

        if frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            st.image(Image.fromarray(rgb), width=300)

        with st.spinner("Finding perfect music…"):
            songs = get_spotify_recommendations(artist, emotion)

        if songs:
            st.subheader("🎵 Recommended Songs")
            for s in songs:
                st.markdown(
                    f"<div class='song-card'>🎵 <b>{s['name']}</b><br>"
                    f"<a href='{s['url']}' target='_blank'>Open in Spotify</a></div>",
                    unsafe_allow_html=True
                )
        else:
            st.warning("Spotify failed → showing YouTube")
            vids = get_youtube_videos(f"{artist} {emotion} music")
            for v in vids:
                st.markdown(
                    f"<div class='song-card'>🎬 <b>{v['name']}</b><br>"
                    f"<a href='{v['url']}' target='_blank'>Watch</a></div>",
                    unsafe_allow_html=True
                )

    st.markdown("<p style='text-align:center;opacity:0.6'>Made with ❤️ & 🎶</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
