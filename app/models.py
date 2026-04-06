from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

db = SQLAlchemy()

# Tabela pomocnicza dla relacji Wiele-do-Wielu (Użytkownicy <-> Grupy)
czlonkowie_grup = db.Table(
    "czlonkowie_grup",
    db.Column(
        "uzytkownik_id", db.Integer, db.ForeignKey("uzytkownicy.id"), primary_key=True
    ),
    db.Column("grupa_id", db.Integer, db.ForeignKey("grupy.id"), primary_key=True),
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

    # Relacje
    grupy = db.relationship("Grupa", secondary=czlonkowie_grup, backref="czlonkowie")
    glosy = db.relationship("Glos", backref="autor", lazy=True)


class Grupa(db.Model):
    __tablename__ = "grupy"
    id = db.Column(db.Integer, primary_key=True)
    nazwa_grupy = db.Column(db.String(100), nullable=False)

    # Relacja do głosów oddanych wewnątrz tej grupy
    glosy = db.relationship("Glos", backref="grupa", lazy=True)


class Media(db.Model):
    __tablename__ = "media"
    id = db.Column(db.Integer, primary_key=True)
    tytul = db.Column(db.String(200), nullable=False)
    typ = db.Column(db.Enum(TypMedia), nullable=False, default=TypMedia.FILM)
    opis = db.Column(db.Text, nullable=True)
    rok_produkcji = db.Column(db.Integer, nullable=True)
    url_plakatu = db.Column(db.String(500), nullable=True)


class Glos(db.Model):
    __tablename__ = "glosy"
    id = db.Column(db.Integer, primary_key=True)
    uzytkownik_id = db.Column(
        db.Integer, db.ForeignKey("uzytkownicy.id"), nullable=False
    )
    media_id = db.Column(db.Integer, db.ForeignKey("media.id"), nullable=False)
    grupa_id = db.Column(db.Integer, db.ForeignKey("grupy.id"), nullable=False)
    decyzja = db.Column(db.Enum(Decyzja), nullable=False)
    data_glosu = db.Column(db.DateTime, default=datetime.utcnow)
