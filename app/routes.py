from flask import Blueprint, jsonify, request
from app.models import Media, db

main_bp = Blueprint('main', __name__)

@main_bp.route('/movies', methods=['GET'])
def get_movies():
    movies = Media.query.all()
    return jsonify([{"id": m.id, "tytul": m.tytul} for m in movies])

@main_bp.route('/vote', methods=['POST'])
def vote():
    data = request.json
    # Tutaj dodasz logikę zapisu głosu do bazy
    return jsonify({"status": "success", "message": "Głos oddany!"})