import os
os.system("git clone https://github.com/suno-ai/bark.git bark_tts")
os.system("pip install -r bark_tts/requirements.txt")
os.system("pip install ./bark_tts")
print("✅ Bark installed successfully")
