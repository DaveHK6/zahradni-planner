import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

def main():
    st.set_page_config(page_title="Záhon Planner Cloud", layout="wide")
    st.title("🌱 Cloudový Zahradní Plánovač")

    # 1. PŘIPOJENÍ
    # Automaticky čte konfiguraci ze st.secrets["connections.gsheets"]
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=0)
        if df is not None:
            df = df.dropna(how="all")
    except Exception as e:
        st.error("❌ Chyba připojení. Zkontroluj Secrets ve Streamlit Cloudu.")
        st.exception(e)
        return

    # Definice růstových dob
    GROWTH = {
        "Ředkvičky": 30, "Špenát": 45, "Cukety": 60, "Salát": 50, "Česnek": 240
    }

    # Zajištění sloupců
    cols = ["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen"]
    if df is None or df.empty:
        df = pd.DataFrame(columns=cols)

    # --- JEDNODUCHÉ ROZHRANÍ ---
    tab1, tab2 = st.tabs(["📊 Přehled", "➕ Přidat záznam"])

    with tab1:
        st.subheader("Aktuální stav v tabulce")
        st.dataframe(df, use_container_width=True)

    with tab2:
        with st.form("garden_form"):
            f_crop = st.selectbox("Co sázíš?", list(GROWTH.keys()))
            f_bed = st.selectbox("Záhon", ["Záhon 1", "Záhon 2"])
            f_pos = st.text_input("Pozice (např. A1)", "A1")
            f_date = st.date_input("Datum výsadby", datetime.now())
            
            if st.form_submit_button("Zapsat do Cloudu"):
                # Výpočet sklizně
                sklizen = f_date + timedelta(days=GROWTH[f_crop])
                
                new_data = pd.DataFrame([{
                    "Plodina": f_crop,
                    "Záhon": f_bed,
                    "Pozice": f_pos,
                    "Datum_Vysadby": f_date.strftime('%Y-%m-%d'),
                    "Ocekavana_Sklizen": sklizen.strftime('%Y-%m-%d')
                }])
                
                # Spojení a odeslání do Google Sheets
                updated_df = pd.concat([df, new_data], ignore_index=True)
                conn.update(data=updated_df)
                st.success("Uloženo! Tabulka se aktualizuje...")
                st.rerun()

if __name__ == "__main__":
    main()