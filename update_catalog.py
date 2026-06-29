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
        "parse_mode": "HTML",
        "disable_web_page_preview": True # Disabilita l'anteprima ingombrante del link su Telegram
    }
    requests.post(url, json=payload)

def main():
    print("Avvio estrazione massiva assoluta su TMDB...")
    
    GENRE_MAP = get_genre_mapping()
    movies = fetch_all_streaming_titles("movie")
    tv_shows = fetch_all_streaming_titles("tv")
    
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
        except:
            db = {"movies": {}, "tv_shows": {}}
    else:
        db = {"movies": {}, "tv_shows": {}}

    nuovi_aggiunti = 0
    titoli_aggiornati = 0
    
    # Elaborazione Film
    for item in movies:
        item_id = str(item["id"])
        if item_id not in db["movies"]:
            item["genre_names"] = [GENRE_MAP.get(gid, "Sconosciuto") for gid in item.get("genre_ids", [])]
            db["movies"][item_id] = item
            nuovi_aggiunti += 1
        elif "genre_names" not in db["movies"][item_id]:
            item["genre_names"] = [GENRE_MAP.get(gid, "Sconosciuto") for gid in item.get("genre_ids", [])]
            db["movies"][item_id] = item
            titoli_aggiornati += 1

    # Elaborazione Serie TV
    print("\nInizio analisi dettagliata Serie TV...")
    for item in tv_shows:
        item_id = str(item["id"])
        is_new = item_id not in db["tv_shows"]
        needs_update = is_new or "status_ita" not in db["tv_shows"][item_id]
        
        if needs_update:
            item["genre_names"] = [GENRE_MAP.get(gid, "Sconosciuto") for gid in item.get("genre_ids", [])]
            
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
                time.sleep(0.05) 
            except Exception as e:
                item["status_ita"] = "Sconosciuto"
                item["number_of_seasons"] = 0
                item["number_of_episodes"] = 0
                
            db["tv_shows"][item_id] = item
            
            if is_new:
                nuovi_aggiunti += 1
            else:
                titoli_aggiornati += 1
                
            if (nuovi_aggiunti + titoli_aggiornati) % 500 == 0:
                print(f"...elaborati {nuovi_aggiunti + titoli_aggiornati} titoli dettagliati...")

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

    print(f"\nEstrazione completata! Aggiunti: {nuovi_aggiunti}, Aggiornati: {titoli_aggiornati}")
    
    link_sito = "https://demon6x6.github.io/MyMovieAgent/"
    messaggio = f"🎬 <b>Resoconto Agente</b>\n" \
                f"➕ Nuovi titoli trovati oggi: <b>{nuovi_aggiunti}</b>\n" \
                f"🔄 Titoli pre-esistenti aggiornati: <b>{titoli_aggiornati}</b>\n\n" \
                f"📊 Il tuo database conta ora <b>{len(db['movies'])} film</b> e <b>{len(db['tv_shows'])} serie TV</b>!\n\n" \
                f"🍿 Sfoglia il catalogo qui:\n{link_sito}"
    
    send_telegram_message(messaggio)

if __name__ == "__main__":
    main()
