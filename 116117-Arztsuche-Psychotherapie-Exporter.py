import streamlit as st
import pandas as pd
import requests
import openpyxl
from datetime import datetime
import time
import base64  # <-- hinzugefügt für req-val Berechnung

# Funktion, um die Koordinaten aus der CSV-Datei zu holen
def get_lat_lon_from_plz(postcode):
    try:
        # Lese die CSV-Datei mit den PLZ-Koordinaten
        df = pd.read_csv("plz_geocoord.csv")
        
        # Suche nach der Zeile mit der passenden PLZ
        result = df[df['plz'] == int(postcode)]
        
        # Überprüfen, ob die PLZ gefunden wurde
        if not result.empty:
            lat = result['lat'].values[0]
            lng = result['lng'].values[0]
            return lat, lng
        else:
            st.warning(f"Keine Koordinaten für die PLZ {postcode} gefunden.")
            return None, None
    except FileNotFoundError as e:
        st.error(f"Datei 'plz_geocoord.csv' wurde nicht gefunden: {e}")
        return None, None
    except Exception as e:
        st.error(f"Fehler beim Lesen der CSV-Datei: {e}")
        return None, None

# --- req-val Generator (Port der JS-Funktion), wie vorgeschlagen ---
def c(e: float, t: float):
    e += 1.1
    [r, a] = str(e).split('.')
    n = r[len(r) - 1]

    t += 2.3
    [l, c_] = str(t).split('.')
    o = l[len(l) - 1]

    s = "000" # time seems not to be checked

    d = n + s[len(s) - 1] + o + s[len(s) - 2] + a[0] + s[len(s) - 3] + c_[0]
    return base64.b64encode(d.encode("utf-8"))

# Streamlit App
st.set_page_config(page_title="116117 Therapie Finder", page_icon="🧠", layout="centered")

st.title("🧠 116117 Psychotherapie Finder")
st.write("")
st.markdown("""
Die Suche nach einem Therapieplatz ist oft mühsam.\n
Diese App erleichtert dir den Prozess: Sie sammelt und strukturiert die Daten von [arztsuche.116117.de](https://arztsuche.116117.de/), damit du dir Copy & Paste sparen kannst.\n\n
Du erhältst bis zu 100 Einträge mit Kontaktdaten und einen übersichtlichen Wochenplan der Telefonsprechzeiten – hilfreich für deine Suche oder als Nachweis bei der Krankenkasse. 🙂
""")
st.write("")

# Sidebar für Hilfestellung
with st.sidebar:
    st.header("FAQ")
    st.markdown("""
          
    **🔎 Wie funktioniert die App?**  

    - Du gibst eine Postleitzahl und ein paar Filter ein.  
    - Die App sucht automatisch nach Psychotherapeut*innen in deiner Nähe.  
    - Sie bereinigt doppelte Einträge und fasst die wichtigsten Daten zusammen.  
    - Am Ende kannst du alles als Excel-Datei herunterladen – praktisch für deine Anrufliste oder als Nachweis für die Krankenkasse.     
    
    **❓ Warum existiert diese App?**  

    Therapieplätze sind rar, besonders mit gesetzlicher Versicherung.  
    Oft muss man zig Praxen anrufen, bekommt Absagen, und Wartezeiten betragen bis zu 1 Jahr.  
    Dieser Prozess ist sehr kräftezehrend.  

    Die App soll dir Zeit und Nerven sparen: schnell, strukturiert, mit Sprechzeiten.  
    Und wenn du keinen Platz findest, kannst du die Excel-Datei als Nachweis bei der Krankenkasse nutzen, um eine Kostenerstattung zu beantragen.  

    Zusätzlich ist der Export für sehbehinderte Menschen hilfreich, weil die Infos barrierefrei in Excel vorliegen (siehe [FragDenStaat](https://fragdenstaat.de/a/299392)).  

    **⚙️ Ein Blick hinter die Kulissen**  

    Die App nutzt die gleiche offizielle Datenquelle wie die 116117-Webseite.  
    Normalerweise sind die Daten nur für den Browser gedacht – hier übernimmt die App den technischen Teil:  
    - Sie erzeugt automatisch die notwendigen Zugangscodes  
    - Fragt die Daten ab  
    - Strukturiert sie neu in einer Excel-Datei  

    Keine eigenen Datenbanken, keine Speicherung persönlicher Daten – nur die öffentlich zugänglichen Infos werden neu aufbereitet.  

    ---  
    Diese App verwendet Daten aus dem Repository [WZBSocialScienceCenter/plz_geocoord](https://github.com/WZBSocialScienceCenter/plz_geocoord), lizenziert unter Apache 2.0.  
    """)


# PLZ Eingabe für den User
postcode = st.text_input("📍 Postleitzahl", value="12345")

# Auswahl für Psychotherapie: Verfahren
verfahren_options = {
    "Analytische Psychotherapie": "A",
    "Systemische Therapie": "S",
    "Tiefenpsychologisch fundierte Psychotherapie": "T",
    "Verhaltenstherapie": "V"
}
verfahren_selection = st.selectbox("Verfahren", list(verfahren_options.keys()), index=0)

# Auswahl für Psychotherapie: Altersgruppe
altersgruppe_options = {
    "Erwachsen": "E",
    "Kinder & Jugend": "K"
}
altersgruppe_selection = st.selectbox("Altersgruppe", list(altersgruppe_options.keys()), index=0)

# Auswahl für Psychotherapie: Setting
setting_options = {
    "Einzeltherapie": "E",
    "Gruppentherapie": "G"
}
setting_selection = st.selectbox("Setting", list(setting_options.keys()), index=0)

# --- KEINE User-Inputs für req-val & Authorization: fest hinterlegt / automatisch ---
# Eingabefelder entfernt; statische Authorization + automatische req-val-Berechnung
AUTH_CODE_BASE64 = "YmRwczpma3I0OTNtdmdfZg=="  # vom Nutzer vorgegeben

if st.button("🔎 Psychotherapeut*innen finden"):
    if not postcode:
        st.warning("Bitte gib eine Postleitzahl ein.")
    else:
        # Holen der Koordinaten aus der CSV-Datei
        lat, lon = get_lat_lon_from_plz(postcode)

        if lat is not None and lon is not None:
            url = "https://arztsuche.116117.de/api/data"

            # req-val aus lat/lon erzeugen (Bytes -> String)
            try:
                req_val_final = c(float(lat), float(lon)).decode("utf-8")
            except Exception as e:
                st.error(f"Fehler bei der req-val Generierung: {e}")
                st.stop()

            headers = {
                "Host": "arztsuche.116117.de",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "req-val": req_val_final,
                "Authorization": f"Basic {AUTH_CODE_BASE64}"
            }

            data = {
                "r": 900,
                "lat": lat,
                "lon": lon,
                "filterSelections": [
                    {"title": "Fachgebiet Kategorie", "fieldName": "fgg", "selectedCodes": ["12"]},
                    {"title": "Psychotherapie: Verfahren", "fieldName": "ptv", "selectedCodes": [verfahren_options[verfahren_selection]]},
                    {"title": "Psychotherapie: Altersgruppe", "fieldName": "pta", "selectedCodes": [altersgruppe_options[altersgruppe_selection]]},
                    {"title": "Psychotherapie: Setting", "fieldName": "pts", "selectedCodes": [setting_options[setting_selection]]}
                ],
                "locOrigin": "USER_INPUT",
                "initialSearch": True,
                "viaDeeplink": False
            }

            try:
                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()  # Prüft auf HTTP-Fehlerstatus
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        if "arztPraxisDatas" in response_data:
                            arzt_praxis_daten = response_data["arztPraxisDatas"]

                            wb = openpyxl.Workbook()
                            ws_praxis = wb.active
                            ws_praxis.title = "Praxisdaten"
                            ws_praxis.append(["id", "name", "tel", "geschlecht", "strasse", "hausnummer", "plz", "ort", "email", "distanz in meter von plz", "web", "telefonische_sprechzeiten"])
                            ws_sprechzeiten = wb.create_sheet("Telefonsprechzeiten")
                            ws_sprechzeiten.append(["Wochentag", "Uhrzeit", "Arzt / Ärztin", "Telefon"])
                            wochentage = {"Mo.": "Mo", "Di.": "Di", "Mi.": "Mi", "Do.": "Do", "Fr.": "Fr", "Sa.": "Sa", "So.": "So"}
                            sprechzeiten_dict = {day: {} for day in wochentage.values()}

                            for arzt in arzt_praxis_daten:
                                telefonische_sprechzeiten = set()
                                if "tsz" in arzt:
                                    for ts in arzt["tsz"]:
                                        for ts_typ in ts.get("tszDesTyps", []):
                                            if ts_typ.get("typ") == "Telefonische Erreichbarkeit":
                                                for sprechzeit in ts_typ.get("sprechzeiten", []):
                                                    zeit = sprechzeit.get("zeit", "")
                                                    tag = ts.get("t", "")
                                                    if tag in wochentage:
                                                        telefonische_sprechzeiten.add(f"{wochentage[tag]} {zeit} Uhr")
                                                        if zeit not in sprechzeiten_dict[wochentage[tag]]:
                                                            sprechzeiten_dict[wochentage[tag]][zeit] = set()
                                                        sprechzeiten_dict[wochentage[tag]][zeit].add(f"{arzt.get('name', 'Unbekannt')} (Tel: {arzt.get('tel', 'Nicht angegeben')})")
                                hausnummer = str(arzt.get("hausnummer", ""))
                                if " " in hausnummer or "-" in hausnummer:
                                    hausnummer = f'"{hausnummer}"'

                                ws_praxis.append([
                                    arzt.get("id", ""), arzt.get("name", ""), arzt.get("tel", ""),
                                    arzt.get("geschlecht", ""), arzt.get("strasse", ""), hausnummer,
                                    arzt.get("plz", ""), arzt.get("ort", ""), arzt.get("email", ""),
                                    arzt.get("distance", ""), arzt.get("web", ""),
                                    ", ".join(telefonische_sprechzeiten)
                                ])

                            for wochentag, zeiten in sprechzeiten_dict.items():
                                sorted_zeiten = sorted(zeiten.items(), key=lambda x: datetime.strptime(x[0].split('-')[0], '%H:%M'))
                                for zeit, aerzte in sorted_zeiten:
                                    ws_sprechzeiten.append([wochentag, zeit, ", ".join(aerzte)])

                            # Ladebalken simulieren
                            progress_bar = st.progress(0)
                            for i in range(100):
                                time.sleep(0.02)  # Simuliere eine Pause von 20ms "oh da passiert ja was!"
                                progress_bar.progress(i + 1)

                            # Speichern der Datei
                            wb.save("116117_therapeuten_mit_sprechstunden.xlsx")
                            
                            # Download-Button anzeigen
                            with open("116117_therapeuten_mit_sprechstunden.xlsx", "rb") as file:
                                st.download_button(
                                    label="📥 Excel-Datei herunterladen",
                                    data=file,
                                    file_name="116117_therapeuten_mit_sprechstunden.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )

                            st.info("Viel Erfolg bei der Suche nach einer Therapie!")
                        else:
                            st.error("❌ Antwort enthält keine 'arztPraxisDatas'.")
                    except Exception as e:
                        st.error(f"⚠️ Fehler beim Parsen der Antwort: {e}")
                else:
                    st.error(f"❌ Anfrage fehlgeschlagen (Statuscode {response.status_code})")
            except requests.exceptions.RequestException as e:
                st.error(f"Fehler bei der Anfrage: {e}")
