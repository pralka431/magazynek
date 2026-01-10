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
    shipments = supabase.table("wydania").select("*, Produkty(nazwa)").order("data_wydania", desc=True).execute().data
    return categories, products, shipments

def add_product(nazwa, liczba, cena, kategoria_id):
    """Sprawdza czy produkt istnieje. Jeśli tak - sumuje ilość. Jeśli nie - tworzy nowy."""
    # 1. Sprawdź, czy produkt o tej nazwie już istnieje
    existing_p = supabase.table("Produkty").select("*").eq("nazwa", nazwa).execute().data
    
    if existing_p:
        # PRODUKT ISTNIEJE -> SUMUJEMY
        p_id = existing_p[0]['id']
        old_qty = existing_p[0]['liczba']
        new_qty = old_qty + liczba
        
        # Aktualizujemy ilość (możesz też opcjonalnie zaktualizować cenę na nową)
        supabase.table("Produkty").update({"liczba": new_qty, "cena": cena}).eq("id", p_id).execute()
        
        # Zapisujemy w historii jako DOSTAWA do istniejącego towaru
        supabase.table("wydania").insert({
            "produkt_id": p_id,
            "ilosc": liczba,
            "odbiorca": "DOSTAWA (IDENTYCZNA NAZWA)",
            "data_wydania": datetime.now().isoformat()
        }).execute()
        st.success(f"Produkt '{nazwa}' już istniał. Zsumowano ilości. Nowy stan: {new_qty}")
    else:
        # PRODUKT NIE ISTNIEJE -> TWORZYMY NOWY
        res = supabase.table("Produkty").insert({
            "nazwa": nazwa, "liczba": liczba, "cena": cena, "kategoria_id": kategoria_id
        }).execute()
        
        if res.data:
            new_id = res.data[0]['id']
            supabase.table("wydania").insert({
                "produkt_id": new_id,
                "ilosc": liczba,
                "odbiorca": "NOWY PRODUKT",
                "data_wydania": datetime.now().isoformat()
            }).execute()
        st.success(f"Dodano nowy produkt: {nazwa}")
    
    st.rerun()

def update_stock(product_id, current_qty, change, typ_operacji="DOSTAWA"):
    """Aktualizuje stan i zapisuje ruch w historii."""
    new_qty = current_qty + change
    if new_qty < 0:
        st.error("Nie można zejść poniżej zera!")
        return
    
    # Aktualizacja stanu w tabeli Produkty
    supabase.table("Produkty").update({"liczba": new_qty}).eq("id", product_id).execute()
    
    # Zapis ruchu w historii (tabela wydania)
    supabase.table("wydania").insert({
        "produkt_id": product_id,
        "ilosc": abs(change),
        "odbiorca": typ_operacji,
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

# --- ZAKŁADKA: STAN MAGAZYNU (Zaktualizowana o ceny) ---
with tabs[0]:
    if products:
        # Nagłówki dla lepszej czytelności
        h1, h2, h3, h4, h5 = st.columns([3, 2, 2, 2, 3])
        h1.write("**Nazwa**")
        h2.write("**Kategoria**")
        h3.write("**Cena jedn.**")
        h4.write("**Wartość**")
        h5.write("**Zarządzaj stanem**")
        st.markdown("---")

        for p in products:
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 3])
                
                # Dane podstawowe
                c1.write(f"**{p['nazwa']}**")
                kat = p['Kategorie']['nazwa'] if p.get('Kategorie') else "Brak"
                c2.write(kat)
                
                # Wyświetlanie ceny
                cena = float(p['cena']) if p.get('cena') else 0.0
                c3.write(f"{cena:.2f} zł")
                
                # Obliczanie wartości całkowitej zapasu
                wartosc_total = cena * p['liczba']
                c4.write(f"**{wartosc_total:.2f} zł**")
                
                # Zarządzanie ilością
                with c5:
                    sub_c1, sub_c2 = st.columns([1, 1])
                    add_amt = sub_c1.number_input("Ilość", min_value=1, step=1, key=f"in_{p['id']}", label_visibility="collapsed")
                    if sub_c2.button("➕ Dodaj", key=f"btn_{p['id']}", use_container_width=True):
                        update_stock(p['id'], p['liczba'], add_amt, "DOSTAWA")
                
                # Mały tekst informujący o stanie pod spodem
                st.caption(f"Aktualnie na stanie: {p['liczba']} szt.")
    else:
        st.info("Magazyn jest pusty.")

# --- ZAKŁADKA: WYDAJ TOWAR ---
with tabs[1]:
    if products:
        with st.form("form_wydania", clear_on_submit=True):
            options = {f"{p['nazwa']} (Stan: {p['liczba']})": p for p in products}
            sel = st.selectbox("Wybierz towar do wydania", options=list(options.keys()))
            qty = st.number_input("Ilość do wydania", min_value=1, step=1)
            
            if st.form_submit_button("Potwierdź Wydanie", type="primary"):
                p_info = options[sel]
                update_stock(p_info['id'], p_info['liczba'], -qty, "WYDANIE")
    else:
        st.warning("Brak produktów.")

# --- ZAKŁADKA: HISTORIA ---
with tabs[2]:
    st.subheader("Ostatnie operacje (Dostawy i Wydania)")
    if shipments:
        df_h = []
        for s in shipments:
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
