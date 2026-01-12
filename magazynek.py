import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazynek Pro", layout="wide", page_icon="📦")

# --- DANE DOSTĘPOWE (BEZPIECZNE) ---
# Klucze są pobierane z pliku secrets.toml (lokalnie) lub ustawień hostingu
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except KeyError:
    st.error("Błąd: Nie znaleziono kluczy konfiguracyjnych w st.secrets!")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# --- FUNKCJE POMOCNICZE CZASU ---

def get_now_pl():
    """Pobiera aktualny czas w PL do zapisu w bazie."""
    tz = pytz.timezone('Europe/Warsaw')
    return datetime.now(tz).isoformat()

def format_date_to_pl(date_str):
    """Konwertuje dowolny format daty z bazy na czas polski do wyświetlania."""
    try:
        # Konwersja na obiekt Timestamp przez pandas (najbardziej odporne na błędy)
        dt = pd.to_datetime(date_str)
        
        # Jeśli data nie ma strefy (naive), zakładamy że przyszła z UTC
        if dt.tzinfo is None:
            dt = dt.tz_localize('UTC').tz_convert('Europe/Warsaw')
        else:
            # Jeśli ma strefę, po prostu konwertujemy na Warszawę
            dt = dt.tz_convert('Europe/Warsaw')
            
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return date_str

# --- FUNKCJE BAZY DANYCH ---

@st.cache_data(ttl=5)
def fetch_data():
    categories = supabase.table("Kategorie").select("*").execute().data
    products = supabase.table("Produkty").select("*, Kategorie(nazwa)").order("nazwa").execute().data
    shipments = supabase.table("wydania").select("*, Produkty(nazwa)").order("data_wydania", desc=True).limit(100).execute().data
    return categories, products, shipments

def add_category(nazwa, opis):
    if nazwa:
        supabase.table("Kategorie").insert({"nazwa": nazwa, "opis": opis}).execute()
        st.cache_data.clear()
        st.rerun()

def log_movement(product_id, qty, recipient):
    supabase.table("wydania").insert({
        "produkt_id": product_id,
        "ilosc": qty,
        "odbiorca": recipient,
        "data_wydania": get_now_pl()
    }).execute()

def add_product(nazwa, liczba, cena, kategoria_id):
    existing_p = supabase.table("Produkty").select("*").eq("nazwa", nazwa).execute().data
    if existing_p:
        p_id = existing_p[0]['id']
        new_qty = existing_p[0]['liczba'] + liczba
        supabase.table("Produkty").update({"liczba": new_qty, "cena": cena}).eq("id", p_id).execute()
        log_movement(p_id, liczba, "DOSTAWA (SUMOWANIE)")
    else:
        res = supabase.table("Produkty").insert({
            "nazwa": nazwa, "liczba": liczba, "cena": cena, "kategoria_id": kategoria_id
        }).execute()
        if res.data:
            log_movement(res.data[0]['id'], liczba, "NOWY PRODUKT")
    st.cache_data.clear()
    st.rerun()

def update_stock(product_id, current_qty, change, typ_operacji="DOSTAWA"):
    new_qty = current_qty + change
    if new_qty >= 0:
        supabase.table("Produkty").update({"liczba": new_qty}).eq("id", product_id).execute()
        log_movement(product_id, abs(change), typ_operacji)
        st.cache_data.clear()
        st.rerun()
    else:
        st.error("Błąd: Brak towaru!")

# --- UI ---

st.title("📦 System Magazynowy Pro")

try:
    categories, products, shipments = fetch_data()
except Exception as e:
    st.error(f"Błąd połączenia: {e}")
    st.stop()

# DASHBOARD
t_val = sum((p['cena'] or 0) * p['liczba'] for p in products)
c1, c2, c3 = st.columns(3)
c1.metric("Wartość zapasów", f"{t_val:,.2f} zł")
c2.metric("Sztuk ogółem", sum(p['liczba'] for p in products))
c3.metric("Kategorie", len(categories))

tabs = st.tabs(["📋 Stan", "📤 Wydaj", "📜 Historia", "➕ Produkt", "📁 Kategorie"])

with tabs[0]: # STAN
    if products:
        for p in products:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([4, 2, 2, 3])
                col1.write(f"**{p['nazwa']}**")
                col2.write(f"🏷️ {p['Kategorie']['nazwa'] if p.get('Kategorie') else 'Brak'}")
                col3.write(f"Stan: **{p['liczba']}**")
                with col4:
                    sub1, sub2 = st.columns([1, 1])
                    amt = sub1.number_input("Ile", 1, key=f"add_{p['id']}", label_visibility="collapsed")
                    if sub2.button("➕", key=f"btn_{p['id']}"):
                        update_stock(p['id'], p['liczba'], amt)

with tabs[1]: # WYDAWANIE
    if products:
        with st.form("wydaj_form"):
            options = {f"{p['nazwa']} (Dostępne: {p['liczba']})": p for p in products}
            sel = st.selectbox("Produkt", options.keys())
            qty = st.number_input("Ilość", 1)
            who = st.text_input("Odbiorca", "Klient")
            if st.form_submit_button("Potwierdź Wydanie"):
                p_inf = options[sel]
                update_stock(p_inf['id'], p_inf['liczba'], -qty, who)

with tabs[2]: # HISTORIA (Z POPRAWIONYM CZASEM)
    if shipments:
        hist_list = []
        for s in shipments:
            is_in = s['odbiorca'] in ["DOSTAWA", "NOWY PRODUKT", "DOSTAWA (SUMOWANIE)"]
            hist_list.append({
                "Data": format_date_to_pl(s['data_wydania']), # KONWERSJA NA CZAS PL
                "Produkt": s['Produkty']['nazwa'] if s.get('Produkty') else "N/A",
                "Typ": "📥 PRZYJĘCIE" if is_in else "📤 WYDANIE",
                "Szczegóły": s['odbiorca'],
                "Ilość": s['ilosc']
            })
        st.dataframe(hist_list, use_container_width=True, hide_index=True)

with tabs[3]: # NOWY PRODUKT
    with st.form("new_p"):
        n = st.text_input("Nazwa")
        c_map = {c['nazwa']: c['id'] for c in categories}
        cat = st.selectbox("Kategoria", c_map.keys()) if categories else st.error("Dodaj najpierw kategorie!")
        q = st.number_input("Ilość", 0)
        p = st.number_input("Cena", 0.0)
        if st.form_submit_button("Dodaj"):
            if n and categories: add_product(n, q, p, c_map[cat])

with tabs[4]: # KATEGORIE
    with st.form("cat"):
        cn = st.text_input("Nazwa kategorii")
        if st.form_submit_button("Dodaj kategorię"):
            add_category(cn, "")
    if categories: st.table(pd.DataFrame(categories)[["nazwa"]])
