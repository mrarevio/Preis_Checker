import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import os
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import cloudscraper
import logging
from typing import Tuple, Optional, Dict, Any

# ========== LOGGING KONFIGURATION ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ========== KONSTANTEN ==========
TIMEZONE = None
DATA_DIR = "preis_daten"
REFRESH_INTERVAL = 3600  # 1 Stunde in Sekunden
MAX_RETRIES = 3
TIMEOUT = 10
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

os.makedirs(DATA_DIR, exist_ok=True)

# ========== DESIGN-EINSTELLUNGEN ==========
primary_color = "#FF4B4B"
secondary_color = "#1F77B4"
bg_color = "#F4F4F4"
text_color = "#333"
font = "Helvetica Neue, sans-serif"

st.set_page_config(
    page_title="GPU Preis-Tracker Pro-Alpha",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

[Ihr vorheriger CSS-Code bleibt unverändert]

# ========== PRODUKTLISTEN ==========
[Ihre vorherigen Produktlisten bleiben unverändert]

def validate_price_data(price: float, date: datetime) -> bool:
    """Validiert die gescrapten Preisdaten."""
    if price is None or price <= 0:
        return False
    if date is None:
        return False
    return True

@st.cache_data(ttl=3600)
def robust_scrape(url: str, max_retries: int = MAX_RETRIES) -> Tuple[Optional[float], Optional[datetime]]:
    """Verbesserte Version der Scraping-Funktion mit Caching und besserer Fehlerbehandlung."""
    scraper = cloudscraper.create_scraper()
    
    for attempt in range(max_retries):
        try:
            res = scraper.get(url, headers=HEADERS, timeout=TIMEOUT)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')

            preis_element = (
                soup.find('strong', id='pricerange-min') or
                soup.find('span', class_='price') or
                soup.find('div', class_='gh_price')
            )

            if preis_element:
                preis_text = preis_element.get_text(strip=True)
                preis = float(''.join(c for c in preis_text if c.isdigit() or c in ',.').replace('.', '').replace(',', '.'))
                datum = datetime.now(TIMEZONE)
                
                if validate_price_data(preis, datum):
                    logging.info(f"Erfolgreich gescraped: {url} - Preis: {preis}€")
                    return preis, datum
                else:
                    logging.warning(f"Ungültige Daten für {url}: Preis={preis}, Datum={datum}")
                    
        except Exception as e:
            logging.error(f"Fehler bei Versuch {attempt + 1} für {url}: {str(e)}")
            time.sleep(2 ** attempt)
            
    logging.error(f"Alle Versuche fehlgeschlagen für {url}")
    return None, None

def speichere_tagesdaten(daten: list, dateipfad: str) -> None:
    """Verbesserte Funktion zum Speichern der Preisdaten mit Backup-Funktion."""
    try:
        df = pd.DataFrame(daten)
        if not df.empty:
            vorhanden = pd.read_json(dateipfad) if os.path.exists(dateipfad) else pd.DataFrame()
            
            # Duplikate entfernen basierend auf Produkt und Datum
            aktualisiert = pd.concat([vorhanden, df]).drop_duplicates(subset=['product', 'date'])
            
            # Nach Datum sortieren
            aktualisiert = aktualisiert.sort_values('date')
            
            # Speichern mit Backup
            backup_path = dateipfad + '.backup'
            if os.path.exists(dateipfad):
                os.rename(dateipfad, backup_path)
            
            aktualisiert.to_json(dateipfad, orient='records', indent=2)
            
            if os.path.exists(backup_path):
                os.remove(backup_path)
                
            logging.info(f"Daten erfolgreich gespeichert in {dateipfad}")
    except Exception as e:
        logging.error(f"Fehler beim Speichern der Daten: {str(e)}")
        if os.path.exists(backup_path):
            os.rename(backup_path, dateipfad)

[Ihre restlichen Funktionen bleiben unverändert]

# ========== HAUPTPROGRAMM ==========
[Ihr Hauptprogramm-Code bleibt unverändert]