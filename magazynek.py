import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- Konfiguracja Strony ---
st.set_page_config(page_title="PRO Magazyn", layout="wide", page_icon="📦")

# --- TWOJE DANE DOSTĘPOWE ---
SUPABASE_URL = "https://ijfoshdlcpccebzgpmox.supabase.co"
SUPABASE_KEY = "sb_publishable_A1XPX9TeO-Q-rdpcujK75g_DeeUqBkf"

# Inicjalizacja klienta
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Błąd połączenia: {e}")

# --- FUNKCJE LOGICZNE (Baza Danych) ---

def fetch_data():
    """Pobiera kategorie i produkty w jednym kroku."""
    categories = supabase.table("Kategorie").select("*").execute().data
    products = supabase.table("Produkty").select("*, Kategorie(nazwa)").execute().data
    return categories, products

def update_quantity(product_id, new_qty):
    """Szybka aktualizacja ilości towaru."""
    if new_qty >= 0:
        supabase.table("Produkty").update({"liczba": new_qty}).eq("id", product_id).execute()
        st.rerun()

def add_product(nazwa, liczba, cena, kategoria_id):
    """Dodaje nowy towar."""
    data = {
        "nazwa": nazwa,
        "liczba": int(liczba),
        "cena": float(cena),
        "kategoria_id": kategoria_id
    }
    supabase.table("Produkty").insert(data).execute()
    st.rerun()

def delete_product(product_id):
    """Usuwa produkt z bazy."""
    supabase.table("Produkty").delete().eq("id", product_id).execute()
    st.rerun()

# --- INTERFEJS UŻYTKOWNIKA ---

st.title("📦 System Zarządzania Magazynem")

# Pobranie aktualnych danych
try:
    categories, products = fetch_data()
except:
    st.error("Problem z pobraniem danych. Sprawdź czy tabele 'Produkty' i 'Kategorie' istnieją.")
    st.stop()

# --- 1. DASHBOARD (STATYSTYKI) ---
if products:
    st.markdown("### Podsumowanie")
    total_items = sum(p['liczba'] for p in products)
    total_value = sum(p['liczba'] * p['cena'] for p in products)
    low_stock = len([p for p in products if p['liczba'] < 5])

    m1, m2, m3 = st.columns(3)
    m1.metric("Wszystkich sztuk", total_items)
    m2.metric("Łączna wartość", f"{total_value:,.2f} zł")
    m3.metric("Niskie stany (<5 szt.)", low_stock, delta_color="inverse")
st.markdown("---")

# --- 2. WYSZUKIWARKA I FILTRY ---
col_search, col_filter = st.columns([2, 1])
with col_search:
    search_query = st.text_input("🔍 Szukaj produktu...", "").lower()
with col_filter:
    cat_names = ["Wszystkie"] + [c['nazwa'] for c in categories]
    selected_cat = st.selectbox("📁 Kategoria", options=cat_names)

# Logika filtrowania
filtered_products = [
    p for p in products 
    if search_query in p['nazwa'].lower() and 
    (selected_cat == "Wszystkie" or (p['Kategorie'] and p['Kategorie']['nazwa'] == selected_cat))
]

# --- 3. ZAKŁADKI: LISTA I DODAWANIE ---
tab_list, tab_add = st.tabs(["📋 Stan Magazynu", "➕ Dodaj Nowy Towar"])

with tab_list:
    if not filtered_products:
        st.info("Nie znaleziono produktów.")
    else:
        # Nagłówki "tabeli"
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([3, 2, 2, 3, 1])
        h_col1.write("**Nazwa**")
        h_col2.write("**Kategoria**")
        h_col3.write("**Cena**")
        h_col4.write("**Zmień Ilość**")
        h_col5.write("**Akcja**")
        
        for p in filtered_products:
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 3, 1])
                
                c1.write(f"**{p['nazwa']}**")
                c2.write(p['Kategorie']['nazwa'] if p['Kategorie'] else "Brak")
                c3.write(f"{p['cena']:.2f} zł")
                
                # Panel sterowania ilością (+ / -)
                with c4:
                    q1, q2, q3 = st.columns([1, 2, 1])
                    if q1.button("➖", key=f"sub_{p['id']}"):
                        update_quantity(p['id'], p['liczba'] - 1)
                    q2.markdown(f"<h4 style='text-align: center; margin: 0;'>{p['liczba']}</h4>", unsafe_allow_html=True)
                    if q3.button("➕", key=f"add_{p['id']}"):
                        update_quantity(p['id'], p['liczba'] + 1)
                
                if c5.button("🗑️", key=f"del_{p['id']}", help="Usuń produkt"):
                    delete_product(p['id'])

with tab_add:
    st.subheader("Nowa dostawa / Nowy produkt")
    with st.form("add_new_form", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            new_n = st.text_input("Nazwa towaru")
            cat_map = {c['nazwa']: c['id'] for c in categories}
            new_c = st.selectbox("Kategoria", options=list(cat_map.keys()))
        with col_f2:
            new_q = st.number_input("Ilość początkowa", min_value=0, value=1)
            new_p = st.number_input("Cena (zł)", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("Dodaj do bazy danych", type="primary"):
            if new_n:
                add_product(new_n, new_q, new_p, cat_map[new_c])
                st.success(f"Dodano: {new_n}")
            else:
                st.error("Nazwa produktu jest wymagana!")
