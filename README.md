# ForMath Authortool

Lokale tool voor het invoeren, valideren en exporteren van wiskunde-opgaven
voor gebruik in een afnemende studenttool. Een Python HTTP-server met een
browser-gebaseerde frontend op basis van MathLive.

## Wat het doet

De Authortool laat een docent of curriculum-auteur:

- een wiskunde-expressie invoeren via MathLive (met LaTeX-snelkoppelingen);
- de expressie automatisch laten parsen tot een abstract syntax tree;
- de AST visueel inspecteren als SVG;
- per mathblock hints, klassificatie en randvoorwaarden invoeren;
- de opgave exporteren als gestructureerde JSON plus SVG voor gebruik in
  de studenttool;
- opgaven organiseren in folders, met een prullenbak via rechtsklik;
- de structurele integriteit van de gegenereerde JSON automatisch laten
  valideren voor opslag.

## Architectuur

De code staat in twee hoofd-directories:

- `formath_web/` is de HTTP-server (`server.py`, poort 8765) plus de
  browser-frontend (`index.html`, `app.js`, `app.css`) en de JSON-schemas
  voor klassificatie.
- `python_bestanden/` bevat gedeelde pipeline-modules: `config.py`,
  `folder_manager.py`, `json_validator.py`. Daaronder staan twee sub-folders
  `getallen/` en `letters/` met de daadwerkelijke pipeline-code per soort
  opgave.

De opgaven-data wordt op een aparte locatie bewaard (default:
`~/Desktop/ForMath_Exercise/`). Die locatie is configureerbaar via
`python_bestanden/config.json` (zie installatie hieronder).

## Installatie

Vereisten: macOS of Linux, Python 3.10 of nieuwer, een moderne browser.

1. Clone de repo en ga erin staan.

2. Maak je eigen `config.json` aan op basis van het voorbeeld:

       cp python_bestanden/config.json.example python_bestanden/config.json

   Pas vervolgens in `python_bestanden/config.json` het pad aan naar de
   locatie waar je je opgaven wilt bewaren. De map hoeft nog niet te
   bestaan; hij wordt automatisch aangemaakt.

3. Start de server:

       cd formath_web
       python3 server.py

4. Open in je browser: `http://localhost:8765`

## Gebruik

- Typ een expressie in het MathField en druk op Parse (of Enter).
- Bekijk de gegenereerde AST in het SVG-paneel; schakel naar JSON-weergave
  via de toggle.
- Bewerk hints en randvoorwaarden in de inspector rechts.
- Klik Opslaan: vul het metadata-formulier in en bevestig om de opgave als
  JSON plus SVG weg te schrijven.
- Klik op het vraagteken-icoon rechtsboven voor een help-overlay met uitleg
  per onderdeel. Labels in de help-overlay zijn versleepbaar; de
  verbindingslijn blijft mee bewegen.

## Workflow voor wijzigingen aan deze repo

Standaard cyclus:

    cd ~/Desktop/Authortool
    git status
    git add .
    git commit -m "Korte uitleg van de wijziging"
    git push

Voor sommige werkstromen handig:

- `git log --oneline -10` toont de laatste tien commits.
- `git diff` toont nog niet-gecommiteerde wijzigingen.
- `git checkout <bestand>` gooit nog niet-gecommiteerde wijzigingen aan
  een bestand weg.

## Status en roadmap

Zie `CHANGELOG.md`, `PROJECT_STATUS.md` en `ROADMAP.md` voor de actuele
stand van zaken.

Belangrijke onderdelen die in ontwikkeling zijn:

- Rondes 2 tot en met 4 van de letters-pipeline (a+a wordt 2a, enzovoort);
- Een afnemende studenttool die de gegenereerde JSON kan afspelen.

## Licentie

Nog te bepalen. Repo is voorlopig prive.
