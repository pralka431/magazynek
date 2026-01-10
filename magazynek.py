import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- Konfiguracja Strony ---
st.set_page_config(page_title="PRO Magazyn", layout="wide", page_icon="📦")

# --- DANE DOSTĘPOWE ---
SUPABASE_URL = "https://ijfoshdlcpccebzgpmox.supabase.co"
SUPABASE_KEY = "sb_publishable_A1XPX9TeO-Q-rdpcujK75g_DeeUqBkf"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNKCJE LOGICZNE (Zgodne z Twoim schematem bazy) ---

def fetch_data():
    """Pobiera dane z tabel: Kategorie, Produkty, wydania."""
    # Kategorie i Produkty z wielkiej litery
    categories = supabase.table("Kategorie").select("*").execute().data
    products = supabase.table("Produkty").select("*, Kategorie(nazwa)").execute().data
    
    # wydania z małej litery, sortowanie po data_wydania
    shipments = supabase.table("wydania").select("*, Produkty(nazwa)").order("data_wydania", desc=True).execute().data
    return categories, products, shipments

def update_quantity(product_id, new_qty):
    if new_qty >= 0:
        supabase.table("Produkty").update({"liczba": new_qty}).eq("id", product_id).execute()
        st.rerun()

def issue_goods(product_id, qty, recipient, current_stock):
    """Wydaje towar i zapisuje w tabeli wydania."""
    if qty > current_stock:
        st.error(f"Błąd: Za mało towaru! (Dostępne: {current_stock})")
        return False
    
    new_stock = current_stock - qty
    # Aktualizacja stanu w Produkty
    supabase.table("Produkty").update({"liczba": new_stock}).eq("id", product_id).execute()
    
    # Zapis w wydania (kolumny: produkt_id, ilosc, odbiorca)
    supabase.table("wydania").insert({
        "produkt_id": product_id,
        "ilosc": qty,
        "odbiorca": recipient
    }).execute()
    
    st.success(f"Wydano {qty} szt. dla: {recipient}")
    st.rerun()

def add_product(nazwa, liczba, cena, kategoria_id):
    supabase.table("Produkty").insert({
        "nazwa": nazwa, 
        "liczba": liczba, 
        "cena": cena, 
        "kategoria_id": kategoria_id
    }).execute()
    st.rerun()

# --- INTERFEJS UŻYTKOWNIKA ---

st.title("📦 System Magazynowy z Wydawaniem")

try:
    categories, products, shipments = fetch_data()
except Exception as e:
    st.error(f"Błąd API: {e}")
    st.stop()

# Zakładki
tab_stan, tab_wydaj, tab_historia, tab_dodaj = st.tabs([
    "📋 Stan Magazynu", "📤 Wydaj Towar", "📜 Historia Wydań", "➕ Nowy Produkt"
])

# --- ZAKŁADKA 1: STAN ---
with tab_stan:
    if products:
        for p in products:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.write(f"**{p['nazwa']}**")
                kat_nazwa = p['Kategorie']['nazwa'] if p.get('Kategorie') else "Brak"
                c2.write(f"Kategoria: {kat_nazwa}")
                c3.write(f"Stan: **{p['liczba']}** szt.")
                if c4.button("➕ Dostawa", key=f"add_{p['id']}"):
                    update_quantity(p['id'], p['liczba'] + 1)
    else:
        st.info("Brak towarów w tabeli Produkty.")

# --- ZAKŁADKA 2: WYDAWANIE ---
with tab_wydaj:
    if products:
        with st.form("form_wydania", clear_on_submit=True):
            options = {f"{p['nazwa']} (Stan: {p['liczba']})": p for p in products}
            sel_label = st.selectbox("Wybierz towar do wydania", options=list(options.keys()))
            qty = st.number_input("Ilość sztuk", min_value=1, step=1)
            rec = st.text_input("Odbiorca (kto pobiera towar)")
            
            if st.form_submit_button("Zatwierdź Wydanie", type="primary"):
                p_info = options[sel_label]
                issue_goods(p_info['id'], qty, rec, p_info['liczba'])
    else:
        st.warning("Najpierw dodaj produkty do magazynu.")

# --- ZAKŁADKA 3: HISTORIA ---
with tab_historia:
    if shipments:
        df_hist = []
        for s in shipments:
            df_hist.append({
                "Data": s['data_wydania'][:16].replace("T", " "), # Użycie data_wydania
                "Produkt": s['Produkty']['nazwa'] if s.get('Produkty') else "N/A",
                "Sztuk": s['ilosc'],
                "Odbiorca": s['odbiorca']
            })
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
    else:
        st.info("Nie zarejestrowano jeszcze żadnych wydań w tabeli wydania.")

# --- ZAKŁADKA 4: NOWY PRODUKT ---
with tab_dodaj:
    st.subheader("Dodaj nowy asortyment")
    with st.form("new_p", clear_on_submit=True):
        name = st.text_input("Nazwa produktu")
        cat_map = {c['nazwa']: c['id'] for c in categories}
        cat = st.selectbox("Kategoria", options=list(cat_map.keys()))
        qty_in = st.number_input("Początkowa ilość", min_value=0, step=1)
        price_in = st.number_input("Cena (numeric)", min_value=0.0)
        
        if st.form_submit_button("Dodaj do Magazynu"):
            if name:
                add_product(name, qty_in, price_in, cat_map[cat])
                st.success(f"Dodano produkt: {name}")
            else:
                st.error("Musisz podać nazwę!")
