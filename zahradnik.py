import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

def main():
    st.set_page_config(page_title="Záhon Planner Pro", layout="wide", page_icon="🌱")
    
    # --- 1. PŘIPOJENÍ A NAČTENÍ DAT ---
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=0).dropna(how="all")
    except Exception as e:
        st.error("Chyba připojení k Google Sheets.")
        st.exception(e)
        return

    # --- 2. KONFIGURACE A LOGIKA ---
    GROWTH = {"Ředkvičky": 30, "Špenát": 45, "Cukety": 60, "Salát": 50, "Česnek": 240, "Rajčata": 80}
    BEDS = ["Záhon 1", "Záhon 2"]
    ROWS = list("ABCDEF")
    COLS = [1, 2, 3]

    if df is None:
        df = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen"])

    if not df.empty:
        df['Datum_Vysadby'] = pd.to_datetime(df['Datum_Vysadby'], errors='coerce').dt.date
        df['Ocekavana_Sklizen'] = pd.to_datetime(df['Ocekavana_Sklizen'], errors='coerce').dt.date
        df = df.dropna(subset=['Datum_Vysadby', 'Ocekavana_Sklizen'])
        dnes = datetime.now().date()
        df['Zbývá dní'] = df['Ocekavana_Sklizen'].apply(lambda x: (x - dnes).days if pd.notnull(x) else 0)

    # --- HLAVNÍ NADPIS A ÚVODNÍ PŘEHLED ---
    st.title("🌱 Zahradní Manažer Pro")
    
    if not df.empty:
        # Výpočet rychlých metrik pro úvod
        aktualne_zasazeno = len(df)
        ke_sklizni = len(df[df['Zbývá dní'] <= 7])
        
        # Zobrazení metrik v pěkných boxech
        m1, m2 = st.columns(2)
        m1.metric("Celkem zasazeno", f"{aktualne_zasazeno} ks")
        m2.metric("Sklizeň do týdne", f"{ke_sklizni} ks", delta_color="inverse")
        
        st.write("### 📋 Hlavní přehledová tabulka")
        # Definice barev pro úvodní tabulku
        def color_skli(val):
            try:
                v = int(val)
                if v < 0: return 'background-color: #ff4b4b; color: white'
                if v <= 7: return 'background-color: #ffa500; color: black'
                return ''
            except: return ''
        
        st.dataframe(df.style.applymap(color_skli, subset=['Zbývá dní']), use_container_width=True)
        st.divider() # Oddělovač mezi úvodem a zbytkem aplikace

    # --- 3. ROZHRANÍ (TABS) ---
    t1, t2, t3 = st.tabs(["📊 Detailní statistiky", "🗺️ Vizuální mapa", "⚙️ Správa dat"])

    # TAB 1: DETAILNÍ STATISTIKY
    with t1:
        st.subheader("Podrobný rozpis sklizní")
        if not df.empty:
            st.write("Zde můžete sledovat časovou osu vašich rostlin.")
            st.table(df[['Plodina', 'Záhon', 'Ocekavana_Sklizen', 'Zbývá dní']].sort_values('Zbývá dní'))
        else:
            st.info("Zatím žádná data k zobrazení.")

    # TAB 2: VIZUÁLNÍ MAPA
    with t2:
        st.subheader("Grafické rozložení záhonů")
        for bed in BEDS:
            with st.expander(f"📍 {bed}", expanded=True):
                for r in ROWS:
                    cols_ui = st.columns(len(COLS))
                    for i, c in enumerate(COLS):
                        pos = f"{r}{c}"
                        match = df[(df["Záhon"] == bed) & (df["Pozice"] == pos)]
                        with cols_ui[i]:
                            if not match.empty:
                                item = match.iloc[-1]
                                st.success(f"**{pos}**\n\n{item['Plodina']}\n\n({item['Zbývá dní']} d.)")
                            else:
                                st.info(f"**{pos}**\n\nVolno")

    # TAB 3: SPRÁVA
    with t3:
        col_add, col_del = st.columns(2)
        with col_add:
            st.write("### ➕ Nová výsadba")
            with st.form("add_form", clear_on_submit=True):
                f_crop = st.selectbox("Plodina", list(GROWTH.keys()))
                f_bed = st.selectbox("Záhon", BEDS)
                f_pos = st.selectbox("Pozice", [f"{r}{c}" for r in ROWS for c in COLS])
                f_date = st.date_input("Datum výsadby", datetime.now())
                
                if st.form_submit_button("Uložit do cloudu"):
                    sklizen = f_date + timedelta(days=GROWTH[f_crop])
                    new_row = pd.DataFrame([{
                        "Plodina": f_crop, "Záhon": f_bed, "Pozice": f_pos,
                        "Datum_Vysadby": f_date.strftime('%Y-%m-%d'), 
                        "Ocekavana_Sklizen": sklizen.strftime('%Y-%m-%d')
                    }])
                    save_df = df.drop(columns=['Zbývá dní']) if 'Zbývá dní' in df.columns else df
                    final_df = pd.concat([save_df, new_row], ignore_index=True)
                    conn.update(data=final_df)
                    st.success("Uloženo!")
                    st.rerun()

        with col_del:
            st.write("### 🗑️ Odstranit záznam")
            if not df.empty:
                delete_options = [f"{i}: {row['Plodina']} ({row['Pozice']})" for i, row in df.iterrows()]
                to_delete = st.selectbox("Vyber řádek", delete_options)
                if st.button("Smazat", type="primary"):
                    idx = int(to_delete.split(":")[0])
                    new_df = df.drop(df.index[idx]).drop(columns=['Zbývá dní'])
                    conn.update(data=new_df)
                    st.success("Smazáno!")
                    st.rerun()

if __name__ == "__main__":
    main()