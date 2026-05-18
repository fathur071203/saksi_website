import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
    KNOWLEDGE_RAW_DIR = KNOWLEDGE_BASE_DIR / "raw"
    KNOWLEDGE_EXTRACTED_DIR = KNOWLEDGE_BASE_DIR / "extracted"
    KNOWLEDGE_CHUNKS_DIR = KNOWLEDGE_BASE_DIR / "chunks"
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "saksi-prototype-secret")
    APP_TITLE = "SAKSI KPSP"
    GEMINI_ENGINE_LABEL = os.getenv("GEMINI_ENGINE_LABEL", "Gemini RAG Engine")
    JSON_DATABASE_LABEL = "Closed-Domain JSON Knowledge Base"
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "25"))
    DOCUMENT_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx"}
    PROFILE_NAME = "Saadiah Ludmilla"
    PROFILE_ROLE = "Asisten Direktur"
    PROFILE_BADGE = "Asisten Direktur · Organik"
