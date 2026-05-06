import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# --- KONFIGURACE STRÁNKY ---
st.set_page_config(page_title="Zahrada Polánka", layout="wide", page_icon="🌱")

# --- FUNKCE PRO POČASÍ ---
def get_weather(api_key, city):
    """Získá data o počasí pro zadané město."""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=cz"
        res = requests.get(url).json()
        if res.get("cod") == 200:
            return res['main']['temp'], res['weather'][0]['description']
        return None, "Lokalita nenalezena"
    except:
        return None, "Chyba spojení"

# --- HLAVNÍ LOGIKA ---
def main():
    st.title("🌱 Zahradní manažer - Polánka")

    # 1. POČASÍ (Data ze Secrets)
    try:
        w_api = st.secrets["weather"]["api_key"]
        w_city = st.secrets["weather"]["city"]
        temp, desc = get_weather(w_api, w_city)
        
        if temp is not None:
            col_w1, col_w2 = st.columns([1, 4])
            col_w1.metric("Teplota", f"{temp} °C")
            if temp < 3:
                col_w2.error(f"❄️ Varování: V Polánce je {temp}°C. Chraňte rostliny před mrazem!")
            else:
                col_w2.success(f"🌤️ Aktuálně: {desc.capitalize()}. Podmínky pro Polánku jsou dobré.")
    except:
        st.info("Tip: Pro zobrazení počasí nastav [weather] v Secrets.")

    st.divider()

    # 2. PŘIPOJENÍ KE GOOGLE SHEETS
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0).dropna(how="all")

    tab1, tab2 = st.tabs(["📋 Aktuální výsadba", "➕ Přidat / Archivovat"])

    # --- TAB 1: ZOBRAZENÍ ---
    with tab1:
        if not df.empty:
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Poznámka": st.column_config.TextColumn("Poznámka", width="large"),
                    "Ocekavana_Sklizen": st.column_config.DateColumn("Očekávaná sklizeň")
                }
            )
        else:
            st.write("Zatím nemáš nic zasazeno. Šup do Tabu 2!")

    # --- TAB 2: SPRÁVA ---
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Nová plodina")
            with st.form("add_form", clear_on_submit=True):
                new_crop = st.text_input("Co jsi zasadil?")
                new_bed = st.selectbox("Záhon", ["Záhon 1", "Záhon 2", "Skleník"])
                new_date = st.date_input("Datum výsadby", datetime.now())
                new_note = st.text_area("Poznámky (hnojení, odrůda)")
                
                if st.form_submit_button("Uložit do tabulky"):
                    # Výpočet sklizně (příklad: 60 dní)
                    harvest_date = new_date + timedelta(days=60)
                    new_data = pd.DataFrame([{
                        "Plodina": new_crop,
                        "Záhon": new_bed,
                        "Datum_Vysadby": new_date.strftime('%Y-%m-%d'),
                        "Ocekavana_Sklizen": harvest_date.strftime('%Y-%m-%d'),
                        "Poznámka": new_note
                    }])
                    updated_df = pd.concat([df, new_data], ignore_index=True)
                    conn.update(data=updated_df)
                    st.success("Zasazeno! Tabulka se aktualizuje...")
                    st.rerun()

        with col2:
            st.subheader("Sklizeň")
            if not df.empty:
                to_archive = st.selectbox("Co jsi sklidil?", df.index, 
                                          format_func=lambda x: f"{df.iloc[x]['Plodina']} ({df.iloc[x]['Záhon']})")
                if st.button("✅ Hotovo - Archivovat"):
                    updated_df = df.drop(index=to_archive)
                    conn.update(data=updated_df)
                    st.balloons()
                    st.rerun()

if __name__ == "__main__":
    main()