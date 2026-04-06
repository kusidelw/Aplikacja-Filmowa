import os
from pathlib import Path
from dotenv import load_dotenv

# Pobieramy ścieżkę do folderu, w którym jest config.py
# (zakładamy, że .env jest w tym samym folderze co config.py i run.py)
basedir = Path(__file__).resolve().parent
env_path = basedir / ".env"

# Wymuszamy załadowanie konkretnego pliku
load_dotenv(dotenv_path=env_path)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "bardzo-tajny-klucz-123"
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL") or "sqlite:///movie_matcher.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Pobieramy klucz - dodajmy mały fallback dla testu
    XMDB_API_KEY = os.environ.get("XMDB_API_KEY")


# --- DEBUG DO TERMINALA ---
print(f"DEBUG: Szukam pliku .env w: {env_path}")
print(f"DEBUG: Czy plik istnieje? {env_path.exists()}")
print(f"DEBUG: Załadowany klucz: {os.environ.get('XMDB_API_KEY')}")
