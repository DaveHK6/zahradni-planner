import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# --- 1. POMOCNÉ FUNKCE (Vzdělávání: Logika získávání dat) ---
def get_weather_data(api_key, city):
    """
    Tato funkce komunikuje s API OpenWeatherMap. 
    Získává 'weather' (aktuální stav) a 'forecast' (předpověď na 5 dní).
    """
    try:
        # Aktuální počasí pro dashboard
        curr_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=cz"
        curr_res = requests.get(curr_url).json()
        
        # Předpověď pro mrazový radar
        fore_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&lang=cz"
        fore_res = requests.get(fore_url).json()
        
        return curr_res, fore_res
    except Exception as e:
        return None, None

def main():
    # --- 2. KONFIGURACE STRÁNKY ---
    st.set_page_config(page_title="Záhon Planner Pro", layout="wide", page_icon="🌱")
    
    # --- 3. PŘIPOJENÍ A NAČTENÍ DAT (GSheets) ---
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_real = conn.read(ttl=0).dropna(how="all")
    except Exception:
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Poznamka"])

    # --- 4. KONFIGURACE DAT (CORE - Neměnný obsah) ---
    GROWTH = {"Ředkvičky": 30, "Špenát": 45, "Cukety": 60, "Salát": 50, "Česnek": 240, "Rajčata": 80, "Fazole": 65, "Pak Choi": 40}
    
    # Parametry citlivosti: Teplota, při které je nutná akce
    FROST_SENSITIVITY = {
        "Rajčata": 7, "Cukety": 5, "Fazole": 5, "Salát": 1, 
        "Ředkvičky": -2, "Špenát": -5, "Česnek": -10, "Pak Choi": 2
    }

    BEDS = ["Záhon 1", "Záhon 2"]
    ROWS = list("ABCDEF")
    COLS = [1, 2, 3]

    # Zpracování dat z tabulky
    if not df_real.empty:
        df_real['Datum_Vysadby'] = pd.to_datetime(df_real['Datum_Vysadby'], errors='coerce').dt.date
        df_real['Ocekavana_Sklizen'] = pd.to_datetime(df_real['Ocekavana_Sklizen'], errors='coerce').dt.date
        dnes = datetime.now().date()
        df_real['Zbývá dní'] = df_real['Ocekavana_Sklizen'].apply(lambda x: (x - dnes).days if pd.notnull(x) else 0)

    st.title("🌱 Zahradní Manažer Pro")

    # --- 5. MRAZOVÝ RADAR (Implementace předpovědi) ---
    current_temp = None
    try:
        if "weather" in st.secrets:
            api_key = st.secrets["weather"]["api_key"]
            city = st.secrets["weather"]["city"]
            curr, fore = get_weather_data(api_key, city)
            
            if curr and curr.get("cod") == 200:
                current_temp = curr['main']['temp']
                desc = curr['weather'][0]['description']
                
                # Horní lišta s aktuální teplotou
                col_w1, col_w2 = st.columns([1, 4])
                col_w1.metric("Teplota", f"{current_temp} °C")
                
                # Logika skenování předpovědi na 3 dny (72 hodin = 24 záznamů)
                active_crops = df_real['Plodina'].unique() if not df_real.empty else []
                forecast_risks = []
                
                if fore and fore.get("cod") == "200":
                    for entry in fore['list'][:24]:
                        f_temp = entry['main']['temp']
                        f_time = datetime.strptime(entry['dt_txt'], '%Y-%m-%d %H:%M:%S')
                        
                        for crop in active_crops:
                            limit = FROST_SENSITIVITY.get(crop, 0)
                            if f_temp <= limit:
                                forecast_risks.append({"crop": crop, "temp": f_temp, "time": f_time})

                # Zobrazení varovných hlášení
                if forecast_risks:
                    worst = min(forecast_risks, key=lambda x: x['temp'])
                    st.error(f"🚨 **MRAZOVÝ ALARM (Předpověď na 3 dny):** Pozor, hrozí pokles na {worst['temp']}°C "
                             f"dne {worst['time'].strftime('%d.%m. v %H:%M')}. "
                             f"Ohroženo: {', '.join(set(r['crop'] for r in forecast_risks))}")
                else:
                    st.success(f"🌤️ Aktuálně: {current_temp}°C ({desc}). V příštích 3 dnech mráz tvou výsadbu neohrozí.")
    except Exception as e:
        st.warning(f"Informace o počasí nejsou momentálně dostupné.")

    st.divider()

    # --- 6. KONFIGURACE ZOBRAZENÍ TABULEK ---
    column_cfg = {
        "Období": st.column_config.TextColumn("Období", width="small"),
        "Plodina": st.column_config.TextColumn("Plodina", width="medium"),
        "Poznámka": st.column_config.TextColumn("Poznámka", width="large")
    }

    tab1, tab2, tab3 = st.tabs(["📝 Plán & Realita", "🗺️ Mapa záhonů", "⚙️ Správa výsadby"])

    # LIST 1: Plán a Realita (Zachování core obsahu)
    with tab1:
        st.header("📝 Kompletní osevní plán (500 m n. m.)")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🟩 ZÁHON 1")
            z1_data = [
                {"Období": "Březen–Květen", "Plodina": "Ředkvičky + Jarní špenát", "Poznámka": "Vysévejte v polovině března. Přikryjte bílou netkanou textilií."},
                {"Období": "Konec května–Září", "Plodina": "Cuketa Tondo di Piacenza", "Poznámka": "Do jamky Trichodermu. Závlaha Blumat."},
                {"Období": "Září–Listopad", "Plodina": "Polníček / Zimní špenát", "Poznámka": "Po cuketách záhon nevynechejte. Vydrží mráz."}
            ]
            st.dataframe(pd.DataFrame(z1_data), hide_index=True, column_config=column_cfg, use_container_width=True)
        
        with c2:
            st.subheader("🟦 ZÁHON 2")
            z2_data = [
                {"Období": "Listopad–Červenec", "Plodina": "Zimní česnek", "Poznámka": "Sázíte na podzim, sklizeň v červenci."},
                {"Období": "Červenec–Září", "Plodina": "Rajčata + Keříčkové fazole", "Poznámka": "Do míst po česneku. Start s Razorminem."},
                {"Období": "Srpen–Říjen", "Plodina": "Asijské saláty (Pak Choi / Mizuna)", "Poznámka": "Rostou raketově mezi fazolemi."}
            ]
            st.dataframe(pd.DataFrame(z2_data), hide_index=True, column_config=column_cfg, use_container_width=True)
        
        st.divider()
        st.subheader("📊 Aktuální stav výsadby")
        if not df_real.empty:
            def style_rows(row):
                styles = [''] * len(row)
                # Prioritní barva pro mráz
                if current_temp is not None:
                    if current_temp <= FROST_SENSITIVITY.get(row['Plodina'], 0):
                        return ['background-color: #721c24; color: white'] * len(row)
                # Barva pro blížící se sklizeň
                try:
                    v = int(row['Zbývá dní'])
                    if v < 0: styles = ['background-color: #ff4b4b; color: white'] * len(row)
                    elif v <= 7: styles = ['background-color: #ffa500; color: black'] * len(row)
                except: pass
                return styles

            st.dataframe(df_real.style.apply(style_rows, axis=1), column_config=column_cfg, use_container_width=True, hide_index=True)
        else:
            st.info("Zatím žádná data z Cloudu.")

    # LIST 2: Mapa záhonů
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
                                is_danger = current_temp is not None and current_temp <= FROST_SENSITIVITY.get(item['Plodina'], 0)
                                if is_danger: st.error(f"**{pos}**: {item['Plodina']} ❄️")
                                else: st.success(f"**{pos}**: {item['Plodina']}")
                            else: st.info(f"**{pos}**\n\nVolno")

    # LIST 3: Správa výsadby
    with tab3:
        st.header("⚙️ Správa dat")
        with st.form("planting_form", clear_on_submit=True):
            f_crop = st.selectbox("Plodina", list(GROWTH.keys()))
            f_bed = st.selectbox("Záhon", BEDS)
            f_pos = st.selectbox("Pozice", [f"{r}{c}" for r in ROWS for c in COLS])
            f_date = st.date_input("Datum", datetime.now())
            f_note = st.text_input("Poznámka")
            if st.form_submit_button("Uložit výsadbu"):
                sklizen = f_date + timedelta(days=GROWTH[f_crop])
                new_data = pd.DataFrame([{"Plodina": f_crop, "Záhon": f_bed, "Pozice": f_pos, "Datum_Vysadby": f_date.strftime('%Y-%m-%d'), "Ocekavana_Sklizen": sklizen.strftime('%Y-%m-%d'), "Poznamka": f_note}])
                save_df = df_real.drop(columns=['Zbývá dní']) if 'Zbývá dní' in df_real.columns else df_real
                conn.update(data=pd.concat([save_df, new_data], ignore_index=True))
                st.success("Zapsáno!"); st.rerun()

if __name__ == "__main__":
    main()