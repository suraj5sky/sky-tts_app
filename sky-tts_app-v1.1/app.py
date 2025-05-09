from flask import Flask, request, jsonify, send_from_directory, render_template, session, redirect, url_for
from flask_cors import CORS
import os
import logging
from datetime import datetime
import edge_tts
import asyncio
from gtts import gTTS
from pathlib import Path
import tempfile
import torch
from werkzeug.utils import secure_filename
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import secrets
from functools import wraps
import stripe
import uuid
import json
import psutil
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
import hmac
import re
from requests_oauthlib import OAuth2Session
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import docx
import sqlite3
from datetime import timedelta

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_TTS_AVAILABLE = True
    AZURE_STT_AVAILABLE = True
except ImportError:
    AZURE_TTS_AVAILABLE = False
    AZURE_STT_AVAILABLE = False

# Load environment variables
load_dotenv()

# Set up Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = secrets.token_hex(16)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_COOKIE_NAME'] = 'sky_tts_session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)  # Session expires after 1 day
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
Session(app)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = 'http://127.0.0.1:5000/api/auth/google/callback'
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_FOLDER = os.path.join(BASE_DIR, 'static', 'audio')
OUTPUT_FOLDER = os.path.join(AUDIO_FOLDER, 'Output')
os.makedirs(OUTPUT_FOLDER, exist_ok=True) 

# SQLite Database Setup
def init_db():
    with sqlite3.connect(os.path.join(BASE_DIR, 'users.db')) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            plan TEXT DEFAULT 'free',
            characters_used INTEGER DEFAULT 0,
            api_calls INTEGER DEFAULT 0
        )''')
        conn.commit()

# Initialize database
init_db()

# Voice configurations
VOICES = {
    "hindi": [
        {"id": "hi-IN-MadhurNeural", "name": "Surja", "service": "edge", "sample_text": "Hello दोस्तों, मैं हूँ Surja! आप कैसे हैं? आपका स्वागत है SKY TTS में। आप सुन रहे हैं SKY TTS वॉइस डेमो।", "style": "friendly", "mood": "positive", "gender": "male", "description": "A warm, friendly male voice.", "use_cases": ["narration", "e-learning"], "age_range": "adult"},
        {"id": "hi-IN-SwaraNeural", "name": "Tanya", "service": "edge", "sample_text": "Hello दोस्तों, मैं हूँ Tanya! आप कैसे हैं? आपका स्वागत है SKY TTS में। आप सुन रहे हैं SKY TTS वॉइस डेमो।", "style": "cheerful", "mood": "friendly", "gender": "female", "description": "A cheerful female voice.", "use_cases": ["podcasts", "commercials"], "age_range": "young-adult"},
        {"id": "en-US-AndrewMultilingualNeural", "name": "Abhi", "service": "edge", "sample_text": "Hello दोस्तों, मैं हूँ Abhi! आप कैसे हैं? आपका स्वागत है SKY TTS में। आप सुन रहे हैं SKY TTS वॉइस डेमो।", "style": "natural", "mood": "friendly", "gender": "male", "description": "A natural-sounding male voice.", "use_cases": ["audiobooks"], "age_range": "adult"},
        {"id": "hi-IN-PoojaNeural", "name": "Riya", "service": "edge", "sample_text": "Hello दोस्तों, मैं हूँ Riya! आप कैसे हैं? आपका स्वागत है SKY TTS में। आप सुन रहे हैं SKY TTS वॉइस डेमो।", "style": "warm", "mood": "welcoming", "gender": "female", "description": "A warm, welcoming female voice.", "use_cases": ["customer-service"], "age_range": "adult"},
        {"id": "en-US-BrianMultilingualNeural", "name": "Baba", "service": "edge", "sample_text": "Hello दोस्तों, मैं हूँ Baba! आप कैसे हैं? आपका स्वागत है SKY TTS में। आप सुन रहे हैं SKY TTS वॉइस डेमो।", "style": "confident", "mood": "assertive", "gender": "male", "description": "A confident male voice.", "use_cases": ["presentations"], "age_range": "adult"},
        {"id": "hi-IN-SwaraNeural", "name": "Niku", "service": "edge", "sample_text": "Hello दोस्तों, मैं हूँ Niku! आप कैसे हैं? आपका स्वागत है SKY TTS में। आप सुन रहे हैं SKY TTS वॉइस डेमो।", "style": "gentle", "mood": "calm", "gender": "female", "description": "A gentle female voice.", "use_cases": ["meditation"], "age_range": "young-adult"},
        {"id": "en-IN-PrabhatNeural", "name": "Prabhat", "service": "edge", "sample_text": "Hello Dosto, Main hu Prabhat! App Kaise hain? Apka Swagat hai SKY TTS mein। Aap sun rahe hai SKY TTS Voice Demo।", "style": "friendly", "mood": "energetic", "gender": "male", "description": "An energetic male voice.", "use_cases": ["advertisements"], "age_range": "young-adult"},
        {"id": "en-US-BrianNeural", "name": "Tushar", "service": "edge", "sample_text": "Hello दोस्तों, मैं हूँ Tushar! आप कैसे हैं? आपका स्वागत है SKY TTS में। आप सुन रहे हैं SKY TTS वॉइस डेमो।", "style": "energetic", "mood": "enthusiastic", "gender": "male", "description": "An energetic male voice.", "use_cases": ["advertisements"], "age_range": "young-adult"}
    ],
    "english": [
        {"id": "en-US-JennyNeural", "name": "Ananya", "service": "edge", "sample_text": "Hello friends, I'm Ananya! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "friendly", "mood": "considerate", "gender": "female", "description": "A friendly female voice.", "use_cases": ["customer-service"], "age_range": "adult"},
        {"id": "en-US-ChristopherNeural", "name": "Pankaj", "service": "edge", "sample_text": "Hello friends, I'm Pankaj! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "reliable", "mood": "authoritative", "gender": "male", "description": "An authoritative male voice.", "use_cases": ["corporate"], "age_range": "adult"},
        {"id": "en-US-AriaNeural", "name": "Kavya", "service": "edge", "sample_text": "Hello friends, I'm Kavya! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "expressive", "mood": "playful", "gender": "female", "description": "An expressive female voice.", "use_cases": ["storytelling"], "age_range": "young-adult"},
        {"id": "en-IN-NeerjaExpressiveNeural", "name": "Neerja", "service": "edge", "sample_text": "Hello friends, I'm Neerja! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "expressive", "mood": "positive", "gender": "female", "description": "A positive, expressive female voice.", "use_cases": ["commercials"], "age_range": "young-adult"},
        {"id": "en-IN-PrabhatNeural", "name": "Rudra", "service": "edge", "sample_text": "Hello friends, I'm Rudra! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "friendly", "mood": "energetic", "gender": "male", "description": "An energetic male voice.", "use_cases": ["advertisements"], "age_range": "young-adult"},
        {"id": "en-GB-SoniaNeural", "name": "Sonia", "service": "edge", "sample_text": "Hello friends, I'm Sonia! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly British female voice.", "use_cases": ["podcasts"], "age_range": "adult"},
        {"id": "en-GB-RyanNeural", "name": "Aryan", "service": "edge", "sample_text": "Hello friends, I'm Aryan! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly British male voice.", "use_cases": ["narration"], "age_range": "adult"},
        {"id": "en-US-GuyNeural", "name": "Shivam", "service": "edge", "sample_text": "Hello friends, I'm Shivam! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "casual", "mood": "relaxed", "gender": "male", "description": "A casual male voice.", "use_cases": ["social-media"], "age_range": "young-adult"},
        {"id": "en-GB-LibbyNeural", "name": "Supriya", "service": "edge", "sample_text": "Hello friends, I'm Supriya! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "cheerful", "mood": "happy", "gender": "female", "description": "A cheerful British female voice.", "use_cases": ["commercials"], "age_range": "young-adult"},
        {"id": "en-AU-NatashaNeural", "name": "Natasha", "service": "edge", "sample_text": "Hello friends, I'm Natasha! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly Australian female voice.", "use_cases": ["e-learning"], "age_range": "adult"},
        {"id": "en-AU-WilliamNeural", "name": "Shiva", "service": "edge", "sample_text": "Hello friends, I'm Shiva! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "confident", "mood": "assertive", "gender": "male", "description": "A confident Australian male voice.", "use_cases": ["presentations"], "age_range": "adult"},
        {"id": "en-US-AnaNeural", "name": "Ana", "service": "edge", "sample_text": "Hello friends, I'm Ana! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "gentle", "mood": "calm", "gender": "female", "description": "A gentle female voice.", "use_cases": ["meditation"], "age_range": "young-adult"},
        {"id": "en-CA-ClaraNeural", "name": "Clara", "service": "edge", "sample_text": "Hello friends, I'm Clara! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly Canadian female voice.", "use_cases": ["podcasts"], "age_range": "adult"},
        {"id": "en-CA-LiamNeural", "name": "Devas", "service": "edge", "sample_text": "Hello friends, I'm Devas! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "confident", "mood": "assertive", "gender": "male", "description": "A confident Canadian male voice.", "use_cases": ["corporate"], "age_range": "adult"},
        {"id": "en-NZ-MitchellNeural", "name": "Mitchell", "service": "edge", "sample_text": "Hello friends, I'm Mitchell! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "casual", "mood": "relaxed", "gender": "male", "description": "A casual New Zealand male voice.", "use_cases": ["social-media"], "age_range": "young-adult"},
        {"id": "en-NZ-MollyNeural", "name": "Neha", "service": "edge", "sample_text": "Hello friends, I'm Neha! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "cheerful", "mood": "happy", "gender": "female", "description": "A cheerful New Zealand female voice.", "use_cases": ["commercials"], "age_range": "young-adult"},
        {"id": "en-IN-NeerjaExpressiveNeural", "name": "Sanaya", "service": "edge", "sample_text": "Hello friends, I'm Sanaya! How are you today? Welcome to SKY TTS. You're listening to a voice demo from SKY TTS.", "style": "cheerful", "mood": "happy", "gender": "female", "description": "A cheerful Australian female voice.", "use_cases": ["commercials"], "age_range": "young-adult"}
    ],
    "japanese": [
        {"id": "ja-JP-KeitaNeural", "name": "Keita (Male)", "service": "edge", "sample_text": "こんにちは!", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["narration"], "age_range": "adult"},
        {"id": "ja-JP-NanamiNeural", "name": "Nanami (Female)", "service": "edge", "sample_text": "お元気ですか？", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["e-learning"], "age_range": "young-adult"}
    ],
    "chinese": [
        {"id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao (Female)", "service": "edge", "sample_text": "你好！", "style": "warm", "mood": "friendly", "gender": "female", "description": "A warm female voice.", "use_cases": ["customer-service"], "age_range": "adult"},
        {"id": "zh-CN-YunxiNeural", "name": "Yunxi (Male)", "service": "edge", "sample_text": "你好吗？", "style": "lively", "mood": "sunshine", "gender": "male", "description": "A lively male voice.", "use_cases": ["advertisements"], "age_range": "young-adult"},
        {"id": "zh-HK-HiuMaanNeural", "name": "HiuMaan (Female)", "service": "edge", "sample_text": "你好！", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["podcasts"], "age_range": "adult"},
        {"id": "zh-HK-WanLungNeural", "name": "WanLung (Male)", "service": "edge", "sample_text": "你好吗？", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["narration"], "age_range": "adult"},
        {"id": "zh-TW-HsiaoYuNeural", "name": "HsiaoYu (Female)", "service": "edge", "sample_text": "你好！", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["e-learning"], "age_range": "adult"},
        {"id": "zh-TW-YunJheNeural", "name": "YunJhe (Male)", "service": "edge", "sample_text": "你好吗？", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["corporate"], "age_range": "adult"}
    ],
    "spanish": [
        {"id": "es-ES-AlvaroNeural", "name": "Alvaro (Male)", "service": "edge", "sample_text": "¡Buenos días!", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["narration"], "age_range": "adult"},
        {"id": "es-ES-ElviraNeural", "name": "Elvira (Female)", "service": "edge", "sample_text": "¡Hola!", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["e-learning"], "age_range": "adult"},
        {"id": "es-MX-JorgeNeural", "name": "Jorge (Male)", "service": "edge", "sample_text": "¡Buen día!", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["podcasts"], "age_range": "adult"},
        {"id": "es-MX-DaliaNeural", "name": "Dalia (Female)", "service": "edge", "sample_text": "¡Hola!", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["commercials"], "age_range": "young-adult"}
    ],
    "italian": [
        {"id": "it-IT-DiegoNeural", "name": "Diego (Male)", "service": "edge", "sample_text": "Ciao!", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["narration"], "age_range": "adult"},
        {"id": "it-IT-IsabellaNeural", "name": "Isabella (Female)", "service": "edge", "sample_text": "Come stai?", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["e-learning"], "age_range": "adult"}
    ],
    "french": [
        {"id": "fr-FR-DeniseNeural", "name": "Denise (Female)", "service": "edge", "sample_text": "Bonjour!", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["podcasts"], "age_range": "adult"},
        {"id": "fr-FR-HenriNeural", "name": "Henri (Male)", "service": "edge", "sample_text": "Salut!", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["narration"], "age_range": "adult"},
        {"id": "fr-CA-SylvieNeural", "name": "Sylvie (Female)", "service": "edge", "sample_text": "Bonjour!", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly Canadian female voice.", "use_cases": ["e-learning"], "age_range": "adult"},
        {"id": "fr-CA-AntoineNeural", "name": "Antoine (Male)", "service": "edge", "sample_text": "Salut!", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly Canadian male voice.", "use_cases": ["corporate"], "age_range": "adult"}
    ],
    "nepali": [
        {"id": "ne-NP-HemkalaNeural", "name": "Hemkala (Female)", "service": "edge", "sample_text": "नमस्ते!", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["e-learning"], "age_range": "adult"},
        {"id": "ne-NP-SagarNeural", "name": "Sagar (Male)", "service": "edge", "sample_text": "तिमी कस्तो छौ?", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["narration"], "age_range": "adult"}
    ],
    "urdu": [
        {"id": "ur-IN-GulNeural", "name": "Gul (Female)", "service": "edge", "sample_text": "سلام!", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["podcasts"], "age_range": "adult"},
        {"id": "ur-IN-SalmanNeural", "name": "Salman (Male)", "service": "edge", "sample_text": "آپ کیسے ہیں؟", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["narration"], "age_range": "adult"},
        {"id": "ur-PK-AsadNeural", "name": "Asad (Male)", "service": "edge", "sample_text": "سلام!", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["corporate"], "age_range": "adult"},
        {"id": "ur-PK-UzmaNeural", "name": "Uzma (Female)", "service": "edge", "sample_text": "آپ کیسے ہیں؟", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["e-learning"], "age_range": "adult"}
    ],
    "bengali": [
        {"id": "bn-BD-NabanitaNeural", "name": "Nabanita (Female)", "service": "edge", "sample_text": "হ্যালো!", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["podcasts"], "age_range": "adult"},
        {"id": "bn-BD-PradeepNeural", "name": "Pradeep (Male)", "service": "edge", "sample_text": "আপনি কেমন আছেন?", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["narration"], "age_range": "adult"},
        {"id": "bn-IN-BashkarNeural", "name": "Bashkar (Male)", "service": "edge", "sample_text": "নমস্কার!", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["corporate"], "age_range": "adult"},
        {"id": "bn-IN-TanishaaNeural", "name": "Tanishaa (Female)", "service": "edge", "sample_text": "আপনি কী করছেন?", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["e-learning"], "age_range": "adult"}
    ],
    "gujarati": [
        {"id": "gu-IN-DhwaniNeural", "name": "Dhwani (Female)", "service": "edge", "sample_text": "નમસ્તે!", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["e-learning"], "age_range": "adult"},
        {"id": "gu-IN-NiranjanNeural", "name": "Niranjan (Male)", "service": "edge", "sample_text": "તમે કેમ છો?", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["narration"], "age_range": "adult"}
    ],
    "kannada": [
        {"id": "kn-IN-GaganNeural", "name": "Gagan (Male)", "service": "edge", "sample_text": "ನಮಸ್ಕಾರ!", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["corporate"], "age_range": "adult"},
        {"id": "kn-IN-SapnaNeural", "name": "Sapna (Female)", "service": "edge", "sample_text": "ನೀವು ಹೇಗಿದ್ದೀರಿ?", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["e-learning"], "age_range": "adult"}
    ],
    "malayalam": [
        {"id": "ml-IN-MidhunNeural", "name": "Midhun (Male)", "service": "edge", "sample_text": "നമസ്കാരം!", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["narration"], "age_range": "adult"},
        {"id": "ml-IN-SobhanaNeural", "name": "Sobhana (Female)", "service": "edge", "sample_text": "നിനക്ക് സുഖമാണോ?", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["e-learning"], "age_range": "adult"},
        {"id": "mr-IN-AarohiNeural", "name": "Aarohi (Female)", "service": "edge", "sample_text": "नमस्कार!", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["podcasts"], "age_range": "adult"},
        {"id": "mr-IN-ManoharNeural", "name": "Manohar (Male)", "service": "edge", "sample_text": "तू कसा आहेस?", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["narration"], "age_range": "adult"}
    ],
    "tamil": [
        {"id": "ta-IN-PallaviNeural", "name": "Pallavi (Female)", "service": "edge", "sample_text": "வணக்கம்!", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["e-learning"], "age_range": "adult"},
        {"id": "ta-IN-ValluvarNeural", "name": "Valluvar (Male)", "service": "edge", "sample_text": "நீங்கள் எப்படி இருக்கிறீர்கள்?", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["narration"], "age_range": "adult"}
    ],
    "telugu": [
        {"id": "te-IN-MohanNeural", "name": "Mohan (Male)", "service": "edge", "sample_text": "హలో!", "style": "friendly", "mood": "positive", "gender": "male", "description": "A friendly male voice.", "use_cases": ["corporate"], "age_range": "adult"},
        {"id": "te-IN-ShrutiNeural", "name": "Shruti (Female)", "service": "edge", "sample_text": "మీరు ఎలా ఉన్నారు?", "style": "friendly", "mood": "positive", "gender": "female", "description": "A friendly female voice.", "use_cases": ["e-learning"], "age_range": "adult"}
    ]
}

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.error("Authentication required")
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

def generate_with_edge_tts(text, voice_id, speed=1.0, pitch=1.0, use_ssml=False):
    try:
        filename = f"edge_{voice_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
        output_file = os.path.join(OUTPUT_FOLDER, filename)
        async def generate():
            kwargs = {}
            if speed != 1.0:
                rate_percent = int((speed - 1.0) * 100)
                kwargs["rate"] = f"{rate_percent:+d}%"
            if pitch != 1.0:
                pitch_hz = int((pitch - 1.0) * 100)
                kwargs["pitch"] = f"{pitch_hz:+d}Hz"
            logger.info(f"Edge TTS: voice={voice_id}, rate={kwargs.get('rate', 'default')}, pitch={kwargs.get('pitch', 'default')}")
            communicate = edge_tts.Communicate(text, voice_id, **kwargs)
            await communicate.save(output_file)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(generate())
        loop.close()
        if not os.path.exists(output_file):
            logger.error(f"Edge TTS failed to generate file: {output_file}")
            return None
        return filename
    except Exception as e:
        logger.error(f"Edge TTS error for voice {voice_id}: {str(e)}")
        return None

def generate_with_azure_tts(text, voice_id, speed=1.0, pitch=1.0):
    if not AZURE_TTS_AVAILABLE:
        logger.error("Azure TTS not available")
        return None
    azure_key = os.getenv("AZURE_SPEECH_KEY")
    azure_region = os.getenv("AZURE_SPEECH_REGION")
    if not azure_key or not azure_region:
        logger.error("Azure TTS: Missing AZURE_SPEECH_KEY or AZURE_SPEECH_REGION")
        return None
    try:
        azure_voice = voice_id.replace("azure_", "")
        filename = f"azure_{voice_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
        output_file = os.path.join(AUDIO_FOLDER, filename)
        speech_config = speechsdk.SpeechConfig(subscription=azure_key, region=azure_region)
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        speed_percent = int(speed * 100)
        pitch_percent = f"{int((pitch - 1) * 50):+d}%"
        ssml = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
            <voice name='{azure_voice}'>
                <prosody rate='{speed_percent}%' pitch='{pitch_percent}'>
                    {text}
                </prosody>
            </voice>
        </speak>
        """
        result = synthesizer.speak_ssml_async(ssml).get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            if not os.path.exists(output_file):
                logger.error(f"Azure TTS failed to generate file: {output_file}")
                return None
            return filename
        else:
            logger.error(f"Azure TTS error for voice {voice_id}: {result.reason}")
            return None
    except Exception as e:
        logger.error(f"Azure TTS error for voice {voice_id}: {str(e)}")
        return None

def speech_to_text_azure(audio_file):
    if not AZURE_STT_AVAILABLE:
        logger.error("Azure STT not available")
        return None
    azure_key = os.getenv("AZURE_SPEECH_KEY")
    azure_region = os.getenv("AZURE_SPEECH_REGION")
    if not azure_key or not azure_region:
        logger.error("Azure STT: Missing AZURE_SPEECH_KEY or AZURE_SPEECH_REGION")
        return None
    try:
        speech_config = speechsdk.SpeechConfig(subscription=azure_key, region=azure_region)
        audio_config = speechsdk.audio.AudioConfig(filename=audio_file)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        result = recognizer.recognize_once()
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text
        else:
            logger.error(f"Azure STT error: {result.reason}")
            return None
    except Exception as e:
        logger.error(f"Azure STT error: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/templates/<path:filename>')
def serve_templates(filename):
    return send_from_directory('templates', filename)

@app.route('/api/languages', methods=['GET'])
def get_languages():
    languages = [{"id": lang, "text": lang.capitalize()} for lang in VOICES.keys()]
    logger.info(f"Returning {len(languages)} languages")
    return jsonify({"languages": languages})

@app.route('/api/voices', methods=['GET'])
def get_voices():
    language = request.args.get("language", "").lower()
    if language:
        if language not in VOICES:
            logger.error(f"Language {language} not supported")
            return jsonify({"error": f"Language {language} not supported"}), 400
        voices = [
            {
                "id": v["id"],
                "text": v["name"],
                "description": v.get("description", f"{v['name']} voice"),
                "style": v.get("style", "N/A"),
                "use_cases": v.get("use_cases", [v.get("style", "general")]),
                "age_range": v.get("age_range", "adult"),
                "mood": v.get("mood", "N/A"),
                "sample_text": v.get("sample_text", ""),
                "service": v.get("service", "edge"),
                "gender": v.get("gender", "unknown"),
                "edge_id": v.get("edge_id", v["id"])
            }
            for v in VOICES[language]
        ]
        logger.info(f"Returning {len(voices)} voices for language {language}")
        return jsonify({"voices": voices})
    all_voices = {lang: [
        {
            "id": v["id"],
            "text": v["name"],
            "description": v.get("description", f"{v['name']} voice"),
            "style": v.get("style", "N/A"),
            "use_cases": v.get("use_cases", [v.get("style", "general")]),
            "age_range": v.get("age_range", "adult"),
            "mood": v.get("mood", "N/A"),
            "sample_text": v.get("sample_text", ""),
            "service": v.get("service", "edge"),
            "gender": v.get("gender", "unknown"),
            "edge_id": v.get("edge_id", v["id"])
        }
        for v in voices
    ] for lang, voices in VOICES.items()}
    logger.info(f"Returning all voices for all languages")
    return jsonify({"voices": all_voices})

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    if not all([name, email, password]):
        logger.error("Signup failed: Missing required fields")
        return jsonify({"error": "Name, email, and password are required"}), 400
    with sqlite3.connect(os.path.join(BASE_DIR, 'users.db')) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password, plan, characters_used, api_calls) VALUES (?, ?, ?, ?, ?, ?)",
                     (name, email, generate_password_hash(password), 'free', 0, 0))
            conn.commit()
            user_id = c.lastrowid
            session['user_id'] = user_id
            user = {"name": name, "email": email, "plan": "free", "chars_used": 0, "char_limit": 5000}
            logger.info(f"User {email} signed up successfully")
            return jsonify({"message": "Signup successful", "user": user})
        except sqlite3.IntegrityError:
            logger.error(f"Signup failed for {email}: Email already exists")
            return jsonify({"error": "Email already exists"}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if not all([email, password]):
        logger.error("Login failed: Missing email or password")
        return jsonify({"error": "Email and password are required"}), 400
    with sqlite3.connect(os.path.join(BASE_DIR, 'users.db')) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, email, password, plan, characters_used FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            user_data = {
                "name": user[1],
                "email": user[2],
                "plan": user[4],
                "chars_used": user[5],
                "char_limit": 5000 if user[4] == "free" else 10000 if user[4] == "Pro" else 50000
            }
            logger.info(f"User {email} logged in successfully")
            return jsonify({"message": "Login successful", "user": user_data})
        logger.error(f"Login failed for {email}: Invalid credentials")
        return jsonify({"error": "Invalid email or password"}), 401

@app.route('/api/auth/google')
def google_auth():
    google = OAuth2Session(GOOGLE_CLIENT_ID, redirect_uri=GOOGLE_REDIRECT_URI, scope=['profile', 'email'])
    authorization_url, state = google.authorization_url(GOOGLE_AUTH_URL, access_type='offline')
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/api/auth/google/callback')
def google_callback():
    if 'error' in request.args:
        logger.error("Google authentication failed")
        return jsonify({"error": "Google authentication failed"}), 400
    google = OAuth2Session(GOOGLE_CLIENT_ID, state=session.get('oauth_state'), redirect_uri=GOOGLE_REDIRECT_URI)
    token = google.fetch_token(GOOGLE_TOKEN_URL, client_secret=GOOGLE_CLIENT_SECRET, authorization_response=request.url)
    user_info = google.get(GOOGLE_USERINFO_URL).json()
    email = user_info.get('email')
    name = user_info.get('name', email.split('@')[0])
    with sqlite3.connect(os.path.join(BASE_DIR, 'users.db')) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, plan, characters_used FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        if user:
            session['user_id'] = user[0]
            user_data = {
                "name": user[1],
                "email": email,
                "plan": user[2],
                "chars_used": user[3],
                "char_limit": 5000 if user[2] == "free" else 10000 if user[2] == "Pro" else 50000
            }
        else:
            c.execute("INSERT INTO users (name, email, password, plan, characters_used, api_calls) VALUES (?, ?, ?, ?, ?, ?)",
                     (name, email, '', 'free', 0, 0))
            conn.commit()
            user_id = c.lastrowid
            session['user_id'] = user_id
            user_data = {
                "name": name,
                "email": email,
                "plan": "free",
                "chars_used": 0,
                "char_limit": 5000
            }
        logger.info(f"Google login for {email} successful")
        return redirect(url_for('index'))

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()  # Clear all session data
    response = jsonify({"message": "Logout successful"})
    response.set_cookie('session', '', expires=0)  # Immediately expire cookie
    logger.info("User logged out Successfully")
    return response

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    if 'user_id' in session:
        with sqlite3.connect(os.path.join(BASE_DIR, 'users.db')) as conn:
            c = conn.cursor()
            c.execute("SELECT name, email, plan, characters_used FROM users WHERE id = ?", (session['user_id'],))
            user = c.fetchone()
            if user:
                user_data = {
                    "name": user[0],
                    "email": user[1],
                    "plan": user[2],
                    "chars_used": user[3],
                    "char_limit": 5000 if user[2] == "free" else 10000 if user[2] == "Pro" else 50000
                }
                logger.info(f"Auth status: User {user[1]} authenticated")
                return jsonify({"authenticated": True, "user": user_data})
    logger.info("Auth status: No user authenticated")
    return jsonify({"authenticated": False})

@app.route('/api/subscribe', methods=['POST'])
@login_required
def subscribe():
    data = request.get_json()
    plan = data.get('plan')
    if not plan or plan not in ['free', 'Pro', 'Enterprise']:
        logger.error(f"Subscription failed: Invalid plan {plan}")
        return jsonify({"error": "Valid plan is required"}), 400
    with sqlite3.connect(os.path.join(BASE_DIR, 'users.db')) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET plan = ? WHERE id = ?", (plan, session['user_id']))
        c.execute("SELECT name, email, plan, characters_used FROM users WHERE id = ?", (session['user_id'],))
        user = c.fetchone()
        conn.commit()
        user_data = {
            "name": user[0],
            "email": user[1],
            "plan": user[2],
            "chars_used": user[3],
            "char_limit": 5000 if user[2] == "free" else 10000 if user[2] == "Pro" else 50000
        }
        logger.info(f"User {user[1]} subscribed to {plan} plan")
        return jsonify({"message": "Subscription updated", "user": user_data})

@app.route('/api/analytics', methods=['GET'])
@login_required
def analytics():
    with sqlite3.connect(os.path.join(BASE_DIR, 'users.db')) as conn:
        c = conn.cursor()
        c.execute("SELECT plan, characters_used, api_calls FROM users WHERE id = ?", (session['user_id'],))
        user = c.fetchone()
        if user:
            plan_limits = {'free': 5000, 'Pro': 10000, 'Enterprise': 50000}
            logger.info(f"Returning analytics for user_id {session['user_id']}")
            return jsonify({
                "chars_used": user[1],
                "char_limit": plan_limits.get(user[0], 5000),
                "api_calls": user[2]
            })
        logger.error(f"Analytics failed: User {session['user_id']} not found")
        return jsonify({"error": "User not found"}), 404

@app.route('/api/generate_tts', methods=['POST'])
@login_required
def generate_tts():
    data = request.get_json()
    if not data:
        logger.error("TTS generation failed: No JSON data provided")
        return jsonify({"error": "No JSON data provided"}), 400
    text = data.get("text")
    language = data.get("language", "english").lower()
    voice_id = data.get("voice")
    speed = float(data.get("speed", 1.0))
    pitch = float(data.get("pitch", 1.0))
    use_ssml = data.get("use_ssml", False)
    if not text or not voice_id:
        logger.error("TTS generation failed: Text and voice are required")
        return jsonify({"error": "Text and voice are required"}), 400
    if language not in VOICES:
        logger.error(f"TTS generation failed: Language {language} not supported")
        return jsonify({"error": f"Language {language} not supported"}), 400
    voice = next((v for v in VOICES[language] if v["id"] == voice_id), None)
    if not voice:
        logger.error(f"TTS generation failed: Voice {voice_id} not found for language {language}")
        return jsonify({"error": f"Voice {voice_id} not found for language {language}"}), 400
    # Update usage
    with sqlite3.connect(os.path.join(BASE_DIR, 'users.db')) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET characters_used = characters_used + ?, api_calls = api_calls + 1 WHERE id = ?",
                 (len(text), session['user_id']))
        conn.commit()
    filename = None
    actual_voice_id = voice.get("edge_id", voice["id"]) if voice["service"] == "edge" else voice["id"]
    if voice["service"] == "edge":
        filename = generate_with_edge_tts(text, actual_voice_id, speed, pitch, use_ssml)
    elif voice["service"] == "azure":
        filename = generate_with_azure_tts(text, actual_voice_id, speed, pitch)
    if filename:
        logger.info(f"TTS generated successfully for voice {voice_id}: {filename}")
        return jsonify({"filename": filename})
    logger.error("TTS generation failed: Failed to generate audio")
    return jsonify({"error": "Failed to generate audio"}), 500

@app.route('/api/voice-preview/<voice_id>', methods=['GET'])
def voice_preview(voice_id):
    for language, voices in VOICES.items():
        voice = next((v for v in voices if v["id"] == voice_id), None)
        if voice:
            text = voice["sample_text"]
            filename = None
            actual_voice_id = voice.get("edge_id", voice["id"]) if voice["service"] == "edge" else voice["id"]
            if voice["service"] == "edge":
                filename = generate_with_edge_tts(text, actual_voice_id, speed=1.0, pitch=1.0)
            elif voice["service"] == "azure":
                filename = generate_with_azure_tts(text, actual_voice_id, speed=1.0, pitch=1.0)
            if filename:
                logger.info(f"Generated preview for voice {voice_id}: {filename}")
                return jsonify({"filename": filename})
            logger.error(f"Failed to generate preview for voice {voice_id}")
            return jsonify({"error": "Failed to generate preview"}), 500
    logger.error(f"Voice {voice_id} not found")
    return jsonify({"error": f"Voice {voice_id} not found"}), 404

@app.route('/api/process-file', methods=['POST'])
@login_required
def process_file():
    if 'file' not in request.files:
        logger.error("File processing failed: No file provided")
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    if file.filename == '':
        logger.error("File processing failed: No file selected")
        return jsonify({"error": "No file selected"}), 400
    try:
        text = ""
        if file.filename.endswith('.txt'):
            text = file.read().decode('utf-8')
        elif file.filename.endswith('.docx'):
            doc = docx.Document(file)
            text = '\n'.join([para.text for para in doc.paragraphs if para.text])
        else:
            logger.error("File processing failed: Unsupported file format")
            return jsonify({"error": "Unsupported file format. Use .txt or .docx"}), 400
        if not text.strip():
            logger.error("File processing failed: File is empty")
            return jsonify({"error": "File is empty"}), 400
        with sqlite3.connect(os.path.join(BASE_DIR, 'users.db')) as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET api_calls = api_calls + 1 WHERE id = ?", (session['user_id'],))
            conn.commit()
        logger.info(f"File processed successfully: {file.filename}")
        return jsonify({"text": text[:5000]})
    except Exception as e:
        logger.error(f"File processing error: {str(e)}")
        return jsonify({"error": "Failed to process file"}), 500

@app.route('/api/speech-to-text', methods=['POST'])
@login_required
def speech_to_text():
    if 'file' not in request.files:
        logger.error("Speech-to-Text failed: No audio file provided")
        return jsonify({"error": "No audio file provided"}), 400
    audio_file = request.files['file']
    if audio_file.filename == '':
        logger.error("Speech-to-Text failed: No audio file selected")
        return jsonify({"error": "No audio file selected"}), 400
    if not audio_file.filename.endswith(('.mp3', '.wav')):
        logger.error("Speech-to-Text failed: Unsupported audio format")
        return jsonify({"error": "Unsupported audio format. Use .mp3 or .wav"}), 400
    try:
        temp_file = os.path.join(tempfile.gettempdir(), audio_file.filename)
        audio_file.save(temp_file)
        text = speech_to_text_azure(temp_file) if AZURE_STT_AVAILABLE else "Mock transcription: This is a placeholder."
        os.remove(temp_file)
        if text:
            with sqlite3.connect(os.path.join(BASE_DIR, 'users.db')) as conn:
                c = conn.cursor()
                c.execute("UPDATE users SET api_calls = api_calls + 1 WHERE id = ?", (session['user_id'],))
                conn.commit()
            logger.info(f"Speech-to-Text successful for file: {audio_file.filename}")
            return jsonify({"text": text})
        logger.error("Speech-to-Text failed: Failed to transcribe audio")
        return jsonify({"error": "Failed to transcribe audio"}), 500
    except Exception as e:
        logger.error(f"Speech-to-Text error: {str(e)}")
        return jsonify({"error": "Failed to transcribe audio"}), 500

@app.route('/api/voice-clone', methods=['POST'])
@login_required
def voice_clone():
    if 'audio' not in request.files or 'voice_name' not in request.form:
        logger.error("Voice cloning failed: Audio file and voice name required")
        return jsonify({"error": "Audio file and voice name are required"}), 400
    audio_file = request.files['audio']
    voice_name = request.form['voice_name']
    voice_style = request.form.get('voice_style', 'natural')
    if audio_file.filename == '' or not voice_name:
        logger.error("Voice cloning failed: Invalid audio file or voice name")
        return jsonify({"error": "Invalid audio file or voice name"}), 400
    if not audio_file.filename.endswith(('.mp3', '.wav')):
        logger.error("Voice cloning failed: Unsupported audio format")
        return jsonify({"error": "Unsupported audio format. Use .mp3 or .wav"}), 400
    try:
        temp_file = os.path.join(tempfile.gettempdir(), audio_file.filename)
        audio_file.save(temp_file)
        cloned_voice_id = f"cloned_{voice_name.lower().replace(' ', '_')}"
        os.remove(temp_file)
        with sqlite3.connect(os.path.join(BASE_DIR, 'users.db')) as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET api_calls = api_calls + 1 WHERE id = ?", (session['user_id'],))
            conn.commit()
        logger.info(f"Voice cloned successfully: {cloned_voice_id}")
        return jsonify({
            "voice_id": cloned_voice_id,
            "voice_name": voice_name,
            "voice_style": voice_style,
            "message": "Voice cloning is coming soon"
        })
    except Exception as e:
        logger.error(f"Voice cloning error: {str(e)}")
        return jsonify({"error": "Failed to clone voice"}), 500

@app.route('/static/audio/Output/<filename>')
def serve_output_audio(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)