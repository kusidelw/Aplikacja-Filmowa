import requests
from flask import current_app
from app.models import Glos, Media, Decyzja, db, TypMedia
from sqlalchemy import func

XMDb_BASE_URL = "https://xmdbapi.com/api/v1"

# --- CZĘŚĆ 1: IMPORT Z API ---


def wypelnij_baze_trending(limit=20):
    """Pobiera najpopularniejsze filmy z XMDb i zapisuje w bazie"""
    api_key = current_app.config.get("XMDB_API_KEY")
    headers = {"X-API-Key": api_key}

    # Dodajemy parametr lang=en (lub pl, jeśli API wspiera już polski)
    url = f"{XMDb_BASE_URL}/trending?count={limit}&lang=en"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Sprawdza czy nie ma błędów (np. 401, 404)
    except Exception as e:
        return f"Błąd połączenia z API: {e}"

    dane = response.json()
    nowe_elementy = 0

    for item in dane.get("results", []):
        # Sprawdzamy czy film już istnieje po xmdb_id (tt...)
        istnieje = Media.query.filter_by(xmdb_id=item["id"]).first()

        if not istnieje:
            # Mapujemy typ z API na nasz Enum
            typ_z_api = item.get("title_type", "Movie")
            nasz_typ = TypMedia.FILM if "Movie" in typ_z_api else TypMedia.SERIAL

            nowy_obiekt = Media(
                xmdb_id=item["id"],
                tytul=item["title"],
                typ=nasz_typ,
                opis=item.get("plot"),
                rok_produkcji=item.get("release_year"),
                url_plakatu=item.get("poster_url"),
            )
            db.session.add(nowy_obiekt)
            nowe_elementy += 1

    db.session.commit()
    return f"Dodano {nowe_elementy} nowych pozycji do bazy!"


# --- CZĘŚĆ 2: ALGORYTM MATCHOWANIA ---


def calculate_advanced_match(user1_ratings, user2_ratings):
    """Twoja logika obliczania dopasowania"""
    seen1 = {item_id for item_id, rating in user1_ratings.items() if rating > 0}
    seen2 = {item_id for item_id, rating in user2_ratings.items() if rating > 0}

    common_items = seen1.intersection(seen2)
    all_seen_items = seen1.union(seen2)

    if not all_seen_items:
        return {"match_total": 0, "message": "Brak wspólnych filmów do oceny"}

    if not common_items:
        taste_score = 0
    else:
        total_diff = 0
        max_possible_diff = 4
        for item_id in common_items:
            diff = abs(user1_ratings[item_id] - user2_ratings[item_id])
            total_diff += diff
        avg_diff = total_diff / len(common_items)
        taste_score = (1 - (avg_diff / max_possible_diff)) * 100

    coverage_score = (len(common_items) / len(all_seen_items)) * 100
    final_match = (taste_score * 0.7) + (coverage_score * 0.3)

    return {
        "match_total": round(final_match, 2),
        "taste_similarity": round(taste_score, 2),
        "common_movies_count": len(common_items),
        "coverage": round(coverage_score, 2),
    }


def pobierz_oceny_uzytkownika(uzytkownik_id, grupa_id):
    glosy = Glos.query.filter_by(uzytkownik_id=uzytkownik_id, grupa_id=grupa_id).all()
    return {g.media_id: g.ocena for g in glosy}


def get_match_between_users(uzytkownik1_id, uzytkownik2_id, grupa_id):
    oceny1 = pobierz_oceny_uzytkownika(uzytkownik1_id, grupa_id)
    oceny2 = pobierz_oceny_uzytkownika(uzytkownik2_id, grupa_id)

    if not oceny1 or not oceny2:
        return {
            "error": "Oboje użytkowników musi ocenić przynajmniej jeden film, aby obliczyć dopasowanie."
        }

    return calculate_advanced_match(oceny1, oceny2)
