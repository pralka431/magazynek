import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- Konfiguracja Strony ---
st.set_page_config(page_title="Magazyn Supabase", layout="wide")

# --- KLUCZE WPISANE BEZPOŚREDNIO (Hardcoded) ---
# Wklej tutaj swoje dane z panelu Supabase:
SUPABASE_URL = "https://ijfoshdlcpccebzgpmox.supabase.co"
SUPABASE_KEY = "sb_publishable_A1XPX9TeO-Q-rdpcujK75g_DeeUqBkf"

# Inicjalizacja klienta przy użyciu zmiennych powyżej
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Funkcje bazy danych ---

def fetch_categories():
    response = supabase.table("Kategorie").select("*").execute()
    return response.data

def fetch_products():
    # Pobieranie produktów z nazwą kategorii dzięki relacji
    response = supabase.table("Produkty").select("id, nazwa, liczba, cena, Kategorie(nazwa)").execute()
    return response.data

def add_product(nazwa, liczba, cena, kategoria_id):
    data = {
        "nazwa": nazwa,
        "liczba": int(liczba),
        "cena": float(cena),
        "kategoria_id": kategoria_id
    }
    supabase.table("Produkty").insert(data).execute()
    st.rerun()

def delete_product(product_id):
    supabase.table("Produkty").delete().eq("id", product_id).execute()
    st.rerun()

# --- Interfejs Użytkownika ---

st.title("📦 Magazyn (Klucze w kodzie)")

# Dalej idzie reszta interfejsu (Tabs, Formularze, Tabela) 
# tak jak w poprzednim przykładzie...
# [Tu wstaw resztę kodu z poprzedniej wiadomości, zaczynając od st.tabs]
