import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# --- 1. POMOCNÉ FUNKCE (Počasí) ---
def get_weather_data(api_key, city):
    try:
        curr_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=cz"
        curr_res = requests.get(curr_url).json()
        fore_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&lang=cz"
        fore_res = requests.get(fore_url).json()
        return curr_res, fore_res
    except:
        return None, None

def main():
    st.set_page_config(page_title="Záhon Planner Pro", layout="wide", page_icon="🌱")
    
    # --- 2. KONFIGURACE NÁZVŮ (Změněno na 'List 1' dle tvé tabulky) ---
    # Tady jsme opravili ten nesoulad, který způsobil chybu na obrázku.
    MAIN_SHEET_NAME = "List 1" 
    ARCHIVE_SHEET_NAME = "Archiv"

    conn = st.connection("gsheets", type=GSheetsConnection)

    # Bezpečné načtení hlavních dat z 'List 1'
    try:
        df_real = conn.read(worksheet=MAIN_SHEET_NAME, ttl=0).dropna(how="all")
    except Exception:
        st.warning(f"⚠️ Pozor: List s názvem '{MAIN_SHEET_NAME}' nebyl v tabulce nalezen.")
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Posledni_Hnojeni", "Ucinnek_Hnojiva", "Poznamka"])

    # Bezpečné načtení archivu
    try:
        df_archive = conn.read(worksheet=ARCHIVE_SHEET_NAME, ttl=0).dropna(how="all")
    except Exception:
        df_archive = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Datum_Sklizne", "Poznamka"])

    # --- 3. INTELIGENTNÍ DATABÁZE PLODIN ---
    PLANT_DATABASE = {
        "Ředkvičky": {"growth": 30, "frost": -2, "def_fert": 10},
        "Špenát": {"growth": 45, "frost": -5, "def_fert": 15},
        "Cukety": {"growth": 60, "frost": 5, "def_fert": 20},
        "Salát": {"growth": 50, "frost": 1, "def_fert": 14},
        "Česnek": {"growth": 240, "frost": -10, "def_fert": 60},
        "Rajčata": {"growth": 80, "frost": 7, "def_fert": 14},
        "Fazole": {"growth": 65, "frost": 5, "def_fert": 21},
        "Pak Choi": {"growth": 40, "frost": 2, "def_fert": 10}
    }

    # Zpracování dat pro tabulku
    if not df_real.empty:
        # Převedeme textová data na formát data, aby s nimi mohl Python počítat
        for col in ['Datum_Vysadby', 'Ocekavana_Sklizen', 'Posledni_Hnojeni']:
            if col in df_real.columns:
                df_real[col] = pd.to_datetime(df_real[col], errors='coerce').dt.date
        
        dnes = datetime.now().date()
        if 'Ocekavana_Sklizen' in df_real.columns:
            df_real['Zbývá dní'] = df_real['Ocekavana_Sklizen'].apply(lambda x: (x - dnes).days if pd.notnull(x) else 0)

    st.title("🌱 Zahradní Manažer Pro")

    # --- 4. MRAZOVÝ RADAR (Nezávislý na chybě v tabulce) ---
    current_temp = None
    if "weather" in st.secrets:
        api_key = st.secrets["weather"]["api_key"]
        city = st.secrets["weather"]["city"]
        curr, fore = get_weather_data(api_key, city)
        
        if curr and curr.get("cod") == 200:
            current_temp = curr['main']['temp']
            st.metric("Aktuálně Polánka", f"{current_temp} °C")
            
            # Pokud máme data o počasí i o rostlinách, vyhodnotíme riziko
            if fore and fore.get("cod") == "200" and not df_real.empty:
                forecast_risks = []
                for entry in fore['list'][:40]:
                    f_temp = entry['main']['temp']
                    f_time = datetime.strptime(entry['dt_txt'], '%Y-%m-%d %H:%M:%S')
                    for crop in df_real['Plodina'].unique():
                        limit = PLANT_DATABASE.get(crop, {}).get("frost", 0)
                        if f_temp <= limit:
                            forecast_risks.append({"crop": crop, "temp": f_temp, "time": f_time})
                
                if forecast_risks:
                    worst = min(forecast_risks, key=lambda x: x['temp'])
                    st.error(f"🚨 **MRAZOVÁ VÝSTRAHA:** {worst['time'].strftime('%d.%m. %H:%M')} bude {worst['temp']}°C.")
                else:
                    st.success("🌤️ Předpověď na 5 dní je pro tvou výsadbu bezpečná.")

    st.divider()

    # --- 5. TABY (Uživatelské rozhraní) ---
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Plán & Živiny", "🗺️ Mapa", "⚙️ Správa", "📂 Archiv"])

    with tab1:
        st.header("📝 Přehled výsadby")
        if not df_real.empty:
            def style_rows(row):
                dnes = datetime.now().date()
                # Výpočet živin
                start_date = row['Posledni_Hnojeni'] if pd.notnull(row.get('Posledni_Hnojeni')) else row['Datum_Vysadby']
                interval = row.get('Ucinnek_Hnojiva', 14) 
                if pd.isna(interval) or interval <= 0: interval = 14
                
                if pd.notnull(start_date):
                    next_fert = start_date + timedelta(days=int(interval))
                    if dnes >= next_fert: return ['background-color: #4b2e2e; color: white'] * len(row)
                
                # Výpočet mrazu
                if current_temp is not None:
                    limit = PLANT_DATABASE.get(row['Plodina'], {}).get("frost", 0)
                    if current_temp <= limit: return ['background-color: #721c24; color: white'] * len(row)
                return [''] * len(row)

            st.dataframe(df_real.style.apply(style_rows, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info(f"Záhon v listu '{MAIN_SHEET_NAME}' je prázdný.")

    with tab3:
        st.header("⚙️ Správa zahrady")
        with st.form("add_form", clear_on_submit=True):
            st.subheader("➕ Nová plodina")
            f_crop = st.selectbox("Plodina", list(PLANT_DATABASE.keys()))
            f_bed = st.selectbox("Záhon", ["Záhon 1", "Záhon 2"])
            f_pos = st.text_input("Pozice (např. A1)")
            f_date = st.date_input("Datum výsadby", datetime.now())
            if st.form_submit_button("Uložit do Google Sheets"):
                sklizen = f_date + timedelta(days=PLANT_DATABASE[f_crop]["growth"])
                new_row = pd.DataFrame([{"Plodina": f_crop, "Záhon": f_bed, "Pozice": f_pos, "Datum_Vysadby": f_date, "Ocekavana_Sklizen": sklizen, "Posledni_Hnojeni": None, "Ucinnek_Hnojiva": 0, "Poznamka": ""}])
                # Zápis zpět do správného listu
                conn.update(worksheet=MAIN_SHEET_NAME, data=pd.concat([df_real.drop(columns=['Zbývá dní'], errors='ignore'), new_row], ignore_index=True))
                st.success("Zapsáno do 'List 1'!"); st.rerun()

if __name__ == "__main__":
    main()