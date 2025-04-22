
import openai
import pdfplumber
from flask import Flask, request, render_template_string, send_file
import os
from docx import Document
import io

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

TEMPLATE_BEFRISTET = """
Arbeitsvertrag (Befristet)

Arbeitgeber:
Hauswartprofis AG, Alte Bahnhofstrasse 7, 5506 Mägenwil

Arbeitnehmer/in:
"Vorname" "Name", "Adresse / Strasse", "PLZ Ort"
Geboren am "Geburtsdatum"

Das Arbeitsverhältnis beginnt per "Eintrittsdatum" und ist befristet bis "Vertragsende". Eine gültige Arbeits- und Aufenthaltsbewilligung wird vorausgesetzt.

Probezeit: drei Monate / entfällt
Für die Berechnung der Dienstjahre gilt der "Datum"

Funktion: "Funktionsbezeichnung"
Funktionsstufe: Stufe 6
Pensum / Arbeitszeit: 100%, 42.0 Stunden / Woche
Angliederung Niederlassung: z. B. Hauswartprofis AG, 5506 Mägenwil
Einsatzort: Kundenobjekt gemäss Tourenplanung / fixes Objekt

Lohn: CHF "Bruttolohn bei 100%" brutto pro Monat
Zuzüglich 13. Monatslohn pro Rata
Abzüglich Beiträge für Sozialversicherungen

Essensentschädigung / Repräsentationsspesen: CHF 350.00 x 12 / CHF 16.00 pro Tag
Ferienanspruch: 25 Tage pro Jahr (bei 100 % Pensum)

Geschäftsfahrzeug: Falls zutreffend, mit privater Nutzung gemäss Fahrzeugreglement
Erfolgsanteil: Falls vereinbart

Allgemeine Bestimmungen:
- Allgemeine Anstellungsbedingungen der Hauswartprofis AG
- Weisungen und Anordnungen des Arbeitgebers
- Spesenreglement(e)
- Fahrzeugreglement

Gerichtsstand: Baden (AG)
"""

TEMPLATE_UNBEFRISTET = """
Arbeitsvertrag (Unbefristet)

Arbeitgeber:
Hauswartprofis AG, Alte Bahnhofstrasse 7, 5506 Mägenwil

Arbeitnehmer/in:
"Vorname" "Name", "Adresse / Strasse", "PLZ Ort"
Geboren am "Geburtsdatum"

Das Arbeitsverhältnis beginnt per "Eintrittsdatum" und wird unbefristet abgeschlossen. Eine gültige Arbeits- und Aufenthaltsbewilligung wird vorausgesetzt.

Probezeit: drei Monate / entfällt
Für die Berechnung der Dienstjahre gilt der "Datum"

Funktion: "Funktionsbezeichnung"
Funktionsstufe: Stufe 6
Pensum / Arbeitszeit: 100%, 42.0 Stunden / Woche
Angliederung Niederlassung: z. B. Hauswartprofis AG, 5506 Mägenwil
Einsatzort: Kundenobjekt gemäss Tourenplanung / fixes Objekt

Lohn: CHF "Bruttolohn bei 100%" brutto pro Monat
Zuzüglich 13. Monatslohn pro Rata
Abzüglich Beiträge für Sozialversicherungen

Essensentschädigung / Repräsentationsspesen: CHF 350.00 x 12 / CHF 16.00 pro Tag
Ferienanspruch: 25 Tage pro Jahr (bei 100 % Pensum)

Geschäftsfahrzeug: Falls zutreffend, mit privater Nutzung gemäss Fahrzeugreglement
Erfolgsanteil: Falls vereinbart

Allgemeine Bestimmungen:
- Allgemeine Anstellungsbedingungen der Hauswartprofis AG
- Weisungen und Anordnungen des Arbeitgebers
- Spesenreglement(e)
- Fahrzeugreglement

Gerichtsstand: Baden (AG)
"""

HTML_FORM = """
<!doctype html>
<title>Vertragsgenerator</title>
<h1>PDF hochladen</h1>
<form method=post enctype=multipart/form-data>
  <label>Angaben zur Vertragserstellung (PDF):</label><br>
  <input type=file name=pdf_file><br><br>
  <label>Geburtsdatum:</label><br>
  <input type=text name=geburtsdatum><br><br>
  <label>Geschlecht:</label><br>
  <select name=geschlecht>
    <option value="Frau">Frau</option>
    <option value="Herr">Herr</option>
  </select><br><br>
  <label>Dienstjahre zählen ab (techn. Eintritt):</label><br>
  <input type=text name=dienstjahre><br><br>
  <input type=submit value=Vertrag generieren>
</form>
{% if vertrag %}
<h2>Generierter Vertrag</h2>
<pre>{{ vertrag }}</pre>
<form action="/download" method="post">
  <input type="hidden" name="vertragstext" value="{{ vertrag | replace('\n', '&#10;') }}">
  <button type="submit">📥 Als Word-Dokument herunterladen</button>
</form>
{% endif %}
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    vertrag = ""
    if request.method == 'POST':
        file = request.files.get('pdf_file')
        geburtsdatum = request.form.get("geburtsdatum")
        geschlecht = request.form.get("geschlecht")
        dienstjahre = request.form.get("dienstjahre")

        if file:
            try:
                with pdfplumber.open(file) as pdf:
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)

                template_to_use = TEMPLATE_UNBEFRISTET
                if "befristet" in text.lower():
                    template_to_use = TEMPLATE_BEFRISTET

                prompt = f"""Hier sind Angaben zur Vertragserstellung:
{text}

Zusätzlich eingegebene Felder:
- Geburtsdatum: {geburtsdatum}
- Geschlecht: {geschlecht}
- Dienstjahre zählen ab: {dienstjahre}

Verwende folgendes Template:
{template_to_use}

Fülle das Template mit den extrahierten Informationen aus. Falls ein Geschäftsfahrzeug erwähnt oder angekreuzt ist, füge eine passende Klausel ein. Wenn der Vertrag befristet ist, ergänze das Befristungsdatum entsprechend."""
                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                vertrag = response.choices[0].message.content

            except Exception as e:
                vertrag = f"Fehler bei der Verarbeitung: {str(e)}"

    return render_template_string(HTML_FORM, vertrag=vertrag)

@app.route('/download', methods=['POST'])
def download():
    vertrag = request.form.get("vertragstext", "")
    doc = Document()
    for line in vertrag.split('\n'):
        doc.add_paragraph(line)

    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)

    return send_file(
        file_stream,
        as_attachment=True,
        download_name="Arbeitsvertrag.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

if __name__ == '__main__':
    app.run()
