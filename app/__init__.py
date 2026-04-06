from flask import Flask
from .models import db


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")  # Parametry bazy z pliku config.py

    db.init_app(app)

    with app.app_context():
        # To stworzy plik bazy (np. sqlite) przy pierwszym uruchomieniu
        db.create_all()



    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app
