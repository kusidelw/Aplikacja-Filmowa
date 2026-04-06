from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

db = SQLAlchemy()

# Tabela pomocnicza: Użytkownicy <-> Grupy
czlonkowie_grup = db.Table(
    "czlonkowie_grup",
    db.Column("uzytkownik_id", db.Integer, db.ForeignKey("uzytkownicy.id"), primary_key=True),
    db.Column("grupa_id", db.Integer, db.ForeignKey("grupy.id"), primary_key=True),
)

# Tabela pomocnicza: Media <-> Kategorie
media_kategorie = db.Table(
    "media_kategorie",
    db.Column("media_id", db.Integer, db.ForeignKey("media.id"), primary_key=True),
    db.Column("kategoria_id", db.Integer, db.ForeignKey("kategorie.id"), primary_key=True),
)

class TypMedia(enum.Enum):
    FILM = "FILM"
    SERIAL = "SERIAL"

class Decyzja(enum.Enum):
    TAK = "TAK"
    NIE = "NIE"
    MOZE = "MOZE"

class Uzytkownik(db.Model):
    __tablename__ = "uzytkownicy"
    id = db.Column(db.Integer, primary_key=True)
    nazwa_uzytkownika = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # NOWE POLA Z FIGMY
    imie = db.Column(db.String(50), nullable=True)
    nazwisko = db.Column(db.String(50), nullable=True)
    # Preferencje gatunków: {"Horror": 1, "Sci-Fi": 10}
    preferencje_gatunkowe = db.Column(db.JSON, default={}, nullable=False)

    grupy = db.relationship("Grupa", secondary=czlonkowie_grup, backref="czlonkowie")
    glosy = db.relationship("Glos", backref="autor", lazy=True)

class Grupa(db.Model):
    __tablename__ = "grupy"
    id = db.Column(db.Integer, primary_key=True)
    nazwa_grupy = db.Column(db.String(100), nullable=False)
    glosy = db.relationship("Glos", backref="grupa", lazy=True)

class Kategoria(db.Model):
    __tablename__ = "kategorie"
    id = db.Column(db.Integer, primary_key=True)
    nazwa = db.Column(db.String(50), unique=True, nullable=False)

class Media(db.Model):
    __tablename__ = "media"
    id = db.Column(db.Integer, primary_key=True)
    xmdb_id = db.Column(db.String(20), unique=True, index=True, nullable=False)
    tytul = db.Column(db.String(200), index=True, nullable=False)
    typ = db.Column(db.Enum(TypMedia), nullable=False)
    opis = db.Column(db.Text, nullable=True)
    rok_produkcji = db.Column(db.Integer, nullable=True)
    url_plakatu = db.Column(db.String(500), nullable=True)

    kategorie = db.relationship("Kategoria", secondary=media_kategorie, backref="media")

class Glos(db.Model):
    __tablename__ = "glosy"
    id = db.Column(db.Integer, primary_key=True)
    uzytkownik_id = db.Column(db.Integer, db.ForeignKey("uzytkownicy.id"), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey("media.id"), nullable=False)
    grupa_id = db.Column(db.Integer, db.ForeignKey("grupy.id"), nullable=False)
    ocena = db.Column(db.Integer, nullable=False) # Skala 0-10
    decyzja = db.Column(db.Enum(Decyzja), nullable=True)
    data_glosu = db.Column(db.DateTime, default=datetime.utcnow)