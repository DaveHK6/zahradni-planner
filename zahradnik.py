import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import requests
import plotly.express as px  # Moderní knihovna pro časové osy

# --- 1. KONSTANTY A TEXTOVÁ DOKUMENTACE ---

TEXT_ZAHON_1 = """
### 🏰 ZÁHON 1: Cuketové království
Tento záhon je zaměřen na rychlou jarní vitamínovou bombu a následně na hlavní letní úrodu.

| Období | Plodina | Poznámka k pěstování |
| :--- | :--- | :--- |
| Březen – Květen | Ředkvičky + Jarní špenát | Vysévejte v polovině března. Přikryjte bílou netkanou textilií – v 500 m n. m. jim vytvoří mikroklima. |
| Konec května – Září | Tykev cuketa Tondo di Piacenza | Po sklizni ředkviček vysaďte sazenice. Do každé jamky lžičku Trichodermy. Nezapomeňte na PET lahve s Blumatem. |
| Září – Listopad | Polníček / Zimní špenát | Po cuketách záhon nevynechejte. Tyto plodiny vydrží mráz a v říjnu z nich máte skvělý salát. |
"""

TEXT_ZAHON_2 = """
### 🔄 ZÁHON 2: Česnekovo-fazolová rotace
Tento záhon využíva fakt, že česnek uvolní místo v červenci, což otevírá prostor pro 'druhou směnu' letní zeleniny.

| Období | Plodina | Poznámka k pěstování |
| :--- | :--- | :--- |
| Listopad – Červenec | Zimní česnek | Sázíte na podzim. Přes zimu o něm nevíte, v červenci sklízíte vlastní palice. |
| Červenec – Září | Sazenice rajčat + Keříčkové fazole | Do prázdných míst po česneku dejte už vzrostlé sazenice rajčat a do volných řádků vysejte fazole. |
| Srpen – Říjen | Asijské saláty (Pak Choi / Mizuna) | Vysejte mezi fazole. Rostou raketově a nevadí jim chladnější zářijové noci v horách. |

**Tipy pro úspěch v 500 m n. m.:** Po česneku prolijte půdu Razorminem. Blumat adaptéry u rajčat jsou nutnost!
"""

# --- 2. POMOCNÉ FUNKCE (LOGIKA) ---

def get_weather_data(api_key, city):
    """Získává rozšířená data o počasí."""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=cz"
        res = requests.get(url, timeout=5).json()
        return res if res.get("cod") == 200 else None
    except:
        return None

def update_db(conn, sheet_name, data):
    """Pomocná funkce pro zápis do Google Sheets."""
    conn.update(worksheet=sheet_name, data=data)

def archive_plant(conn, main_df, arch_df, target_idx, main_sheet, arch_sheet):
    """Logika přesunu plodiny do archivu."""
    row = main_df.loc[[target_idx]].copy()
    row['Datum_Sklizne'] = pd.Timestamp(datetime.now())
    update_db(conn, arch_sheet, pd.concat([arch_df, row], ignore_index=True))
    update_db(conn, main_sheet, main_df.drop(target_idx))
    st.balloons()

def create_gantt_chart(df):
    """Vytvoří Ganttův diagram pomocí Plotly Express."""
    if df.empty:
        return None
    
    # OPRAVA: Zde jsem odebral neplatné parametry 'start' a 'finish'
    fig = px.timeline(
        df, 
        x_start="Datum_Vysadby", 
        x_end="Ocekavana_Sklizen", 
        y="Plodina",
        color="Záhon",
        hover_data=["Pozice"],
        title="Harmonogram pěstování",
        template="plotly_white"
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(xaxis_title="Datum", yaxis_title="Plodina", xaxis=dict(tickformat="%d.%m."))
    return fig

# --- 3. HLAVNÍ FUNKCE APP ---

def main():
    st.set_page_config(page_title="Zahradní Manažer Pro", layout="wide", page_icon="🌱")
    
    # Konfigurace GSheets
    MAIN_SHEET = "List 1"
    ARCHIVE_SHEET = "Archiv"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Načtení dat
    try:
        df_real = conn.read(worksheet=MAIN_SHEET, ttl=0).dropna(how="all")
        for col in ['Datum_Vysadby', 'Ocekavana_Sklizen', 'Posledni_Hnojeni']:
            if col in df_real.columns:
                df_real[col] = pd.to_datetime(df_real[col], dayfirst=True, errors='coerce')
    except:
        df_real = pd.DataFrame(columns=["Plodina", "Záhon", "Pozice", "Datum_Vysadby", "Ocekavana_Sklizen", "Posledni_Hnojeni"])

    PLANT_DATABASE = {
        "Ředkvičky": {"growth": 30, "sensitive": False},
        "Jarní špenát": {"growth": 45, "sensitive": False},
        "Cuketa Tondo di Piacenza": {"growth": 70, "sensitive": True},
        "Zimní česnek": {"growth": 240, "sensitive": False},
        "Rajčata": {"growth": 90, "sensitive": True},
        "Keříčkové fazole": {"growth": 65, "sensitive": True},
        "Pak Choi / Mizuna": {"growth": 40, "sensitive": False}
    }

    # --- SEKCE POČASÍ ---
    st.title("🌱 Zahradní Manažer Pro")
    if "weather" in st.secrets:
        w = get_weather_data(st.secrets["weather"]["api_key"], st.secrets["weather"]["city"])
        if w:
            temp, hum, wind = w["main"]["temp"], w["main"]["humidity"], w["wind"]["speed"]
            desc, icon = w["weather"][0]["description"], w["weather"][0]["icon"]
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Teplota", f"{temp} °C")
            c2.metric("Vlhkost", f"{hum} %")
            c3.metric("Vítr", f"{wind} m/s")
            c4.image(f"http://openweathermap.org/img/wn/{icon}.png", width=60)
            
            with st.container():
                if temp < 5.0:
                    st.error(f"❄️ **POZOR NA MRÁZ!** Teplota {temp}°C. Chraňte citlivé rostliny!")
                elif temp > 25.0 and hum < 40:
                    st.warning("☀️ **VAROVÁNÍ PŘED SUCHEM:** Zkontrolujte závlahu.")
                if wind > 10.0:
                    st.info("💨 **SILNÝ VÍTR:** Zkontrolujte opory u rajčat.")

    st.divider()

    # --- TABY ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Přehled", "🗺️ Mapa", "⏳ Časová osa", "⚙️ Správa", "📂 Archiv"])

    with tab1:
        st.markdown(TEXT_ZAHON_1)
        st.markdown(TEXT_ZAHON_2)
        if not df_real.empty:
            st.subheader("📊 Aktuálně v zemi")
            df_disp = df_real.copy()
            for col in ['Datum_Vysadby', 'Ocekavana_Sklizen', 'Posledni_Hnojeni']:
                if col in df_disp.columns:
                    df_disp[col] = df_disp[col].dt.strftime('%d.%m.%Y').replace('NaT', '-')
            st.dataframe(df_disp, use_container_width=True, hide_index=True)

    with tab2:
        st.header("🗺️ Mapa osázení")
        for bed in ["Záhon 1", "Záhon 2"]:
            with st.expander(bed, expanded=True):
                for r in list("ABCDEF"):
                    cols = st.columns(3)
                    for i, c in enumerate([1, 2, 3]):
                        pos = f"{r}{c}"
                        match = df_real[(df_real["Záhon"] == bed) & (df_real["Pozice"] == pos)]
                        with cols[i]:
                            if not match.empty:
                                st.success(f"**{pos}**\n\n{match.iloc[-1]['Plodina']}")
                            else:
                                st.info(f"**{pos}**")

    with tab3:
        st.header("⏳ Harmonogram pěstování")
        if not df_real.empty:
            fig = create_gantt_chart(df_real)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Zatím nemáte nic zasazeno.")

    with tab4:
        st.header("⚙️ Správa")
        with st.form("new_plant_form"):
            c1, c2, c3 = st.columns(3)
            p_crop = c1.selectbox("Plodina", list(PLANT_DATABASE.keys()))
            p_bed = c2.selectbox("Záhon", ["Záhon 1", "Záhon 2"])
            p_pos = c3.selectbox("Pozice", [f"{r}{c}" for r in "ABCDEF" for c in [1,2,3]])
            p_date = st.date_input("Datum výsadby", datetime.now())
            if st.form_submit_button("Zasadit"):
                expected = pd.Timestamp(p_date) + timedelta(days=PLANT_DATABASE[p_crop]["growth"])
                new_row = pd.DataFrame([{"Plodina": p_crop, "Záhon": p_bed, "Pozice": p_pos, "Datum_Vysadby": pd.Timestamp(p_date), "Ocekavana_Sklizen": expected}])
                update_db(conn, MAIN_SHEET, pd.concat([df_real, new_row], ignore_index=True))
                st.rerun()

        if not df_real.empty:
            st.divider()
            target = st.selectbox("Vyberte rostlinu pro akci", df_real.index, format_func=lambda x: f"{df_real.loc[x, 'Plodina']} ({df_real.loc[x, 'Pozice']})")
            h, s, d = st.columns(3)
            if h.button("💧 Zapsat hnojení"):
                df_real.at[target, 'Posledni_Hnojeni'] = pd.Timestamp(datetime.now())
                update_db(conn, MAIN_SHEET, df_real)
                st.rerun()
            if s.button("🧺 Sklidit a Archivovat"):
                try: df_arch = conn.read(worksheet=ARCHIVE_SHEET, ttl=0).dropna(how="all")
                except: df_arch = pd.DataFrame()
                archive_plant(conn, df_real, df_arch, target, MAIN_SHEET, ARCHIVE_SHEET)
                st.rerun()
            if d.button("🗑️ Smazat"):
                update_db(conn, MAIN_SHEET, df_real.drop(target))
                st.rerun()

    with tab5:
        st.header("📂 Archiv")
        try:
            df_arch_disp = conn.read(worksheet=ARCHIVE_SHEET, ttl=0)
            if not df_arch_disp.empty:
                for col in df_arch_disp.columns:
                    if any(x in col for x in ['Datum', 'Ocekavana', 'Sklizne']):
                        df_arch_disp[col] = pd.to_datetime(df_arch_disp[col], errors='coerce').dt.strftime('%d.%m.%Y')
                st.dataframe(df_arch_disp, use_container_width=True, hide_index=True)
        except:
            st.info("Archiv je prázdný.")

if __name__ == "__main__":
    main()