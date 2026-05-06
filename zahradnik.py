import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
# Tvůj odkaz na Google Tabulku
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GVqF6BobYV7nuOPZzgBwi5sp3v8y5iV1QxhMRnIUs48/edit?gid=0#gid=0"

GROWTH_PERIODS = {
    "Ředkvičky": 30, "Špenát": 45, "Kulaté cukety (Tondo)": 60,
    "Polníček": 50, "Zimní salát": 60, "Zimní česnek": 240,
    "Sazenice rajčat": 75, "Keříčkové fazole": 65, "Vodnice": 60, "Černá ředkev": 90
}

def main():
    st.set_page_config(page_title="Záhon Planner Cloud", layout="wide")
    st.title("🌱 Cloudový Zahradní Plánovač")

    # 1. PŘIPOJENÍ KE GOOGLE SHEETS
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    try:
        # ttl=0 zajistí, že uvidíme změny hned po uložení
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        df = df.dropna(how="all")
    except Exception:
        df = pd.DataFrame()

    # Pojistka pro sloupce (aby aplikace nespadla, když je tabulka prázdná)
    required_columns = ["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Poznamka"]
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    # --- 2. INFORMATIVNÍ TABULKY (OSEVNÍ PLÁN) ---
    st.header("ZÁHON 1: Jarní vitaminy a grilovací speciály")
    data1 = [
        ["Březen – Květen", "Ředkvičky + Špenát", "Vysévejte pod bílou netkanou textilii."],
        ["Červen – Září", "Kulaté cukety (Tondo di Piacenza)", "Po ředkvičkách saďte sazenice."],
        ["Září – Listopad", "Polníček / Zimní salát", "Zasejte po sklizni cuket."]
    ]
    st.table(pd.DataFrame(data1, columns=["Období", "Plodina", "Tip pro 500 m n. m."]))

    st.header("ZÁHON 2: Zimní česnek a letní „druhá směna“")
    data2 = [
        ["Listopad – Červenec", "Zimní česnek", "Sází se hluboko (8–10 cm)."],
        ["Červenec – Září", "Sazenice rajčat + Keříčkové fazole", "Razormin při výsadbě."],
        ["Srpen – Říjen", "Vodnice / Černá ředkev", "Milují podzimní chlad."]
    ]
    st.table(pd.DataFrame(data2, columns=["Období", "Plodina", "Tip pro 500 m n. m."]))

    # --- 3. KOMPAKTNÍ VIZUÁLNÍ MAPA ---
    st.divider()
    st.subheader("🖼️ Aktuální osázení (Mřížka 3x6)")
    z_tabs = st.tabs(["Záhon 1", "Záhon 2"])
    
    for i, tab in enumerate(z_tabs):
        z_name = f"Záhon {i+1}"
        with tab:
            for r in ["A", "B", "C", "D", "E", "F"]:
                cols = st.columns(3)
                for s in range(1, 4):
                    p = f"{r}{s}"
                    with cols[s-1]:
                        # Hledáme poslední plodinu na dané pozici
                        match = df[(df["Záhon"] == z_name) & (df["Pozice"] == p)]
                        if not match.empty and match.iloc[-1]["Plodina"]:
                            st.caption(f"📍 {p}")
                            st.success(f"**{match.iloc[-1]['Plodina']}**")
                        else:
                            st.caption(f"📍 {p}")
                            st.code("volno")

    # --- 4. FORMULÁŘ PRO ZÁPIS A HISTORIE ---
    st.divider()
    col_form, col_hist = st.columns([1, 1.2])

    with col_form:
        st.subheader("📝 Nový záznam")
        with st.form("cloud_form", clear_on_submit=True):
            f_crop = st.selectbox("Plodina", list(GROWTH_PERIODS.keys()) + ["Jiná..."])
            f_zahon = st.selectbox("Záhon", ["Záhon 1", "Záhon 2"])
            pozice_list = [f"{r}{s}" for r in ["A", "B", "C", "D", "E", "F"] for s in range(1, 4)]
            f_pos = st.selectbox("Pozice", pozice_list)
            f_date = st.date_input("Datum výsadby", datetime.now())
            f_note = st.text_input("Poznámka")
            
            if st.form_submit_button("🚀 Zapsat do Cloudu"):
                # Výpočet sklizně
                dny = GROWTH_PERIODS.get(f_crop, 30)
                sklizen = f_date + timedelta(days=dny)
                
                # Nová data
                new_row = pd.DataFrame([{
                    "Plodina": f_crop, "Záhon": f_zahon, "Pozice": f_pos, 
                    "Datum_Vysadby": f_date.strftime('%Y-%m-%d'), 
                    "Ocekavana_Sklizen": sklizen.strftime('%Y-%m-%d'), 
                    "Poznamka": f_note
                }])
                
                # Spojení a odeslání
                updated_df = pd.concat([df, new_row], ignore_index=True)
                try:
                    conn.update(spreadsheet=SHEET_URL, data=updated_df)
                    st.success("Zapsáno! Obnovuji aplikaci...")
                    st.rerun()
                except Exception as e:
                    st.error(f"Chyba při zápisu: {e}")
                    st.info("💡 Tip: Nastav v Google Sheets sdílení pro 'EDITOR'!")

    with col_hist:
        st.subheader("📖 Správa historie")
        if not df.empty:
            # Editor umožňující mazat a měnit řádky
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="history_editor")
            if st.button("💾 Uložit změny v historii"):
                try:
                    conn.update(spreadsheet=SHEET_URL, data=edited_df)
                    st.success("Tabulka v Google Sheets aktualizována!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Chyba při ukládání: {e}")
        else:
            st.info("Zatím nejsou k dispozici žádná data.")

if __name__ == "__main__":
    main()