import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- Konfiguracja Strony ---
st.set_page_config(page_title="Magazynek Pro", layout="wide", page_icon="📦")

# --- DANE DOSTĘPOWE (Zalecane użycie st.secrets) ---
# W wersji produkcyjnej użyj: st.secrets["SUPABASE_URL"]
SUPABASE_URL = "https://ijfoshdlcpccebzgpmox.supabase.co"
SUPABASE_KEY = "sb_publishable_A1XPX9TeO-Q-rdpcujK75g_DeeUqBkf"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNKCJE BAZY DANYCH ---
@st.cache_data(ttl=60) # Cache na 60 sekund, żeby nie odpytywać bazy przy każdym kliknięciu
def fetch_data():
    categories = supabase.table("Kategorie").select("*").execute().data
    products = supabase.table("Produkty").select("*, Kategorie(nazwa)").order("nazwa").execute().data
    shipments = supabase.table("wydania").select("*, Produkty(nazwa)").order("data_wydania", desc=True).limit(50).execute().data
    return categories, products, shipments

def add_category(nazwa, opis):
    if nazwa:
        supabase.table("Kategorie").insert({"nazwa": nazwa, "opis": opis}).execute()
        st.cache_data.clear()
        st.success(f"Dodano kategorię: {nazwa}")
        st.rerun()

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

def log_movement(product_id, qty, type_name):
    supabase.table("wydania").insert({
        "produkt_id": product_id, "ilosc": qty, "odbiorca": type_name, "data_wydania": datetime.now().isoformat()
    }).execute()

def update_stock(product_id, current_qty, change, typ_operacji="DOSTAWA"):
    new_qty = current_qty + change
    if new_qty >= 0:
        supabase.table("Produkty").update({"liczba": new_qty}).eq("id", product_id).execute()
        log_movement(product_id, abs(change), typ_operacji)
        st.cache_data.clear()
        st.rerun()
    else:
        st.error("Błąd: Niewystarczająca ilość towaru!")

# --- INTERFEJS UŻYTKOWNIKA ---

st.title("📦 Inteligentny System Magazynowy")

try:
    categories, products, shipments = fetch_data()
except Exception as e:
    st.error(f"Problem z połączeniem: {e}")
    st.stop()

# --- DASHBOARD (METRYKI) ---
total_value = sum((p['cena'] or 0) * p['liczba'] for p in products)
total_items = sum(p['liczba'] for p in products)

m1, m2, m3 = st.columns(3)
m1.metric("Wartość Magazynu", f"{total_value:,.2f} zł".replace(",", " "))
m2.metric("Liczba Produktów", total_items)
m3.metric("Liczba Kategorii", len(categories))

st.divider()

tabs = st.tabs(["📋 Stan i Szybka Dostawa", "📤 Wydawanie Towaru", "📜 Historia Ruchów", "🛠 Konfiguracja"])

# --- ZAKŁADKA 1: STAN ---
with tabs[0]:
    if products:
        # Nagłówki
        h1, h2, h3, h4, h5 = st.columns([3, 2, 2, 2, 3])
        h1.caption("PRODUKT")
        h2.caption("KATEGORIA")
        h3.caption("CENA NETTO")
        h4.caption("WARTOŚĆ")
        h5.caption("DOSTAWA")
        
        for p in products:
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 3])
                c1.write(f"**{p['nazwa']}**")
                kat = p['Kategorie']['nazwa'] if p.get('Kategorie') else "Brak"
                c2.write(f"🏷️ {kat}")
                cena = float(p['cena'] or 0)
                c3.write(f"{cena:.2f} zł")
                c4.write(f"**{cena * p['liczba']:.2f} zł**")
                
                with c5:
                    sub_c1, sub_c2 = st.columns([1, 1])
                    amt = sub_c1.number_input("Szt", min_value=1, key=f"in_{p['id']}", label_visibility="collapsed")
                    if sub_c2.button("➕", key=f"btn_{p['id']}", help="Szybkie dodanie do stanu"):
                        update_stock(p['id'], p['liczba'], amt)
                
                # Pasek postępu dla wizualizacji stanu (opcjonalnie)
                st.caption(f"Aktualny stan: {p['liczba']} szt.")
                st.divider()
    else:
        st.info("Brak towarów w bazie.")

# --- ZAKŁADKA 2: WYDAWANIE ---
with tabs[1]:
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.subheader("Wydaj towar z magazynu")
        if products:
            with st.form("form_wydania", clear_on_submit=True):
                options = {f"{p['nazwa']} (Dostępne: {p['liczba']})": p for p in products}
                sel = st.selectbox("Wybierz towar", options=list(options.keys()))
                qty = st.number_input("Ilość do wydania", min_value=1, step=1)
                klient = st.text_input("Odbiorca / Nr zamówienia", "Klient Detaliczny")
                
                if st.form_submit_button("Zatwierdź wydanie 📤", use_container_width=True):
                    p_info = options[sel]
                    if p_info['liczba'] >= qty:
                        update_stock(p_info['id'], p_info['liczba'], -qty, klient)
                    else:
                        st.error("Nie masz tyle towaru!")

# --- ZAKŁADKA 3: HISTORIA ---
with tabs[2]:
    if shipments:
        data_hist = []
        for s in shipments:
            is_in = s['odbiorca'] in ["DOSTAWA", "NOWY PRODUKT", "DOSTAWA (SUMOWANIE)"]
            data_hist.append({
                "Data": s['data_wydania'][:16].replace("T", " "),
                "Produkt": s['Produkty']['nazwa'] if s.get('Produkty') else "Produkt usunięty",
                "Operacja": "🟢 PRZYJĘCIE" if is_in else f"🔴 WYDANIE ({s['odbiorca']})",
                "Ilość": s['ilosc']
            })
        df = pd.DataFrame(data_hist)
        st.dataframe(df, use_container_width=True, hide_index=True)

# --- ZAKŁADKA 4: KONFIGURACJA (Kategorie + Nowe Produkty) ---
with tabs[3]:
    c_left, c_right = st.columns(2)
    
    with c_left:
        st.subheader("🆕 Nowy Produkt")
        if categories:
            with st.form("new_p"):
                name = st.text_input("Nazwa produktu")
                cat_map = {c['nazwa']: c['id'] for c in categories}
                sel_cat = st.selectbox("Kategoria", options=list(cat_map.keys()))
                p_qty = st.number_input("Ilość początkowa", min_value=0)
                p_price = st.number_input("Cena zakupu netto", min_value=0.0)
                if st.form_submit_button("Zapisz Produkt", use_container_width=True):
                    add_product(name, p_qty, p_price, cat_map[sel_cat])
        else:
            st.warning("Najpierw dodaj kategorię!")

    with c_right:
        st.subheader("📁 Zarządzanie Kategoriami")
        with st.form("new_cat"):
            c_name = st.text_input("Nazwa kategorii (np. Elektronika)")
            c_desc = st.text_area("Opis")
            if st.form_submit_button("Dodaj Kategorię", use_container_width=True):
                add_category(c_name, c_desc)
        
        if categories:
            with st.expander("Zobacz istniejące kategorie"):
                st.table(pd.DataFrame(categories)[["nazwa", "opis"]])
