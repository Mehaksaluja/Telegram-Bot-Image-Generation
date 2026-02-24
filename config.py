import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FAL_KEY = os.getenv("FAL_KEY")

if not TELEGRAM_TOKEN or not FAL_KEY:
    raise ValueError("Missing Environment Variables!")