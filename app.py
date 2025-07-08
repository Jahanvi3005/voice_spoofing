import os
import requests
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_from_directory
from pymongo import MongoClient
import uuid # For unique filenames
import librosa # For audio processing
import numpy as np # For numerical operations
import tensorflow as tf # For loading and using the Keras model
from tensorflow.keras.models import load_model # Specific import for loading a *trained* model
from werkzeug.security import generate_password_hash, check_password_hash # For password hashing
from datetime import datetime # For timestamps in analysis history

# --- Flask App Setup ---
# Ensure static_folder is correctly set to 'static'
app = Flask(__name__, static_folder='static', template_folder='templates')

# Configure Secret Key for Sessions
# IMPORTANT: Use a strong, random key in production and load from environment variables!
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_super_secret_key_here')

# --- Configuration for Audio and Model ---
UPLOAD_FOLDER = 'uploads' # Folder to temporarily save audio files
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- MongoDB Configuration ---
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'voice_spoofing_db')

# Initialize MongoDB client and collections
client = None
db = None
users_collection = None
analyses_collection = None

try:
    client = MongoClient(MONGO_URI)
    
    client.admin.command('ping')
    db = client[MONGO_DB_NAME]
    users_collection = db.users
    analyses_collection = db.analyses
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"CRITICAL ERROR: Could not connect to MongoDB: {e}")
    print("Please check your MONGO_URI environment variable, database user credentials, and IP whitelist in MongoDB Atlas.")
    # In a production app, you might want to exit or handle this more gracefully
    # For now, we'll let the app continue but it will fail on DB operations.

# Model and audio processing constants
SAMPLE_RATE = 16000      # 16 kHz audio
CLIP_LENGTH = 5          # seconds per file
N_MELS = 128             # Mel spectrogram feature size
MAX_T = 501              # Expected time dimension of Mel spectrogram for 5-second clips
N_FFT = 400              # FFT window size
HOP_LENGTH = 160         # Hop length for spectrogram calculation

# Path to  model 
MODEL_SAVE_PATH = 'audio_spoof_model_improved_regularized_final.h5'

# Global variable for the local model
global_spoofing_model = None



def load_spoofing_model():
    """
    Loads the pre-trained voice spoofing detection model.
    This function will load the Keras model saved from your notebook.
    """
    global global_spoofing_model
    print(f"Attempting to load model from: {os.path.abspath(MODEL_SAVE_PATH)}")
    if not os.path.exists(MODEL_SAVE_PATH):
        print(f"Error: Model file NOT FOUND at {os.path.abspath(MODEL_SAVE_PATH)}. Please ensure it's in the correct directory.")
        global_spoofing_model = None
        return None
    try:
        # Clear any previous Keras session to ensure a fresh load
        tf.keras.backend.clear_session()
        global_spoofing_model = load_model(MODEL_SAVE_PATH)
        global_spoofing_model.summary() # Print model summary to confirm load
        print(f"Successfully loaded voice spoofing model from {MODEL_SAVE_PATH}")
    except Exception as e:
        print(f"CRITICAL ERROR loading spoofing model: {e}")
        print("Please ensure TensorFlow and Keras are correctly installed and the .h5 file is not corrupted.")
        global_spoofing_model = None
    return global_spoofing_model

def preprocess_audio_for_model(audio_path):
    """
    Processes an audio file to generate the Mel spectrogram features
    required by the TensorFlow model, following the logic from your notebook.
    """
    try:
        # Load audio using librosa
        try:
            audio, _ = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True) # Ensure mono and correct SR
        except Exception as e_load:
            print(f"ERROR: Failed to load audio file {audio_path} with librosa. Reason: {e_load}")
            print("This often indicates missing FFmpeg or libsndfile. Please check your system dependencies.")
            return None

        # Silence Trimming with Librosa
        audio_trimmed, _ = librosa.effects.trim(audio, top_db=60)
        if audio_trimmed.shape[0] == 0:
            # Handle empty audio after trim: return a dummy silent array
            audio_trimmed = np.zeros(int(SAMPLE_RATE * CLIP_LENGTH), dtype=np.float32) # Cast to int
            print("Warning: Audio was completely silent after trimming. Using dummy silent array.")

        # Ensure uniform length (padding or truncation)
        target_audio_length = int(SAMPLE_RATE * CLIP_LENGTH) # Cast to int
        if len(audio_trimmed) > target_audio_length:
            audio_processed = audio_trimmed[:target_audio_length]
        else:
            padding_needed = target_audio_length - len(audio_trimmed);
            audio_processed = np.pad(audio_trimmed, (0, padding_needed), mode='constant')

        # Generate Mel spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=audio_processed, sr=SAMPLE_RATE, n_mels=N_MELS, n_fft=N_FFT, hop_length=HOP_LENGTH
        )
        mel_db = librosa.power_to_db(mel_spec, ref=np.max)

        # DEBUG: Print shape before padding/truncation
        print(f"DEBUG: mel_db.shape[1] BEFORE padding/truncation: {mel_db.shape[1]}")

        # Ensure spectrogram time dimension is consistent with MAX_T
        if mel_db.shape[1] < MAX_T:
            pad_amt = MAX_T - mel_db.shape[1]
            mel_db = np.pad(mel_db, ((0,0),(0,pad_amt)), mode='constant')
            print(f"DEBUG: Padded mel_db to shape: {mel_db.shape}")
        elif mel_db.shape[1] > MAX_T:
            mel_db = mel_db[:, :MAX_T]
            print(f"DEBUG: Truncated mel_db to shape: {mel_db.shape}")

        # Add channel dimension and ensure float32 type for TensorFlow input
        # The model expects input shape (batch_size, N_MELS, MAX_T, 1)
        features = mel_db[np.newaxis, ..., np.newaxis].astype(np.float32)
        # DEBUG: Print final features shape
        print(f"DEBUG: Features shape before returning: {features.shape}")
        return features

    except Exception as e:
        print(f"Error processing audio for model: {e}")
        return None

# Routes 

@app.before_request
def before_request():
    # Load the model once when the app starts or before the first request
    global global_spoofing_model
    if global_spoofing_model is None:
        load_spoofing_model()

@app.route('/')
def index():
    """
    Serves the main application HTML page.
    """
    return render_template('app.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """
    Serves static files from the 'static' directory.
    This now correctly serves script.js and style.css from the 'static' folder.
    """
    return send_from_directory(app.static_folder, filename)

@app.route('/static/partials/<path:filename>')
def partial_html_files(filename):
    """
    Serves partial HTML files from the 'static/partials' directory.
    """
    return send_from_directory(os.path.join(app.static_folder, 'partials'), filename)

@app.route('/favicon.ico')
def favicon():
    """
    Serves the favicon.ico file.
    """
    return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# API Endpoints for User Authentication and Analysis Data
@app.route('/api/register', methods=['POST'])
def register_user():
    """
    Handles user registration.
    """
    if users_collection is None:
        return jsonify({"message": "Database not connected"}), 500

    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    if users_collection.find_one({"email": email}):
        return jsonify({"message": "User with this email already exists"}), 409

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    users_collection.insert_one({
        "email": email,
        "password_hash": hashed_password,
        "created_at": datetime.utcnow()
    })
    return jsonify({"message": "Registration successful"}), 201

@app.route('/api/login', methods=['POST'])
def login_user():
    """
    Handles user login.
    """
    if users_collection is None:
        return jsonify({"message": "Database not connected"}), 500

    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    user = users_collection.find_one({"email": email})
    if user and check_password_hash(user['password_hash'], password):
        session['user_email'] = email
        return jsonify({"message": "Login successful", "user_email": email}), 200
    else:
        return jsonify({"message": "Invalid email or password"}), 401

@app.route('/api/logout', methods=['POST'])
def logout_user():
    """
    Handles user logout.
    """
    session.pop('user_email', None)
    return jsonify({"message": "Logout successful"}), 200

@app.route('/api/current_user', methods=['GET'])
def get_current_user():
    """
    Returns the email of the currently logged-in user.
    """

    if 'user_email' in session:
        return jsonify({"user_email": session['user_email']}), 200
    return jsonify({"user_email": None}), 200

#  /api/analysis route to use local model 
@app.route('/api/analysis', methods=['POST'])
def analyze_voice_api():
    if 'user_email' not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    if analyses_collection is None:
        return jsonify({"message": "Database not connected"}), 500

    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': 'No selected audio file'}), 400

    # Model is loaded once at startup via @app.before_request.
    global global_spoofing_model
    if global_spoofing_model is None:
        print("Error: global_spoofing_model is None during analysis request. Model was not loaded at startup.")
        return jsonify({'error': 'Voice spoofing model not loaded. Please check server logs.'}), 500

    # Save the audio file temporarily
    unique_filename = str(uuid.uuid4()) + os.path.splitext(audio_file.filename)[1]
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    audio_file.save(audio_path)
    print(f"Processing audio file: {audio_file.filename} saved to {audio_path}") 

    try:
        # Preprocess audio for the model
        features = preprocess_audio_for_model(audio_path)
        if features is None:
            print(f"Error: Failed to preprocess audio for analysis for {audio_file.filename}.")
            return jsonify({'error': 'Failed to preprocess audio for analysis'}), 500

        # Perform prediction using the loaded Keras model
        # The model outputs probabilities for each class 
        predictions = global_spoofing_model.predict(features, verbose=0)[0]
        
        # label = 0 for 'spoofed' and 1 for 'bonafide' (genuine)
        
        spoofed_confidence = predictions[0]
        genuine_confidence = predictions[1]

        print(f"Raw predictions for {audio_file.filename}: Spoofed={spoofed_confidence:.4f}, Genuine={genuine_confidence:.4f}") # Updated for debugging
        
        # Decision logic 
        # Classify based on which confidence is higher
        if genuine_confidence > spoofed_confidence:
            result_type = "genuine"
            confidence = genuine_confidence
            message = "The voice is likely genuine."
            color = "green"
        else: # spoofed_confidence >= genuine_confidence
            result_type = "spoofed"
            confidence = spoofed_confidence
            message = "WARNING: The voice is likely AI-spoofed!"
            color = "red"


        response_data = {
            'result': result_type,
            'confidence': round(float(confidence * 100), 2), # Convert to percentage and then to standard float
            'isSpoofed': (result_type == "spoofed"), # Explicitly add for history
            'message': message,
            'color': color
        }
        print(f"Analysis result for {audio_file.filename}: {response_data}") 

        # Save to history if logged in
        from datetime import datetime
        analyses_collection.insert_one({
            "user_email": session['user_email'],
            "fileName": audio_file.filename,
            "isSpoofed": (result_type == "spoofed"), # Store boolean
            "confidence": response_data['confidence'], # This is now a standard Python float
            "timestamp": datetime.utcnow()
        })
        print(f"Analysis saved to history for user: {session['user_email']} for file {audio_file.filename}")

        return jsonify(response_data)

    except Exception as e:
        print(f"Unhandled error during voice analysis for {audio_file.filename}: {e}")
        return jsonify({'error': f'An unexpected error occurred during analysis: {e}'}), 500
    finally:
        # Clean up the temporary audio file
        print(f"Attempting to remove temporary audio file: {audio_path}")
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                print(f"Temporary audio file removed successfully: {audio_path}")
            except OSError as e:
                print(f"ERROR: Could not remove temporary audio file {audio_path}: {e}")
                print("This might be due to file permissions or the file being locked.")
        else:
            print(f"Temporary audio file not found at path: {audio_path}. Already removed or never created?")


@app.route('/api/analyses', methods=['GET'])
def get_analyses():
    """
    Retrieves all analysis results for the current user.
    """
    if 'user_email' not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    if analyses_collection is None:
        return jsonify({"message": "Database not connected"}), 500

    user_analyses = list(analyses_collection.find({"user_email": session['user_email']}).sort("timestamp", -1))
    # Convert ObjectId to string for JSON serialization
    for analysis in user_analyses:
        analysis['_id'] = str(analysis['_id'])
        # Ensure datetime objects are serialized correctly
        if 'timestamp' in analysis and isinstance(analysis['timestamp'], datetime):
            analysis['timestamp'] = analysis['timestamp'].isoformat()
    return jsonify({"analyses": user_analyses}), 200

# /api/news endpoint 
NEWS_API_KEY = os.environ.get('NEWS_API_KEY', '4004719a0aa54f07868c82c0aabc8e88') # Your actual NewsAPI.org key
NEWS_API_URL = "https://newsapi.org/v2/everything"

@app.route('/api/news', methods=['GET'])
def get_news():
    """
    Fetches news articles related to voice spoofing from NewsAPI.org.
    Falls back to mock data if API call fails.
    """
    # Mock data to be used as a fallback
    mock_news_articles = [
        {
            "id": 1,
            "title": "New AI Voice Spoofing Attacks Target Financial Institutions",
            "description": "Recent reports indicate a surge in sophisticated AI-generated voice attacks aimed at defrauding customers of major banks.",
            "url": "https://example.com/news/article1",
            "source": "CyberSecurity Today",
            "publishedAt": "2024-07-01T10:00:00Z"
        },
        {
            "id": 2,
            "title": "How Deepfake Voices Are Being Used in Phishing Scams",
            "description": "An in-depth look at the techniques criminals use to create convincing deepfake voices for social engineering and phishing.",
            "url": "https://example.com/news/article2",
            "source": "Tech Insights",
            "publishedAt": "2024-06-28T14:30:00Z"
        },
        {
            "id": 3,
            "title": "Voice Biometrics vs. AI Spoofing: The Ongoing Battle",
            "description": "Experts discuss the evolving cat-and-mouse game between voice biometric security systems and advanced AI voice synthesis.",
            "url": "https://example.com/news/article3",
            "source": "Security Weekly",
            "publishedAt": "2024-06-25T09:15:00Z"
        },
        {
            "id": 4,
            "title": "Detecting Synthetic Speech: New Research Breakthroughs",
            "description": "Researchers announce significant progress in developing algorithms capable of identifying subtle artifacts in AI-generated speech.",
            "url": "https://example.com/news/article4",
            "source": "AI Journal",
            "publishedAt": "2024-06-20T11:00:00Z"
        },
        {
            "id": 5,
            "title": "The Ethical Implications of Voice Cloning Technology",
            "description": "A discussion on the societal and ethical challenges posed by readily available voice cloning tools and their potential for misuse.",
            "url": "https://example.com/news/article5",
            "source": "Ethics in AI",
            "publishedAt": "2024-06-15T16:00:00Z"
        }
    ]

    # Check if API key is configured. If not, return mock data immediately.
    if not NEWS_API_KEY or NEWS_API_KEY == 'YOUR_NEWSAPI_API_KEY':
        print("NEWS_API_KEY is not set or is a placeholder. Returning mock news data.")
        return jsonify({"articles": mock_news_articles, "message": "API key not configured, returning mock data."}), 200

    params = {
        
        'q': '("voice spoofing" OR "deepfake voice" OR "synthetic voice detection" )',
        'language': 'en',
        'sortBy': 'relevancy', 
        'apiKey': NEWS_API_KEY,
        'pageSize': 5
    }

    try:
        response = requests.get(NEWS_API_URL, params=params)
        response.raise_for_status() 
        news_data = response.json()
        
        articles = []
        if news_data.get('articles'):
            for i, article in enumerate(news_data['articles']):
                articles.append({
                    "id": i + 1,
                    "title": article.get('title'),
                    "description": article.get('description'),
                    "url": article.get('url'),
                    "source": article['source'].get('name') if article.get('source') else 'Unknown',
                    "publishedAt": article.get('publishedAt')
                })
        print(f"Fetched {len(articles)} articles from NewsAPI.org.")
        return jsonify({"articles": articles}), 200

    except requests.exceptions.RequestException as e:
        print(f"Error fetching news from NewsAPI: {e}")
        # Fallback to mock data on API error
        return jsonify({"articles": mock_news_articles, "error": f"Failed to fetch news from API: {e}. Returning mock data."}), 500


if __name__ == '__main__':
    # Try to load the model at startup
    load_spoofing_model()
   
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))