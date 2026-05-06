import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# --- 1. POMOCNÉ FUNKCE ---
def get_weather_data(api_key, city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=cz"
        res = requests.get(url, timeout=5).json()
        return res
    except Exception:
        return None

def main():
    st.set_page_config(page_title="Zahradní Manažer Pro", layout="wide", page_icon="🌱")
    
    # --- 2. KONFIGURACE DAT ---
    MAIN_SHEET = "List 1"
    ARCHIVE_SHEET = "Archiv"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Načtení hlavních dat
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

    POSITIONS = [f"{r}{c}" for r in list("ABCDEF") for c in [1, 2, 3]]

    # --- 3. HLAVIČKA A POČASÍ ---
    st.title("🌱 Zahradní Manažer Pro")
    if "weather" in st.secrets:
        w = get_weather_data(st.secrets["weather"]["api_key"], st.secrets["weather"]["city"])
        if w and "main" in w:
            current_temp = w["main"]["temp"]
            st.metric(f"Aktuálně: {st.secrets['weather']['city']}", f"{current_temp} °C")
            if current_temp < 5.0:
                sensitive_planted = df_real[df_real["Plodina"].isin([k for k, v in PLANT_DATABASE.items() if v["sensitive"]])]
                if not sensitive_planted.empty:
                    st.error(f"⚠️ **POZOR NA MRÁZ!** Aktuální teplota je {current_temp}°C. Máš vysazeno: {', '.join(sensitive_planted['Plodina'].unique())}. Zakryj rostliny!")

    st.divider()

    # --- 4. TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Přehled výsadby", "🗺️ Mapa", "⚙️ Správa & Hnojení", "📂 Archiv"])

    with tab1:
        st.header("🏰 ZÁHON 1: Cuketové království")
        st.markdown("| Období | Plodina | Poznámka |\n| :--- | :--- | :--- |\n| Březen – Květen | Ředkvičky + Špenát | Vysévejte v březnu pod textilii. |")
        
        st.header("🔄 ZÁHON 2: Česnekovo-fazolová rotace")
        st.markdown("| Období | Plodina | Poznámka |\n| :--- | :--- | :--- |\n| Listopad – Červenec | Zimní česnek | Sázíte na podzim. |")
        
        st.divider()
        st.subheader("📊 Aktuální stav (Live data)")
        if not df_real.empty:
            df_display = df_real.copy()
            for col in ['Datum_Vysadby', 'Ocekavana_Sklizen', 'Posledni_Hnojeni']:
                if col in df_display.columns:
                    df_display[col] = df_display[col].dt.strftime('%d.%m.%Y').replace('NaT', '-')
            st.dataframe(df_display, use_container_width=True, hide_index=True)

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
        
        # Sekce pro přidání nové plodiny
        with st.form("add_form"):
            c1, c2, c3 = st.columns(3)
            p_crop = c1.selectbox("Plodina", list(PLANT_DATABASE.keys()))
            p_bed = c2.selectbox("Záhon", ["Záhon 1", "Záhon 2"])
            p_pos = c3.selectbox("Pozice", POSITIONS)
            p_date = st.date_input("Datum výsadby", datetime.now(), format="DD.MM.YYYY")
            
            if st.form_submit_button("Zasadit"):
                days = PLANT_DATABASE[p_crop]["growth"]
                expected = pd.Timestamp(p_date) + timedelta(days=days)
                new_row = pd.DataFrame([{
                    "Plodina": p_crop, "Záhon": p_bed, "Pozice": p_pos,
                    "Datum_Vysadby": pd.Timestamp(p_date), "Ocekavana_Sklizen": expected,
                    "Ucinnek_Hnojiva": 14
                }])
                conn.update(worksheet=MAIN_SHEET, data=pd.concat([df_real, new_row], ignore_index=True))
                st.success("Zasazeno!"); st.rerun()

        st.divider()
        
        # Sekce Údržba s novou funkcí ARCHIVACE
        if not df_real.empty:
            st.subheader("🧪 Údržba a Sklizeň")
            target_idx = st.selectbox("Vyber plodinu k akci", df_real.index, 
                                     format_func=lambda x: f"{df_real.loc[x, 'Plodina']} ({df_real.loc[x, 'Pozice']})")
            
            col_hnoj, col_skliz, col_smaz = st.columns(3)
            
            # 1. Hnojení
            if col_hnoj.button("💧 Zapsat hnojení"):
                df_real.at[target_idx, 'Posledni_Hnojeni'] = pd.Timestamp(datetime.now())
                conn.update(worksheet=MAIN_SHEET, data=df_real)
                st.success("Hnojeno!"); st.rerun()
            
            # 2. Sklizeň (Archivace)
            if col_skliz.button("🧺 Sklidit do archivu"):
                # Načtení archivu
                try:
                    df_archive = conn.read(worksheet=ARCHIVE_SHEET, ttl=0).dropna(how="all")
                except:
                    df_archive = pd.DataFrame()
                
                # Příprava řádku pro archiv
                row_to_archive = df_real.loc[[target_idx]].copy()
                row_to_archive['Datum_Sklizne'] = pd.Timestamp(datetime.now())
                
                # Update obou listů
                new_archive = pd.concat([df_archive, row_to_archive], ignore_index=True)
                conn.update(worksheet=ARCHIVE_SHEET, data=new_archive)
                conn.update(worksheet=MAIN_SHEET, data=df_real.drop(target_idx))
                
                st.balloons()
                st.success("Sklizeno a uloženo do archivu!"); st.rerun()
            
            # 3. Smazání
            if col_smaz.button("🗑️ Smazat (bez sklizně)"):
                conn.update(worksheet=MAIN_SHEET, data=df_real.drop(target_idx))
                st.warning("Odstraněno bez záznamu."); st.rerun()

    with tab4:
        st.header("📂 Archiv sklizní")
        try:
            df_archive = conn.read(worksheet=ARCHIVE_SHEET, ttl=0)
            if not df_archive.empty:
                # Formátování dat pro zobrazení
                for col in df_archive.columns:
                    if 'Datum' in col or 'Ocekavana' in col or 'Sklizne' in col:
                        df_archive[col] = pd.to_datetime(df_archive[col], errors='coerce').dt.strftime('%d.%m.%Y')
                st.dataframe(df_archive, use_container_width=True, hide_index=True)
        except:
            st.info("Archiv je zatím prázdný. Sklidit můžeš v záložce Správa.")

if __name__ == "__main__":
    main()