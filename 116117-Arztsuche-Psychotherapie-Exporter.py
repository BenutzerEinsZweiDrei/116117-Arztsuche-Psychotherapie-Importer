import streamlit as st
import pandas as pd
import requests
import openpyxl
from datetime import datetime, timedelta  # <-- timedelta ergänzt
import time
import base64  # <-- hinzugefügt für req-val Berechnung
from zoneinfo import ZoneInfo  # <-- hinzugefügt für Zeitzone Europe/Berlin
import re  # <-- hinzugefügt für robuste Zeitformat-Parsing

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

# ---- Neu: Helfer für "jetzt telefonisch erreichbar" & "nächste Zeitfenster" ----
def _parse_time(hhmm: str):
    return datetime.strptime(hhmm.strip(), "%H:%M").time()

weekday_idx_map = {"Mo.": 0, "Di.": 1, "Mi.": 2, "Do.": 3, "Fr.": 4, "Sa.": 5, "So.": 6}

def is_reachable_now(arzt: dict, now_dt: datetime) -> bool:
    """Prüft, ob der Eintrag jetzt (Europe/Berlin) telefonisch erreichbar ist."""
    today_idx = now_dt.weekday()

    for ts in arzt.get("tsz", []):
        tag = ts.get("t", "")
        if weekday_idx_map.get(tag, -1) != today_idx:
            continue
        for ts_typ in ts.get("tszDesTyps", []):
            if ts_typ.get("typ") != "Telefonische Erreichbarkeit":
                continue
            for sprechzeit in ts_typ.get("sprechzeiten", []):
                raw = (sprechzeit.get("zeit", "") or "").replace(" ", "")
                # mehrere Intervalle per ; oder , getrennt erlauben
                for interval in re.split(r"[;,]", raw):
                    if not interval or "-" not in interval:
                        continue
                    try:
                        start_s, end_s = interval.split("-")
                        start_t, end_t = _parse_time(start_s), _parse_time(end_s)
                        if start_t <= now_dt.time() <= end_t:
                            return True
                    except Exception:
                        continue
    return False

def todays_phone_windows(arzt: dict, now_dt: datetime) -> str:
    """Gibt alle heutigen Telefonzeiten als kommagetrennte Liste zurück (für Anzeige)."""
    today_idx = now_dt.weekday()
    windows = []
    for ts in arzt.get("tsz", []):
        if weekday_idx_map.get(ts.get("t", ""), -1) != today_idx:
            continue
        for ts_typ in ts.get("tszDesTyps", []):
            if ts_typ.get("typ") == "Telefonische Erreichbarkeit":
                for sprechzeit in ts_typ.get("sprechzeiten", []):
                    w = sprechzeit.get("zeit", "").strip()
                    if w:
                        windows.append(w)
    # Duplikate entfernen, sortiert ausgeben
    return ", ".join(sorted(set(windows)))

def _norm_tel(t: str) -> str:
    # Nur Ziffern behalten -> stabile Vergleichsbasis für Duplikaterkennung
    return re.sub(r"\D+", "", t or "")

def next_available_windows(arzt_liste: list[dict], now_dt: datetime, max_results: int = 5):
    """Sucht die nächsten Telefon-Zeitfenster (nur zukünftige Starts; bis 7 Tage voraus), ohne Duplikate."""
    results = []
    seen = set()  # <-- Duplikate verhindern
    tz = ZoneInfo("Europe/Berlin")
    now_local = now_dt  # already in Europe/Berlin

    for a in arzt_liste:
        name = a.get("name", "") or ""
        tel = a.get("tel", "") or ""
        tel_norm = _norm_tel(tel)
        ort = a.get("ort", "") or ""
        plz = a.get("plz", "") or ""
        arzt_id = a.get("id", "") or ""

        for day_offset in range(0, 7):  # heute + nächste 6 Tage
            day_dt = (now_local + timedelta(days=day_offset)).date()
            for ts in a.get("tsz", []):
                tag = ts.get("t", "")
                if weekday_idx_map.get(tag, -1) != (now_local.weekday() + day_offset) % 7:
                    continue
                for ts_typ in ts.get("tszDesTyps", []):
                    if ts_typ.get("typ") != "Telefonische Erreichbarkeit":
                        continue
                    for sprechzeit in ts_typ.get("sprechzeiten", []):
                        raw = (sprechzeit.get("zeit", "") or "").replace(" ", "")
                        for interval in re.split(r"[;,]", raw):
                            if not interval or "-" not in interval:
                                continue
                            try:
                                start_s, end_s = interval.split("-")
                                start_t, end_t = _parse_time(start_s), _parse_time(end_s)
                                start_dt = datetime.combine(day_dt, start_t).replace(tzinfo=tz)
                                end_dt = datetime.combine(day_dt, end_t).replace(tzinfo=tz)
                                # NUR echte Zukunft: Start > jetzt (keine laufenden Slots)
                                if start_dt > now_local:
                                    key = (arzt_id, name.strip(), tel_norm, start_dt, end_dt)
                                    if key in seen:
                                        continue
                                    seen.add(key)
                                    results.append({
                                        "Start": start_dt,
                                        "Ende": end_dt,
                                        "Name": name,
                                        "Telefon": tel,
                                        "Ort": ort,
                                        "PLZ": plz
                                    })
                            except Exception:
                                continue
    # Nach Startzeit sortieren und begrenzen
    results_sorted = sorted(results, key=lambda x: x["Start"])[:max_results]
    return results_sorted

# Streamlit App

# Page config
st.set_page_config(
    page_title="Therapie-Kontakte in deiner Nähe",
    page_icon="🔎",
    layout="centered"
)

# Title + Subtitle
st.title("🔎 Therapie-Kontakte in deiner Nähe")
st.markdown(
    "#### Bis zu 100 Kontakte von 116117 als Excel-Download – mit einfacher Anrufliste. Spart dir Zeit und Nerven."
)


# Sidebar für Hilfestellung
with st.sidebar:
    st.header("ℹ️ Infos")
    st.markdown("""

                
    Die Suche nach einem Therapieplatz ist oft mühsam.\n Diese App soll es dir erleichtern: Sie sammelt und strukturiert die Daten von [arztsuche.116117.de](https://arztsuche.116117.de/) und lädt sie für dich als Excel-Datei herunter.\n\n
    Du erhältst bis zu 100 Einträge mit Kontaktdaten und einen übersichtlichen Wochenplan der Telefonsprechzeiten – hilfreich für deine Suche oder als Nachweis bei der Krankenkasse. 
                
    Selbstverständlich ist diese App kostenlos.

    ---
               
    Diese App speichert keine persönlichen Daten.
    Es gibt keine eigene Datenbank – es werden ausschließlich öffentlich zugängliche Informationen neu aufbereitet.
    
    ---

    Diese App verwendet Daten aus dem Repository [WZBSocialScienceCenter/plz_geocoord](https://github.com/WZBSocialScienceCenter/plz_geocoord), lizenziert unter Apache 2.0.  
    """)


# PLZ Eingabe für den User
postcode = st.text_input("Postleitzahl", value="12345")

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

                            # --- Jetzt erreichbar (Europe/Berlin) ---
                            try:
                                now_berlin = datetime.now(ZoneInfo("Europe/Berlin"))
                                reachable = [a for a in arzt_praxis_daten if is_reachable_now(a, now_berlin)]

                                st.subheader("📞 Jetzt telefonisch erreichbar")
                                st.caption(f"Aktuelle Zeit: {now_berlin.strftime('%a, %d.%m.%Y %H:%M')} – Treffer: {len(reachable)}")

                                if reachable:
                                    df_now = pd.DataFrame([{
                                        "Name": a.get("name", ""),
                                        "Telefon": a.get("tel", ""),
                                        "Ort": a.get("ort", ""),
                                        "PLZ": a.get("plz", ""),
                                        "Zeiten heute": todays_phone_windows(a, now_berlin),
                                        "Entfernung (m)": a.get("distance", "")
                                    } for a in reachable])

                                    if "Entfernung (m)" in df_now.columns:
                                        df_now = df_now.sort_values(by=["Entfernung (m)"], kind="stable")

                                    st.dataframe(df_now.head(10), use_container_width=True, hide_index=True)
                                else:
                                    st.info("Gerade ist leider niemand mit ausgewiesener telefonischer Erreichbarkeit verfügbar.")

                                # --- Immer anzeigen: Nächste verfügbare Telefonsprechzeiten (Top 5) ---
                                next_slots = next_available_windows(arzt_praxis_daten, now_berlin, max_results=5)
                                if next_slots:
                                    st.subheader("⏭️ Nächste Telefonsprechzeiten")
                                    df_next = pd.DataFrame([{
                                        "Telefonsprechzeit": f'{s["Start"].strftime("%d.%m.%Y %H:%M")} bis {s["Ende"].strftime("%H:%M")}',
                                        "Name": s["Name"],
                                        "Telefon": s["Telefon"],
                                        "Ort": s["Ort"],
                                        "PLZ": s["PLZ"]
                                    } for s in next_slots])
                                    st.dataframe(df_next, use_container_width=True, hide_index=True)
                                else:
                                    st.caption("Keine kommenden Telefonsprechzeiten in den nächsten 7 Tagen gefunden.")

                            except Exception as e:
                                st.warning(f"Vorschau konnte nicht angezeigt werden: {e}")

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
                                time.sleep(0.05)  # Simuliere eine Pause von 20ms "oh da passiert ja was!"
                                progress_bar.progress(i + 1)

                            # Speichern der Datei
                            wb.save("116117_therapeuten_mit_sprechstunden.xlsx")
                            
                            # Download-Button anzeigen
                            with open("116117_therapeuten_mit_sprechstunden.xlsx", "rb") as file:
                                st.download_button(
                                    label="📥 Excel-Datei mit Therapie-Kontakten herunterladen",
                                    data=file,
                                    file_name="116117_therapeuten_mit_sprechstunden.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )

                            st.info("Viel Erfolg bei der Suche nach einer Therapie! :)")
                        else:
                            st.error("❌ Antwort enthält keine 'arztPraxisDatas'.")
                    except Exception as e:
                        st.error(f"⚠️ Fehler beim Parsen der Antwort: {e}")
                else:
                    st.error(f"❌ Anfrage fehlgeschlagen (Statuscode {response.status_code})")
            except requests.exceptions.RequestException as e:
                st.error(f"Fehler bei der Anfrage: {e}")
