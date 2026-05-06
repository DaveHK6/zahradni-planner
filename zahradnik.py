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

    # --- 2. KONFIGURACE DAT ---
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

    # --- 3. KONFIGURACE ZALAMOVÁNÍ TEXTU (FIX) ---
    # Tato konfigurace zajistí, že sloupce s textem budou mít dost místa a nebudou se ořezávat
    column_cfg = {
        "Období": st.column_config.TextColumn("Období", width="small"),
        "Plodina": st.column_config.TextColumn("Plodina", width="medium"),
        "Poznámka": st.column_config.TextColumn("Poznámka", width="large", required=True),
        "Poznamka": st.column_config.TextColumn("Poznamka", width="large")
    }

    # --- 4. ROZDĚLENÍ DO LISTŮ ---
    tab1, tab2, tab3 = st.tabs(["📝 Plán & Realita", "🗺️ Mapa záhonů", "⚙️ Správa výsadby"])

    # LIST 1: Plán a Realita
    with tab1:
        st.header("📝 Kompletní osevní plán (500 m n. m.)")
        
        z1_data = [
            {"Období": "Březen–Květen", "Plodina": "Ředkvičky + Jarní špenát", "Poznámka": "Vysévejte v polovině března. Přikryjte bílou netkanou textilií – vytvoří potřebné mikroklima."},
            {"Období": "Konec května–Září", "Plodina": "Cuketa Tondo di Piacenza", "Poznámka": "Do jamky lžičku Trichodermy. Nezapomeňte na PET lahve s Blumatem pro závlahu."},
            {"Období": "Září–Listopad", "Plodina": "Polníček / Zimní špenát", "Poznámka": "Po cuketách záhon nevynechejte. Plodiny vydrží mráz a v říjnu zajistí čerstvý salát."}
        ]
        
        z2_data = [
            {"Období": "Listopad–Červenec", "Plodina": "Zimní česnek", "Poznámka": "Sázíte na podzim. Přes zimu o něm nevíte, v červenci sklízíte vlastní palice."},
            {"Období": "Červenec–Září", "Plodina": "Rajčata + Keříčkové fazole", "Poznámka": "Do míst po česneku vzrostlé sazenice. Prolijte Razorminem pro start v horku."},
            {"Období": "Srpen–Říjen", "Plodina": "Asijské saláty (Pak Choi / Mizuna)", "Poznámka": "Rostou raketově mezi fazolemi. Nevadí jim chladnější zářijové noci na horách."}
        ]

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🟩 ZÁHON 1")
            st.dataframe(pd.DataFrame(z1_data), hide_index=True, column_config=column_cfg, use_container_width=True)
        with c2:
            st.subheader("🟦 ZÁHON 2")
            st.dataframe(pd.DataFrame(z2_data), hide_index=True, column_config=column_cfg, use_container_width=True)
        
        st.divider()
        st.subheader("📊 Aktuální stav výsadby")
        if not df_real.empty:
            def style_rows(val):
                try:
                    v = int(val)
                    if v < 0: return 'background-color: #ff4b4b; color: white'
                    if v <= 7: return 'background-color: #ffa500; color: black'
                    return ''
                except: return ''
            
            # Aplikace konfigurace i na tabulku s reálnými daty
            st.dataframe(df_real.style.map(style_rows, subset=['Zbývá dní']), 
                         column_config=column_cfg, 
                         use_container_width=True, 
                         hide_index=True)
        else:
            st.info("Zatím žádná data z Cloudu.")

    # [Zbytek kódu pro Mapu a Správu zůstává stejný jako v předchozí verzi]
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

    with tab3:
        st.header("⚙️ Správa dat")
        with st.form("planting_form", clear_on_submit=True):
            f_crop = st.selectbox("Plodina", list(GROWTH.keys()))
            f_bed = st.selectbox("Záhon", BEDS)
            f_pos = st.selectbox("Pozice", [f"{r}{c}" for r in ROWS for c in COLS])
            f_date = st.date_input("Datum", datetime.now())
            f_note = st.text_input("Poznámka")
            if st.form_submit_button("Uložit výsadbu"):
                sklizen = f_date + timedelta(days=GROWTH[f_crop])
                new_data = pd.DataFrame([{"Plodina": f_crop, "Záhon": f_bed, "Pozice": f_pos, "Datum_Vysadby": f_date.strftime('%Y-%m-%d'), "Ocekavana_Sklizen": sklizen.strftime('%Y-%m-%d'), "Poznamka": f_note}])
                save_df = df_real.drop(columns=['Zbývá dní']) if 'Zbývá dní' in df_real.columns else df_real
                conn.update(data=pd.concat([save_df, new_data], ignore_index=True))
                st.success("Zapsáno!"); st.rerun()

        if not df_real.empty:
            st.divider()
            col_edit, col_del = st.columns(2)
            with col_edit:
                st.subheader("📝 Upravit poznámku")
                edit_list = [f"{i}: {row['Plodina']} ({row['Pozice']})" for i, row in df_real.iterrows()]
                selected_edit = st.selectbox("Vyber k úpravě", edit_list)
                idx_edit = int(selected_edit.split(":")[0])
                new_note = st.text_input("Nová poznámka", value=df_real.at[idx_edit, 'Poznamka'])
                if st.button("Aktualizovat"):
                    df_real.at[idx_edit, 'Poznamka'] = new_note
                    conn.update(data=df_real.drop(columns=['Zbývá dní']))
                    st.success("Upraveno!"); st.rerun()
            with col_del:
                st.subheader("🗑️ Smazat")
                del_list = [f"{i}: {row['Plodina']} ({row['Pozice']})" for i, row in df_real.iterrows()]
                selected_del = st.selectbox("Smazat", del_list)
                if st.button("Smazat", type="primary"):
                    idx_del = int(selected_del.split(":")[0])
                    conn.update(data=df_real.drop(df_real.index[idx_del]).drop(columns=['Zbývá dní']))
                    st.success("Smazáno!"); st.rerun()

if __name__ == "__main__":
    main()