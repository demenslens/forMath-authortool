# tools/

Bevat hulpprogramma's die los staan van de pipeline. Niet voor productie-gebruik
in de Authortool; alleen om handmatig te draaien wanneer je iets nodig hebt.

Tools verwachten dat de pipeline-bestanden (`expression_parser.py`,
`ast_normalizer.py`, etc.) in de parent-directory staan. Ze voegen die
parent-directory zelf aan `sys.path` toe, dus je kunt ze vanaf elk werkpad
aanroepen.

## validate_opgave.py

Valideert een door de pipeline gegenereerd opgave-JSON-bestand op vier
categorieën:

1. **Schema-integriteit** — alle verplichte velden aanwezig met juiste typen
2. **Interne consistentie** — alle ID-verwijzingen kloppen, geen circulaire
   afhankelijkheden, DUO matcht steps, mathblocks hebben een operation-entry
   in node_map
3. **Wiskundige correctheid** — herparst `metadata.expressie.tekst`, draait
   door de hele pipeline en vergelijkt met de output van het laatste mathblock
4. **Randvoorwaarden** — interne consistentie (geen breuken+decimalen,
   ranges in [0, 15], geldige `wortel_resultaat`) plus match met inhoud
   (geen MIXED_NUMBER_OP op root als `uitkomst_als_gemengd_getal=False`,
   waarschuwing voor π-expressie zonder pi-decimalen)

### Hoe te draaien

```bash
# Eén bestand
python3 tools/validate_opgave.py ~/Desktop/JSON_files_ForMath/opgave_001.json

# Hele bibliotheek
python3 tools/validate_opgave.py ~/Desktop/JSON_files_ForMath/*.json

# Machine-leesbaar voor scripts/CI
python3 tools/validate_opgave.py opgave_001.json --json
```

Exit-code is `0` als alle bestanden valideren (warnings tellen niet mee), `1`
als ergens een error gevonden is.

### Hoe te gebruiken als module

```python
from tools.validate_opgave import validate

with open('opgave_001.json') as f:
    opgave = json.load(f)

report = validate(opgave)
if not report.is_ok():
    for issue in report.errors():
        print(f"{issue.code}: {issue.message}")
```

### Bekende beperkingen

- **`wortel_resultaat='plus_en_min'` wordt niet ondersteund door de pipeline.**
  De validator detecteert dit en geeft een warning. Het is bewust ingebouwd
  als reminder dat dit een openstaand ontwerppunt is (zie discussie over
  abc-formule en ±-takken).
- **Tussenuitkomsten van mathblocks worden niet gecontroleerd.** Alleen de
  einduitkomst (laatste mathblock). Een opgave waarvan de einduitkomst klopt
  maar tussenstappen verkeerd zijn, slaagt nu nog.

### Wanneer hergebruiken

- Vóór elke batch-import van opgaven
- Tijdens ontwikkeling van pipeline-aanpassingen (regressie-test)
- Bij twijfel over een specifieke opgave

## formath_doc.py

Genereert een PDF met technische documentatie over de ForMath pipeline:
architectuur, input/output, ontwerpbeslissingen en per-bestand-uitleg.

### Wat het is

Een ReportLab-script (1154 regels, geen externe data-bron). De inhoud van het
document zit hardgecodeerd in de Python; je past het document aan door de
Python te bewerken, niet via een markdown-bron of templates.

Hoofdstukken die het document oplevert:

1. Projectoverzicht
2. Input en Output
3. Pipeline Architectuur (incl. landscape flow-tabel)
4. Bestandsdocumentatie (4.1 t/m 4.10 — per pipeline-bestand een sectie)

### Hoe te draaien

```bash
python3 tools/formath_doc.py
```

Het script schrijft naar het pad dat in `build_doc()` is hardgecodeerd
(regel 176): `/mnt/user-data/outputs/ForMath_Pipeline_Documentatie.pdf`.

**Pas dit pad aan voordat je het lokaal draait.** Dit pad bestaat alleen in
de Claude-werkomgeving, niet op je Mac. Een lokaal alternatief:

```python
# regel 176, bijvoorbeeld:
path = os.path.expanduser('~/Desktop/ForMath_Pipeline_Documentatie.pdf')
```

### Vereisten

- Python 3
- `reportlab` (`pip install reportlab`)

### Belangrijk: documenteert ook verwijderde code

Het document beschrijft secties 4.5 (`tak_allocator.py`), 4.6 (`step_calculator.py`),
4.8 (`ast_to_mathjson.py`) en 4.9 (`json_generator_v2.py`) als onderdelen van
de pipeline. **Die bestanden zijn inmiddels verwijderd** en bestaan niet meer
in de actieve codebase. Voordat je het document opnieuw genereert moet je
beslissen:

- óf die secties verwijderen uit `formath_doc.py`,
- óf in het document expliciet maken dat het historische/gearchiveerde modules zijn.

De versiestempel staat op "Versie 1.0 &nbsp;|&nbsp; Maart 2026" (regel 200) —
update die ook bij elke regeneratie.

### Wanneer hergebruiken

- Bij significante wijziging in de pipeline-architectuur
- Voor onboarding van een nieuwe ontwikkelaar
- Voor archiveringsdoeleinden (versie-snapshot)

Voor dagelijks gebruik is `01_project_snapshot.md` voldoende — die is sneller
te updaten en korter te lezen.
