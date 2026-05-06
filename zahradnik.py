import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

def main():
    st.set_page_config(page_title="Záhon Planner Pro", layout="wide", page_icon="🌱")
    
    # --- 1. PŘIPOJENÍ A NAČTENÍ DAT ---
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_real = conn.read(ttl=0).dropna(how="all")
    except Exception:
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Poznamka"])

    # --- 2. KONFIGURACE ---
    GROWTH = {"Ředkvičky": 30, "Špenát": 45, "Cukety": 60, "Salát": 50, "Česnek": 240, "Rajčata": 80, "Fazole": 65, "Pak Choi": 40}
    BEDS = ["Záhon 1", "Záhon 2"]
    ROWS = list("ABCDEF")
    COLS = [1, 2, 3]

    if not df_real.empty:
        df_real['Datum_Vysadby'] = pd.to_datetime(df_real['Datum_Vysadby'], errors='coerce').dt.date
        df_real['Ocekavana_Sklizen'] = pd.to_datetime(df_real['Ocekavana_Sklizen'], errors='coerce').dt.date
        dnes = datetime.now().date()
        df_real['Zbývá dní'] = df_real['Ocekavana_Sklizen'].apply(lambda x: (x - dnes).days if pd.notnull(x) else 0)

    st.title("🌱 Zahradní Manažer Pro")

    # --- 3. ROZDĚLENÍ DO LISTŮ ---
    tab1, tab2, tab3 = st.tabs(["📝 Plán & Realita", "🗺️ Mapa záhonů", "⚙️ Správa výsadby"])

    # --- LIST 1: Plán a Realita ---
    with tab1:
        st.header("📝 Osevní plán pro 500 m n. m.")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🟩 ZÁHON 1")
            st.table([{"Období": "Březen–Květen", "Plodina": "Ředkvičky + Špenát", "Tip": "Netkaná textilie"},
                      {"Období": "Květen–Září", "Plodina": "Cuketa Tondo", "Tip": "Trichoderma + Blumat"}])
        with c2:
            st.subheader("🟦 ZÁHON 2")
            st.table([{"Období": "Listopad–Červenec", "Plodina": "Zimní česnek", "Tip": "Sázet na podzim"},
                      {"Období": "Červenec–Září", "Plodina": "Rajčata + Fazole", "Tip": "Po česneku"}])
        
        st.divider()
        st.subheader("📊 Detailní přehled výsadby")
        if not df_real.empty:
            # Barevné stylování zbývajících dnů
            def color_style(val):
                try:
                    v = int(val); return 'background-color: #ff4b4b' if v < 0 else ('background-color: #ffa500' if v <= 7 else '')
                except: return ''
            st.dataframe(df_real.style.map(color_style, subset=['Zbývá dní']), use_container_width=True)
        else:
            st.info("Zatím žádná data.")

    # --- LIST 2: Mapa ---
    with tab2:
        st.header("📍 Vizuální mapa")
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
                                st.success(f"**{pos}**: {item['Plodina']}\n\n💬 {item.get('Poznamka', '')}")
                            else:
                                st.info(f"**{pos}**\n\nVolno")

    # --- LIST 3: Správa (Nová výsadba, Editace a Mazání) ---
    with tab3:
        st.header("⚙️ Správa dat")
        
        # 1. SEKCE: PŘIDÁVÁNÍ
        st.subheader("➕ Nová výsadba")
        with st.form("planting_form"):
            f_crop = st.selectbox("Plodina", list(GROWTH.keys()))
            f_bed = st.selectbox("Záhon", BEDS)
            f_pos = st.selectbox("Pozice", [f"{r}{c}" for r in ROWS for c in COLS])
            f_date = st.date_input("Datum", datetime.now())
            f_note = st.text_input("Poznámka")
            if st.form_submit_button("Uložit novou výsadbu"):
                sklizen = f_date + timedelta(days=GROWTH[f_crop])
                new_data = pd.DataFrame([{"Plodina": f_crop, "Záhon": f_bed, "Pozice": f_pos, "Datum_Vysadby": f_date.strftime('%Y-%m-%d'), "Ocekavana_Sklizen": sklizen.strftime('%Y-%m-%d'), "Poznamka": f_note}])
                save_df = df_real.drop(columns=['Zbývá dní']) if 'Zbývá dní' in df_real.columns else df_real
                conn.update(data=pd.concat([save_df, new_data], ignore_index=True))
                st.success("Zapsáno!"); st.rerun()

        st.divider()

        # 2. SEKCE: ÚPRAVA A MAZÁNÍ
        if not df_real.empty:
            col_edit, col_del = st.columns(2)
            
            with col_edit:
                st.subheader("📝 Upravit poznámku")
                edit_list = [f"{i}: {row['Plodina']} ({row['Pozice']})" for i, row in df_real.iterrows()]
                selected_edit = st.selectbox("Vyber plodinu k úpravě", edit_list)
                idx_edit = int(selected_edit.split(":")[0])
                new_note = st.text_input("Nová poznámka", value=df_real.at[idx_edit, 'Poznamka'])
                
                if st.button("Aktualizovat poznámku"):
                    df_real.at[idx_edit, 'Poznamka'] = new_note
                    save_df = df_real.drop(columns=['Zbývá dní']) if 'Zbývá dní' in df_real.columns else df_real
                    conn.update(data=save_df)
                    st.success("Poznámka upravena!"); st.rerun()

            with col_del:
                st.subheader("🗑️ Smazat výsadbu")
                del_list = [f"{i}: {row['Plodina']} ({row['Pozice']})" for i, row in df_real.iterrows()]
                selected_del = st.selectbox("Vyber plodinu ke smazání", del_list)
                if st.button("Definitivně smazat", type="primary"):
                    idx_del = int(selected_del.split(":")[0])
                    save_df = df_real.drop(df_real.index[idx_del]).drop(columns=['Zbývá dní'], errors='ignore')
                    conn.update(data=save_df)
                    st.success("Smazáno!"); st.rerun()
        else:
            st.info("Žádná data k úpravě nebo mazání.")

if __name__ == "__main__":
    main()