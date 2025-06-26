import os
import io
import base64
import numpy as np
import librosa
import tensorflow as tf
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson.binary import Binary 
from datetime import datetime
from pydub import AudioSegment # New import for audio conversion

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a_very_secret_key_for_demo_purposes_only')

# --- MongoDB Configuration ---
# IMPORTANT: For Render deployment, replace 'mongodb://localhost:27017/' with your MongoDB Atlas URI.
# Example: "mongodb+srv://<username>:<password>@<cluster-url>/voice_spoofing_db?retryWrites=true&w=majority"
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = 'voice_spoofing_db'
USERS_COLLECTION_NAME = 'users'
AUDIO_RECORDS_COLLECTION_NAME = 'audio_records' 

try:
    mongo_client = MongoClient(MONGO_URI)
    db_mongo = mongo_client[DB_NAME]
    users_collection = db_mongo[USERS_COLLECTION_NAME]
    audio_records_collection = db_mongo[AUDIO_RECORDS_COLLECTION_NAME] 
    print(f"[{os.path.basename(__file__)}] MongoDB connected successfully to '{DB_NAME}' database.")
except Exception as e:
    print(f"[{os.path.basename(__file__)}] ERROR: MongoDB connection failed: {e}")
    mongo_client = None
    db_mongo = None
    users_collection = None # Ensure it's None if connection fails
    audio_records_collection = None # Ensure it's None if connection fails

# --- Configuration for Audio Processing and CNN Model ---
TARGET_SAMPLE_RATE = 16000
N_MFCC = 40
TARGET_MFCC_FRAMES = 94 

MODEL_DIR = "your_model_files" 
MODEL_NAME = "your_cnn_model.h5" 
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_NAME)

# Global variable to store the last prediction result for the Results page
last_prediction_result = {
    "verdict": "No analysis performed yet.",
    "confidence": {"Genuine": 0.5, "Spoofed": 0.5}
}

print(f"[{os.path.basename(__file__)}] Initializing Flask app...")

# --- CNN Model Loading ---
CNN_MODEL = None
try:
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
        print(f"[{os.path.basename(__file__)}] Created directory: {MODEL_DIR}")

    if os.path.exists(MODEL_PATH):
        CNN_MODEL = tf.keras.models.load_model(MODEL_PATH)
        print(f"[{os.path.basename(__file__)}] CNN model loaded successfully from {MODEL_PATH}.")
    else:
        print(f"[{os.path.basename(__file__)}] Model file not found at {MODEL_PATH}. Creating a dummy CNN model.")
        CNN_MODEL = tf.keras.models.Sequential([
            tf.keras.layers.InputLayer(input_shape=(N_MFCC, TARGET_MFCC_FRAMES, 1)),
            tf.keras.layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
            tf.keras.layers.MaxPooling2D((2, 2)),
            tf.keras.layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
            tf.keras.layers.MaxPooling2D((2, 2)),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dropout(0.5),
            tf.keras.layers.Dense(2, activation='softmax')
        ])
        CNN_MODEL.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
        CNN_MODEL.save(MODEL_PATH)
        print(f"[{os.path.basename(__file__)}] Dummy CNN model created and saved to {MODEL_PATH}.")
        print(f"[{os.path.basename(__file__)}] This model will produce random-like predictions as it's untrained.")

except Exception as e:
    CNN_MODEL = None
    print(f"[{os.path.basename(__file__)}] ERROR: Loading or creating CNN model failed: {e}. Predictions will fallback to random dummy values.")

# --- Language Translations ---
TRANSLATIONS = {
    'app_title': {'en': 'Voice Spoofing Detector', 'hi': 'वॉयस स्पूफिंग डिटेक्टर'},
    'dashboard_title': {'en': 'Dashboard', 'hi': 'डैशबोर्ड'},
    'home_nav': {'en': 'Home', 'hi': 'होम'},
    'results_nav': {'en': 'Results', 'hi': 'परिणाम'},
    'account_nav': {'en': 'Account', 'hi': 'खाता'},
    'logout_btn': {'en': 'Logout', 'hi': 'लॉग आउट'},
    'login_title': {'en': 'Login or Register', 'hi': 'लॉगिन या रजिस्टर करें'},
    'login_prompt': {'en': 'Please enter your credentials.', 'hi': 'कृपया अपनी क्रेडेंशियल दर्ज करें।'},
    'username_label': {'en': 'Username:', 'hi': 'यूज़रनेम:'},
    'password_label': {'en': 'Password:'},
    'login_btn': {'en': 'Login', 'hi': 'लॉगिन करें'},
    'register_btn': {'en': 'Register', 'hi': 'रजिस्टर करें'},
    'reg_info': {'en': 'If username does not exist, an account will be created.', 'hi': 'यदि यूज़रनेम मौजूद नहीं है, तो एक खाता बनाया जाएगा।'},
    'home_tagline': {'en': 'Upload an audio file or record your voice to determine if it\'s genuine or spoofed.', 'hi': 'यह निर्धारित करने के लिए ऑडियो फ़ाइल अपलोड करें या अपनी आवाज़ रिकॉर्ड करें कि यह वास्तविक है या स्पूफ़ेड।'},
    'input_audio_header': {'en': 'Input Audio', 'hi': 'ऑडियो इनपुट'},
    'drag_drop_prompt': {'en': 'Drag & Drop Audio File Here', 'hi': 'यहां ऑडियो फ़ाइल खींचें और छोड़ें'},
    'or_click_browse': {'en': 'Or Click to Browse', 'hi': 'या ब्राउज़ करने के लिए क्लिक करें'},
    'record_audio_prompt': {'en': 'Or Record Live Audio', 'hi': 'या लाइव ऑडियो रिकॉर्ड करें'},
    'start_recording_btn': {'en': 'Start Recording', 'hi': 'रिकॉर्डिंग शुरू करें'},
    'stop_recording_btn': {'en': 'Stop Recording', 'hi': 'रिकॉर्डिंग बंद करें'},
    'analyze_audio_btn': {'en': 'Analyze Audio', 'hi': 'ऑडियो का विश्लेषण करें'},
    'detection_results_header': {'en': 'Detection Results', 'hi': 'जाँच के परिणाम'},
    'overall_verdict': {'en': 'Overall Verdict:', 'hi': 'कुल मिलाकर निर्णय:'},
    'confidence_scores': {'en': 'Confidence Scores:', 'hi': 'विश्वसनीयता स्कोर:'},
    'genuine': {'en': 'Genuine', 'hi': 'वास्तविक'}, # Changed to just the word for flexible use
    'spoofed': {'en': 'Spoofed', 'hi': 'स्पूफ़ेड'},   # Changed to just the word for flexible use
    'play_audio': {'en': 'Play Submitted Audio:', 'hi': 'सबमिट किया गया ऑडियो चलाएं:'},
    'clear_all_btn': {'en': 'Clear All', 'hi': 'सभी साफ करें'},
    'no_analysis_yet': {'en': 'No analysis yet.', 'hi': 'अभी तक कोई विश्लेषण नहीं हुआ है।'},
    'analyzing_audio': {'en': 'Analyzing audio...', 'hi': 'ऑडियो का विश्लेषण हो रहा है...'},
    'no_audio_provided': {'en': 'Please provide audio first (upload or record).', 'hi': 'पहले ऑडियो प्रदान करें (अपलोड करें या रिकॉर्ड करें)।'},
    'network_error': {'en': 'Network Error', 'hi': 'नेटवर्क त्रुटि'},
    'analysis_summary': {'en': 'Quick Summary:', 'hi': 'त्वरित सारांश:'},
    'view_full_history': {'en': 'View Full Analysis History', 'hi': 'पूरा विश्लेषण इतिहास देखें'},
    'thank_you_title': {'en': 'Analysis Complete! Thank You!', 'hi': 'विश्लेषण पूर्ण! धन्यवाद!'},
    'thank_you_message': {'en': 'Your audio has been successfully analyzed.', 'hi': 'आपके ऑडियो का सफलतापूर्वक विश्लेषण किया गया है।'},
    'last_analysis_results': {'en': 'Last Analysis Results', 'hi': 'अंतिम विश्लेषण परिणाम'},
    'history_header': {'en': 'Your Audio Analysis History', 'hi': 'आपका ऑडियो विश्लेषण इतिहास'},
    'analysis_time': {'en': 'Analysis Time:', 'hi': 'विश्लेषण का समय:'},
    'file_label': {'en': 'File:', 'hi': 'फ़ाइल:'},
    'original_audio': {'en': 'Original Audio:', 'hi': 'मूल ऑडियो:'},
    'no_records_found': {'en': 'No previous analysis records found for your account.', 'hi': 'आपके खाते के लिए कोई पिछला विश्लेषण रिकॉर्ड नहीं मिला।'},
    'audio_data_not_available': {'en': 'Audio data not available.', 'hi': 'ऑडियो डेटा उपलब्ध नहीं है।'},
    'account_header': {'en': 'My Account', 'hi': 'मेरा खाता'},
    'account_tagline': {'en': 'View and manage your account settings.', 'hi': 'अपनी खाता सेटिंग्स देखें और प्रबंधित करें।'},
    'user_info_header': {'en': 'User Information', 'hi': 'उपयोगकर्ता जानकारी'},
    'username_display': {'en': 'Username:', 'hi': 'यूज़रनेम:'},
    'preferred_theme': {'en': 'Preferred Theme:', 'hi': 'पसंदीदा थीम:'},
    'account_created': {'en': 'Account Created:', 'hi': 'खाता बनाया गया:'},
    'last_login': {'en': 'Last Login:', 'hi': 'अंतिम लॉगिन:'},
    'save_preferences_btn': {'en': 'Save Preferences', 'hi': 'पसंद सहेजें'},
    'no_user_data': {'en': 'No user data found. Please log in.', 'hi': 'कोई उपयोगकर्ता डेटा नहीं मिला। कृपया लॉग इन करें।'},
    'toggle_theme': {'en': 'Toggle Theme', 'hi': 'थीम टॉगल करें'},
    'light_mode': {'en': 'Light', 'hi': 'लाइट'},
    'dark_mode': {'en': 'Dark', 'hi': 'डार्क'},
    'select_language': {'en': 'Select Language:', 'hi': 'भाषा चुनें:'},
    'recording_status_recording': {'en': 'Recording...', 'hi': 'रिकॉर्डिंग हो रही है...'},
    'recording_status_stop_prompt': {'en': 'Recording (Click to stop)', 'hi': 'रिकॉर्डिंग (रोकने के लिए क्लिक करें)'},
    'recording_status_finished': {'en': 'Recording finished. Ready for analysis.', 'hi': 'रिकॉर्डिंग समाप्त। विश्लेषण के लिए तैयार।'},
    'mic_error': {'en': 'Error accessing microphone. Please ensure permissions are granted.', 'hi': 'माइक्रोफ़ोन तक पहुंचने में त्रुटि। कृपया सुनिश्चित करें कि अनुमतियाँ दी गई हैं।'},
    'file_selected': {'en': 'File selected:', 'hi': 'फ़ाइल चुनी गई:'},
    'upload_file_label': {'en': 'Upload Audio File (.wav, .mp3)', 'hi': 'ऑडियो फ़ाइल अपलोड करें (.wav, .mp3)'},
    'logged_in_as': {'en': 'Logged in as: ', 'hi': 'के रूप में लॉग इन किया गया है: '}, 
    'supported': {'en': 'supported', 'hi': 'समर्थित'},
    'user_not_authenticated': {'en': 'User not authenticated.', 'hi': 'उप उपयोगकर्ता प्रमाणित नहीं है।'},
    'no_audio_file_provided': {'en': 'No audio file provided.', 'hi': 'कोई ऑडियो फ़ाइल प्रदान नहीं की गई।'},
    'failed_load_audio_empty': {'en': 'Failed to load audio: Empty or invalid audio data after librosa.load.', 'hi': 'ऑडियो लोड करने में विफल: librosa.load के बाद खाली या अमान्य ऑडियो डेटा।'},
    'failed_preprocess_audio': {'en': 'Failed to preprocess audio (e.g., audio too short or silent).', 'hi': 'ऑडियो को प्रीप्रोसेस करने में विफल (जैसे, ऑडियो बहुत छोटा या मौन)।'},
    'audio_processing_failed': {'en': 'Audio processing failed', 'hi': 'ऑडियो प्रोसेसिंग विफल हुई'},
    'please_login_access_dashboard': {'en': 'Please log in to access the dashboard.', 'hi': 'डैशबोर्ड तक पहुंचने के लिए कृपया लॉग इन करें।'},
    'invalid_session_login_again': {'en': 'Your session is invalid. Please log in again.', 'hi': 'आपका सत्र अमान्य है। कृपया फिर से लॉग इन करें।'},
    'please_login_view_account': {'en': 'Please log in to view your account.', 'hi': 'अपना खाता देखने के लिए कृपया लॉग इन करें।'},
    'database_not_available': {'en': 'Database not available. Please contact admin.', 'hi': 'डेटाबेस उपलब्ध नहीं है। कृपया व्यवस्थापक से संपर्क करें।'},
    'username_password_required': {'en': 'Username and password are required.', 'hi': 'यूज़रनेम और पासवर्ड आवश्यक हैं।'},
    'username_exists': {'en': 'Username already exists. Please choose a different one or log in.', 'hi': 'यूज़रनेम पहले से मौजूद है। कृपया कोई भिन्न चुनें या लॉग इन करें।'},
    'account_created_logged_in': {'en': 'Account created and logged in successfully for {username}!', 'hi': '{username} के लिए खाता सफलतापूर्वक बनाया और लॉग इन किया गया!'},
    'welcome_back': {'en': 'Welcome back, {username}!', 'hi': 'वापस स्वागत है, {username}!'},
    'invalid_username_password': {'en': 'Invalid username or password.', 'hi': 'अमान्य यूज़रनेम या पासवर्ड।'},
    'username_not_found': {'en': 'Username not found. Please register or check your username.', 'hi': 'यूज़रनेम नहीं मिला। कृपया रजिस्टर करें या अपना यूज़रनेम जांचें।'},
    'invalid_action': {'en': 'Invalid action.', 'hi': 'अमान्य कार्रवाई।'},
    'an_error_occurred': {'en': 'An error occurred', 'hi': 'एक त्रुटि हुई'},
    'logged_out_successfully': {'en': 'You have been logged out successfully!', 'hi': 'आप सफलतापूर्वक लॉग आउट हो गए हैं!'},
    'results_tagline': {'en': 'Here are the results from your most recent voice analysis.', 'hi': 'यहां आपके सबसे हाल के वॉयस विश्लेषण के परिणाम दिए गए हैं।'},
    'welcome_back_generic': {'en': 'Welcome!', 'hi': 'स्वागत है!'},
    'to_our_channel': {'en': 'To Our Application', 'hi': 'हमारे एप्लिकेशन में'},
    'login_page_intro_text': {'en': 'Analyze voice for spoofing detection. Log in or register to get started.', 'hi': 'स्पूफिंग डिटेक्शन के लिए आवाज का विश्लेषण करें। शुरू करने के लिए लॉग इन करें या रजिस्टर करें।'},
    'remember_me': {'en': 'Remember Me', 'hi': 'मुझे याद रखें'},
    'forget_password': {'en': 'Forgot Password?', 'hi': 'पासवर्ड भूल गए?'},
    'dont_have_account': {'en': 'Don\'t have an account?', 'hi': 'खाता नहीं है?'},
    'already_have_account': {'en': 'Already have an account?', 'hi': 'पहले से ही खाता है?'},
    'download_audio': {'en': 'Download Audio', 'hi': 'ऑडियो डाउनलोड करें'}, # Added new translation
    'playback_speed': {'en': 'Playback Speed', 'hi': 'प्लेबैक गति'}, # Added new translation
    'welcome_to_voicesentinel': {'en': 'Welcome to VoiceSentinel!', 'hi': 'वॉयससेंटिनल में आपका स्वागत है!'}, 
    'voicesentinel_description_part1': {'en': 'Your ultimate solution for detecting voice spoofing. In an era where digital voices are becoming indistinguishable from real ones, securing your verbal interactions is paramount. Our advanced system uses cutting-edge machine learning to identify synthetic or manipulated voices, ensuring your peace of mind in a world of evolving threats.', 'hi': 'वॉयस स्पूफिंग का पता लगाने के लिए आपका अंतिम समाधान। ऐसे युग में जहां डिजिटल आवाजें वास्तविक लोगों से अप्रभेद्य होती जा रही हैं, आपके मौखिक इंटरैक्शन को सुरक्षित करना सर्वोपरि है। हमारी उन्नत प्रणाली सिंथेटिक या हेरफेर की गई आवाजों की पहचान करने के लिए अत्याधुनिक मशीन लर्निंग का उपयोग करती है, जो विकसित होती खतरों की दुनिया में आपकी मन की शांति सुनिश्चित करती है।'}, 
    'voicesentinel_description_part2': {'en': 'Simply upload an audio file or use your microphone to get an instant analysis. Protect your privacy and security with confidence.', 'hi': 'तत्काल विश्लेषण प्राप्त करने के लिए बस एक ऑडियो फ़ाइल अपलोड करें या अपने माइक्रोफ़ोन का उपयोग करें। आत्मविश्वास के साथ अपनी गोपनीयता और सुरक्षा को सुरक्षित रखें।'}, 
    'rise_of_spoofing_attacks': {'en': 'The Rise of Voice Spoofing Attacks', 'hi': 'वॉयस स्पूफिंग हमलों का उदय'},
    # Condensed description to two sentences:
    'rise_of_spoofing_attacks_description': {
        'en': 'Voice spoofing is a growing concern where artificial voices bypass security. Our system analyzes audio to distinguish between genuine and spoofed voices, providing a robust defense.',
        'hi': 'वॉयस स्पूफिंग एक बढ़ती चिंता है जहां कृत्रिम आवाजें सुरक्षा को दरकिनार करती हैं। हमारा सिस्टम वास्तविक और स्पूफ़ेड आवाजों के बीच अंतर करने के लिए ऑडियो का विश्लेषण करता है, जिससे एक मजबूत रक्षा मिलती है।'
    },
    'not_audio_file': {'en': 'Please drop an audio file.', 'hi': 'कृपया एक ऑडियो फ़ाइल गिराएँ।'}, 
    'not_audio_file_uploaded': {'en': 'Please upload an audio file.', 'hi': 'कृपया एक ऑडियो फ़ाइल अपलोड करें।'}, 
    'no_audio_to_download': {'en': 'No audio to download.', 'hi': 'डाउनलोड करने के लिए कोई ऑडियो नहीं है।'}, 
}

def get_translated_text(key):
    """Retrieves translated text based on the session's preferred language."""
    lang = session.get('preferred_language', 'en')
    return TRANSLATIONS.get(key, {}).get(lang, TRANSLATIONS.get(key, {}).get('en', key))

@app.context_processor
def inject_translations():
    """Injects translation function and current language into all templates."""
    return dict(get_text=get_translated_text, current_language=session.get('preferred_language', 'en'))


# --- Audio Preprocessing Function ---
def preprocess_audio(audio_data, original_sr):
    if original_sr != TARGET_SAMPLE_RATE:
        audio_data = librosa.resample(y=audio_data, orig_sr=original_sr, target_sr=TARGET_SAMPLE_RATE)
        original_sr = TARGET_SAMPLE_RATE
    if audio_data.size == 0:
        print(f"[{os.path.basename(__file__)}] Warning: Empty audio data after resampling.")
        return None
    mfccs = librosa.feature.mfcc(y=audio_data, sr=original_sr, n_mfcc=N_MFCC)
    if mfccs.shape[1] < TARGET_MFCC_FRAMES:
        pad_width = TARGET_MFCC_FRAMES - mfccs.shape[1]
        mfccs = np.pad(mfccs, pad_width=((0, 0), (0, pad_width)), mode='constant')
    elif mfccs.shape[1] > TARGET_MFCC_FRAMES:
        mfccs = mfccs[:, :TARGET_MFCC_FRAMES]
    min_val = np.min(mfccs)
    max_val = np.max(mfccs)
    if (max_val - min_val) > 0:
        mfccs = (mfccs - min_val) / (max_val - min_val)
    else:
        mfccs = np.zeros_like(mfccs)
    processed_features = mfccs[np.newaxis, :, :, np.newaxis]
    return processed_features

# --- CNN Prediction Function ---
def predict_with_cnn(features):
    if CNN_MODEL is None:
        random_score = np.random.rand()
        if random_score > 0.6:
            prob_genuine = np.random.uniform(0.7, 0.95)
            prob_spoofed = 1.0 - prob_genuine
        elif random_score < 0.3:
            prob_spoofed = np.random.uniform(0.7, 0.95)
            prob_genuine = 1.0 - prob_spoofed
        else:
            prob_genuine = np.random.uniform(0.4, 0.6)
            prob_spoofed = 1.0 - prob_genuine
        probs = np.array([prob_genuine, prob_spoofed])
        probs = probs / np.sum(probs)
        probs = np.clip(probs, 0.001, 0.999)
        
        # Determine verdict based on probabilities and then get localized text
        if probs[0] > probs[1]:
            verdict_en = "✅ Genuine" # Store English verdict for consistent frontend logic
            verdict_current_lang = f"✅ {get_translated_text('genuine')}"
        else:
            verdict_en = "🔴 Spoofed Voice Detected!" # Store English verdict
            verdict_current_lang = f"🔴 {get_translated_text('spoofed')}"
            
        confidence_breakdown = {"Genuine": float(probs[0]), "Spoofed": float(probs[1])}
        return verdict_current_lang, verdict_en, confidence_breakdown
    try:
        predictions = CNN_MODEL.predict(features, verbose=0)[0]
        prob_genuine = predictions[0]
        prob_spoofed = predictions[1]
        
        # Determine verdict based on probabilities and then get localized text
        if prob_genuine > prob_spoofed:
            verdict_en = "✅ Genuine" # Store English verdict for consistent frontend logic
            verdict_current_lang = f"✅ {get_translated_text('genuine')}" 
        else:
            verdict_en = "🔴 Spoofed Voice Detected!" # Store English verdict
            verdict_current_lang = f"🔴 {get_translated_text('spoofed')}" 

        confidence_breakdown = {"Genuine": float(prob_genuine), "Spoofed": float(prob_spoofed)}
        return verdict_current_lang, verdict_en, confidence_breakdown
    except Exception as e:
        print(f"[{os.path.basename(__file__)}] Error during CNN prediction: {e}")
        return f"Prediction Error: {e}", f"Prediction Error: {e}", {"Genuine": 0.5, "Spoofed": 0.5}

@app.before_request
def check_login_and_load_user_data():
    # Set default language if not in session (e.g., first visit, or after logout)
    if 'preferred_language' not in session:
        session['preferred_language'] = 'en' # Default to English

    # Allow access to static files, login page, and login submission without authentication
    if request.path.startswith('/static/') or request.path == '/login' or request.path == '/login_submit':
        return 
    
    if 'user_id' not in session:
        print(f"[{os.path.basename(__file__)}] No user_id in session. Redirecting to login.")
        flash(get_translated_text('please_login_access_dashboard'), 'error') # Translated flash message
        return redirect(url_for('login'))
    
    # FIX: Use 'is not None' for PyMongo collection objects
    if users_collection is not None:
        user_doc = users_collection.find_one({'username': session['user_id']})
        if user_doc:
            session['preferred_mode'] = user_doc.get('preferred_mode', 'light') 
            session['preferred_language'] = user_doc.get('preferred_language', 'en') # Load preferred language
        else:
            # If user_id exists in session but not in DB, clear session
            session.pop('user_id', None)
            session.pop('preferred_mode', None)
            session.pop('preferred_language', None)
            flash(get_translated_text('invalid_session_login_again'), 'error') # Translated flash message
            return redirect(url_for('login'))
    else: # If users_collection is None, it means DB connection failed at startup
        print(f"[{os.path.basename(__file__)}] WARNING: users_collection is None. Database not available for session check.")
        flash(get_translated_text('database_not_available'), 'error')
        # You might want to redirect to a special error page or login with a clearer message here
        return redirect(url_for('login'))


    print(f"[{os.path.basename(__file__)}] User '{session.get('user_id')}' logged in. Preferred mode: {session.get('preferred_mode')}. Language: {session.get('preferred_language')}. Proceeding.")

@app.route('/')
def root_redirect():
    """Redirects to the home page."""
    return redirect(url_for('home'))

@app.route('/home')
def home():
    """Renders the home page with audio input."""
    print(f"[{os.path.basename(__file__)}] Accessing home route.")
    try:
        return render_template('home.html', last_prediction=last_prediction_result,
                               user_name=session.get('user_id'), preferred_mode=session.get('preferred_mode'))
    except Exception as e:
        print(f"[{os.path.basename(__file__)}] ERROR: Exception during home rendering: {e}")
        return "<h1>Server Error</h1><p>Could not load home page: " + str(e) + "</p><p>Check Flask terminal for details.</p>", 500

@app.route('/results')
def results():
    """Renders the results page."""
    print(f"[{os.path.basename(__file__)}] Accessing results route.")
    try:
        user_audio_records = []
        # FIX: Use 'is not None' for PyMongo collection objects
        if audio_records_collection is not None and 'user_id' in session:
            # Sort by timestamp descending to show most recent first
            user_audio_records = list(audio_records_collection.find({'user_id': session['user_id']}).sort('timestamp', -1))
            # Format datetime objects for display if necessary
            for record in user_audio_records:
                if 'timestamp' in record and isinstance(record['timestamp'], datetime):
                    record['formatted_timestamp'] = record['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                else:
                    record['formatted_timestamp'] = 'N/A'
                # Convert Binary audio data to base64 for embedding in HTML audio tag
                if 'audio_data' in record and isinstance(record['audio_data'], Binary):
                    record['audio_data_b64'] = base64.b64encode(record['audio_data']).decode('utf-8')
                    record['audio_data_url'] = f"data:{record.get('audio_mimetype', 'audio/wav')};base64,{record['audio_data_b64']}"
                else:
                    record['audio_data_url'] = ''

        return render_template('results.html', last_prediction=last_prediction_result,
                               user_name=session.get('user_id'), preferred_mode=session.get('preferred_mode'),
                               user_audio_records=user_audio_records)
    except Exception as e:
        print(f"[{os.path.basename(__file__)}] ERROR: Exception during results rendering: {e}")
        return "<h1>Server Error</h1><p>Could not load results page: " + str(e) + "</p><p>Check Flask terminal for details.</p>", 500

@app.route('/account', methods=['GET'])
def account():
    """Renders the account page."""
    print(f"[{os.path.basename(__file__)}] Accessing account route.")
    if 'user_id' not in session:
        flash(get_translated_text('please_login_view_account'), 'error') 
        return redirect(url_for('login'))
    
    user_data = None
    # FIX: Use 'is not None' for PyMongo collection objects
    if users_collection is not None:
        user_data = users_collection.find_one({'username': session['user_id']})
    
    return render_template('account.html', user_data=user_data,
                           user_name=session.get('user_id'), preferred_mode=session.get('preferred_mode'))

@app.route('/update_preferences', methods=['POST'])
def update_preferences():
    """Updates user preferences (preferred_mode and preferred_language) in the database."""
    print(f"[{os.path.basename(__file__)}] Accessing update_preferences route.")
    if 'user_id' not in session:
        print(f"[{os.path.basename(__file__)}] User not logged in for preference update.")
        return jsonify({"success": False, "message": "Not logged in."}), 401
    
    if users_collection is None:
        print(f"[{os.path.basename(__file__)}] Database not available for preference update.")
        return jsonify({"success": False, "message": get_translated_text('database_not_available')}), 500

    user_id = session['user_id']
    data = request.get_json()
    update_fields = {}

    # Handle preferred_mode update
    if 'preferred_mode' in data:
        new_mode = data.get('preferred_mode')
        if new_mode in ['light', 'dark']:
            update_fields['preferred_mode'] = new_mode
            session['preferred_mode'] = new_mode 
            print(f"[{os.path.basename(__file__)}] User '{user_id}' updated preferred_mode to '{new_mode}'.")
        else:
            print(f"[{os.path.basename(__file__)}] Invalid mode received: {new_mode}")
            return jsonify({"success": False, "message": "Invalid mode."}), 400

    # Handle preferred_language update
    if 'preferred_language' in data:
        new_language = data.get('preferred_language')
        if new_language in ['en', 'hi']: # Validate supported languages
            update_fields['preferred_language'] = new_language
            session['preferred_language'] = new_language # Update session immediately
            print(f"[{os.path.basename(__file__)}] User '{user_id}' updated preferred_language to '{new_language}'.")
        else:
            print(f"[{os.path.basename(__file__)}] Invalid language received: {new_language}")
            return jsonify({"success": False, "message": "Invalid language."}), 400

    if not update_fields:
        print(f"[{os.path.basename(__file__)}] No preferences provided in request body.")
        return jsonify({"success": False, "message": "No preferences provided to update."}), 400

    try:
        users_collection.update_one({'username': user_id}, {'$set': update_fields})
        print(f"[{os.path.basename(__file__)}] Preferences saved to DB for '{user_id}': {update_fields}")
        return jsonify({"success": True, "message": "Preferences updated."})
    except Exception as e:
        print(f"[{os.path.basename(__file__)}] ERROR updating preferences for '{user_id}': {e}")
        return jsonify({"success": False, "message": f"Failed to update preferences: {e}"}), 500

# Removed the separate /update_language_preference route as it's merged into /update_preferences


@app.route('/login', methods=['GET']) 
def login():
    """Renders the login/registration page."""
    print(f"[{os.path.basename(__file__)}] Accessing login GET route.")
    try:
        return render_template('login.html')
    except Exception as e:
        print(f"[{os.path.basename(__file__)}] ERROR: Exception during login rendering: {e}")
        return "<h1>Server Error</h1><p>Could not load login page: " + str(e) + "</p>", 500


@app.route('/login_submit', methods=['POST'])
def login_submit():
    """Handles login form submission."""
    print(f"[{os.path.basename(__file__)}] Accessing login POST route.")
    username = request.form.get('username')
    password = request.form.get('password')
    action = request.form.get('action') 

    # FIX: Use 'is None' for PyMongo collection objects
    if users_collection is None:
        print(f"[{os.path.basename(__file__)}] ERROR: MongoDB connection not established or users_collection is None.")
        flash(get_translated_text('database_not_available'), 'error') 
        return redirect(url_for('login'))

    if not username or not password:
        flash(get_translated_text('username_password_required'), 'error') 
        return redirect(url_for('login'))

    try:
        user_doc = users_collection.find_one({'username': username})

        if action == 'register':
            if user_doc:
                flash(get_translated_text('username_exists'), 'error') 
                print(f"[{os.path.basename(__file__)}] Registration failed: Username '{username}' already exists.")
                return redirect(url_for('login'))
            else:
                hashed_password = generate_password_hash(password)
                users_collection.insert_one({
                    'username': username, 
                    'password_hash': hashed_password,
                    'preferred_mode': 'light', 
                    'preferred_language': 'en', # Default language for new users
                    'created_at': datetime.now(),
                    'last_login': datetime.now()
                })
                session['user_id'] = username
                session['preferred_mode'] = 'light' 
                session['preferred_language'] = 'en' # Set session language for new user
                flash(get_translated_text('account_created_logged_in').format(username=username), 'success')
                print(f"[{os.path.basename(__file__)}] Registered and logged in new user: {username}.")
                return redirect(url_for('home'))
        
        elif action == 'login':
            if user_doc:
                stored_hash = user_doc['password_hash']
                if check_password_hash(stored_hash, password):
                    session['user_id'] = username
                    session['preferred_mode'] = user_doc.get('preferred_mode', 'light') 
                    session['preferred_language'] = user_doc.get('preferred_language', 'en') # Load language
                    users_collection.update_one({'username': username}, {'$set': {'last_login': datetime.now()}})
                    flash(get_translated_text('welcome_back').format(username=username), 'success')
                    print(f"[{os.path.basename(__file__)}] Successful login for user: {username}.")
                    return redirect(url_for('home'))
                else:
                    flash(get_translated_text('invalid_username_password'), 'error')
                    print(f"[{os.path.basename(__file__)}] Failed login for user {username}: Invalid password.")
                    return redirect(url_for('login'))
            else:
                flash(get_translated_text('username_not_found'), 'error')
                print(f"[{os.path.basename(__file__)}] Login failed: Username '{username}' not found.")
                return redirect(url_for('login'))
        else:
            flash(get_translated_text('invalid_action'), 'error')
            print(f"[{os.path.basename(__file__)}] Login submission failed: Invalid action '{action}'.")
            return redirect(url_for('login'))

    except Exception as e:
        flash(f"{get_translated_text('an_error_occurred')}: {e}", 'error')
        print(f"[{os.path.basename(__file__)}] ERROR during login/registration: {e}")
        return redirect(url_for('login'))


@app.route('/logout', methods=['POST'])
def logout():
    """Handles logout and clears session."""
    print(f"[{os.path.basename(__file__)}] User logging out.")
    session.pop('user_id', None)
    session.pop('preferred_mode', None)
    session.pop('preferred_language', None) # Clear language from session
    flash(get_translated_text('logged_out_successfully'), 'info') 
    return redirect(url_for('login'))

@app.route('/predict', methods=['POST'])
def predict():
    """Handles audio prediction requests."""
    print(f"[{os.path.basename(__file__)}] Accessing predict route.")
    global last_prediction_result 

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": get_translated_text('user_not_authenticated')}), 401

    if 'audio' not in request.files:
        print(f"[{os.path.basename(__file__)}] Predict error: No audio file provided.")
        return jsonify({"error": get_translated_text('no_audio_file_provided')}), 400

    audio_file_stream = request.files['audio']
    
    audio_bytes = audio_file_stream.read()
    audio_file_stream.seek(0) 

    print(f"[{os.path.basename(__file__)}] Received audio file: name='{audio_file_stream.filename}', mimetype='{audio_file_stream.mimetype}', content_length={len(audio_bytes)} bytes.")

    try:
        # Check if the audio is webm and convert to wav in-memory using pydub
        if audio_file_stream.mimetype == 'audio/webm' or audio_file_stream.mimetype == 'audio/webm;codecs=opus':
            print(f"[{os.path.basename(__file__)}] Converting webm audio to wav using pydub...")
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
            # Export to WAV in a new BytesIO object
            wav_io = io.BytesIO()
            audio_segment.export(wav_io, format="wav")
            wav_io.seek(0)
            audio_bytes_processed = wav_io.read()
            audio_mimetype_for_librosa = 'audio/wav'
            print(f"[{os.path.basename(__file__)}] WebM to WAV conversion complete.")
        else:
            audio_bytes_processed = audio_bytes
            audio_mimetype_for_librosa = audio_file_stream.mimetype

        audio_data, original_sr = librosa.load(io.BytesIO(audio_bytes_processed), sr=None, mono=True)
        
        if audio_data is None or len(audio_data) == 0:
            print(f"[{os.path.basename(__file__)}] ERROR: librosa.load returned empty audio_data or None.")
            return jsonify({"error": get_translated_text('failed_load_audio_empty')}), 400

        processed_features = preprocess_audio(audio_data, original_sr)

        if processed_features is None:
            print(f"[{os.path.basename(__file__)}] Predict error: Failed to preprocess audio (e.g., audio too short or silent).")
            return jsonify({"error": get_translated_text('failed_preprocess_audio')}), 400

        verdict_current_lang, verdict_en, confidence_breakdown = predict_with_cnn(processed_features)

        # Update the global result for results.html and thank_you.html
        last_prediction_result['verdict'] = verdict_current_lang
        last_prediction_result['confidence'] = confidence_breakdown
        print(f"[{os.path.basename(__file__)}] Prediction successful: {verdict_current_lang}")

        # Store Audio Record in MongoDB
        # FIX: Use 'is not None' for PyMongo collection objects
        if audio_records_collection is not None:
            audio_record = {
                'user_id': user_id,
                'timestamp': datetime.now(),
                'audio_data': Binary(audio_bytes), # Store raw binary audio (original webm)
                'audio_filename': audio_file_stream.filename, 
                'audio_mimetype': audio_file_stream.mimetype, # Store original mimetype
                'verdict_en': verdict_en, # Store English verdict for consistent retrieval if needed
                'verdict_current_lang': verdict_current_lang, # Store localized verdict
                'confidence': confidence_breakdown
            }
            audio_records_collection.insert_one(audio_record)
            print(f"[{os.path.basename(__file__)}] Audio record saved to MongoDB for user '{user_id}'.")
        else:
            print(f"[{os.path.basename(__file__)}] WARNING: Audio record not saved. MongoDB audio_records_collection not available.")

        return jsonify({
            "verdict": verdict_current_lang,
            "verdict_en": verdict_en, # Include English verdict for frontend logic
            "confidence": confidence_breakdown,
            "redirect_to": url_for('thank_you') 
        })
    except Exception as e:
        print(f"[{os.path.basename(__file__)}] Predict route ERROR during audio processing: {type(e).__name__}: {e}")
        return jsonify({"error": f"{get_translated_text('audio_processing_failed')}: {e}"}), 500

@app.route('/thank_you')
def thank_you():
    """Renders the thank you page after a prediction."""
    print(f"[{os.path.basename(__file__)}] Accessing thank_you route.")
    try:
        return render_template('thank_you.html', last_prediction=last_prediction_result,
                               user_name=session.get('user_id'), preferred_mode=session.get('preferred_mode'))
    except Exception as e:
        print(f"[{os.path.basename(__file__)}] ERROR: Exception during thank_you rendering: {e}")
        return "<h1>Server Error</h1><p>Could not load thank you page: " + str(e) + "</p><p>Check Flask terminal for details.</p>", 500


if __name__ == '__main__':
    print(f"[{os.path.basename(__file__)}] Starting Flask development server...")
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
        print(f"[{os.path.basename(__file__)}] Created directory: {MODEL_DIR}")
    
    app.run(debug=True, port=5001)
