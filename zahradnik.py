import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

def main():
    st.set_page_config(page_title="Záhon Planner Pro", layout="wide", page_icon="🌱")
    
    # --- 1. PŘIPOJENÍ A NAČTENÍ DAT ---
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Načteme data a odstraníme úplně prázdné řádky
        df = conn.read(ttl=0).dropna(how="all")
    except Exception as e:
        st.error("Chyba připojení k Google Sheets. Zkontroluj Secrets.")
        st.exception(e)
        return

    # --- 2. KONFIGURACE A LOGIKA ---
    # Slovník růstových dob (v dnech)
    GROWTH = {
        "Ředkvičky": 30, "Špenát": 45, "Cukety": 60, 
        "Salát": 50, "Česnek": 240, "Rajčata": 80
    }
    BEDS = ["Záhon 1", "Záhon 2"]
    ROWS = list("ABCDEF") # Řádky záhonu
    COLS = [1, 2, 3]      # Sloupce záhonu

    # Zpracování dat, pokud tabulka není prázdná
    if not df.empty:
        df['Datum_Vysadby'] = pd.to_datetime(df['Datum_Vysadby']).dt.date
        df['Ocekavana_Sklizen'] = pd.to_datetime(df['Ocekavana_Sklizen']).dt.date
        dnes = datetime.now().date()
        # Výpočet zbývajících dnů
        df['Zbývá dní'] = (df['Ocekavana_Sklizen'] - dnes).apply(lambda x: x.days)
    else:
        # Definice prázdného DataFrame se správnými sloupci
        df = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen"])

    st.title("🌱 Zahradní Manažer Pro")

    # --- 3. ROZHRANÍ (TABS) ---
    t1, t2, t3 = st.tabs(["📊 Přehled & Sklizeň", "🗺️ Vizuální mapa", "⚙️ Správa dat"])

    # TAB 1: PŮVODNÍ TABULKA
    with t1:
        st.subheader("Aktuální stav osevního plánu")
        if not df.empty and 'Zbývá dní' in df.columns:
            def color_skli(val):
                try:
                    v = int(val)
                    if v < 0: return 'color: #ff4b4b; font-weight: bold' # Po termínu (červená)
                    if v <= 7: return 'color: #ffa500; font-weight: bold' # Do týdne (oranžová)
                    return 'color: #28a745' # V pořádku (zelená)
                except: return None
            
            # Použití opravené metody .map() místo .applymap()
            styled_df = df.style.map(color_skli, subset=['Zbývá dní'])
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("Zatím žádná data. Přidej výsadbu v záložce Správa.")

    # TAB 2: VIZUÁLNÍ MAPA
    with t2:
        st.subheader("Grafické rozložení záhonů")
        for bed in BEDS:
            with st.expander(f"📍 {bed}", expanded=True):
                for r in ROWS:
                    cols_ui = st.columns(len(COLS))
                    for i, c in enumerate(COLS):
                        pos = f"{r}{c}"
                        # Najdeme, zda na této pozici něco roste
                        match = df[(df["Záhon"] == bed) & (df["Pozice"] == pos)]
                        with cols_ui[i]:
                            if not match.empty:
                                item = match.iloc[-1]
                                st.success(f"**{pos}**\n\n{item['Plodina']}\n\n({item['Zbývá dní']} d.)")
                            else:
                                st.info(f"**{pos}**\n\nVolno")

    # TAB 3: SPRÁVA (PŘIDÁVÁNÍ A MAZÁNÍ)
    with t3:
        col_add, col_del = st.columns(2)
        
        with col_add:
            st.write("### ➕ Nová výsadba")
            with st.form("add_form", clear_on_submit=True):
                f_crop = st.selectbox("Plodina", list(GROWTH.keys()))
                f_bed = st.selectbox("Záhon", BEDS)
                # Vygenerujeme seznam všech možných pozic A1 až F3
                all_pos = [f"{r}{c}" for r in ROWS for c in COLS]
                f_pos = st.selectbox("Pozice", all_pos)
                f_date = st.date_input("Datum výsadby", datetime.now())
                
                if st.form_submit_button("Uložit do cloudu"):
                    # Výpočet data sklizně
                    sklizen = f_date + timedelta(days=GROWTH[f_crop])
                    new_row = pd.DataFrame([{
                        "Plodina": f_crop, "Záhon": f_bed, "Pozice": f_pos,
                        "Datum_Vysadby": f_date, "Ocekavana_Sklizen": sklizen
                    }])
                    # Sloučení a odeslání (bez pomocného sloupce 'Zbývá dní')
                    final_df = pd.concat([df.drop(columns=['Zbývá dní']) if 'Zbývá dní' in df else df, new_row], ignore_index=True)
                    conn.update(data=final_df)
                    st.success("Data uložena!")
                    st.rerun()

        with col_del:
            st.write("### 🗑️ Odstranit záznam")
            if not df.empty and len(df) > 0:
                # Vytvoření čitelného seznamu pro smazání
                delete_options = [f"{i}: {row['Plodina']} v {row['Záhon']} ({row['Pozice']})" for i, row in df.iterrows()]
                to_delete = st.selectbox("Vyber řádek ke smazání", delete_options)
                
                if st.button("Definitivně smazat", type="primary"):
                    idx = int(to_delete.split(":")[0])
                    # Odstraníme řádek a pomocný sloupec
                    new_df = df.drop(df.index[idx])
                    if 'Zbývá dní' in new_df.columns:
                        new_df = new_df.drop(columns=['Zbývá dní'])
                    
                    conn.update(data=new_df)
                    st.success("Záznam odstraněn!")
                    st.rerun()
            else:
                st.write("Žádná data k smazání.")

if __name__ == "__main__":
    main()