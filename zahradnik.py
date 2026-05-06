import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

def main():
    st.set_page_config(page_title="Záhon Planner Pro", layout="wide", page_icon="🌱")
    
    # 1. PŘIPOJENÍ A NAČTENÍ DAT
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=0).dropna(how="all")
    except Exception as e:
        st.error("Chyba připojení k Google Sheets.")
        st.exception(e)
        return

    # Definice parametrů
    GROWTH = {"Ředkvičky": 30, "Špenát": 45, "Cukety": 60, "Salát": 50, "Česnek": 240}
    BEDS = ["Záhon 1", "Záhon 2"]
    ROWS = list("ABCDEF")
    COLS = [1, 2, 3]

    # Zajištění správných datových typů
    if not df.empty:
        df['Datum_Vysadby'] = pd.to_datetime(df['Datum_Vysadby']).dt.date
        df['Ocekavana_Sklizen'] = pd.to_datetime(df['Ocekavana_Sklizen']).dt.date
        dnes = datetime.now().date()
        df['Zbývá dní'] = (df['Ocekavana_Sklizen'] - dnes).apply(lambda x: x.days)

    st.title("🌱 Zahradní Manažer Pro")

    # --- TAB 1: PŮVODNÍ TABULKA A PŘEHLED ---
    t1, t2, t3 = st.tabs(["📊 Přehled & Sklizeň", "🗺️ Vizuální mapa", "⚙️ Správa & Mazání"])

    with t1:
        st.subheader("Aktuální stav osevního plánu")
        if not df.empty:
            # Stylizace tabulky
            def color_skli(val):
                color = 'red' if val < 0 else 'orange' if val <= 7 else 'white'
                return f'color: {color}'
            
            st.dataframe(df.style.applymap(color_skli, subset=['Zbývá dní']), use_container_width=True)
        else:
            st.info("Tabulka je zatím prázdná.")

    # --- TAB 2: VIZUÁLNÍ MAPA ---
    with t2:
        st.subheader("Grafické rozložení záhonů")
        for bed in BEDS:
            with st.expander(f"📍 {bed}", expanded=True):
                for r in ROWS:
                    cols = st.columns(len(COLS))
                    for i, c in enumerate(COLS):
                        pos = f"{r}{c}"
                        # Hledáme, co je na této pozici v tomto záhonu
                        match = df[(df["Záhon"] == bed) & (df["Pozice"] == pos)]
                        with cols[i]:
                            if not match.empty:
                                crop = match.iloc[-1]["Plodina"]
                                days = match.iloc[-1]["Zbývá dní"]
                                st.success(f"**{pos}: {crop}**  \n({days} dní)")
                            else:
                                st.info(f"**{pos}:**  \nVolno")

    # --- TAB 3: SPRÁVA, MAZÁNÍ A ÚPRAVA ---
    with t3:
        col_add, col_edit = st.columns(2)
        
        with col_add:
            st.write("### ➕ Nová výsadba")
            with st.form("add_form", clear_on_submit=True):
                f_crop = st.selectbox("Plodina", list(GROWTH.keys()))
                f_bed = st.selectbox("Záhon", BEDS)
                f_pos = st.selectbox("Pozice", [f"{r}{c}" for r in ROWS for c in COLS])
                f_date = st.date_input("Datum výsadby", datetime.now())
                
                if st.form_submit_button("Uložit výsadbu"):
                    sklizen = f_date + timedelta(days=GROWTH[f_crop])
                    new_row = pd.DataFrame([{
                        "Plodina": f_crop, "Záhon": f_bed, "Pozice": f_pos,
                        "Datum_Vysadby": f_date, "Ocekavana_Sklizen": sklizen
                    }])
                    updated_df = pd.concat([df.drop(columns=['Zbývá dní']) if 'Zbývá dní' in df else df, new_row], ignore_index=True)
                    conn.update(data=updated_df)
                    st.success("Zapsáno!"); st.rerun()

        with col_edit:
            st.write("### 🗑️ Odstranit záznam")
            if not df.empty:
                # Vytvoříme identifikátor pro smazání (index + název)
                df_to_delete = df.copy()
                df_to_delete['ID'] = df_to_delete.index.astype(str) + ": " + df_to_delete['Plodina'] + " (" + df_to_delete['Pozice'] + ")"
                to_remove = st.selectbox("Vyber záznam k odstranění", df_to_delete['ID'])
                
                if st.form_submit_button("Smazat vybrané", use_container_width=True):
                    idx_to_remove = int(to_remove.split(":")[0])
                    # Odstraníme řádek podle indexu a pomocný sloupec
                    updated_df = df.drop(df.index[idx_to_remove]).drop(columns=['Zbývá dní'])
                    conn.update(data=updated_df)
                    st.success("Smazáno!"); st.rerun()
            else:
                st.write("Není co mazat.")

if __name__ == "__main__":
    main()