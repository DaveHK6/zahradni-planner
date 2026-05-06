import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
# URL tvojí Google tabulky (tu sem vložíš později nebo do Secrets)
SHEET_URL = "SEM_VLOZ_ODKAZ_NA_TVOJI_TABULKU"

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
        # Načtení existujících dat
        df = conn.read(spreadsheet=SHEET_URL)
    except:
        # Pokud je tabulka prázdná, vytvoříme prázdný DataFrame
        df = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Poznamka"])

    # --- (Zde následuje kód pro Osevní plán a Mřížku, stejný jako dříve) ---
    # ... zkráceno pro přehlednost, princip zůstává ...

    # --- 2. ZÁPIS NOVÝCH DAT DO GOOGLE SHEETS ---
    with st.form("cloud_form"):
        # (vstupní pole pro plodinu, záhon, pozici...)
        # ... 
        submit = st.form_submit_button("Zasadit online")
        
        if submit:
            # Výpočet dat
            # ...
            # Vytvoření nového řádku
            new_row = pd.DataFrame([{
                "Plodina": crop, "Záhon": zahon, "Pozice": pos, 
                "Datum_Vysadby": datum.strftime('%Y-%m-%d'), 
                "Ocekavana_Sklizen": sklizen.strftime('%Y-%m-%d'), 
                "Poznamka": note
            }])
            
            # Spojení starých dat s novým řádkem
            updated_df = pd.concat([df, new_row], ignore_index=True)
            
            # Zápis zpět do Google Sheets
            conn.update(spreadsheet=SHEET_URL, data=updated_df)
            st.success("Zapsáno do Google Tabulek!")
            st.rerun()

if __name__ == "__main__":
    main()