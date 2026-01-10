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
    # Pobieranie Kategorii, Produktów i wydań
    categories = supabase.table("Kategorie").select("*").execute().data
    products = supabase.table("Produkty").select("*, Kategorie(nazwa)").execute().data
    shipments = supabase.table("wydania").select("*, Produkty(nazwa)").order("data_wydania", desc=True).execute().data
    return categories, products, shipments

def add_category(nazwa, opis):
    """Dodaje nową kategorię do tabeli Kategorie"""
    supabase.table("Kategorie").insert({"nazwa": nazwa, "opis": opis}).execute()
    st.rerun()

def add_product(nazwa, liczba, cena, kategoria_id):
    """Inteligentne dodawanie: sumuje jeśli nazwa istnieje, tworzy jeśli nie."""
    existing_p = supabase.table("Produkty").select("*").eq("nazwa", nazwa).execute().data
    
    if existing_p:
        # SUMOWANIE
        p_id = existing_p[0]['id']
        new_qty = existing_p[0]['liczba'] + liczba
        supabase.table("Produkty").update({"liczba": new_qty, "cena": cena}).eq("id", p_id).execute()
        
        supabase.table("wydania").insert({
            "produkt_id": p_id, "ilosc": liczba, "odbiorca": "DOSTAWA (SUMOWANIE)", "data_wydania": datetime.now().isoformat()
        }).execute()
    else:
        # NOWY TOWAR
        res = supabase.table("Produkty").insert({
            "nazwa": nazwa, "liczba": liczba, "cena": cena, "kategoria_id": kategoria_id
        }).execute()
        if res.data:
            supabase.table("wydania").insert({
                "produkt_id": res.data[0]['id'], "ilosc": liczba, "odbiorca": "NOWY PRODUKT", "data_wydania": datetime.now().isoformat()
            }).execute()
    st.rerun()

def update_stock(product_id, current_qty, change, typ_operacji="DOSTAWA"):
    new_qty = current_qty + change
    if new_qty >= 0:
        supabase.table("Produkty").update({"liczba": new_qty}).eq("id", product_id).execute()
        supabase.table("wydania").insert({
            "produkt_id": product_id, "ilosc": abs(change), "odbiorca": typ_operacji, "data_wydania": datetime.now().isoformat()
        }).execute()
        st.rerun()

# --- INTERFEJS UŻYTKOWNIKA ---

st.title("📦 System Magazynowy")

try:
    categories, products, shipments = fetch_data()
except Exception as e:
    st.error(f"Błąd: {e}")
    st.stop()

tabs = st.tabs(["📋 Stan Magazynu", "📤 Wydaj Towar", "📜 Historia Ruchu", "➕ Nowy Produkt", "📁 Kategorie"])

# --- ZAKŁADKA 1: STAN (Z CENAMI) ---
with tabs[0]:
    if products:
        h1, h2, h3, h4, h5 = st.columns([3, 2, 2, 2, 3])
        h1.write("**Nazwa**")
        h2.write("**Kategoria**")
        h3.write("**Cena jedn.**")
        h4.write("**Wartość zapasu**")
        h5.write("**Szybka Dostawa**")
        
        for p in products:
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 3])
                c1.write(f"**{p['nazwa']}**")
                kat = p['Kategorie']['nazwa'] if p.get('Kategorie') else "Brak"
                c2.write(kat)
                cena = float(p['cena']) if p.get('cena') else 0.0 #
                c3.write(f"{cena:.2f} zł")
                c4.write(f"**{cena * p['liczba']:.2f} zł**")
                
                with c5:
                    sub_c1, sub_c2 = st.columns([1, 1])
                    amt = sub_c1.number_input("Ilość", min_value=1, key=f"in_{p['id']}", label_visibility="collapsed")
                    if sub_c2.button("➕ Dodaj", key=f"btn_{p['id']}"):
                        update_stock(p['id'], p['liczba'], amt)
                st.caption(f"Stan: {p['liczba']} szt.")
    else:
        st.info("Magazyn jest pusty.")

# --- ZAKŁADKA 2: WYDAWANIE ---
with tabs[1]:
    if products:
        with st.form("form_wydania", clear_on_submit=True):
            options = {f"{p['nazwa']} (Stan: {p['liczba']})": p for p in products}
            sel = st.selectbox("Wybierz towar", options=list(options.keys()))
            qty = st.number_input("Ilość", min_value=1, step=1)
            if st.form_submit_button("Potwierdź Wydanie"):
                p_info = options[sel]
                update_stock(p_info['id'], p_info['liczba'], -qty, "WYDANIE")

# --- ZAKŁADKA 3: HISTORIA ---
with tabs[2]:
    if shipments:
        df_h = []
        for s in shipments:
            is_deliv = s['odbiorca'] in ["DOSTAWA", "NOWY PRODUKT", "DOSTAWA (SUMOWANIE)"]
            df_h.append({
                "Data": s['data_wydania'][:16].replace("T", " "), #
                "Produkt": s['Produkty']['nazwa'] if s.get('Produkty') else "N/A",
                "Typ": "📥 DODANIE" if is_deliv else "📤 WYDANIE",
                "Sztuk": s['ilosc']
            })
        st.dataframe(df_h, use_container_width=True, hide_index=True)

# --- ZAKŁADKA 4: NOWY PRODUKT ---
with tabs[3]:
    if not categories:
        st.warning("Najpierw dodaj kategorię w zakładce 'Kategorie'!")
    else:
        with st.form("new_p"):
            name = st.text_input("Nazwa produktu")
            cat_map = {c['nazwa']: c['id'] for c in categories}
            sel_cat = st.selectbox("Kategoria", options=list(cat_map.keys()))
            p_qty = st.number_input("Ilość", min_value=0)
            p_price = st.number_input("Cena", min_value=0.0)
            if st.form_submit_button("Dodaj/Sumuj Produkt"):
                if name:
                    add_product(name, p_qty, p_price, cat_map[sel_cat])

# --- ZAKŁADKA 5: KATEGORIE ---
with tabs[4]:
    st.subheader("Zarządzanie Kategoriami")
    with st.form("new_cat"):
        c_name = st.text_input("Nazwa nowej kategorii")
        c_desc = st.text_area("Opis kategorii")
        if st.form_submit_button("Zapisz"):
            if c_name:
                add_category(c_name, c_desc)
    
    if categories:
        st.write("**Lista kategorii:**")
        st.table(pd.DataFrame(categories)[["nazwa", "opis"]])
