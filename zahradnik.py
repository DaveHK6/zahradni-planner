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

    # LIST 1: Plán a Realita
    with tab1:
        st.header("📝 Osevní plán pro 500 m n. m.")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🟩 ZÁHON 1: Cuketové království")
            st.table([
                {"Období": "Březen–Květen", "Plodina": "Ředkvičky + Špenát", "Tip": "Netkaná textilie"},
                {"Období": "Květen–Září", "Plodina": "Cuketa Tondo", "Tip": "Trichoderma + Blumat"},
                {"Období": "Září–Listopad", "Plodina": "Polníček / Špenát", "Tip": "Mrazuvzdorné"}
            ])
        with c2:
            st.subheader("🟦 ZÁHON 2: Česnekovo-fazolová rotace")
            st.table([
                {"Období": "Listopad–Červenec", "Plodina": "Zimní česnek", "Tip": "Sázet na podzim"},
                {"Období": "Červenec–Září", "Plodina": "Rajčata + Fazole", "Tip": "Po česneku, Razormin"},
                {"Období": "Srpen–Říjen", "Plodina": "Asijské saláty", "Tip": "Rychlý start"}
            ])
        
        st.divider()
        st.subheader("📊 Co právě roste")
        if not df_real.empty:
            st.dataframe(df_real, use_container_width=True)

    # LIST 2: Mapa
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

    # LIST 3: Správa
    with tab3:
        st.header("⚙️ Správa")
        with st.form("planting_form"):
            f_crop = st.selectbox("Plodina", list(GROWTH.keys()))
            f_bed = st.selectbox("Záhon", BEDS)
            f_pos = st.selectbox("Pozice", [f"{r}{c}" for r in ROWS for c in COLS])
            f_date = st.date_input("Datum", datetime.now())
            f_note = st.text_input("Poznámka (např. Razormin, Blumat...)")
            
            if st.form_submit_button("Uložit výsadbu"):
                sklizen = f_date + timedelta(days=GROWTH[f_crop])
                new_data = pd.DataFrame([{
                    "Plodina": f_crop, "Záhon": f_bed, "Pozice": f_pos,
                    "Datum_Vysadby": f_date.strftime('%Y-%m-%d'), 
                    "Ocekavana_Sklizen": sklizen.strftime('%Y-%m-%d'),
                    "Poznamka": f_note
                }])
                save_df = df_real.drop(columns=['Zbývá dní']) if 'Zbývá dní' in df_real.columns else df_real
                conn.update(data=pd.concat([save_df, new_data], ignore_index=True))
                st.success("Zapsáno!"); st.rerun()

if __name__ == "__main__":
    main()