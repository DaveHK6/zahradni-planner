import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# --- 1. POMOCNÉ FUNKCE ---
def get_weather_data(api_key, city):
    """Získává aktuální data a předpověď z OpenWeatherMap na 5 dní."""
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
    
    # --- 2. PŘIPOJENÍ K DATŮM (Načítání hlavního listu a archivu) ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df_real = conn.read(worksheet="Sheet1", ttl=0).dropna(how="all")
    except:
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Posledni_Hnojeni", "Ucinnek_Hnojiva", "Poznamka"])

    try:
        df_archive = conn.read(worksheet="Archiv", ttl=0).dropna(how="all")
    except:
        df_archive = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Datum_Sklizne", "Poznamka"])

    # --- 3. INTELIGENTNÍ DATABÁZE PLODIN (Konstanty pro výpočty) ---
    # def_fert: výchozí počet dní do dalšího hnojení, pokud není zadáno ručně
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

    # Převod datových typů pro správné výpočty
    if not df_real.empty:
        df_real['Datum_Vysadby'] = pd.to_datetime(df_real['Datum_Vysadby']).dt.date
        df_real['Ocekavana_Sklizen'] = pd.to_datetime(df_real['Ocekavana_Sklizen']).dt.date
        df_real['Posledni_Hnojeni'] = pd.to_datetime(df_real['Posledni_Hnojeni']).dt.date
        dnes = datetime.now().date()
        df_real['Zbývá dní'] = df_real['Ocekavana_Sklizen'].apply(lambda x: (x - dnes).days if pd.notnull(x) else 0)

    st.title("🌱 Zahradní Manažer Pro")

    # --- 4. MRAZOVÝ RADAR (Analýza 120 hodin) ---
    current_temp = None
    if "weather" in st.secrets:
        api_key = st.secrets["weather"]["api_key"]
        city = st.secrets["weather"]["city"]
        curr, fore = get_weather_data(api_key, city)
        
        if curr and curr.get("cod") == 200:
            current_temp = curr['main']['temp']
            col_w1, col_w2 = st.columns([1, 4])
            col_w1.metric("Aktuálně Polánka", f"{current_temp} °C")
            
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
                    st.error(f"🚨 **VÝSTRAHA:** {worst['time'].strftime('%d.%m. %H:%M')} bude {worst['temp']}°C. Ohroženo: {', '.join(set(r['crop'] for r in forecast_risks))}")
                else:
                    st.success("🌤️ V příštích 5 dnech mráz tvou výsadbu neohrozí.")

    st.divider()

    # --- 5. TABY A UŽIVATELSKÉ ROZHRANÍ ---
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Plán & Živiny", "🗺️ Mapa", "⚙️ Správa", "📂 Archiv"])

    with tab1:
        st.header("📝 Přehled výsadby")
        if not df_real.empty:
            def style_rows(row):
                dnes = datetime.now().date()
                # Výpočet příštího hnojení
                start_date = row['Posledni_Hnojeni'] if pd.notnull(row['Posledni_Hnojeni']) else row['Datum_Vysadby']
                interval = row['Ucinnek_Hnojiva'] if pd.notnull(row['Ucinnek_Hnojiva']) and row['Ucinnek_Hnojiva'] > 0 else PLANT_DATABASE.get(row['Plodina'], {}).get("def_fert", 14)
                next_fert = start_date + timedelta(days=int(interval))
                
                # Styl pro vypršelé hnojivo (hnědá)
                if dnes >= next_fert:
                    return ['background-color: #4b2e2e; color: white'] * len(row)
                # Styl pro mráz (červená)
                if current_temp is not None:
                    limit = PLANT_DATABASE.get(row['Plodina'], {}).get("frost", 0)
                    if current_temp <= limit: return ['background-color: #721c24; color: white'] * len(row)
                return [''] * len(row)

            st.dataframe(df_real.style.apply(style_rows, axis=1), use_container_width=True, hide_index=True)
            st.info("💡 Hnědé řádky: Vypršelo hnojivo | Červené řádky: Teplota pod limitem plodiny.")
        else:
            st.info("Záhon je prázdný.")

    with tab2:
        st.header("📍 Vizuální mapa záhonů")
        for bed in BEDS:
            with st.expander(f"{bed}", expanded=True):
                for r in ROWS:
                    ui_cols = st.columns(len(COLS))
                    for i, c in enumerate(COLS):
                        pos = f"{r}{c}"
                        match = df_real[(df_real["Záhon"] == bed) & (df_real["Pozice"] == pos)] if not df_real.empty else pd.DataFrame()
                        with ui_cols[i]:
                            if not match.empty:
                                item = match.iloc[-1]
                                st.success(f"**{pos}**\n\n{item['Plodina']}")
                            else: st.info(f"**{pos}**\n\nVolno")

    with tab3:
        st.header("⚙️ Správa dat a hnojení")
        
        # Formulář pro přidání nové plodiny
        with st.form("add_form", clear_on_submit=True):
            st.subheader("➕ Nová plodina")
            c1, c2, c3 = st.columns(3)
            f_crop = c1.selectbox("Plodina", list(PLANT_DATABASE.keys()))
            f_bed = c2.selectbox("Záhon", BEDS)
            f_pos = c3.selectbox("Pozice", [f"{r}{c}" for r in ROWS for c in COLS])
            f_date = st.date_input("Datum výsadby", datetime.now())
            if st.form_submit_button("Uložit do systému"):
                sklizen = f_date + timedelta(days=PLANT_DATABASE[f_crop]["growth"])
                new_row = pd.DataFrame([{
                    "Plodina": f_crop, "Záhon": f_bed, "Pozice": f_pos, 
                    "Datum_Vysadby": f_date.strftime('%Y-%m-%d'), 
                    "Ocekavana_Sklizen": sklizen.strftime('%Y-%m-%d'),
                    "Posledni_Hnojeni": None, "Ucinnek_Hnojiva": 0, "Poznamka": ""
                }])
                clean_df = df_real.drop(columns=['Zbývá dní'], errors='ignore')
                conn.update(worksheet="Sheet1", data=pd.concat([clean_df, new_row], ignore_index=True))
                st.rerun()

        # Sekce pro hnojení a sklizně
        if not df_real.empty:
            st.divider()
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.subheader("🧪 Zapsat hnojení")
                target_idx = st.selectbox("Vyber plodinu", df_real.index, format_func=lambda x: f"{df_real.loc[x, 'Plodina']} ({df_real.loc[x, 'Pozice']})", key="fert_sel")
                f_dur = st.number_input("Účinek hnojiva (dny)", min_value=1, value=14)
                if st.button("Uložit hnojení"):
                    df_real.at[target_idx, 'Posledni_Hnojeni'] = datetime.now().date()
                    df_real.at[target_idx, 'Ucinnek_Hnojiva'] = f_dur
                    conn.update(worksheet="Sheet1", data=df_real.drop(columns=['Zbývá dní'], errors='ignore'))
                    st.success("Hnojení zapsáno!"); st.rerun()

            with col_b:
                st.subheader("🧺 Sklidit plodinu")
                h_idx = st.selectbox("Vyber ke sklizni", df_real.index, format_func=lambda x: f"{df_real.loc[x, 'Plodina']} ({df_real.loc[x, 'Pozice']})", key="harvest_sel")
                if st.button("Přesunout do archivu"):
                    row_to_arch = df_real.loc[[h_idx]].copy()
                    row_to_arch['Datum_Sklizne'] = datetime.now().date().strftime('%Y-%m-%d')
                    new_arch = pd.concat([df_archive, row_to_arch.drop(columns=['Zbývá dní'], errors='ignore')], ignore_index=True)
                    new_real = df_real.drop(h_idx).drop(columns=['Zbývá dní'], errors='ignore')
                    conn.update(worksheet="Archiv", data=new_arch)
                    conn.update(worksheet="Sheet1", data=new_real)
                    st.rerun()

    with tab4:
        st.header("📂 Archiv sklizně")
        if not df_archive.empty:
            st.dataframe(df_archive, use_container_width=True, hide_index=True)
            if st.button("Vymazat testovací data (Celý archiv)", type="secondary"):
                conn.update(worksheet="Archiv", data=pd.DataFrame(columns=df_archive.columns))
                st.rerun()
            
            st.subheader("🗑️ Smazat záznam z archivu")
            del_arch = st.selectbox("Vyber záznam", df_archive.index, format_func=lambda x: f"{df_archive.loc[x, 'Plodina']} ({df_archive.loc[x, 'Datum_Sklizne']})")
            if st.button("Definitivně smazat"):
                conn.update(worksheet="Archiv", data=df_archive.drop(del_arch))
                st.rerun()
        else:
            st.info("Archiv je zatím prázdný.")

if __name__ == "__main__":
    main()