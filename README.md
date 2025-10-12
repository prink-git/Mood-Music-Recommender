# **Mood Music Recommender**
## 🚀 **Project Overview**
The **Mood Music Recommender** is a web app that generates personalized music playlists based on the user’s mood. By integrating **Spotify's API** and **DeepFace** for facial emotion recognition, this app provides real-time music recommendations through an intuitive **Streamlit** interface.

## 🔑 **Key Features**
- **Mood Detection**: Uses **DeepFace** to analyze facial expressions and determine the user's emotional state (e.g., happy, sad, angry).
- **Spotify Integration**: Fetches music playlists that match the detected mood via the **Spotify API**.
- **YouTube Fallback**: In case Spotify is unavailable, the app falls back to **YouTube** for music recommendations.
- **User-friendly Interface**: Built with **Streamlit**, offering an interactive UI for easy user engagement.

## ⚙️ **Tech Stack**
- **Frontend**: **Streamlit** (for web app development).
- **Backend**: **Python** (handles mood detection, music recommendations).
- **APIs**:
  - **Spotify API**: For fetching music based on mood.
  - **DeepFace**: For facial emotion recognition.
  - **YouTube API**: For fallback music recommendations.
- **Libraries**: **requests**, **dotenv**, **numpy**, **pandas**, **opencv-python**, **spotipy**, etc.

## 🛠 **Installation & Setup**
Follow these steps to set up the project locally:

```bash
#1. Clone the Repository
git clone https://github.com/prink-git/Mood-Music-Recommender.git
cd Mood-Music-Recommender

#2. Create a Virtual Environment
python -m venv mood-music-env

#3. Activate the Virtual Environment
#For Windows:
mood-music-env\Scripts\activate
#For macOS/Linux:
source mood-music-env/bin/activate

#4. Install Dependencies
pip install -r requirements.txt

#5. Set Up API Keys
#Create a .env file in the root directory of project and add the following keys:
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=your_spotify_redirect_uri
YOUTUBE_API_KEY=your_youtube_api_key
#Replace the placeholder values with actual API keys

#6. Run the Application
streamlit run app.py
#The app will open in the browser at http://localhost:8501
