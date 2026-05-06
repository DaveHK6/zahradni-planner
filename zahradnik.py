import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# --- 1. POMOCNÉ FUNKCE ---
def get_weather_data(api_key, city):
    """Získává aktuální data a předpověď z OpenWeatherMap (5 dní / 3 hodiny)."""
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
    
    # --- 2. PŘIPOJENÍ K DATŮM ---
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_real = conn.read(ttl=0).dropna(how="all")
    except Exception:
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Poznamka"])

    # --- 3. INTELIGENTNÍ DATABÁZE PLODIN (Vlastní limity) ---
    PLANT_DATABASE = {
        "Ředkvičky": {"growth": 30, "frost": -2},
        "Špenát": {"growth": 45, "frost": -5},
        "Cukety": {"growth": 60, "frost": 5},
        "Salát": {"growth": 50, "frost": 1},
        "Česnek": {"growth": 240, "frost": -10},
        "Rajčata": {"growth": 80, "frost": 7},
        "Fazole": {"growth": 65, "frost": 5},
        "Pak Choi": {"growth": 40, "frost": 2}
    }

    BEDS = ["Záhon 1", "Záhon 2"]
    ROWS = list("ABCDEF")
    COLS = [1, 2, 3]

    if not df_real.empty:
        df_real['Datum_Vysadby'] = pd.to_datetime(df_real['Datum_Vysadby'], errors='coerce').dt.date
        df_real['Ocekavana_Sklizen'] = pd.to_datetime(df_real['Ocekavana_Sklizen'], errors='coerce').dt.date
        dnes = datetime.now().date()
        df_real['Zbývá dní'] = df_real['Ocekavana_Sklizen'].apply(lambda x: (x - dnes).days if pd.notnull(x) else 0)

    st.title("🌱 Zahradní Manažer Pro")

    # --- 4. MRAZOVÝ RADAR (Předpověď na 5 DNÍ) ---
    current_temp = None
    try:
        if "weather" in st.secrets:
            api_key = st.secrets["weather"]["api_key"]
            city = st.secrets["weather"]["city"]
            curr, fore = get_weather_data(api_key, city)
            
            if curr and curr.get("cod") == 200:
                current_temp = curr['main']['temp']
                col_w1, col_w2 = st.columns([1, 4])
                col_w1.metric("Teplota", f"{current_temp} °C")
                
                active_crops = df_real['Plodina'].unique() if not df_real.empty else []
                forecast_risks = []
                
                if fore and fore.get("cod") == "200":
                    # ZMĚNA: Prověřujeme 40 záznamů (5 dní), co API dovolí
                    for entry in fore['list'][:40]: 
                        f_temp = entry['main']['temp']
                        f_time = datetime.strptime(entry['dt_txt'], '%Y-%m-%d %H:%M:%S')
                        for crop in active_crops:
                            limit = PLANT_DATABASE.get(crop, {}).get("frost", 0)
                            if f_temp <= limit:
                                forecast_risks.append({"crop": crop, "temp": f_temp, "time": f_time})

                if forecast_risks:
                    worst = min(forecast_risks, key=lambda x: x['temp'])
                    st.error(f"🚨 **DLOUHODOBÁ VÝSTRAHA (5 DNÍ):** Pozor na {worst['time'].strftime('%d.%m. %H:%M')}. "
                             f"Teplota klesne na {worst['temp']}°C. Ohroženo: {', '.join(set(r['crop'] for r in forecast_risks))}")
                else:
                    st.success(f"🌤️ V příštích 5 dnech vypadá předpověď pro tvou zahradu bezpečně.")
    except:
        pass

    st.divider()

    # --- 5. ZOBRAZENÍ TABULEK ---
    column_cfg = {"Období": st.column_config.TextColumn("Období", width="small"), "Plodina": st.column_config.TextColumn("Plodina", width="medium"), "Poznámka": st.column_config.TextColumn("Poznámka", width="large")}
    tab1, tab2, tab3 = st.tabs(["📝 Plán & Realita", "🗺️ Mapa záhonů", "⚙️ Správa výsadby"])

    with tab1:
        st.header("📝 Kompletní osevní plán (500 m n. m.)")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🟩 ZÁHON 1")
            z1_data = [{"Období": "Březen–Květen", "Plodina": "Ředkvičky + Jarní špenát", "Poznámka": "Vysévejte v polovině března. Přikryjte bílou netkanou textilií."}, {"Období": "Konec května–Září", "Plodina": "Cuketa Tondo di Piacenza", "Poznámka": "Do jamky Trichodermu. Závlaha Blumat."}, {"Období": "Září–Listopad", "Plodina": "Polníček / Zimní špenát", "Poznámka": "Vydrží mráz."}]
            st.dataframe(pd.DataFrame(z1_data), hide_index=True, column_config=column_cfg, use_container_width=True)
        with c2:
            st.subheader("🟦 ZÁHON 2")
            z2_data = [{"Období": "Listopad–Červenec", "Plodina": "Zimní česnek", "Poznámka": "Sázíte na podzim, sklizeň v červenci."}, {"Období": "Červenec–Září", "Plodina": "Rajčata + Keříčkové fazole", "Poznámka": "Do míst po česneku. Start s Razorminem."}, {"Období": "Srpen–Říjen", "Plodina": "Asijské saláty (Pak Choi / Mizuna)", "Poznámka": "Rostou raketově mezi fazolemi."}]
            st.dataframe(pd.DataFrame(z2_data), hide_index=True, column_config=column_cfg, use_container_width=True)
        
        st.divider()
        st.subheader("📊 Aktuální stav výsadby")
        if not df_real.empty:
            def style_rows(row):
                if current_temp is not None:
                    limit = PLANT_DATABASE.get(row['Plodina'], {}).get("frost", 0)
                    if current_temp <= limit: return ['background-color: #721c24; color: white'] * len(row)
                return [''] * len(row)
            st.dataframe(df_real.style.apply(style_rows, axis=1), column_config=column_cfg, use_container_width=True, hide_index=True)
        else:
            st.info("Zatím žádná data z Cloudu.")

    with tab2:
        st.header("📍 Vizuální mapa")
        for bed in BEDS:
            with st.expander(f"Mřížka: {bed}", expanded=True):
                for r in ROWS:
                    ui_cols = st.columns(len(COLS))
                    for i, c in enumerate(COLS):
                        pos = f"{r}{c}"
                        match = df_real[(df_real["Záhon"] == bed) & (df_real["Pozice"] == pos)] if not df_real.empty else pd.DataFrame()
                        with ui_cols[i]:
                            if not match.empty:
                                item = match.iloc[-1]
                                limit = PLANT_DATABASE.get(item['Plodina'], {}).get("frost", 0)
                                danger = current_temp is not None and current_temp <= limit
                                if danger: st.error(f"**{pos}**: {item['Plodina']} ❄️")
                                else: st.success(f"**{pos}**: {item['Plodina']}")
                            else: st.info(f"**{pos}**\n\nVolno")

    with tab3:
        st.header("⚙️ Správa dat")
        with st.form("planting_form", clear_on_submit=True):
            f_crop = st.selectbox("Plodina", list(PLANT_DATABASE.keys()))
            f_bed = st.selectbox("Záhon", BEDS)
            f_pos = st.selectbox("Pozice", [f"{r}{c}" for r in ROWS for c in COLS])
            f_date = st.date_input("Datum výsadby", datetime.now())
            f_note = st.text_input("Poznámka")
            if st.form_submit_button("Uložit výsadbu"):
                days_to_grow = PLANT_DATABASE[f_crop]["growth"]
                sklizen = f_date + timedelta(days=days_to_grow)
                new_data = pd.DataFrame([{"Plodina": f_crop, "Záhon": f_bed, "Pozice": f_pos, "Datum_Vysadby": f_date.strftime('%Y-%m-%d'), "Ocekavana_Sklizen": sklizen.strftime('%Y-%m-%d'), "Poznamka": f_note}])
                save_df = df_real.drop(columns=['Zbývá dní']) if 'Zbývá dní' in df_real.columns else df_real
                conn.update(data=pd.concat([save_df, new_data], ignore_index=True))
                st.success(f"Zapsáno! Sklizeň: {sklizen.strftime('%d.%m.%Y')}"); st.rerun()

        if not df_real.empty:
            st.divider()
            st.subheader("🗑️ Odstranit záznam")
            del_list = [f"{i}: {row['Plodina']} ({row['Záhon']} - {row['Pozice']})" for i, row in df_real.iterrows()]
            selected_del = st.selectbox("Vyber záznam ke smazání", del_list)
            if st.button("Smazat vybraný záznam", type="primary"):
                idx_to_del = int(selected_del.split(":")[0])
                new_df = df_real.drop(df_real.index[idx_to_del])
                if 'Zbývá dní' in new_df.columns: new_df = new_df.drop(columns=['Zbývá dní'])
                conn.update(data=new_df)
                st.success("Smazáno!"); st.rerun()

if __name__ == "__main__":
    main()