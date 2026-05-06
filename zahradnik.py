import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

def main():
    st.set_page_config(page_title="Záhon Planner Pro", layout="wide", page_icon="🌱")
    
    # --- 1. PŘIPOJENÍ K DATŮM (Google Sheets) ---
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_real = conn.read(ttl=0).dropna(how="all")
    except Exception:
        df_real = pd.DataFrame()

    # --- 2. STATICKÁ DATA: OSEVNÍ PLÁN (Tvůj manuál) ---
    osevni_plan_data = [
        {"Plodina": "Ředkvičky", "Kdy sázet": "Březen - Duben", "Spon": "15x3 cm", "Poznámka": "Rychlá sklizeň, sázet postupně"},
        {"Plodina": "Salát", "Kdy sázet": "Duben - Srpen", "Spon": "25x25 cm", "Poznámka": "Chránit před slimáky"},
        {"Plodina": "Cukety", "Kdy sázet": "Květen (po zmrzlých)", "Spon": "100x100 cm", "Poznámka": "Potřebuje hodně kompostu"},
        {"Plodina": "Česnek", "Kdy sázet": "Listopad", "Spon": "20x10 cm", "Poznámka": "Sázet hluboko do země"},
        {"Plodina": "Rajčata", "Kdy sázet": "Květen", "Spon": "50x50 cm", "Poznámka": "Vyštipovat boční výhony"}
    ]
    df_plan = pd.DataFrame(osevni_plan_data)

    # --- 3. LOGIKA PRO DYNAMICKÁ DATA (Co už roste) ---
    GROWTH = {"Ředkvičky": 30, "Špenát": 45, "Cukety": 60, "Salát": 50, "Česnek": 240, "Rajčata": 80}
    
    if not df_real.empty:
        df_real['Datum_Vysadby'] = pd.to_datetime(df_real['Datum_Vysadby'], errors='coerce').dt.date
        df_real['Ocekavana_Sklizen'] = pd.to_datetime(df_real['Ocekavana_Sklizen'], errors='coerce').dt.date
        dnes = datetime.now().date()
        df_real['Zbývá dní'] = df_real['Ocekavana_Sklizen'].apply(lambda x: (x - dnes).days if pd.notnull(x) else 0)

    # --- 4. ZOBRAZENÍ APLIKACE ---
    st.title("🌱 Zahradní Manažer Pro")

    # A) PŮVODNÍ OSEVNÍ PLÁN (Statický manuál)
    st.header("📝 Osevní plán (Celoroční přehled)")
    st.table(df_plan) # Používáme st.table pro hezký čistý vzhled
    
    st.divider()

    # B) AKTUÁLNÍ STAV (Co je v zemi)
    st.header("📊 Aktuálně zasazeno v zahradě")
    if not df_real.empty:
        # Metriky
        m1, m2 = st.columns(2)
        m1.metric("Celkem v záhonech", f"{len(df_real)} ks")
        m2.metric("Sklizeň brzy", f"{len(df_real[df_real['Zbývá dní'] <= 7])} ks")

        # OPRAVENÁ TABULKA (Chyba byla zde - applymap -> map)
        def color_skli(val):
            try:
                v = int(val)
                if v < 0: return 'background-color: #ff4b4b; color: white'
                if v <= 7: return 'background-color: #ffa500; color: black'
                return ''
            except: return ''
            
        st.dataframe(df_real.style.map(color_skli, subset=['Zbývá dní']), use_container_width=True)
    else:
        st.info("V záhonech zatím nic není.")

    # C) DALŠÍ FUNKCE V TABECH
    t2, t3 = st.tabs(["🗺️ Vizuální mapa", "⚙️ Správa dat"])

    with t2:
        st.subheader("Grafické rozložení záhonů")
        BEDS = ["Záhon 1", "Záhon 2"]
        ROWS = list("ABCDEF")
        COLS = [1, 2, 3]
        for bed in BEDS:
            with st.expander(f"📍 {bed}", expanded=True):
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

    with t3:
        col_add, col_del = st.columns(2)
        with col_add:
            st.write("### ➕ Nová výsadba")
            with st.form("add_form", clear_on_submit=True):
                f_crop = st.selectbox("Plodina", list(GROWTH.keys()))
                f_bed = st.selectbox("Záhon", ["Záhon 1", "Záhon 2"])
                f_pos = st.selectbox("Pozice", [f"{r}{c}" for r in list("ABCDEF") for c in [1, 2, 3]])
                f_date = st.date_input("Datum výsadby", datetime.now())
                
                if st.form_submit_button("Uložit do cloudu"):
                    sklizen = f_date + timedelta(days=GROWTH[f_crop])
                    new_row = pd.DataFrame([{
                        "Plodina": f_crop, "Záhon": f_bed, "Pozice": f_pos,
                        "Datum_Vysadby": f_date.strftime('%Y-%m-%d'), 
                        "Ocekavana_Sklizen": sklizen.strftime('%Y-%m-%d')
                    }])
                    save_df = df_real.drop(columns=['Zbývá dní']) if 'Zbývá dní' in df_real.columns else df_real
                    final_df = pd.concat([save_df, new_row], ignore_index=True)
                    conn.update(data=final_df)
                    st.success("Uloženo!")
                    st.rerun()

        with col_del:
            st.write("### 🗑️ Odstranit záznam")
            if not df_real.empty:
                delete_options = [f"{i}: {row['Plodina']} ({row['Pozice']})" for i, row in df_real.iterrows()]
                to_delete = st.selectbox("Vyber řádek", delete_options)
                if st.button("Smazat", type="primary"):
                    idx = int(to_delete.split(":")[0])
                    new_df = df_real.drop(df_real.index[idx]).drop(columns=['Zbývá dní'])
                    conn.update(data=new_df)
                    st.success("Smazáno!")
                    st.rerun()

if __name__ == "__main__":
    main()