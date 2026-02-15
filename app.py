import streamlit as st
import cv2
from deepface import DeepFace
from PIL import Image
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.discovery import build
import time
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

if not CLIENT_ID or not CLIENT_SECRET or not YOUTUBE_API_KEY:
    raise ValueError("API keys are missing from environment variables.")

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
)

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


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

def load_css():
    st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            color: #ffffff;
        }

        h1, h2, h3 {
            text-align: center;
            font-family: 'Trebuchet MS', sans-serif;
        }

        .song-card {
            background-color: rgba(255, 255, 255, 0.08);
            padding: 14px;
            margin: 10px 0;
            border-radius: 14px;
        }

        .song-card a {
            color: #1DB954;
            text-decoration: none;
            font-weight: bold;
        }

        /* MAIN BUTTON */
div.stButton > button {
    background-color: #1DB954;
    border-radius: 12px;
    height: 3em;
    width: 100%;
    font-size: 16px;
    font-weight: bold;
    border: none;
}

div.stButton > button span {
    color: #000000;        /* BLACK text by default */
}

/* HOVER STATE */
div.stButton > button:hover {
    background-color: #18ac4d;
}

div.stButton > button:hover span {
    color: #ffffff;        /* WHITE on hover */
}

/* ACTIVE / CLICK */
div.stButton > button:active span,
div.stButton > button:focus span {
    color: #ffffff;
}

        input {
            border-radius: 10px !important;
        }
    </style>
    """, unsafe_allow_html=True)


def detect_emotion():
    st.info("📷 Look at the camera… detecting your mood")
    cap = cv2.VideoCapture(0)
    time.sleep(2)

    emotions = []
    last_frame = None

    for _ in range(5):
        ret, frame = cap.read()
        if not ret:
            continue

        last_frame = frame
        try:
            result = DeepFace.analyze(
                frame,
                actions=["emotion"],
                enforce_detection=False
            )
            emotions.append(result[0]["dominant_emotion"])
        except:
            pass

        time.sleep(0.3)

    cap.release()

    if not emotions:
        return "no face detected", last_frame

    final_emotion = max(set(emotions), key=emotions.count)
    confidence = int((emotions.count(final_emotion) / len(emotions)) * 100)
    st.caption(f"🧠 Emotion confidence: {confidence}%")

    return final_emotion, last_frame

# ======================================================
# SPOTIFY RECOMMENDATIONS (SIMPLE & RELIABLE)
# ======================================================
def get_spotify_recommendations(artist_or_genre, emotion):
    try:
        songs = []
        seen = set()

        query = artist_or_genre.strip()
        st.write(f"🔍 Searching Spotify for **{query}**")

        # 1️⃣ Artist top tracks
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

        # 2️⃣ Playlist search (artist / genre)
        if not songs:
            playlists = sp.search(q=query, type="playlist", limit=5)
            items = playlists.get("playlists", {}).get("items", [])

            if items:
                playlist_id = items[0]["id"]
                tracks = sp.playlist_tracks(playlist_id, limit=20)

                for item in tracks.get("items", []):
                    track = item.get("track")
                    if track:
                        url = track["external_urls"]["spotify"]
                        if url not in seen:
                            songs.append({
                                "name": f"{track['name']} – {track['artists'][0]['name']}",
                                "url": url
                            })
                            seen.add(url)

        # 3️⃣ Emotion-based fallback playlist
        if not songs:
            fallback = emotion_genres.get(emotion, "pop")
            st.info(f"🎼 Mood-based playlist: **{fallback}**")

            playlists = sp.search(q=fallback, type="playlist", limit=5)
            items = playlists.get("playlists", {}).get("items", [])

            if items:
                playlist_id = items[0]["id"]
                tracks = sp.playlist_tracks(playlist_id, limit=20)

                for item in tracks.get("items", []):
                    track = item.get("track")
                    if track:
                        url = track["external_urls"]["spotify"]
                        if url not in seen:
                            songs.append({
                                "name": f"{track['name']} – {track['artists'][0]['name']}",
                                "url": url
                            })
                            seen.add(url)

        return songs[:10]

    except Exception as e:
        st.error(f"❌ Spotify Error: {e}")
        return []

# ======================================================
# YOUTUBE FALLBACK
# ======================================================
def get_youtube_videos(query, max_results=10):
    try:
        request = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=max_results
        )
        response = request.execute()

        videos = []
        for item in response.get("items", []):
            title = item["snippet"]["title"]
            video_id = item["id"]["videoId"]
            url = f"https://www.youtube.com/watch?v={video_id}"
            videos.append({"name": title, "url": url})

        return videos
    except Exception as e:
        st.error(f"❌ YouTube API Error: {e}")
        return []

# ======================================================
# MAIN UI
# ======================================================
def main():
    st.set_page_config(
        page_title="Mood Music Recommender",
        page_icon="🎧",
        layout="centered"
    )

    load_css()

    st.markdown("<h1>🎧 Mood Music Recommender</h1>", unsafe_allow_html=True)
    st.markdown("""
    <p style="text-align:center; font-size:18px; opacity:0.9;">
        Let your <b>face</b> decide your <b>music</b> 🎶<br>
        <span style="opacity:0.7;">Emotion-aware music discovery</span>
    </p>
    """, unsafe_allow_html=True)

    with st.form("user_input"):
        st.markdown("### 🎤 Choose your vibe")
        artist_or_genre = st.text_input(
            "Artist or Genre",
            placeholder="Adele, Arijit, Pop, Indie..."
        )
        submit = st.form_submit_button("🎶 Detect Mood & Play Music")

    if submit:
        if not artist_or_genre.strip():
            st.warning("⚠️ Please enter an artist or genre.")
            return

        emotion, frame = detect_emotion()

        if emotion == "no face detected":
            st.error("❌ No face detected. Please try again.")
            return

        emoji = emoji_map.get(emotion, "")
        st.markdown(
            f"""
            <div class="song-card" style="text-align:center;">
                <h3>🧠 Detected Mood</h3>
                <h2>{emoji} {emotion.capitalize()}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

        if frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            st.image(Image.fromarray(rgb), caption="📸 Captured Image", width=350)

        with st.spinner("🎧 Finding the perfect tracks for you..."):
            songs = get_spotify_recommendations(artist_or_genre, emotion)

        if songs:
            st.subheader("🎵 Recommended Songs")
            for song in songs:
                st.markdown(
                    f"""
                    <div class="song-card">
                        🎵 <b>{song['name']}</b><br>
                        <a href="{song['url']}" target="_blank">▶ Open in Spotify</a>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.warning("⚠️ Spotify failed. Falling back to YouTube.")
            videos = get_youtube_videos(f"{artist_or_genre} {emotion} music")

            if videos:
                st.subheader("🎬 YouTube Recommendations")
                for video in videos:
                    st.markdown(
                        f"""
                        <div class="song-card">
                            🎬 <b>{video['name']}</b><br>
                            <a href="{video['url']}" target="_blank">▶ Watch on YouTube</a>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.error("❌ No recommendations found.")

    st.markdown(
        "<p style='text-align:center; opacity:0.6;'>Made with ❤️ & 🎶</p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
=======
import streamlit as st
import cv2
from deepface import DeepFace
from PIL import Image
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.discovery import build
import time
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

if not CLIENT_ID or not CLIENT_SECRET or not YOUTUBE_API_KEY:
    raise ValueError("API keys are missing from environment variables.")

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
)

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


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

def load_css():
    st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            color: #ffffff;
        }

        h1, h2, h3 {
            text-align: center;
            font-family: 'Trebuchet MS', sans-serif;
        }

        .song-card {
            background-color: rgba(255, 255, 255, 0.08);
            padding: 14px;
            margin: 10px 0;
            border-radius: 14px;
        }

        .song-card a {
            color: #1DB954;
            text-decoration: none;
            font-weight: bold;
        }

        /* MAIN BUTTON */
div.stButton > button {
    background-color: #1DB954;
    border-radius: 12px;
    height: 3em;
    width: 100%;
    font-size: 16px;
    font-weight: bold;
    border: none;
}

div.stButton > button span {
    color: #000000;        /* BLACK text by default */
}

/* HOVER STATE */
div.stButton > button:hover {
    background-color: #18ac4d;
}

div.stButton > button:hover span {
    color: #ffffff;        /* WHITE on hover */
}

/* ACTIVE / CLICK */
div.stButton > button:active span,
div.stButton > button:focus span {
    color: #ffffff;
}

        input {
            border-radius: 10px !important;
        }
    </style>
    """, unsafe_allow_html=True)


def detect_emotion():
    st.info("📷 Look at the camera… detecting your mood")
    cap = cv2.VideoCapture(0)
    time.sleep(2)

    emotions = []
    last_frame = None

    for _ in range(5):
        ret, frame = cap.read()
        if not ret:
            continue

        last_frame = frame
        try:
            result = DeepFace.analyze(
                frame,
                actions=["emotion"],
                enforce_detection=False
            )
            emotions.append(result[0]["dominant_emotion"])
        except:
            pass

        time.sleep(0.3)

    cap.release()

    if not emotions:
        return "no face detected", last_frame

    final_emotion = max(set(emotions), key=emotions.count)
    confidence = int((emotions.count(final_emotion) / len(emotions)) * 100)
    st.caption(f"🧠 Emotion confidence: {confidence}%")

    return final_emotion, last_frame

# ======================================================
# SPOTIFY RECOMMENDATIONS (SIMPLE & RELIABLE)
# ======================================================
def get_spotify_recommendations(artist_or_genre, emotion):
    try:
        songs = []
        seen = set()

        query = artist_or_genre.strip()
        st.write(f"🔍 Searching Spotify for **{query}**")

        # 1️⃣ Artist top tracks
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

        # 2️⃣ Playlist search (artist / genre)
        if not songs:
            playlists = sp.search(q=query, type="playlist", limit=5)
            items = playlists.get("playlists", {}).get("items", [])

            if items:
                playlist_id = items[0]["id"]
                tracks = sp.playlist_tracks(playlist_id, limit=20)

                for item in tracks.get("items", []):
                    track = item.get("track")
                    if track:
                        url = track["external_urls"]["spotify"]
                        if url not in seen:
                            songs.append({
                                "name": f"{track['name']} – {track['artists'][0]['name']}",
                                "url": url
                            })
                            seen.add(url)

        # 3️⃣ Emotion-based fallback playlist
        if not songs:
            fallback = emotion_genres.get(emotion, "pop")
            st.info(f"🎼 Mood-based playlist: **{fallback}**")

            playlists = sp.search(q=fallback, type="playlist", limit=5)
            items = playlists.get("playlists", {}).get("items", [])

            if items:
                playlist_id = items[0]["id"]
                tracks = sp.playlist_tracks(playlist_id, limit=20)

                for item in tracks.get("items", []):
                    track = item.get("track")
                    if track:
                        url = track["external_urls"]["spotify"]
                        if url not in seen:
                            songs.append({
                                "name": f"{track['name']} – {track['artists'][0]['name']}",
                                "url": url
                            })
                            seen.add(url)

        return songs[:10]

    except Exception as e:
        st.error(f"❌ Spotify Error: {e}")
        return []

# ======================================================
# YOUTUBE FALLBACK
# ======================================================
def get_youtube_videos(query, max_results=10):
    try:
        request = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=max_results
        )
        response = request.execute()

        videos = []
        for item in response.get("items", []):
            title = item["snippet"]["title"]
            video_id = item["id"]["videoId"]
            url = f"https://www.youtube.com/watch?v={video_id}"
            videos.append({"name": title, "url": url})

        return videos
    except Exception as e:
        st.error(f"❌ YouTube API Error: {e}")
        return []

# ======================================================
# MAIN UI
# ======================================================
def main():
    st.set_page_config(
        page_title="Mood Music Recommender",
        page_icon="🎧",
        layout="centered"
    )

    load_css()

    st.markdown("<h1>🎧 Mood Music Recommender</h1>", unsafe_allow_html=True)
    st.markdown("""
    <p style="text-align:center; font-size:18px; opacity:0.9;">
        Let your <b>face</b> decide your <b>music</b> 🎶<br>
        <span style="opacity:0.7;">Emotion-aware music discovery</span>
    </p>
    """, unsafe_allow_html=True)

    with st.form("user_input"):
        st.markdown("### 🎤 Choose your vibe")
        artist_or_genre = st.text_input(
            "Artist or Genre",
            placeholder="Adele, Arijit, Pop, Indie..."
        )
        submit = st.form_submit_button("🎶 Detect Mood & Play Music")

    if submit:
        if not artist_or_genre.strip():
            st.warning("⚠️ Please enter an artist or genre.")
            return

        emotion, frame = detect_emotion()

        if emotion == "no face detected":
            st.error("❌ No face detected. Please try again.")
            return

        emoji = emoji_map.get(emotion, "")
        st.markdown(
            f"""
            <div class="song-card" style="text-align:center;">
                <h3>🧠 Detected Mood</h3>
                <h2>{emoji} {emotion.capitalize()}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

        if frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            st.image(Image.fromarray(rgb), caption="📸 Captured Image", width=350)

        with st.spinner("🎧 Finding the perfect tracks for you..."):
            songs = get_spotify_recommendations(artist_or_genre, emotion)

        if songs:
            st.subheader("🎵 Recommended Songs")
            for song in songs:
                st.markdown(
                    f"""
                    <div class="song-card">
                        🎵 <b>{song['name']}</b><br>
                        <a href="{song['url']}" target="_blank">▶ Open in Spotify</a>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.warning("⚠️ Spotify failed. Falling back to YouTube.")
            videos = get_youtube_videos(f"{artist_or_genre} {emotion} music")

            if videos:
                st.subheader("🎬 YouTube Recommendations")
                for video in videos:
                    st.markdown(
                        f"""
                        <div class="song-card">
                            🎬 <b>{video['name']}</b><br>
                            <a href="{video['url']}" target="_blank">▶ Watch on YouTube</a>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.error("❌ No recommendations found.")

    st.markdown(
        "<p style='text-align:center; opacity:0.6;'>Made with ❤️ & 🎶</p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
