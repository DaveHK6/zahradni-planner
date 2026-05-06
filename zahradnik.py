import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# --- POMOCNÉ FUNKCE ---
def get_weather(api_key, city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=cz"
        response = requests.get(url)
        res = response.json()
        if res.get("cod") == 200:
            return res['main']['temp'], res['weather'][0]['description'], None
        else:
            return None, None, res.get("message", "Chyba API")
    except Exception as e:
        return None, None, str(e)

def main():
    st.set_page_config(page_title="Záhon Planner Pro", layout="wide", page_icon="🌱")
    
    # --- 1. PŘIPOJENÍ A NAČTENÍ DAT ---
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_real = conn.read(ttl=0).dropna(how="all")
    except Exception:
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Poznamka"])

    # --- 2. KONFIGURACE DAT ---
    GROWTH = {"Ředkvičky": 30, "Špenát": 45, "Cukety": 60, "Salát": 50, "Česnek": 240, "Rajčata": 80, "Fazole": 65, "Pak Choi": 40}
    
    # NOVÉ: Citlivost plodin na nízké teploty (v °C), pod kterými začíná problém
    FROST_SENSITIVITY = {
        "Rajčata": 7, 
        "Cukety": 5, 
        "Fazole": 5, 
        "Salát": 1, 
        "Ředkvičky": -2, 
        "Špenát": -5, 
        "Česnek": -10, 
        "Pak Choi": 2
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

    # --- 3. SEKCE POČASÍ A MRAZOVÉHO VAROVÁNÍ ---
    current_temp = None
    try:
        if "weather" in st.secrets:
            api_key = st.secrets["weather"]["api_key"]
            city = st.secrets["weather"]["city"]
            temp, desc, err = get_weather(api_key, city)
            current_temp = temp
            
            if temp is not None:
                col_w1, col_w2 = st.columns([1, 4])
                with col_w1:
                    st.metric("Teplota", f"{temp} °C")
                with col_w2:
                    # Logika hromadného varování
                    if temp < 5:
                        # Zjistíme, které plodiny z aktuálně vysázených jsou v ohrožení
                        active_crops = df_real['Plodina'].unique() if not df_real.empty else []
                        at_risk = [c for c in active_crops if temp <= FROST_SENSITIVITY.get(c, 0)]
                        
                        if at_risk:
                            st.error(f"⚠️ **POZOR:** Aktuální teplota {temp}°C ohrožuje: {', '.join(at_risk)}! Doporučujeme zakrýt textilií.")
                        else:
                            st.warning(f"❄️ Chladno ({temp}°C), ale tvá aktuální výsadba by měla být v bezpečí.")
                    else:
                        st.success(f"🌤️ V Polánce je {temp}°C ({desc}). Podmínky jsou ideální.")
    except Exception as e:
        st.info(f"Diagnostika počasí: {e}")

    st.divider()

    # --- 4. KONFIGURACE TABULEK ---
    column_cfg = {
        "Období": st.column_config.TextColumn("Období", width="small"),
        "Plodina": st.column_config.TextColumn("Plodina", width="medium"),
        "Poznámka": st.column_config.TextColumn("Poznámka", width="large"),
        "Poznamka": st.column_config.TextColumn("Poznamka", width="large")
    }

    tab1, tab2, tab3 = st.tabs(["📝 Plán & Realita", "🗺️ Mapa záhonů", "⚙️ Správa výsadby"])

    # LIST 1: Plán a Realita
    with tab1:
        st.header("📝 Kompletní osevní plán (500 m n. m.)")
        # [Zde zůstávají tvá data osevního plánu beze změny...]
        z1_data = [{"Období": "Březen–Květen", "Plodina": "Ředkvičky + Jarní špenát", "Poznámka": "Vysévejte v polovině března. Přikryjte bílou netkanou textilií."}]
        st.dataframe(pd.DataFrame(z1_data), hide_index=True, column_config=column_cfg, use_container_width=True)
        
        st.divider()
        st.subheader("📊 Aktuální stav výsadby")
        if not df_real.empty:
            # NOVÉ: Dynamické stylování řádků podle mrazu
            def style_frost_risk(row):
                styles = [''] * len(row)
                if current_temp is not None:
                    limit = FROST_SENSITIVITY.get(row['Plodina'], 0)
                    if current_temp <= limit:
                        # Pokud je teplota pod limitem plodiny, obarvíme celý řádek
                        return ['background-color: #721c24; color: white'] * len(row)
                return styles

            st.dataframe(df_real.style.apply(style_frost_risk, axis=1), 
                         column_config=column_cfg, use_container_width=True, hide_index=True)
        else:
            st.info("Zatím žádná data z Cloudu.")

    # [Zbytek kódu pro Mapu a Správu zůstává beze změny, jak bylo dohodnuto]
    # ... (Tab 2 a Tab 3) ...
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
                                # NOVÉ: Vizuální varování v mapě
                                is_danger = current_temp is not None and current_temp <= FROST_SENSITIVITY.get(item['Plodina'], 0)
                                if is_danger:
                                    st.error(f"**{pos}**: {item['Plodina']} ❄️\n\nPOZOR MRÁZ!")
                                else:
                                    st.success(f"**{pos}**: {item['Plodina']}\n\n💬 {item.get('Poznamka', '')}")
                            else:
                                st.info(f"**{pos}**\n\nVolno")

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