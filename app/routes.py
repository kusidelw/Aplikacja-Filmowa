from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import Uzytkownik, Grupa, Media, Glos, Decyzja
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from app.services import (
    wypelnij_baze_trending,
    get_match_between_users,
    importuj_duzo_filmow,
    import_masowy,
    importuj_po_slowie_kluczowym,
    get_safe_recommendations,
)

# Zmieniamy nazwę na 'main', aby pasowała do url_for w Twoich plikach HTML
main = Blueprint("main", __name__)


# --- STRONA GŁÓWNA ---
@main.route("/")
def home():
    # Pobieramy polecane filmy do gridu na dole strony
    polecane_filmy = Media.query.order_by(func.random()).limit(10).all()

    aktywnosci = []
    aktywna_grupa = None
    match_procent = 0

    if current_user.is_authenticated:
        # Feed aktywności: ostatnie głosy z bazy
        aktywnosci = Glos.query.order_by(Glos.data_glosu.desc()).limit(5).all()

        # Pobieramy pierwszą grupę użytkownika do sidebaru
        if current_user.grupy:
            aktywna_grupa = current_user.grupy[0]
            # Przykładowy wyliczenie matchu dla grupy w sidebarze
            if len(aktywna_grupa.czlonkowie) > 1:
                partner = [
                    u for u in aktywna_grupa.czlonkowie if u.id != current_user.id
                ][0]
                match_data = get_match_between_users(
                    current_user.id, partner.id, aktywna_grupa.id
                )
                match_procent = match_data.get("match_total", 0)

    return render_template(
        "index.html",
        polecane_filmy=polecane_filmy,
        aktywnosci=aktywnosci,
        aktywna_grupa=aktywna_grupa,
        match_procent=match_procent,
    )


# --- AUTORYZACJA ---
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Pobieramy dane zgodnie z polami 'name' w Twoim HTML
        imie = request.form.get("imie")
        nazwisko = request.form.get("nazwisko")
        nazwa_uzytkownika = request.form.get("nazwa_uzytkownika")
        email = request.form.get("email")
        password = request.form.get("password")

        istnieje = Uzytkownik.query.filter(
            (Uzytkownik.email == email)
            | (Uzytkownik.nazwa_uzytkownika == nazwa_uzytkownika)
        ).first()
        if istnieje:
            flash("Użytkownik o takim emailu lub loginie już istnieje.")
            return redirect(url_for("main.register"))

        nowy = Uzytkownik(
            imie=imie,
            nazwisko=nazwisko,
            nazwa_uzytkownika=nazwa_uzytkownika,
            email=email,
            password=generate_password_hash(password),
        )
        db.session.add(nowy)
        db.session.commit()
        flash("Konto utworzone! Możesz się zalogować.")
        return redirect(url_for("main.login"))

    return render_template("register.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Pole 'username' z Twojego formularza
        username = request.form.get("username")
        password = request.form.get("password")

        user = Uzytkownik.query.filter_by(nazwa_uzytkownika=username).first()
        if not user or not check_password_hash(user.password, password):
            flash("Błędna nazwa użytkownika lub hasło.")
            return redirect(url_for("main.login"))

        login_user(user)
        return redirect(url_for("main.home"))

    return render_template("login.html")


@main.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.home"))


# --- GRUPY ---
@main.route("/groups")
@login_required
def groups():
    return render_template("your_groups.html")


@main.route("/groups/create", methods=["POST"])
@login_required
def create_group():
    nazwa = request.form.get("nazwa_grupy")  #
    if nazwa:
        nowa_grupa = Grupa(nazwa_grupy=nazwa)
        nowa_grupa.czlonkowie.append(current_user)
        db.session.add(nowa_grupa)
        db.session.commit()
    return redirect(url_for("main.groups"))


@main.route("/match/<int:grupa_id>")
@login_required
def match(grupa_id):
    grupa = Grupa.query.get_or_404(grupa_id)
    match_procent = 0
    if len(grupa.czlonkowie) > 1:
        partner = [u for u in grupa.czlonkowie if u.id != current_user.id][0]
        match_data = get_match_between_users(current_user.id, partner.id, grupa.id)
        match_procent = match_data.get("match_total", 0)

    return render_template("match.html", grupa=grupa, match_procent=match_procent)


# --- TRYB OCENIANIA ---
@main.route("/rate")
@main.route("/rate/<int:media_id>")  # Dodaliśmy drugą opcję trasy
@login_required
def rate(media_id=None):
    if media_id:
        # Jeśli kliknięto "Oceń" przy konkretnym filmie na stronie głównej
        film = Media.query.get_or_404(media_id)
    else:
        # Standardowe losowanie nieocenionego filmu
        ocenione_ids = [g.media_id for g in current_user.glosy]
        film = (
            Media.query.filter(~Media.id.in_(ocenione_ids))
            .order_by(func.random())
            .first()
        )

    return render_template("vote.html", film=film)


@main.route("/rate/submit", methods=["POST"])
@login_required
def rate_submit():
    media_id = request.form.get("media_id")
    ocena = int(request.form.get("ocena", 0))
    decyzja_str = request.form.get("decyzja", "NIE")
    decyzja = Decyzja.TAK if decyzja_str == "TAK" else Decyzja.NIE

    if not current_user.grupy:
        flash("Musisz najpierw stworzyć grupę lub do niej dołączyć, aby oceniać filmy!")
        return redirect(url_for("main.groups"))

    for grupa in current_user.grupy:
        istniejacy_glos = Glos.query.filter_by(
            uzytkownik_id=current_user.id, media_id=media_id, grupa_id=grupa.id
        ).first()

        if istniejacy_glos:
            istniejacy_glos.ocena = ocena
            istniejacy_glos.decyzja = decyzja
        else:
            nowy_glos = Glos(
                uzytkownik_id=current_user.id,
                media_id=media_id,
                grupa_id=grupa.id,
                ocena=ocena,
                decyzja=decyzja,
            )
            db.session.add(nowy_glos)

    db.session.commit()
    return redirect(url_for("main.rate"))


# --- USTAWIENIA I ARCHIWUM ---
@main.route("/my-votes")
@login_required
def my_votes():
    return render_template("your_votes.html")


@main.route("/settings")
@login_required
def settings():
    return render_template("settings.html")


@main.route("/settings/update", methods=["POST"])
@login_required
def update_settings():
    current_user.imie = request.form.get("imie")  #
    current_user.nazwisko = request.form.get("nazwisko")
    current_user.email = request.form.get("email")
    db.session.commit()
    flash("Dane zostały zaktualizowane.")
    return redirect(url_for("main.settings"))


# --- ENDPOINTY ADMINISTRACYJNE (API) ---
@main.route("/import-search/<string:fraza>")
def import_search(fraza):
    wynik = importuj_po_slowie_kluczowym(fraza, limit=50)
    return jsonify({"status": "success", "message": wynik})


@main.route("/import-mass")
def import_mass_route():
    ile = import_masowy(ilosc_stron=50)
    return jsonify({"status": "success", "message": f"Dodano {ile} nowych pozycji."})
