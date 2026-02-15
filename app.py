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
# ENV
# ========================
load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID") or st.secrets.get("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET") or st.secrets.get("SPOTIFY_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY") or st.secrets.get("YOUTUBE_API_KEY")

if not CLIENT_ID or not CLIENT_SECRET or not YOUTUBE_API_KEY:
    st.error("API keys missing.")
    st.stop()

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
)

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
# CSS (YOUR ORIGINAL STYLE)
# ========================
def load_css():
    st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
            color:white;
        }
        h1,h2,h3 { text-align:center; }
        .song-card {
            background: rgba(255,255,255,0.08);
            padding:14px;
            margin:10px 0;
            border-radius:14px;
        }
        .song-card a {
            color:#1DB954;
            text-decoration:none;
            font-weight:bold;
        }
    </style>
    """, unsafe_allow_html=True)

# ========================
# IMAGE INPUT (OUTSIDE FORM)
# ========================
def get_image():
    st.markdown("### 📸 Capture or Upload Photo")

    cam = st.camera_input("Take a photo")
    upload = st.file_uploader("Or upload image", type=["jpg","jpeg","png"])

    if cam:
        return Image.open(cam).convert("RGB")

    if upload:
        return Image.open(upload).convert("RGB")

    return None

# ========================
# EMOTION DETECTION
# ========================
def detect_emotion(image):
    frame = np.array(image)
    frame = cv2.resize(frame, (640,480))

    try:
        result = DeepFace.analyze(
            frame,
            actions=['emotion'],
            enforce_detection=False,
            detector_backend='retinaface'
        )
        return result[0]["dominant_emotion"], frame
    except:
        return None, frame

# ========================
# SPOTIFY
# ========================
def get_spotify_recommendations(query, emotion):
    try:
        songs = []
        seen = set()

        # 🔹 Try artist top tracks
        artist = sp.search(q=query, type="artist", limit=1)
        items = artist.get("artists", {}).get("items", [])

        if items:
            tracks = sp.artist_top_tracks(items[0]["id"], country="IN")
            for t in tracks["tracks"]:
                url = t["external_urls"]["spotify"]
                if url not in seen:
                    songs.append((t["name"], url))
                    seen.add(url)
                if len(songs) >= 30:
                    return songs

        # 🔹 If not enough → search playlists
        mood = emotion_genres.get(emotion, "pop")
        playlists = sp.search(q=f"{query} {mood}", type="playlist", limit=5)

        for pl in playlists["playlists"]["items"]:
            tracks = sp.playlist_tracks(pl["id"], limit=50)

            for item in tracks["items"]:
                track = item.get("track")
                if track:
                    url = track["external_urls"]["spotify"]
                    if url not in seen:
                        songs.append((track["name"], url))
                        seen.add(url)

                if len(songs) >= 30:
                    return songs

        return songs

    except Exception as e:
        st.error(f"Spotify Error: {e}")
        return []


# ========================
# YOUTUBE FALLBACK
# ========================
def get_youtube_videos(query):
    req=youtube.search().list(q=query,part="snippet",type="video",maxResults=5)
    res=req.execute()
    vids=[]
    for item in res["items"]:
        vids.append((item["snippet"]["title"],
                     f"https://youtube.com/watch?v={item['id']['videoId']}"))
    return vids

# ========================
# MAIN APP
# ========================
def main():
    st.set_page_config(page_title="Mood Music Recommender", page_icon="🎧")
    load_css()

    st.markdown("<h1>🎧 Mood Music Recommender</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center'>Let your face decide your music 🎶</p>", unsafe_allow_html=True)

    image = get_image()

    if image:
        st.image(image, caption="Selected Image", use_column_width=True)

    with st.form("user_input"):
        st.markdown("### 🎤 Choose your vibe")
        artist = st.text_input("Artist or Genre", placeholder="Adele, Arijit, Pop...")
        submit = st.form_submit_button("🎶 Detect Mood & Play Music")

    if submit:
        if image is None:
            st.warning("Please capture or upload a photo.")
            return

        if not artist.strip():
            st.warning("Enter artist or genre.")
            return

        emotion, frame = detect_emotion(image)

        if emotion is None:
            st.error("Face not detected. Try good lighting & centered face.")
            return

        emoji = emoji_map.get(emotion,"")
        st.markdown(f"<h2>{emoji} {emotion.capitalize()}</h2>", unsafe_allow_html=True)

        with st.spinner("🎧 Finding music..."):
            songs = get_spotify_recommendations(artist, emotion)

        if songs:
            for name,url in songs:
                st.markdown(f"<div class='song-card'><b>{name}</b><br><a href='{url}' target='_blank'>▶ Open in Spotify</a></div>", unsafe_allow_html=True)
        else:
            vids = get_youtube_videos(f"{artist} {emotion} music")
            for name,url in vids:
                st.markdown(f"<div class='song-card'><b>{name}</b><br><a href='{url}' target='_blank'>▶ Watch</a></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
