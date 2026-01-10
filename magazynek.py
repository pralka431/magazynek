import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- Konfiguracja Strony ---
st.set_page_config(page_title="Magazyn PRO", layout="wide", page_icon="📦")

# --- DANE DOSTĘPOWE ---
SUPABASE_URL = "https://ijfoshdlcpccebzgpmox.supabase.co"
SUPABASE_KEY = "sb_publishable_A1XPX9TeO-Q-rdpcujK75g_DeeUqBkf"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNKCJE BAZY DANYCH ---

def fetch_data():
    categories = supabase.table("Kategorie").select("*").execute().data
    products = supabase.table("Produkty").select("*, Kategorie(nazwa)").execute().data
    # Pobieramy historię (tabela wydania)
    shipments = supabase.table("wydania").select("*, Produkty(nazwa)").order("data_wydania", desc=True).execute().data
    return categories, products, shipments

def add_product(nazwa, liczba, cena, kategoria_id):
    """Dodaje produkt i zapisuje to jako 'Dodanie' w historii."""
    # 1. Dodaj produkt
    res = supabase.table("Produkty").insert({
        "nazwa": nazwa, "liczba": liczba, "cena": cena, "kategoria_id": kategoria_id
    }).execute()
    
    # 2. Zapisz w historii jako dodatni ruch (odbiorca = 'DOSTAWA')
    if res.data:
        new_id = res.data[0]['id']
        supabase.table("wydania").insert({
            "produkt_id": new_id,
            "ilosc": liczba,
            "odbiorca": "NOWY PRODUKT",
            "data_wydania": datetime.now().isoformat()
        }).execute()
    st.rerun()

def update_stock(product_id, current_qty, change):
    """Aktualizuje stan i zapisuje ruch w historii."""
    new_qty = current_qty + change
    if new_qty < 0:
        st.error("Nie można zejść poniżej zera!")
        return
    
    # Aktualizacja stanu
    supabase.table("Produkty").update({"liczba": new_qty}).eq("id", product_id).execute()
    
    # Zapis ruchu w historii (dodatnia liczba = dostawa, ujemna = wydanie)
    typ_ruchu = "DOSTAWA" if change > 0 else "WYDANIE"
    supabase.table("wydania").insert({
        "produkt_id": product_id,
        "ilosc": abs(change),
        "odbiorca": typ_ruchu,
        "data_wydania": datetime.now().isoformat()
    }).execute()
    st.rerun()

# --- INTERFEJS UŻYTKOWNIKA ---

st.title("📦 System Magazynowy")

try:
    categories, products, shipments = fetch_data()
except Exception as e:
    st.error(f"Błąd połączenia: {e}")
    st.stop()

tabs = st.tabs(["📋 Stan Magazynu", "📤 Wydaj Towar", "📜 Historia Ruchu", "➕ Nowy Produkt"])

# --- ZAKŁADKA: STAN ---
with tabs[0]:
    if products:
        for p in products:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.write(f"**{p['nazwa']}**")
                kat = p['Kategorie']['nazwa'] if p.get('Kategorie') else "Brak"
                c2.write(f"Kategoria: {kat}")
                c3.write(f"Stan: **{p['liczba']}** szt.")
                if c4.button("➕ Dostawa (+1)", key=f"inc_{p['id']}"):
                    update_stock(p['id'], p['liczba'], 1)
    else:
        st.info("Magazyn jest pusty.")

# --- ZAKŁADKA: WYDAJ TOWAR ---
with tabs[1]:
    if products:
        with st.form("form_wydania", clear_on_submit=True):
            options = {f"{p['nazwa']} (Stan: {p['liczba']})": p for p in products}
            sel = st.selectbox("Wybierz towar do wydania", options=list(options.keys()))
            qty = st.number_input("Ilość do wydania", min_value=1, step=1)
            # Odbiorca usunięty z formularza zgodnie z prośbą
            
            if st.form_submit_button("Potwierdź Wydanie", type="primary"):
                p_info = options[sel]
                update_stock(p_info['id'], p_info['liczba'], -qty)
    else:
        st.warning("Brak produktów.")

# --- ZAKŁADKA: HISTORIA ---
with tabs[2]:
    st.subheader("Ostatnie operacje (Dostawy i Wydania)")
    if shipments:
        df_h = []
        for s in shipments:
            # Określamy czy to było dodanie czy wydanie na podstawie pola odbiorca
            is_delivery = s['odbiorca'] in ["DOSTAWA", "NOWY PRODUKT"]
            df_h.append({
                "Data": s['data_wydania'][:16].replace("T", " "),
                "Produkt": s['Produkty']['nazwa'] if s.get('Produkty') else "Usunięty",
                "Typ": "📥 DODANIE" if is_delivery else "📤 WYDANIE",
                "Sztuk": s['ilosc']
            })
        st.dataframe(df_h, use_container_width=True, hide_index=True)
    else:
        st.info("Brak historii ruchu.")

# --- ZAKŁADKA: NOWY PRODUKT ---
with tabs[3]:
    if not categories:
        st.warning("Najpierw dodaj kategorie w bazie danych.")
    else:
        with st.form("new_p"):
            name = st.text_input("Nazwa produktu")
            cat_map = {c['nazwa']: c['id'] for c in categories}
            sel_cat = st.selectbox("Kategoria", options=list(cat_map.keys()))
            p_qty = st.number_input("Ilość początkowa", min_value=0)
            p_price = st.number_input("Cena", min_value=0.0)
            if st.form_submit_button("Dodaj Produkt"):
                if name:
                    add_product(name, p_qty, p_price, cat_map[sel_cat])
