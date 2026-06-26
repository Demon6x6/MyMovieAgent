import os
import json
import requests
import time
from datetime import datetime

# 1. Caricamento delle chiavi di sicurezza (Secrets)
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DB_FILE = "database.json"

def fetch_all_streaming_titles(content_type="movie"):
    """Estrae il 100% dei titoli spacchettando la ricerca anno per anno."""
    all_results = []
    current_year = datetime.now().year
    
    url = f"https://api.themoviedb.org/3/discover/{content_type}"
    
    # Viaggio nel tempo: dal 1950 all'anno in corso
    for year in range(1950, current_year + 1):
        page = 1
        max_pages = 500
        
        while page <= max_pages:
            params = {
                "api_key": TMDB_API_KEY,
                "language": "it-IT",
                "region": "IT",
                "watch_region": "IT",
                "with_watch_monetization_types": "flatrate|free|ads|rent|buy", # La chiave per avere TUTTE le piattaforme!
                "page": page
            }
            
            # Filtro per anno esatto in base a se è film o serie
            if content_type == "movie":
                params["primary_release_year"] = year
            else:
                params["first_air_date_year"] = year
                
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if not results:
                break # Pagina vuota, passiamo alla successiva
                
            all_results.extend(results)
            
            total_pages = data.get("total_pages", 1)
            
            if page >= total_pages:
                break # Finite le pagine di questo specifico anno!
                
            page += 1
            time.sleep(0.05) # Pausa di sicurezza per l'API
            
        # Stampiamo nei log di GitHub a che anno siamo arrivati
        print(f"Scaricati tutti i {content_type} dell'anno {year}...")
        
    return all_results

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
    print("Avvio estrazione massiva assoluta su TMDB...")
    
    movies = fetch_all_streaming_titles("movie")
    tv_shows = fetch_all_streaming_titles("tv")
    
    # Carichiamo il DB esistente in modo sicuro
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
        except:
            db = {"movies": {}, "tv_shows": {}}
    else:
        db = {"movies": {}, "tv_shows": {}}

    new_additions = 0
    
    # Inserimento film
    for item in movies:
        item_id = str(item["id"])
        if item_id not in db["movies"]:
            db["movies"][item_id] = item
            new_additions += 1

    # Inserimento serie TV
    for item in tv_shows:
        item_id = str(item["id"])
        if item_id not in db["tv_shows"]:
            db["tv_shows"][item_id] = item
            new_additions += 1

    # Salviamo il "mega" database aggiornato
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

    print(f"Estrazione completata! Aggiunti {new_additions} titoli totali al DB.")
    
    # Notifica Telegram finale
    link_sito = "https://demon6x6.github.io/MyMovieAgent/" 
    messaggio = f"🎬 <b>Estrazione Assoluta Completata!</b>\nHo trovato {new_additions} nuovi titoli.\nIl tuo archivio totale vanta ora <b>{len(db['movies'])} film</b> e <b>{len(db['tv_shows'])} serie TV</b>!\n\n🍿 Esplora tutto qui:\n{link_sito}"
    
    send_telegram_message(messaggio)

if __name__ == "__main__":
    main()
