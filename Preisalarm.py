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
import json
from st_aggrid import AgGrid, GridOptionsBuilder

# ========== KONFIGURATION ==========
TIMEZONE = None
DATA_DIR = "preis_daten"
os.makedirs(DATA_DIR, exist_ok=True)

# ========== DESIGN-EINSTELLUNGEN ==========
primary_color = "#4B8DFF"  # Blau statt Rot für technisches Thema
secondary_color = "#1F77B4"
bg_color = "#F0F2F6"
text_color = "#333"
font = "Helvetica Neue, sans-serif"

st.set_page_config(
    page_title="RTX 5080 Preis-Tracker Pro",
    page_icon="🖥️",
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
            border-radius: 8px;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
            border: none;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .stButton>button:hover {{
            background-color: #3A7BFF;
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        .stAlert {{
            border-left: 4px solid {primary_color};
        }}
        .stProgress > div > div > div {{
            background-color: {primary_color};
        }}
        h1, h2, h3 {{
            font-family: 'Arial', sans-serif;
            font-weight: 600;
            color: #2c3e50;
        }}
        .css-1aumxhk {{
            background-color: #FFF;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0px 2px 15px rgba(0, 0, 0, 0.08);
            margin-bottom: 20px;
        }}
        .timeframe-btn {{
            margin: 5px !important;
        }}
        .price-card {{
            background: linear-gradient(135deg, #f5f9ff 0%, #e0e9ff 100%);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            transition: all 0.3s ease;
            border-left: 4px solid {primary_color};
        }}
        .price-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
        }}
        .price-change-positive {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .price-change-negative {{
            color: #27ae60;
            font-weight: bold;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 10px;
        }}
        .stTabs [data-baseweb="tab"] {{
            padding: 10px 20px;
            border-radius: 8px 8px 0 0 !important;
            background-color: #f0f2f6 !important;
            transition: all 0.3s ease;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {primary_color} !important;
            color: white !important;
        }}
        .stDataFrame {{
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
    </style>
""", unsafe_allow_html=True)

# ========== PRODUKTLISTEN ==========
produkte_5080 = {
    "Palit GeForce RTX 5080 GamingPro V1": "https://geizhals.at/gainward-geforce-rtx-5080-phoenix-v1-5615-ne75080s19t2-gb2031c-a3491334.html",
    "Zotac GeForce RTX 5080": "https://geizhals.at/zotac-geforce-rtx-5080-v186817.html",
    "INNO3D GeForce RTX 5080 X3": "https://geizhals.at/inno3d-geforce-rtx-5080-x3-n50803-16d7-176068n-a3382794.html",
    "Gainward GeForce RTX 5080 Phoenix GS V1": "https://geizhals.at/gainward-geforce-rtx-5080-phoenix-v1-5615-ne75080s19t2-gb2031c-a3491334.html",
    "Palit GeForce RTX 5080 GamingPro": "https://geizhals.at/palit-geforce-rtx-5080-gamingpro-ne75080019t2-gb2031a-a3382521.html",
    "Manli Nebula GeForce RTX 5080": "https://geizhals.at/manli-nebula-geforce-rtx-5080-a3449904.html?hloc=eu&nocookie=1",
    "MSI GeForce RTX 5080 16G Shadow 3X OC": "https://geizhals.at/msi-geforce-rtx-5080-16g-shadow-3x-oc-v531-003r-a3448293.html",
    "Gigabyte GeForce RTX 5080 Gaming OC": "https://geizhals.at/gigabyte-geforce-rtx-5080-windforce-oc-sff-16g-gv-n5080wf3oc-16gd-a3381809.html",
}

# ========== FUNKTIONEN ==========
@st.cache_data(ttl=3600, show_spinner="Scraping Preisdaten...")
def robust_scrape(url, max_retries=3):
    """Robuste Funktion zum Scrapen von Preisdaten mit Cloudflare-Umgehung"""
    scraper = cloudscraper.create_scraper()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }

    for attempt in range(max_retries):
        try:
            res = scraper.get(url, headers=headers, timeout=15)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')

            # Verbesserte Preisermittlung
            preis_element = (
                soup.find('strong', id='pricerange-min') or
                soup.find('span', class_='price__amount') or
                soup.find('span', class_='gh_price') or
                soup.find('meta', {'itemprop': 'price'})
            )

            if preis_element:
                preis_text = preis_element.get('content') if preis_element.name == 'meta' else preis_element.get_text(strip=True)
                preis = float(''.join(c for c in preis_text if c.isdigit() or c in ',.').replace('.', '').replace(',', '.'))
                datum = datetime.now(TIMEZONE)
                
                # Zusätzliche Infos sammeln
                shop_element = soup.find('span', class_='gh_offer_shop') or soup.find('a', class_='offer__seller')
                shop = shop_element.get_text(strip=True) if shop_element else "Unbekannt"
                
                return {
                    'price': preis,
                    'date': datum,
                    'shop': shop,
                    'url': url
                }
        except Exception as e:
            print(f"Fehler bei Versuch {attempt + 1} für {url}: {e}")
            time.sleep(2 ** attempt)  # Exponentielles Backoff

    return None

def speichere_daten(daten, dateipfad):
    """Speichert Daten im JSON-Format mit Backup-System"""
    try:
        # Backup alter Daten falls vorhanden
        if os.path.exists(dateipfad):
            backup_path = f"{dateipfad}.bak"
            with open(dateipfad, 'r') as f, open(backup_path, 'w') as b:
                b.write(f.read())
        
        # Neue Daten speichern
        with open(dateipfad, 'w') as f:
            json.dump(daten, f, indent=2, default=str)
    except Exception as e:
        st.error(f"Fehler beim Speichern der Daten: {e}")

def lade_daten(dateipfad):
    """Lädt Daten aus JSON-Datei mit Fehlerbehandlung"""
    try:
        if os.path.exists(dateipfad):
            with open(dateipfad, 'r') as f:
                daten = json.load(f)
                
                # Konvertiere String-Datumsangaben zurück zu datetime-Objekten
                for eintrag in daten:
                    if 'date' in eintrag:
                        eintrag['date'] = datetime.strptime(eintrag['date'], '%Y-%m-%d %H:%M:%S.%f')
                
                return daten
        return []
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return []

def berechne_preisänderung(aktueller_preis, historische_daten, tage):
    """Berechnet Preisänderung über einen bestimmten Zeitraum"""
    if not historische_daten or len(historische_daten) < 2:
        return None, None
    
    cutoff_date = datetime.now() - timedelta(days=tage)
    historische_preise = [d['price'] for d in historische_daten if d['date'] >= cutoff_date]
    
    if not historische_preise:
        return None, None
    
    start_preis = historische_preise[0]
    änderung = aktueller_preis - start_preis
    prozent = (änderung / start_preis) * 100
    
    return änderung, prozent

def erstelle_preiskarte(name, preis, änderung, prozent, shop):
    """Erstellt eine visuelle Preiskarte mit allen relevanten Infos"""
    if änderung is not None and prozent is not None:
        änderung_text = f"{'📈' if änderung > 0 else '📉'} {änderung:+.2f}€ ({prozent:+.2f}%)"
        änderung_class = "price-change-positive" if änderung > 0 else "price-change-negative"
    else:
        änderung_text = "Keine Vergleichsdaten"
        änderung_class = ""
    
    st.markdown(f"""
    <div class="price-card">
        <h3>{name}</h3>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h2 style="margin: 0;">{preis:.2f}€</h2>
            <small style="color: #7f8c8d;">{shop}</small>
        </div>
        <p><span class="{änderung_class}">{änderung_text}</span></p>
    </div>
    """, unsafe_allow_html=True)

def erstelle_preisdiagramm(daten, ausgewählte_modelle):
    """Erstellt ein interaktives Preisdiagramm mit Plotly"""
    if not daten or not ausgewählte_modelle:
        return None
    
    fig = go.Figure()
    
    farben = px.colors.qualitative.Plotly
    farb_index = 0
    
    for produkt in ausgewählte_modelle:
        produkt_daten = [d for d in daten if d['product'] == produkt]
        if not produkt_daten:
            continue
            
        # Sortiere nach Datum
        produkt_daten.sort(key=lambda x: x['date'])
        
        datum = [d['date'] for d in produkt_daten]
        preis = [d['price'] for d in produkt_daten]
        
        fig.add_trace(go.Scatter(
            x=datum,
            y=preis,
            name=produkt,
            mode='lines+markers',
            line=dict(width=2.5, color=farben[farb_index % len(farben)]),
            marker=dict(size=8, color=farben[farb_index % len(farben)]),
            hovertemplate="<b>%{y:.2f}€</b><br>%{x|%d.%m.%Y}",
            showlegend=True
        ))
        
        farb_index += 1
    
    fig.update_layout(
        title="Preisentwicklung der RTX 5080 Modelle",
        xaxis_title="Datum",
        yaxis_title="Preis (€)",
        hovermode="x unified",
        plot_bgcolor='white',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color=text_color),
        height=500,
        margin=dict(l=50, r=50, b=50, t=80, pad=4),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Range Selector hinzufügen
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=7, label="1W", step="day", stepmode="backward"),
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(step="all", label="Alles")
            ])
        )
    )
    
    return fig

def erstelle_preisvergleichstabelle(daten):
    """Erstellt eine interaktive Tabelle mit allen Preisdaten"""
    if not daten:
        return None
    
    # Erstelle DataFrame für die Tabelle
    df = pd.DataFrame(daten)
    
    # Sortiere nach Produkt und Datum
    df = df.sort_values(['product', 'date'], ascending=[True, False])
    
    # Berechne Preisänderungen
    df['price_change'] = df.groupby('product')['price'].diff(-1)
    df['percent_change'] = (df['price_change'] / df['price'].shift(-1)) * 100
    
    # Formatierung
    df['date'] = df['date'].dt.strftime('%d.%m.%Y %H:%M')
    df['price'] = df['price'].apply(lambda x: f"{x:.2f}€")
    df['price_change'] = df['price_change'].apply(lambda x: f"{x:+.2f}€" if pd.notnull(x) else "")
    df['percent_change'] = df['percent_change'].apply(lambda x: f"{x:+.2f}%" if pd.notnull(x) else "")
    
    # AG Grid konfigurieren
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationPageSize=10)
    gb.configure_side_bar()
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=False)
    
    # Spalten konfigurieren
    gb.configure_column("product", header_name="Modell", pinned=True)
    gb.configure_column("price", header_name="Preis", type=["numericColumn","numberColumnFilter","customNumericFormat"], 
                       valueFormatter="data.price")
    gb.configure_column("date", header_name="Datum")
    gb.configure_column("shop", header_name="Shop")
    gb.configure_column("price_change", header_name="Änderung (€)", type=["numericColumn","numberColumnFilter"])
    gb.configure_column("percent_change", header_name="Änderung (%)", type=["numericColumn","numberColumnFilter"])
    
    gridOptions = gb.build()
    
    return AgGrid(
        df,
        gridOptions=gridOptions,
        enable_enterprise_modules=True,
        height=500,
        width='100%',
        theme='streamlit',
        update_mode='MODEL_CHANGED',
        fit_columns_on_grid_load=True
    )

# ========== HAUPTPROGRAMM ==========
def main():
    st.title("🖥️ RTX 5080 Preis-Tracker Pro")
    st.markdown("""
    <div style="background-color: #e8f4ff; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
        <p style="margin: 0;">📊 <strong>Echtzeit-Preise</strong> für alle RTX 5080 Modelle | 🔔 <strong>Preisalarme</strong> | 📈 <strong>Historische Analysen</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialisiere Session State mit ALLEN Produkten
    if 'selected_products' not in st.session_state:
        st.session_state.selected_products = list(produkte_5080.keys())  # Alle Modelle laden
    
    if 'timeframe' not in st.session_state:
        st.session_state.timeframe = 30  # Standard: 1 Monat
    
    # Fortschrittsbalken für Scraping
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Aktuelle Preise abrufen
    daten = []
    total_products = len(produkte_5080)
    
    for i, (name, url) in enumerate(produkte_5080.items()):
        status_text.text(f"Scrape {name}... ({i+1}/{total_products})")
        progress_bar.progress((i + 1) / total_products)
        
        produkt_daten = robust_scrape(url)
        if produkt_daten:
            produkt_daten['product'] = name
            daten.append(produkt_daten)
        
        time.sleep(1)  # Höfliches Crawling
    
    progress_bar.empty()
    status_text.empty()
    
    # Alte Daten laden und mit neuen kombinieren
    dateipfad = os.path.join(DATA_DIR, "preise_5080.json")
    alte_daten = lade_daten(dateipfad)
    
    # Prüfe auf Duplikate (gleiches Produkt, gleicher Preis, gleicher Shop, gleicher Tag)
    heute = datetime.now().date()
    neue_daten = []
    
    for eintrag in daten:
        ist_duplikat = any(
            (e['product'] == eintrag['product'] and 
             e['price'] == eintrag['price'] and 
             e['shop'] == eintrag['shop'] and 
             e['date'].date() == heute)
            for e in alte_daten
        )
        
        if not ist_duplikat:
            neue_daten.append(eintrag)
    
    if neue_daten:
        alle_daten = alte_daten + neue_daten
        speichere_daten(alle_daten, dateipfad)
        st.success(f"{len(neue_daten)} neue Preise aktualisiert!")
    else:
        alle_daten = alte_daten
        st.info("Keine neuen Preisänderungen gefunden.")
    
    # Dashboard Layout
    tab1, tab2, tab3 = st.tabs(["📊 Übersicht", "📈 Preisverlauf", "📋 Alle Daten"])
    
    with tab1:
        st.header("Aktuelle Preise & Trends")
        
        # Zeitraum-Auswahl
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("1 Woche", key="week_btn", use_container_width=True):
                st.session_state.timeframe = 7
        with col2:
            if st.button("1 Monat", key="month_btn", use_container_width=True):
                st.session_state.timeframe = 30
        with col3:
            if st.button("1 Jahr", key="year_btn", use_container_width=True):
                st.session_state.timeframe = 365
        
        # Produktauswahl - Multiselect mit allen vorausgewählten Produkten
        auswahl = st.multiselect(
            "Modelle auswählen",
            options=list(produkte_5080.keys()),
            default=st.session_state.selected_products,  # Alle vorausgewählt
            key="product_select"
        )
        
        # Automatisch alle Produkte auswählen, wenn keine spezifische Auswahl getroffen wurde
        if not auswahl:
            auswahl = list(produkte_5080.keys())
        
        st.session_state.selected_products = auswahl
        
        # Preiskarten anzeigen - in zwei Spalten für bessere Lesbarkeit
        if st.session_state.selected_products:
            # Erstelle zwei Spalten
            col1, col2 = st.columns(2)
            
            for idx, produkt in enumerate(st.session_state.selected_products):
                # Wechsle zwischen den Spalten
                current_col = col1 if idx % 2 == 0 else col2
                
                with current_col:
                    produkt_daten = [d for d in alle_daten if d['product'] == produkt]
                    if produkt_daten:
                        aktuellster_eintrag = max(produkt_daten, key=lambda x: x['date'])
                        änderung, prozent = berechne_preisänderung(
                            aktuellster_eintrag['price'],
                            produkt_daten,
                            st.session_state.timeframe
                        )
                        
                        erstelle_preiskarte(
                            produkt,
                            aktuellster_eintrag['price'],
                            änderung,
                            prozent,
                            aktuellster_eintrag['shop']
                        )
                    else:
                        st.warning(f"Keine Daten für {produkt} verfügbar")
        
        # Preisstatistiken
        st.subheader("Preisstatistiken")
        if alle_daten:
            df = pd.DataFrame(alle_daten)
            stats = df.groupby('product')['price'].agg(['min', 'max', 'mean', 'median', 'std', 'count'])
            stats.columns = ['Tiefstpreis', 'Höchstpreis', 'Durchschnitt', 'Median', 'Standardabweichung', 'Anzahl']
            st.dataframe(stats.style.format("{:.2f}€"), use_container_width=True)
    
    with tab2:
        st.header("Preisverlauf analysieren")
        
        if alle_daten and st.session_state.selected_products:
            fig = erstelle_preisdiagramm(alle_daten, st.session_state.selected_products)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            
            # Preisänderungen berechnen
            st.subheader("Preisänderungen")
            änderungen = []
            
            for produkt in st.session_state.selected_products:
                produkt_daten = [d for d in alle_daten if d['product'] == produkt]
                if len(produkt_daten) >= 2:
                    neuester = max(produkt_daten, key=lambda x: x['date'])
                    ältester = min(produkt_daten, key=lambda x: x['date'])
                    
                    änderung = neuester['price'] - ältester['price']
                    prozent = (änderung / ältester['price']) * 100
                    
                    änderungen.append({
                        'Modell': produkt,
                        'Startpreis': f"{ältester['price']:.2f}€",
                        'Aktueller Preis': f"{neuester['price']:.2f}€",
                        'Änderung (€)': f"{änderung:+.2f}€",
                        'Änderung (%)': f"{prozent:+.2f}%",
                        'Zeitraum': f"{(neuester['date'] - ältester['date']).days} Tage"
                    })
            
            if änderungen:
                st.table(pd.DataFrame(änderungen))
            else:
                st.info("Nicht genügend Daten für Preisvergleich vorhanden.")
    
    with tab3:
        st.header("Alle Preisdaten")
        if alle_daten:
            grid = erstelle_preisvergleichstabelle(alle_daten)
            
            # Datenexport
            st.download_button(
                label="Daten als CSV exportieren",
                data=pd.DataFrame(alle_daten).to_csv(index=False).encode('utf-8'),
                file_name="rtx5080_preise.csv",
                mime="text/csv"
            )
        else:
            st.warning("Noch keine Daten verfügbar.")

if __name__ == "__main__":
    main()
