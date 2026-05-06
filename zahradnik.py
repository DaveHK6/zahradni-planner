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
        return curr_res
    except:
        return None

def main():
    st.set_page_config(page_title="Zahradní Manažer Pro", layout="wide", page_icon="🌱")
    
    # --- 2. KONFIGURACE DAT (Respektujeme 'List 1') ---
    MAIN_SHEET = "List 1"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        df_real = conn.read(worksheet=MAIN_SHEET, ttl=0).dropna(how="all")
    except:
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Posledni_Hnojeni", "Ucinnek_Hnojiva"])

    PLANT_DATABASE = {
        "Ředkvičky": {"growth": 30, "frost": -2, "fert": 10},
        "Špenát": {"growth": 45, "frost": -5, "fert": 15},
        "Cukety": {"growth": 60, "frost": 5, "fert": 20},
        "Salát": {"growth": 50, "frost": 1, "fert": 14},
        "Rajčata": {"growth": 80, "frost": 7, "fert": 14},
        "Pak Choi": {"growth": 40, "frost": 2, "fert": 10}
    }

    # Předzpracování dat
    if not df_real.empty:
        for col in ['Datum_Vysadby', 'Ocekavana_Sklizen', 'Posledni_Hnojeni']:
            if col in df_real.columns:
                df_real[col] = pd.to_datetime(df_real[col], errors='coerce').dt.date

    st.title("🌱 Zahradní Manažer Pro")

    # --- 3. POČASÍ ---
    if "weather" in st.secrets:
        weather = get_weather_data(st.secrets["weather"]["api_key"], st.secrets["weather"]["city"])
        if weather and weather.get("cod") == 200:
            st.metric(f"Aktuálně: {st.secrets['weather']['city']}", f"{weather['main']['temp']} °C")

    st.divider()

    # --- 4. TABY ---
    tab1, tab2, tab3 = st.tabs(["📝 Přehled výsadby", "🗺️ Mapa", "⚙️ Správa & Hnojení"])

    with tab1:
        # --- TVŮJ CORE TEXTOVÝ PŘEHLED (Statický obsah) ---
        st.header("🏰 ZÁHON 1: Cuketové království")
        st.write("Tento záhon je zaměřen na rychlou jarní vitamínovou bombu a následně na hlavní letní úrodu.")
        
        st.markdown("""
        | Období | Plodina | Poznámka k pěstování |
        | :--- | :--- | :--- |
        | Březen – Květen | Ředkvičky + Jarní špenát | Vysévejte v polovině března. Přikryjte bílou netkanou textilií. |
        | Konec května – Září | Tykev cuketa Tondo di Piacenza | Po sklizni ředkviček vysaďte sazenice. Použijte Trichodermu a Blumaty. |
        | Září – Listopad | Polníček / Zimní špenát | Po cuketách záhon nevynechejte, vydrží i mráz. |
        """)

        st.header("🔄 ZÁHON 2: Česnekovo-fazolová rotace")
        st.write("Využívá fakt, že česnek uvolní místo v červenci pro druhou směnu zeleniny.")

        st.markdown("""
        | Období | Plodina | Poznámka k pěstování |
        | :--- | :--- | :--- |
        | Listopad – Červenec | Zimní česnek | Sázíte na podzim, v červenci sklízíte vlastní palice. |
        | Červenec – Září | Sazenice rajčat + Keříčkové fazole | Do prázdných míst po česneku dejte rajčata a fazole. |
        | Srpen – Říjen | Asijské saláty (Pak Choi / Mizuna) | Vysejte mezi fazole, rostou raketově. |
        """)

        st.info("""
        **Tipy pro úspěch v 500 m n. m.**
        1. **Po sklizni česneku (Červenec):** Prolijte záhon Razorminem pro bleskový start rajčat a fazolí.
        2. **Strategie pro rajčata:** Blumat adaptéry jsou nutností pro rychlé dozrání v září.
        3. **Co dál?** Skvěle se daří i černé ředkvi nebo vodnici – prevence proti rýmě z hor!
        
        *Můj tip: Jednu kulatou cuketu nechte vyrůst v obří kouli, vydrží ve sklepě až do Vánoc!*
        """)

        st.divider()
        
        # --- DYNAMICKÁ TABULKA S DATY (Z List 1) ---
        st.subheader("📊 Aktuální stav v záhonech (Live data)")
        if not df_real.empty:
            def highlight_fert(row):
                dnes = datetime.now().date()
                last = row['Posledni_Hnojeni'] if pd.notnull(row['Posledni_Hnojeni']) else row['Datum_Vysadby']
                interval = row['Ucinnek_Hnojiva'] if pd.notnull(row['Ucinnek_Hnojiva']) and row['Ucinnek_Hnojiva'] > 0 else 14
                if pd.notnull(last) and (dnes - last).days >= interval:
                    return ['background-color: #4b2e2e; color: white'] * len(row)
                return [''] * len(row)
            st.dataframe(df_real.style.apply(highlight_fert, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("Žádná živá data v tabulce. Přidej první plodinu v záložce Správa.")

    with tab2:
        st.header("🗺️ Mapa")
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

    with tab3:
        st.header("⚙️ Správa")
        # --- SEKCE HNOJENÍ ---
        st.subheader("🧪 Záznam hnojení")
        if not df_real.empty:
            with st.form("fert_form"):
                idx_f = st.selectbox("Hnojit plodinu", df_real.index, format_func=lambda x: f"{df_real.loc[x, 'Plodina']} ({df_real.loc[x, 'Pozice']})")
                f_date = st.date_input("Datum", datetime.now())
                f_dur = st.number_input("Účinek (dny)", min_value=1, value=14)
                if st.form_submit_button("Uložit hnojení"):
                    df_real.at[idx_f, 'Posledni_Hnojeni'] = f_date
                    df_real.at[idx_f, 'Ucinnek_Hnojiva'] = f_dur
                    conn.update(worksheet=MAIN_SHEET, data=df_real)
                    st.success("Hnojení uloženo!"); st.rerun()

        st.divider()
        # --- SEKCE PŘIDÁVÁNÍ ---
        st.subheader("➕ Nová výsadba")
        with st.form("add_form"):
            c1, c2, c3 = st.columns(3)
            p_crop = c1.selectbox("Plodina", list(PLANT_DATABASE.keys()))
            p_bed = c2.selectbox("Záhon", ["Záhon 1", "Záhon 2"])
            p_pos = c3.text_input("Pozice (A1-F3)")
            p_date = st.date_input("Datum výsadby", datetime.now())
            if st.form_submit_button("Zasadit"):
                sklizen = p_date + timedelta(days=PLANT_DATABASE[p_crop]["growth"])
                new_data = pd.DataFrame([{"Plodina": p_crop, "Záhon": p_bed, "Pozice": p_pos, "Datum_Vysadby": p_date, "Ocekavana_Sklizen": sklizen, "Ucinnek_Hnojiva": 14}])
                updated_df = pd.concat([df_real, new_data], ignore_index=True)
                conn.update(worksheet=MAIN_SHEET, data=updated_df)
                st.success("Přidáno!"); st.rerun()

        st.divider()
        # --- SEKCE MAZÁNÍ ---
        st.subheader("🗑️ Odstranit plodinu")
        if not df_real.empty:
            delete_idx = st.selectbox("Vyber plodinu k odstranění", df_real.index, format_func=lambda x: f"{df_real.loc[x, 'Plodina']} ({df_real.loc[x, 'Pozice']})")
            if st.button("Definitivně smazat"):
                new_df = df_real.drop(delete_idx)
                conn.update(worksheet=MAIN_SHEET, data=new_df)
                st.success("Odstraněno."); st.rerun()

if __name__ == "__main__":
    main()