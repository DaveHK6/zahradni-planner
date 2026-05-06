import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

def main():
    st.set_page_config(page_title="Záhon Planner Pro", layout="wide", page_icon="🌱")
    
    # --- 1. PŘIPOJENÍ A NAČTENÍ DAT ---
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Načteme data a okamžitě vyčistíme prázdné řádky
        df = conn.read(ttl=0).dropna(how="all")
    except Exception as e:
        st.error("Chyba připojení k Google Sheets.")
        st.exception(e)
        return

    # --- 2. KONFIGURACE A LOGIKA VÝPOČTŮ ---
    GROWTH = {"Ředkvičky": 30, "Špenát": 45, "Cukety": 60, "Salát": 50, "Česnek": 240, "Rajčata": 80}
    BEDS = ["Záhon 1", "Záhon 2"]
    ROWS = list("ABCDEF")
    COLS = [1, 2, 3]

    # Zajištění, aby df nebyl None
    if df is None:
        df = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen"])

    # Výpočty provádíme pouze, pokud máme data
    if not df.empty:
        # Bezpečný převod na datum - errors='coerce' změní špatná data na NaT (Not a Time)
        df['Datum_Vysadby'] = pd.to_datetime(df['Datum_Vysadby'], errors='coerce').dt.date
        df['Ocekavana_Sklizen'] = pd.to_datetime(df['Ocekavana_Sklizen'], errors='coerce').dt.date
        
        # Odstraníme řádky, kde se nepodařilo datum převést (prevence chyb)
        df = df.dropna(subset=['Datum_Vysadby', 'Ocekavana_Sklizen'])
        
        dnes = datetime.now().date()
        # Výpočet zbývajících dnů jako celé číslo
        df['Zbývá dní'] = df['Ocekavana_Sklizen'].apply(lambda x: (x - dnes).days if pd.notnull(x) else 0)

    st.title("🌱 Zahradní Manažer Pro")

    # --- 3. ROZHRANÍ (TABS) ---
    t1, t2, t3 = st.tabs(["📊 Přehled & Sklizeň", "🗺️ Vizuální mapa", "⚙️ Správa dat"])

    # TAB 1: PŘEHLED (Tady byla chyba)
    with t1:
        st.subheader("Aktuální stav osevního plánu")
        if not df.empty:
            # Definice barvy textu
            def color_skli(val):
                try:
                    v = int(val)
                    if v < 0: return 'color: #ff4b4b; font-weight: bold'
                    if v <= 7: return 'color: #ffa500; font-weight: bold'
                    return 'color: #28a745'
                except: return None
            
            # Zobrazení stylizované tabulky
            st.dataframe(df.style.map(color_skli, subset=['Zbývá dní']), use_container_width=True)
        else:
            st.info("V tabulce zatím nejsou žádná platná data. Přidej výsadbu v záložce Správa.")

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
                    # Odstraníme pomocný sloupec před uložením
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