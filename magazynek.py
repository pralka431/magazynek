import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- Konfiguracja Strony ---
st.set_page_config(page_title="PRO Magazyn + Wydania", layout="wide", page_icon="📦")

# --- TWOJE DANE DOSTĘPOWE ---
SUPABASE_URL = "https://ijfoshdlcpccebzgpmox.supabase.co"
SUPABASE_KEY = "sb_publishable_A1XPX9TeO-Q-rdpcujK75g_DeeUqBkf"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNKCJE LOGICZNE ---

def fetch_data():
    categories = supabase.table("kategorie").select("*").execute().data
    products = supabase.table("produkty").select("*, kategorie(nazwa)").execute().data
    # Pobieramy historię wydań z nazwami produktów
    shipments = supabase.table("wydania").select("*, produkty(nazwa)").order("created_at", desc=True).execute().data
    return categories, products, shipments

def issue_goods(product_id, qty, recipient, current_stock):
    """Obsługuje wydanie towaru: aktualizuje stan i dodaje wpis do historii."""
    if qty > current_stock:
        st.error(f"Błąd: Nie masz tyle na stanie! (Dostępne: {current_stock})")
        return False
    
    try:
        # 1. Zmniejsz stan w tabeli produkty
        new_stock = current_stock - qty
        supabase.table("produkty").update({"liczba": new_stock}).eq("id", product_id).execute()
        
        # 2. Dodaj wpis do tabeli wydania
        supabase.table("wydania").insert({
            "produkt_id": product_id,
            "ilosc": qty,
            "odbiorca": recipient
        }).execute()
        
        st.success(f"Wydano {qty} szt. towaru dla: {recipient}")
        st.rerun()
    except Exception as e:
        st.error(f"Błąd podczas wydawania: {e}")

def update_quantity(product_id, new_qty):
    if new_qty >= 0:
        supabase.table("produkty").update({"liczba": new_qty}).eq("id", product_id).execute()
        st.rerun()

def add_product(nazwa, liczba, cena, kategoria_id):
    supabase.table("produkty").insert({
        "nazwa": nazwa, "liczba": liczba, "cena": cena, "kategoria_id": kategoria_id
    }).execute()
    st.rerun()

# --- INTERFEJS ---

st.title("📦 System Magazynowy z Wydawaniem")

categories, products, shipments = fetch_data()

# Zakładki
tab_stan, tab_wydaj, tab_historia, tab_dodaj = st.tabs([
    "📋 Stan Magazynu", "📤 Wydaj Towar", "📜 Historia Wydań", "➕ Nowy Produkt"
])

# --- ZAKŁADKA 1: STAN ---
with tab_stan:
    st.subheader("Aktualne zapasy")
    if products:
        for p in products:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.write(f"**{p['nazwa']}**")
                c2.write(f"Kat: {p['kategorie']['nazwa'] if p['kategorie'] else 'Brak'}")
                c3.write(f"Stan: **{p['liczba']}** szt.")
                if c4.button("➕ Szybka Dostawa", key=f"s_add_{p['id']}"):
                    update_quantity(p['id'], p['liczba'] + 1)
    else:
        st.info("Magazyn jest pusty.")

# --- ZAKŁADKA 2: WYDAWANIE ---
with tab_wydaj:
    st.subheader("Formularz wydania zewnętrznego")
    if products:
        with st.form("form_wydania", clear_on_submit=True):
            # Tworzymy mapę produktów do wyboru
            prod_map = {f"{p['nazwa']} (Dostępne: {p['liczba']})": p for p in products}
            selected_prod_label = st.selectbox("Wybierz produkt", options=list(prod_map.keys()))
            
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                w_qty = st.number_input("Ilość do wydania", min_value=1, step=1)
            with col_w2:
                w_recipient = st.text_input("Odbiorca / Cel wydania (np. Jan Kowalski, Budowa A)")
            
            if st.form_submit_button("Potwierdź Wydanie", type="primary"):
                p_data = prod_map[selected_prod_label]
                issue_goods(p_data['id'], w_qty, w_recipient, p_data['liczba'])
    else:
        st.warning("Brak produktów w bazie.")

# --- ZAKŁADKA 3: HISTORIA ---
with tab_historia:
    st.subheader("Ostatnie wydania z magazynu")
    if shipments:
        history_df = []
        for s in shipments:
            history_df.append({
                "Data": s['created_at'][:16].replace("T", " "),
                "Produkt": s['produkty']['nazwa'] if s['produkty'] else "Usunięty",
                "Ilość": s['ilosc'],
                "Odbiorca": s['odbiorca']
            })
        st.table(pd.DataFrame(history_df))
    else:
        st.info("Nie zarejestrowano jeszcze żadnych wydań.")

# --- ZAKŁADKA 4: DODAWANIE ---
with tab_dodaj:
    st.subheader("Dodaj nowy asortyment do bazy")
    with st.form("add_p"):
        f1, f2 = st.columns(2)
        with f1:
            name = st.text_input("Nazwa")
            cat_map = {c['nazwa']: c['id'] for c in categories}
            cat = st.selectbox("Kategoria", options=list(cat_map.keys()))
        with f2:
            qty = st.number_input("Ilość", min_value=0)
            price = st.number_input("Cena", min_value=0.0)
        
        if st.form_submit_button("Dodaj"):
            add_product(name, qty, price, cat_map[cat])
