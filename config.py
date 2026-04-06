import os

class Config:
    # Ścieżka do bazy danych (SQLite na początek)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'bardzo-tajny-klucz-123'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///movie_matcher.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False