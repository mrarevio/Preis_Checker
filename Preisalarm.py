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

# ========== KONFIGURATION ==========
TIMEZONE = None
DATA_DIR = "preis_daten"
os.makedirs(DATA_DIR, exist_ok=True)

# ========== DESIGN-EINSTELLUNGEN ==========
primary_color = "#FF4B4B"
secondary_color = "#1F77B4"
bg_color = "#F4F4F4"
text_color = "#333"
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
            background-color: #FF6464;
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
            background-color: #FFF;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
        }}
        .timeframe-btn {{
            margin: 5px !important;
        }}
        .price-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .price-change-positive {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .price-change-negative {{
            color: #2ecc71;
            font-weight: bold;
        }}
    </style>
""", unsafe_allow_html=True)

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
            res.raise_for_status()  # Raise an error for bad responses
            soup = BeautifulSoup(res.text, 'html.parser')
            preis_element = (
                soup.find('strong', {'id': 'pricerange-min'}) or
                soup.find('span', class_='price') or
                soup.find('div', class_='gh_price')
            )

            if preis_element:
                preis_text = preis_element.get_text(strip=True)
                preis = float(''.join(c for c in preis_text if c.isdigit() or c in ',.').replace('.', '').replace(',', '.'))
                datum = datetime.now(TIMEZONE)  # Aktuelles Datum
                return preis, datum
        except requests.exceptions.RequestException as e:
            print(f"Fehler beim Scrapen von {url}: {e}")
            time.sleep(10)  # Wartezeit, um Anfragen zu streuen bei Rate Limit
        except Exception as e:
            print(f"Fehler bei Versuch {attempt + 1}: {e}")
            time.sleep(2 ** attempt)  # Exponentielles Backoff

    return None, None

def speichere_tagesdaten(daten, dateipfad):
    df = pd.DataFrame(daten)
    if not df.empty:
        vorhanden = pd.read_json(dateipfad) if os.path.exists(dateipfad) else pd.DataFrame()
        aktualisiert = pd.concat([vorhanden, df])
        aktualisiert.to_json(dateipfad, orient='records', indent=2)

def lade_daten(dateipfad):
    return pd.read_json(dateipfad) if os.path.exists(dateipfad) else pd.DataFrame()

# === SCRAPING UND DATEN SPEICHERN ===
# Scraping Daten für 5070 Ti
daten_5070ti = []
for name, url in produkte_5070ti.items():
    preis, datum = robust_scrape(url)
    if preis is not None:
        daten_5070ti.append({'product': name, 'price': preis, 'date': datum, 'url': url})
    time.sleep(random.uniform(1, 3))  # Zufällige Pause zwischen den Anfragen
speichere_tagesdaten(daten_5070ti, os.path.join(DATA_DIR, "preise_5070ti.json"))

# Scraping Daten für 5080
daten_5080 = []
for name, url in produkte_5080.items():
    preis, datum = robust_scrape(url)
    if preis is not None:
        daten_5080.append({'product': name, 'price': preis, 'date': datum, 'url': url})
    time.sleep(random.uniform(1, 3))  # Zufällige Pause zwischen den Anfragen
speichere_tagesdaten(daten_5080, os.path.join(DATA_DIR, "preise_5080.json"))

# Daten laden
df_5070ti = lade_daten(os.path.join(DATA_DIR, "preise_5070ti.json"))
df_5080 = lade_daten(os.path.join(DATA_DIR, "preise_5080.json"))

# ========== STREAMLIT TABS ==========
tab1, tab2, tab3 = st.tabs(["5070 Ti Übersicht", "5080 Übersicht", "Preis-Dashboard"])

# === TAB 1: 5070 Ti Preisübersicht ===
with tab1:
    st.header("Preisübersicht für 5070 Ti")
    if not df_5070ti.empty:
        st.dataframe(df_5070ti[['product', 'price', 'date', 'url']], use_container_width=True)
    else:
        st.warning("Keine Preisdaten für RTX 5070 Ti verfügbar.")

# === TAB 2: 5080 Preisübersicht ===
with tab2:
    st.header("Preisübersicht für 5080")
    if not df_5080.empty:
        st.dataframe(df_5080[['product', 'price', 'date', 'url']], use_container_width=True)
    else:
        st.warning("Keine Preisdaten für RTX 5080 verfügbar.")

# === TAB 3: Preis-Dashboard ===
with tab3:
    st.header("Preis-Dashboard")
    combined_df = pd.concat([df_5070ti, df_5080], ignore_index=True)
    if not combined_df.empty:
        st.dataframe(combined_df[['product', 'price', 'date']], use_container_width=True)
        
        # Hier können Sie zusätzliche Analysen oder Grafiken hinzufügen
    else:
        st.info("Keine Preisdaten verfügbar.")
