import streamlit as st

# --- Konfiguracja Strony ---
st.set_page_config(
    page_title="Prosty Magazyn (Streamlit + Sesja)",
    layout="wide"
)

# --- Inicjalizacja Danych Magazynu ---

# Sprawdzanie, czy lista towarów istnieje już w stanie sesji.
# Jeśli nie istnieje (pierwsze uruchomienie), tworzymy pustą listę.
if 'inventory' not in st.session_state:
    st.session_state['inventory'] = []

## --- Funkcje Magazynu ---

def add_item(name, quantity):
    """Dodaje nowy towar do magazynu (listy w stanie sesji)."""
    if name and quantity:
        try:
            quantity_int = int(quantity)
            if quantity_int > 0:
                new_item = {"Nazwa": name, "Ilość": quantity_int}
                st.session_state.inventory.append(new_item)
                st.success(f"Dodano: {name} (Ilość: {quantity_int})")
            else:
                st.error("Ilość musi być liczbą całkowitą większą od zera.")
        except ValueError:
            st.error("Ilość musi być poprawną liczbą całkowitą.")
    else:
        st.error("Proszę podać nazwę i ilość towaru.")

def delete_item(index):
    """Usuwa towar z magazynu na podstawie jego indeksu."""
    if 0 <= index < len(st.session_state.inventory):
        removed_item = st.session_state.inventory.pop(index)
        st.success(f"Usunięto towar: {removed_item['Nazwa']}")
    else:
        st.error("Wystąpił błąd podczas usuwania. Indeks poza zakresem.")


# --- Interfejs Użytkownika Streamlit ---

st.title("📦 Prosty Magazyn w Streamlit")
st.markdown("---")

# 1. Panel Dodawania Towaru
with st.container(border=True):
    st.header("➕ Dodaj Nowy Towar")
    
    # Używamy kolumn dla lepszego układu
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        new_item_name = st.text_input("Nazwa Towaru", key="new_name")
    with col2:
        new_item_quantity = st.number_input("Ilość", min_value=1, value=1, step=1, key="new_quantity")
    with col3:
        # Pusty wiersz dla wyrównania przycisku
        st.markdown("<br>", unsafe_allow_html=True)
        # Przyciski Streamlit domyślnie wywołują ponowne uruchomienie skryptu
        if st.button("Dodaj do Magazynu", type="primary"):
            # Wywołujemy funkcję dodającą
            # Przekazujemy wartości z pól, które Streamlit automatycznie zaktualizował
            add_item(new_item_name, new_item_quantity)

st.markdown("---")

# 2. Wyświetlanie Magazynu i Panel Usuwania
st.header("📋 Aktualny Stan Magazynu")

if st.session_state.inventory:
    # Tworzenie DataFrame dla lepszej wizualizacji w Streamlit
    import pandas as pd
    df = pd.DataFrame(st.session_state.inventory)
    
    # Wyświetlanie danych jako interaktywna tabela
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_order=["Nazwa", "Ilość"]
    )
    
    st.subheader("🗑️ Usuń Towar")
    
    # Lista nazw towarów do wyboru
    item_names = [item['Nazwa'] for item in st.session_state.inventory]
    
    # Widget Selectbox do wyboru towaru do usunięcia
    item_to_delete_name = st.selectbox(
        "Wybierz towar do usunięcia:",
        options=item_names,
        index=None,
        placeholder="Wybierz towar...",
        key="select_to_delete"
    )

    if st.button("Usuń Wybrany Towar", type="secondary"):
        if item_to_delete_name:
            # Znajdujemy indeks wybranego towaru
            try:
                index_to_delete = item_names.index(item_to_delete_name)
                delete_item(index_to_delete)
            except ValueError:
                st.error("Błąd: Nie znaleziono wybranego towaru.")
        else:
            st.warning("Proszę wybrać towar do usunięcia.")
    
else:
    st.info("Magazyn jest pusty. Dodaj pierwszy towar powyżej.")

# --- Koniec Aplikacji ---
