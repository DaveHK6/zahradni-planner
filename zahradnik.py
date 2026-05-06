import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests

# --- KONFIGURACE STRÁNKY ---
st.set_page_config(page_title="Zahrada Polánka", layout="wide", page_icon="🌱")

# --- FUNKCE PRO POČASÍ ---
def get_weather(api_key, city):
    """Získá data o počasí a vrátí (teplota, popis, chyba)."""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=cz"
        response = requests.get(url)
        res = response.json()
        if res.get("cod") == 200:
            return res['main']['temp'], res['weather'][0]['description'], None
        else:
            return None, None, res.get("message", "Neznámá chyba")
    except Exception as e:
        return None, None, str(e)

# --- HLAVNÍ APLIKACE ---
def main():
    st.title("🌱 Zahradní manažer - Polánka")

    # 1. SEKCE POČASÍ (Data ze st.secrets)
    try:
        if "weather" in st.secrets:
            w_api = st.secrets["weather"]["api_key"]
            w_city = st.secrets["weather"]["city"]
            temp, desc, err = get_weather(w_api, w_city)
            
            if temp is not None:
                col_w1, col_w2 = st.columns([1, 4])
                col_w1.metric("Teplota", f"{temp} °C")
                status_text = f"🌤️ Aktuálně v Polánce: {desc.capitalize()}."
                if temp < 3:
                    col_w2.error(f"{status_text} POZOR NA MRAZÍKY!")
                else:
                    col_w2.success(status_text)
            else:
                st.warning(f"⚠️ Počasí: API klíč se aktivuje nebo je chybný ({err}).")
        else:
            st.info("💡 Tip: Pro počasí doplň [weather] sekci do Secrets.")
    except Exception as e:
        st.error(f"Chyba při načítání počasí: {e}")

    st.divider()

    # 2. PŘIPOJENÍ KE GOOGLE SHEETS
    # Tato část vyžaduje nastavené [connections.gsheets] v Secrets
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Načteme data a vymažeme úplně prázdné řádky
        df = conn.read(ttl=0).dropna(how="all")
    except Exception as e:
        st.error(f"Chyba připojení k tabulce: {e}")
        return

    # 3. ROZHRANÍ S TABY (ZÁLOŽKAMI)
    tab1, tab2 = st.tabs(["📋 Aktuální výsadba", "➕ Správa záhonů"])

    # --- TAB 1: ZOBRAZENÍ TABULKY ---
    with tab1:
        if not df.empty:
            st.subheader("Přehled plodin na záhonech")
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Poznámka": st.column_config.TextColumn("Poznámka", width="large"),
                    "Ocekavana_Sklizen": st.column_config.DateColumn("Očekávaná sklizeň"),
                    "Datum_Vysadby": st.column_config.DateColumn("Zasazeno")
                }
            )
        else:
            st.info("V tabulce zatím nejsou žádná data. Přidej první plodinu v záložce Správa záhonů.")

    # --- TAB 2: PŘIDÁVÁNÍ A ARCHIVACE ---
    with tab2:
        col_add, col_arc = st.columns(2)
        
        # Formulář pro přidání nové plodiny
        with col_add:
            st.subheader("Zapsat novou výsadbu")
            with st.form("novy_zaznam", clear_on_submit=True):
                crop = st.text_input("Plodina (např. Rajčata)")
                bed = st.selectbox("Záhon", ["Záhon 1", "Záhon 2", "Záhon 3", "Skleník", "Bylinky"])
                plant_date = st.date_input("Datum výsadby", datetime.now())
                note = st.text_area("Poznámky")
                
                submit = st.form_submit_button("Uložit do Google Sheets")
                
                if submit and crop:
                    # Výpočet sklizně (prozatím fixních 60 dní)
                    harvest_date = plant_date + timedelta(days=60)
                    
                    new_row = pd.DataFrame([{
                        "Plodina": crop,
                        "Záhon": bed,
                        "Datum_Vysadby": plant_date.strftime('%Y-%m-%d'),
                        "Ocekavana_Sklizen": harvest_date.strftime('%Y-%m-%d'),
                        "Poznámka": note
                    }])
                    
                    # Spojení starých dat s novým řádkem
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(data=updated_df)
                    st.success(f"✅ {crop} uloženo!")
                    st.rerun()

        # Sekce pro odstranění (archivaci)
        with col_arc:
            st.subheader("Odebrat sklizené")
            if not df.empty:
                to_delete = st.selectbox(
                    "Vyber plodinu ke smazání", 
                    df.index, 
                    format_func=lambda x: f"{df.iloc[x]['Plodina']} ({df.iloc[x]['Záhon']})"
                )
                if st.button("🗑️ Odstranit z aktivních"):
                    updated_df = df.drop(index=to_delete)
                    conn.update(data=updated_df)
                    st.toast("Položka byla odstraněna.")
                    st.rerun()
            else:
                st.write("Žádná data k odstranění.")

if __name__ == "__main__":
    main()