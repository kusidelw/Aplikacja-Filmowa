import requests
import time
from flask import current_app
from app.models import Glos, Media, Decyzja, db, TypMedia, Kategoria, Uzytkownik
from sqlalchemy import func

XMDb_BASE_URL = "https://xmdbapi.com/api/v1"

# --- CZĘŚĆ 1: IMPORTY (Wszystkie funkcje, których szuka routes.py) ---


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
            for nazwa_gatunku in item.get("genres", []):
                kat = Kategoria.query.filter_by(
                    nazwa=nazwa_gatunku
                ).first() or Kategoria(nazwa=nazwa_gatunku)
                nowy.kategorie.append(kat)
            db.session.add(nowy)
            nowe_elementy += 1
    db.session.commit()
    return f"Sukces! Dodano {nowe_elementy} nowych pozycji."


def importuj_duzo_filmow(limit_stron=5):
    """Przywrócona funkcja, której brakowało w Twoim pliku"""
    api_key = current_app.config.get("XMDB_API_KEY")
    headers = {"X-API-Key": api_key}
    nastepny_kursor = None
    lacznie_dodano = 0
    for strona in range(limit_stron):
        url = f"{XMDb_BASE_URL}/trending?count=50&lang=pl"
        if nastepny_kursor:
            url += f"&after={nastepny_kursor}"
        try:
            res = requests.get(url, headers=headers)
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
        if dane.get("has_next_page"):
            nastepny_kursor = dane.get("next_cursor")
            time.sleep(1)
        else:
            break
    return lacznie_dodano


def import_masowy(ilosc_stron=50):
    """Przywrócona funkcja do budowania wielkiej bazy"""
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
            if res.status_code == 429:
                time.sleep(30)
                continue
            res.raise_for_status()
            dane = res.json()
        except:
            break
        for item in dane.get("results", []):
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
        time.sleep(1.2)
        if dane.get("has_next_page"):
            nastepny_kursor = dane.get("next_cursor")
        else:
            break
    return lacznie_dodano


def importuj_po_slowie_kluczowym(fraza, limit=50):
    """Przywrócona funkcja wyszukiwania"""
    api_key = current_app.config.get("XMDB_API_KEY")
    url = f"{XMDb_BASE_URL}/search?q={fraza}&limit={limit}&lang=pl"
    headers = {"X-API-Key": api_key}
    try:
        res = requests.get(url, headers=headers)
        dane = res.json()
    except:
        return "Błąd API"
    nowe = 0
    for item in dane.get("results", []):
        if item.get("type") != "title":
            continue
        if not Media.query.filter_by(xmdb_id=item["id"]).first():
            m = requests.get(
                f"{XMDb_BASE_URL}/movies/{item['id']}",
                params={"apiKey": api_key, "lang": "pl"},
            ).json()
            nowy = Media(
                xmdb_id=item["id"],
                tytul=m.get("title") or item.get("name"),
                typ=(
                    TypMedia.FILM
                    if "Movie" in m.get("title_type", "Movie")
                    else TypMedia.SERIAL
                ),
                opis=m.get("plot"),
                rok_produkcji=m.get("release_year") or item.get("year"),
                url_plakatu=m.get("poster_url") or item.get("image"),
            )
            for g in m.get("genres", []):
                kat = Kategoria.query.filter_by(nazwa=g).first() or Kategoria(nazwa=g)
                nowy.kategorie.append(kat)
            db.session.add(nowy)
            nowe += 1
            time.sleep(1.2)
    db.session.commit()
    return f"Dodano {nowe} pozycji."


# --- CZĘŚĆ 2: LOGIKA TWOJEJ DZIEWCZYNY (Veto, Rekomendacje, Match 1-10) ---


def czy_gatunek_zablokowany(uzytkownik, media, oceny_uzytkownika):
    media_kategorie_nazwy = [k.nazwa.lower() for k in media.kategorie]
    if (
        hasattr(uzytkownik, "preferencje_gatunkowe")
        and uzytkownik.preferencje_gatunkowe
    ):
        for gatunek, pref_ocena in uzytkownik.preferencje_gatunkowe.items():
            if gatunek.lower() in media_kategorie_nazwy and pref_ocena <= 2:
                return True
    for kat_obj in media.kategorie:
        niskie_oceny = (
            Glos.query.join(Media)
            .filter(
                Glos.uzytkownik_id == uzytkownik.id,
                Glos.ocena.between(1, 2),
                Media.kategorie.contains(kat_obj),
            )
            .count()
        )
        if niskie_oceny >= 3:
            return True
    return False


def calculate_advanced_match(user1_ratings, user2_ratings):
    seen1 = {i_id for i_id, r in user1_ratings.items() if r > 0}
    seen2 = {i_id for i_id, r in user2_ratings.items() if r > 0}
    common = seen1.intersection(seen2)
    all_seen = seen1.union(seen2)
    if not all_seen:
        return {"match_total": 0, "taste_similarity": 0, "coverage": 0}
    taste_score = 0
    if common:
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
    r1 = {
        g.media_id: g.ocena
        for g in Glos.query.filter_by(uzytkownik_id=u1_id, grupa_id=g_id).all()
    }
    r2 = {
        g.media_id: g.ocena
        for g in Glos.query.filter_by(uzytkownik_id=u2_id, grupa_id=g_id).all()
    }
    if not r1 or not r2:
        return {"error": "Brak wspólnych ocen", "match_total": 0}
    return calculate_advanced_match(r1, r2)


def get_safe_recommendations(u1_id, u2_id, g_id, limit=5):
    u2 = Uzytkownik.query.get(u2_id)
    oceny1 = {
        g.media_id: g.ocena
        for g in Glos.query.filter_by(uzytkownik_id=u1_id, grupa_id=g_id).all()
    }
    oceny2 = {
        g.media_id: g.ocena
        for g in Glos.query.filter_by(uzytkownik_id=u2_id, grupa_id=g_id).all()
    }
    propozycje = []
    for m_id, ocena in oceny1.items():
        if ocena >= 9 and oceny2.get(m_id, 0) == 0:
            film = Media.query.get(m_id)
            if film and not czy_gatunek_zablokowany(u2, film, oceny2):
                propozycje.append(film)
        if len(propozycje) >= limit:
            break
    return propozycje
