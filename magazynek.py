import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- Konfiguracja Strony ---
st.set_page_config(page_title="Magazyn PRO", layout="wide", page_icon="📦")

# --- DANE DOSTĘPOWE ---
SUPABASE_URL = "https://ijfoshdlcpccebzgpmox.supabase.co"
SUPABASE_KEY = "sb_publishable_A1XPX9TeO-Q-rdpcujK75g_DeeUqBkf"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNKCJE BAZY DANYCH ---

def fetch_data():
    """Pobiera dane zgodnie ze schematem: Produkty, Kategorie, wydania."""
    # Kategorie i Produkty (wielkie litery)
    categories = supabase.table("Kategorie").select("*").execute().data
    products = supabase.table("Produkty").select("*, Kategorie(nazwa)").execute().data
    
    # wydania (małe litery), sortowane po data_wydania
    shipments = supabase.table("wydania").select("*, Produkty(nazwa)").order("data_wydania", desc=True).execute().data
    return categories, products, shipments

def add_category(nazwa, opis):
    """Dodaje nową kategorię do tabeli Kategorie."""
    supabase.table("Kategorie").insert({"nazwa": nazwa, "opis": opis}).execute()
    st.rerun()

def add_product(nazwa, liczba, cena, kategoria_id):
    """Dodaje produkt do tabeli Produkty."""
    supabase.table("Produkty").insert({
        "nazwa": nazwa, 
        "liczba": liczba, 
        "cena": cena, 
        "kategoria_id": kategoria_id
    }).execute()
    st.rerun()

def issue_goods(product_id, qty, recipient, current_stock):
    """Rejestruje wydanie w tabeli wydania i aktualizuje stan w Produkty."""
    if qty > current_stock:
        st.error(f"Błąd: Za mało towaru! (Dostępne: {current_stock})")
        return False
    
    new_stock = current_stock - qty
    supabase.table("Produkty").update({"liczba": new_stock}).eq("id", product_id).execute()
    
    # Zapis w tabeli wydania
    supabase.table("wydania").insert({
        "produkt_id": product_id,
        "ilosc": qty,
        "odbiorca": recipient
    }).execute()
    st.rerun()

# --- INTERFEJS UŻYTKOWNIKA ---

st.title("📦 System Magazynowy")

try:
    categories, products, shipments = fetch_data()
except Exception as e:
    st.error(f"Błąd połączenia z bazą: {e}")
    st.stop()

# Zakładki, w tym nowa do zarządzania kategoriami
tabs = st.tabs(["📋 Stan", "📤 Wydaj", "📜 Historia", "➕ Nowy Produkt", "📁 Kategorie"])

# --- ZAKŁADKA: STAN ---
with tabs[0]:
    if products:
        for p in products:
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 3, 3])
                c1.write(f"**{p['nazwa']}**")
                kat = p['Kategorie']['nazwa'] if p.get('Kategorie') else "Brak"
                c2.write(f"Kategoria: {kat}")
                c3.write(f"Stan: **{p['liczba']}** szt.")
    else:
        st.info("Brak towarów.")

# --- ZAKŁADKA: WYDAJ TOWAR ---
with tabs[1]:
    if products:
        with st.form("form_wydania"):
            options = {f"{p['nazwa']} (Stan: {p['liczba']})": p for p in products}
            sel = st.selectbox("Wybierz towar", options=list(options.keys()))
            qty = st.number_input("Ilość", min_value=1, step=1)
            rec = st.text_input("Odbiorca")
            if st.form_submit_button("Potwierdź Wydanie"):
                p_info = options[sel]
                issue_goods(p_info['id'], qty, rec, p_info['liczba'])
    else:
        st.warning("Najpierw dodaj produkty.")

# --- ZAKŁADKA: HISTORIA ---
with tabs[2]:
    if shipments:
        df_h = []
        for s in shipments:
            df_h.append({
                "Data": s['data_wydania'][:16].replace("T", " "),
                "Produkt": s['Produkty']['nazwa'] if s.get('Produkty') else "N/A",
                "Sztuk": s['ilosc'],
                "Odbiorca": s['odbiorca']
            })
        st.dataframe(df_h, use_container_width=True, hide_index=True)

# --- ZAKŁADKA: NOWY PRODUKT ---
with tabs[3]:
    if not categories:
        st.warning("Musisz najpierw dodać przynajmniej jedną kategorię w zakładce 'Kategorie'!")
    else:
        with st.form("new_product"):
            name = st.text_input("Nazwa produktu")
            # Bezpieczne mapowanie kategorii, które zapobiega KeyError
            cat_map = {c['nazwa']: c['id'] for c in categories}
            sel_cat = st.selectbox("Kategoria", options=list(cat_map.keys()))
            p_qty = st.number_input("Ilość", min_value=0)
            p_price = st.number_input("Cena", min_value=0.0)
            
            if st.form_submit_button("Dodaj Produkt"):
                if name:
                    add_product(name, p_qty, p_price, cat_map[sel_cat])
                else:
                    st.error("Podaj nazwę produktu.")

# --- ZAKŁADKA: KATEGORIE (NOWA) ---
with tabs[4]:
    st.subheader("Dodaj nową kategorię")
    with st.form("new_category"):
        c_name = st.text_input("Nazwa kategorii (np. Elektronika)")
        c_desc = st.text_area("Opis")
        if st.form_submit_button("Zapisz kategorię"):
            if c_name:
                add_category(c_name, c_desc)
                st.success(f"Dodano kategorię: {c_name}")
            else:
                st.error("Nazwa kategorii jest wymagana.")
    
    if categories:
        st.markdown("---")
        st.write("**Istniejące kategorie:**")
        st.table(pd.DataFrame(categories)[["nazwa", "opis"]])
