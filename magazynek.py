import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- Konfiguracja Strony ---
st.set_page_config(page_title="Magazyn Pro - Supabase", layout="wide")

# --- Połączenie z Supabase ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- Funkcje bazy danych ---

def fetch_categories():
    """Pobiera wszystkie kategorie."""
    response = supabase.table("Kategorie").select("*").execute()
    return response.data

def fetch_products():
    """Pobiera produkty wraz z nazwami ich kategorii (JOIN)."""
    # Supabase pozwala na proste łączenie tabel przez relacje:
    response = supabase.table("Produkty").select("id, nazwa, liczba, cena, Kategorie(nazwa)").execute()
    return response.data

def add_product(nazwa, liczba, cena, kategoria_id):
    """Dodaje produkt do bazy."""
    data = {
        "nazwa": nazwa,
        "liczba": int(liczba),
        "cena": float(cena),
        "kategoria_id": kategoria_id
    }
    supabase.table("Produkty").insert(data).execute()
    st.rerun()

def delete_product(product_id):
    """Usuwa produkt."""
    supabase.table("Produkty").delete().eq("id", product_id).execute()
    st.rerun()

# --- Interfejs Użytkownika ---

st.title("📦 Zaawansowany Magazyn")

# Pobieramy dane na starcie
categories = fetch_categories()
products = fetch_products()

# Tworzymy zakładki dla lepszej organizacji
tab1, tab2 = st.tabs(["📋 Stan Magazynu", "➕ Dodaj Produkt"])

with tab2:
    st.header("Dodaj nowy produkt")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Nazwa produktu")
            # Selectbox dla kategorii - mapujemy nazwę na ID
            cat_options = {c['nazwa']: c['id'] for c in categories}
            selected_cat_name = st.selectbox("Kategoria", options=list(cat_options.keys()))
            
        with col2:
            qty = st.number_input("Liczba sztuk", min_value=0, step=1)
            price = st.number_input("Cena (PLN)", min_value=0.0, step=0.01)
            
        submit = st.form_submit_button("Dodaj produkt", type="primary")
        
        if submit:
            if name and selected_cat_name:
                add_product(name, qty, price, cat_options[selected_cat_name])
                st.success(f"Dodano produkt: {name}")
            else:
                st.error("Wypełnij wszystkie pola!")

with tab1:
    st.header("Aktualne zapasy")
    
    if products:
        # Przekształcenie danych do ładnej tabeli
        display_data = []
        for p in products:
            display_data.append({
                "ID": p['id'],
                "Nazwa": p['nazwa'],
                "Liczba": p['liczba'],
                "Cena": f"{p['cena']} zł",
                "Kategoria": p['Kategorie']['nazwa'] if p['Kategorie'] else "Brak"
            })
        
        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("🗑️ Usuwanie produktów")
        
        # Opcja usuwania
        del_col1, del_col2 = st.columns([3, 1])
        with del_col1:
            to_delete = st.selectbox("Wybierz produkt do usunięcia", 
                                     options=[f"{p['nazwa']} (ID: {p['id']})" for p in products])
        with del_col2:
            st.write("") # Margines
            if st.button("Usuń trwale", type="secondary", use_container_width=True):
                # Wyciągamy ID z tekstu: "Nazwa (ID: 123)"
                p_id = int(to_delete.split("ID: ")[1].replace(")", ""))
                delete_product(p_id)
    else:
        st.info("Magazyn jest pusty. Dodaj pierwszy produkt w zakładce obok.")
