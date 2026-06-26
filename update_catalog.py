import os
import json
import requests
from datetime import datetime, timedelta

# 1. Caricamento delle chiavi di sicurezza (Secrets)
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DB_FILE = "database.json"

def fetch_recent_titles(content_type="movie"):
    """Scarica le uscite dell'ultimo mese per film o serie tv in Italia."""
    one_month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    url = f"https://api.themoviedb.org/3/discover/{content_type}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "it-IT",
        "region": "IT",
        "sort_by": "primary_release_date.desc" if content_type == "movie" else "first_air_date.desc",
        "watch_region": "IT",
        "with_watch_providers": "8|119|337|350|390|2|3", # Netflix, Prime, Disney, Apple, Now, ecc.
    }
    
    if content_type == "movie":
        params["primary_release_date.gte"] = one_month_ago
    else:
        params["first_air_date.gte"] = one_month_ago

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json().get("results", [])

def send_telegram_message(text):
    """Invia un messaggio al bot Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

def main():
    print("Avvio ricerca su TMDB...")
    
    movies = fetch_recent_titles("movie")
    tv_shows = fetch_recent_titles("tv")
    
    # Carichiamo il database esistente o ne creiamo uno vuoto
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    else:
        db = {"movies": {}, "tv_shows": {}}

    new_additions = 0
    
    # Aggiorniamo i film
    for item in movies:
        item_id = str(item["id"])
        if item_id not in db["movies"]:
            db["movies"][item_id] = item
            new_additions += 1

    # Aggiorniamo le serie tv
    for item in tv_shows:
        item_id = str(item["id"])
        if item_id not in db["tv_shows"]:
            db["tv_shows"][item_id] = item
            new_additions += 1

    # Salviamo il database aggiornato
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

    print(f"Database aggiornato! Aggiunti {new_additions} nuovi titoli.")
    
    # Notifica Telegram temporanea
    messaggio = f"🎬 <b>Agente Aggiornato!</b>\nHo appena aggiunto {new_additions} nuovi titoli al database."
    send_telegram_message(messaggio)

if __name__ == "__main__":
    main()
