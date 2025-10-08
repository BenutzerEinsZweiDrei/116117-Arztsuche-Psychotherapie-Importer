import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="Tages-Telefonkontakte", page_icon="📞", layout="centered")

st.title("📞 Tages-Telefonkontakte")

uploaded_file = st.file_uploader("Bitte Excel-Datei hochladen", type=["xlsx"])

if uploaded_file is not None:
    excel = pd.ExcelFile(uploaded_file)
    sheet_name = excel.sheet_names[1] if len(excel.sheet_names) > 1 else excel.sheet_names[0]
    df = pd.read_excel(excel, sheet_name=sheet_name)

    today = datetime.today().strftime("%A")
    weekdays_map = {
        "Monday": "Mo", "Tuesday": "Di", "Wednesday": "Mi",
        "Thursday": "Do", "Friday": "Fr", "Saturday": "Sa", "Sunday": "So"
    }
    today_de = weekdays_map.get(today, today)

    st.subheader(f"Heutige Kontakte – {today_de}")

    if "Wochentag" not in df.columns:
        st.error("❌ Keine Spalte 'Wochentag' im Tabellenblatt gefunden.")
    else:
        day_df = df[df["Wochentag"].str.strip().str.lower() == today_de.lower()]

        if day_df.empty:
            st.info(f"Keine Kontakte für {today_de} gefunden.")
        else:
            view_cols = ["Arzt / Ärztin", "Uhrzeit", "Telefon"]
            if not all(col in day_df.columns for col in view_cols):
                st.error("❌ Spalten 'Arzt / Ärztin', 'Uhrzeit' oder 'Telefon' fehlen in der Datei.")
            else:
                if "Status" not in day_df.columns:
                    day_df["Status"] = ""
                if "Notiz" not in day_df.columns:
                    day_df["Notiz"] = ""

                st.markdown("---")
                st.markdown("### 💬 Kontakt-Chat")

                for i, row in day_df.iterrows():
                    with st.chat_message("user"):
                        st.markdown(f"**{row['Arzt / Ärztin']}**  \n🕒 {row['Uhrzeit']}  \n📞 {row['Telefon']}")

                    with st.chat_message("assistant"):
                        status = st.radio(
                            f"Status für {row['Arzt / Ärztin']}",
                            ["Noch offen", "Nicht Erreicht", "Auf AB gesprochen", "Auf Warteliste"],
                            key=f"status_{i}",
                            horizontal=True
                        )
                        day_df.at[i, "Status"] = status if status != "Noch offen" else ""

                        note = st.text_input(
                            f"Notiz zu {row['Arzt / Ärztin']}",
                            key=f"note_{i}",
                            placeholder="Kurze Notiz (optional)"
                        )
                        day_df.at[i, "Notiz"] = note

                        st.markdown("---")
                # Fortschritt berechnen
                total = len(day_df)
                done = day_df["Status"].replace("", pd.NA).notna().sum()
                progress = done / total
            

                st.markdown("### 📊 Fortschritt")
                st.progress(progress)
                st.write(f"{done} von {total} Kontakten bearbeitet")
              
                if all(day_df["Status"].replace("", pd.NA).notna()):
                    st.success("🎉 Alle Kontakte für heute wurden bearbeitet!")

                # Download der aktualisierten Datei
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    merged_df = df.merge(
                        day_df[["Arzt / Ärztin", "Uhrzeit", "Status", "Notiz"]],
                        on=["Arzt / Ärztin", "Uhrzeit"],
                        how="left",
                        suffixes=("", "_neu")
                    )
                    merged_df.to_excel(writer, sheet_name=sheet_name, index=False)

                st.download_button(
                    "📥 Aktualisierte Excel-Datei herunterladen",
                    data=output.getvalue(),
                    file_name="aktualisierte_kontakte.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
