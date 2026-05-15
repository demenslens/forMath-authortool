# CHANGELOG

## Iteratie 6 — Opdracht, keyboard-navigatie, SVG-header (20 april 2026)

Verzameling gerichte UX-verbeteringen en een nieuwe metadata-sleutel.

### Nieuwe metadata-sleutel `opdracht`

- **`metadata.opdracht`** — de opdracht die de student met de expressie
  moet doen. Waarden: `"reken_uit"` (default) of `"vereenvoudig"`.
- Wordt gekozen in een dropdown bovenin het invoerpaneel (waar eerder
  het statische label "Wiskundige expressie" stond).
- Elke nieuwe opgave krijgt impliciet `reken_uit`; docent kiest
  `vereenvoudig` waar relevant.
- Gaat mee in de JSON en wordt bij selectie van een bestaande opgave
  weer teruggeladen.

**Exporter:** `generate_formath_json()` accepteert een nieuwe parameter
`opdracht`. Onbekende waarden vallen stil terug op `reken_uit`
(validator geeft error bij expliciete foutieve waarde).

**Validator:** `_check_opdracht` controleert het veld wanneer aanwezig.
Ontbreken is geen fout (optioneel veld, forward-compatible met oudere
JSONs).

### SVG-header vernieuwd

- Was: `AST: <expressie>` + kleine `= <expressie>` regel.
- Nu: **`Opgave: <expressie>`** op regel 1 en **`Uitkomst: <waarde>`**
  op regel 2.
- `Uitkomst` wordt automatisch berekend via `evaluate` + `format_result`
  uit `ast_visualizer`. Als evaluatie faalt (bv. bij symbolische
  expressies) wordt de regel weggelaten.
- **Grijze achtergrond (`#FAFAFA`) in de SVG is verwijderd** —
  schema is nu transparant.

### Visuele onrust rondom schema opgeschoond

- `.result-panel` heeft geen paneel-achtergrond meer en geen border.
  Schema staat visueel los op de pagina i.p.v. in een kadertje.
- `#svg-wrapper` border ook weggehaald voor dezelfde reden.

### Keyboard-navigatie in opgave-lijst

- **↑ / ↓** — vorige / volgende opgave (focus verplaatsen, niet
  meteen selecteren)
- **Home / End** — eerste / laatste opgave
- **Enter** of **Spatie** — selecteer het gefocuste item
- Gebruikt roving-tabindex (listbox-best-practice): één item zit in
  de tab-volgorde, pijltjes verschuiven die tussen items. Geselecteerd
  item heeft voorrang bij initiële focus.

### MathLive readonly-bug gefixt

Bij het aanklikken van "Edit toestaan" reageerde het veld niet; cursor
verscheen niet. Oorzaak: HTML-spec stelt dat de **aanwezigheid** van
het `readonly`-attribuut read-only triggert, ongeacht de waarde.
`setAttribute('readonly', 'false')` hield het veld dus vergrendeld.
Fix: `removeAttribute('readonly')` bij unlock, plus `mathField.readOnly`
property-kant ook zetten voor oudere MathLive-versies.

### Tests

- `test_klasse_randvoorwaarden.py` uitgebreid met 9 tests voor opdracht
  (exporter default/expliciet/unknown + validator geldig/ongeldig/
  ontbrekend/verkeerd-type). Totaal nu 35 unit tests in dit bestand.
- `test_inspector_e2e.py` uitgebreid met 3 E2E-tests voor opdracht.
  Totaal nu 19 E2E-tests.

**Totaal nu: 15 smoke + 37 latex + 17 round-trip + 6 error-integratie +
8 check-export + 35 klasse/rv/opdracht-unit + 19 inspector-e2e +
32 opgaven-mgmt = 169 tests groen.**

---

## Iteratie 5 — Opgavenbeheer (linker inspector) (20 april 2026)

Nieuw linker paneel met een overzicht van alle geëxporteerde opgaven.
Vanuit de lijst kan een docent opgaven selecteren, bekijken (als SVG of
als JSON), bewerken en verwijderen. Export-flow uitgebreid met een
"bestaande wijzigen / als nieuwe opslaan"-keuze wanneer een opgave
geselecteerd is.

### Nieuwe backend-endpoints

- **`GET /api/list_opgaven`** — lijst van alle `opgave_*.json` bestanden
  in `OUTPUT_DIR`, met per item `id`, `filename`, `tekst`,
  `aantal_mathblocks`, `aantal_steps`, `has_svg`. Corrupte JSONs krijgen
  een `corrupt: true` vlag maar worden wel getoond.
- **`GET /api/load_opgave?id=XXX`** — volledige JSON van één opgave plus
  de bijbehorende SVG-inhoud.
- **`POST /api/delete_opgave`** body `{id}` — verwijdert zowel JSON als
  SVG-bestand van de betreffende opgave.
- **`POST /api/export_json`** accepteert nu optioneel `overwrite_id` —
  als meegegeven, behoudt `generate_formath_json` dat ID in plaats van
  een nieuw te genereren. Effect: dezelfde bestandsnaam wordt
  overschreven.

**Security**: alle ID-parameters worden via regex gevalideerd op
`[A-Za-z0-9_]+` om path-traversal (`../etc/passwd`) te blokkeren.

### Exporter-wijziging

`generate_formath_json()` heeft een nieuwe parameter `opgave_id=None`.
Bij `None` blijft het gedrag identiek (nieuw ID via `_generate_id`); bij
een expliciete string wordt dat ID gebruikt zodat overschrijven werkt.

### Frontend

- **3-koloms layout** boven 1100px: linker inspector (260px) + main (1fr)
  + rechter inspector (320px). Onder 1100px schuift de linker inspector
  naar boven; onder 960px alles in 1 kolom.
- **Linker inspector** — "Opgaven" — toont alle opgaven in de outputmap
  als klikbare lijst. Alleen de ID wordt getoond (bijv. `20260420_001`).
  Live telling in de subtitel ("3 opgaven"). Lijst ververst automatisch
  na elke export en na elke delete. Ook in- en uitklapbaar via dezelfde
  rail-pattern als de rechter inspector.
- **Opgave selecteren** vult de `math-field` met de opgave-expressie en
  **zet het veld op slot** (`readonly`). De rechter inspector wordt
  ingevuld met de klasse- en randvoorwaarden-waarden uit de JSON (ook
  read-only). SVG-view wordt direct getoond.
- **JSON / SVG toggle** in het result-panel — schakelt tussen de
  grafische AST-boom en de ruwe JSON-inhoud (monospace, indent 2).
- **"Edit toestaan"-knop** zet het veld vrij zodat de expressie aangepast
  kan worden. Na aanpassen én Parse verschijnt bij Exporteer JSON een
  extra keuze in de dialoog: **"Bestaande wijzigen"** (overschrijft
  dezelfde opgave met hetzelfde ID) of **"Als nieuwe opslaan"** (nieuw
  ID, origineel blijft staan).
- **"Delete"-knop** opent een aparte bevestigingsdialoog. Verwijdert
  zowel de JSON als de bijbehorende SVG.

### UX-detail

Wanneer er een opgave geselecteerd is en de docent drukt op Parse zonder
eerst Edit toestaan aan te klikken, toont de statusregel: "Klik eerst op
Edit toestaan om de expressie te kunnen aanpassen." Dit voorkomt dat de
view ongemerkt overschreven wordt met een her-parse van dezelfde input.

### Tests

Nieuw: **`tests/test_opgaven_management.py`** — 32 integratie-tests:
- `list_opgaven` leeg en met inhoud, alle velden aanwezig
- `load_opgave` op bestaand ID, SVG mee-geladen
- `load_opgave` op onbestaand ID faalt netjes
- Path-traversal bescherming op load, delete, en overwrite_id
- Overwrite-flow: expressie verandert, filename blijft, lijst telt gelijk
- Delete-flow: JSON + SVG beide weg, lijst krimpt
- Delete op onbestaand ID faalt netjes

**Totaal nu: 15 smoke + 37 unit + 17 round-trip + 6 error-integratie +
8 check-export + 26 klasse-unit + 16 inspector-e2e + 32 opgaven-mgmt
= 157 tests groen.**

### Niet in deze iteratie

- **Zoeken / filteren** in de opgave-lijst (de lijst toont nu gewoon
  alles, alfabetisch gesorteerd op filename).
- **Groeperen** op datum, klasse of thema.
- **Direct pushen naar werkblad** vanuit de invoertool.
- **Model A** (tussenstap-controle) blijft voor later, zie `ROADMAP.md`.

---

## Iteratie 4 — Inspector & randvoorwaarden (20 april 2026)

Nieuw inspector-paneel rechts in de UI, waar randvoorwaarden en klasse-keuzes
per mathblock worden bewerkt. Beide komen mee in de JSON-export. Werkt volgens
"model B": klasse is metadata die het werkblad gebruikt voor hint-selectie;
er worden nog geen tussenstappen gegenereerd of gecontroleerd (dat blijft
expliciet voor latere uitbreiding — zie `ROADMAP.md`).

### JSON-schema uitbreidingen

- **`metadata.randvoorwaarden`** — optionele dict met opgave-brede instellingen.
  Nu gedefinieerd:
  - `vereenvoudig_uitkomst` (bool, default `false`): de student moet de
    einduitkomst vereenvoudigen. Dit dekt twee dingen: een breuk in laagste
    termen brengen (4/6 → 2/3) en een oneigenlijke breuk herschrijven als
    gemengd getal (9/4 → 2 + 1/4).

- **`mathblocks[i].klasse`** — optioneel veld per mathblock met de
  didactische klasse. Waarden: `"A1"` (rechttoe-rechtaan), `"B1"`
  (kruislingse methode voor breuken), `"B2"` (KGV-methode voor breuken).
  Alleen aanwezig als de docent expliciet een klasse heeft gekozen.

- **`mathblocks[i].kgv`** — bij klasse `B2` op een optelling of
  manifold-sommatie berekent de exporter de KGV van de noemers van de
  input-breuken. Geen KGV als er geen breuken zijn.

### Backend

- **`generate_formath_json()`** heeft drie nieuwe parameters: `randvoorwaarden`,
  `mathblock_klasses`, en `dry_run`. Alle drie optioneel en backward-compatibel.
  `dry_run=True` schrijft geen bestand; gebruikt door `/api/process` om een
  mathblock-samenvatting aan de frontend te geven zonder side-effect.
- **Nieuwe helpers** in `json_exporter.py`: `_lcm`, `_lcm_list`,
  `_extract_denominators`, `_apply_mathblock_klasses`.
- **`/api/process`** retourneert nu een extra veld `mathblocks` met voor elk
  mathblock: `id`, `step`, `symbool`, `heeft_breuken` en `input_preview`.
  Zo kan de frontend-inspector de klasse-keuzes renderen.
- **`/api/export_json`** accepteert `randvoorwaarden` en `mathblock_klasses`
  in de request-body en geeft ze door aan de exporter.

### Validator

Twee nieuwe checks in `tests/formath_validator.py`:

- `_check_randvoorwaarden`: als `metadata.randvoorwaarden` bestaat, moet het
  een dict zijn met de bekende sleutels en correcte types. Onbekende sleutels
  geven een warning (forward-compat); non-bool waarden zijn errors.
- `_check_mathblock_klasses`: onbekende klasse-waarden zijn errors;
  B2-mathblocks zonder `kgv`-veld geven een warning; `kgv` moet een positieve
  integer zijn.

### Frontend

- **Layout omgezet naar 2-kolom grid**: main-content links (invoer + schema),
  inspector rechts (320px breed). Responsive fallback naar 1-kolom <960px.
- **Inspector-sectie "Randvoorwaarden"**: toggle-switch voor
  "Uitkomst vereenvoudigen" met uitleg-tekst. Altijd zichtbaar.
- **Inspector-sectie "Mathblocks"**: verschijnt na Parse. Per mathblock een
  rij met ID, step-nummer, input-preview en een A1/B1/B2 pill-toggle. Klikken
  selecteert de klasse; state blijft bewaard tot `Wissen` of nieuwe Parse.
- **Inspector-state** (in `app.js`) wordt automatisch meegestuurd bij
  `Exporteer JSON`.

### Tests

Twee nieuwe test-files:

- **`tests/test_klasse_randvoorwaarden.py`** — 26 unit tests: LCM-helpers,
  noemer-extractie, exporter-gedrag met/zonder klasses/randvoorwaarden,
  validator-fouten en waarschuwingen.
- **`tests/test_inspector_e2e.py`** — 16 end-to-end integratie-tests die de
  volledige HTTP-flow verifiëren: `/api/process` geeft mathblocks terug,
  `/api/export_json` accepteert inspector-velden, het geschreven JSON-bestand
  bevat `randvoorwaarden` en per-mathblock `klasse` + `kgv`.

**Totaal: 15 smoke + 37 unit + 17 round-trip + 6 error-integratie + 8
check-export + 26 klasse-unit + 16 inspector-e2e = 125 tests groen.**

### Ontwerpkeuzes

- **Hint-teksten NIET in de JSON.** Het werkblad krijgt alleen de `klasse` en
  kiest zelf de juiste hint-tekst uit een centrale template-tabel. Voordelen:
  consistentie, geen JSON-bloat, en geen hergeneratie van oude opgaven nodig
  als de hint-formuleringen verbeteren.
- **A1 als default** voor alle optel-mathblocks. De docent moet expliciet
  B1 of B2 kiezen. Veilig minimum.
- **`klasse`-veld optioneel** op elk mathblock (niet alleen optellingen).
  Het schema is ruim genoeg om later klassen voor vermenigvuldiging of deling
  toe te voegen zonder breuken te maken in bestaande opgaven.

### Niet in deze iteratie (zie `ROADMAP.md`)

- **Linker inspector** voor overzicht/beheer van bestaande opgaven.
- **Model A**: automatisch genereren van tussenstappen per klasse en
  werkblad-validatie van die tussenstappen.
- **Pipeline-bug 311_007** (mathblocks zonder operation-entry in node_map).

---

## Iteratie 3 — UI/UX & visuele afwerking (19 april 2026)

Herindeling van de bestaande features (geen nieuwe functionaliteit) en een
eigen visuele taal. Nieuwe bevestigingsflow bij JSON-export.

### Herindeling

- **Layout omgedraaid.** Was: invoerveld onderaan, SVG bovenaan. Nu: invoer
  bovenaan, schema eronder — volgt de natuurlijke leesrichting.
- **Actieknoppen op eigen rij** onder het invoerveld, met duidelijke hiërarchie:
  `Parse` (primair, donker), `Exporteer JSON` (secundair, wit),
  `Wissen` (ghost). Knop-labels in Nederlands; oude cryptische "OK"/"JSON"/"Clear"
  vervangen. Statusregel staat rechts naast de knoppen.
- **Mode-toggle als pill-switch** naast het label, niet meer als losse
  knop tussen label en invoerveld.
- **Inline CSS weg uit HTML.** Was: grijze box met inline style-attribute.
  Nu: semantische `<aside class="pipeline-info">` met `<dl>`, gestyled in
  app.css.
- **Pipeline-info samenvatting** verschijnt pas ná een succesvolle parse,
  en toont: de platte expressie (tekst) en de LaTeX-string die naar de
  JSON gaat. Was eerder verspreid over twee losse divs.
- **Header toont live telling**: "N bewerkingen · M waarden" in monospace,
  rechts in de header, alleen na succesvolle parse.
- **Placeholder-scherm** in de SVG-container: grote regel "Nog geen schema"
  + subregel "Typ een expressie en druk op <kbd>Parse</kbd>", in plaats
  van de vage grijze zin die er eerder stond.

### Visuele taal

Refined-editorial richting: kalme papieren achtergrond, diep-inkt tekst,
mosterd-oker accent.

- **Palet**: off-white papier (`#f6f4ed`), panelen iets lichter
  (`#fbfaf5`), inkt-tekst (`#1c1f26`), mosterd accent (`#ae7a15`).
  Feedback-kleuren gedempt (niet de standaard-rood/groen).
- **Typografie**: drie webfonts van Google Fonts — Fraunces (display serif)
  voor labels en titels, IBM Plex Sans voor UI-tekst, JetBrains Mono voor
  code en expressies. Alle drie variabel, preload'd.
- **Geen gradients, shadows of gloss.** Platte oppervlakken, dunne 1px-randen.
  Componenten onderscheiden zich via contrast, niet via diepte.
- **Design tokens** in `:root` als CSS-variabelen (kleuren, fonts, radii)
  — één plek om de look aan te passen.

### Bevestigingsdialoog bij export

- **Nieuwe flow**: klik op `Exporteer JSON` → backend checkt duplicaten →
  dialoog toont expressie, doelmap en eventuele waarschuwing →
  gebruiker klikt `Exporteren` of `Annuleren`.
- **Duplicaat-detectie**: matcht op de platte `tekst`-expressie (stabieler
  dan LaTeX-vergelijking). Als er al bestanden met dezelfde expressie zijn,
  toont de dialoog welke filenames dat zijn. Export gaat door met een nieuw
  volgnummer; bestaande bestanden blijven staan (per afspraak).
- **Dialog-UX**: `Escape` of klik buiten dialoog sluit 'm. `Enter` bevestigt
  (focus staat automatisch op de primaire knop). Semantische `role="dialog"`
  + `aria-modal="true"`.

### Nieuw endpoint

- **`POST /api/check_export`** (in `server.py`) — neemt `latex`, geeft terug:
  `{success, expression, output_dir, duplicates: [filenames]}`. Leest
  alleen, schrijft niets. Matcht op `metadata.expressie.tekst` van
  bestaande JSONs in de output-dir.

### Tests

- **`tests/test_check_export.py`** — 8 integratie-tests voor het nieuwe
  endpoint: lege dir, na export, andere expressie, lege input, alle
  verplichte response-velden aanwezig. **8/8 geslaagd.**
- Smoke test had een false-positive heuristiek (`regel-telling < 100`)
  die faalde op de nieuwe rijkere `index.html`. Vervangen door een regex
  die expliciet naar inline `<script>`-content zoekt.

**Totaal: 14 smoke + 37 unit + 17 round-trip + 6 error-integratie +
8 check-export = 82 tests groen.**

### Niet veranderd

- De pipeline en alle bestaande endpoints (`/api/process`, `/api/export_json`)
  gedragen zich identiek. Iteratie 3 voegde alleen een endpoint toe en
  herindeelde de frontend.
- Het `OUTPUT_DIR`-pad is ongewijzigd (`~/Desktop/formath_JSON/`).
- MathLive-integratie onveranderd.

---

## Iteratie 2 — Validatie & foutafhandeling (17 april 2026)

Drie bugs gevonden en gefixt, plus een complete test-infrastructuur.

### Bugs gevonden en gefixt

- **🔴 `metadata.expressie.latex` ontbrak in de output.** De exporter schreef
  `latex_display` (naast `tekst` en `mathml`), maar het werkblad verwacht
  een veld dat letterlijk `latex` heet. JSON-outputs waren daardoor niet
  laadbaar in het werkblad-prototype. Fix in `json_exporter.py`: `latex`
  is nu de primaire sleutel (met de AST-teruggerekende LaTeX); `tekst`
  blijft behouden voor de platte ascii-math.

- **🟡 ROOT-conventie mismatch.** `latex_to_expression` in `server.py`
  schreef `\sqrt[3]{27}` als `root(27,3)`, maar `expression_parser.py`
  verwacht `root(n, x)` = n-de wortel van x. Een derdemachtswortel
  rendered daardoor als `\sqrt[27]{3}` in plaats van `\sqrt[3]{27}`.
  Fix in `server.py` regel 68 (regex-argumentvolgorde omgedraaid);
  regressietest `test_sqrt_nth_roundtrip` toegevoegd.

- **🟡 Documentatiefout in INSTALLATIE.txt.** De sectie OPMERKINGEN claimde
  dat de punt (.) als vermenigvuldiging wordt geïnterpreteerd. De parser
  ondersteunt dat niet — `2.(9+3)` crasht met "Onbekend karakter: '.'".
  INSTALLATIE.txt bijgewerkt naar de werkelijk ondersteunde operatoren
  (`*`, `×`, `\cdot`, `/`, `:`).

### Nieuw: testinfrastructuur

Zeven assets in `tests/`:

- **`formath_validator.py`** — schema-validator die een JSON-dict toetst
  tegen `SPECIFICATIE_AST.md`. Checkt top-level velden, MathJSON heads
  (`Add`, `Negate`, `Multiply`, `Divide`, `Rational`, `Power`, `Sqrt`,
  `Root`) met arity-controle, `node_map`-structuur, en kruisverwijzingen
  tussen `node_map` ↔ `mathblocks`, `steps` ↔ `mathblocks` en
  `duo_verzameling` ↔ `mathblocks`. CLI en programmatische API
  (`validate_opgave(dict) -> ValidationResult`).

- **`test_round_trip.py`** — draait de volledige pipeline op 16 expressies
  (11 originele voorbeelden + 5 edges) en valideert elke output tegen
  de specificatie. Resultaat: **16/16 geslaagd** (1 warning op 311_007
  — zie "Bekende issues" hieronder).

- **`test_latex_conversion.py`** — 32 unit tests op `latex_to_expression`
  en de AST → LaTeX-display conversie, inclusief 6 round-trip property
  tests die bewijzen dat `expr → AST → LaTeX → expr' → AST'` dezelfde
  AST produceert. Resultaat: **32/32 geslaagd**.

- **`test_error_integration.py`** — bevestigt dat parse-fouten via
  `/api/process` en `/api/export_json` als gestructureerde `FriendlyError`
  in het JSON-response terechtkomen. Resultaat: **6/6 geslaagd**.

- **`tests/README.md`** — handleiding voor het draaien van de tests.

### Nieuw: gebruikersvriendelijke parser-fouten

- **`python_bestanden/error_formatter.py`** — vertaalt technische parser-
  foutmeldingen (bv. "Unexpected token in factor") naar Nederlandse
  uitleg met optionele tip en visuele snippet (met `^` onder de
  foutpositie). 8 patronen gedekt: onbekend karakter, ongesloten haakje,
  ongesloten vierkante haak, halverwege afgebroken expressie, onverwacht
  teken na einde, verkeerd aantal argumenten voor `sqrt` en `root`,
  onbekende functie. Generieke fallback voor onbekende foutmeldingen.

- **Server-integratie** — `/api/process` en `/api/export_json` geven nu
  een `error_detail` dict terug met `message`, `hint`, `position`,
  `snippet` en `raw` in plaats van een rauw `"Parse fout: Parser error at
  token Token(...)"`.

- **Frontend-rendering** — `app.js` heeft een `renderError(data)` helper
  die de snippet in een monospace block toont met de hint eronder.
  Styling in `app.css` (`.error-snippet`, `.error-hint`).

### Bekende issues (voor iteratie 3+)

- **311_007** (`[(3^2)*(12-9)^3]:(9-6)^3:(-3)*[(-6)^2]:3^4+(-2)^3`) produceert
  9 mathblocks zonder `operation`-entry in `node_map`. Cursor-tracking
  en pinpointing in het werkblad werken niet voor die blocks. Structureel
  probleem in `_build_mathjson_ast`; valt buiten de scope van iteratie 2.

### Niet aangeraakt

De pipeline-logica zelf (`expression_parser`, `ast_normalizer`,
`manifold_*`, `ast_visualizer`, `_build_mathjson_ast`) is inhoudelijk
ongewijzigd — de test-suites dekken de bestaande gedragingen zonder er
iets aan te wijzigen. Dat maakt iteratie 3 (UI/UX) veilig en iteratie 4
(pipeline-verbeteringen zoals de 311_007-warning) gefundeerd op een
bestaande test-safety-net.

---

## Iteratie 1 — Opruimen & fundament (17 april 2026)

Eerste professionaliseringsslag. Doel: dode code weg, één waarheid voor paden,
frontend in modulaire bestanden, en een reproduceerbare smoke test. Geen
gedragswijzigingen in de pipeline zelf.

### Gewijzigd

- **Dode code gearchiveerd** naar `_archief/python_bestanden/` (niet verwijderd):
  - `json_exporter_oud.py`, `manifold_detector_oud.py`, `manifold_converter_oud.py`
  - `json_generator_v2.py`, `step_calculator.py`, `tak_allocator.py`
    (de laatste twee waren alleen door `json_generator_v2` gebruikt — transitief dood)
  - `grid_visualizer.py`
  - `ast_to_mathjson.py` — niet equivalent aan de actieve `_build_mathjson_ast()`
    in `json_exporter.py` (test bevestigde verschillende MathJSON-bomen en
    node_maps op 5 voorbeeldexpressies). Gearchiveerd om toekomstige verwarring
    te voorkomen.

  Netto: ~8.465 → ~3.890 regels actieve Python-code (−54%).

- **Output-pad geconsolideerd** naar één waarheid:
  - Was: code gebruikte `~/Desktop/JSON_files_ForMath`, docstrings en
    `INSTALLATIE.txt` verwezen naar `~/Desktop/formath_JSON`.
  - Nu: overal `~/Desktop/formath_JSON/`, gedefinieerd in
    `python_bestanden/json_exporter.py` als `OUTPUT_DIR`-constante.

- **Frontend gesplitst** (`formath_web/`):
  - Was: `index.html` (611 regels) met inline `<style>` en `<script>`.
  - Nu: `index.html` (59 r) + `app.css` (295 r) + `app.js` (255 r).
  - Typo `Kunje ` vóór `<!DOCTYPE html>` verwijderd.

- **Kleine kwaliteitsfixes** in `formath_web/server.py`:
  - Docstring op `_node_to_latex_unbracketed()` is nu een raw string — lost
    `SyntaxWarning: invalid escape sequence '\l'` op.
  - TCP-bind van `""` → `"127.0.0.1"`: server luistert nu alleen op localhost,
    niet op alle netwerk-interfaces.

- **`INSTALLATIE.txt`** bijgewerkt: nieuwe frontend-structuur (3 bestanden),
  `json_exporter.py` staat nu correct in `python_bestanden/`, output-pad
  consistent beschreven.

### Nieuw

- `_archief/smoke_test.py` — end-to-end test zonder server-proces.
  Test statische file serving, `/api/process` op 4 expressies, en
  `/api/export_json` met validatie dat `metadata.expressie.ast`
  (met `tree` en `node_map`) aanwezig is. Resultaat iteratie 1: **14/14**.

  Draaien:

      cd formath
      python3 _archief/smoke_test.py

- `_archief/README.md` — overzicht van alle gearchiveerde modules met
  reden per bestand.

### Niet aangeraakt

De pipeline zelf (`expression_parser`, `ast_normalizer`, `manifold_detector`,
`manifold_converter`, `ast_visualizer`, `json_exporter`) is inhoudelijk
onveranderd. Ook `latex_to_expression()` en `_node_to_latex()` in `server.py`
zijn niet aangepast — die komen in iteratie 2 aan de beurt met tests en
betere foutafhandeling.
