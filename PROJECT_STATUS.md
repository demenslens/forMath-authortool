# ForMath Opgave Invoertool — Projectstatus

**Laatste update:** 20 april 2026, na iteratie 6
**Werkbestand:** `formath_v2.zip` in `/mnt/user-data/outputs/`

Dit document is de **single source of truth** voor de status van het
professionaliserings-traject. Het is bedoeld als overdracht zodat elke
volgende chat direct verder kan zonder de hele historie door te ploegen.

---

## 1. Projectcontext in één alinea

ForMath is een pipeline voor interactieve wiskunde-opgaven in het middelbaar
onderwijs. Twee delen: (1) de **Opgave Invoertool** — lokale Python/HTTP-server
+ browser-frontend waarin een docent wiskundige expressies invoert, de AST
parseert, en een uitgebreide JSON exporteert; (2) het **Wiskunde Werkblad** —
een apart prototype waarin studenten de geëxporteerde opgaven stapsgewijs
vereenvoudigen. Deze chat professionaliseerde **alleen de Invoertool**. Het
Werkblad was referentiemateriaal voor het JSON-formaat.

## 2. Wat er voor de sessie was

Uitgangspunt: `formath.zip` met ~8.500 regels Python, een monolithische
`index.html` van 611 regels met inline CSS en JS, meerdere `_oud`-varianten
naast actieve modules, drie verschillende output-paden in code/docs, en geen
tests. Eerste-regel-typo `Kunje` vóór `<!DOCTYPE html>`. Pipeline deels
werkend maar brittle op de randen.

## 3. Gekozen aanpak

Iteratief werken, per iteratie één afgerond en testbaar verbeterstuk. Bij
elke iteratie: inventarisatie → prioritering met akkoord van gebruiker →
uitvoeren → testen → zip opleveren → gebruiker verifieert in eigen setup.

Geen pipeline-inhoudelijke wijzigingen tenzij een bug het vereist; de focus
was structuur, UI, validatie, en data-schema — niet de parse-logica zelf.

## 4. Voltooide iteraties

### Iteratie 1 — Opruimen & fundament

- Dode code gearchiveerd naar `_archief/python_bestanden/`:
  `json_exporter_oud.py`, `manifold_detector_oud.py`,
  `manifold_converter_oud.py`, `json_generator_v2.py`, `step_calculator.py`
  (transitief dood), `tak_allocator.py` (transitief dood), `grid_visualizer.py`,
  `ast_to_mathjson.py` (niet equivalent aan actieve implementatie, getest
  en bevestigd verschillend op 5 expressies).
- Netto: ~8.465 → ~3.890 regels actieve Python (−54%).
- Output-pad geconsolideerd naar `~/Desktop/formath_JSON/` (was drie
  verschillende plekken genoemd).
- `index.html` (611 r, inline alles) opgesplitst in `index.html` (59 r) +
  `app.css` (295 r) + `app.js` (255 r). Typo `Kunje ` weggehaald.
- TCP-bind van `""` naar `"127.0.0.1"` (alleen localhost).
- `SyntaxWarning: invalid escape sequence '\l'` opgelost via raw docstring.
- Smoke test `_archief/smoke_test.py` — draait handler in-process; 14/14
  geslaagd.

### Iteratie 2 — Validatie & foutafhandeling

**Drie bugs gefixt:**

1. **🔴 `metadata.expressie.latex` ontbrak** in de output. Exporter schreef
   `latex_display` maar het werkblad verwacht sleutel `latex`. Fix:
   `latex` is nu de primaire sleutel met de AST-teruggerekende LaTeX;
   `tekst` blijft voor de platte ascii-math.
2. **🟡 ROOT-conventie mismatch**: `\sqrt[3]{27}` werd `root(27,3)` door
   `latex_to_expression`, maar `expression_parser` verwacht
   `root(n, x)` = n-de wortel van x. Derdemachtswortel rendered als
   `\sqrt[27]{3}` in plaats van `\sqrt[3]{27}`. Fix in regex-argumentvolgorde.
3. **🟡 Documentatiefout in INSTALLATIE.txt**: claimde dat `.` (punt)
   werkt als vermenigvuldiging. Parser kent dat niet. Docs bijgewerkt.

**Tests toegevoegd:**

- `tests/formath_validator.py` — schema-validator met CLI
- `tests/test_round_trip.py` — 16 expressies door volledige pipeline
- `tests/test_latex_conversion.py` — 32 unit tests, waaronder 6 round-trip
  property tests
- `tests/test_error_integration.py` — 6 API-foutmelding tests

**Gebruikersvriendelijke parser-fouten:**

- `python_bestanden/error_formatter.py` vertaalt 8 foutpatronen naar NL
  met tip en visuele snippet (`^` onder foutpositie)
- Server-integratie: `/api/process` en `/api/export_json` geven
  `error_detail` terug met `message`, `hint`, `position`, `snippet`, `raw`
- Frontend rendert snippet in monospace-block met hint

### Iteratie 2-follow-up — POWER-base haakjes-bug

**🟡 Door gebruiker gemeld tijdens live test**: `(1/4)^3` produceerde
`\frac{1}{4}^{3}` in plaats van `\left(\frac{1}{4}\right)^{3}`. Alleen de
noemer werd tot de macht verheven in MathLive-weergave. Fix in
`_node_to_latex` POWER-tak: `needs_parens` uitgebreid naar `FRACTION`,
`BINARY_OP`, `MANIFOLD_OP`, `MATROESJKA_OP`, `ROOT` (niet alleen `POWER`).
Dubbele-haken-bescherming: controleer of base-LaTeX al met `\left(` begint.
5 regressietests + round-trip-case toegevoegd.

### Iteratie 3 — UI/UX & visuele afwerking

Herindeling van bestaande features (geen nieuwe functionaliteit),
eigen visuele taal, bevestigingsdialoog bij export.

- **Layout omgedraaid**: invoer boven, schema eronder (natuurlijke leesrichting)
- **Knoppen op eigen rij** met hiërarchie primair/secundair/ghost, NL-labels
- **Mode-toggle als pill-switch** naast label
- **Pipeline-info paneel** na Parse met tekst + latex_display
- **Header toont live**: "N bewerkingen · M waarden"
- **Visuele taal**: warme papier-achtergrond (`#f6f4ed`), inkt-tekst,
  mosterd-oker accent (`#ae7a15`). Fraunces (display serif) + IBM Plex Sans
  (UI) + JetBrains Mono (code). Platte oppervlakken, 1px-randen, geen
  gradients/shadows.
- **Export-flow met bevestigingsdialoog**: Exporteer → backend checkt
  duplicaten (match op `tekst`-veld) → modal toont expressie + doelmap +
  waarschuwing → Exporteren of Annuleren
- **Nieuw endpoint** `/api/check_export` (alleen-lezen)
- **Toegankelijkheid**: `role="dialog"`, Escape sluit, klik-buiten sluit,
  Enter bevestigt

**Tests toegevoegd:** `tests/test_check_export.py` — 8 integratie-tests.

### Iteratie 3-follow-up — Dialog kon niet sluiten

**🟡 Door gebruiker gemeld**: dialog bleef zichtbaar na klik op Annuleren/×/
Escape. Oorzaak: CSS-regel `.dialog-overlay { display: flex }` had hogere
specificity dan user-agent `[hidden] { display: none }`. Fix: globale regel
`[hidden] { display: none !important; }` bovenaan `app.css`. Smoke test
uitgebreid met een regex-check op deze guard.

### Iteratie 3-follow-up — Integraal-glyph vervangen door wortel-breuk-logo

**Gebruiker-verzoek**: integraal-teken ∫ in header vervangen door een
wortelteken met daaronder een breuk met lege vakjes. Inline SVG toegevoegd
(path voor wortelteken, twee `<rect>`'s met stroke-dasharray voor
lege vakjes, `<line>` voor deelstreep). Gebruikt `currentColor` zodat de
accent-kleur via CSS wordt overgenomen.

### Iteratie 4 — Inspector & randvoorwaarden

**JSON-schema uitbreidingen:**

- `metadata.randvoorwaarden.vereenvoudig_uitkomst` (bool, default `false`)
  — dekt zowel vereenvoudigen van breuken (4/6 → 2/3) als gemengde getallen
  (9/4 → 2 + 1/4). **Per-opgave** scope.
- `mathblocks[i].klasse` optioneel, waarden `"A1"` / `"B1"` / `"B2"`:
  - A1 = rechttoe-rechtaan
  - B1 = kruislingse methode voor breuken (a/b + c/d = (a·d+b·c)/(b·d))
  - B2 = KGV-methode
- `mathblocks[i].kgv` — automatisch berekend voor B2 op een optelling of
  manifold-som met breuk-inputs

**Ontwerpkeuze — model B (bevestigd met gebruiker):**

Klasse is **metadata voor hint-selectie** in het werkblad. Geen tussenstap-
generatie of -controle in deze iteratie. Upgrade-pad naar model A later
staat in `ROADMAP.md`.

**Ontwerpkeuze — hint-teksten NIET in JSON (voorgesteld, akkoord):**

Het werkblad heeft een centrale template-tabel `{A1: ..., B1: ..., B2: ...}`.
Voordelen: consistentie, geen JSON-bloat, geen hergeneratie bij hint-wijziging.

**Backend:**

- `generate_formath_json()` accepteert 3 nieuwe parameters:
  `randvoorwaarden`, `mathblock_klasses`, `dry_run`. Alle optioneel.
- Nieuwe helpers in `json_exporter.py`: `_lcm`, `_lcm_list`,
  `_extract_denominators`, `_apply_mathblock_klasses`.
- `/api/process` geeft nu `mathblocks` terug (via `dry_run=True` op de
  exporter) met `{id, step, symbool, heeft_breuken, input_preview}`.
- `/api/export_json` accepteert `randvoorwaarden` en `mathblock_klasses`.

**Validator:**

- `_check_randvoorwaarden`: onbekende sleutels → warning (forward-compat);
  non-bool waarden → error.
- `_check_mathblock_klasses`: onbekende klasses → error; B2 zonder `kgv`
  → warning; kgv moet positieve int zijn.

**Frontend:**

- Layout naar 2-kolom grid (main + 320px inspector rechts, fallback
  naar 1-kolom <960px).
- Inspector altijd zichtbaar. Sectie "Randvoorwaarden" met toggle-switch
  voor "Uitkomst vereenvoudigen". Sectie "Mathblocks" met pill-toggles
  (A1/B1/B2) per block, verschijnt na Parse.
- Inspector-state (`inspectorState = {randvoorwaarden, klasses}`) wordt
  meegestuurd bij Exporteer.

**Tests:**

- `tests/test_klasse_randvoorwaarden.py` — 26 unit tests (LCM, extractie,
  exporter, validator)
- `tests/test_inspector_e2e.py` — 16 E2E-tests van HTTP-flow

### Iteratie 4-follow-up — Rechter inspector collapsible

Gebruiker-verzoek na oplevering iteratie 4: mogelijkheid om de rechter
inspector weg te klikken. Toggle-knop toegevoegd in de inspector-header.
Wanneer ingeklapt verschijnt een smalle verticale rail (40px breed) met
verticaal label "Inspector"; klik op de rail opent weer. Grid-template
van `.app-main` past automatisch aan via class `.inspector-collapsed`.
Keyboard-toegankelijk met `aria-expanded` en automatisch focus-management.

### Iteratie 5 — Opgavenbeheer (linker inspector)

Nieuw paneel links met overzicht en beheer van alle geëxporteerde opgaven.

**Nieuwe backend-endpoints:**

- `GET /api/list_opgaven` — lijst met id, filename, tekst,
  aantal_mathblocks, aantal_steps, has_svg. Corrupte JSONs krijgen
  `corrupt: true` vlag (wel tonen, niet crashen).
- `GET /api/load_opgave?id=...` — volledige JSON + bijbehorende SVG.
- `POST /api/delete_opgave` body `{id}` — verwijdert JSON én SVG.
- `POST /api/export_json` accepteert optioneel `overwrite_id` voor
  overschrijven zonder nieuw volgnummer.

**Security:** alle ID-parameters worden via regex `[A-Za-z0-9_]+`
gevalideerd. Path-traversal (`../etc/passwd`) wordt geblokkeerd op
load, delete én overwrite_id.

**Exporter-wijziging:**

`generate_formath_json()` parameter `opgave_id=None`. Bij `None` behoud
van oud gedrag (nieuw ID). Bij expliciete string wordt dat ID gebruikt,
waardoor overschrijven van zowel JSON als SVG in OUTPUT_DIR werkt.

**Frontend:**

- **3-koloms layout** boven 1100px (260px + 1fr + 320px). Fallback naar
  2-koloms onder 1100px (linker inspector schuift naar top), naar 1-kolom
  onder 960px.
- **Linker inspector** toont alleen de ID per opgave (simpel, compact).
  Subtitle toont live telling ("3 opgaven"). Automatische refresh na
  elke export en na elke delete. Zelfde collapsible-patroon als rechter
  inspector.
- **Opgave selecteren** → `math-field` gevuld met opgave-expressie,
  `readonly`. Rechter inspector gevuld met klasse- en randvoorwaarden-
  waarden uit de JSON, ook alleen-lezen. SVG-view direct zichtbaar.
- **JSON / SVG toggle** in result-panel-head. JSON-view is een
  monospace `<pre>` met indent 2.
- **"Edit toestaan"-knop** zet `readonly` af; bij daarna Parse + Exporteer
  verschijnt een extra sectie in de export-dialoog met radio-keuze:
  "Bestaande wijzigen" (stuurt `overwrite_id` mee) of "Als nieuwe opslaan"
  (nieuw ID).
- **"Delete"-knop** opent aparte bevestigingsdialoog (`#delete-dialog`).
  Escape en klik-buiten sluiten de dialoog.

**UX-detail:** Parse op een geselecteerde opgave zonder Edit toestaan aan
geeft een statusbericht in plaats van te parsen. Voorkomt onbedoelde
view-wijzigingen.

**Tests:**

- `tests/test_opgaven_management.py` — 32 integratie-tests. Volledige
  lifecycle: list leeg/gevuld, load bestaand/onbestaand, overwrite-flow
  (expressie verandert, ID blijft, lijst telt gelijk), delete-flow (JSON
  + SVG beide weg), path-traversal bescherming op alle drie endpoints.

**Gebruiker-verzoeken tijdens iteratie** die nog open staan: zoeken/
filteren in opgave-lijst, groeperen op datum/klasse, archiveren ipv
verwijderen — vastgelegd in `ROADMAP.md`.

### Iteratie 6 — Opdracht, keyboard-navigatie, SVG-header

Verzameling UX-verbeteringen en een nieuwe metadata-sleutel.

**JSON-schema uitbreiding:**
- `metadata.opdracht` (`"reken_uit"` default | `"vereenvoudig"`) — de
  opdracht die de student moet uitvoeren op de expressie. Per-opgave.
- Exporter heeft nieuwe parameter `opdracht`; validator heeft
  `_check_opdracht`.

**Frontend:**
- Statisch label "Wiskundige expressie" vervangen door dropdown
  met twee opties. Keuze wordt meegestuurd bij export.
- Keyboard-navigatie in opgave-lijst met ↑/↓/Home/End/Enter (roving
  tabindex, listbox-best-practice).
- SVG-header toont nu "Opgave: <expr>" en "Uitkomst: <waarde>"; grijs
  vlak (`#FAFAFA`) uit de SVG verwijderd. Uitkomst auto-berekend via
  `evaluate` + `format_result`.
- `.result-panel` zonder paneel-achtergrond en border; `#svg-wrapper`
  border ook weg. Schema staat visueel los op de pagina.

**Bugfix:** MathLive `readonly`-attribuut werd niet correct afgezet
(spec: aanwezigheid van attribuut triggert read-only, waarde doet er
niet toe). Fix: `removeAttribute('readonly')` + property-kant zetten.

**Tests:** 35 klasse/rv/opdracht-unit (was 26), 19 inspector-e2e (was 16).

---

## 5. Huidige testsuite (169 groen)

```
_archief/smoke_test.py                   15/15
tests/test_latex_conversion.py           37/37
tests/test_round_trip.py                 17/17 (1 met warning, zie §7)
tests/test_error_integration.py           6/6
tests/test_check_export.py                8/8
tests/test_klasse_randvoorwaarden.py     35/35
tests/test_inspector_e2e.py              19/19
tests/test_opgaven_management.py         32/32
                                        ───────
                                        169/169
```

Alle tests draaien in-process (geen server-proces nodig) en gebruiken alleen
Python stdlib. Commando om alle tests te draaien staat in `tests/README.md`.

## 6. Mapstructuur huidige staat

```
formath/
├── CHANGELOG.md               # uitgebreide per-iteratie log
├── ROADMAP.md                 # open werk (zie §7)
├── INSTALLATIE.txt            # eind-gebruiker docs
├── _archief/
│   ├── README.md              # wat en waarom gearchiveerd
│   ├── smoke_test.py          # in-process smoke test
│   ├── python_bestanden/      # 8 gearchiveerde modules
│   └── voorbeeld_outputs/     # oude JSONs + xlsx (pre-AST)
├── formath_web/
│   ├── server.py              # HTTP handler + LaTeX ↔ expr converters
│   ├── index.html             # HTML-structuur
│   ├── app.css                # design tokens + styling
│   └── app.js                 # frontend-logica, inspector-state
├── python_bestanden/          # actieve pipeline
│   ├── expression_parser.py
│   ├── ast_normalizer.py
│   ├── manifold_detector.py
│   ├── manifold_converter.py
│   ├── ast_visualizer.py
│   ├── json_exporter.py       # met randvoorwaarden + klasses
│   └── error_formatter.py
└── tests/
    ├── README.md
    ├── formath_validator.py   # CLI + programmatic
    ├── inspect_export.py      # diagnostiek
    ├── test_latex_conversion.py
    ├── test_round_trip.py
    ├── test_error_integration.py
    ├── test_check_export.py
    ├── test_klasse_randvoorwaarden.py
    └── test_inspector_e2e.py
```

## 7. Open werk (op volgorde van urgentie)

### A. Model A — tussenstap-controle per klasse

Hint-selectie werkt nu via klasse-metadata (model B). Voor echte
tussenstap-validatie (student moet écht volgens B1 kruisvermenigvuldigen)
moet:

- Pipeline per klasse een canonieke tussenstap-expressie genereren (bv.
  B1 op `1/2+1/3` → `(1·3+2·1)/(2·3)`)
- JSON een `tussenstap`-veld per mathblock bevatten
- Werkblad tussenstap-validatie doen naast einduitkomst-validatie

### B. Pipeline-bug 311_007 — mathblocks zonder operation-entry

Complexe expressie `[(3^2)*(12-9)^3]:(9-6)^3:(-3)*[(-6)^2]:3^4+(-2)^3`
levert 9 mathblocks zonder `operation`-entry in `node_map`. Cursor-tracking
werkt niet voor die blocks in het werkblad. Structureel probleem in
`_build_mathjson_ast` in `json_exporter.py`. Round-trip test geeft warning
(niet fail) zodat het zichtbaar blijft.

### C. Opgavenbeheer uitbreidingen

Iteratie 5 levert de basis (lijst, selecteer, bewerken, overschrijven,
verwijderen). Vervolg-opties:

- **Zoeken / filteren** op expressie-inhoud of ID-prefix
- **Groeperen** op datum, klasse of thema (tags?)
- **Archiveren** als alternatief voor verwijderen
- **Batch-operaties**: meerdere opgaven tegelijk
- **Direct pushen naar werkblad** vanuit de invoertool

### D. Nog niet beslist

- Randvoorwaarde 1 per-opgave of per-mathblock? Nu per-opgave gekozen
  pragmatisch; gebruiker had geen uitgesproken voorkeur.
- Klassen voor vermenigvuldiging / deling: schema staat er klaar voor
  (`klasse` mag op elk mathblock), maar er zijn geen klassen voor die
  operaties gedefinieerd.

## 8. Sleutelbeslissingen en hun waarom

| Beslissing | Reden |
|---|---|
| Iteratief werken met aparte zips | Gebruiker kan elke iteratie in eigen setup verifiëren; minimaliseert blind doorbouwen op foute aanname |
| Dode code archiveren, niet deleten | Referentie-waarde; `_archief/README.md` per-bestand waarom |
| Geen pipeline-logica aanraken | Parser etc. werken; tests dekken eerste het gedrag vast; pipeline-wijzigingen zijn hoog-risico |
| Python stdlib only behouden | Geen `pip install` nodig voor eind-gebruiker; was bestaande constraint |
| Model B voor klassen, niet model A | Model A vereist pipeline-uitbreiding én werkblad-uitbreiding; model B is nu alleen metadata; forward-compatibel |
| Hint-teksten buiten JSON | Consistentie, geen bloat, geen hergeneratie |
| `latex`-veld in metadata.expressie | Werkblad-compatibiliteit — bug 🔴 uit iteratie 2 |
| `randvoorwaarden` als dict (niet flat) | Forward-compat voor meer randvoorwaarden later |
| A1 als default klasse | Veilig minimum; docent kiest expliciet B1/B2 |
| Dialog met `[hidden]`-guard | Voorkomt hele klasse bugs waar CSS display-rules het attribuut overrulen |
| 2-kolom layout boven 960px | Inspector moet naast hoofdpaneel staan op gangbaar scherm; fallback voorkomt kapot op smal |
| 3-kolom layout boven 1100px | Linker inspector erbij; break naar 2-kolom op 1100px, naar 1-kolom op 960px |
| Alleen ID in opgave-lijst | Gebruiker expliciet gekozen, houdt lijst compact en scan-baar |
| Realtime refresh van opgave-lijst | Gebruiker expliciet gekozen; voorkomt stale-state verwarring na export/delete |
| Rechter inspector read-only bij selectie | Gebruiker expliciet gekozen; "Edit toestaan" ontgrendelt |
| `overwrite_id` via regex-whitelist | Path-traversal bescherming; blokkeert `../etc/passwd` op drie endpoints |
| Export-dialoog radio-keuze bij selectie | "Bestaande wijzigen" vs "Als nieuwe" — duidelijker dan impliciete gedrag op basis van edit-state |

## 9. Bekende eigenaardigheden en valkuilen

- **`_node_to_latex` in `server.py`** bevat veel tak-specifieke logica voor
  haakjes. Uitbreiden vereist zorgvuldige dubbel-haken-bescherming
  (`base_latex.startswith(r'\left(')`). Zie POWER-tak voor patroon.
- **MathJSON in `json_exporter.py._build_mathjson_ast`** heeft een ander
  gedrag dan de parallelle implementatie in de oude `ast_to_mathjson.py`
  (gearchiveerd). Niet samenvoegen zonder uitgebreide tests.
- **`manifold_detector.detect_manifolds`** annoteert nodes met tijdelijke
  metadata die `manifold_converter` weer opruimt. Extra bewerkingen na
  conversie moeten `remove_all_annotations` respecteren.
- **Browser-cache op Safari** is notoir. Gebruikersverificatie van UI-
  wijzigingen moet met hard refresh of caches leegmaken (Safari vereist
  Cmd+Option+E via devtools).
- **Python pycache** bij Mac-mini van gebruiker: `.cpython-314.pyc` files.
  Bij verdachte oude-versie-serving: eerst pycache weg.
- **MathLive-fonts 404 vanaf unpkg** is een bekende low-priority issue; doet
  niets aan functionaliteit, alleen visuele mooiheid van wiskundeletters.

## 10. Voor de volgende chat

### Als je niet weet wat te doen
- Lees `CHANGELOG.md` voor details per iteratie
- Lees `ROADMAP.md` voor wat nog open staat
- Draai alle tests om te verifiëren dat de staat nog gezond is
- Vraag de gebruiker wat hij als volgende wil

### Als je iets nieuws gaat bouwen
- Eerst plan voorstellen vóór code schrijven
- Pas iteratie-discipline toe: kleine testbare stappen
- Houd backward-compat in JSON-schema: optionele velden toevoegen, nooit
  bestaande betekenis wijzigen
- Bij pipeline-logica: regressietest *vóór* je iets wijzigt, niet na

### Waar de gebruiker waarde aan hecht
- Iteratief, verifieerbaar, niet in één keer alles
- Herkennen van echte bugs en ze fixen, niet omheen werken
- Nederlandse UI-teksten en toegankelijke error-meldingen
- Eerlijke analyse vóór ruwe uitvoering

### Format voor interactie met deze gebruiker
- Korte concrete opties in `ask_user_input_v0` tool bij keuzes
- Niet lange monologen zonder bevestiging
- Gebruiker kan vragen niet beantwoorden; dan pragmatisch kiezen en uitleggen
- Bij visuele wijzigingen: mockup of preview tonen vóór implementatie
