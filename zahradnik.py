import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
# Tvůj odkaz na Google Sheets
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
        # Čtení dat - vracíme dataframe
        df = conn.read(spreadsheet=SHEET_URL, ttl="0")
        # Odstranění prázdných řádků, pokud existují
        df = df.dropna(how="all")
    except Exception as e:
        st.error(f"Nepodařilo se připojit k tabulce. Zkontrolujte sdílení. Chyba: {e}")
        df = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Poznamka"])

    # --- 2. OSEVNÍ PLÁN (Původní tabulky) ---
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
                        match = df[(df["Záhon"] == z_name) & (df["Pozice"] == p)]
                        if not match.empty:
                            last_p = match.iloc[-1]["Plodina"]
                            st.caption(f"📍 {p}")
                            st.success(f"**{last_p}**")
                        else:
                            st.caption(f"📍 {p}")
                            st.code("volno")

    # --- 4. FORMULÁŘ A HISTORIE ---
    st.divider()
    col_form, col_hist = st.columns([1, 1.2])

    with col_form:
        st.subheader("📝 Nový záznam")
        with st.form("cloud_form", clear_on_submit=True):
            f_crop = st.selectbox("Plodina", list(GROWTH_PERIODS.keys()) + ["Jiná..."])
            f_zahon = st.selectbox("Záhon", ["Záhon 1", "Záhon 2"])
            pozice_list = [f"{r}{s}" for r in ["A", "B", "C", "D", "E", "F"] for s in range(1, 4)]
            f_pos = st.selectbox("Pozice", pozice_list)
            f_date = st.date_input("Datum", datetime.now())
            f_note = st.text_input("Poznámka")
            
            if st.form_submit_button("🚀 Zapsat do Cloudu"):
                dny = GROWTH_PERIODS.get(f_crop, 30)
                sklizen = f_date + timedelta(days=dny)
                
                new_row = pd.DataFrame([{
                    "Plodina": f_crop, "Záhon": f_zahon, "Pozice": f_pos, 
                    "Datum_Vysadby": f_date.strftime('%Y-%m-%d'), 
                    "Ocekavana_Sklizen": sklizen.strftime('%Y-%m-%d'), 
                    "Poznamka": f_note
                }])
                
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, data=updated_df)
                st.success("Synchronizováno s Google Sheets!")
                st.rerun()

    with col_hist:
        st.subheader("📖 Správa dat")
        if not df.empty:
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="cloud_edit")
            if st.button("💾 Uložit změny v tabulce"):
                conn.update(spreadsheet=SHEET_URL, data=edited_df)
                st.success("Změny uloženy!")
                st.rerun()
        else:
            st.info("Zatím žádná data v Google Sheets.")

if __name__ == "__main__":
    main()