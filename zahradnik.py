import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACE ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1GVqF6BobYV7nuOPZzgBwi5sp3v8y5iV1QxhMRnIUs48/edit?gid=0#gid=0"

GROWTH_PERIODS = {
    "Ředkvičky": 30, "Špenát": 45, "Kulaté cukety (Tondo)": 60,
    "Polníček": 50, "Zimní salát": 60, "Zimní česnek": 240,
    "Sazenice rajčat": 75, "Keříčkové fazole": 65, "Vodnice": 60, "Černá ředkev": 90
}

def main():
    st.set_page_config(page_title="Záhon Planner Cloud", layout="wide")
    st.title("🌱 Cloudový Zahradní Plánovač")

    conn = st.connection("gsheets", type=GSheetsConnection)
    
    try:
        # ttl=0 zajistí, že data budou vždy čerstvá
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        df = df.dropna(how="all")
    except Exception:
        df = pd.DataFrame()

    # --- POJISTKA PRO CHYBĚJÍCÍ SLOUPCE ---
    required_columns = ["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Poznamka"]
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    # --- OSEVNÍ PLÁN (Zobrazení zůstává stejné) ---
    st.header("ZÁHON 1: Jarní vitaminy")
    # ... (zde jsou tvé tabulky s osevním plánem) ...

    # --- MŘÍŽKA ZÁHONŮ ---
    st.divider()
    st.subheader("🖼️ Aktuální osázení")
    z_tabs = st.tabs(["Záhon 1", "Záhon 2"])
    
    for i, tab in enumerate(z_tabs):
        z_name = f"Záhon {i+1}"
        with tab:
            for r in ["A", "B", "C", "D", "E", "F"]:
                cols = st.columns(3)
                for s in range(1, 4):
                    p = f"{r}{s}"
                    with cols[s-1]:
                        # Nyní už sloupec 'Záhon' a 'Pozice' zaručeně existují díky pojistce
                        match = df[(df["Záhon"] == z_name) & (df["Pozice"] == p)]
                        if not match.empty and match.iloc[-1]["Plodina"]:
                            st.caption(f"📍 {p}")
                            st.success(f"**{match.iloc[-1]['Plodina']}**")
                        else:
                            st.caption(f"📍 {p}")
                            st.code("volno")

    # --- FORMULÁŘ PRO ZÁPIS ---
    # ... (zbytek tvého kódu pro formulář a historii) ...
    # (Při ukládání použij: conn.update(spreadsheet=SHEET_URL, data=updated_df))

if __name__ == "__main__":
    main()