import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# --- 1. POMOCNÉ FUNKCE (Počasí a API) ---
def get_weather_data(api_key, city):
    """Získává data z OpenWeatherMap API."""
    try:
        curr_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=cz"
        curr_res = requests.get(curr_url).json()
        return curr_res
    except:
        return None

def main():
    st.set_page_config(page_title="Záhon Planner Pro", layout="wide", page_icon="🌱")
    
    # --- 2. KONFIGURACE DAT ---
    MAIN_SHEET = "List 1"  # Tvůj specifický název listu
    ARCHIVE_SHEET = "Archiv"
    
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Načtení dat s ošetřením chyb
    try:
        df_real = conn.read(worksheet=MAIN_SHEET, ttl=0).dropna(how="all")
    except:
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Posledni_Hnojeni", "Ucinnek_Hnojiva"])

    # Databáze konstant plodin
    PLANT_DATABASE = {
        "Ředkvičky": {"growth": 30, "frost": -2, "fert": 10},
        "Špenát": {"growth": 45, "frost": -5, "fert": 15},
        "Cukety": {"growth": 60, "frost": 5, "fert": 20},
        "Salát": {"growth": 50, "frost": 1, "fert": 14},
        "Rajčata": {"growth": 80, "frost": 7, "fert": 14}
    }

    # Předzpracování dat pro výpočty
    if not df_real.empty:
        df_real['Datum_Vysadby'] = pd.to_datetime(df_real['Datum_Vysadby'], errors='coerce').dt.date
        df_real['Posledni_Hnojeni'] = pd.to_datetime(df_real['Posledni_Hnojeni'], errors='coerce').dt.date
        df_real['Ocekavana_Sklizen'] = pd.to_datetime(df_real['Ocekavana_Sklizen'], errors='coerce').dt.date
        dnes = datetime.now().date()
        df_real['Dní do sklizně'] = df_real['Ocekavana_Sklizen'].apply(lambda x: (x - dnes).days if pd.notnull(x) else 0)

    st.title("🌱 Zahradní Manažer Pro")

    # --- 3. POČASÍ ---
    if "weather" in st.secrets:
        weather = get_weather_data(st.secrets["weather"]["api_key"], st.secrets["weather"]["city"])
        if weather and weather.get("cod") == 200:
            st.metric(f"Aktuálně: {st.secrets['weather']['city']}", f"{weather['main']['temp']} °C")

    st.divider()

    # --- 4. HLAVNÍ ROZHRANÍ (TABY) ---
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Přehled výsadby", "🗺️ Mapa", "⚙️ Správa & Hnojení", "📂 Archiv"])

    # TAB 1: PŘEHLEDOVÁ TABULKA
    with tab1:
        st.header("📝 Aktuální stav plodin")
        if not df_real.empty:
            def highlight_fert(row):
                """Logika barvení řádků podle hnojení."""
                dnes = datetime.now().date()
                last_fert = row['Posledni_Hnojeni'] if pd.notnull(row['Posledni_Hnojeni']) else row['Datum_Vysadby']
                interval = row['Ucinnek_Hnojiva'] if pd.notnull(row['Ucinnek_Hnojiva']) and row['Ucinnek_Hnojiva'] > 0 else 14
                
                if pd.notnull(last_fert) and (dnes - last_fert).days >= interval:
                    return ['background-color: #4b2e2e; color: white'] * len(row)
                return [''] * len(row)

            st.dataframe(df_real.style.apply(highlight_fert, axis=1), use_container_width=True, hide_index=True)
            st.info("💡 Hnědý řádek = Rostlina potřebuje hnojivo (vypršel interval).")
        else:
            st.info("Žádné plodiny nenalezeny. Přidejte je v záložce Správa.")

    # TAB 2: VIZUÁLNÍ MAPA
    with tab2:
        st.header("🗺️ Mapa záhonů")
        if not df_real.empty:
            for bed in ["Záhon 1", "Záhon 2"]:
                with st.expander(bed, expanded=True):
                    for r in list("ABCDEF"):
                        cols = st.columns(3)
                        for i, c in enumerate([1, 2, 3]):
                            pos = f"{r}{c}"
                            match = df_real[(df_real["Záhon"] == bed) & (df_real["Pozice"] == pos)]
                            with cols[i]:
                                if not match.empty:
                                    st.success(f"**{pos}**\n\n{match.iloc[-1]['Plodina']}")
                                else:
                                    st.info(f"**{pos}**\n\n--")
        else:
            st.info("Zatím není co zobrazit na mapě.")

    # TAB 3: SPRÁVA & HNOJENÍ
    with tab3:
        st.header("⚙️ Správa zahrady")
        
        # FORMULÁŘ PRO HNOJENÍ
        st.subheader("🧪 Zadat hnojení")
        if not df_real.empty:
            with st.form("fert_form"):
                idx = st.selectbox("Vyber plodinu", df_real.index, format_func=lambda x: f"{df_real.loc[x, 'Plodina']} ({df_real.loc[x, 'Pozice']})")
                f_date = st.date_input("Datum hnojení", datetime.now())
                f_days = st.number_input("Délka účinku (dny)", min_value=1, value=14)
                if st.form_submit_button("Uložit hnojení"):
                    df_real.at[idx, 'Posledni_Hnojeni'] = f_date
                    df_real.at[idx, 'Ucinnek_Hnojiva'] = f_days
                    conn.update(worksheet=MAIN_SHEET, data=df_real.drop(columns=['Dní do sklizně'], errors='ignore'))
                    st.success("Hnojení zapsáno!"); st.rerun()

        st.divider()

        # FORMULÁŘ PRO NOVOU VÝSADBU
        st.subheader("➕ Nová výsadba")
        with st.form("add_form"):
            col1, col2, col3 = st.columns(3)
            p_crop = col1.selectbox("Plodina", list(PLANT_DATABASE.keys()))
            p_bed = col2.selectbox("Záhon", ["Záhon 1", "Záhon 2"])
            p_pos = col3.text_input("Pozice (např. A1)")
            p_date = st.date_input("Datum výsadby", datetime.now())
            if st.form_submit_button("Zasadit"):
                sklizen = p_date + timedelta(days=PLANT_DATABASE[p_crop]["growth"])
                new_data = pd.DataFrame([{"Plodina": p_crop, "Záhon": p_bed, "Pozice": p_pos, "Datum_Vysadby": p_date, "Ocekavana_Sklizen": sklizen, "Ucinnek_Hnojiva": 14}])
                updated_df = pd.concat([df_real.drop(columns=['Dní do sklizně'], errors='ignore'), new_data], ignore_index=True)
                conn.update(worksheet=MAIN_SHEET, data=updated_df)
                st.success("Plodina přidána!"); st.rerun()

if __name__ == "__main__":
    main()