import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# --- 1. POMOCNÉ FUNKCE (LOGIKA A DATA) ---

def get_weather_data(api_key, city):
    """Získává rozšířená data o počasí z OpenWeatherMap."""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=cz"
        res = requests.get(url, timeout=5).json()
        if res.get("cod") != 200:
            return None
        return res
    except Exception:
        return None

def update_db(conn, sheet_name, data):
    """Jednotný zápis do Google Sheets."""
    conn.update(worksheet=sheet_name, data=data)

def archive_plant(conn, main_df, arch_df, target_idx, main_sheet, arch_sheet):
    """Přesun plodiny do archivu se zapsáním data sklizně."""
    row = main_df.loc[[target_idx]].copy()
    row['Datum_Sklizne'] = pd.Timestamp(datetime.now())
    updated_arch = pd.concat([arch_df, row], ignore_index=True)
    update_db(conn, arch_sheet, updated_arch)
    update_db(conn, main_sheet, main_df.drop(target_idx))
    st.balloons()

# --- 2. HLAVNÍ APLIKACE ---

def main():
    st.set_page_config(page_title="Zahradní Manažer Pro", layout="wide", page_icon="🌱")
    
    # Konfigurace
    MAIN_SHEET = "List 1"
    ARCHIVE_SHEET = "Archiv"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Načtení dat
    try:
        df_real = conn.read(worksheet=MAIN_SHEET, ttl=0).dropna(how="all")
        for col in ['Datum_Vysadby', 'Ocekavana_Sklizen', 'Posledni_Hnojeni']:
            if col in df_real.columns:
                df_real[col] = pd.to_datetime(df_real[col], dayfirst=True, errors='coerce')
    except:
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Posledni_Hnojeni", "Ucinnek_Hnojiva"])

    PLANT_DATABASE = {
        "Ředkvičky": {"growth": 30, "sensitive": False},
        "Jarní špenát": {"growth": 45, "sensitive": False},
        "Cuketa Tondo di Piacenza": {"growth": 70, "sensitive": True},
        "Zimní česnek": {"growth": 240, "sensitive": False},
        "Rajčata": {"growth": 90, "sensitive": True},
        "Keříčkové fazole": {"growth": 65, "sensitive": True},
        "Pak Choi / Mizuna": {"growth": 40, "sensitive": False}
    }

    # --- 3. VYLEPŠENÝ MODUL POČASÍ ---
    st.title("🌱 Zahradní Manažer Pro")
    
    if "weather" in st.secrets:
        w = get_weather_data(st.secrets["weather"]["api_key"], st.secrets["weather"]["city"])
        if w:
            temp = w["main"]["temp"]
            hum = w["main"]["humidity"]
            wind = w["wind"]["speed"]
            desc = w["weather"][0]["description"]
            icon = w["weather"][0]["icon"]

            # Horní lišta s metrikami
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Teplota", f"{temp} °C")
            c2.metric("Vlhkost", f"{hum} %")
            c3.metric("Vítr", f"{wind} m/s")
            c4.write(f"**Stav:** {desc.capitalize()}")
            c4.image(f"http://openweathermap.org/img/wn/{icon}.png")

            # Inteligentní logika doporučení
            with st.container():
                # Varování před mrazem
                if temp < 5.0:
                    sensitive = [k for k, v in PLANT_DATABASE.items() if v["sensitive"]]
                    if not df_real[df_real["Plodina"].isin(sensitive)].empty:
                        st.error(f"❄️ **Kritické varování:** Teplota {temp}°C! Zakryj rajčata a cukety textilií.")
                
                # Varování před suchem
                elif temp > 25.0 and hum < 40:
                    st.warning("☀️ **Pozor na sucho:** Je horko a suchý vzduch. Zkontroluj hladinu vody v sudech a Blumaty.")
                
                # Varování před větrem
                if wind > 10.0:
                    st.info("💨 **Silný vítr:** Zkontroluj opory u rajčat, hrozí polámání.")

    st.divider()

    # --- 4. TABS (Zbytek aplikace zůstává kompletní) ---
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Přehled výsadby", "🗺️ Mapa", "⚙️ Správa & Hnojení", "📂 Archiv"])

    with tab1:
        st.header("🏰 ZÁHON 1: Cuketové království")
        st.markdown("| Období | Plodina | Poznámka |\n| :--- | :--- | :--- |\n| Březen – Květen | Ředkvičky + Špenát | Vysévejte v březnu. |")
        
        st.header("🔄 ZÁHON 2: Česnekovo-fazolová rotace")
        st.markdown("| Období | Plodina | Poznámka |\n| :--- | :--- | :--- |\n| Listopad – Červenec | Zimní česnek | Sklizeň v červenci. |")
        
        if not df_real.empty:
            st.subheader("📊 Aktuální stav (Live data)")
            df_disp = df_real.copy()
            for col in ['Datum_Vysadby', 'Ocekavana_Sklizen', 'Posledni_Hnojeni']:
                if col in df_disp.columns:
                    df_disp[col] = df_disp[col].dt.strftime('%d.%m.%Y').replace('NaT', '-')
            st.dataframe(df_disp, use_container_width=True, hide_index=True)

    with tab2:
        st.header("🗺️ Mapa osázení")
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
                                st.info(f"**{pos}**")

    with tab3:
        st.header("⚙️ Správa")
        # Formulář pro novou výsadbu
        with st.form("new_p"):
            c1, c2, c3 = st.columns(3)
            p_crop = c1.selectbox("Plodina", list(PLANT_DATABASE.keys()))
            p_bed = c2.selectbox("Záhon", ["Záhon 1", "Záhon 2"])
            p_pos = c3.selectbox("Pozice", [f"{r}{c}" for r in "ABCDEF" for c in [1,2,3]])
            p_date = st.date_input("Datum", datetime.now())
            if st.form_submit_button("Zasadit"):
                expected = pd.Timestamp(p_date) + timedelta(days=PLANT_DATABASE[p_crop]["growth"])
                new_row = pd.DataFrame([{"Plodina": p_crop, "Záhon": p_bed, "Pozice": p_pos, "Datum_Vysadby": pd.Timestamp(p_date), "Ocekavana_Sklizen": expected, "Ucinnek_Hnojiva": 14}])
                update_db(conn, MAIN_SHEET, pd.concat([df_real, new_row], ignore_index=True))
                st.rerun()

        # Údržba a Sklizeň
        if not df_real.empty:
            st.divider()
            target = st.selectbox("Vyber plodinu k akci", df_real.index, format_func=lambda x: f"{df_real.loc[x, 'Plodina']} ({df_real.loc[x, 'Pozice']})")
            h, s, d = st.columns(3)
            if h.button("💧 Hnojit"):
                df_real.at[target, 'Posledni_Hnojeni'] = pd.Timestamp(datetime.now())
                update_db(conn, MAIN_SHEET, df_real)
                st.rerun()
            if s.button("🧺 Sklidit"):
                try: df_arch = conn.read(worksheet=ARCHIVE_SHEET, ttl=0).dropna(how="all")
                except: df_arch = pd.DataFrame()
                archive_plant(conn, df_real, df_arch, target, MAIN_SHEET, ARCHIVE_SHEET)
                st.rerun()
            if d.button("🗑️ Smazat"):
                update_db(conn, MAIN_SHEET, df_real.drop(target))
                st.rerun()

    with tab4:
        st.header("📂 Archiv")
        try:
            df_arch_disp = conn.read(worksheet=ARCHIVE_SHEET, ttl=0)
            if not df_arch_disp.empty:
                for col in df_arch_disp.columns:
                    if any(x in col for x in ['Datum', 'Ocekavana', 'Sklizne']):
                        df_arch_disp[col] = pd.to_datetime(df_arch_disp[col], errors='coerce').dt.strftime('%d.%m.%Y')
                st.dataframe(df_arch_disp, use_container_width=True, hide_index=True)
        except: st.info("Archiv je prázdný.")

if __name__ == "__main__":
    main()