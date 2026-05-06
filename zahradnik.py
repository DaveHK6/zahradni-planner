import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests
import plotly.figure_factory as ff  # Nová knihovna pro Ganttův diagram

# --- 1. KONSTANTY A TEXTOVÁ DOKUMENTACE ---
TEXT_ZAHON_1 = """### 🏰 ZÁHON 1: Cuketové království...""" # (zkráceno pro přehlednost, v tvém kódu ponech celé)
TEXT_ZAHON_2 = """### 🔄 ZÁHON 2: Česnekovo-fazolová rotace..."""

# --- 2. POMOCNÉ FUNKCE ---

def get_weather_data(api_key, city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=cz"
        res = requests.get(url, timeout=5).json()
        return res if res.get("cod") == 200 else None
    except: return None

def update_db(conn, sheet_name, data):
    conn.update(worksheet=sheet_name, data=data)

def create_gantt_chart(df):
    """Vytvoří Ganttův diagram z datového rámce výsadby."""
    if df.empty:
        return None
    
    df_gantt = []
    for _, row in df.iterrows():
        df_gantt.append(dict(
            Task=f"{row['Plodina']} ({row['Pozice']})",
            Start=row['Datum_Vysadby'],
            Finish=row['Ocekavana_Sklizen'],
            Resource=row['Záhon']
        ))
    
    # Vytvoření grafu pomocí Plotly
    fig = ff.create_gantt(df_gantt, index_col='Resource', show_colorbar=True,
                          group_tasks=True, showgrid_x=True, showgrid_y=True,
                          title="Časový plán sklizně")
    fig.update_layout(xaxis_type='date')
    return fig

# --- 3. HLAVNÍ APLIKACE ---

def main():
    st.set_page_config(page_title="Zahradní Manažer Pro", layout="wide", page_icon="🌱")
    
    # Připojení a načtení dat
    conn = st.connection("gsheets", type=GSheetsConnection)
    MAIN_SHEET, ARCHIVE_SHEET = "List 1", "Archiv"

    try:
        df_real = conn.read(worksheet=MAIN_SHEET, ttl=0).dropna(how="all")
        for col in ['Datum_Vysadby', 'Ocekavana_Sklizen', 'Posledni_Hnojeni']:
            if col in df_real.columns:
                df_real[col] = pd.to_datetime(df_real[col], dayfirst=True, errors='coerce')
    except:
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen"])

    # --- POČASÍ (viz předchozí verze) ---
    st.title("🌱 Zahradní Manažer Pro")
    # ... (zde zůstává kód pro počasí) ...

    st.divider()

    # --- TABS (Přidána nová záložka) ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Přehled", "🗺️ Mapa", "⏳ Časová osa", "⚙️ Správa", "📂 Archiv"])

    with tab1:
        st.markdown(TEXT_ZAHON_1)
        st.markdown(TEXT_ZAHON_2)

    with tab2:
        st.header("🗺️ Mapa osázení")
        # ... (zde zůstává kód pro mapu) ...

    with tab3:
        st.header("⏳ Časová osa pěstování")
        if not df_real.empty:
            with st.spinner("Generuji časovou osu..."):
                fig = create_gantt_chart(df_real)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Zatím nemáš nic zasazeno, časová osa je prázdná.")

    with tab4:
        st.header("⚙️ Správa a Hnojení")
        # ... (zde zůstává kód pro formulář a tlačítka) ...

    with tab5:
        st.header("📂 Archiv")
        # ... (zde zůstává kód pro zobrazení archivu) ...

if __name__ == "__main__":
    main()