from flask import Blueprint, jsonify, request, render_template
from app.models import db, Media, Glos, Decyzja, Uzytkownik, Grupa, Kategoria
from sqlalchemy import func
from app.services import (
    wypelnij_baze_trending,
    get_match_between_users,
    importuj_duzo_filmow,
    import_masowy,
    importuj_po_slowie_kluczowym,  # DODANE
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET", "POST"])
def index():
    # Pobieramy 20 losowych filmów na start
    movies = Media.query.order_by(func.random()).limit(20).all()
    match_results = None
    return render_template("index.html", movies=movies, results=match_results)


@main_bp.route("/movies", methods=["GET"])
def get_movies():
    movies = Media.query.all()
    return jsonify(
        [
            {
                "id": m.id,
                "tytul": m.tytul,
                "opis": m.opis,
                "plakat": m.url_plakatu,
                "kategorie": [k.nazwa for k in m.kategorie],
            }
            for m in movies
        ]
    )


# NOWY ENDPOINT: Wyszukiwanie masowe po słowie
# Użycie: 127.0.0.1:5000/import-search/Batman
@main_bp.route("/import-search/<string:fraza>")
def import_search(fraza):
    wynik = importuj_po_slowie_kluczowym(fraza, limit=50)
    return jsonify({"status": "success", "message": wynik})


@main_bp.route("/import-mass")
def import_mass_route():
    ile = import_masowy(ilosc_stron=50)
    return jsonify({"status": "success", "message": f"Dodano {ile} nowych pozycji."})


@main_bp.route("/import-full")
def import_full():
    ile = importuj_duzo_filmow(limit_stron=10)
    return jsonify({"status": "success", "message": f"Dodano {ile} pozycji."})


@main_bp.route("/vote", methods=["POST"])
def vote():
    data = request.json
    glos = Glos.query.filter_by(
        uzytkownik_id=data["uzytkownik_id"],
        media_id=data["media_id"],
        grupa_id=data["grupa_id"],
    ).first()

    if glos:
        glos.ocena = data["ocena"]
    else:
        db.session.add(
            Glos(
                uzytkownik_id=data["uzytkownik_id"],
                media_id=data["media_id"],
                grupa_id=data["grupa_id"],
                ocena=data["ocena"],
            )
        )
    db.session.commit()
    return jsonify({"status": "success"})


@main_bp.route("/init-data")
def init_data():
    if not Uzytkownik.query.first():
        u1 = Uzytkownik(nazwa_uzytkownika="Emil", email="emil@test.pl")
        u2 = Uzytkownik(nazwa_uzytkownika="Dziewczyna", email="ona@test.pl")
        g1 = Grupa(nazwa_grupy="Nasze Kino")
        db.session.add_all([u1, u2, g1])
        db.session.commit()
        return "Dodano użytkowników i grupę."
    return "Dane już są."
