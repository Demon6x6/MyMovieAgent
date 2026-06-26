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

def get_genre_mapping():
    """Scarica il dizionario dei generi per tradurre gli ID numerici in testo."""
    genres = {}
    try:
        urls = [
            f"https://api.themoviedb.org/3/genre/movie/list?api_key={TMDB_API_KEY}&language=it-IT",
            f"https://api.themoviedb.org/3/genre/tv/list?api_key={TMDB_API_KEY}&language=it-IT"
        ]
        for url in urls:
            resp = requests.get(url)
            if resp.status_code == 200:
                for g in resp.json().get("genres", []):
                    genres[g["id"]] = g["name"]
    except Exception as e:
        print("Errore nel recupero generi:", e)
    return genres

def fetch_all_streaming_titles(content_type="movie"):
    """Estrae il 100% dei titoli spacchettando la ricerca anno per anno."""
    all_results = []
    current_year = datetime.now().year
    
    url = f"https://api.themoviedb.org/3/discover/{content_type}"
    
    for year in range(1950, current_year + 1):
        page = 1
        max_pages = 500
        
        while page <= max_pages:
            params = {
                "api_key": TMDB_API_KEY,
                "language": "it-IT",
                "region": "IT",
                "watch_region": "IT",
                "with_watch_monetization_types": "flatrate|free|ads|rent|buy",
                "page": page
            }
            
            if content_type == "movie":
                params["primary_release_year"] = year
            else:
                params["first_air_date_year"] = year
                
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if not results:
                break 
                
            all_results.extend(results)
            total_pages = data.get("total_pages", 1)
            
            if page >= total_pages:
                break 
                
            page += 1
            time.sleep(0.05) 
            
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
    
    # 1. Recuperiamo la mappa dei generi
    GENRE_MAP = get_genre_mapping()
    
    # 2. Scarichiamo le liste generali
    movies = fetch_all_streaming_titles("movie")
    tv_shows = fetch_all_streaming_titles("tv")
    
    # 3. Carichiamo il DB esistente
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
        except:
            db = {"movies": {}, "tv_shows": {}}
    else:
        db = {"movies": {}, "tv_shows": {}}

    elementi_aggiornati = 0
    
    # 4. Elaborazione Film
    for item in movies:
        item_id = str(item["id"])
        # Aggiorniamo se è nuovo o se gli mancano i nomi dei generi (aggiornamento per la nuova UI)
        if item_id not in db["movies"] or "genre_names" not in db["movies"][item_id]:
            item["genre_names"] = [GENRE_MAP.get(gid, "Sconosciuto") for gid in item.get("genre_ids", [])]
            db["movies"][item_id] = item
            elementi_aggiornati += 1

    # 5. Elaborazione Serie TV (con estrazione dettagli extra)
    print("\nInizio analisi dettagliata Serie TV (recupero info su interruzioni e stagioni)...")
    for item in tv_shows:
        item_id = str(item["id"])
        
        # Entriamo qui se la serie è nuova OPPURE se è già nel DB ma non le abbiamo mai chiesto lo status
        if item_id not in db["tv_shows"] or "status_ita" not in db["tv_shows"][item_id]:
            item["genre_names"] = [GENRE_MAP.get(gid, "Sconosciuto") for gid in item.get("genre_ids", [])]
            
            # Chiamata specifica per i dettagli della singola serie TV
            detail_url = f"https://api.themoviedb.org/3/tv/{item_id}"
            params = {"api_key": TMDB_API_KEY, "language": "it-IT"}
            try:
                resp = requests.get(detail_url, params=params)
                if resp.status_code == 200:
                    details = resp.json()
                    item["number_of_seasons"] = details.get("number_of_seasons", 0)
                    item["number_of_episodes"] = details.get("number_of_episodes", 0)
                    
                    raw_status = details.get("status", "")
                    if raw_status == "Canceled":
                        item["status_ita"] = "🚨 CANCELLATA / INTERROTTA"
                    elif raw_status == "Ended":
                        item["status_ita"] = "✅ Conclusa"
                    elif raw_status == "Returning Series":
                        item["status_ita"] = "🔄 In corso (Rinnovata)"
                    elif raw_status == "Miniseries":
                        item["status_ita"] = "📺 Miniserie"
                    else:
                        item["status_ita"] = raw_status 
                time.sleep(0.05) # Pausa vitale per non farsi bloccare da TMDB!
            except Exception as e:
                item["status_ita"] = "Sconosciuto"
                item["number_of_seasons"] = 0
                item["number_of_episodes"] = 0
                
            db["tv_shows"][item_id] = item
            elementi_aggiornati += 1
            
            # Un piccolo log per tenere traccia se stiamo macinando molti dati
            if elementi_aggiornati % 500 == 0:
                print(f"...elaborati {elementi_aggiornati} titoli dettagliati...")

    # Salviamo il database aggiornato
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

    print(f"\nEstrazione e patch completata! Elaborati/Aggiunti {elementi_aggiornati} titoli totali.")
    
    # Notifica Telegram
    link_sito = "https://demon6x6.github.io/MyMovieAgent/" 
    messaggio = f"🎬 <b>Aggiornamento Profondo Completato!</b>\nHo aggiunto o aggiornato con i nuovi dettagli {elementi_aggiornati} titoli.\nIl database contiene <b>{len(db['movies'])} film</b> e <b>{len(db['tv_shows'])} serie TV</b>!\n\n🍿 Filtra per genere e scopri le serie interrotte qui:\n{link_sito}"
    
    send_telegram_message(messaggio)

if __name__ == "__main__":
    main()
