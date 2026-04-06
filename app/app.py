from flask import Flask, render_template, request
from app.services import calculate_advanced_match

app = Flask(__name__)

# Przykładowa baza filmów
MOVIES = [
    {"id": 1, "title": "Incepcja"},
    {"id": 2, "title": "Interstellar"},
    {"id": 3, "title": "Pulp Fiction"},
    {"id": 4, "title": "Król Lew"},
]

# Symulacja ocen drugiej osoby (np. Twojego partnera/koleżanki)
OTHER_USER_RATINGS = {1: 5, 2: 4, 3: 1, 4: 5}

@app.route('/', methods=['GET', 'POST'])
def index():
    my_ratings = {}
    match_results = None

    if request.method == 'POST':
        # Pobieramy oceny z formularza
        for movie in MOVIES:
            rating_val = request.form.get(f'movie_{movie["id"]}', 0)
            my_ratings[movie["id"]] = int(rating_val)
        
        # Liczymy match za pomocą naszej funkcji w services.py
        match_results = calculate_advanced_match(my_ratings, OTHER_USER_RATINGS)

    return render_template('index.html', movies=MOVIES, results=match_results)

if __name__ == '__main__':
    app.run(debug=True)