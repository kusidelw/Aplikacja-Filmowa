from app.models import Glos, Media, Decyzja, db
from sqlalchemy import func

def calculate_advanced_match(user1_ratings, user2_ratings):
    """
    Logika:
    1. Znajduje filmy obejrzane przez któregokolwiek z użytkowników (pula ogólna).
    2. Wylicza 'Wspólny mianownik' (co oboje widzieli).
    3. Oblicza podobieństwo ocen tylko dla tych wspólnych tytułów.
    4. Koryguje wynik o 'Coverage' (ile mają ze sobą wspólnego w kontekście obejrzanych rzeczy).
    """
    
    # Zbiory ID filmów, które zostały obejrzane (ocena > 0)
    seen1 = {item_id for item_id, rating in user1_ratings.items() if rating > 0}
    seen2 = {item_id for item_id, rating in user2_ratings.items() if rating > 0}
    
    # Filmy obejrzane przez OBOJE (część wspólna)
    common_items = seen1.intersection(seen2)
    
    # Filmy obejrzane przez PRZYNAJMNIEJ JEDNEGO (suma)
    all_seen_items = seen1.union(seen2)

    if not all_seen_items:
        return 0

    # --- KROK 1: PODOBIEŃSTWO GUSTU (Taste Score) ---
    if not common_items:
        taste_score = 0
    else:
        total_diff = 0
        max_possible_diff = 4  # 5 (uwielbiam) - 1 (nie lubię)
        
        for item_id in common_items:
            diff = abs(user1_ratings[item_id] - user2_ratings[item_id])
            total_diff += diff
            
        avg_diff = total_diff / len(common_items)
        taste_score = (1 - (avg_diff / max_possible_diff)) * 100

    # --- KROK 2: WSPÓLNE DOŚWIADCZENIE (Coverage Score) ---
    # Ile z obejrzanych filmów znamy oboje? 
    # Jeśli ja widziałam 100 filmów, a Ty 5 (i to są te same), 
    # to coverage będzie niski, bo mamy mało punktów styku.
    coverage_score = (len(common_items) / len(all_seen_items)) * 100

    # --- KROK 3: FINALNY MATCH ---
    # Możemy nadać wagi, np. 70% to gust, a 30% to wspólna baza filmów.
    # Albo po prostu średnia – Ty decydujesz!
    final_match = (taste_score * 0.7) + (coverage_score * 0.3)

    return {
        "match_total": round(final_match, 2),
        "taste_similarity": round(taste_score, 2),
        "common_movies_count": len(common_items),
        "coverage": round(coverage_score, 2)
    }