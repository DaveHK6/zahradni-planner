import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

def main():
    st.set_page_config(page_title="Záhon Planner Pro", layout="wide", page_icon="🌱")
    
    # --- 1. PŘIPOJENÍ K DATŮM (GOOGLE SHEETS) ---
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_real = conn.read(ttl=0).dropna(how="all")
    except Exception:
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen"])

    # --- 2. LOGIKA PRO VÝPOČTY ---
    GROWTH = {
        "Ředkvičky": 30, "Špenát": 45, "Cukety": 60, "Salát": 50, 
        "Česnek": 240, "Rajčata": 80, "Fazole": 65, "Pak Choi": 40
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

    # --- 3. ROZDĚLENÍ DO LISTŮ (TABS) ---
    tab1, tab2, tab3 = st.tabs(["📝 Plán & Realita", "🗺️ Mapa záhonů", "⚙️ Správa výsadby"])

    # --- LIST 1: OSEVNÍ PLÁN + AKTUÁLNĚ ZASAZENO ---
    with tab1:
        st.header("📝 Osevní plán pro 500 m n. m.")
        
        col_z1, col_z2 = st.columns(2)
        
        with col_z1:
            st.subheader("🟩 ZÁHON 1: Cuketové království")
            z1_data = [
                {"Období": "Březen – Květen", "Plodina": "Ředkvičky + Špenát", "Poznámka": "Bílá textilie – mikroklima."},
                {"Období": "Květen – Září", "Plodina": "Cuketa Tondo", "Poznámka": "Trichoderma + Blumat adaptéry."},
                {"Období": "Září – Listopad", "Plodina": "Polníček / Špenát", "Poznámka": "Vydrží mráz, skvělé saláty."}
            ]
            st.table(pd.DataFrame(z1_data))

        with col_z2:
            st.subheader("🟦 ZÁHON 2: Česnekovo-fazolová rotace")
            z2_data = [
                {"Období": "Listopad – Červenec", "Plodina": "Zimní česnek", "Poznámka": "Sázíte na podzim, sklizeň v červenci."},
                {"Období": "Červenec – Září", "Plodina": "Rajčata + Fazole", "Poznámka": "Do prázdných míst po česneku."},
                {"Období": "Srpen – Říjen", "Plodina": "Asijské saláty", "Poznámka": "Rostou raketově i v chladu."}
            ]
            st.table(pd.DataFrame(z2_data))

        with st.expander("💡 Tipy pro úspěch na horách (500 m n. m.)"):
            st.markdown("""
            *   **Po česneku (Červenec):** Prolijte záhon **Razorminem**. Pomůže sazenicím překonat šok z letního vedra.
            *   **Strategie pro rajčata:** Blumat adaptéry jsou nutnost! Rajče musí růst 'rychlostí blesku', aby stihlo dozrát.
            *   **Černá ředkev a vodnice:** Skvělá volba po česneku, rostou bleskově a jsou prevencí proti rýmě.
            *   **Tip pro cukety:** Jednu 'kouli' nechte dorůst – ve sklepě vydrží klidně až do Vánoc!
            """)

        st.divider()
        st.subheader("📊 Co právě roste (Data z tabulky)")
        if not df_real.empty:
            def style_rows(val):
                try:
                    v = int(val)
                    if v < 0: return 'background-color: #ff4b4b; color: white'
                    if v <= 7: return 'background-color: #ffa500; color: black'
                    return ''
                except: return ''
            st.dataframe(df_real.style.map(style_rows, subset=['Zbývá dní']), use_container_width=True)
        else:
            st.info("Zatím žádná reálná výsadba.")

    # --- LIST 2: GRAFICKÉ ROZLOŽENÍ ---
    with tab2:
        st.header("📍 Vizuální mapa zahrady")
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
                                st.success(f"**{pos}**\n\n{item['Plodina']}\n\n({item['Zbývá dní']} d.)")
                            else:
                                st.info(f"**{pos}**\n\nVolno")

    # --- LIST 3: SPRÁVA DAT ---
    with tab3:
        st.header("⚙️ Správa zahrady")
        col_add, col_del = st.columns(2)
        with col_add:
            st.subheader("➕ Nová výsadba")
            with st.form("new_planting", clear_on_submit=True):
                f_crop = st.selectbox("Co sázíš?", list(GROWTH.keys()))
                f_bed = st.selectbox("Který záhon?", BEDS)
                f_pos = st.selectbox("Pozice (A1-F3)", [f"{r}{c}" for r in ROWS for c in COLS])
                f_date = st.date_input("Datum výsadby", datetime.now())
                if st.form_submit_button("Zapsat do Cloudu"):
                    sklizen = f_date + timedelta(days=GROWTH[f_crop])
                    new_row = pd.DataFrame([{
                        "Plodina": f_crop, "Záhon": f_bed, "Pozice": f_pos,
                        "Datum_Vysadby": f_date.strftime('%Y-%m-%d'), 
                        "Ocekavana_Sklizen": sklizen.strftime('%Y-%m-%d')
                    }])
                    clean_df = df_real.drop(columns=['Zbývá dní']) if 'Zbývá dní' in df_real.columns else df_real
                    conn.update(data=pd.concat([clean_df, new_row], ignore_index=True))
                    st.success("Uloženo!"); st.rerun()

        with col_del:
            st.subheader("🗑️ Odstranit záznam")
            if not df_real.empty:
                del_list = [f"{i}: {row['Plodina']} ({row['Pozice']})" for i, row in df_real.iterrows()]
                to_delete = st.selectbox("Vyber řádek", del_list)
                if st.button("Smazat vybrané", type="primary"):
                    idx = int(to_delete.split(":")[0])
                    conn.update(data=df_real.drop(df_real.index[idx]).drop(columns=['Zbývá dní']))
                    st.success("Smazáno!"); st.rerun()

if __name__ == "__main__":
    main()