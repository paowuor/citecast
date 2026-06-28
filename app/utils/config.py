import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # B2
    B2_KEY_ID = os.getenv("B2_KEY_ID")
    B2_APP_KEY = os.getenv("B2_APP_KEY")
    B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")
    
    # API Keys
    GMI_API_KEY = os.getenv("GMI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")