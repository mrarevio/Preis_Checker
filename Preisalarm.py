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
import cloudscraper  # neuer Import

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

# ========== PRODUKTLISTEN ==========
produkte_5070ti = {
    "Gainward RTX 5070 Ti": "https://geizhals.at/gainward-geforce-rtx-5070-ti-v186843.html",
    "MSI RTX 5070 Ti": "https://geizhals.at/msi-geforce-rtx-5070-ti-v186766.html",
    "Palit RTX 5070 Ti": "https://geizhals.at/palit-geforce-rtx-5070-ti-v186845.html",
    "Gainward Phoenix": "https://geizhals.at/gainward-geforce-rtx-5070-ti-phoenix-v1-5509-ne7507t019t2-gb2031c-a3470768.html",
    "MSI Gaming Trio": "https://geizhals.at/msi-geforce-rtx-5070-ti-16g-gaming-trio-oc-a3445122.html",
    "ASUS ROG Strix": "https://geizhals.at/asus-rog-strix-geforce-rtx-5070-ti-oc-a3382464.html",
    "Palit GamingPro V1": "https://geizhals.at/palit-geforce-rtx-5070-ti-gamingpro-v1-ne7507t019t2-gb2031y-a3470756.html",
    "Palit GamingPro OC V1": "https://geizhals.at/palit-geforce-rtx-5070-ti-gamingpro-oc-v1-ne7507ts19t2-gb2031y-a3470759.html"
}

produkte_5080 = {
    "Palit GeForce RTX 5080 GamingPro V1": "https://geizhals.at/palit-geforce-rtx-5080-gamingpro-v1-ne75080019t2-gb2031y-a3487808.html",
    "Zotac GeForce RTX 5080": "https://geizhals.at/zotac-geforce-rtx-5080-v186817.html",
    "INNO3D GeForce RTX 5080 X3": "https://geizhals.at/inno3d-geforce-rtx-5080-x3-n50803-16d7-176068n-a3382794.html",
    "Gainward GeForce RTX 5080 Phoenix GS V1": "https://geizhals.at/gainward-geforce-rtx-5080-phoenix-v1-5615-ne75080s19t2-gb2031c-a3491334.html",
    "Palit GeForce RTX 5080 GamingPro": "https://geizhals.at/palit-geforce-rtx-5080-gamingpro-ne75080019t2-gb2031a-a3382521.html",
    "ZOTAC RTX 5080": "https://www.idealo.at/preisvergleich/OffersOfProduct/205789430_-geforce-rtx-5080-zotac.html",
    "Palit RTX 5080 GamingPro OC": "https://www.idealo.at/preisvergleich/OffersOfProduct/205796824_-geforce-rtx-5080-gamingpro-oc-palit.html",
    "Gainward RTX 5080": "https://www.idealo.at/preisvergleich/OffersOfProduct/205796547_-geforce-rtx-5080-gainward.html",
    "Gainward RTX 5080 Phoenix": "https://www.idealo.at/preisvergleich/OffersOfProduct/205796554_-geforce-rtx-5080-phoenix-gainward.html"
}

def robust_scrape(url, max_retries=3):
    scraper = cloudscraper.create_scraper()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }

    for attempt in range(max_retries):
        try:
            res = scraper.get(url, headers=headers, timeout=10)
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
                return preis, datum
        except Exception as e:
            print(f"Fehler bei Versuch {attempt + 1}: {e}")
            time.sleep(2 ** attempt)
    return None, None

def speichere_tagesdaten(daten, dateiname):
    df = pd.DataFrame(daten)
    vorhanden = pd.read_json(dateiname) if os.path.exists(dateiname) else pd.DataFrame()
    aktualisiert = pd.concat([vorhanden, df])
    aktualisiert.to_json(dateiname, orient='records', indent=2)

def lade_daten(dateiname):
    return pd.read_json(dateiname) if os.path.exists(dateiname) else pd.DataFrame()

def show_prices(df):
    if df.empty:
        st.info("Noch keine Daten verfügbar.")
    else:
        st.dataframe(df[['product', 'price', 'date', 'url']], use_container_width=True)

st.title("💻 GPU Preis-Tracker Pro")

tab1, tab2 = st.tabs(["5070 Ti", "5080"])

with tab1:
    st.header("Preisübersicht für 5070 Ti")
    daten_5070ti = []
    for name, url in produkte_5070ti.items():
        preis, datum = robust_scrape(url)
        if preis is not None:
            daten_5070ti.append({'product': name, 'price': preis, 'date': datum, 'url': url})
    speichere_tagesdaten(daten_5070ti, os.path.join(DATA_DIR, "preise_5070ti.json"))
    df_5070ti = lade_daten(os.path.join(DATA_DIR, "preise_5070ti.json"))
    show_prices(df_5070ti)

with tab2:
    st.header("Preisübersicht für 5080")
    daten_5080 = []
    for name, url in produkte_5080.items():
        preis, datum = robust_scrape(url)
        if preis is not None:
            daten_5080.append({'product': name, 'price': preis, 'date': datum, 'url': url})
    speichere_tagesdaten(daten_5080, os.path.join(DATA_DIR, "preise_5080.json"))
    df_5080 = lade_daten(os.path.join(DATA_DIR, "preise_5080.json"))
    show_prices(df_5080)
