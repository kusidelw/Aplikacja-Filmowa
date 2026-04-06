import requests
import time
from flask import current_app
from app.models import Glos, Media, Decyzja, db, TypMedia, Kategoria
from sqlalchemy import func

XMDb_BASE_URL = "https://xmdbapi.com/api/v1"

# --- CZĘŚĆ 1: IMPORT Z API ---


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
                typ=(
                    TypMedia.FILM
                    if "Movie" in item.get("title_type", "")
                    else TypMedia.SERIAL
                ),
                opis=item.get("plot"),
                rok_produkcji=item.get("release_year"),
                url_plakatu=item.get("poster_url"),
            )
            # Obsługa kategorii
            for nazwa_gatunku in item.get("genres", []):
                kat = Kategoria.query.filter_by(nazwa=nazwa_gatunku).first()
                if not kat:
                    kat = Kategoria(nazwa=nazwa_gatunku)
                    db.session.add(kat)
                nowy.kategorie.append(kat)

            db.session.add(nowy)
            nowe_elementy += 1

    db.session.commit()
    return f"Sukces! Dodano {nowe_elementy} nowych pozycji."


def importuj_duzo_filmow(limit_stron=5):
    api_key = current_app.config.get("XMDB_API_KEY")
    headers = {"X-API-Key": api_key}
    nastepny_kursor = None
    lacznie_dodano = 0

    for strona in range(limit_stron):
        url = f"{XMDb_BASE_URL}/trending?count=50&lang=pl"
        if nastepny_kursor:
            url += f"&after={nastepny_kursor}"

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            dane = response.json()
        except Exception as e:
            print(f"Błąd na stronie {strona}: {e}")
            break

        results = dane.get("results", [])
        if not results:
            break

        for item in results:
            if not Media.query.filter_by(xmdb_id=item["id"]).first():
                nowy = Media(
                    xmdb_id=item["id"],
                    tytul=item["title"],
                    typ=(
                        TypMedia.FILM
                        if "Movie" in item.get("title_type", "")
                        else TypMedia.SERIAL
                    ),
                    opis=item.get("plot"),
                    rok_produkcji=item.get("release_year"),
                    url_plakatu=item.get("poster_url"),
                )
                for nazwa_gatunku in item.get("genres", []):
                    kat = Kategoria.query.filter_by(nazwa=nazwa_gatunku).first()
                    if not kat:
                        kat = Kategoria(nazwa=nazwa_gatunku)
                        db.session.add(kat)
                    nowy.kategorie.append(kat)
                db.session.add(nowy)
                lacznie_dodano += 1

        db.session.commit()
        if dane.get("has_next_page"):
            nastepny_kursor = dane.get("next_cursor")
            time.sleep(1)  # Mały odstęp dla bezpieczeństwa
        else:
            break

    return lacznie_dodano


def import_masowy(ilosc_stron=50):
    """Pobiera tysiące filmów, respektując limity API"""
    api_key = current_app.config.get("XMDB_API_KEY")
    headers = {"X-API-Key": api_key}
    nastepny_kursor = None
    lacznie_dodano = 0

    for strona in range(ilosc_stron):
        url = f"{XMDb_BASE_URL}/trending?count=50&lang=pl"
        if nastepny_kursor:
            url += f"&after={nastepny_kursor}"

        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 429:  # Rate limit
                time.sleep(30)
                continue
            res.raise_for_status()
            dane = res.json()
        except:
            break

        results = dane.get("results", [])
        for item in results:
            if not Media.query.filter_by(xmdb_id=item["id"]).first():
                nowy = Media(
                    xmdb_id=item["id"],
                    tytul=item["title"],
                    typ=(
                        TypMedia.FILM
                        if "Movie" in item.get("title_type", "")
                        else TypMedia.SERIAL
                    ),
                    opis=item.get("plot"),
                    rok_produkcji=item.get("release_year"),
                    url_plakatu=item.get("poster_url"),
                )
                for g in item.get("genres", []):
                    kat = Kategoria.query.filter_by(nazwa=g).first() or Kategoria(
                        nazwa=g
                    )
                    nowy.kategorie.append(kat)
                db.session.add(nowy)
                lacznie_dodano += 1

        db.session.commit()
        print(f"Postęp: Strona {strona+1}/{ilosc_stron} zaimportowana.")
        time.sleep(1.2)  # Prędkość bezpieczna dla API

        if dane.get("has_next_page"):
            nastepny_kursor = dane.get("next_cursor")
        else:
            break

    return lacznie_dodano


# --- CZĘŚĆ 2: LOGIKA MATCHOWANIA ---
def calculate_advanced_match(user1_ratings, user2_ratings):
    seen1 = {i_id for i_id, r in user1_ratings.items() if r > 0}
    seen2 = {i_id for i_id, r in user2_ratings.items() if r > 0}
    common = seen1.intersection(seen2)
    all_seen = seen1.union(seen2)

    if not all_seen:
        return {"match_total": 0}

    taste_score = 0
    if common:
        total_diff = sum(abs(user1_ratings[i] - user2_ratings[i]) for i in common)
        taste_score = (1 - (total_diff / (len(common) * 4))) * 100

    coverage_score = (len(common) / len(all_seen)) * 100
    final = (taste_score * 0.7) + (coverage_score * 0.3)

    return {
        "match_total": round(final, 2),
        "common_count": len(common),
        "coverage": round(coverage_score, 2),
    }


def get_match_between_users(u1_id, u2_id, g_id):
    r1 = {
        g.media_id: g.ocena
        for g in Glos.query.filter_by(uzytkownik_id=u1_id, grupa_id=g_id).all()
    }
    r2 = {
        g.media_id: g.ocena
        for g in Glos.query.filter_by(uzytkownik_id=u2_id, grupa_id=g_id).all()
    }
    if not r1 or not r2:
        return {"error": "Brak ocen"}
    return calculate_advanced_match(r1, r2)


def importuj_po_slowie_kluczowym(fraza, limit=50):
    """Szuka filmów po słowie (np. 'Marvel', 'Love', 'Police', '2024') i dodaje do bazy"""
    api_key = current_app.config.get("XMDB_API_KEY")
    # Endpoint /search zgodnie z dokumentacją
    url = f"{XMDb_BASE_URL}/search?q={fraza}&limit={limit}&lang=pl"
    headers = {"X-API-Key": api_key}

    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        dane = res.json()
    except Exception as e:
        return f"Błąd: {e}"

    nowe = 0
    results = dane.get("results", [])

    for item in results:
        # Sprawdzamy czy to tytuł (API search zwraca też osoby)
        if item.get("type") != "title":
            continue

        if not Media.query.filter_by(xmdb_id=item["id"]).first():
            # Tutaj musimy dociągnąć szczegóły (plot, genres), bo /search daje tylko podstawy
            # Robimy zapytanie do /movies/{id}
            movie_res = requests.get(
                f"{XMDb_BASE_URL}/movies/{item['id']}",
                params={"apiKey": api_key, "lang": "pl"},
            )
            m_dane = movie_res.json()

            nowy = Media(
                xmdb_id=item["id"],
                tytul=m_dane.get("title") or item.get("name"),
                typ=(
                    TypMedia.FILM
                    if "Movie" in m_dane.get("title_type", "Movie")
                    else TypMedia.SERIAL
                ),
                opis=m_dane.get("plot"),
                rok_produkcji=m_dane.get("release_year") or item.get("year"),
                url_plakatu=m_dane.get("poster_url") or item.get("image"),
            )

            # Dodaj kategorie
            for g in m_dane.get("genres", []):
                kat = Kategoria.query.filter_by(nazwa=g).first() or Kategoria(nazwa=g)
                nowy.kategorie.append(kat)

            db.session.add(nowy)
            nowe += 1
            time.sleep(1.2)  # Respektujemy limity API

    db.session.commit()
    return f"Wyszukiwanie '{fraza}': Dodano {nowe} nowych pozycji."
