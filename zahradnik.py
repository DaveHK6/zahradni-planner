import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# --- 1. POMOCNÉ FUNKCE (Počasí a UI) ---
def get_weather_data(api_key, city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=cz"
        res = requests.get(url, timeout=5).json()
        return res
    except Exception:
        return None

def main():
    st.set_page_config(page_title="Zahradní Manažer Pro", layout="wide", page_icon="🌱")
    
    # --- 2. KONFIGURACE DAT A SPOJENÍ ---
    MAIN_SHEET = "List 1"
    ARCHIVE_SHEET = "Archiv"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Načtení dat (List 1)
    try:
        df_real = conn.read(worksheet=MAIN_SHEET, ttl=0).dropna(how="all")
        # Konverze sloupců na datetime pro správné výpočty
        for col in ['Datum_Vysadby', 'Ocekavana_Sklizen', 'Posledni_Hnojeni']:
            if col in df_real.columns:
                df_real[col] = pd.to_datetime(df_real[col], errors='coerce')
    except:
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Posledni_Hnojeni", "Ucinnek_Hnojiva"])

    # Databáze plodin (Vzdělávání: Zde definujeme dny růstu)
    PLANT_DATABASE = {
        "Ředkvičky": {"growth": 30},
        "Jarní špenát": {"growth": 45},
        "Cuketa Tondo di Piacenza": {"growth": 70},
        "Zimní česnek": {"growth": 240},
        "Rajčata": {"growth": 90},
        "Keříčkové fazole": {"growth": 65},
        "Pak Choi / Mizuna": {"growth": 40}
    }

    # Seznam pozic pro skrolovací výběr
    POSITIONS = [f"{r}{c}" for r in list("ABCDEF") for c in [1, 2, 3]]

    # --- 3. HLAVIČKA A POČASÍ ---
    st.title("🌱 Zahradní Manažer Pro")
    if "weather" in st.secrets:
        w = get_weather_data(st.secrets["weather"]["api_key"], st.secrets["weather"]["city"])
        if w and "main" in w:
            st.metric(f"Aktuálně: {st.secrets['weather']['city']}", f"{w['main']['temp']} °C", help=w['weather'][0]['description'].capitalize())

    st.divider()

    # --- 4. TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Přehled výsadby", "🗺️ Mapa", "⚙️ Správa & Hnojení", "📂 Archiv"])

    with tab1:
        # --- ZÁHON 1 (Tvůj kompletní text) ---
        st.header("🏰 ZÁHON 1: Cuketové království")
        st.write("Tento záhon je zaměřen na rychlou jarní vitamínovou bombu a následně na hlavní letní úrodu.")
        st.markdown("""
        | Období | Plodina | Poznámka k pěstování |
        | :--- | :--- | :--- |
        | Březen – Květen | Ředkvičky + Jarní špenát | Vysévejte v polovině března. Přikryjte bílou netkanou textilií. |
        | Konec května – Září | Tykev cuketa Tondo di Piacenza | Po sklizni ředkviček vysaďte sazenice. Použijte Trichodermu a Blumaty. |
        | Září – Listopad | Polníček / Zimní špenát | Vydrží mráz, v říjnu máte skvělý salát. |
        """)

        # --- ZÁHON 2 (Tvůj kompletní text) ---
        st.header("🔄 ZÁHON 2: Česnekovo-fazolová rotace")
        st.write("Využívá fakt, že česnek uvolní místo v červenci pro 'druhou směnu' zeleniny.")
        st.markdown("""
        | Období | Plodina | Poznámka k pěstování |
        | :--- | :--- | :--- |
        | Listopad – Červenec | Zimní česnek | Sázíte na podzim, v červenci sklízíte vlastní palice. |
        | Červenec – Září | Sazenice rajčat + Keříčkové fazole | Do míst po česneku rajčata, do volných řádků fazole. |
        | Srpen – Říjen | Asijské saláty (Pak Choi / Mizuna) | Vysejte mezi fazole, rostou raketově. |
        """)

        st.info("**Tip pro 500 m n. m.:** Po česneku prolijte půdu Razorminem. Blumaty jsou pro rajčata nutnost!")
        
        st.divider()
        st.subheader("📊 Aktuální stav (Live data)")
        if not df_real.empty:
            df_display = df_real.copy()
            # Formátování data pro uživatele
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
        
        # --- NOVÁ VÝSADBA (Skrolovací pozice) ---
        st.subheader("➕ Nová výsadba")
        with st.form("add_form"):
            c1, c2, c3 = st.columns(3)
            p_crop = c1.selectbox("Plodina", list(PLANT_DATABASE.keys()))
            p_bed = c2.selectbox("Záhon", ["Záhon 1", "Záhon 2"])
            p_pos = c3.selectbox("Pozice", POSITIONS) # Skrolovací výběr pozice
            p_date = st.date_input("Datum výsadby", datetime.now())
            
            if st.form_submit_button("Zasadit"):
                days = PLANT_DATABASE[p_crop]["growth"]
                expected = pd.Timestamp(p_date) + timedelta(days=days)
                new_row = pd.DataFrame([{
                    "Plodina": p_crop, "Záhon": p_bed, "Pozice": p_pos,
                    "Datum_Vysadby": pd.Timestamp(p_date), "Ocekavana_Sklizen": expected,
                    "Ucinnek_Hnojiva": 14
                }])
                conn.update(worksheet=MAIN_SHEET, data=pd.concat([df_real, new_row], ignore_index=True))
                st.success("Uloženo!"); st.rerun()

        st.divider()
        # --- HNOJENÍ A MAZÁNÍ ---
        if not df_real.empty:
            st.subheader("🧪 Údržba")
            target_idx = st.selectbox("Vyber plodinu", df_real.index, 
                                     format_func=lambda x: f"{df_real.loc[x, 'Plodina']} ({df_real.loc[x, 'Pozice']})")
            
            cola, colb = st.columns(2)
            if cola.button("💧 Zapsat hnojení"):
                df_real.at[target_idx, 'Posledni_Hnojeni'] = pd.Timestamp(datetime.now())
                conn.update(worksheet=MAIN_SHEET, data=df_real)
                st.success("Hnojeno!"); st.rerun()
            
            if colb.button("🗑️ Smazat bez archivu"):
                conn.update(worksheet=MAIN_SHEET, data=df_real.drop(target_idx))
                st.warning("Smazáno."); st.rerun()

    with tab4:
        st.header("📂 Archiv")
        try:
            df_archive = conn.read(worksheet=ARCHIVE_SHEET, ttl=0)
            st.dataframe(df_archive, use_container_width=True, hide_index=True)
        except:
            st.info("Archiv je prázdný.")

if __name__ == "__main__":
    main()