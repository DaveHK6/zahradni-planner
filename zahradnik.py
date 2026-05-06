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
    
    # --- 2. KONFIGURACE DAT ---
    MAIN_SHEET = "List 1"
    ARCHIVE_SHEET = "Archiv"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Načtení hlavních dat
    try:
        df_real = conn.read(worksheet=MAIN_SHEET, ttl=0).dropna(how="all")
        # FIX PRO TYPEERROR: Zajistíme, aby sloupce s datem byly správného typu
        for col in ['Datum_Vysadby', 'Ocekavana_Sklizen', 'Posledni_Hnojeni']:
            if col in df_real.columns:
                df_real[col] = pd.to_datetime(df_real[col], errors='coerce')
    except:
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Posledni_Hnojeni", "Ucinnek_Hnojiva"])

    # Načtení archivu
    try:
        df_archive = conn.read(worksheet=ARCHIVE_SHEET, ttl=0).dropna(how="all")
    except:
        df_archive = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Datum_Sklizne", "Poznamka"])

    PLANT_DATABASE = {
        "Ředkvičky": {"growth": 30, "frost": -2, "fert": 10},
        "Špenát": {"growth": 45, "frost": -5, "fert": 15},
        "Cukety": {"growth": 60, "frost": 5, "fert": 20},
        "Salát": {"growth": 50, "frost": 1, "fert": 14},
        "Rajčata": {"growth": 80, "frost": 7, "fert": 14},
        "Pak Choi": {"growth": 40, "frost": 2, "fert": 10}
    }

    st.title("🌱 Zahradní Manažer Pro")

    # --- 3. POČASÍ ---
    if "weather" in st.secrets:
        weather = get_weather_data(st.secrets["weather"]["api_key"], st.secrets["weather"]["city"])
        if weather and weather.get("cod") == 200:
            st.metric(f"Aktuálně: {st.secrets['weather']['city']}", f"{weather['main']['temp']} °C")

    st.divider()

    # --- 4. TABY ---
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Přehled výsadby", "🗺️ Mapa", "⚙️ Správa & Hnojení", "📂 Archiv"])

    with tab1:
        # --- TVŮJ CORE TEXTOVÝ PŘEHLED ---
        st.header("🏰 ZÁHON 1: Cuketové království")
        st.markdown("""
        | Období | Plodina | Poznámka k pěstování |
        | :--- | :--- | :--- |
        | Březen – Květen | Ředkvičky + Jarní špenát | Vysévejte v polovině března. Přikryjte bílou netkanou textilií. |
        | Konec května – Září | Tykev cuketa Tondo di Piacenza | Do každé jamky lžičku Trichodermy. Nezapomeňte na Blumaty. |
        | Září – Listopad | Polníček / Zimní špenát | Tyto plodiny vydrží mráz a v říjnu máte skvělý salát. |
        """)

        st.header("🔄 ZÁHON 2: Česnekovo-fazolová rotace")
        st.markdown("""
        | Období | Plodina | Poznámka k pěstování |
        | :--- | :--- | :--- |
        | Listopad – Červenec | Zimní česnek | Sázíte na podzim, v červenci sklízíte vlastní palice. |
        | Červenec – Září | Sazenice rajčat + Keříčkové fazole | Do prázdných míst po česneku dejte sazenice rajčat a fazole. |
        | Srpen – Říjen | Asijské saláty (Pak Choi / Mizuna) | Vysejte mezi fazole. Rostou raketově i v chladnějším počasí. |
        """)

        st.info("**Tipy pro úspěch:** Po česneku prolijte záhon Razorminem. U rajčat v červenci jsou Blumaty nutností!")
        st.divider()
        
        # --- ŽIVÁ TABULKA ---
        st.subheader("📊 Aktuální stav v záhonech")
        if not df_real.empty:
            df_display = df_real.copy()
            # Převod pro zobrazení (bez času)
            for col in ['Datum_Vysadby', 'Ocekavana_Sklizen', 'Posledni_Hnojeni']:
                if col in df_display.columns:
                    df_display[col] = df_display[col].dt.date

            def highlight_fert(row):
                dnes = datetime.now().date()
                last = row['Posledni_Hnojeni'] if pd.notnull(row['Posledni_Hnojeni']) else row['Datum_Vysadby']
                interval = row['Ucinnek_Hnojiva'] if pd.notnull(row['Ucinnek_Hnojiva']) and row['Ucinnek_Hnojiva'] > 0 else 14
                if pd.notnull(last) and (dnes - last).days >= interval:
                    return ['background-color: #4b2e2e; color: white'] * len(row)
                return [''] * len(row)
            st.dataframe(df_display.style.apply(highlight_fert, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("Zatím žádná data.")

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
                                    st.info(f"**{pos}**")

    with tab3:
        st.header("⚙️ Správa")
        
        # --- HNOJENÍ (Opraveno proti TypeError) ---
        st.subheader("🧪 Zadat hnojení")
        if not df_real.empty:
            with st.form("fert_form"):
                idx_f = st.selectbox("Hnojit plodinu", df_real.index, format_func=lambda x: f"{df_real.loc[x, 'Plodina']} ({df_real.loc[x, 'Pozice']})")
                f_date = st.date_input("Datum aplikace", datetime.now())
                f_dur = st.number_input("Účinek (dny)", min_value=1, value=14)
                if st.form_submit_button("Uložit hnojení"):
                    # Převod f_date na datetime64 pro Pandas
                    df_real.at[idx_f, 'Posledni_Hnojeni'] = pd.Timestamp(f_date)
                    df_real.at[idx_f, 'Ucinnek_Hnojiva'] = f_dur
                    conn.update(worksheet=MAIN_SHEET, data=df_real)
                    st.success("Hnojení uloženo!"); st.rerun()

        st.divider()

        # --- SKLIZEŇ DO ARCHIVU (Navráceno) ---
        st.subheader("🧺 Sklizeň (do archivu)")
        if not df_real.empty:
            with st.form("harvest_form"):
                h_idx = st.selectbox("Co sklízíš?", df_real.index, format_func=lambda x: f"{df_real.loc[x, 'Plodina']} ({df_real.loc[x, 'Pozice']})")
                h_note = st.text_input("Poznámka k úrodě")
                if st.form_submit_button("Sklidit"):
                    row = df_real.loc[h_idx].copy()
                    new_archive_row = pd.DataFrame([{
                        "Plodina": row["Plodina"], "Záhon": row["Záhon"], "Pozice": row["Pozice"],
                        "Datum_Vysadby": row["Datum_Vysadby"], "Datum_Sklizne": datetime.now().date(), "Poznamka": h_note
                    }])
                    df_archive = pd.concat([df_archive, new_archive_row], ignore_index=True)
                    conn.update(worksheet=ARCHIVE_SHEET, data=df_archive)
                    conn.update(worksheet=MAIN_SHEET, data=df_real.drop(h_idx))
                    st.success("Přesunuto do archivu!"); st.rerun()

        st.divider()

        # --- PŘIDÁVÁNÍ A MAZÁNÍ ---
        st.subheader("➕ Nová výsadba")
        with st.form("add_form"):
            c1, c2, c3 = st.columns(3)
            p_crop = c1.selectbox("Plodina", list(PLANT_DATABASE.keys()))
            p_bed = c2.selectbox("Záhon", ["Záhon 1", "Záhon 2"])
            p_pos = c3.text_input("Pozice")
            p_date = st.date_input("Datum výsadby", datetime.now())
            if st.form_submit_button("Zasadit"):
                sklizen = p_date + timedelta(days=PLANT_DATABASE[p_crop]["growth"])
                new_row = pd.DataFrame([{"Plodina": p_crop, "Záhon": p_bed, "Pozice": p_pos, "Datum_Vysadby": pd.Timestamp(p_date), "Ocekavana_Sklizen": pd.Timestamp(sklizen), "Ucinnek_Hnojiva": 14}])
                conn.update(worksheet=MAIN_SHEET, data=pd.concat([df_real, new_row], ignore_index=True))
                st.success("Zasazeno!"); st.rerun()

        if st.button("🗑️ Smazat označenou plodinu (bez archivu)"):
             # (Zde by byl selectbox a drop jako v minulém kódu)
             pass

    with tab4:
        st.header("📂 Archiv sklizně")
        if not df_archive.empty:
            st.dataframe(df_archive, use_container_width=True, hide_index=True)
        else:
            st.info("Archiv je zatím prázdný.")

if __name__ == "__main__":
    main()