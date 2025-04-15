from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import os
import logging
from datetime import datetime
import edge_tts
import asyncio
from gtts import gTTS
from bark_tts.generate_bark import generate_bark_tts
from pathlib import Path
import tempfile
import torch
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

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
            "id": "hi-IN-KedarNeural",
            "name": "Roohi (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits",
            "style": "serious",
            "use_cases": ["documentaries", "education"],
            "description": "Clear and precise voice for instructional content",
            "sample_text": "आज हम विज्ञान के एक महत्वपूर्ण सिद्धांत पर चर्चा करेंगे...",
            "age_range": "35-50",
            "mood": "professional"
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
        {
            "id": "en-US-DavisNeural",
            "name": "Sophia (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-ljspeech-tacotron2-DDC",
            "style": "professional",
            "use_cases": ["business", "presentations"],
            "description": "Clear and articulate voice for professional content",
            "sample_text": "Hello everyone. Let's begin today's presentation.",
            "age_range": "30-45",
            "mood": "authoritative"
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
            "id": "en-US-RogerNeural",
            "name": "Shobhit (Male)",
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
            "id": "en-IN-PriyaNeural",
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
            "id": "en-AU-ElsieNeural",
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
            "id": "en-US-NancyNeural",
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

# Flask app setup
app = Flask(__name__)
CORS(app)

# Modern Flask initialization
@app.before_request
def initialize_services():
    if not hasattr(app, 'services_initialized'):
        # Initialize services once
        if BARK_INITIALIZED:
            logging.info("Bark TTS initialized successfully")
        else:
            logging.warning("Bark TTS initialization failed - offline mode limited")
        app.services_initialized = True
        
# Initialize Bark when app starts
with app.app_context():
    from bark_tts.generate_bark import BARK_INITIALIZED
    if not BARK_INITIALIZED:
        logging.error("Failed to initialize Bark TTS - offline functionality will be limited")							 
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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        # Validate parameters
        speed = max(0.5, min(2.0, float(speed)))
        pitch = max(0.9, min(1.1, float(pitch)))
        
        # Calculate rate adjustment (Edge-TTS expects string like "+20%" or "-10%")
        rate = None
        if speed != 1.0 or pitch != 1.0:
            # Convert speed to percentage (-50% to +100%)
            rate = f"{int((speed - 1) * 100)}%"
            if speed > 1.0:
                rate = f"+{rate}"  # Add + for positive values
            
            # Add subtle pitch adjustment (-5% to +5%)
            pitch_adjust = int((pitch - 1) * 5)
            if pitch_adjust != 0:
                rate += f"{pitch_adjust:+}%"  # Format with sign

        # Generate SSML if needed
        content = f"<speak>{text}</speak>" if ssml else text

        # Create communicate object with proper rate format
        communicate = edge_tts.Communicate(
            text=content,
            voice=voice_id,
            rate=rate if rate else "+0%"  # Edge-TTS requires string rate
        )

        # Save to temp file
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
        # Create new event loop for async call
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

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/voices', methods=['GET'])
def get_voices():
    try:
        # Enhanced response with preview URLs
        voices_with_previews = {}
        for lang, voice_list in VOICES.items():
            voices_with_previews[lang] = []
            for voice in voice_list:
                voice_data = voice.copy()
                if voice_data.get('id'):
                    voice_data['preview_url'] = f"/api/voice-preview/{voice_data['id']}"
                voices_with_previews[lang].append(voice_data)
        
        return jsonify({
            'status': 'success',
            'languages': LANGUAGES,
            'voices': voices_with_previews,
            'max_char_limit': 5000,
            'supports': {
                'speed_control': True,
                'pitch_control': True,
                'ssml': True,
                'file_upload': True
            }
        })
    except Exception as e:
        logger.error(f"Error getting voices: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/generate_tts', methods=['POST'])
def generate_tts():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    text = data.get('text', '').strip()
    language = data.get('language', '')
    voice_id = data.get('voice_id', '')
    use_bark = data.get('use_bark', False)
    use_ssml = data.get('use_ssml', False)
    speed = float(data.get('speed', 1.0))  # Default 1.0 (0.5-2.0)
    pitch = float(data.get('pitch', 1.0))  # Default 1.0 (0.5-1.5)
    
    # Validate parameters
    if not text or not language or not voice_id:
        return jsonify({'status': 'error', 'message': 'Text, language and voice_id are required'}), 400
    
    if len(text) > 5000:
        return jsonify({
            'status': 'error', 
            'message': 'Text exceeds 5000 character limit',
            'max_limit': 5000
        }), 400

    try:
        selected_voice = next((v for v in VOICES.get(language, []) if v.get('id') == voice_id), None)
        
        if not selected_voice:
            return jsonify({'status': 'error', 'message': 'Invalid voice selection'}), 400

        # Determine service to use
        service = selected_voice.get('service', 'edge')
        audio_data = None
        
        # Try Bark TTS first if requested
        if use_bark:
            output_path = os.path.join(AUDIO_FOLDER, f"bark_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav")
            try:
                generate_bark_tts(text, output_path, speed=speed, pitch=pitch)
                with open(output_path, 'rb') as f:
                    audio_data = f.read()
                return jsonify({
                    'status': 'success',
                    'audio_url': f"/static/audio/{os.path.basename(output_path)}",
                    'voice_used': f"Bark TTS ({selected_voice['name']})",
                    'service': 'bark',
                    'parameters': {
                        'speed': speed,
                        'pitch': pitch,
                        'ssml': use_ssml
                    }
                })
            except Exception as e:
                logger.warning(f"Bark TTS failed, falling back: {str(e)}")
        
        # Normal TTS flow
        if service == 'edge' and selected_voice.get('id'):
            audio_data = generate_with_edge(text, selected_voice['id'], speed, pitch, use_ssml)
        
        # Fallback to gTTS (note: gTTS doesn't support speed/pitch)
        if not audio_data:
            logger.info("Falling back to gTTS")
            lang_code = GTTS_LANG_CODES.get(language, "en")
            audio_data = generate_with_gtts(text, lang=lang_code)
            if audio_data:
                selected_voice['name'] += " (gTTS Fallback)"

        if not audio_data:
            raise Exception("All TTS methods failed")

        extension = "mp3" if service == 'gtts' else "wav"
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
               

@app.route('/api/bark_tts', methods=['POST'])
def bark_tts():
    data = request.json
    text = data.get("text", "")
    speed = float(data.get("speed", 1.0))
    pitch = float(data.get("pitch", 1.0))
    
    output_path = os.path.join(AUDIO_FOLDER, f"bark_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav")
    try:
        generate_bark_tts(text, output_path, speed=speed, pitch=pitch)
        return jsonify({
            "status": "success", 
            "audio_url": f"/static/audio/{os.path.basename(output_path)}",
            "parameters": {
                "speed": speed,
                "pitch": pitch
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/process-file', methods=['POST'])
def process_file():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
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
            return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
        return jsonify({
            'status': 'error',
            'message': 'Allowed file types: .txt'
        }), 400

@app.route('/api/voice-preview/<voice_id>')
def voice_preview(voice_id):
    try:
        # Find voice in configuration
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

        # Check if preview exists
        preview_file = f"{voice_id}_preview.mp3"
        preview_path = os.path.join(VOICE_PREVIEWS, preview_file)
        
        if not os.path.exists(preview_path):
            # Generate preview if missing
            sample_text = voice.get('sample_text', 'Hello, this is a sample')
            
            # Try Edge TTS first
            audio_data = generate_with_edge(sample_text, voice['id'])
            
            if not audio_data:
                # Fallback to gTTS
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

@app.route('/static/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)