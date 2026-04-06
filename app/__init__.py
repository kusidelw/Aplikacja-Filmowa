from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager  # DODANE
from .models import db, Uzytkownik  # DODANE Uzytkownik


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)

    # --- KONFIGURACJA LOGOWANIA ---
    login_manager = LoginManager()
    login_manager.login_view = (
        "main.login"  # Gdzie przekierować, gdy ktoś nie jest zalogowany
    )
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        # To mówi Flask-Login, jak znaleźć użytkownika w bazie po ID
        return Uzytkownik.query.get(int(user_id))

    # ------------------------------

    with app.app_context():
        db.create_all()

    from .routes import main

    app.register_blueprint(main)

    return app
