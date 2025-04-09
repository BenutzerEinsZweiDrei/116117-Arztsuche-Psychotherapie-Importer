import streamlit as st
import pandas as pd
import requests
import openpyxl
from datetime import datetime
import time

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

# Streamlit App
st.set_page_config(page_title="116117 Therapie Finder", page_icon="🧠", layout="centered")

st.title("🧠 116117 Psychotherapie Finder")
st.markdown("Die Suche nach einem Therapieplatz kann ganz schön anstrengend sein. Diese App soll dir dabei helfen! Sie speichert die Daten von https://arztsuche.116117.de/ strukturiert, damit du dir das lästige Copy & Paste sparen kannst. \n\n Du bekommst eine Liste mit maximal 100 Psychotherapeut*innen sowie einen Wochenplan der Telefonsprechzeiten. So wird die Suche nach einem Therapieplatz hoffentlich leichter – oder dein Antrag auf Kostenerstattung etwas unkomplizierter! :) \n\n Links findest du Hinweise zu den req-val- und Authorization-Code-Feldern, die für die 116117 API notwendig sind.")

# Sidebar für Hilfestellung
with st.sidebar:
    st.header("🧑‍💻 Wie finde ich req-val und Authorization?")
    st.markdown("""
                
    🛈 Die Authorization- und req-val-Werte sind notwendig, um die API-Anfrage zu authentifizieren.\n
                
    **1. Gehe auf 116117:**  
    Öffne die Webseite [https://arztsuche.116117.de/](https://arztsuche.116117.de/)

    **2. Öffne die Entwicklertools:**  
    Drücke `CTRL + SHIFT + I` oder rechtsklicke auf die Seite und wähle „Untersuchen“, um die Entwicklertools zu öffnen.

    **3. Gehe zum Tab "Network":**

    **4. Führe eine Suche durch:**  
    Suche nach Psychotherapie mit der selben PLZ, wie hier.

    **5. Finde die Anfrage "data" im Network tab:**  
    Im Network tab solltest du jetzt viele Werte sehen. Klicke auf die Anfrage „data“, die erscheint, nachdem die Seite die Therapeuten lädt.

    **6. Authorization und req-val finden:**  
    - Im Reiter **"Headers"** unter **"Request Headers"** findest du die beiden Werte:
        - **Authorization**: Der Wert, der nach „Basic“ folgt.
        - **req-val**: Der Wert, der nach „req-val“ steht.
    
    Du kannst diese Werte dann in das App-Formular eintragen und suchen! :) \n

    ---
    
    **❓ Warum hast du diese App gebaut?**  
    Ich habe die App gebaut, weil es extrem schwer ist, einen Therapieplatz mit gesetzlicher Versicherung zu finden. Man muss oft zig Praxen anrufen, bekommt nur Absagen, Wartezeiten betragen häufig 1 Jahr und der ganze Prozess ist sehr kräftezehrend. Mit der App will ich den Prozess erleichtern: schnell, strukturiert, mit Sprechzeiten. Und: Wer keinen Platz findet, kann die Excel-Datei als Basis für den Kontaktnachweis für die Krankenkasse nutzen, um eine Kostenerstattung bei Systemversagen zu beantragen. Zudem kann ein Export der Arztsuche als Datei sehbinderten Personen helfen, siehe https://fragdenstaat.de/a/299392.

    ---            
    Diese App verwendet Daten aus dem Repository [WZBSocialScienceCenter/plz_geocoord](https://github.com/WZBSocialScienceCenter/plz_geocoord), das unter der Apache License 2.0 lizenziert ist. Weitere Informationen unter: http://www.apache.org/licenses/.
                                
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

# Eingabefelder für req-val und Authorization
req_val = st.text_input("🔑 Req-val (siehe Hinweise links)", value="XXXXXXXXXx==")
auth_code = st.text_input("🔐 Authorization Code (nach 'Basic ')", value="XXXXXXXXXXXXXXXXXXXXXx==")

if st.button("🔎 Psychotherapeut*innen finden"):
    if not req_val or not auth_code:
        st.warning("Bitte gib sowohl req-val als auch Authorization Code ein.")
    elif not postcode:
        st.warning("Bitte gib eine Postleitzahl ein.")
    else:
        # Holen der Koordinaten aus der CSV-Datei
        lat, lon = get_lat_lon_from_plz(postcode)

        if lat is not None and lon is not None:
            url = "https://arztsuche.116117.de/api/data"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                "Host": "arztsuche.116117.de",
                "req-val": req_val,
                "Authorization": f"Basic {auth_code}"
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
