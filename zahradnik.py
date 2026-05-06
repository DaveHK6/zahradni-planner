import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# --- 1. POMOCNÉ FUNKCE ---
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
    
    # --- 2. PŘIPOJENÍ K DATŮM (Ošetřeno proti chybějícím listům) ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Definujeme názvy listů (Ujisti se, že se tak jmenují i v Google Sheets!)
    MAIN_SHEET = "Sheet1" 
    ARCHIVE_SHEET = "Archiv"

    try:
        df_real = conn.read(worksheet=MAIN_SHEET, ttl=0).dropna(how="all")
    except Exception as e:
        st.error(f"⚠️ Nepodařilo se načíst hlavní list '{MAIN_SHEET}'. Zkontroluj název v Google tabulce.")
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Posledni_Hnojeni", "Ucinnek_Hnojiva", "Poznamka"])

    try:
        df_archive = conn.read(worksheet=ARCHIVE_SHEET, ttl=0).dropna(how="all")
    except:
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

    BEDS = ["Záhon 1", "Záhon 2"]
    ROWS = list("ABCDEF")
    COLS = [1, 2, 3]

    if not df_real.empty:
        df_real['Datum_Vysadby'] = pd.to_datetime(df_real['Datum_Vysadby']).dt.date
        if 'Ocekavana_Sklizen' in df_real.columns:
            df_real['Ocekavana_Sklizen'] = pd.to_datetime(df_real['Ocekavana_Sklizen']).dt.date
        if 'Posledni_Hnojeni' in df_real.columns:
            df_real['Posledni_Hnojeni'] = pd.to_datetime(df_real['Posledni_Hnojeni']).dt.date
        
        dnes = datetime.now().date()
        df_real['Zbývá dní'] = df_real['Ocekavana_Sklizen'].apply(lambda x: (x - dnes).days if pd.notnull(x) else 0)

    st.title("🌱 Zahradní Manažer Pro")

    # --- 4. MRAZOVÝ RADAR ---
    current_temp = None
    if "weather" in st.secrets:
        api_key = st.secrets["weather"]["api_key"]
        city = st.secrets["weather"]["city"]
        curr, fore = get_weather_data(api_key, city)
        
        if curr and curr.get("cod") == 200:
            current_temp = curr['main']['temp']
            st.metric("Aktuálně Polánka", f"{current_temp} °C")
            
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
                    st.success("🌤️ V příštích 5 dnech mráz nehrozí.")

    st.divider()

    # --- 5. TABY ---
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Plán & Živiny", "🗺️ Mapa", "⚙️ Správa", "📂 Archiv"])

    with tab1:
        st.header("📝 Přehled výsadby")
        if not df_real.empty:
            def style_rows(row):
                dnes = datetime.now().date()
                start_date = row['Posledni_Hnojeni'] if pd.notnull(row['Posledni_Hnojeni']) else row['Datum_Vysadby']
                interval = row['Ucinnek_Hnojiva'] if pd.notnull(row['Ucinnek_Hnojiva']) and row['Ucinnek_Hnojiva'] > 0 else PLANT_DATABASE.get(row['Plodina'], {}).get("def_fert", 14)
                next_fert = start_date + timedelta(days=int(interval))
                
                if dnes >= next_fert: return ['background-color: #4b2e2e; color: white'] * len(row)
                if current_temp is not None:
                    limit = PLANT_DATABASE.get(row['Plodina'], {}).get("frost", 0)
                    if current_temp <= limit: return ['background-color: #721c24; color: white'] * len(row)
                return [''] * len(row)

            st.dataframe(df_real.style.apply(style_rows, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("Záhon je prázdný.")

    # ... (zbytek tabů 2, 3 a 4 zůstává stejný jako v tvém Core kódu)

if __name__ == "__main__":
    main()