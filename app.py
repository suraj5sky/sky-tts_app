from flask import Flask, request, jsonify, send_from_directory, render_template, session, redirect, url_for
from flask_cors import CORS
import os
import logging
from datetime import datetime
import edge_tts
import asyncio
from gtts import gTTS
# from bark_tts.generate_bark import generate_bark_tts  # COMMENTED OUT FOR NOW																			   
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
from authlib.integrations.flask_client import OAuth
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
class Config:
    SECRET_KEY = secrets.token_hex(32)
    STRIPE_PUBLIC_KEY = 'pk_test_your_stripe_public_key'
    STRIPE_SECRET_KEY = 'sk_test_your_stripe_secret_key'
    STRIPE_WEBHOOK_SECRET = 'whsec_your_webhook_secret'
    FREE_CHAR_LIMIT = 1000
    PRO_CHAR_LIMIT = 5000
    FREE_DAILY_CONVERSIONS = 5
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = secrets.token_hex(32)
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = './flask_session'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    SESSION_COOKIE_SECURE = True  # Important for production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
CORS(app, supports_credentials=True, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5000",
            "http://127.0.0.1:5000",            
            "http://localhost:3000",  # If you have a frontend dev server
            "https://tts.skyinfinitetech.com"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": [
            "Content-Type", 
            "Authorization",
            "X-CSRFToken",
            "X-Requested-With"
        ],
        "expose_headers": [
            "Content-Type",
            "X-CSRFToken",
            "Content-Disposition"  # Useful for file downloads
        ],
        "supports_credentials": True,
        "max_age": 86400  # 24-hour preflight cache
    }
})

# After app creation, add:
csrf = CSRFProtect(app)
oauth = OAuth(app)

# Configure OAuth providers
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),  # Get from environment variables
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

github = oauth.register(
    name='github',
    client_id=os.getenv('GITHUB_CLIENT_ID'),
    client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={
        'scope': 'user:email'
    }
)

# Required configuration for Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './flask_session'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session lifetime

# Initialize Flask-Session
Session(app)

# Required helper functions
def validate_email(email):
    """Basic email validation"""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def secure_compare(a, b):
    """Timing-attack safe string comparison"""
    return hmac.compare_digest(a.encode(), b.encode())

# Initialize Stripe
stripe.api_key = app.config['STRIPE_SECRET_KEY']

# Initialize AWS Polly client
try:
    polly_client = boto3.client('polly')
    logger.info("Amazon Polly client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Amazon Polly client: {str(e)}")
    polly_client = None

# Database simulation (in production, use a real database)
users_db = {}
subscriptions_db = {}
usage_db = {}

# File system configuration
AUDIO_FOLDER = 'static/audio'
VOICE_PREVIEWS = 'static/voice_previews'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'txt'}

app.config['AUDIO_FOLDER'] = AUDIO_FOLDER
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Create directories
for folder in [AUDIO_FOLDER, VOICE_PREVIEWS, UPLOAD_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Complete Voice Configuration (unchanged from your original)
LANGUAGES = ["hindi", "english", "spanish", "french", "arabic", "german", "japanese", 
             "bengali", "gujarati", "tamil", "punjabi", "kannada"]
             
VOICES = {
    "hindi": [
	    {
            "id": "hi-IN-MadhurNeural",
            "name": "Surja (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits",
            "style": "authoritative",
            "use_cases": ["news", "presentations"],
            "description": "Deep commanding voice for professional narration",
            "sample_text": "Hello Dosto, मैं सूरज। आज का मुख्य समाचार सुनिए...",
            "age_range": "30-45",
            "mood": "professional"
        },
        # Amazon Polly Hindi Voices
        {
            "id": "Aditi",
            "name": "Aditi (Female)",
            "gender": "female",
            "service": "polly",
            "style": "neutral",
            "use_cases": ["general", "customer_service"],
            "description": "High quality Hindi female voice from Amazon Polly",
            "sample_text": "नमस्ते, मैं आदिति हूँ। आप कैसे हैं?",
            "age_range": "25-35",
            "mood": "neutral"
        },
        {
            "id": "Kajal",
            "name": "Kajal (Female)",
            "gender": "female",
            "service": "polly",
            "style": "expressive",
            "use_cases": ["storytelling", "entertainment"],
            "description": "Expressive Hindi female voice from Amazon Polly",
            "sample_text": "आज का मौसम बहुत सुहावना है!",
            "age_range": "20-30",
            "mood": "cheerful"
        },
        {
            "id": "hi-IN-SwaraNeural",
            "name": "Riya (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits--female",
            "style": "cheerful",
            "use_cases": ["storytelling", "customer_service"],
            "description": "Warm and friendly voice ideal for conversational apps",
            "sample_text": "आपका स्वागत है! मैं रिया आपके लिए कहानी सुनाउंगी...",
            "age_range": "20-35",
            "mood": "friendly"
        },
        {
            "id": "hi-IN-MadhurNeural",
            "name": "Aarav (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits",
            "style": "authoritative",
            "use_cases": ["news", "presentations"],
            "description": "Deep commanding voice for professional narration",
            "sample_text": "नमस्ते, मैं आरव हूँ। आज का समाचार सुनिए...",
            "age_range": "30-40",
            "mood": "professional"
        },
        {
            "id": "en-US-AndrewMultilingualNeural",
            "name": "Ravi (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "natural",
            "use_cases": ["storytelling", "educational", "motivational"],
            "description": "Warm and clear Hindi voice, ideal for narration and YouTube content",
            "sample_text": "एक समय की बात है, एक छोटे से गाँव में एक बच्चा रहता था...",
            "age_range": "30-40",
            "mood": "inspiring"
        },
         {
            "id": "en-US-BrianMultilingualNeural",
            "name": "Anup (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "deep",
            "use_cases": ["mythological", "devotional", "voiceovers"],
            "description": "Deep and authoritative Hindi voice perfect for spiritual or historical content",
            "sample_text": "भगवान श्रीराम ने अपने अनुयायियों को धर्म का मार्ग दिखाया...",
            "age_range": "35-50",
            "mood": "calm & powerful"
        },
        {
            "id": "en-US-BrianNeural",
            "name": "Brian (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "Conversation",
            "use_cases": ["customer_service", "education"],
            "description": "Conversation, Copilot  Warm, Confident, Authentic, Honest",
            "sample_text": "Hello! मैं आज आपकी सहायता कैसे करूं?",
            "age_range": "25-35",
            "mood": "Copilot  Warm"
        },
        {
            "id": "hi-IN-SwaraNeural",
            "name": "Anchal (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits--female",
            "style": "cheerful",
            "use_cases": ["storytelling", "customer_service"],
            "description": "Warm and friendly voice ideal for children's content",
            "sample_text": "आज मैं आपके लिए एक कहानी लायी हूँ...",
            "age_range": "20-30",
            "mood": "friendly"
        },
        {
            "id": "hi-IN-PoojaNeural",
            "name": "Kavya (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits--female",
            "style": "calm",
            "use_cases": ["meditation", "audiobooks"],
            "description": "Soothing voice perfect for relaxation content",
            "sample_text": "आँखें बंद करें और गहरी सांस लें...",
            "age_range": "25-40",
            "mood": "relaxing"
        }
    ],
    "english": [
        # Amazon Polly English Voices
        {
            "id": "Joanna",
            "name": "Joanna (Female)",
            "gender": "female",
            "service": "polly",
            "style": "neutral",
            "use_cases": ["general", "customer_service"],
            "description": "High quality English female voice from Amazon Polly",
            "sample_text": "Hello, I'm Joanna. How can I help you today?",
            "age_range": "25-35",
            "mood": "neutral"
        },
        {
            "id": "Matthew",
            "name": "Matthew (Male)",
            "gender": "male",
            "service": "polly",
            "style": "neutral",
            "use_cases": ["business", "presentations"],
            "description": "High quality English male voice from Amazon Polly",
            "sample_text": "Good morning! This is Matthew speaking.",
            "age_range": "30-45",
            "mood": "professional"
        },
        {
            "id": "en-IN-PrabhatNeural",
            "name": "Prabhat (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "friendly",
            "use_cases": ["customer_service", "education"],
            "description": "Approachable voice for interactive applications",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "warm"
        },
        {
            "id": "hi-IN-SwaraNeural",
            "name": "Niku (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits--female",
            "style": "cheerful",
            "use_cases": ["storytelling", "customer_service"],
            "description": "Warm and friendly voice ideal for conversational apps",
            "sample_text": "Hello, This is a Test...",
            "age_range": "20-35",
            "mood": "friendly"
        },
        {
            "id": "en-IN-NeerjaNeural",
            "name": "Sapna (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "friendly",
            "use_cases": ["customer_service", "education"],
            "description": "Approachable voice for interactive applications",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "warm"
        },
        {
            "id": "en-IN-NeerjaExpressiveNeural",
            "name": "Neerja (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "friendly",
            "use_cases": ["customer_service", "education"],
            "description": "Approachable voice for interactive applications",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "warm"
        },
        {
            "id": "en-US-AndrewNeural",
            "name": "Shiva (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "Conversation",
            "use_cases": ["customer_service", "education"],
            "description": "Conversation, Copilot  Warm, Confident, Authentic, Honest",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "Copilot  Warm"
        },
        {
            "id": "en-US-ChristopherNeural",
            "name": "Devas (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "Conversation",
            "use_cases": ["customer_service", "education"],
            "description": "Conversation, Copilot  Warm, Confident, Authentic, Honest",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "News, Novel"
        },
         {
            "id": "en-US-EricNeural",
            "name": "Deva (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "Conversation",
            "use_cases": ["customer_service", "education"],
            "description": "Conversation, Copilot  Warm, Confident, Authentic, Honest",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "News, Novel"
        },
         {
            "id": "en-US-RogerNeural",
            "name": "Anand (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "Conversation",
            "use_cases": ["customer_service", "education"],
            "description": "Conversation, Copilot  Warm, Confident, Authentic, Honest",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "News, Novel"
        },
        {
            "id": "en-US-JennyNeural",
            "name": "Supriya (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "friendly",
            "use_cases": ["customer_service", "education"],
            "description": "Approachable voice for interactive applications",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "warm"
        },    
        {
            "id": "en-US-AnaNeural",
            "name": "Priya (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "conversational",
            "use_cases": ["educational", "narration", "explainer"],
            "description": "Friendly and clear voice ideal for educational content",
            "sample_text": "Let’s explore the basics of machine learning today...",
            "age_range": "25-35",
            "mood": "warm"
        },
        {
            "id": "en-US-GuyNeural",
            "name": "Abhi (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-ljspeech-glow-tts",
            "style": "casual",
            "use_cases": ["podcasts", "entertainment"],
            "description": "Natural conversational voice for casual content",
            "sample_text": "Hey there! Welcome to the show.",
            "age_range": "20-40",
            "mood": "engaging"
        },
        {
            "id": "en-US-AriaNeural",
            "name": "Sanaya (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "expressive",
            "use_cases": ["storytelling", "animation"],
            "description": "Dynamic voice with emotional range",
            "sample_text": "Once upon a time in a magical kingdom...",
            "age_range": "20-30",
            "mood": "playful"
        },
        {
            "id": "en-US-AvaMultilingualNeural",
            "name": "Nancy (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "expressive",
            "use_cases": ["storytelling", "animation"],
            "description": "Dynamic voice with emotional range",
            "sample_text": "Once upon a time in a magical kingdom...",
            "age_range": "20-30",
            "mood": "playful"
        },
        {
            "id": "en-CA-ClaraNeural",
            "name": "Neha (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "bold",
            "use_cases": ["trailers", "promos", "tech"],
            "description": "Bold, cinematic voice perfect for trailers",
            "sample_text": "This summer, prepare for an unforgettable journey...",
            "age_range": "20-30",
            "mood": "dramatic"
        },
        {
            "id": "en-AU-NatashaNeural",
            "name": "Zara (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "empathetic",
            "use_cases": ["healthcare", "emotional storytelling"],
            "description": "Soothing voice with an empathetic tone",
            "sample_text": "We’re here to support you on your wellness journey...",
            "age_range": "30-45",
           "mood": "calm"
        },
        {
            "id": "en-US-EmmaMultilingualNeural",
            "name": "Tanya (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "elegant",
            "use_cases": ["documentaries", "luxury_brands"],
            "description": "Sophisticated voice for premium content",
            "sample_text": "The finest craftsmanship begins with passion...",
            "age_range": "30-50",
            "mood": "refined"
        }
    ],
    "spanish": [
        {
            "id": "es-ES-AlvaroNeural",
            "name": "Carlos (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "es-css10-vits",
            "style": "formal",
            "use_cases": ["business", "education"],
            "description": "Professional Spanish voice for formal contexts",
            "sample_text": "Buenos días. Comencemos nuestra reunión.",
            "age_range": "35-50",
            "mood": "professional"
        },
        # Amazon Polly Spanish Voice
        {
            "id": "Lupe",
            "name": "Lupe (Female) - Polly",
            "gender": "female",
            "service": "polly",
            "style": "neutral",
            "use_cases": ["general", "customer_service"],
            "description": "High quality Spanish female voice from Amazon Polly",
            "sample_text": "¡Hola! ¿Cómo estás?",
            "age_range": "25-35",
            "mood": "neutral"
        },
        {
            "id": "es-ES-ElviraNeural",
            "name": "Sofia (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "es-css10-vits",
            "style": "warm",
            "use_cases": ["customer_service", "audiobooks"],
            "description": "Friendly Spanish voice for everyday interactions",
            "sample_text": "Hola, ¿en qué puedo ayudarte hoy?",
            "age_range": "25-40",
            "mood": "friendly"
        }
    ],
    "french": [
        {
            "id": "fr-FR-HenriNeural",
            "name": "Luc (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "fr-css10-vits",
            "style": "sophisticated",
            "use_cases": ["luxury_brands", "education"],
            "description": "Elegant French voice with Parisian accent",
            "sample_text": "Bonjour, je m'appelle Luc. Enchanté.",
            "age_range": "30-50",
            "mood": "refined"
        },
        {
            "id": "fr-FR-DeniseNeural",
            "name": "Élodie (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "fr-css10-vits",
            "style": "charming",
            "use_cases": ["fashion", "travel"],
            "description": "Charming voice with melodic French intonation",
            "sample_text": "Bienvenue à Paris, la ville de l'amour!",
            "age_range": "25-40",
            "mood": "playful"
        }
    ],
    "arabic": [
        {
            "id": "ar-SA-HamedNeural",
            "name": "Khalid (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "ar-css10-vits",
            "style": "authoritative",
            "use_cases": ["news", "religious"],
            "description": "Strong traditional Arabic voice",
            "sample_text": "السلام عليكم. أهلاً وسهلاً بكم.",
            "age_range": "35-55",
            "mood": "formal"
        },
        {
            "id": "ar-SA-ZariyahNeural",
            "name": "Layla (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "ar-css10-vits",
            "style": "gentle",
            "use_cases": ["education", "children"],
            "description": "Soft-spoken Arabic voice for nurturing content",
            "sample_text": "مرحباً صغيري، هل تريد أن أقرأ لك قصة؟",
            "age_range": "25-40",
            "mood": "caring"
        }
    ],
    "german": [
        {
            "id": "de-DE-ConradNeural",
            "name": "Max (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "de-css10-vits",
            "style": "precise",
            "use_cases": ["technology", "education"],
            "description": "Clear and precise German voice",
            "sample_text": "Guten Tag. Willkommen zu unserer Vorstellung.",
            "age_range": "30-50",
            "mood": "professional"
        },
        {
            "id": "de-DE-KatjaNeural",
            "name": "Anna (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "de-css10-vits",
            "style": "friendly",
            "use_cases": ["customer_service", "tourism"],
            "description": "Approachable German voice for everyday use",
            "sample_text": "Hallo! Wie kann ich Ihnen helfen?",
            "age_range": "25-40",
            "mood": "welcoming"
        }
    ],
    "japanese": [
        {
            "id": "ja-JP-KeitaNeural",
            "name": "Haruto (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "ja-css10-vits",
            "style": "formal",
            "use_cases": ["business", "education"],
            "description": "Polite Japanese voice for professional settings",
            "sample_text": "こんにちは、私はハルトと申します。よろしくお願いします。",
            "age_range": "30-50",
            "mood": "respectful"
        },
        {
            "id": "ja-JP-NanamiNeural",
            "name": "Sakura (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "ja-css10-vits",
            "style": "gentle",
            "use_cases": ["entertainment", "children"],
            "description": "Soft Japanese voice with friendly tone",
            "sample_text": "おはようございます！今日も元気にいきましょう！",
            "age_range": "20-35",
            "mood": "cheerful"
        },
        {
            "id": "hi-IN-MadhurNeural",
            "name": "Aarav (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits",
            "style": "authoritative",
            "use_cases": ["news", "presentations"],
            "description": "Deep commanding voice for professional narration",
            "sample_text": "नमस्ते, मैं आरव हूँ। आज का समाचार सुनिए...",
            "age_range": "30-40",
            "mood": "professional"
        },
        {
            "id": "hi-IN-SwaraNeural",
            "name": "Ananya (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits--female",
            "style": "cheerful",
            "use_cases": ["storytelling", "customer_service"],
            "description": "Warm and friendly voice ideal for children's content",
            "sample_text": "आज मैं आपके लिए एक कहानी लायी हूँ...",
            "age_range": "20-30",
            "mood": "friendly"
        }
    ],
    "bengali": [
        {
            "id": "bn-IN-TanishaaNeural",
            "name": "Tanishaa (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "bn-cv-vits",
            "style": "gentle",
            "use_cases": ["audiobooks", "ASMR"],
            "description": "Soft-spoken voice with lyrical quality",
            "sample_text": "আজ আমরা একটি নতুন গল্প শুরু করব...",
            "age_range": "25-35",
            "mood": "calm"
        },
        {
            "id": "bn-IN-BashkarNeural",
            "name": "Bashkar (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "bn-cv-vits",
            "style": "serious",
            "use_cases": ["documentaries", "news"],
            "description": "Authoritative delivery for factual content",
            "sample_text": "এই সংবাদটি গুরুত্বপূর্ণ...",
            "age_range": "35-45",
            "mood": "professional"
        }
    ],
    "punjabi": [
        {
            "id": None,
            "name": "Shruti (Female)",
            "gender": "female",
            "service": "coqui",
            "coqui_model": "pa-custom-v1",
            "style": "energetic",
            "use_cases": ["marketing", "podcasts"],
            "description": "High-energy voice for advertisements",
            "sample_text": "ਹੈਲੋ, ਮੈਂ ਓਜਸ ਹਾਂ...",
            "age_range": "25-40",
            "mood": "enthusiastic",
            "training_required": True,
            "training_steps": [
                "1. Collect 1 hour Punjabi male recordings",
                "2. Fine-tune on coqui.ai",
                "3. Host model on Render"
            ]
        },
        {
            "id": None,
            "name": "Vaani (Female)",
            "gender": "female",
            "service": "coqui",
            "coqui_model": "pa-cv-vits--female",
            "style": "warm",
            "use_cases": ["storytelling", "education"],
            "description": "Motherly tone for folk tales",
            "sample_text": "ਇੱਕ ਵਾਰ ਦੀ ਗੱਲ ਹੈ...",
            "age_range": "30-50",
            "mood": "nurturing"
        }
    ]
}

GTTS_LANG_CODES = {
    "hindi": "hi",
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "arabic": "ar",
    "german": "de",
    "japanese": "ja",
    "bengali": "bn",
    "gujarati": "gu",
    "tamil": "ta",
    "punjabi": "pa",
    "kannada": "kn"
}

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_audio_file(audio_data, voice_id, extension="wav"):
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"tts_{voice_id}_{timestamp}.{extension}"
        filepath = os.path.join(AUDIO_FOLDER, filename)
        
        with open(filepath, 'wb') as f:
            f.write(audio_data)
        
        return {
            "status": "success",
            "audio_url": f"/static/audio/{filename}",
            "filepath": filepath
        }
    except Exception as e:
        logger.error(f"Error saving audio file: {str(e)}")
        return {"status": "error", "message": str(e)}

async def async_generate_with_edge(text, voice_id, speed=1.0, pitch=1.0, ssml=False):
    try:
        speed = max(0.5, min(2.0, float(speed)))
        pitch = max(0.9, min(1.1, float(pitch)))
        
        rate = None
        if speed != 1.0 or pitch != 1.0:
            rate = f"{int((speed - 1) * 100)}%"
            if speed > 1.0:
                rate = f"+{rate}"
            pitch_adjust = int((pitch - 1) * 5)
            if pitch_adjust != 0:
                rate += f"{pitch_adjust:+}%"

        content = f"<speak>{text}</speak>" if ssml else text

        communicate = edge_tts.Communicate(
            text=content,
            voice=voice_id,
            rate=rate if rate else "+0%"
        )

        temp_file = os.path.join(
            tempfile.gettempdir(),
            f"edge_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"
        )
        await communicate.save(temp_file)
        return temp_file
    except Exception as e:
        logger.error(f"Edge-TTS error: {str(e)}")
        return None

def generate_with_edge(text, voice_id, speed=1.0, pitch=1.0, ssml=False):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        temp_file = loop.run_until_complete(
            async_generate_with_edge(text, voice_id, speed, pitch, ssml)
        )
        loop.close()
        
        if temp_file and os.path.exists(temp_file):
            with open(temp_file, 'rb') as f:
                audio_data = f.read()
            os.remove(temp_file)
            return audio_data
        return None
    except Exception as e:
        logger.error(f"Edge-TTS sync error: {str(e)}")
        return None

def generate_with_gtts(text, lang='en'):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            temp_path = tmp_file.name
        
        tts = gTTS(text=text, lang=lang)
        tts.save(temp_path)
        
        with open(temp_path, 'rb') as f:
            audio_data = f.read()
        
        os.remove(temp_path)
        return audio_data
    except Exception as e:
        logger.error(f"gTTS error: {str(e)}")
        return None

def generate_with_polly(text, voice_id, speed=1.0, pitch=1.0, ssml=False):
    try:
        if not polly_client:
            raise Exception("Amazon Polly client not initialized")
        
        speed_percentage = f"{int(speed * 100)}%"
        pitch_semitones = str(int((pitch - 1.0) * 12))
        
        ssml_text = f"""
        <speak>
            <prosody rate="{speed_percentage}" pitch="{pitch_semitones}st">
                {text}
            </prosody>
        </speak>
        """ if ssml else text

        response = polly_client.synthesize_speech(
            Text=ssml_text if ssml else text,
            OutputFormat='mp3',
            VoiceId=voice_id,
            TextType='ssml' if ssml else 'text'
        )

        return response['AudioStream'].read()
    except (BotoCoreError, ClientError) as error:
        logger.error(f"Amazon Polly error: {str(error)}")
        return None
    except Exception as e:
        logger.error(f"Error in Polly generation: {str(e)}")
        return None

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/csrf-token', methods=['GET'])
def get_csrf():
    return jsonify({'csrf_token': generate_csrf()})

@app.errorhandler(404)
def not_found(error):
    return jsonify({'status': 'error', 'message': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500    

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    if 'user_id' in session:
        user_id = session['user_id']
        user = users_db.get(user_id)
        if user:
            return jsonify({
                'status': 'success',
                'authenticated': True,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'subscription': subscriptions_db.get(user['id'], 'free')
                }
            })
    return jsonify({'status': 'success', 'authenticated': False})
    
# Add these new routes
@app.route('/api/auth/google')
def google_login():
    redirect_uri = url_for('google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/api/auth/google/authorize')
def google_authorize():
    token = google.authorize_access_token()
    user_info = google.get('userinfo').json()
    
    # Check if user exists
    user = next((u for u in users_db.values() if u['email'] == user_info['email']), None)
    
    if not user:
        # Create new user
        user_id = str(uuid.uuid4())
        users_db[user_id] = {
            'id': user_id,
            'email': user_info['email'],
            'name': user_info.get('name', 'Google User'),
            'password_hash': None,  # No password for OAuth users
            'created_at': datetime.utcnow().isoformat()
        }
        subscriptions_db[user_id] = 'free'
        user = users_db[user_id]
    
    # Create session
    session.clear()
    session['user_id'] = user['id']
    session['logged_in'] = True
    
    return redirect(url_for('home'))

@app.route('/api/auth/github')
def github_login():
    redirect_uri = url_for('github_authorize', _external=True)
    return github.authorize_redirect(redirect_uri)

@app.route('/api/auth/github/authorize')
def github_authorize():
    token = github.authorize_access_token()
    resp = github.get('user')
    user_info = resp.json()
    
    # Get primary email (GitHub requires separate request)
    email_resp = github.get('user/emails')
    emails = email_resp.json()
    primary_email = next(e['email'] for e in emails if e['primary'])
    
    # Check if user exists
    user = next((u for u in users_db.values() if u['email'] == primary_email), None)
    
    if not user:
        # Create new user
        user_id = str(uuid.uuid4())
        users_db[user_id] = {
            'id': user_id,
            'email': primary_email,
            'name': user_info.get('name', 'GitHub User'),
            'password_hash': None,  # No password for OAuth users
            'created_at': datetime.utcnow().isoformat()
        }
        subscriptions_db[user_id] = 'free'
        user = users_db[user_id]
    
    # Create session
    session.clear()
    session['user_id'] = user['id']
    session['logged_in'] = True
    
    return redirect(url_for('home'))    

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        if not request.is_json:
            return jsonify({'status': 'error', 'message': 'Content-Type must be application/json'}), 400

        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()

        # Validation
        if not email or not password:
            return jsonify({'status': 'error', 'message': 'Email and password are required'}), 400

        # Find user
        user = None
        for u in users_db.values():
            if u['email'].lower() == email.lower():  # Case-insensitive email comparison
                user = u
                break

        # Verify password
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401

        # Create session
        session.clear()
        session['user_id'] = user['id']
        session['logged_in'] = True

        response = jsonify({
            'status': 'success',
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'subscription': subscriptions_db.get(user['id'], 'free'),
                'created_at': user['created_at']
            }
        })
        
        # Ensure CORS headers are set
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5000')  # Update with your domain
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        
        return response

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Login failed'}), 500

# Helper functions needed:
def validate_email(email):
    """Basic email validation"""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def secure_compare(a, b):
    """Timing-attack safe string comparison"""
    return hmac.compare_digest(a.encode(), b.encode())

# You'll need to add these at startup:
from werkzeug.security import generate_password_hash, check_password_hash
    
@app.route('/api/auth/profile')
@login_required
def get_profile():
    user_id = session['user_id']
    user = users_db.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found'}), 404
    
    return jsonify({
        'status': 'success',
        'profile': {
            'email': user['email'],
            'name': user['name'],
            'created_at': user['created_at'],
            'subscription': subscriptions_db.get(user_id, 'free'),
            'chars_used': usage_db.get(user_id, {}).get('chars_used', 0),
            'daily_conversions': usage_db.get(user_id, {}).get('conversions_today', 0)
        }
    })    

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        name = data.get('name', '').strip()

        # Validation
        if not all([email, password, name]):
            return jsonify({'status': 'error', 'message': 'All fields are required'}), 400

        if not validate_email(email):
            return jsonify({'status': 'error', 'message': 'Invalid email format'}), 400

        if len(password) < 8:
            return jsonify({'status': 'error', 'message': 'Password must be at least 8 characters'}), 400

        # Check if user exists
        if any(u['email'].lower() == email.lower() for u in users_db.values()):
            return jsonify({'status': 'error', 'message': 'Email already registered'}), 400

        # Create user with hashed password
        user_id = str(uuid.uuid4())
        users_db[user_id] = {
            'id': user_id,
            'email': email,
            'name': name,
            'password_hash': generate_password_hash(password),
            'created_at': datetime.utcnow().isoformat()
        }
        subscriptions_db[user_id] = 'free'

        # Automatically log in the user
        session.clear()
        session['user_id'] = user_id
        session['logged_in'] = True

        return jsonify({
            'status': 'success',
            'user': {
                'id': user_id,
                'email': email,
                'name': name,
                'created_at': users_db[user_id]['created_at'],
                'subscription': 'free'
            }
        }), 201

    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Registration failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'status': 'success'})

@app.route('/api/subscriptions/plans')
def get_subscription_plans():
    return jsonify({
        'status': 'success',
        'plans': {
            'free': {
                'name': 'Free',
                'price': 0,
                'features': [
                    f'Up to {app.config["FREE_CHAR_LIMIT"]} characters per conversion',
                    f'Up to {app.config["FREE_DAILY_CONVERSIONS"]} conversions per day',
                    'Basic voices',
                    'Email support'
                ]
            },
            'pro': {
                'name': 'Pro',
                'price': 9.99,
                'features': [
                    f'Up to {app.config["PRO_CHAR_LIMIT"]} characters per conversion',
                    'Unlimited conversions',
                    'Premium voices',
                    'Priority support',
                    'Commercial license'
                ]
            },
            'enterprise': {
                'name': 'Enterprise',
                'price': 29.99,
                'features': [
                    'Unlimited characters',
                    'Unlimited conversions',
                    'All premium voices',
                    '24/7 priority support',
                    'API access',
                    'Commercial license'
                ]
            }
        }
    })

@app.route('/api/subscriptions/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    data = request.get_json()
    plan = data.get('plan')
    
    if plan not in ['pro', 'enterprise']:
        return jsonify({'status': 'error', 'message': 'Invalid plan'}), 400
    
    price_id = {
        'pro': 'price_your_pro_plan_id',
        'enterprise': 'price_your_enterprise_plan_id'
    }.get(plan)
    
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payment_canceled', _external=True),
            client_reference_id=session['user_id']
        )
        return jsonify({'status': 'success', 'sessionId': checkout_session['id']})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/payment/success')
def payment_success():
    return render_template('payment_success.html')

@app.route('/payment/canceled')
def payment_canceled():
    return render_template('payment_canceled.html')

@app.route('/api/subscriptions/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, app.config['STRIPE_WEBHOOK_SECRET']
        )
    except ValueError as e:
        return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'status': 'error', 'message': 'Invalid signature'}), 400
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session['client_reference_id']
        subscriptions_db[user_id] = 'pro' if 'pro' in session['display_items'][0]['plan']['id'] else 'enterprise'
    
    return jsonify({'status': 'success'})

@app.route('/api/voices', methods=['GET'])
def get_voices():
    try:
        response = {
            'status': 'success',
            'languages': list(VOICES.keys()),
            'voices': {}
        }
        
        for lang, voices in VOICES.items():
            response['voices'][lang] = []
            for voice in voices:
                response['voices'][lang].append({
                    'id': voice.get('id', voice.get('name', '')),
                    'name': voice.get('name', 'Unnamed Voice'),
                    'gender': voice.get('gender', 'unknown'),
                    'service': voice.get('service', 'edge'),
                    'style': voice.get('style', 'neutral'),
                    'description': voice.get('description', ''),
                    'sample_text': voice.get('sample_text', ''),
                    'age_range': voice.get('age_range', ''),
                    'mood': voice.get('mood', ''),
                    'use_cases': voice.get('use_cases', [])
                })
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
        
# 1. First define the admin_required decorator
def admin_required(f):
    """Restrict access to admin users only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'status': 'error', 'message': 'Login required'}), 401
            
        user = users_db.get(session['user_id'])
        if not user or not user.get('is_admin'):
            return jsonify({'status': 'error', 'message': 'Admin privileges required'}), 403
            
        return f(*args, **kwargs)
    return decorated_function

# 2. Then define your admin routes with unique endpoint names
@app.route('/api/admin/voice-config', methods=['GET'])
@admin_required
def admin_voice_config():
    """Get voice configuration details"""
    return jsonify({
        'status': 'success',
        'languages': sorted(VOICES.keys()),
        'voice_counts': {lang: len(voices) for lang, voices in VOICES.items()},
        'services': {
            'edge_tts': any(v.get('service') == 'edge' for voices in VOICES.values() for v in voices),
            'polly': any(v.get('service') == 'polly' for voices in VOICES.values() for v in voices),
            'gtts': bool(GTTS_LANG_CODES)
        }
    })

@app.route('/api/admin/system-status', methods=['GET'])
@admin_required
def admin_system_status():
    """Get system health metrics"""
    if not hasattr(app, 'start_time'):
        app.start_time = datetime.utcnow()
    
    return jsonify({
        'status': 'success',
        'system': {
            'time': datetime.utcnow().isoformat(),
            'cpu': psutil.cpu_percent(),
            'memory': psutil.virtual_memory().percent,
            'disk': psutil.disk_usage('/').percent
        },
        'app': {
            'start_time': app.start_time.isoformat(),
            'uptime': (datetime.utcnow() - app.start_time).total_seconds(),
            'config_keys': [k for k in app.config.keys() if not k.startswith('SECRET')]
        }
    })

@app.route('/api/admin/auth-status', methods=['GET'])
@admin_required
def admin_auth_status():
    """Get authentication statistics"""
    return jsonify({
        'status': 'success',
        'auth': {
            'user_id': session.get('user_id'),
            'logged_in': 'user_id' in session,
            'session_expiry': app.permanent_session_lifetime.total_seconds() 
                            if app.permanent_session_lifetime else None
        },
        'stats': {
            'total_users': len(users_db),
            'active_subscriptions': sum(1 for sub in subscriptions_db.values() if sub != 'free')
        }
    })

@app.route('/api/voices/raw-debug')
def voices_debug():
    """Return raw voice data exactly as stored in VOICES"""
    from pprint import pformat
    return f"<pre>{pformat(VOICES)}</pre>", 200

@app.route('/api/generate_tts', methods=['POST'])
@csrf.exempt
def generate_tts():  # Removed @login_required decorator
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    text = data.get('text', '').strip()
    language = data.get('language', '')
    voice_id = data.get('voice_id', '')
    use_ssml = data.get('use_ssml', False)
    speed = float(data.get('speed', 1.0))
    pitch = float(data.get('pitch', 1.0))
    
    if not text or not language or not voice_id:
        return jsonify({'status': 'error', 'message': 'Text, language and voice_id are required'}), 400
    
    # For anonymous users, apply basic limits
    char_limit = 1000  # Example limit for anonymous users
    if len(text) > char_limit:
        return jsonify({
            'status': 'error',
            'message': f'Text exceeds {char_limit} character limit for anonymous usage',
            'max_limit': char_limit,
            'code': 'char_limit_exceeded'
        }), 400

    try:
        selected_voice = next((v for v in VOICES.get(language, []) if v.get('id') == voice_id), None)
        
        if not selected_voice:
            return jsonify({'status': 'error', 'message': 'Invalid voice selection'}), 400

        service = selected_voice.get('service', 'edge')
        audio_data = None
        
        if service == 'polly':
            audio_data = generate_with_polly(text, selected_voice['id'], speed, pitch, use_ssml)
        elif service == 'edge' and selected_voice.get('id'):
            audio_data = generate_with_edge(text, selected_voice['id'], speed, pitch, use_ssml)
        
        if not audio_data:
            logger.info("Falling back to gTTS")
            lang_code = GTTS_LANG_CODES.get(language, "en")
            audio_data = generate_with_gtts(text, lang=lang_code)
            if audio_data:
                selected_voice['name'] += " (gTTS Fallback)"

        if not audio_data:
            raise Exception("All TTS methods failed")

        extension = "mp3" if service in ['gtts', 'polly'] else "wav"
        save_result = save_audio_file(audio_data, voice_id, extension)
        if save_result['status'] != 'success':
            raise Exception(save_result['message'])

        response = {
            'status': 'success',
            'audio_url': save_result['audio_url'],
            'voice_used': selected_voice['name'],
            'language': language,
            'service': service,
            'parameters': {
                'speed': speed,
                'pitch': pitch,
                'ssml': use_ssml
            },
            'voice_metadata': {
                'style': selected_voice.get('style'),
                'use_cases': selected_voice.get('use_cases', []),
                'description': selected_voice.get('description'),
                'sample_text': selected_voice.get('sample_text'),
                'age_range': selected_voice.get('age_range'),
                'mood': selected_voice.get('mood')
            }
        }
        return jsonify(response)

    except Exception as e:
        logger.error(f"TTS generation error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# COMMENTED OUT BARK TTS ENDPOINT
# @app.route('/api/bark_tts', methods=['POST'])
# def bark_tts():
#     data = request.json
#     text = data.get("text", "")
#     speed = float(data.get("speed", 1.0))
#     pitch = float(data.get("pitch", 1.0))
#     
#     output_path = os.path.join(AUDIO_FOLDER, f"bark_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav")
#     try:
#         generate_bark_tts(text, output_path, speed=speed, pitch=pitch)
#         return jsonify({
#             "status": "success", 
#             "audio_url": f"/static/audio/{os.path.basename(output_path)}",
#             "parameters": {
#                 "speed": speed,
#                 "pitch": pitch
#             }
#         })
#     except Exception as e:
#         return jsonify({"status": "error", "message": str(e)})
								 
@app.route('/api/process-file', methods=['POST'])
@login_required
def process_file():
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No selected file'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'status': 'error', 'message': 'Allowed file types: .txt'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            os.remove(filepath)
            return jsonify({
                'status': 'success',
                'text': text,
                'filename': filename
            })
        except Exception as e:
            logger.error(f"File processing error: {str(e)}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'status': 'error', 'message': 'Failed to read file'}), 500
            
    except Exception as e:
        logger.error(f"Unexpected error in file processing: {str(e)}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred'}), 500

@app.route('/api/voice-preview/<voice_id>')
def voice_preview(voice_id):
    try:
        voice = None
        for lang in VOICES.values():
            for v in lang:
                if v.get('id') == voice_id:
                    voice = v
                    break
            if voice:
                break

        if not voice:
            return jsonify({'status': 'error', 'message': 'Voice not found'}), 404

        preview_file = f"{voice_id}_preview.mp3"
        preview_path = os.path.join(VOICE_PREVIEWS, preview_file)
        
        if not os.path.exists(preview_path):
            sample_text = voice.get('sample_text', 'Hello, this is a sample')
            
            if voice.get('service') == 'polly':
                audio_data = generate_with_polly(sample_text, voice['id'])
            elif voice.get('service') == 'edge':
                audio_data = generate_with_edge(sample_text, voice['id'])
            else:
                lang_code = GTTS_LANG_CODES.get(voice.get('language'), "en")
                audio_data = generate_with_gtts(sample_text, lang=lang_code)
            
            if not audio_data:
                raise Exception("All TTS methods failed for preview")
            
            with open(preview_path, 'wb') as f:
                f.write(audio_data)

        return send_from_directory(VOICE_PREVIEWS, preview_file, mimetype="audio/mp3")

    except Exception as e:
        logger.error(f"Voice preview error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/polly-voices', methods=['GET'])
def get_polly_voices():
    try:
        if not polly_client:
            return jsonify({'status': 'error', 'message': 'Amazon Polly not configured'}), 500
            
        response = polly_client.describe_voices()
        return jsonify({
            'status': 'success',
            'voices': response['Voices']
        })
    except Exception as e:
        logger.error(f"Error fetching Polly voices: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/static/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename)

if __name__ == '__main__':
    # Create session directory if it doesn't exist
    if not os.path.exists(app.config['SESSION_FILE_DIR']):
        os.makedirs(app.config['SESSION_FILE_DIR'])
    
    #app.run(debug=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)