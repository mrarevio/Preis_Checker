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
}

produkte_5080 = {
    "Palit GeForce RTX 5080 GamingPro V1": "https://geizhals.at/palit-geforce-rtx-5080-gamingpro-v1-ne75080019t2-gb2031y-a3487808.html",
    "Zotac GeForce RTX 5080": "https://geizhals.at/zotac-geforce-rtx-5080-v186817.html",
    "INNO3D GeForce RTX 5080 X3": "https://geizhals.at/inno3d-geforce-rtx-5080-x3-n50803-16d7-176068n-a3382794.html",
    "Gainward GeForce RTX 5080 Phoenix GS V1,": "https://geizhals.at/gainward-geforce-rtx-5080-phoenix-v1-5615-ne75080s19t2-gb2031c-a3491334.html",
    "Palit GeForce RTX 5080 GamingPro,": "https://geizhals.at/palit-geforce-rtx-5080-gamingpro-ne75080019t2-gb2031a-a3382521.html",
}

def clean_data(df):
    # Standardisieren Sie Produktnamen
    name_mapping = {
        **{k: k for k in produkte_5070ti.keys()},
        **{k: k for k in produkte_5080.keys()}
    }

    if 'product' in df.columns:
        df['product'] = df['product'].replace(name_mapping)
    
    # Sicherstellen, dass der Preis numerisch ist
    if 'price' in df.columns:
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
    
    # Duplikate entfernen
    df = df.drop_duplicates(subset=['product', 'date', 'price'], keep='last')
    
    return df

# ========== FUNKTIONEN ==========
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

            # Für Geizhals
            preis_element = (
                soup.find('strong', id='pricerange-min') or
                soup.find('span', class_='price') or
                soup.find('div', class_='gh_price')
            )
            
            # Für Idealo
            if not preis_element:
                preis_element = soup.find('div', {'class': 'offerList-item-price'})
                if preis_element:
                    preis_text = preis_element.get_text(strip=True)
                    preis = float(''.join(c for c in preis_text if c.isdigit() or c in ',.').replace('.', '').replace(',', '.'))
                    datum = datetime.now(TIMEZONE)
                    return preis, datum

            if preis_element:
                preis_text = preis_element.get_text(strip=True)
                preis = float(''.join(c for c in preis_text if c.isdigit() or c in ',.').replace('.', '').replace(',', '.'))
                datum = datetime.now(TIMEZONE)
                return preis, datum
        except Exception as e:
            print(f"Fehler bei Versuch {attempt + 1}: {e}")
            time.sleep(2 ** attempt)
    return None, None

def speichere_tagesdaten(daten):
    heute = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    datei = os.path.join(DATA_DIR, f"preise_{heute}.json")
    
    # Konvertiere die eingehenden Daten zu DataFrame und bereinige sie
    df = pd.DataFrame(daten)
    df = clean_data(df)
    
    vorhanden = pd.read_json(datei) if os.path.exists(datei) else pd.DataFrame()
    vorhanden = clean_data(vorhanden)
    
    aktualisiert = pd.concat([vorhanden, df])
    aktualisiert.to_json(datei, orient='records', indent=2)

def lade_alle_daten():
    alle_daten = []
    for datei in os.listdir(DATA_DIR):
        if datei.startswith("preise_") and datei.endswith(".json"):
            try:
                df = pd.read_json(os.path.join(DATA_DIR, datei))
                df = clean_data(df)
                alle_daten.append(df)
            except:
                continue
    return pd.concat(alle_daten, ignore_index=True) if alle_daten else pd.DataFrame()

# Funktion zum Anzeigen des Preisverlaufs
def show_price_trend(df, title="📈 Preisverlauf"):
    st.subheader(title)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        ausgewählte_produkte = st.multiselect(
            "Modelle auswählen",
            options=df['product'].unique(),
            default=df['product'].unique()[:3],
            key=f"multiselect_{title}"
        )

        if ausgewählte_produkte:
            gefiltert = df[df['product'].isin(ausgewählte_produkte)]
            fig = make_subplots(specs=[[{"secondary_y": False}]])

            for produkt in ausgewählte_produkte:
                pdata = gefiltert[gefiltert['product'] == produkt]
                fig.add_trace(go.Scatter(
                    x=pdata['date'],
                    y=pdata['price'],
                    name=produkt,
                    mode='lines+markers',
                    line=dict(width=2),
                    marker=dict(size=8)
                ))

            fig.update_layout(
                title=f"Preisverlauf der {title} GPUs",
                xaxis_title="Datum",
                yaxis_title="Preis (€)",
                hovermode="x unified",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color=text_color)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Bitte wähle mindestens ein Modell aus, um den Preisverlauf anzuzeigen.")

# Funktion zum Anzeigen historischer Preise
def show_historical_prices(df, title="📜 Historische Preise"):
    st.subheader(title)
    if not df.empty:
        ausgewähltes_produkt = st.selectbox(
            "Wähle ein Produkt aus",
            options=df['product'].unique(),
            key=f"selectbox_{title}"
        )

        historisch_df = df[df['product'] == ausgewähltes_produkt]

        if not historisch_df.empty:
            historisch_df['date'] = pd.to_datetime(historisch_df['date'])
            historisch_df = historisch_df.sort_values('date')
            st.dataframe(historisch_df[['date', 'price']], use_container_width=True)
        else:
            st.info("Keine historischen Daten für das gewählte Produkt verfügbar.")

# ========== DASHBOARD ==========
st.title("💻 GPU Preis-Tracker Pro")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Übersicht", "⚙️ Einstellungen", "📈 RTX 5070 Ti", "📈 RTX 5080"])

# === TAB 1: Übersicht ===
with tab1:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("🔔 Aktive Preisalarme")
        if 'alarm_price' in st.session_state:
            df = lade_alle_daten()
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                aktuell = df.sort_values('date', ascending=False).drop_duplicates('product')
                alarme = aktuell[aktuell['price'] <= st.session_state.alarm_price]
                if not alarme.empty:
                    for _, row in alarme.iterrows():
                        st.warning(f"**{row['product']}** für {row['price']:.2f} €")
                        st.markdown(f"[🔗 Produktlink]({row['url']})")
                else:
                    st.success("Keine aktiven Preisalarme")
            else:
                st.info("Noch keine Daten verfügbar")

        st.subheader("🔄 Schnellaktionen")
        if st.button("Alle Preise jetzt aktualisieren"):
            with st.spinner("Preise werden aktualisiert..."):
                daten = []
                fortschritt = st.progress(0)
                # 5070 Ti Modelle
                for i, (name, url) in enumerate(produkte_5070ti.items()):
                    preis, datum = robust_scrape(url)
                    if preis:
                        daten.append({'product': name, 'price': preis, 'date': datum, 'url': url})
                    fortschritt.progress((i + 1) / (len(produkte_5070ti) + len(produkte_5080)))
                    time.sleep(1)
                # 5080 Modelle
                for i, (name, url) in enumerate(produkte_5080.items(), start=len(produkte_5070ti)):
                    preis, datum = robust_scrape(url)
                    if preis:
                        daten.append({'product': name, 'price': preis, 'date': datum, 'url': url})
                    fortschritt.progress((i + 1) / (len(produkte_5070ti) + len(produkte_5080)))
                    time.sleep(1)
                if daten:
                    speichere_tagesdaten(daten)
                    st.success(f"{len(daten)} Preise aktualisiert!")
                    st.rerun()

    with col2:
        df = lade_alle_daten()
        if not df.empty:
            show_price_trend(df, "📈 Preisverlauf aller GPUs")

# === TAB 2: Einstellungen ===
with tab2:
    with st.form("einstellungen_formular"):
        alarm_price = st.number_input("Preisalarm setzen (€)", min_value=100, value=700, step=10)
        email = st.text_input("Benachrichtigungs-E-Mail")
        smtp_server = st.text_input("SMTP-Server", "smtp.gmail.com")
        smtp_port = st.number_input("Port", 465)
        smtp_user = st.text_input("Benutzername")
        smtp_pass = st.text_input("Passwort", type="password")

        if st.form_submit_button("💾 Einstellungen speichern"):
            st.session_state.alarm_price = alarm_price
            st.session_state.email = email
            st.session_state.smtp = {
                "server": smtp_server,
                "port": smtp_port,
                "user": smtp_user,
                "password": smtp_pass
            }
            st.success("Einstellungen gespeichert!")

# === TAB 3: RTX 5070 Ti ===
with tab3:
    df = lade_alle_daten()
    df_5070ti = df[df['product'].isin(produkte_5070ti.keys())]
    
    if st.button("RTX 5070 Ti Preise aktualisieren"):
        with st.spinner("RTX 5070 Ti Preise werden aktualisiert..."):
            daten = []
            fortschritt = st.progress(0)
            for i, (name, url) in enumerate(produkte_5070ti.items()):
                preis, datum = robust_scrape(url)
                if preis:
                    daten.append({'product': name, 'price': preis, 'date': datum, 'url': url})
                fortschritt.progress((i + 1) / len(produkte_5070ti))
                time.sleep(1)
            if daten:
                speichere_tagesdaten(daten)
                st.success(f"{len(daten)} RTX 5070 Ti Preise aktualisiert!")
                st.rerun()
    
    if not df_5070ti.empty:
        show_price_trend(df_5070ti, "📈 RTX 5070 Ti Preisverlauf")
        show_historical_prices(df_5070ti, "📜 RTX 5070 Ti Historische Preise")
        
        st.subheader("📊 RTX 5070 Ti Analyse")
        df_5070ti['date'] = pd.to_datetime(df_5070ti['date'])
        st.dataframe(df_5070ti.sort_values('date', ascending=False), use_container_width=True)

        st.subheader("Statistik")
        stats = df_5070ti.groupby('product')['price'].agg(['min', 'max', 'mean', 'last'])
        st.dataframe(stats.style.format("{:.2f}€"), use_container_width=True)

        fig = px.box(df_5070ti, x="product", y="price", color="product")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine Daten für RTX 5070 Ti verfügbar")

# === TAB 4: RTX 5080 ===
with tab4:
    df = lade_alle_daten()
    df_5080 = df[df['product'].isin(produkte_5080.keys())]
    
    if st.button("RTX 5080 Preise aktualisieren"):
        with st.spinner("RTX 5080 Preise werden aktualisiert..."):
            daten = []
            fortschritt = st.progress(0)
            for i, (name, url) in enumerate(produkte_5080.items()):
                preis, datum = robust_scrape(url)
                if preis:
                    daten.append({'product': name, 'price': preis, 'date': datum, 'url': url})
                fortschritt.progress((i + 1) / len(produkte_5080))
                time.sleep(1)
            if daten:
                speichere_tagesdaten(daten)
                st.success(f"{len(daten)} RTX 5080 Preise aktualisiert!")
                st.rerun()
    
    if not df_5080.empty:
        show_price_trend(df_5080, "📈 RTX 5080 Preisverlauf")
        show_historical_prices(df_5080, "📜 RTX 5080 Historische Preise")
        
        st.subheader("📊 RTX 5080 Analyse")
        df_5080['date'] = pd.to_datetime(df_5080['date'])
        st.dataframe(df_5080.sort_values('date', ascending=False), use_container_width=True)

        st.subheader("Statistik")
        stats = df_5080.groupby('product')['price'].agg(['min', 'max', 'mean', 'last'])
        st.dataframe(stats.style.format("{:.2f}€"), use_container_width=True)

        fig = px.box(df_5080, x="product", y="price", color="product")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine Daten für RTX 5080 verfügbar")

# === AUTOMATISCHES UPDATE ===
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.min

if (datetime.now() - st.session_state.last_update) > timedelta(hours=24):
    with st.spinner("Tägliches Update läuft..."):
        auto_data = []
        # 5070 Ti Modelle
        for name, url in produkte_5070ti.items():
            preis, datum = robust_scrape(url)
            if preis:
                auto_data.append({'product': name, 'price': preis, 'date': datum, 'url': url})
                time.sleep(1)
        # 5080 Modelle
        for name, url in produkte_5080.items():
            preis, datum = robust_scrape(url)
            if preis:
                auto_data.append({'product': name, 'price': preis, 'date': datum, 'url': url})
                time.sleep(1)
        if auto_data:
            speichere_tagesdaten(auto_data)
            st.session_state.last_update = datetime.now()
            st.rerun()
