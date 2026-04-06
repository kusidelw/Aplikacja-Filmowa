from flask import Blueprint, jsonify, request, render_template
from app.models import db, Media, Glos, Decyzja
from app.services import wypelnij_baze_trending, get_match_between_users
from app.models import Uzytkownik, Grupa

main_bp = Blueprint("main", __name__)



@main_bp.route("/", methods=["GET", "POST"])
def index():
    # 1. Pobieramy filmy z bazy
    movies = Media.query.all()
    match_results = None

    if request.method == "POST":
        # Tymczasowo zakładamy: Ty to ID=1, Twoja połówka to ID=2, Grupa=1
        u_id = 1 
        g_id = 1

        # 2. Zapisujemy Twoje głosy z formularza do bazy
        for movie in movies:
            rating_val = request.form.get(f'movie_{movie.id}', 0)
            rating_val = int(rating_val)

            if rating_val > 0:  # Zapisujemy tylko jeśli widziałaś
                istniejacy_glos = Glos.query.filter_by(
                    uzytkownik_id=u_id, media_id=movie.id, grupa_id=g_id
                ).first()

                if istniejacy_glos:
                    istniejacy_glos.ocena = rating_val
                else:
                    nowy_glos = Glos(uzytkownik_id=u_id, media_id=movie.id, grupa_id=g_id, ocena=rating_val)
                    db.session.add(nowy_glos)
        
        db.session.commit()

        # 3. Liczymy match z drugą osobą (u2=2)
        match_results = get_match_between_users(1, 2, 1)

    return render_template("index.html", movies=movies, results=match_results)
# 1. Pobieranie listy filmów z bazy (do wyświetlenia w aplikacji)
@main_bp.route("/movies", methods=["GET"])
def get_movies():
    movies = Media.query.all()
    return jsonify(
        [
            {
                "id": m.id,
                "xmdb_id": m.xmdb_id,
                "tytul": m.tytul,
                "opis": m.opis,
                "plakat": m.url_plakatu,
            }
            for m in movies
        ]
    )


# 2. Importowanie filmów z API XMDb (wywołaj to raz na początku)
@main_bp.route("/import-trending", methods=["GET"])
def import_trending():
    # Pobieramy np. 50 najpopularniejszych pozycji
    wynik = wypelnij_baze_trending(limit=50)
    return jsonify({"status": "success", "message": wynik})


# 3. Oddawanie głosu (zapis do bazy)
@main_bp.route("/vote", methods=["POST"])
def vote():
    data = request.json

    # Wyciągamy dane z JSON-a
    uzytkownik_id = data.get("uzytkownik_id")
    media_id = data.get("media_id")
    grupa_id = data.get("grupa_id")
    ocena = data.get("ocena")  # np. skala 1-5

    # Sprawdzamy, czy użytkownik już głosował na ten film w tej grupie
    istniejacy_glos = Glos.query.filter_by(
        uzytkownik_id=uzytkownik_id, media_id=media_id, grupa_id=grupa_id
    ).first()

    if istniejacy_glos:
        istniejacy_glos.ocena = ocena  # Aktualizujemy ocenę
    else:
        nowy_glos = Glos(
            uzytkownik_id=uzytkownik_id,
            media_id=media_id,
            grupa_id=grupa_id,
            ocena=ocena,
        )
        db.session.add(nowy_glos)

    db.session.commit()
    return jsonify({"status": "success", "message": "Głos zapisany!"})


# 4. Sprawdzanie dopasowania (wywołanie algorytmu)
@main_bp.route("/match-check", methods=["GET"])
def match_check():
    # Pobieramy ID z parametrów URL: /match-check?u1=1&u2=2&g=1
    u1 = request.args.get("u1", type=int)
    u2 = request.args.get("u2", type=int)
    g = request.args.get("g", type=int)

    if not all([u1, u2, g]):
        return jsonify({"error": "Brakujące parametry u1, u2 lub g"}), 400

    wynik = get_match_between_users(u1, u2, g)
    return jsonify(wynik)


@main_bp.route("/init-data")
def init_data():
    if not Uzytkownik.query.first():
        u1 = Uzytkownik(nazwa_uzytkownika="Emil", email="emil@test.pl")
        u2 = Uzytkownik(nazwa_uzytkownika="Dziewczyna", email="ona@test.pl")
        g1 = Grupa(nazwa_grupy="Nasze Kino")
        db.session.add_all([u1, u2, g1])
        db.session.commit()
        return "Dodano użytkowników i grupę (ID: 1 i 2, Grupa: 1)"
    return "Dane już są w bazie."
