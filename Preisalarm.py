# ... (Design-Einstellungen und Imports bleiben gleich)

# ========== PRODUKTLISTE ==========
produkte_5070ti = {
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
