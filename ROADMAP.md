# ForMath Opgave Invoertool — Roadmap

Dit document noteert geplande uitbreidingen en open ontwerpbeslissingen
voor toekomstige iteraties. Afgeronde iteraties staan in `CHANGELOG.md`.

---

## Geplande iteraties

### Model A — tussenstap-controle per klasse

**Status:** beslist in iteratie 4 om dit later te doen (zie `CHANGELOG.md`
iteratie 4 — werken volgens "model B").

De huidige implementatie (model B) gebruikt `klasse` alleen als metadata
voor hint-selectie in het werkblad. Als later tussenstap-controle gewenst
is (docent wil dat student de kruislingsmethode écht uitvoert), moet:

- De pipeline per klasse een canonieke tussenstap-expressie genereren
- De JSON een `tussenstap`-veld per mathblock bevatten
- Het werkblad tussenstap-validatie uitvoeren naast eindwaarde-validatie

---

### Pipeline-bug 311_007 — mathblocks zonder operation-entry in node_map

**Status:** bekend issue sinds iteratie 2.

Complexe expressie
`[(3^2)*(12-9)^3]:(9-6)^3:(-3)*[(-6)^2]:3^4+(-2)^3` levert 9 mathblocks
zonder `operation`-entry in `node_map` (cursor-tracking werkt dan niet).
Structureel probleem in `_build_mathjson_ast`; valt buiten iteratie 4.

---

### Opgavenbeheer uitbreidingen

**Status:** basis geïmplementeerd in iteratie 5; vervolgen mogelijk.

- **Zoeken / filteren** op expressie-inhoud of ID-prefix in de opgave-lijst
- **Groeperen** op datum, klasse of thema (tags?)
- **Archiveren** als alternatief voor verwijderen
- **Direct pushen naar werkblad** vanuit de invoertool (tight integration)
- **Batch-operaties**: meerdere opgaven tegelijk verwijderen of exporteren

