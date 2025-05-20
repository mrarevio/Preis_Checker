import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import os
import time
import smtplib
from email.message import EmailMessage
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import cloudscraper  # ← NEU hinzugefügt

# ========== KONFIGURATION ==========
TIMEZONE = None
DATA_DIR = "preis_daten"
os.makedirs(DATA_DIR, exist_ok=True)

# ========== DESIGN-EINSTELLUNGEN ==========
primary_color = "#FF4B4B"
secondary_color = "#1F77B4"
bg_color = "#F4F4F4"  # Helle Hintergrundfarbe für bessere Lesbarkeit
text_color = "#333"  # Dunklere Schriftfarbe für besseren Kontrast
font = "Helvetica Neue, sans-serif"

st.set_page_config(
    page_title="GPU Preis-Tracker Pro",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(f"""
    <style>
        .main {{
            background-color: {bg_color};
            color: {text_color};
            font-family: {font};
        }}
        .stButton>button {{
            background-color: {primary_color};
            color: white;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            transition: background-color 0.3s ease;
        }}
        .stButton>button:hover {{
            background-color: #FF6464; /* Hellerer Farbton bei Hover */
        }}
        .stAlert {{
            border-left: 4px solid {primary_color};
        }}
        .stProgress > div > div > div {{
            background-color: {primary_color};
        }}
        h1, h2, h3 {{
            font-family: 'Arial', sans-serif;
            font-weight: bold;
        }}
        .css-1aumxhk {{
            background-color: #FFF; /* Kartenhintergrund */
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
        }}
    </style>
""", unsafe_allow_html=True)
# ... (Design-Einstellungen und Imports bleiben gleich)

# ========== PRODUKTLISTE ==========
produkte_5070ti = {
    "Gainward RTX 5070 Ti": "https://geizhals.at/gainward-geforce-rtx-5070-ti-v186843.html",
    "MSI RTX 5070 Ti": "https://geizhals.at/msi-geforce-rtx-5070-ti-v186766.html",
    "Palit RTX 5070 Ti": "https://geizhals.at/palit-geforce-rtx-5070-ti-v186845.html",
    "Gainward Phoenix": "https://geizhals.at/gainward-geforce-rtx-5070-ti-phoenix-v1-5509-ne7507t019t2-gb2031c-a3470768.html",
    "MSI Gaming Trio": "https://geizhals.at/msi-geforce-rtx-5070-ti-16g-gaming-trio-oc-a3445122.html",
    "ASUS ROG Strix": "https://geizhals.at/asus-rog-strix-geforce-rtx-5070-ti-oc-a3382464.html",
    "Palit GamingPro V1": "https://geizhals.at/palit-geforce-rtx-5070-ti-gamingpro-v1-ne7507t019t2-gb2031y-a3470756.html",
    "Palit GamingPro OC V1": "https://geizhals.at/palit-geforce-rtx-5070-ti-gamingpro-oc-v1-ne7507ts19t2-gb2031y-a3470759.html"
    # ... (bestehende 5070 Ti Einträge)
}


produkte_5080 = {
    "ZOTAC RTX 5080": "https://www.idealo.at/preisvergleich/OffersOfProduct/205789430_-geforce-rtx-5080-zotac.html",
    "Palit RTX 5080 GamingPro OC": "https://www.idealo.at/preisvergleich/OffersOfProduct/205796824_-geforce-rtx-5080-gamingpro-oc-palit.html",
    "Gainward RTX 5080": "https://www.idealo.at/preisvergleich/OffersOfProduct/205796547_-geforce-rtx-5080-gainward.html",
    "Gainward RTX 5080 Phoenix": "https://www.idealo.at/preisvergleich/OffersOfProduct/205796554_-geforce-rtx-5080-phoenix-gainward.html"
}

# ========== PERFORMANCE OPTIMIERUNGEN ==========
SESSION = requests.Session()
SCRAPER = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)
HEADERS = {
    'Accept-Language': 'de-DE,de;q=0.9',
    'Referer': 'https://www.google.com/',
    'DNT': '1'
}

def robust_scrape(url, max_retries=3):
    try:
        # Unterschiedliche Behandlung für Geizhals/Idealo
        if "idealo" in url:
            return handle_idealo_scrape(url)
        else:
            return handle_geizhals_scrape(url)
    except Exception as e:
        st.error(f"Critical error: {str(e)}")
        return None, None

def handle_idealo_scrape(url):
    response = SCRAPER.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Neuer Parser für Idealo
    price_container = soup.find('div', {'class': 'offerList-item-price'})
    if price_container:
        price_text = price_container.find('span', {'class': 'price'}).get_text(strip=True)
        price = float(''.join(c for c in price_text if c.isdigit() or c == ',').replace(',', '.'))
        return price, datetime.now(TIMEZONE)
    
    return None, None

def handle_geizhals_scrape(url):
    response = SCRAPER.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    preis_element = soup.find('span', class_='price') or soup.find('div', class_='gh_price')
    
    if preis_element:
        price_text = preis_element.get_text(strip=True)
        price = float(''.join(c for c in price_text if c.isdigit() or c in ',.').replace('.', '').replace(',', '.'))
        return price, datetime.now(TIMEZONE)
    
    return None, None

# ========== PARALLELE VERARBEITUNG ==========
from concurrent.futures import ThreadPoolExecutor

def batch_scrape(products):
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for name, url in products.items():
            futures.append(executor.submit(scrape_product, name, url))
        
        for future in futures:
            result = future.result()
            if result:
                results.append(result)
    return results

def scrape_product(name, url):
    try:
        preis, datum = robust_scrape(url)
        if preis:
            return {'product': name, 'price': preis, 'date': datum, 'url': url}
        return None
    except Exception as e:
        st.error(f"Fehler bei {name}: {str(e)}")
        return None

# ========== AKTUALISIERUNGSFUNKTIONEN ==========
def update_prices(products, progress_bar):
    daten = batch_scrape(products)
    if daten:
        speichere_tagesdaten(daten)
        progress_bar.progress(1.0)
        time.sleep(0.5)
        return len(daten)
    return 0

# ========== DASHBOARD ANPASSUNGEN ==========
# In den Update-Buttons ersetzen durch:
if st.button("RTX 5080 Preise aktualisieren"):
    with st.spinner("RTX 5080 Preise werden aktualisiert..."):
        progress_bar = st.progress(0)
        count = update_prices(produkte_5080, progress_bar)
        if count > 0:
            st.success(f"{count} RTX 5080 Preise aktualisiert!")
            st.rerun()
        else:
            st.error("Fehler beim Aktualisieren der RTX 5080 Preise!")

# ========== CACHE OPTIMIERUNG ==========
@st.cache_resource(ttl=3600)
def load_cached_data():
    return lade_alle_daten()

# ========== DEBUGGING TOOLS ==========
def show_raw_response(url):
    response = SCRAPER.get(url, headers=HEADERS)
    with st.expander("Raw HTML Response"):
        st.code(response.text[:5000])

# In den Tabs hinzufügen:
with tab4:
    if st.checkbox("Debug-Modus aktivieren"):
        show_raw_response(next(iter(produkte_5080.values())))
