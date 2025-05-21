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

def speichere_tagesdaten(daten, dateipfad):
    df = pd.DataFrame(daten)
    if not df.empty:
        vorhanden = pd.read_json(dateipfad) if os.path.exists(dateipfad) else pd.DataFrame()
        aktualisiert = pd.concat([vorhanden, df])
        aktualisiert.to_json(dateipfad, orient='records', indent=2)

def lade_daten(dateipfad):
    return pd.read_json(dateipfad) if os.path.exists(dateipfad) else pd.DataFrame()

def filter_timeframe(df, days):
    if df.empty:
        return df
    cutoff_date = datetime.now() - timedelta(days=days)
    return df[df['date'] >= cutoff_date.strftime('%Y-%m-%d')]

def calculate_price_change(df, product, days):
    if df.empty:
        return None, None
    
    product_data = df[df['product'] == product].sort_values('date')
    if len(product_data) < 2:
        return None, None
    
    current_price = product_data.iloc[-1]['price']
    
    cutoff_date = datetime.now() - timedelta(days=days)
    past_data = product_data[product_data['date'] >= cutoff_date.strftime('%Y-%m-%d')]
    
    if len(past_data) == 0:
        return None, None
    
    past_price = past_data.iloc[0]['price']
    price_change = current_price - past_price
    percent_change = (price_change / past_price) * 100
    
    return price_change, percent_change

def create_price_card(product, current_price, price_change, percent_change):
    change_direction = "positive" if price_change > 0 else "negative"
    change_icon = "📈" if price_change > 0 else "📉"
    
    st.markdown(f"""
    <div class="price-card">
        <h3>{product}</h3>
        <h2>{current_price:.2f}€</h2>
        <p>{change_icon} <span class="price-change-{change_direction}">
        {price_change:+.2f}€ ({percent_change:+.2f}%)</span></p>
    </div>
    """, unsafe_allow_html=True)

def show_price_trend(df, selected_timeframe):
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Filter data based on selected timeframe
        if selected_timeframe == "1 Woche":
            df = filter_timeframe(df, 7)
        elif selected_timeframe == "1 Monat":
            df = filter_timeframe(df, 30)
        elif selected_timeframe == "1 Jahr":
            df = filter_timeframe(df, 365)

        # Initialize session state for selected products if not exists
        if 'selected_products' not in st.session_state:
            st.session_state.selected_products = df['product'].unique()[:3]
        
        ausgewählte_produkte = st.multiselect(
            "Modelle auswählen",
            options=df['product'].unique(),
            default=st.session_state.selected_products,
            key="product_selection"
        )
        
        # Update session state only if we have selected products
        if ausgewählte_produkte:
            if 'selected_products' not in st.session_state or ausgewählte_produkte != st.session_state.selected_products:
                st.session_state.selected_products = ausgewählte_produkte
                st.rerun()

        if ausgewählte_produkte:
            gefiltert = df[df['product'].isin(ausgewählte_produkte)]
            
            # Create price cards for selected products
            cols = st.columns(len(ausgewählte_produkte))
            for idx, produkt in enumerate(ausgewählte_produkte):
                pdata = gefiltert[gefiltert['product'] == produkt]
                if not pdata.empty:
                    current_price = pdata.iloc[-1]['price']
                    price_change, percent_change = calculate_price_change(pdata, produkt, 
                                                                        7 if selected_timeframe == "1 Woche" else 
                                                                        30 if selected_timeframe == "1 Monat" else 365)
                    
                    with cols[idx]:
                        if price_change is not None and percent_change is not None:
                            create_price_card(produkt, current_price, price_change, percent_change)
                        else:
                            st.markdown(f"""
                            <div class="price-card">
                                <h3>{produkt}</h3>
                                <h2>{current_price:.2f}€</h2>
                                <p>Keine Vergleichsdaten</p>
                            </div>
                            """, unsafe_allow_html=True)

            # Create interactive chart
            fig = make_subplots(specs=[[{"secondary_y": False}]])
            
            for produkt in ausgewählte_produkte:
                pdata = gefiltert[gefiltert['product'] == produkt]
                fig.add_trace(go.Scatter(
                    x=pdata['date'],
                    y=pdata['price'],
                    name=produkt,
                    mode='lines+markers',
                    line=dict(width=2),
                    marker=dict(size=8),
                    hoverinfo='text',
                    hovertext=[f"{produkt}<br>{x.date()}<br>{y:.2f}€" for x, y in zip(pdata['date'], pdata['price'])]
                ))

            fig.update_layout(
                title=f"Preisverlauf der GPUs - {selected_timeframe}",
                xaxis_title="Datum",
                yaxis_title="Preis (€)",
                hovermode="x unified",
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color=text_color),
                height=500
            )
            
            # Add range slider
            fig.update_layout(
                xaxis=dict(
                    rangeselector=dict(
                        buttons=list([
                            dict(count=7, label="1W", step="day", stepmode="backward"),
                            dict(count=1, label="1M", step="month", stepmode="backward"),
                            dict(count=6, label="6M", step="month", stepmode="backward"),
                            dict(count=1, label="1J", step="year", stepmode="backward"),
                            dict(label="Alles", step="all")
                        ])
                    ),
                    rangeslider=dict(visible=True),
                    type="date"
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Bitte wähle mindestens ein Modell aus, um den Preisverlauf anzuzeigen.")

def show_historical_prices(df):
    if not df.empty:
        ausgewähltes_produkt = st.selectbox(
            "Wähle ein Produkt aus",
            options=df['product'].unique()
        )

        historisch_df = df[df['product'] == ausgewähltes_produkt]

        if not historisch_df.empty:
            historisch_df['date'] = pd.to_datetime(historisch_df['date'])
            historisch_df = historisch_df.sort_values('date', ascending=False)
            
            # Calculate price changes
            historisch_df['price_change'] = historisch_df['price'].diff(-1)
            historisch_df['percent_change'] = (historisch_df['price_change'] / historisch_df['price'].shift(-1)) * 100
            
            # Format the display
            display_df = historisch_df[['date', 'price', 'price_change', 'percent_change']].copy()
            display_df['price'] = display_df['price'].apply(lambda x: f"{x:.2f}€")
            display_df['price_change'] = display_df['price_change'].apply(lambda x: f"{x:+.2f}€" if pd.notnull(x) else "")
            display_df['percent_change'] = display_df['percent_change'].apply(lambda x: f"{x:+.2f}%" if pd.notnull(x) else "")
            
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("Keine historischen Daten für das gewählte Produkt verfügbar.")

st.title("💻 GPU Preis-Tracker Pro")

tab1, tab2, tab3 = st.tabs(["5070 Ti", "5080", "📈 Preis-Dashboard"])

# === TAB 1: 5070 Ti Preisübersicht ===
with tab1:
    st.header("Preisübersicht für 5070 Ti")
    daten_5070ti = []
    for name, url in produkte_5070ti.items():
        preis, datum = robust_scrape(url)
        if preis is not None:
            daten_5070ti.append({'product': name, 'price': preis, 'date': datum, 'url': url})
    speichere_tagesdaten(daten_5070ti, os.path.join(DATA_DIR, "preise_5070ti.json"))
    df_5070ti = lade_daten(os.path.join(DATA_DIR, "preise_5070ti.json"))
    st.dataframe(df_5070ti[['product', 'price', 'date', 'url']], use_container_width=True)

# === TAB 2: 5080 Preisübersicht ===
with tab2:
    st.header("Preisübersicht für 5080")
    daten_5080 = []
    for name, url in produkte_5080.items():
        preis, datum = robust_scrape(url)
        if preis is not None:
            daten_5080.append({'product': name, 'price': preis, 'date': datum, 'url': url})
    speichere_tagesdaten(daten_5080, os.path.join(DATA_DIR, "preise_5080.json"))
    df_5080 = lade_daten(os.path.join(DATA_DIR, "preise_5080.json"))
    st.dataframe(df_5080[['product', 'price', 'date', 'url']], use_container_width=True)

# === TAB 3: Preis-Dashboard ===
with tab3:
    df = pd.concat([df_5070ti, df_5080], ignore_index=True)
    if not df.empty:
        # Timeframe selection
        st.subheader("Zeitraum auswählen")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("1 Woche", key="week_btn", help="Zeigt die Preisentwicklung der letzten Woche"):
                st.session_state.timeframe = "1 Woche"
        with col2:
            if st.button("1 Monat", key="month_btn", help="Zeigt die Preisentwicklung der letzten 30 Tage"):
                st.session_state.timeframe = "1 Monat"
        with col3:
            if st.button("1 Jahr", key="year_btn", help="Zeigt die Preisentwicklung der letzten 365 Tage"):
                st.session_state.timeframe = "1 Jahr"
        
        # Set default timeframe if not set
        if 'timeframe' not in st.session_state:
            st.session_state.timeframe = "1 Monat"
        
        st.markdown(f"### 📊 Preis-Dashboard - {st.session_state.timeframe}")
        
        # Schnellzugriff für GPU-Serien
        st.subheader("Schnellauswahl")
        quick_col1, quick_col2, quick_col3 = st.columns(3)
        with quick_col1:
            if st.button("Alle RTX 5070 Ti Modelle", key="all_5070"):
                st.session_state.selected_products = list(produkte_5070ti.keys())
                st.rerun()
        with quick_col2:
            if st.button("Alle RTX 5080 Modelle", key="all_5080"):
                st.session_state.selected_products = list(produkte_5080.keys())
                st.rerun()
        with quick_col3:
            if st.button("Auswahl zurücksetzen", key="reset_selection"):
                st.session_state.selected_products = []
                  st.rerun()

        # Show the price trend with the selected timeframe
        try:
            # Datenaufbereitung
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Zeitfilterung
            if st.session_state.timeframe == "1 Woche":
                df = filter_timeframe(df, 7)
            elif st.session_state.timeframe == "1 Monat":
                df = filter_timeframe(df, 30)
            elif st.session_state.timeframe == "1 Jahr":
                df = filter_timeframe(df, 365)

            # Initialisiere Session State für ausgewählte Produkte
            if 'selected_products' not in st.session_state:
                available_products = df['product'].unique()
                st.session_state.selected_products = available_products[:min(3, len(available_products))]

            # Produktauswahl mit eindeutigem Key
            ausgewählte_produkte = st.multiselect(
                "Modelle auswählen",
                options=df['product'].unique(),
                default=st.session_state.selected_products,
                key="product_multiselect_unique_key"
            )

            # Aktualisiere Session State bei Änderungen
            if 'selected_products' not in st.session_state or set(ausgewählte_produkte) != set(st.session_state.selected_products):
                st.session_state.selected_products = ausgewählte_produkte
                if st.session_state.get('auto_rerun', True):
                    st.session_state.auto_rerun = False
                    st.experimental_rerun()

            # Zeige Preiskarten und Diagramm
            if st.session_state.selected_products:
                # Preiskarten in einer scrollbaren horizontalen Anordnung
                st.markdown("""
                <style>
                    .horizontal-scroll {
                        overflow-x: auto;
                        white-space: nowrap;
                        padding-bottom: 10px;
                    }
                    .price-card-container {
                        display: inline-block;
                        margin-right: 15px;
                        vertical-align: top;
                    }
                </style>
                <div class="horizontal-scroll">
                """, unsafe_allow_html=True)
                
                # Container für die Preiskarten
                with st.container():
                    cols = st.columns(len(st.session_state.selected_products))
                    for idx, produkt in enumerate(st.session_state.selected_products):
                        pdata = df[df['product'] == produkt]
                        if not pdata.empty:
                            current_price = pdata.iloc[-1]['price']
                            days = 7 if st.session_state.timeframe == "1 Woche" else 30 if st.session_state.timeframe == "1 Monat" else 365
                            price_change, percent_change = calculate_price_change(pdata, produkt, days)
                            
                            with cols[idx]:
                                if price_change is not None and percent_change is not None:
                                    create_price_card(produkt, current_price, price_change, percent_change)
                                else:
                                    st.markdown(f"""
                                    <div class="price-card">
                                        <h3>{produkt}</h3>
                                        <h2>{current_price:.2f}€</h2>
                                        <p>Keine Vergleichsdaten</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)

                # Interaktives Diagramm
                fig = make_subplots(specs=[[{"secondary_y": False}]])
                
                for produkt in st.session_state.selected_products:
                    pdata = df[df['product'] == produkt]
                    fig.add_trace(go.Scatter(
                        x=pdata['date'],
                        y=pdata['price'],
                        name=produkt,
                        mode='lines+markers',
                        line=dict(width=2),
                        marker=dict(size=8),
                        hoverinfo='text',
                        hovertext=[f"{produkt}<br>{x.date()}<br>{y:.2f}€" for x, y in zip(pdata['date'], pdata['price'])]
                    ))

                fig.update_layout(
                    title=f"Preisverlauf der ausgewählten GPUs - {st.session_state.timeframe}",
                    xaxis_title="Datum",
                    yaxis_title="Preis (€)",
                    hovermode="x unified",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=text_color),
                    height=500
                )
                
                fig.update_layout(
                    xaxis=dict(
                        rangeselector=dict(
                            buttons=list([
                                dict(count=7, label="1W", step="day", stepmode="backward"),
                                dict(count=1, label="1M", step="month", stepmode="backward"),
                                dict(count=6, label="6M", step="month", stepmode="backward"),
                                dict(count=1, label="1J", step="year", stepmode="backward"),
                                dict(label="Alles", step="all")
                            ])
                        ),
                        rangeslider=dict(visible=True),
                        type="date"
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Bitte wähle mindestens ein Modell aus, um den Preisverlauf anzuzeigen.")

        except Exception as e:
            st.error(f"Fehler beim Anzeigen des Preisverlaufs: {str(e)}")
            st.stop()

        # Show historical prices
        with st.expander("📜 Detaillierte historische Preise anzeigen"):
            try:
                show_historical_prices(df)
            except Exception as e:
                st.error(f"Fehler beim Anzeigen der historischen Preise: {str(e)}")

        # Statistics section
        with st.expander("📊 Statistische Analyse"):
            try:
                st.subheader("Statistische Übersicht")
                
                # Basisstatistiken
                st.markdown("**Grundlegende Statistiken**")
                stats = df.groupby('product')['price'].agg(['min', 'max', 'mean', 'last', 'count'])
                stats.columns = ['Minimalpreis', 'Maximalpreis', 'Durchschnittspreis', 'Aktueller Preis', 'Anzahl Einträge']
                st.dataframe(stats.style.format("{:.2f}€"), use_container_width=True)

                # Boxplot für Preisverteilung
                st.markdown("**Preisverteilung**")
                fig_box = px.box(df, x="product", y="price", color="product", 
                                points="all", hover_data=["date"])
                st.plotly_chart(fig_box, use_container_width=True)

                # Preisänderungen der letzten 7/30 Tage
                st.markdown("**Preisänderungen**")
                change_col1, change_col2 = st.columns(2)
                with change_col1:
                    st.markdown("**Letzte 7 Tage**")
                    changes_7d = []
                    for product in df['product'].unique():
                        pdata = df[df['product'] == product]
                        change, pct_change = calculate_price_change(pdata, product, 7)
                        if change is not None:
                            changes_7d.append({
                                'Modell': product,
                                'Änderung (€)': change,
                                'Änderung (%)': pct_change
                            })
                    if changes_7d:
                        st.dataframe(pd.DataFrame(changes_7d), use_container_width=True)
                
                with change_col2:
                    st.markdown("**Letzte 30 Tage**")
                    changes_30d = []
                    for product in df['product'].unique():
                        pdata = df[df['product'] == product]
                        change, pct_change = calculate_price_change(pdata, product, 30)
                        if change is not None:
                            changes_30d.append({
                                'Modell': product,
                                'Änderung (€)': change,
                                'Änderung (%)': pct_change
                            })
                    if changes_30d:
                        st.dataframe(pd.DataFrame(changes_30d), use_container_width=True)

            except Exception as e:
                st.error(f"Fehler bei der statistischen Analyse: {str(e)}")

# === AUTOMATISCHES UPDATE ===
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.min

if (datetime.now() - st.session_state.last_update) > timedelta(hours=24):
    with st.spinner("Tägliches Update läuft..."):
        try:
            # Update 5070 Ti Daten
            auto_data_5070ti = []
            for name, url in produkte_5070ti.items():
                preis, datum = robust_scrape(url)
                if preis is not None:
                    auto_data_5070ti.append({'product': name, 'price': preis, 'date': datum, 'url': url})
                time.sleep(1)
            speichere_tagesdaten(auto_data_5070ti, os.path.join(DATA_DIR, "preise_5070ti.json"))
            
            # Update 5080 Daten
            auto_data_5080 = []
            for name, url in produkte_5080.items():
                preis, datum = robust_scrape(url)
                if preis is not None:
                    auto_data_5080.append({'product': name, 'price': preis, 'date': datum, 'url': url})
                time.sleep(1)
            speichere_tagesdaten(auto_data_5080, os.path.join(DATA_DIR, "preise_5080.json"))

            st.session_state.last_update = datetime.now()
            st.session_state.auto_rerun = True
            st.rerun()
            
        except Exception as e:
            st.error(f"Fehler beim automatischen Update: {str(e)}")
