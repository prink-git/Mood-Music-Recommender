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

CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

if not CLIENT_ID or not CLIENT_SECRET or not YOUTUBE_API_KEY:
    raise ValueError("API keys are missing from environment variables.")
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)


# Map emotions to fallback genres
emotion_genres = {
    "happy": "pop",
    "sad": "acoustic",
    "angry": "metal",
    "fear": "ambient",
    "neutral": "chill",
    "surprise": "electronic",
    "disgust": "instrumental"
}

# Emoji mapping for UI
emoji_map = {
    "happy": "😄", "sad": "😢", "angry": "😠", "neutral": "😐",
    "fear": "😨", "surprise": "😲", "disgust": "🤢"
}

def detect_emotion():
    st.info("📷 Initializing webcam for emotion detection...")
    cap = cv2.VideoCapture(0)
    time.sleep(2)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        st.error("❌ Failed to capture image from webcam.")
        return "no face detected", None

    try:
        result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=True)
        emotion = result[0]['dominant_emotion']
        return emotion, frame
    except Exception as e:
        st.error(f"❌ Error detecting emotion: {e}")
        return "no face detected", frame

def get_spotify_recommendations(artist_or_genre, emotion):
    try:
        songs = []
        seen_urls = set()

        query = artist_or_genre.strip().lower()
        st.write(f"🔍 Searching Spotify for: **{query}**")

        # Artist search
        artist_results = sp.search(q=query, type='artist', limit=1)
        artists = artist_results.get('artists', {}).get('items', [])

        if artists:
            artist_id = artists[0].get('id')
            if artist_id:
                try:
                    recommendations = sp.recommendations(limit=30, seed_artists=[artist_id])
                    tracks = recommendations.get('tracks') if recommendations else None
                    if tracks:
                        for track in tracks:
                            url = track['external_urls']['spotify']
                            if url not in seen_urls:
                                songs.append({"name": track['name'], "url": url})
                                seen_urls.add(url)
                    else:
                        st.warning(f"⚠️ No artist-based recommendations found for '{query}'.")
                except spotipy.exceptions.SpotifyException as e:
                    if e.http_status == 404:
                        st.info(f"🔁 No recommendations available for artist '{query}', falling back to playlists.")
                    else:
                        st.warning(f"⚠️ Spotify error: {e}")

        # Playlist search if no songs yet
        if not songs:
            playlist_results = sp.search(q=query, type='playlist', limit=10)
            playlists = playlist_results.get('playlists', {}).get('items', [])
            if playlists:
                playlist_id = playlists[0].get('id')
                if playlist_id:
                    tracks = sp.playlist_tracks(playlist_id, limit=30)
                    for item in tracks.get('items', []):
                        track = item.get('track')
                        if track:
                            url = track.get('external_urls', {}).get('spotify')
                            if url and url not in seen_urls:
                                songs.append({"name": track.get('name', 'Unknown'), "url": url})
                                seen_urls.add(url)

        # Fallback genre playlists
        if not songs and emotion:
            fallback_genre = emotion_genres.get(emotion.lower(), "pop")
            st.info(f"🔁 Using fallback genre on Spotify: **{fallback_genre}**")
            genre_playlists = sp.search(q=fallback_genre, type='playlist', limit=10)
            fallback_playlists = genre_playlists.get('playlists', {}).get('items', [])
            if fallback_playlists:
                playlist_id = fallback_playlists[0].get('id')
                if playlist_id:
                    tracks = sp.playlist_tracks(playlist_id, limit=30)
                    for item in tracks.get('items', []):
                        track = item.get('track')
                        if track:
                            url = track.get('external_urls', {}).get('spotify')
                            if url and url not in seen_urls:
                                songs.append({"name": track.get('name', 'Unknown'), "url": url})
                                seen_urls.add(url)

        return songs

    except Exception as e:
        st.error(f"❌ Spotify API Error: {e}")
        return []

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
        for item in response.get('items', []):
            title = item['snippet']['title']
            video_id = item['id']['videoId']
            url = f"https://www.youtube.com/watch?v={video_id}"
            videos.append({"name": title, "url": url})
        return videos
    except Exception as e:
        st.error(f"❌ YouTube API Error: {e}")
        return []

def main():
    st.set_page_config(page_title="Mood Music Recommender", page_icon="🎧", layout="centered")
    st.title("🎵 Mood-Based Music Recommendation System")
    st.markdown("Let your **face** tell us your **mood** — and get matching music from **Spotify** with YouTube fallback 🎶")

    with st.form("user_input_form"):
        genre_or_artist = st.text_input("🎤 Enter a Singer or Genre (e.g., 'Adele', 'Pop')", max_chars=30)
        submitted = st.form_submit_button("Detect Emotion & Get Songs")

    if submitted:
        if not genre_or_artist.strip():
            st.warning("⚠️ Please enter a singer or genre.")
            return

        emotion, frame = detect_emotion()

        if emotion == "no face detected":
            st.error("❌ Couldn't detect a face. Please ensure your webcam is clear and try again.")
            if st.button("🔁 Try Again"):
                st.experimental_rerun()
            return

        emoji = emoji_map.get(emotion.lower(), "")
        st.success(f"✅ Detected Emotion: **{emotion.capitalize()}** {emoji}")

        # Showing the captured image
        if frame is not None:
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            st.image(Image.fromarray(img_rgb), caption="📸 Captured Image", width=400)

        st.info("🎧 Fetching Spotify Recommendations...")

        recommendations = get_spotify_recommendations(genre_or_artist, emotion)

        if recommendations:
            st.subheader("🔊 Recommended Songs (Spotify):")
            for idx, song in enumerate(recommendations, 1):
                st.markdown(f"{idx}. [{song['name']}]({song['url']})")
        else:
            st.warning("⚠️ No Spotify recommendations found. Searching YouTube as fallback...")
            yt_query = f"{genre_or_artist} {emotion} music"
            yt_videos = get_youtube_videos(yt_query, max_results=10)
            if yt_videos:
                st.subheader("🎬 Recommended Videos (YouTube):")
                for idx, video in enumerate(yt_videos, 1):
                    st.markdown(f"{idx}. [{video['name']}]({video['url']})")
            else:
                st.error("❌ No recommendations found on YouTube either. Try a different artist or genre.")

if __name__ == "__main__":
    main()
