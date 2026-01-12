import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz

# --- Konfiguracja Strony ---
st.set_page_config(page_title="Magazynek Pro", layout="wide", page_icon="📦")

# --- DANE DOSTĘPOWE ---
SUPABASE_URL = "https://ijfoshdlcpccebzgpmox.supabase.co"
SUPABASE_KEY = "sb_publishable_A1XPX9TeO-Q-rdpcujK75g_DeeUqBkf"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNKCJE POMOCNICZE ---

def get_now_pl():
    """Zwraca aktualny czas w Polsce w formacie ISO."""
    tz = pytz.timezone('Europe/Warsaw')
    return datetime.now(tz).isoformat()

# --- FUNKCJE BAZY DANYCH ---

@st.cache_data(ttl=10)
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
    """Zapisuje ruch w tabeli wydania z poprawnym czasem PL."""
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
        st.error("Błąd: Niewystarczająca ilość towaru na stanie!")

# --- INTERFEJS UŻYTKOWNIKA ---

st.title("📦 System Magazynowy Pro")

try:
    categories, products, shipments = fetch_data()
except Exception as e:
    st.error(f"Problem z połączeniem z bazą: {e}")
    st.stop()

# --- DASHBOARD FINANSOWY ---
total_val = sum((p['cena'] or 0) * p['liczba'] for p in products)
m1, m2, m3 = st.columns(3)
m1.metric("Wartość magazynu", f"{total_val:,.2f} zł")
m2.metric("Liczba towarów", sum(p['liczba'] for p in products))
m3.metric("Kategorie", len(categories))

st.divider()

tabs = st.tabs(["📋 Stan Magazynu", "📤 Wydaj Towar", "📜 Historia Ruchu", "➕ Dodaj Produkt", "📁 Kategorie"])

# --- TAB 1: STAN ---
with tabs[0]:
    if products:
        h1, h2, h3, h4, h5 = st.columns([3, 2, 1.5, 1.5, 3])
        h1.write("**Nazwa**")
        h2.write("**Kategoria**")
        h3.write("**Cena jedn.**")
        h4.write("**Wartość**")
        h5.write("**Szybka Dostawa**")
        
        for p in products:
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 1.5, 1.5, 3])
                c1.write(f"**{p['nazwa']}**")
                kat = p['Kategorie']['nazwa'] if p.get('Kategorie') else "Brak"
                c2.write(kat)
                cena = float(p['cena'] or 0)
                c3.write(f"{cena:.2f} zł")
                c4.write(f"**{cena * p['liczba']:.2f} zł**")
                
                with c5:
                    sub_c1, sub_c2 = st.columns([1, 1])
                    amt = sub_c1.number_input("Ilość", min_value=1, key=f"in_{p['id']}", label_visibility="collapsed")
                    if sub_c2.button("➕ Dodaj", key=f"btn_{p['id']}", use_container_width=True):
                        update_stock(p['id'], p['liczba'], amt)
                st.caption(f"Aktualny stan: **{p['liczba']}** szt.")
    else:
        st.info("Magazyn jest obecnie pusty.")

# --- TAB 2: WYDAWANIE ---
with tabs[1]:
    if products:
        with st.form("form_wydania", clear_on_submit=True):
            options = {f"{p['nazwa']} (Stan: {p['liczba']})": p for p in products}
            sel = st.selectbox("Wybierz towar", options=list(options.keys()))
            qty = st.number_input("Ilość do wydania", min_value=1, step=1)
            klient = st.text_input("Odbiorca / Komentarz", "Klient")
            if st.form_submit_button("Potwierdź Wydanie", use_container_width=True):
                p_info = options[sel]
                update_stock(p_info['id'], p_info['liczba'], -qty, klient)

# --- TAB 3: HISTORIA ---
with tabs[2]:
    if shipments:
        df_data = []
        for s in shipments:
            # Sprawdzamy czy to dodanie czy wydanie
            is_delivery = s['odbiorca'] in ["DOSTAWA", "NOWY PRODUKT", "DOSTAWA (SUMOWANIE)"]
            
            # Konwersja czasu na czytelny format (Supabase daje ISO)
            raw_date = datetime.fromisoformat(s['data_wydania'].replace('Z', '+00:00'))
            # Formatujemy do wyświetlenia
            clean_date = raw_date.strftime("%Y-%m-%d %H:%M:%S")
            
            df_data.append({
                "Data i Godzina": clean_date,
                "Produkt": s['Produkty']['nazwa'] if s.get('Produkty') else "N/A",
                "Typ": "📥 PRZYJĘCIE" if is_delivery else "📤 WYDANIE",
                "Odbiorca/Źródło": s['odbiorca'],
                "Ilość": s['ilosc']
            })
        st.dataframe(df_data, use_container_width=True, hide_index=True)

# --- TAB 4: NOWY PRODUKT ---
with tabs[3]:
    if not categories:
        st.warning("Najpierw dodaj kategorię w ostatniej zakładce!")
    else:
        with st.form("new_p"):
            name = st.text_input("Pełna nazwa produktu")
            cat_map = {c['nazwa']: c['id'] for c in categories}
            sel_cat = st.selectbox("Kategoria", options=list(cat_map.keys()))
            p_qty = st.number_input("Stan początkowy", min_value=0)
            p_price = st.number_input("Cena zakupu netto", min_value=0.0)
            if st.form_submit_button("Zapisz w bazie"):
                if name:
                    add_product(name, p_qty, p_price, cat_map[sel_cat])

# --- TAB 5: KATEGORIE ---
with tabs[4]:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Dodaj nową")
        with st.form("new_cat"):
            c_name = st.text_input("Nazwa")
            c_desc = st.text_area("Opis")
            if st.form_submit_button("Dodaj"):
                add_category(c_name, c_desc)
    with col2:
        st.subheader("Istniejące")
        if categories:
            st.table(pd.DataFrame(categories)[["nazwa", "opis"]])
