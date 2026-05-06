import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# --- 1. POMOCNÉ FUNKCE ---
def get_weather_data(api_key, city):
    try:
        # Přidáno ošetření pro korektní URL a jednotky
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

    # Načtení dat s vynucením typů (prevence 'None' a chyb v datu)
    try:
        df_real = conn.read(worksheet=MAIN_SHEET, ttl=0).dropna(how="all")
        for col in ['Datum_Vysadby', 'Ocekavana_Sklizen', 'Posledni_Hnojeni']:
            if col in df_real.columns:
                df_real[col] = pd.to_datetime(df_real[col], errors='coerce')
    except:
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Posledni_Hnojeni", "Ucinnek_Hnojiva"])

    # Databáze plodin s opravenými časy růstu
    PLANT_DATABASE = {
        "Ředkvičky": {"growth": 30},
        "Jarní špenát": {"growth": 45},
        "Cuketa Tondo di Piacenza": {"growth": 70},
        "Zimní česnek": {"growth": 240},
        "Rajčata": {"growth": 90},
        "Keříčkové fazole": {"growth": 65},
        "Pak Choi / Mizuna": {"growth": 40}
    }

    # Generování seznamu pozic (A1, A2, A3, B1...)
    POSITIONS = [f"{r}{c}" for r in list("ABCDEF") for c in [1, 2, 3]]

    # --- 3. POČASÍ ---
    st.title("🌱 Zahradní Manažer Pro")
    if "weather" in st.secrets:
        w_data = get_weather_data(st.secrets["weather"]["api_key"], st.secrets["weather"]["city"])
        if w_data and "main" in w_data:
            temp = w_data["main"]["temp"]
            desc = w_data["weather"][0]["description"]
            st.metric(f"Aktuálně: {st.secrets['weather']['city']}", f"{temp} °C", help=desc.capitalize())

    st.divider()

    # --- 4. TABY ---
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Přehled výsadby", "🗺️ Mapa", "⚙️ Správa & Hnojení", "📂 Archiv"])

    with tab1:
        # --- KOMPLETNÍ TEXTY (CORE OBSAH) ---
        st.header("🏰 ZÁHON 1: Cuketové království")
        st.write("Tento záhon je zaměřen na rychlou jarní vitamínovou bombu a následně na hlavní letní úrodu.")
        st.markdown("""
        | Období | Plodina | Poznámka k pěstování |
        | :--- | :--- | :--- |
        | Březen – Květen | Ředkvičky + Jarní špenát | Vysévejte v polovině března. Přikryjte bílou netkanou textilií – v 500 m n. m. jim vytvoří mikroklima. |
        | Konec května – Září | Tykev cuketa Tondo di Piacenza | Po sklizni ředkviček vysaďte sazenice. Do každé jamky lžičku Trichodermy. Nezapomeňte na PET lahve s Blumatem. |
        | Září – Listopad | Polníček / Zimní špenát | Po cuketách záhon nevynechejte. Tyto plodiny vydrží mráz a v říjnu z nich máte skvělý salát. |
        """)

        st.header("🔄 ZÁHON 2: Česnekovo-fazolová rotace")
        st.write("Tento záhon využívá fakt, že česnek uvolní místo v červenci, což otevírá prostor pro 'druhou směnu' letní zeleniny.")
        st.markdown("""
        | Období | Plodina | Poznámka k pěstování |
        | :--- | :--- | :--- |
        | Listopad – Červenec | Zimní česnek | Sázíte na podzim. Přes zimu o něm nevíte, v červenci sklízíte vlastní palice. |
        | Červenec – Září | Sazenice rajčat + Keříčkové fazole | Do prázdných míst po česneku dejte už vzrostlé sazenice rajčat a do volných řádků vysejte fazole. |
        | Srpen – Říjen | Asijské saláty (Pak Choi / Mizuna) | Vysejte mezi fazole. Rostou raketově a nevadí jim chladnější zářijové noci v horách. |
        """)

        st.info("""
        **Tipy pro úspěch v 500 m n. m.**
        1. **Po sklizni česneku:** Půda bude hladová. Prolijte ji Razorminem pro bleskový start rajčat.
        2. **Strategie v červenci:** Blumat adaptéry u rajčat jsou nutnost, aby stihla dozrát v září.
        3. **Extra plodiny:** Po česneku zkuste i černou ředkev nebo vodnici – skvělá prevence proti rýmě!
        """)
        
        st.divider()
        st.subheader("📊 Aktuální stav (Live data)")
        if not df_real.empty:
            # Čištění zobrazení data pro tabulku
            df_view = df_real.copy()
            for col in ['Datum_Vysadby', 'Ocekavana_Sklizen', 'Posledni_Hnojeni']:
                if col in df_view.columns:
                    df_view[col] = df_view[col].dt.strftime('%d.%m.%Y').replace('NaT', '-')
            st.dataframe(df_view, use_container_width=True, hide_index=True)

    with tab2:
        st.header("🗺️ Vizualizace záhonů")
        for bed in ["Záhon 1", "Záhon 2"]:
            with st.expander(f"Zobrazit {bed}", expanded=True):
                for r in list("ABCDEF"):
                    cols = st.columns(3)
                    for i, c in enumerate([1, 2, 3]):
                        pos = f"{r}{c}"
                        match = df_real[(df_real["Záhon"] == bed) & (df_real["Pozice"] == pos)]
                        with cols[i]:
                            if not match.empty:
                                st.success(f"**{pos}**\n\n{match.iloc[-1]['Plodina']}")
                            else:
                                st.info(f"**{pos}**\n\n(volno)")

    with tab3:
        st.header("⚙️ Správa zahrady")
        
        # --- NOVÁ VÝSADBA (S výsuvným seznamem pozic) ---
        st.subheader("➕ Přidat plodinu")
        with st.form("new_plant"):
            c1, c2, c3 = st.columns(3)
            p_crop = c1.selectbox("Plodina", list(PLANT_DATABASE.keys()))
            p_bed = c2.selectbox("Záhon", ["Záhon 1", "Záhon 2"])
            # TADY JE TA ZMĚNA: Selectbox místo psaní
            p_pos = c3.selectbox("Pozice", POSITIONS) 
            p_date = st.date_input("Datum výsadby", datetime.now())
            
            if st.form_submit_button("Zapsat do knihy"):
                growth_days = PLANT_DATABASE[p_crop]["growth"]
                expected = pd.Timestamp(p_date) + timedelta(days=growth_days)
                
                new_entry = pd.DataFrame([{
                    "Plodina": p_crop, "Záhon": p_bed, "Pozice": p_pos,
                    "Datum_Vysadby": pd.Timestamp(p_date), "Ocekavana_Sklizen": expected,
                    "Ucinnek_Hnojiva": 14
                }])
                
                updated = pd.concat([df_real, new_entry], ignore_index=True)
                conn.update(worksheet=MAIN_SHEET, data=updated)
                st.success(f"{p_crop} na pozici {p_pos} uloženo!"); st.rerun()

        st.divider()
        # --- HNOJENÍ A MAZÁNÍ ---
        if not df_real.empty:
            st.subheader("🧪 Údržba a hnojení")
            target = st.selectbox("Vyber plodinu", df_real.index, 
                                format_func=lambda x: f"{df_real.loc[x, 'Plodina']} ({df_real.loc[x, 'Záhon']} - {df_real.loc[x, 'Pozice']})")
            
            col_a, col_b = st.columns(2)
            if col_a.button("💧 Zaznamenat hnojení"):
                df_real.at[target, 'Posledni_Hnojeni'] = pd.Timestamp(datetime.now())
                conn.update(worksheet=MAIN_SHEET, data=df_real)
                st.success("Hnojení uloženo!"); st.rerun()
                
            if col_b.button("🗑️ Smazat bez sklizně"):
                df_deleted = df_real.drop(target)
                conn.update(worksheet=MAIN_SHEET, data=df_deleted)
                st.warning("Plodina odstraněna."); st.rerun()

    with tab4:
        st.header("📂 Archiv sklizně")
        try:
            df_arc = conn.read(worksheet=ARCHIVE_SHEET, ttl=0)
            st.dataframe(df_arc, use_container_width=True)
        except:
            st.info("Archiv je prázdný.")

if __name__ == "__main__":
    main()