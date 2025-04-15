import os
import torch
import logging
import warnings
from functools import wraps
from bark import SAMPLE_RATE, generate_audio, preload_models
from scipy.io.wavfile import write as write_wav
import numpy as np

# Configure cache location
BARK_CACHE_DIR = os.path.expanduser("~/.cache/suno/bark_v0")
os.makedirs(BARK_CACHE_DIR, exist_ok=True)

def initialize_bark():
    """Initialize Bark models with proper weights handling"""
    try:
        # Create a context manager for safe loading
        from torch.serialization import safe_globals
        with safe_globals([np.core.multiarray.scalar]):
            # Check for existing models
            required_files = ["text_2.pt", "coarse_2.pt", "fine_2.pt", "encodec_model.pt"]
            models_exist = all(os.path.exists(os.path.join(BARK_CACHE_DIR, f)) for f in required_files)
            
            if models_exist:
                logging.info("Using cached Bark models")
            else:
                logging.info("Downloading Bark models (first time may take several minutes)...")
            
            preload_models(
                text_use_gpu=False,
                text_use_small=False,
                coarse_use_gpu=False,
                fine_use_gpu=False,
                codec_use_gpu=False
            )
        return True
    except Exception as e:
        logging.error(f"Bark initialization failed: {str(e)}")
        return False

# Initialize on import
BARK_INITIALIZED = initialize_bark()

def generate_bark_tts(text, output_path="tts_output.wav"):
    if not BARK_INITIALIZED:
        raise Exception("Bark models not initialized - check logs for details")
    
    try:
        audio_array = generate_audio(text)
        audio_array = (audio_array * 32767).astype(np.int16)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        write_wav(output_path, SAMPLE_RATE, audio_array)
        return output_path
    except Exception as e:
        raise Exception(f"Bark TTS generation failed: {str(e)}")