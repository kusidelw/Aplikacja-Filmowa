import requests
import time
from flask import current_app
from app.models import Glos, Media, Decyzja, db, TypMedia, Kategoria, Uzytkownik
from sqlalchemy import func

XMDb_BASE_URL = "https://xmdbapi.com/api/v1"

# --- CZĘŚĆ 1: IMPORTY (Bez zmian w strukturze API) ---

def wypelnij_baze_trending(limit=20):
    api_key = current_app.config.get("XMDB_API_KEY")
    params = {"apiKey": api_key, "count": limit, "lang": "pl"}
    try:
        response = requests.get(f"{XMDb_BASE_URL}/trending", params=params)
        response.raise_for_status()
        dane = response.json()
    except Exception as e:
        return f"Błąd połączenia z API: {e}"

    results = dane.get("results", [])
    nowe_elementy = 0
    for item in results:
        istnieje = Media.query.filter_by(xmdb_id=item["id"]).first()
        if not istnieje:
            nowy = Media(
                xmdb_id=item["id"],
                tytul=item["title"],
                typ=TypMedia.FILM if "Movie" in item.get("title_type", "") else TypMedia.SERIAL,
                opis=item.get("plot"),
                rok_produkcji=item.get("release_year"),
                url_plakatu=item.get("poster_url"),
            )
            for nazwa_gatunku in item.get("genres", []):
                kat = Kategoria.query.filter_by(nazwa=nazwa_gatunku).first() or Kategoria(nazwa=nazwa_gatunku)
                nowy.kategorie.append(kat)
            db.session.add(nowy)
            nowe_elementy += 1
    db.session.commit()
    return f"Sukces! Dodano {nowe_elementy} nowych pozycji."

# --- CZĘŚĆ 2: LOGIKA MATCHOWANIA I BEZPIECZEŃSTWA ---

def czy_gatunek_zablokowany(uzytkownik, media, oceny_uzytkownika):
    """
    Sprawdza Veto Rule:
    1. Czy gatunek jest oceniony na <= 2 w preferencjach profilu?
    2. Czy użytkownik dał ocenę 1-2 dla min. 3 filmów z tej kategorii?
    """
    media_kategorie_nazwy = [k.nazwa.lower() for k in media.kategorie]
    
    # 1. Sprawdzenie jawne w profilu (Settings.tsx)
    for gatunek, pref_ocena in uzytkownik.preferencje_gatunkowe.items():
        if gatunek.lower() in media_kategorie_nazwy and pref_ocena <= 2:
            return True

    # 2. Sprawdzenie ukryte (historia ocen 1-2)
    for kat_obj in media.kategorie:
        niskie_oceny = Glos.query.join(Media).filter(
            Glos.uzytkownik_id == uzytkownik.id,
            Glos.ocena.between(1, 2),
            Media.kategorie.contains(kat_obj)
        ).count()
        if niskie_oceny >= 3:
            return True
            
    return False

def calculate_advanced_match(user1_ratings, user2_ratings):
    """Obliczenia dla skali 1-10 (max różnica = 9)"""
    seen1 = {i_id for i_id, r in user1_ratings.items() if r > 0}
    seen2 = {i_id for i_id, r in user2_ratings.items() if r > 0}
    common = seen1.intersection(seen2)
    all_seen = seen1.union(seen2)

    if not all_seen:
        return {"match_total": 0, "taste_similarity": 0, "coverage": 0}

    taste_score = 0
    if common:
        # Skala 1-10: max różnica to 9
        total_diff = sum(abs(user1_ratings[i] - user2_ratings[i]) for i in common)
        taste_score = (1 - (total_diff / (len(common) * 9))) * 100

    coverage_score = (len(common) / len(all_seen)) * 100
    final = (taste_score * 0.7) + (coverage_score * 0.3)

    return {
        "match_total": round(final, 2),
        "taste_similarity": round(taste_score, 2),
        "common_count": len(common),
        "coverage": round(coverage_score, 2),
    }

def get_match_between_users(u1_id, u2_id, g_id):
    r1 = {g.media_id: g.ocena for g in Glos.query.filter_by(uzytkownik_id=u1_id, grupa_id=g_id).all()}
    r2 = {g.media_id: g.ocena for g in Glos.query.filter_by(uzytkownik_id=u2_id, grupa_id=g_id).all()}
    
    if not r1 or not r2:
        return {"error": "Brak wspólnych ocen", "match_total": 0}
        
    return calculate_advanced_match(r1, r2)

def get_safe_recommendations(u1_id, u2_id, g_id, limit=5):
    """Zwraca filmy, które U1 uwielbia (9-10), a U2 nie widział (0) + filtr Veto"""
    u2 = Uzytkownik.query.get(u2_id)
    oceny1 = {g.media_id: g.ocena for g in Glos.query.filter_by(uzytkownik_id=u1_id, grupa_id=g_id).all()}
    oceny2 = {g.media_id: g.ocena for g in Glos.query.filter_by(uzytkownik_id=u2_id, grupa_id=g_id).all()}

    propozycje = []
    # Szukaj filmów wysoko ocenionych przez U1, których U2 nie zna
    for m_id, ocena in oceny1.items():
        if ocena >= 9 and oceny2.get(m_id, 0) == 0:
            film = Media.query.get(m_id)
            if not czy_gatunek_zablokowany(u2, film, oceny2):
                propozycje.append(film)
        
        if len(propozycje) >= limit:
            break
            
    return propozycje