import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- Konfiguracja Strony ---
st.set_page_config(page_title="PRO Magazyn", layout="wide", page_icon="📦")

# --- TWOJE DANE DOSTĘPOWE ---
SUPABASE_URL = "https://ijfoshdlcpccebzgpmox.supabase.co"
SUPABASE_KEY = "sb_publishable_A1XPX9TeO-Q-rdpcujK75g_DeeUqBkf"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNKCJE LOGICZNE (Nazwy tabel z Wielkich Liter) ---

def fetch_data():
    """Pobiera dane z tabel o nazwach: Kategorie, Produkty, Wydania."""
    # Pobieranie kategorii
    categories = supabase.table("Kategorie").select("*").execute().data
    
    # Pobieranie produktów (zwróć uwagę na Wielkie Litery w JOINie)
    products = supabase.table("Produkty").select("*, Kategorie(nazwa)").execute().data
    
    # Pobieranie historii wydań
    shipments = supabase.table("Wydania").select("*, Produkty(nazwa)").order("created_at", desc=True).execute().data
    return categories, products, shipments

def update_quantity(product_id, new_qty):
    """Aktualizuje tabelę Produkty."""
    if new_qty >= 0:
        supabase.table("Produkty").update({"liczba": new_qty}).eq("id", product_id).execute()
        st.rerun()

def issue_goods(product_id, qty, recipient, current_stock):
    """Wydaje towar i zapisuje w tabeli Wydania."""
    if qty > current_stock:
        st.error(f"Błąd: Za mało towaru! (Dostępne: {current_stock})")
        return False
    
    new_stock = current_stock - qty
    # Aktualizacja stanu
    supabase.table("Produkty").update({"liczba": new_stock}).eq("id", product_id).execute()
    # Zapis historii
    supabase.table("Wydania").insert({
        "produkt_id": product_id,
        "ilosc": qty,
        "odbiorca": recipient
    }).execute()
    
    st.success(f"Wydano {qty} szt. dla: {recipient}")
    st.rerun()

def add_product(nazwa, liczba, cena, kategoria_id):
    """Dodaje do tabeli Produkty."""
    supabase.table("Produkty").insert({
        "nazwa": nazwa, 
        "liczba": liczba, 
        "cena": cena, 
        "kategoria_id": kategoria_id
    }).execute()
    st.rerun()

# --- INTERFEJS UŻYTKOWNIKA ---

st.title("📦 System Magazynowy")

try:
    categories, products, shipments = fetch_data()
except Exception as e:
    st.error(f"Wystąpił błąd podczas pobierania danych: {e}")
    st.info("💡 Sprawdź w Supabase czy Twoje tabele na pewno nazywają się: 'Produkty', 'Kategorie' i 'Wydania' (dokładnie tak, z wielkiej litery).")
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
                # Dostęp przez wielką literę 'Kategorie'
                kat_nazwa = p['Kategorie']['nazwa'] if p.get('Kategorie') else "Brak"
                c2.write(f"Kategoria: {kat_nazwa}")
                c3.write(f"Stan: **{p['liczba']}** szt.")
                if c4.button("➕ Dostawa", key=f"add_{p['id']}"):
                    update_quantity(p['id'], p['liczba'] + 1)
    else:
        st.info("Brak towarów.")

# --- ZAKŁADKA 2: WYDAWANIE ---
with tab_wydaj:
    if products:
        with st.form("form_wydania"):
            options = {f"{p['nazwa']} (Stan: {p['liczba']})": p for p in products}
            sel_label = st.selectbox("Wybierz towar", options=list(options.keys()))
            qty = st.number_input("Ile sztuk", min_value=1)
            rec = st.text_input("Kto odbiera?")
            
            if st.form_submit_button("Zatwierdź"):
                p_info = options[sel_label]
                issue_goods(p_info['id'], qty, rec, p_info['liczba'])

# --- ZAKŁADKA 3: HISTORIA ---
with tab_historia:
    if shipments:
        df_hist = []
        for s in shipments:
            df_hist.append({
                "Data": s['created_at'][:16].replace("T", " "),
                "Produkt": s['Produkty']['nazwa'] if s.get('Produkty') else "N/A",
                "Sztuk": s['ilosc'],
                "Odbiorca": s['odbiorca']
            })
        st.table(df_hist)

# --- ZAKŁADKA 4: NOWY PRODUKT ---
with tab_dodaj:
    with st.form("new_p"):
        name = st.text_input("Nazwa")
        cat_map = {c['nazwa']: c['id'] for c in categories}
        cat = st.selectbox("Kategoria", options=list(cat_map.keys()))
        qty = st.number_input("Ilość", min_value=0)
        price = st.number_input("Cena")
        if st.form_submit_button("Dodaj"):
            add_product(name, qty, price, cat_map[cat])
