/* ─── DOM refs ────────────────────────────────────────────────────── */
const mathField        = document.getElementById('math-input');
const textInput        = document.getElementById('text-input');
const svgContainer     = document.getElementById('svg-container');
const svgInner         = document.getElementById('svg-inner');
const placeholderText  = document.getElementById('placeholder-text');
const statusEl         = document.getElementById('status');  // oude inline, verborgen via CSS
const headerMeta       = document.getElementById('header-meta'); // verwijderd uit HTML, null-safe
const statusbarMeta    = document.getElementById('statusbar-meta');
const statusbarStatus  = document.getElementById('statusbar-status');
const btnOk            = document.getElementById('btn-ok');
const btnJson          = document.getElementById('btn-json');
const btnClear         = document.getElementById('btn-clear');
const zoomLevelEl      = document.getElementById('zoom-level');
const pipelineInfo     = document.getElementById('pipeline-info');
const infoTekst        = document.getElementById('info-tekst');
const infoLatex        = document.getElementById('info-latex');

const dialog           = document.getElementById('export-dialog');
const dialogExpr       = document.getElementById('dialog-expr');
const dialogDir        = document.getElementById('dialog-dir');
const dialogDupWarn    = document.getElementById('dialog-dup-warning');
const dialogDupList    = document.getElementById('dialog-dup-list');
const dialogConfirm    = document.getElementById('dialog-confirm');

// Inspector refs
// Oude inspector-refs (elementen zijn weg, maar refs null-safe maken voor compat)
const rvSimplify       = document.getElementById('rv-simplify');
const mbSection        = document.getElementById('mb-section');
const mbList           = document.getElementById('mb-list');
const mbPlaceholder    = document.getElementById('mb-placeholder');

// Nieuwe hints-editor refs
const hintsAccordion   = document.getElementById('hints-accordion');
const hintsPlaceholder = document.getElementById('hints-placeholder');
const hintsSavebar     = document.getElementById('hints-savebar');
const hintsDirtyCount  = document.getElementById('hints-dirty-count');
const btnHintsSave     = document.getElementById('btn-hints-save');
const hintsSubtitle    = document.getElementById('hints-subtitle');
const inspectorAside   = document.getElementById('inspector');
const inspectorRail    = document.getElementById('inspector-rail');
const btnCollapse      = document.getElementById('btn-inspector-collapse');
const appMain          = document.querySelector('.app-main');

// Opgavenbeheer (linker inspector) refs
const olAside          = document.getElementById('opgave-lijst');
const olRail           = document.getElementById('ol-rail');
const btnOlCollapse    = document.getElementById('btn-ol-collapse');
const olList           = document.getElementById('ol-list');
const olPlaceholder    = document.getElementById('ol-placeholder');
const olCount          = document.getElementById('ol-count');
const btnEdit          = document.getElementById('btn-edit');
const btnDelete        = document.getElementById('btn-delete');
const viewSvgBtn       = document.getElementById('view-svg');
const viewJsonBtn      = document.getElementById('view-json');
const svgContainerEl   = document.getElementById('svg-container');
const jsonView         = document.getElementById('json-view');
const deleteDialog     = document.getElementById('delete-dialog');
const deleteIdEl       = document.getElementById('delete-id');
const deleteConfirmBtn = document.getElementById('delete-confirm');
const dialogOverwriteChoice = document.getElementById('dialog-overwrite-choice');
const dialogOverwriteId     = document.getElementById('dialog-overwrite-id');

// Dropdowns boven de input
const soortOpgaveSelect = document.getElementById('soort-opgave-select');
const productieSelect   = document.getElementById('productie-select');
const opdrachtSelect    = document.getElementById('opdracht-select');

// Defaults (single source of truth)
const SOORT_OPGAVE_DEFAULT = 'rekenen_getallen';
const PRODUCTIE_DEFAULT    = 'enkelvoudig';
const OPDRACHT_DEFAULT     = 'reken_uit';
// Nieuwe metadata-velden (sub-ronde D)
const ONDERWIJSTYPE_DEFAULT    = 'havo';
const ONDERWIJSNIVEAU_DEFAULT  = 'onderbouw';

let currentSoortOpgave    = SOORT_OPGAVE_DEFAULT;
let currentProductie      = PRODUCTIE_DEFAULT;
let currentOpdracht       = OPDRACHT_DEFAULT;
let currentOnderwijstype  = ONDERWIJSTYPE_DEFAULT;
let currentOnderwijsniveau = ONDERWIJSNIVEAU_DEFAULT;
let currentNotitie        = '';

// Lookup-tabellen voor mooie labels in de statische topbalk
const META_LABEL_MAP = {
    soort: {
        'rekenen_getallen': 'Rekenen met getallen',
        'rekenen_letters': 'Rekenen met letters',
        'simpele_vergelijkingen': 'Simpele vergelijkingen',
    },
    onderwijstype: {
        'basisonderwijs': 'Basisonderwijs',
        'vmbo': 'vmbo',
        'havo': 'havo',
        'vwo': 'vwo',
        'mbo': 'mbo',
        'hbo': 'hbo',
        'wo': 'wo',
    },
    onderwijsniveau: {
        'brugklas': 'Brugklas',
        'onderbouw': 'Onderbouw',
        'bovenbouw': 'Bovenbouw',
    },
    opdracht: {
        'reken_uit': 'Reken uit',
        'vereenvoudig': 'Vereenvoudig',
    },
    productie: {
        'enkelvoudig': 'Enkelvoudig',
        'sjabloon': 'Sjabloon',
    },
};

/* ─── State ───────────────────────────────────────────────────────── */
let textMode = false;
let currentZoom = 1;
let lastProcessed = null;   // { latex, tekst, latex_display, ast } na succesvolle parse
let hasUnparsedChanges = false;  // true als expressie is gewijzigd sinds LAATSTE PARSE
                                  // - bij invoer-event:        true  (Parse wordt actief)
                                  // - na succesvolle parse:    false (Opslaan wordt actief)
                                  // - bij selectOpgave:        false (geladen ≡ geparsed)
let justSaved = false;            // true direct na opslaan, totdat er weer iets gebeurt
                                  // (gebruikt om Delete tijdelijk uit te zetten na save)
let editSessionTouched = false;   // true als er in de huidige edit-sessie iets is gebeurd
                                  // (wijziging, parse, opslaan). Reset bij toggleEdit.
                                  // Bepaalt of Wissen in edit-modus actief is.

// Inspector-state (oude delen, nog gebruikt door server.py export)
const inspectorState = {
    randvoorwaarden: {
        // Defaults volgens specificatie
        vereenvoudig_uitkomst: false,    // bestaande optie (werd gebruikt voor SIMPLIFY_OP)
        antwoord_in_breuken: true,       // 1. Rekensom met antwoord in breuken
        antwoord_in_decimalen: false,    // 2. Rekensom met antwoord in decimalen
        decimalen_afronden: 2,           // 2a. Afronden op n decimalen achter de komma
        pi_decimalen: 2,                 // 3. Aantal decimalen pi
        uitkomst_als_gemengd_getal: true, // 4. Uitkomst als gemengd getal
        hints_aan: true,                 // 5. Hints staan aan
        feedback_aan: true,              // 6. Feedback staat aan
    },
    klasses: {},                    // { mathblock_id: "A1" | "B1" | "B2" }
    classificatie: {},              // zie classificatie_schema.json — leeg = ongeclassificeerd
};

// Sticky defaults: blijven hangen tussen opgaven binnen één sessie.
// Worden NIET geleegd door resetInspector(). Worden bijgewerkt zodra de
// auteur ze aanpast, en gebruikt als default voor de volgende lege opgave.
const classificatieDefaults = {
    stroom: [],         // bv. ['havo', 'vwo']
    leerjaar: [],       // bv. [3, 4]
    bron: '',
    auteur: '',
};

// Hints-editor state. Bevat per mathblock-id de bewerkbare hints + feedback.
// - original: wat oorspronkelijk uit de JSON kwam (read-only referentie voor "dirty?")
// - edits:    live bewerkte versie (wat de textareas tonen)
// - openId:   welke accordion-sectie momenteel uitgeklapt is (één tegelijk)
const hintsState = {
    mathblocks: [],   // lijst van mathblock-metadata voor rendering {id, step, symbool, beschrijving}
    original: {},     // { mb_id: { structureel:{...}, feedback:{...}, didactisch:{...} } }
    edits:    {},     // idem, maar bewerkt
    openId:   null,
};

// Opgavenbeheer state
let selectedOpgaveId = null;    // null = geen selectie (nieuwe opgave)
let selectedOpgaveJson = null;  // volledige JSON van geselecteerde opgave
let selectedOpgaveSvg = null;   // bijbehorende SVG-tekst
let editMode = false;           // math-field op slot (false) of vrijgegeven (true)
let currentView = 'svg';        // 'svg' | 'json'

const ZOOM_MIN  = 0.2;
const ZOOM_MAX  = 3;
const ZOOM_STEP = 0.15;

/* ─── Utilities ───────────────────────────────────────────────────── */

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function setStatus(html, type) {
    // Schrijf naar oude inline element (voor backwards-compat) en naar statusbar
    if (statusEl) {
        statusEl.className = 'status' + (type ? ' ' + type : '');
        statusEl.innerHTML = html;
    }
    if (statusbarStatus) {
        statusbarStatus.className = 'statusbar-status' + (type ? ' status-' + type : '');
        statusbarStatus.innerHTML = html;
    }
}

function clearStatus() {
    if (statusEl) {
        statusEl.className = 'status';
        statusEl.innerHTML = '';
    }
    if (statusbarStatus) {
        statusbarStatus.className = 'statusbar-status';
        statusbarStatus.innerHTML = '';
    }
}

function renderError(data) {
    const detail = data.error_detail;
    if (!detail) {
        setStatus('Fout: ' + escapeHtml(data.error || 'onbekend'), 'error');
        return;
    }
    let html = '<strong>' + escapeHtml(detail.message) + '</strong>';
    if (detail.snippet) {
        html += '<pre class="error-snippet">' + escapeHtml(detail.snippet) + '</pre>';
    }
    if (detail.hint) {
        html += '<div class="error-hint">' + escapeHtml(detail.hint) + '</div>';
    }
    setStatus(html, 'error');
}

/* ─── Mode wissel ─────────────────────────────────────────────────── */

function setMode(mode) {
    textMode = (mode === 'text');
    document.body.classList.toggle('text-mode', textMode);
    document.getElementById('mode-math').classList.toggle('is-active', !textMode);
    document.getElementById('mode-text').classList.toggle('is-active', textMode);
    // Quick-buttons alleen in math-modus zichtbaar
    const qb = document.getElementById('quick-buttons');
    if (qb) qb.hidden = textMode;
    // Focus op actieve veld
    setTimeout(() => {
        try {
            if (textMode) { textInput.focus(); textInput.select(); }
            else           { mathField.focus(); }
        } catch (e) {}
    }, 30);
}

function getExpression() {
    if (textMode) return textInput.value.trim();
    try {
        return mathField.getValue('latex').trim();
    } catch (e) {
        return mathField.value.trim();
    }
}

/* ─── Zoom ────────────────────────────────────────────────────────── */

function setZoom(level) {
    currentZoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, level));
    svgInner.style.transform = `scale(${currentZoom})`;

    // Pas ook expliciete width/height op svg-inner aan, zodat de browser
    // weet hoeveel layoutruimte het element inneemt. Zonder dit klopt de
    // scrollbar niet: transform: scale schaalt visueel, maar laat de layout-
    // grootte staan op het origineel — bij grote SVG's blijft dan een deel
    // (vaak de top) onbereikbaar via de scrollbalk.
    const svg = svgInner.querySelector('svg');
    if (svg) {
        const w = parseFloat(svg.getAttribute('width'))  || svg.viewBox?.baseVal?.width  || 0;
        const h = parseFloat(svg.getAttribute('height')) || svg.viewBox?.baseVal?.height || 0;
        if (w && h) {
            svgInner.style.width  = (w * currentZoom) + 'px';
            svgInner.style.height = (h * currentZoom) + 'px';
        }
    }

    zoomLevelEl.textContent = Math.round(currentZoom * 100) + '%';
}

function zoomIn()  { setZoom(currentZoom + ZOOM_STEP); }
function zoomOut() { setZoom(currentZoom - ZOOM_STEP); }

function zoomFit() {
    const svg = svgInner.querySelector('svg');
    if (!svg) return;
    const wrapperRect = svgContainer.getBoundingClientRect();
    const svgW = svg.getAttribute('width')
              || svg.viewBox?.baseVal?.width
              || svg.getBoundingClientRect().width;
    const svgH = svg.getAttribute('height')
              || svg.viewBox?.baseVal?.height
              || svg.getBoundingClientRect().height;
    const scaleX = (wrapperRect.width  - 40) / svgW;
    const scaleY = (wrapperRect.height - 40) / svgH;
    setZoom(Math.min(scaleX, scaleY, 1.5));
    svgContainer.scrollLeft = 0;
    svgContainer.scrollTop  = 0;
}

/* Scroll-to-zoom */
svgContainer.addEventListener('wheel', (e) => {
    if (svgContainer.classList.contains('is-empty')) return;
    e.preventDefault();
    setZoom(currentZoom + (e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP));
}, { passive: false });

/* Drag-to-pan */
let isDragging = false, dragStartX, dragStartY, scrollStartX, scrollStartY;

svgContainer.addEventListener('mousedown', (e) => {
    if (svgContainer.classList.contains('is-empty')) return;
    isDragging = true;
    dragStartX = e.clientX; dragStartY = e.clientY;
    scrollStartX = svgContainer.scrollLeft;
    scrollStartY = svgContainer.scrollTop;
    svgContainer.style.cursor = 'grabbing';
});

window.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    svgContainer.scrollLeft = scrollStartX - (e.clientX - dragStartX);
    svgContainer.scrollTop  = scrollStartY - (e.clientY - dragStartY);
});

window.addEventListener('mouseup', () => {
    isDragging = false;
    svgContainer.style.cursor = '';
});

/* ─── Text-input events ───────────────────────────────────────────── */

textInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        processExpression();
    }
});

/* Bij elke wijziging in tekstveld of math-field: markeer expressie als dirty
   en herbereken knop-states.

   MathLive vuurt 'input' soms niet betrouwbaar (afhankelijk van versie en hoe
   de waarde verandert). We luisteren daarom op meerdere events en gebruiken
   ook een keydown-fallback voor het rauwe toetsenbord. */

function _markDirty() {
    hasUnparsedChanges = true;
    justSaved = false;
    editSessionTouched = true;
    updateButtonStates();
}

textInput.addEventListener('input', _markDirty);
textInput.addEventListener('keyup', _markDirty);
textInput.addEventListener('paste', () => setTimeout(_markDirty, 0));

// MathLive: 'input' is de officiële, maar 'change' werkt ook. Beide hechten
// helpt voor robuustheid over versies heen.
mathField.addEventListener('input', _markDirty);
mathField.addEventListener('change', _markDirty);
mathField.addEventListener('keyup', _markDirty);
// Voor virtueel-toetsenbord en menu-acties die geen keyup geven:
mathField.addEventListener('focus', () => {
    // Bij focus markeren we (nog) niet dirty — alleen daadwerkelijke wijziging
    // moet dat doen. Maar we zorgen wel dat de knop-staat klopt.
    updateButtonStates();
});

/* ─── Centrale knop-state machine ──────────────────────────────────────
 * Implementeert de matrix uit Knoppen_Authortool.xlsx:
 *
 * NIEUWE OPGAVE (geen selectie):
 *   Parse:    actief als hasUnparsedChanges
 *   Opslaan:  actief als hasParse && !hasUnparsedChanges
 *   Edit:     niet zichtbaar (hidden)
 *   Delete:   niet zichtbaar (hidden)
 *
 * BESTAANDE OPGAVE (geselecteerd uit lijst):
 *   Parse:    actief alleen in edit-modus én hasUnparsedChanges
 *   Opslaan:  actief alleen in edit-modus én editSessionTouched
 *             én hasParse && !hasUnparsedChanges én !justSaved
 *   Edit:     zichtbaar; tekst toggelt tussen 'Edit toestaan' / 'Edit vergrendelen'
 *   Delete:   zichtbaar; actief tenzij net opgeslagen
 *
 * WISSEN (geldt overal, beide takken):
 *   actief tenzij het scherm én de expressie volledig leeg zijn,
 *   d.w.z. niets te wissen valt: geen parse, geen selectie, geen wijziging,
 *   geen tekst in invoervelden.
 */
function updateButtonStates() {
    const hasSelection = !!selectedOpgaveId;
    const hasParse = !!lastProcessed;
    const hasContent = (
        (textInput && textInput.value && textInput.value.trim().length > 0) ||
        (mathField && mathField.value && String(mathField.value).trim().length > 0)
    );
    // Wissen is actief tenzij echt alles leeg is.
    const screenIsEmpty = !hasParse && !hasSelection && !hasUnparsedChanges && !hasContent;

    if (!hasSelection) {
        // ── NIEUWE OPGAVE ──────────────────────────────────────
        if (btnOk)     btnOk.disabled    = !hasUnparsedChanges;
        if (btnJson)   btnJson.disabled  = !(hasParse && !hasUnparsedChanges);
        if (btnEdit)   btnEdit.hidden    = true;
        if (btnDelete) btnDelete.hidden  = true;
    } else {
        // ── BESTAANDE OPGAVE ───────────────────────────────────
        if (btnEdit)   btnEdit.hidden    = false;
        if (btnDelete) btnDelete.hidden  = false;

        if (editMode) {
            // Edit-modus AAN: gebruiker mag de expressie aanpassen
            if (btnOk)     btnOk.disabled    = !hasUnparsedChanges;
            if (btnJson)   btnJson.disabled  = !(editSessionTouched && hasParse && !hasUnparsedChanges) || justSaved;
            if (btnDelete) btnDelete.disabled = justSaved;
        } else {
            // Edit-modus UIT (default na selecteren of na vergrendelen)
            if (btnOk)     btnOk.disabled    = true;
            if (btnJson)   btnJson.disabled  = true;
            if (btnDelete) btnDelete.disabled = justSaved;
        }
        if (btnEdit)   btnEdit.disabled = false;
    }

    // Wissen: enkele globale regel — actief tenzij scherm leeg is
    if (btnClear)  btnClear.disabled = screenIsEmpty;
}

/* ─── Clear ───────────────────────────────────────────────────────── */

function clearAll() {
    textInput.value = '';
    try { mathField.setValue(''); } catch (e) {}
    svgInner.innerHTML = '';
    svgContainer.classList.add('is-empty');
    clearStatus();
    pipelineInfo.hidden = true;
    if (statusbarMeta) statusbarMeta.innerHTML = '';
    lastProcessed = null;
    hasUnparsedChanges = false;
    justSaved = false;
    editSessionTouched = false;
    setZoom(1);
    resetInspector();
    deselectOpgave();
    // Sub-ronde D: behoud de current* metadata-state, alleen Notitie wist.
    // De selects in topbalk zijn nu verborgen maar krijgen wel de huidige
    // waardes mee (zodat eventuele oude code consistente waardes ziet).
    currentNotitie = '';
    if (soortOpgaveSelect) {
        soortOpgaveSelect.value = currentSoortOpgave;
        soortOpgaveSelect.disabled = false;
    }
    if (productieSelect) {
        productieSelect.value = currentProductie;
        productieSelect.disabled = false;
    }
    if (opdrachtSelect) {
        opdrachtSelect.value = currentOpdracht;
        opdrachtSelect.disabled = false;
    }
    // Statische labels in topbalk bijwerken (waardes zijn niet gewijzigd,
    // maar het label voor 'soort' kan nog 'onbekend' tonen na een eerdere fout).
    if (typeof updateMetaLabels === 'function') updateMetaLabels();
    // Terug naar SVG-view (default)
    setView('svg');
    updateButtonStates();
}

/* ─── Parse ───────────────────────────────────────────────────────── */

async function processExpression() {
    const latex = getExpression();
    if (!latex) {
        setStatus('Voer eerst een expressie in.', 'error');
        return;
    }
    // Als er een opgave geselecteerd is en edit niet is toegestaan,
    // blokkeer Parse — anders zou je per ongeluk de view van de
    // opgave herberekenen met dezelfde input.
    if (selectedOpgaveId && !editMode) {
        setStatus('Klik eerst op <strong>Edit toestaan</strong> om de expressie te kunnen aanpassen.', 'info');
        return;
    }

    // Tijdens parsen: knoppen tijdelijk uit
    if (btnOk) btnOk.disabled = true;
    if (btnJson) btnJson.disabled = true;
    setStatus('<span class="spinner"></span>Verwerken…', 'info');

    try {
        const response = await fetch('/api/process', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                latex,
                randvoorwaarden: inspectorState.randvoorwaarden,
            })
        });
        const data = await response.json();

        if (!data.success) {
            renderError(data);
            return;
        }

        // SVG tonen
        svgContainer.classList.remove('is-empty');
        svgInner.innerHTML = data.svg;
        requestAnimationFrame(() => zoomFit());

        // Pipeline info samenvatting
        const tekst = data.data?.tekst || latex;
        const latexDisplay = data.data?.latex_display || latex;
        infoTekst.textContent = tekst;
        infoLatex.textContent = latexDisplay;
        pipelineInfo.hidden = false;

        // Header meta: mathblocks + steps (best-effort uit AST data)
        updateHeaderMeta(data);

        // Inspector: render mathblock-lijst voor klasse-keuze
        renderInspectorMathblocks(data.mathblocks || []);

        // Onthoud voor export
        lastProcessed = { latex, tekst, latex_display: latexDisplay, ast: data.ast };

        // Parse zojuist gelukt — geen onbewerkte wijzigingen meer
        hasUnparsedChanges = false;
        justSaved = false;
        editSessionTouched = true;

        // Classificatie-sectie tonen — auteur kan de opgave nu taggen
        showClassificatieSection(true);
        // Randvoorwaarden-sectie tonen en met huidige waarden vullen
        showRandvoorwaardenSection(true);
        fillRandvoorwaardenUI();

        setStatus('Schema gegenereerd.', 'success');

        // Focus herstel
        setTimeout(() => {
            try {
                if (textMode) textInput.focus();
                else           mathField.focus();
            } catch (e) {}
        }, 100);

    } catch (err) {
        setStatus('Verbindingsfout: ' + escapeHtml(err.message), 'error');
    } finally {
        // Knop-states opnieuw bepalen op basis van actuele state
        updateButtonStates();
    }
}

function updateHeaderMeta(data) {
    // /api/process geeft een clean_ast terug zonder expliciete mathblock-tellers,
    // maar we kunnen de AST recursief tellen. Eenvoudige heuristiek:
    // tel BINARY_OP / MANIFOLD_OP / MATROESJKA_OP / POWER / ROOT nodes.
    const ast = data.ast;
    if (!ast) { if (statusbarMeta) statusbarMeta.innerHTML = ''; return; }
    const counts = countNodes(ast);
    if (statusbarMeta) {
        statusbarMeta.innerHTML =
            `<span>${counts.ops} bewerkingen</span>` +
            `<span class="sep">·</span>` +
            `<span>${counts.leaves} waarden</span>`;
    }
}

function countNodes(node) {
    const OP_TYPES = new Set(['BINARY_OP','MANIFOLD_OP','MATROESJKA_OP','POWER','ROOT']);
    let ops = 0, leaves = 0;
    function walk(n) {
        if (!n || typeof n !== 'object') return;
        const t = n.type;
        if (OP_TYPES.has(t)) ops++;
        else if (t === 'NUMBER' || t === 'FRACTION') leaves++;
        for (const k of Object.keys(n)) {
            const v = n[k];
            if (Array.isArray(v)) v.forEach(walk);
            else if (v && typeof v === 'object') walk(v);
        }
    }
    walk(node);
    return { ops, leaves };
}

/* ─── Export flow ─────────────────────────────────────────────────── */

async function requestExport() {
    if (!lastProcessed) {
        setStatus('Eerst parsen (druk op Parse) voordat je exporteert.', 'error');
        return;
    }

    if (btnJson) btnJson.disabled = true;
    setStatus('<span class="spinner"></span>Duplicaten controleren…', 'info');

    try {
        const resp = await fetch('/api/check_export', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ latex: lastProcessed.latex })
        });
        const data = await resp.json();
        clearStatus();

        if (!data.success) {
            setStatus('Fout: ' + escapeHtml(data.error || 'onbekend'), 'error');
            updateButtonStates();
            return;
        }

        // Vul dialoog
        dialogExpr.textContent = data.expression || lastProcessed.tekst;
        dialogDir.textContent  = data.output_dir || '~/Desktop/formath_JSON/';

        if (data.duplicates && data.duplicates.length > 0) {
            dialogDupList.innerHTML = data.duplicates
                .map(f => '<li>' + escapeHtml(f) + '</li>').join('');
            dialogDupWarn.hidden = false;
        } else {
            dialogDupWarn.hidden = true;
            dialogDupList.innerHTML = '';
        }

        // Overwrite-keuze zichtbaar maken als er een opgave geselecteerd is
        // én edit aan staat. Default-selectie is 'overwrite'.
        if (selectedOpgaveId && editMode) {
            dialogOverwriteId.textContent = selectedOpgaveId;
            dialogOverwriteChoice.hidden = false;
            // Reset radio naar 'overwrite' zodat de popup altijd consistent start
            const r = document.querySelector('input[name="export-mode"][value="overwrite"]');
            if (r) r.checked = true;
        } else {
            dialogOverwriteChoice.hidden = true;
        }

        openExportDialog();

    } catch (err) {
        setStatus('Verbindingsfout: ' + escapeHtml(err.message), 'error');
        updateButtonStates();
    }
}

function openExportDialog() {
    dialog.hidden = false;
    dialogConfirm.disabled = false;
    dialogConfirm.textContent = 'Exporteren';
    // Focus op bevestigingsknop zodat Enter direct werkt
    setTimeout(() => dialogConfirm.focus(), 50);
}

function closeExportDialog() {
    dialog.hidden = true;
    updateButtonStates();
}

async function confirmExport() {
    if (!lastProcessed) { closeExportDialog(); return; }

    dialogConfirm.disabled = true;
    dialogConfirm.textContent = 'Bezig…';

    // Lees de export-keuze als die zichtbaar was
    let overwriteId = null;
    if (!dialogOverwriteChoice.hidden && selectedOpgaveId) {
        const mode = (document.querySelector('input[name="export-mode"]:checked') || {}).value;
        if (mode === 'overwrite') overwriteId = selectedOpgaveId;
    }

    try {
        const resp = await fetch('/api/export_json', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                latex:  lastProcessed.latex,
                mathml: '',
                randvoorwaarden:    inspectorState.randvoorwaarden,
                mathblock_klasses:  inspectorState.klasses,
                soort_opgave:       currentSoortOpgave,
                productie:          currentProductie,
                opdracht:           currentOpdracht,
                // Sub-ronde D: nieuwe metadata-velden
                onderwijstype:      currentOnderwijstype,
                onderwijsniveau:    currentOnderwijsniveau,
                notitie:            currentNotitie,
                classificatie:      getClassificatieForExport(),
                overwrite_id:       overwriteId,
            })
        });
        const data = await resp.json();

        closeExportDialog();

        if (data.success) {
            const action = overwriteId ? 'bijgewerkt' : 'opgeslagen';
            setStatus(
                'JSON ' + action + ': <code class="mono">' +
                escapeHtml(data.filename) + '</code>',
                'success'
            );
            // Integriteit-waarschuwingen (niet-blokkerend) tonen in een
            // status-bericht eronder. Deze dingen zijn niet kritiek maar
            // de gebruiker moet ze wel zien.
            if (Array.isArray(data.integrity_warnings) && data.integrity_warnings.length > 0) {
                console.warn('[INTEGRITEIT] Waarschuwingen:', data.integrity_warnings);
                // Toon een korte samenvatting bovenaan
                setTimeout(() => {
                    const msg = 'Let op: integriteits-waarschuwing — ' +
                                escapeHtml(data.integrity_warnings[0]) +
                                (data.integrity_warnings.length > 1
                                    ? ` (en ${data.integrity_warnings.length - 1} meer; zie console)`
                                    : '');
                    setStatus(msg, 'warning');
                }, 1500);  // even wachten zodat de "opgeslagen"-status zichtbaar blijft
            }

            // Bepaal het ID dat we straks willen selecteren
            // - bij overwrite: het bestaande ID
            // - bij nieuw: ID afgeleid uit de server-response (filename zonder .json)
            let targetId = overwriteId;
            if (!targetId && data.filename) {
                targetId = data.filename.replace(/\.json$/i, '');
            }

            // Edit lock op de expressie weer aan, maar de Didactiek &
            // Classificatie-sectie moet juist bewerkbaar BLIJVEN zodat de
            // auteur direct na opslaan de metadata kan invullen/aanpassen.
            editMode = false;
            btnEdit.textContent = 'Edit toestaan';
            applyEditLock();
            // Classificatie en Randvoorwaarden expliciet ontgrendelen
            // (overschrijft de lock van applyEditLock, die alles op slot zet)
            applyClassificatieLock(false);
            applyRandvoorwaardenLock(false);

            // Expressie is nu opgeslagen — niet meer dirty
            hasUnparsedChanges = false;
            justSaved = true;
            editSessionTouched = true;

            // Eerst de lijst herladen, dan de opgave selecteren zodat hints
            // en feedback meteen zichtbaar zijn. De Didactiek & Classificatie-
            // sectie blijft bewerkbaar zodat de auteur direct metadata kan
            // invullen of aanpassen.
            await loadOpgavenLijst();
            if (targetId) {
                await selectOpgave(targetId, { unlockClassificatieAfter: true });
            } else {
                deselectOpgave();
            }
        } else if (Array.isArray(data.integrity_errors) && data.integrity_errors.length > 0) {
            // Server heeft een integriteitscheck-fout gedetecteerd. Toon
            // de fouten (en evt. waarschuwingen) in een dialog.
            showIntegrityDialog(data.integrity_errors, data.integrity_warnings || []);
        } else if (data.error_detail) {
            renderError(data);
        } else {
            setStatus('Fout: ' + escapeHtml(data.error || 'onbekend'), 'error');
        }
    } catch (err) {
        closeExportDialog();
        setStatus('Verbindingsfout: ' + escapeHtml(err.message), 'error');
    } finally {
        updateButtonStates();
    }
}

/* Sluit dialoog met Escape */
document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (!dialog.hidden) { closeExportDialog(); return; }
    if (!deleteDialog.hidden) { closeDeleteDialog(); return; }
});

/* Klik op overlay buiten dialog sluit 'm */
dialog.addEventListener('click', (e) => {
    if (e.target === dialog) closeExportDialog();
});

/* ─── Inspector ───────────────────────────────────────────────────── */

/* Randvoorwaarde: uitkomst vereenvoudigen (oude element, nu null-safe) */
if (rvSimplify) {
    rvSimplify.addEventListener('change', (e) => {
        inspectorState.randvoorwaarden.vereenvoudig_uitkomst = e.target.checked;
    });
}

/**
 * Oude renderInspectorMathblocks - behouden als null-safe stub zodat
 * bestaande aanroepen niet crashen. Doet nu niets meer; hints-editor
 * neemt de inspector over via renderHintsEditor().
 */
function renderInspectorMathblocks(mathblocks) {
    if (!mbList) return;  // oude element weg
    // Niets te doen; de hints-editor vervangt deze weergave.
}

function resetInspector() {
    const rv = inspectorState.randvoorwaarden;
    rv.vereenvoudig_uitkomst = false;
    rv.antwoord_in_breuken = true;
    rv.antwoord_in_decimalen = false;
    rv.decimalen_afronden = 2;
    rv.pi_decimalen = 2;
    rv.uitkomst_als_gemengd_getal = true;
    rv.hints_aan = true;
    rv.feedback_aan = true;
    for (const k of Object.keys(inspectorState.klasses)) delete inspectorState.klasses[k];
    if (rvSimplify) rvSimplify.checked = false;
    // Classificatie resetten (sticky defaults blijven bewaard)
    resetClassificatie();
    // Ook de hints-editor resetten
    resetHintsEditor();
}

/* ─── Classificatie-sectie ─────────────────────────────────────────
 * UI ↔ inspectorState.classificatie. Volgt het patroon van rvSimplify:
 * - DOM-events updaten state direct
 * - setClassificatieToUI() vult UI vanuit state (bij load/reset)
 * - getClassificatieFromUI() bouwt het exportblok op uit state
 *
 * Schema-versie 1.0 — zie formath_web/schemas/classificatie_schema.json
 * ────────────────────────────────────────────────────────────────── */

// DOM refs
const clSection      = document.getElementById('cl-section');
const clProgress     = document.getElementById('cl-progress');
const clBody         = document.getElementById('cl-body');
const clChevron      = document.getElementById('cl-chevron');
const clDomein       = document.getElementById('cl-domein');
const clOnderwerp    = document.getElementById('cl-onderwerp');
const clSubonderwerp = document.getElementById('cl-subonderwerp');
const clType         = document.getElementById('cl-type');
const clRtti         = document.getElementById('cl-rtti');
const clDiffBars     = document.getElementById('cl-diff-bars');
const clDiffValue    = document.getElementById('cl-diff-value');
const clLeerjaar     = document.getElementById('cl-leerjaar');
const clStroom       = document.getElementById('cl-stroom');
const clRefniveau    = document.getElementById('cl-refniveau');
const clRefdomein    = document.getElementById('cl-refdomein');
const clExamendomein = document.getElementById('cl-examendomein');
const clTagsContainer = document.getElementById('cl-tags-container');
const clTagInput     = document.getElementById('cl-tag-input');
const clTagList      = document.getElementById('cl-tag-list');
const clOnderwerpList = document.getElementById('cl-onderwerp-list');
const clSubonderwerpList = document.getElementById('cl-subonderwerp-list');
const clBron         = document.getElementById('cl-bron');
const clAuteur       = document.getElementById('cl-auteur');
const clOpmerkingen  = document.getElementById('cl-opmerkingen');
const clAdmSummary   = document.getElementById('cl-adm-summary');
const clAdmFields    = document.getElementById('cl-adm-fields');
const clAdmChevron   = document.getElementById('cl-adm-chevron');

// Lijst van velden voor voortgangsteller (12 totaal)
const CL_FIELDS = [
    'domein', 'onderwerp', 'subonderwerp', 'type', 'niveau_rtti',
    'moeilijkheid', 'leerjaar', 'stroom', 'referentieniveau',
    'referentiedomein', 'examendomein', 'tags',
];

// Autocomplete-cache per veld (in-memory, vult zich uit eerder ingevoerde waarden)
const clAutocomplete = {
    onderwerp:    new Set(),
    subonderwerp: new Set(),
    tag:          new Set(),
};

/* Sectie tonen/verbergen — sectie is altijd zichtbaar zodra een opgave
 * geladen of geparseerd is. */
function showClassificatieSection(visible) {
    if (clSection) clSection.hidden = !visible;
}

/* Toggle hoofdsectie inklappen/uitklappen */
function toggleClSection() {
    if (!clBody) return;
    const collapsed = clBody.hidden;
    clBody.hidden = !collapsed;
    if (clChevron) {
        clChevron.style.transform = collapsed ? '' : 'rotate(-90deg)';
        clChevron.style.transition = 'transform 0.15s';
    }
}

/* Toggle de Hints & Feedback sectie (analoog aan toggleClSection). */
function toggleHintsSection() {
    const body = document.getElementById('hints-section-body');
    const chevron = document.getElementById('hints-section-chevron');
    if (!body) return;
    const collapsed = body.hidden;
    body.hidden = !collapsed;
    if (chevron) {
        chevron.style.transform = collapsed ? '' : 'rotate(-90deg)';
        chevron.style.transition = 'transform 0.15s';
    }
}

/* Toggle administratie-subsectie (oude versie, blijft werken voor compat) */
function toggleClAdm() {
    if (!clAdmFields) return;
    const collapsed = clAdmFields.hidden;
    clAdmFields.hidden = !collapsed;
    if (clAdmChevron) {
        clAdmChevron.style.transform = collapsed ? 'rotate(90deg)' : '';
        clAdmChevron.style.transition = 'transform 0.15s';
    }
}

/* Toggle een classificatie-groep (cl-mb harmonica-blok). Slechts één tegelijk
   open, analoog aan de mathblocks-accordeon. */
function toggleClGroup(groupName) {
    const allMbs = document.querySelectorAll('.cl-mb');
    const target = document.querySelector(`.cl-mb[data-cl-group="${groupName}"]`);
    if (!target) return;
    const wasOpen = target.classList.contains('is-open');
    // Sluit alle andere
    allMbs.forEach(m => m.classList.remove('is-open'));
    // Open de doel als die nog dicht stond
    if (!wasOpen) target.classList.add('is-open');
}

/* Vul statistiek-tellers op basis van een geladen opgave (data.opgave.mathblocks
   en data.opgave.externe_inputs) */
function fillClStats(opgave) {
    function setVal(id, v) {
        const el = document.getElementById(id);
        if (el) el.textContent = (v === undefined || v === null) ? '—' : String(v);
    }

    if (!opgave) {
        // Reset alle tellers
        ['cl-stat-mb-total', 'cl-stat-mb-binary', 'cl-stat-mb-manifold',
         'cl-stat-mb-matroesjka', 'cl-stat-mb-simplify', 'cl-stat-mb-mixed',
         'cl-stat-mb-power', 'cl-stat-mb-root',
         'cl-stat-in-total', 'cl-stat-in-int', 'cl-stat-in-frac',
         'cl-stat-in-dec', 'cl-stat-steps'].forEach(i => setVal(i, '—'));
        const sum = document.getElementById('cl-stats-summary');
        if (sum) sum.textContent = '—';
        return;
    }

    // Tellers mathblocks per type
    const mbs = opgave.mathblocks || [];
    const types = {
        binary: 0, manifold: 0, matroesjka: 0, simplify: 0,
        mixed: 0, power: 0, root: 0,
    };
    for (const mb of mbs) {
        const sym = (mb.operatie && mb.operatie.symbool) || '';
        const desc = (mb.operatie && mb.operatie.beschrijving) || '';
        // Op basis van symbool of beschrijving categoriseren
        if (sym === 'GG' || desc === 'gemengd getal') types.mixed++;
        else if (sym === '÷GGD' || desc === 'vereenvoudigen') types.simplify++;
        else if (sym && sym.startsWith('M+') || sym && sym.startsWith('M×')
                 || desc.includes('manifold')) types.manifold++;
        else if (sym && sym.startsWith('Mtr')) types.matroesjka++;
        else if (desc === 'machtsverheffen' || sym === '^') types.power++;
        else if (desc === 'worteltrekken' || sym === '√') types.root++;
        else types.binary++;
    }
    setVal('cl-stat-mb-total', mbs.length);
    setVal('cl-stat-mb-binary', types.binary);
    setVal('cl-stat-mb-manifold', types.manifold);
    setVal('cl-stat-mb-matroesjka', types.matroesjka);
    setVal('cl-stat-mb-simplify', types.simplify);
    setVal('cl-stat-mb-mixed', types.mixed);
    setVal('cl-stat-mb-power', types.power);
    setVal('cl-stat-mb-root', types.root);

    // Tellers externe inputs
    const ext = opgave.externe_inputs || [];
    const inputs = { int: 0, frac: 0, dec: 0 };
    for (const inp of ext) {
        const t = inp.type || '';
        const v = inp.waarde;
        if (t === 'FRACTION' || (typeof v === 'string' && v.includes('/'))) {
            inputs.frac++;
        } else if (typeof v === 'string' && (v.includes('.') || v.includes(','))) {
            inputs.dec++;
        } else if (typeof v === 'number' && !Number.isInteger(v)) {
            inputs.dec++;
        } else {
            inputs.int++;
        }
    }
    setVal('cl-stat-in-total', ext.length);
    setVal('cl-stat-in-int', inputs.int);
    setVal('cl-stat-in-frac', inputs.frac);
    setVal('cl-stat-in-dec', inputs.dec);

    // Stappen
    const meta = opgave.metadata || {};
    setVal('cl-stat-steps', meta.aantal_steps || 0);

    // Compacte samenvatting in de header
    const sum = document.getElementById('cl-stats-summary');
    if (sum) {
        sum.textContent = `${mbs.length} mb · ${ext.length} in`;
    }
}

/* Pas edit-lock toe op alle classificatie-controls */
function applyClassificatieLock(locked) {
    if (!clSection) return;
    if (locked) {
        clSection.classList.add('cl-locked');
    } else {
        clSection.classList.remove('cl-locked');
    }
}

/* Bouw classificatieblok uit state op voor export.
 * Alleen niet-lege velden meesturen; onderlinge consistentie wordt
 * door het serverschema gevalideerd. */
function getClassificatieForExport() {
    const c = inspectorState.classificatie;
    const out = {};
    for (const k of Object.keys(c)) {
        const v = c[k];
        if (v === null || v === undefined) continue;
        if (Array.isArray(v) && v.length === 0) continue;
        if (typeof v === 'string' && v.trim() === '') continue;
        out[k] = v;
    }
    // Voeg administratiedatum toe als er überhaupt iets is geclassificeerd
    if (Object.keys(out).length > 0) {
        if (!out.geclassificeerd_op) {
            out.geclassificeerd_op = new Date().toISOString().slice(0, 10);
        }
        if (!out.schema_versie) out.schema_versie = '1.0';
    }
    return out;
}

/* Tel ingevulde velden voor de voortgangsindicator */
function clCountFilled() {
    let n = 0;
    const c = inspectorState.classificatie;
    for (const k of CL_FIELDS) {
        const v = c[k];
        if (v === null || v === undefined) continue;
        if (Array.isArray(v) && v.length === 0) continue;
        if (typeof v === 'string' && v.trim() === '') continue;
        n++;
    }
    return n;
}

/* Werk de voortgangsindicator + administratie-samenvatting bij */
function clRenderMeta() {
    if (clProgress) {
        clProgress.textContent = `${clCountFilled()} / ${CL_FIELDS.length}`;
    }
    if (clAdmSummary) {
        const c = inspectorState.classificatie;
        const parts = [];
        if (c.auteur) parts.push(c.auteur);
        if (c.geclassificeerd_op) parts.push(c.geclassificeerd_op);
        if (c.bron) parts.push('bron: ' + c.bron);
        clAdmSummary.textContent = parts.length ? parts.join(' · ') : '—';
    }
}

/* Helpers voor segmented controls (RTTI, ref-niveau) */
function clSegSet(container, value) {
    if (!container) return;
    container.querySelectorAll('.cl-seg-opt').forEach(el => {
        el.classList.toggle('cl-active', el.dataset.value === value);
    });
}
function clSegBind(container, stateKey) {
    if (!container) return;
    container.addEventListener('click', (e) => {
        const opt = e.target.closest('.cl-seg-opt');
        if (!opt) return;
        const newVal = opt.dataset.value;
        // Klik op actieve optie wist hem
        if (inspectorState.classificatie[stateKey] === newVal) {
            inspectorState.classificatie[stateKey] = null;
            clSegSet(container, null);
        } else {
            inspectorState.classificatie[stateKey] = newVal;
            clSegSet(container, newVal);
        }
        clRenderMeta();
    });
}

/* Helpers voor moeilijkheidsbalkjes */
function clDiffSet(value) {
    if (!clDiffBars) return;
    clDiffBars.querySelectorAll('.cl-diff-bar').forEach(el => {
        const n = parseInt(el.dataset.value, 10);
        el.classList.toggle('cl-active', value !== null && value !== undefined && n <= value);
    });
    if (clDiffValue) {
        clDiffValue.textContent = (value === null || value === undefined)
            ? '—' : `${value} / 5`;
    }
}

/* Helpers voor multi-select buttons (leerjaar, stroom) */
function clMultiSet(container, values, btnSelector) {
    if (!container) return;
    const set = new Set((values || []).map(String));
    container.querySelectorAll(btnSelector).forEach(el => {
        el.classList.toggle('cl-active', set.has(el.dataset.value));
    });
}
function clMultiBind(container, btnSelector, stateKey, parseValue) {
    if (!container) return;
    container.addEventListener('click', (e) => {
        const btn = e.target.closest(btnSelector);
        if (!btn) return;
        const raw = btn.dataset.value;
        const v = parseValue ? parseValue(raw) : raw;
        const arr = inspectorState.classificatie[stateKey] || [];
        const idx = arr.indexOf(v);
        if (idx >= 0) {
            arr.splice(idx, 1);
        } else {
            arr.push(v);
            // Voor leerjaar: gesorteerd
            if (stateKey === 'leerjaar') arr.sort((a, b) => a - b);
        }
        inspectorState.classificatie[stateKey] = arr.length ? arr : null;
        // Sticky default bijwerken
        if (stateKey === 'stroom' || stateKey === 'leerjaar') {
            classificatieDefaults[stateKey] = arr.slice();
        }
        clMultiSet(container, arr, btnSelector);
        clRenderMeta();
    });
}

/* Tags-renderer */
function clRenderTags() {
    if (!clTagsContainer) return;
    // Verwijder alle bestaande tag-pillen, behoud het input-veld
    Array.from(clTagsContainer.querySelectorAll('.cl-tag')).forEach(el => el.remove());
    const tags = inspectorState.classificatie.tags || [];
    tags.forEach(tag => {
        const el = document.createElement('span');
        el.className = 'cl-tag';
        el.innerHTML = escapeHtml(tag) +
            ' <span class="cl-tag-x" title="Verwijder">×</span>';
        el.querySelector('.cl-tag-x').addEventListener('click', (e) => {
            e.stopPropagation();
            const arr = inspectorState.classificatie.tags || [];
            const i = arr.indexOf(tag);
            if (i >= 0) arr.splice(i, 1);
            inspectorState.classificatie.tags = arr.length ? arr : null;
            clRenderTags();
            clRenderMeta();
        });
        clTagsContainer.insertBefore(el, clTagInput);
    });
}

/* Datalist-helpers voor autocomplete */
function clRefreshDatalist(listEl, set) {
    if (!listEl) return;
    listEl.innerHTML = '';
    Array.from(set).sort().forEach(v => {
        const o = document.createElement('option');
        o.value = v;
        listEl.appendChild(o);
    });
}

/* Vul UI vanuit state */
function setClassificatieToUI() {
    const c = inspectorState.classificatie;
    if (clDomein)       clDomein.value       = c.domein || '';
    if (clOnderwerp)    clOnderwerp.value    = c.onderwerp || '';
    if (clSubonderwerp) clSubonderwerp.value = c.subonderwerp || '';
    if (clType)         clType.value         = c.type || '';
    if (clRefdomein)    clRefdomein.value    = c.referentiedomein || '';
    if (clExamendomein) clExamendomein.value = c.examendomein || '';
    if (clBron)         clBron.value         = c.bron || '';
    if (clAuteur)       clAuteur.value       = c.auteur || '';
    if (clOpmerkingen)  clOpmerkingen.value  = c.opmerkingen || '';
    clSegSet(clRtti, c.niveau_rtti || null);
    clSegSet(clRefniveau, c.referentieniveau || null);
    clDiffSet(c.moeilijkheid || null);
    clMultiSet(clLeerjaar, c.leerjaar || [], '.cl-year-btn');
    clMultiSet(clStroom, c.stroom || [], '.cl-pill');
    clRenderTags();
    clRenderMeta();
}

/* Initialiseer event-bindings (één keer bij paginalaad) */
function initClassificatieUI() {
    if (!clSection) return;  // sectie niet aanwezig in deze HTML

    // Dropdowns
    if (clDomein) clDomein.addEventListener('change', (e) => {
        inspectorState.classificatie.domein = e.target.value || null;
        clRenderMeta();
    });
    if (clType) clType.addEventListener('change', (e) => {
        inspectorState.classificatie.type = e.target.value || null;
        clRenderMeta();
    });
    if (clRefdomein) clRefdomein.addEventListener('change', (e) => {
        inspectorState.classificatie.referentiedomein = e.target.value || null;
        clRenderMeta();
    });
    if (clExamendomein) clExamendomein.addEventListener('change', (e) => {
        inspectorState.classificatie.examendomein = e.target.value || null;
        clRenderMeta();
    });

    // Vrije velden + autocomplete
    if (clOnderwerp) {
        clOnderwerp.addEventListener('input', (e) => {
            inspectorState.classificatie.onderwerp = e.target.value.trim() || null;
            clRenderMeta();
        });
        clOnderwerp.addEventListener('change', (e) => {
            const v = e.target.value.trim();
            if (v) {
                clAutocomplete.onderwerp.add(v);
                clRefreshDatalist(clOnderwerpList, clAutocomplete.onderwerp);
            }
        });
    }
    if (clSubonderwerp) {
        clSubonderwerp.addEventListener('input', (e) => {
            inspectorState.classificatie.subonderwerp = e.target.value.trim() || null;
            clRenderMeta();
        });
        clSubonderwerp.addEventListener('change', (e) => {
            const v = e.target.value.trim();
            if (v) {
                clAutocomplete.subonderwerp.add(v);
                clRefreshDatalist(clSubonderwerpList, clAutocomplete.subonderwerp);
            }
        });
    }

    // Administratieve tekstvelden
    if (clBron) clBron.addEventListener('input', (e) => {
        const v = e.target.value.trim();
        inspectorState.classificatie.bron = v || null;
        classificatieDefaults.bron = v;
        clRenderMeta();
    });
    if (clAuteur) clAuteur.addEventListener('input', (e) => {
        const v = e.target.value.trim();
        inspectorState.classificatie.auteur = v || null;
        classificatieDefaults.auteur = v;
        clRenderMeta();
    });
    if (clOpmerkingen) clOpmerkingen.addEventListener('input', (e) => {
        inspectorState.classificatie.opmerkingen = e.target.value.trim() || null;
    });

    // Segmented controls
    clSegBind(clRtti, 'niveau_rtti');
    clSegBind(clRefniveau, 'referentieniveau');

    // Difficulty bars (klik op balkje N → moeilijkheid = N; opnieuw klik op
    // huidige waarde → wist het)
    if (clDiffBars) {
        clDiffBars.addEventListener('click', (e) => {
            const bar = e.target.closest('.cl-diff-bar');
            if (!bar) return;
            const v = parseInt(bar.dataset.value, 10);
            if (inspectorState.classificatie.moeilijkheid === v) {
                inspectorState.classificatie.moeilijkheid = null;
            } else {
                inspectorState.classificatie.moeilijkheid = v;
            }
            clDiffSet(inspectorState.classificatie.moeilijkheid);
            clRenderMeta();
        });
    }

    // Multi-selects
    clMultiBind(clLeerjaar, '.cl-year-btn', 'leerjaar', (raw) => parseInt(raw, 10));
    clMultiBind(clStroom, '.cl-pill', 'stroom');

    // Tag-input: Enter of komma voegt tag toe
    if (clTagInput) {
        clTagInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                addTagFromInput();
            } else if (e.key === 'Backspace' && !clTagInput.value) {
                // Backspace op leeg input → laatste tag verwijderen
                const arr = inspectorState.classificatie.tags || [];
                if (arr.length > 0) {
                    arr.pop();
                    inspectorState.classificatie.tags = arr.length ? arr : null;
                    clRenderTags();
                    clRenderMeta();
                }
            }
        });
        clTagInput.addEventListener('blur', () => {
            if (clTagInput.value.trim()) addTagFromInput();
        });
    }

    function addTagFromInput() {
        const raw = clTagInput.value.trim().toLowerCase().replace(/\s+/g, '_');
        if (!raw) return;
        if (!/^[a-z0-9_]+$/.test(raw)) {
            // Stilzwijgend afkappen: alleen geldige karakters houden
            const cleaned = raw.replace(/[^a-z0-9_]/g, '');
            if (!cleaned) {
                clTagInput.value = '';
                return;
            }
            clTagInput.value = '';
            const arr = inspectorState.classificatie.tags || [];
            if (!arr.includes(cleaned)) arr.push(cleaned);
            inspectorState.classificatie.tags = arr;
            clAutocomplete.tag.add(cleaned);
            clRefreshDatalist(clTagList, clAutocomplete.tag);
            clRenderTags();
            clRenderMeta();
            return;
        }
        const arr = inspectorState.classificatie.tags || [];
        if (!arr.includes(raw)) arr.push(raw);
        inspectorState.classificatie.tags = arr;
        clAutocomplete.tag.add(raw);
        clRefreshDatalist(clTagList, clAutocomplete.tag);
        clTagInput.value = '';
        clRenderTags();
        clRenderMeta();
    }

    clRenderMeta();
}

/* Vul classificatieblok vanuit een geladen opgave-JSON */
function loadClassificatieFromJSON(opgaveJson) {
    const c = opgaveJson?.metadata?.classificatie || {};
    // Volledig vervangen — alle velden komen uit de geladen opgave
    inspectorState.classificatie = JSON.parse(JSON.stringify(c));
    // Vul autocomplete-cache uit deze opgave (zodat vrije velden gesuggereerd worden)
    if (c.onderwerp) clAutocomplete.onderwerp.add(c.onderwerp);
    if (c.subonderwerp) clAutocomplete.subonderwerp.add(c.subonderwerp);
    if (Array.isArray(c.tags)) c.tags.forEach(t => clAutocomplete.tag.add(t));
    clRefreshDatalist(clOnderwerpList, clAutocomplete.onderwerp);
    clRefreshDatalist(clSubonderwerpList, clAutocomplete.subonderwerp);
    clRefreshDatalist(clTagList, clAutocomplete.tag);
    setClassificatieToUI();
}

/* Reset classificatie naar lege staat, maar herstel sticky defaults
 * zodat batch-invoer minder klikken vraagt. */
function resetClassificatie() {
    inspectorState.classificatie = {};
    if (classificatieDefaults.stroom.length) {
        inspectorState.classificatie.stroom = classificatieDefaults.stroom.slice();
    }
    if (classificatieDefaults.leerjaar.length) {
        inspectorState.classificatie.leerjaar = classificatieDefaults.leerjaar.slice();
    }
    if (classificatieDefaults.bron) {
        inspectorState.classificatie.bron = classificatieDefaults.bron;
    }
    if (classificatieDefaults.auteur) {
        inspectorState.classificatie.auteur = classificatieDefaults.auteur;
    }
    setClassificatieToUI();
}

// Initialiseer zodra DOM klaar is
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initClassificatieUI);
} else {
    initClassificatieUI();
}

/* ─── Hints-editor ────────────────────────────────────────────────── */

/**
 * Vul de hints-editor op basis van de mathblocks uit een geladen opgave-JSON.
 * Verwacht data.opgave.mathblocks met elk een `hints` veld.
 */
function renderHintsEditor(mathblocks) {
    if (!hintsAccordion) return;

    // Reset
    hintsState.mathblocks = [];
    hintsState.original = {};
    hintsState.edits = {};
    hintsState.openId = null;

    if (!Array.isArray(mathblocks) || mathblocks.length === 0) {
        hintsAccordion.innerHTML = '';
        if (hintsPlaceholder) hintsPlaceholder.hidden = false;
        if (hintsSavebar) hintsSavebar.hidden = true;
        if (hintsSubtitle) hintsSubtitle.textContent = 'per opgave';
        const mbCountEl = document.getElementById('hints-mb-count');
        if (mbCountEl) mbCountEl.textContent = '— mathblocks';
        return;
    }

    if (hintsPlaceholder) hintsPlaceholder.hidden = true;

    // Metadata verzamelen + initialiseren
    for (const mb of mathblocks) {
        const meta = {
            id: mb.id,
            step: mb.step,
            symbool: (mb.operatie && mb.operatie.symbool) || '?',
            beschrijving: (mb.operatie && mb.operatie.beschrijving) || '',
        };
        hintsState.mathblocks.push(meta);

        // Clone originele hints (zodat edits niet de bron muteren)
        const original = _cloneHints(mb.hints || {});
        hintsState.original[mb.id] = original;
        hintsState.edits[mb.id] = _cloneHints(original);
    }

    _renderHintsAccordion();
    _updateHintsSavebar();
    const labelText = mathblocks.length + ' mathblock' +
        (mathblocks.length === 1 ? '' : 's');
    if (hintsSubtitle) hintsSubtitle.textContent = 'per opgave';
    const mbCountEl = document.getElementById('hints-mb-count');
    if (mbCountEl) mbCountEl.textContent = labelText;
}

function resetHintsEditor() {
    hintsState.mathblocks = [];
    hintsState.original = {};
    hintsState.edits = {};
    hintsState.openId = null;
    if (hintsAccordion) hintsAccordion.innerHTML = '';
    if (hintsPlaceholder) hintsPlaceholder.hidden = false;
    if (hintsSavebar) hintsSavebar.hidden = true;
    if (hintsSubtitle) hintsSubtitle.textContent = 'per opgave';
    const mbCountEl = document.getElementById('hints-mb-count');
    if (mbCountEl) mbCountEl.textContent = '— mathblocks';
}

function _cloneHints(h) {
    // Deep copy, maar alleen velden die we bewerken (structureel / feedback / didactisch)
    const out = {
        structureel: {},
        feedback:    {},
        didactisch:  {},
    };
    const s = h.structureel || {};
    out.structureel.wat       = s.wat || '';
    out.structureel.hoe       = s.hoe || '';
    out.structureel.let_op    = s.let_op || '';
    if ('voorbeeld' in s) out.structureel.voorbeeld = s.voorbeeld || '';
    const f = h.feedback || {};
    out.feedback.bij_correct       = f.bij_correct || '';
    out.feedback.bij_fout_algemeen = f.bij_fout_algemeen || '';
    const d = h.didactisch || {};
    out.didactisch.didactische_uitleg  = d.didactische_uitleg || '';
    out.didactisch.voorbeeld           = d.voorbeeld || '';
    out.didactisch.verwijzing_lesstof  = d.verwijzing_lesstof || '';
    return out;
}

function _renderHintsAccordion() {
    if (!hintsAccordion) return;
    hintsAccordion.innerHTML = '';

    for (const meta of hintsState.mathblocks) {
        const mbEl = document.createElement('div');
        mbEl.className = 'hints-mb';
        mbEl.setAttribute('data-mb-id', meta.id);
        if (meta.id === hintsState.openId) mbEl.classList.add('is-open');
        if (_isMbDirty(meta.id)) mbEl.classList.add('is-dirty');

        // Header: ID + beschrijving + dirty-dot + chevron
        const header = document.createElement('div');
        header.className = 'hints-mb-header';
        header.innerHTML = `
            <svg class="hints-mb-chevron" viewBox="0 0 12 12" fill="none"
                 stroke="currentColor" stroke-width="2" stroke-linecap="round"
                 stroke-linejoin="round" aria-hidden="true">
                <polyline points="4 2 8 6 4 10"/>
            </svg>
            <span class="hints-mb-id">${escapeHtml(meta.id)}</span>
            <span class="hints-mb-label">${escapeHtml(meta.beschrijving || meta.symbool)}</span>
            <span class="hints-mb-dirty-dot" title="Gewijzigd"></span>
        `;
        header.addEventListener('click', () => _toggleHintsMb(meta.id));

        const body = document.createElement('div');
        body.className = 'hints-mb-body';
        body.innerHTML = _renderHintsBody(meta.id);

        mbEl.appendChild(header);
        mbEl.appendChild(body);
        hintsAccordion.appendChild(mbEl);

        // Event listeners op de textareas
        body.querySelectorAll('textarea[data-field]').forEach(ta => {
            const path = ta.getAttribute('data-field').split('.');
            ta.addEventListener('input', () => {
                _setEditValue(meta.id, path, ta.value);
                _updateDirtyIndicators(meta.id);
            });
        });
    }
}

function _renderHintsBody(mbId) {
    const edits = hintsState.edits[mbId] || {};
    const s = edits.structureel || {};
    const f = edits.feedback || {};
    const d = edits.didactisch || {};

    const fld = (label, path, value, rows) => {
        const isEmpty = !value;
        return `
            <div class="hints-field">
                <label class="hints-field-label">${escapeHtml(label)}</label>
                <textarea class="hints-field-input mono ${isEmpty ? 'is-empty' : ''}"
                          data-field="${path}"
                          rows="${rows || 2}">${escapeHtml(value || '')}</textarea>
            </div>
        `;
    };

    let html = '';

    // Type 1 — Structureel
    html += '<div class="hints-group">';
    html += '<div class="hints-group-title">Structureel (Type 1)</div>';
    html += fld('Wat',    'structureel.wat',    s.wat, 2);
    html += fld('Hoe',    'structureel.hoe',    s.hoe, 3);
    html += fld('Let op', 'structureel.let_op', s.let_op, 2);
    if ('voorbeeld' in s) {
        html += fld('Voorbeeld', 'structureel.voorbeeld', s.voorbeeld, 2);
    }
    html += '</div>';

    // Feedback (Type 1 / standaard)
    html += '<div class="hints-group">';
    html += '<div class="hints-group-title">Feedback</div>';
    html += fld('Bij correct',       'feedback.bij_correct',       f.bij_correct, 2);
    html += fld('Bij fout (algemeen)', 'feedback.bij_fout_algemeen', f.bij_fout_algemeen, 2);
    html += '</div>';

    // Type 3 — Didactisch
    html += '<div class="hints-group">';
    html += '<div class="hints-group-title">Didactisch (Type 3)</div>';
    html += fld('Didactische uitleg',  'didactisch.didactische_uitleg',  d.didactische_uitleg, 3);
    html += fld('Voorbeeld',           'didactisch.voorbeeld',           d.voorbeeld, 2);
    html += fld('Verwijzing lesstof',  'didactisch.verwijzing_lesstof',  d.verwijzing_lesstof, 2);
    html += '</div>';

    return html;
}

function _toggleHintsMb(mbId) {
    // Accordeon: slechts één tegelijk open
    if (hintsState.openId === mbId) {
        hintsState.openId = null;
    } else {
        hintsState.openId = mbId;
    }
    // Alleen de open-state bijwerken zonder hele accordeon te rebuilden
    // (anders verliezen textareas focus/caret-positie)
    hintsAccordion.querySelectorAll('.hints-mb').forEach(el => {
        const id = el.getAttribute('data-mb-id');
        el.classList.toggle('is-open', id === hintsState.openId);
    });
}

function _setEditValue(mbId, path, value) {
    // path is ['structureel', 'wat'] of ['feedback', 'bij_correct'] enz.
    const obj = hintsState.edits[mbId];
    if (!obj) return;
    const [grp, field] = path;
    if (!obj[grp]) obj[grp] = {};
    obj[grp][field] = value;
}

function _isMbDirty(mbId) {
    const o = hintsState.original[mbId];
    const e = hintsState.edits[mbId];
    if (!o || !e) return false;
    return JSON.stringify(o) !== JSON.stringify(e);
}

function _dirtyMbIds() {
    return hintsState.mathblocks
        .map(m => m.id)
        .filter(_isMbDirty);
}

function _updateDirtyIndicators(changedMbId) {
    // Zet dirty-dot op deze MB
    const el = hintsAccordion.querySelector(`[data-mb-id="${changedMbId}"]`);
    if (el) el.classList.toggle('is-dirty', _isMbDirty(changedMbId));
    _updateHintsSavebar();
}

function _updateHintsSavebar() {
    if (!hintsSavebar) return;
    const dirty = _dirtyMbIds();
    if (dirty.length === 0) {
        hintsSavebar.hidden = true;
        if (btnHintsSave) btnHintsSave.disabled = true;
        return;
    }
    hintsSavebar.hidden = false;
    if (btnHintsSave) btnHintsSave.disabled = false;
    if (hintsDirtyCount) {
        hintsDirtyCount.textContent = dirty.length + ' mathblock' +
            (dirty.length === 1 ? '' : 's') + ' gewijzigd';
    }
}

/**
 * Bewaart alle wijzigingen in de hints van de momenteel geladen opgave.
 * Overschrijft het bestaande JSON-bestand via /api/export_json met overwrite_id.
 */
async function saveHintsEdits() {
    if (!selectedOpgaveId || !selectedOpgaveJson) {
        setStatus('Geen opgave geladen om hints op te slaan.', 'error');
        return;
    }

    // Werk de hints in de in-memory JSON bij
    const mbs = selectedOpgaveJson.mathblocks || [];
    for (const mb of mbs) {
        const edits = hintsState.edits[mb.id];
        if (!edits) continue;
        mb.hints = _cloneHints(edits);
    }

    // Stuur de bijgewerkte opgave naar de server.
    // Omdat we niet alleen hints-wijzigingen maar ook evt. andere velden
    // hebben, schrijven we de hele JSON opnieuw via een nieuw endpoint.
    btnHintsSave.disabled = true;
    btnHintsSave.textContent = 'Bezig…';
    try {
        const r = await fetch('/api/save_hints', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: selectedOpgaveId,
                mathblocks: selectedOpgaveJson.mathblocks,
            }),
        });
        const data = await r.json();
        if (data.success) {
            setStatus('Hints opgeslagen voor <code class="mono">' +
                escapeHtml(selectedOpgaveId) + '</code>', 'success');
            // Original updaten naar huidige edits (niet meer dirty)
            for (const id of Object.keys(hintsState.edits)) {
                hintsState.original[id] = _cloneHints(hintsState.edits[id]);
            }
            // Alle dirty-dots weghalen
            hintsAccordion.querySelectorAll('.hints-mb').forEach(el => {
                el.classList.remove('is-dirty');
            });
            _updateHintsSavebar();
        } else {
            setStatus('Fout bij opslaan: ' + escapeHtml(data.error || 'onbekend'), 'error');
        }
    } catch (err) {
        setStatus('Verbindingsfout: ' + escapeHtml(err.message), 'error');
    } finally {
        btnHintsSave.disabled = false;
        btnHintsSave.textContent = 'Opslaan';
    }
}

function discardHintsEdits() {
    // Zet alle edits terug naar original
    for (const id of Object.keys(hintsState.original)) {
        hintsState.edits[id] = _cloneHints(hintsState.original[id]);
    }
    _renderHintsAccordion();
    _updateHintsSavebar();
    setStatus('Wijzigingen ongedaan gemaakt.', 'info');
}

/**
 * Opdracht-dropdown: "Reken uit" of "Vereenvoudig". De keuze
 * belandt in metadata.opdracht bij export.
 */
function onOpdrachtChange(value) {
    currentOpdracht = value || OPDRACHT_DEFAULT;
}

/**
 * Soort opgave: 'rekenen_getallen', 'rekenen_letters', 'simpele_vergelijkingen'.
 * Belandt in metadata.soort_opgave bij export en bepaalt straks (server-side)
 * welke pipeline-tak gebruikt wordt.
 *
 * TODO: 'Soort opgave' beïnvloedt later de inhoud van 'Opdracht voor de leerling'
 * (bijv. 'Reken uit' is niet zinvol bij vergelijkingen). Voor nu nog geen logica.
 */
function onSoortOpgaveChange(value) {
    currentSoortOpgave = value || SOORT_OPGAVE_DEFAULT;
}

/**
 * Productie: 'enkelvoudig' (één opgave) of 'sjabloon' (template voor meerdere
 * varianten). Belandt in metadata.productie bij export.
 */
function onProductieChange(value) {
    currentProductie = value || PRODUCTIE_DEFAULT;
}

/**
 * Klap de inspector in of uit. De voorkeur leeft alleen in-memory
 * (reset bij page reload). De grid-template past automatisch aan via
 * de class .inspector-collapsed op .app-main.
 */
function toggleInspector() {
    const isCollapsed = appMain.classList.toggle('inspector-collapsed');
    inspectorAside.hidden  = isCollapsed;
    inspectorRail.hidden   = !isCollapsed;
    btnCollapse.setAttribute('aria-expanded', String(!isCollapsed));
    btnCollapse.setAttribute(
        'aria-label',
        isCollapsed ? 'Inspector openen' : 'Inspector inklappen'
    );
    btnCollapse.setAttribute(
        'title',
        isCollapsed ? 'Inspector openen' : 'Inspector inklappen'
    );

    // Focus-management: geef focus aan de zichtbare knop zodat
    // keyboard-gebruikers direct verder kunnen.
    requestAnimationFrame(() => {
        (isCollapsed ? inspectorRail : btnCollapse).focus();
    });
}

/* ─── Opgavenbeheer (linker inspector) ────────────────────────────── */

function toggleOpgaveLijst() {
    const isCollapsed = appMain.classList.toggle('opgaven-collapsed');
    olAside.hidden = isCollapsed;
    olRail.hidden  = !isCollapsed;
    btnOlCollapse.setAttribute('aria-expanded', String(!isCollapsed));
    btnOlCollapse.setAttribute('aria-label',
        isCollapsed ? 'Opgaven openen' : 'Opgaven inklappen');
    btnOlCollapse.setAttribute('title',
        isCollapsed ? 'Opgaven openen' : 'Opgaven inklappen');
    requestAnimationFrame(() => {
        (isCollapsed ? olRail : btnOlCollapse).focus();
    });
}

/**
 * Haal de opgave-lijst op van de server en render hem. Wordt aangeroepen
 * bij start, na elke export en na elke delete.
 */
// State voor de folder-boom in de linkerkolom.
// openFolders is een Set met namen van geopende folders (in deze sub-ronde
// alleen één niveau diep; later wordt dit een Set van paden).
// selectedFolder is de naam van de visueel geselecteerde folder (of null).
const openFolders = new Set();
let selectedFolder = null;

async function loadOpgavenLijst() {
    try {
        const r = await fetch('/api/list_opgaven');
        const data = await r.json();
        // Update de placeholder-directory met de actuele waarde
        const dirSpan = document.getElementById('ol-placeholder-dir');
        if (dirSpan && data.output_dir) {
            dirSpan.textContent = data.output_dir;
        }
        if (!data.success) {
            olPlaceholder.textContent = 'Fout bij laden van opgaven.';
            olPlaceholder.hidden = false;
            olList.hidden = true;
            return;
        }
        renderOpgavenLijst(data.opgaven || [], data.folders || []);
    } catch (err) {
        olPlaceholder.textContent = 'Verbindingsfout: ' + err.message;
        olPlaceholder.hidden = false;
        olList.hidden = true;
    }
}

function renderOpgavenLijst(opgaven, folders) {
    // Aantal opgaven blijft de tekst bovenaan
    olCount.textContent = opgaven.length === 0
        ? 'geen opgaven'
        : (opgaven.length === 1 ? '1 opgave' : `${opgaven.length} opgaven`);

    // Lege root (geen folders én geen opgaven): toon placeholder
    if (folders.length === 0 && opgaven.length === 0) {
        const dirSpan = document.getElementById('ol-placeholder-dir');
        const dirText = dirSpan ? dirSpan.textContent : '';
        olPlaceholder.innerHTML = 'Geen opgaven gevonden in <code class="mono" id="ol-placeholder-dir">' +
            escapeHtml(dirText) + '</code>';
        olPlaceholder.hidden = false;
        olList.hidden = true;
        olList.innerHTML = '';
        return;
    }

    olPlaceholder.hidden = true;
    olList.hidden = false;
    olList.innerHTML = '';

    // Groepeer opgaven per folder. Het 'folder'-veld is een relatief pad
    // ('' voor root, 'Trial' voor Trial-folder, etc.).
    const opgavenByFolder = new Map();
    for (const o of opgaven) {
        const key = o.folder || '';
        if (!opgavenByFolder.has(key)) opgavenByFolder.set(key, []);
        opgavenByFolder.get(key).push(o);
    }

    // Render elke folder. Folders komen uit de server-response — ook lege.
    // Sorteer alfabetisch (case-insensitive).
    const sortedFolders = [...folders].sort((a, b) =>
        a.name.toLowerCase().localeCompare(b.name.toLowerCase()));

    for (const folder of sortedFolders) {
        const folderEl = renderFolder(folder, opgavenByFolder.get(folder.name) || []);
        olList.appendChild(folderEl);
    }

    // Opgaven die direct in de root staan (geen sub-folder) krijgen
    // een speciale pseudo-folder bovenaan. Vooral voor backward-compat:
    // pre-migratie opgaven die nog niet in een sub-folder zitten.
    const rootOpgaven = opgavenByFolder.get('') || [];
    if (rootOpgaven.length > 0) {
        const rootEl = renderFolder(
            {name: '(root)', opgave_count: rootOpgaven.length, isRoot: true},
            rootOpgaven
        );
        olList.insertBefore(rootEl, olList.firstChild);
    }
}

/**
 * Bouw één folder-element met driehoekje, naam, count, en (indien open)
 * de bijbehorende opgaven of een lege-folder-boodschap.
 */
function renderFolder(folder, opgaven) {
    const wrap = document.createElement('li');
    wrap.className = 'ol-folder-wrap';
    wrap.setAttribute('data-folder', folder.name);

    // Header-rij: driehoekje + naam + count
    const header = document.createElement('div');
    header.className = 'ol-folder';
    if (openFolders.has(folder.name)) header.classList.add('is-open');
    if (selectedFolder === folder.name) header.classList.add('is-selected');

    const arrow = document.createElement('span');
    arrow.className = 'ol-folder-arrow';
    arrow.textContent = '▶';
    arrow.setAttribute('aria-label', 'Open/sluit folder');

    const name = document.createElement('span');
    name.className = 'ol-folder-name';
    name.textContent = folder.name;

    const count = document.createElement('span');
    count.className = 'ol-folder-count';
    count.textContent = String(folder.opgave_count);

    header.appendChild(arrow);
    header.appendChild(name);
    header.appendChild(count);
    wrap.appendChild(header);

    // Klik op driehoekje (of links daarvan): klap open/dicht
    arrow.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleFolderOpen(folder.name);
    });

    // Klik op naam: selecteer folder (visueel)
    name.addEventListener('click', (e) => {
        e.stopPropagation();
        selectFolder(folder.name);
    });

    // Klik op de count (of elders in de header): doe niets specifieks
    // — alleen driehoekje en naam zijn actief, zoals afgesproken.

    // Inhoud-container (alleen als folder open is)
    if (openFolders.has(folder.name)) {
        const contents = document.createElement('div');
        contents.className = 'ol-folder-contents';

        if (opgaven.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'ol-folder-empty';
            empty.textContent = 'Folder is leeg. Maak een eerste opgave door op Nieuw te klikken.';
            contents.appendChild(empty);
        } else {
            for (let i = 0; i < opgaven.length; i++) {
                const o = opgaven[i];
                const li = document.createElement('div');
                li.className = 'ol-item';
                if (o.corrupt) li.classList.add('is-corrupt');
                const isSelected = (o.id === selectedOpgaveId);
                if (isSelected) li.classList.add('is-selected');
                li.setAttribute('role', 'option');
                li.setAttribute('aria-selected', String(isSelected));
                li.setAttribute('tabindex', '0');
                li.setAttribute('data-id', o.id);
                li.setAttribute('data-idx', String(i));
                li.textContent = o.id;
                li.addEventListener('click', () => {
                    li.focus();
                    justSaved = false;
                    selectOpgave(o.id);
                });
                // Rechtsklik → contextmenu (Verwijderen → Prullenbak).
                // Werkt onafhankelijk van selectie; menu komt op voor
                // de aangeklikte opgave (Finder-stijl).
                li.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    showOpgaveContextMenu(e.clientX, e.clientY, {
                        id: o.id,
                        folder: o.folder || ''
                    });
                });
                contents.appendChild(li);
            }
        }

        wrap.appendChild(contents);
    }

    return wrap;
}

/**
 * Klap een folder open/dicht. Werkt onafhankelijk van andere folders —
 * meerdere folders kunnen tegelijk open zijn.
 */
function toggleFolderOpen(name) {
    if (openFolders.has(name)) {
        openFolders.delete(name);
    } else {
        openFolders.add(name);
    }
    loadOpgavenLijst();  // herrender — async, geen probleem
}

/**
 * Selecteer een folder visueel. Slechts één folder tegelijk geselecteerd.
 * In sub-ronde B heeft selectie alleen visuele betekenis; functionele
 * gevolgen komen later (default-doelmap voor Nieuw etc.).
 */
function selectFolder(name) {
    selectedFolder = (selectedFolder === name) ? null : name;
    // Alleen de header-classes hoeven bijgewerkt — geen volledige herrender
    document.querySelectorAll('.ol-folder').forEach(el => {
        const wrap = el.closest('.ol-folder-wrap');
        if (!wrap) return;
        const folderName = wrap.getAttribute('data-folder');
        el.classList.toggle('is-selected', folderName === selectedFolder);
    });
}

/**
 * Keyboard-navigatie in de opgavenlijst (event listener op de UL).
 *   ↓ / ↑       — volgende / vorige opgave (focus + direct selecteren)
 *   Home / End  — eerste / laatste opgave (direct selecteren)
 *   Enter/Space — expliciet selecteren (wanneer focus op een LI ligt)
 */
function onOpgavenListKey(e) {
    const items = Array.from(olList.querySelectorAll('.ol-item'));
    if (items.length === 0) return;

    // Vind welke LI nu de 'huidige' is: de gefocuste, of anders de geselecteerde
    let currentIdx = items.findIndex(it => it === document.activeElement);
    if (currentIdx === -1) {
        currentIdx = items.findIndex(it => it.getAttribute('data-id') === selectedOpgaveId);
    }
    // Nog niets: begin bovenaan
    if (currentIdx === -1) currentIdx = 0;

    let nextIdx = currentIdx;
    switch (e.key) {
        case 'ArrowDown':
            nextIdx = Math.min(items.length - 1, currentIdx + 1);
            break;
        case 'ArrowUp':
            nextIdx = Math.max(0, currentIdx - 1);
            break;
        case 'Home':
            nextIdx = 0;
            break;
        case 'End':
            nextIdx = items.length - 1;
            break;
        case 'Enter':
        case ' ':
            if (document.activeElement && document.activeElement.classList.contains('ol-item')) {
                e.preventDefault();
                justSaved = false;
                selectOpgave(document.activeElement.getAttribute('data-id'));
            }
            return;
        default:
            return;
    }
    e.preventDefault();
    const target = items[nextIdx];
    if (!target) return;
    target.focus();
    target.scrollIntoView({block: 'nearest'});
    // Auto-select: verplaatsen in de lijst laadt meteen de opgave.
    const id = target.getAttribute('data-id');
    if (id && id !== selectedOpgaveId) {
        justSaved = false;
        selectOpgave(id);
    }
}

// Oude per-li handler blijft behouden voor compat, maar we verleggen naar UL-level
function onOpgaveKey(e) {
    return onOpgavenListKey(e);
}

/**
 * Een opgave uit de lijst selecteren: laad de JSON + SVG, vul de
 * math-field, zet math-field op slot, zet edit-mode uit, toon Edit- en
 * Delete-knoppen, rechter inspector naar read-only modus.
 */
async function selectOpgave(id, options = {}) {
    const { unlockClassificatieAfter = false } = options;
    try {
        const r = await fetch('/api/load_opgave?id=' + encodeURIComponent(id));
        const data = await r.json();
        if (!data.success) {
            setStatus('Kon opgave niet laden: ' + escapeHtml(data.error || id), 'error');
            return;
        }
        selectedOpgaveId = id;
        selectedOpgaveJson = data.opgave;
        selectedOpgaveSvg  = data.svg || '';
        editMode = false;

        // Vul math-field en zet op slot.
        // Voorkeur: latex_display (correcte LaTeX-notatie van MathLive,
        // zoals \frac{1}{2} of geneste \frac{\frac{1}{2}}{...}).
        // Fallback: tekst (ASCII-math zoals "1/2+1/4") voor oude opgaven die
        // alleen tekst hebben opgeslagen. Daarna nog 'latex' als oude veldnaam.
        const expr = data.opgave?.metadata?.expressie || {};
        const latex = expr.latex_display || expr.latex || expr.tekst || '';
        setMode('math');        // forceer MathLive-modus

        // Probeer meerdere strategieën om de math-field te vullen
        function setMathFieldValue(val) {
            if (!mathField) return false;
            if (typeof mathField.setValue === 'function') {
                try { mathField.setValue(val); return true; }
                catch (e) {}
            }
            try { mathField.value = val; return true; }
            catch (e) {}
            return false;
        }
        setMathFieldValue(latex);
        // En nog eens nadat MathLive's custom element zeker upgraded is
        requestAnimationFrame(() => setMathFieldValue(latex));

        applyEditLock();

        // Rechter inspector uit JSON vullen (read-only totdat edit aan)
        const rv = data.opgave?.metadata?.randvoorwaarden || {};
        // Defaults gebruiken voor velden die niet aanwezig zijn (oude opgaven)
        const ist = inspectorState.randvoorwaarden;
        ist.vereenvoudig_uitkomst    = !!rv.vereenvoudig_uitkomst;
        ist.antwoord_in_breuken      = rv.antwoord_in_breuken !== undefined ? !!rv.antwoord_in_breuken : true;
        ist.antwoord_in_decimalen    = !!rv.antwoord_in_decimalen;
        ist.decimalen_afronden       = (typeof rv.decimalen_afronden === 'number') ? rv.decimalen_afronden : 2;
        ist.pi_decimalen             = (typeof rv.pi_decimalen === 'number') ? rv.pi_decimalen : 2;
        ist.uitkomst_als_gemengd_getal = rv.uitkomst_als_gemengd_getal !== undefined ? !!rv.uitkomst_als_gemengd_getal : true;
        ist.hints_aan                = rv.hints_aan !== undefined ? !!rv.hints_aan : true;
        ist.feedback_aan             = rv.feedback_aan !== undefined ? !!rv.feedback_aan : true;
        if (rvSimplify) rvSimplify.checked = !!rv.vereenvoudig_uitkomst;

        // Opdracht ook uit metadata laden (default als ontbreekt)
        const opdr = data.opgave?.metadata?.opdracht || OPDRACHT_DEFAULT;
        currentOpdracht = opdr;
        if (opdrachtSelect) opdrachtSelect.value = opdr;

        // Soort opgave en productie ook laden (defaults als ontbreken — opgaven
        // van vóór deze velden hebben ze nog niet)
        const soort = data.opgave?.metadata?.soort_opgave || SOORT_OPGAVE_DEFAULT;
        const prod  = data.opgave?.metadata?.productie    || PRODUCTIE_DEFAULT;
        currentSoortOpgave = soort;
        currentProductie   = prod;
        if (soortOpgaveSelect) soortOpgaveSelect.value = soort;
        if (productieSelect)   productieSelect.value   = prod;

        // Onderwijstype, onderwijsniveau, notitie (sub-ronde D).
        // Defaults als veld ontbreekt — pre-D opgaven hebben deze nog niet.
        currentOnderwijstype   = data.opgave?.metadata?.onderwijstype   || ONDERWIJSTYPE_DEFAULT;
        currentOnderwijsniveau = data.opgave?.metadata?.onderwijsniveau || ONDERWIJSNIVEAU_DEFAULT;
        currentNotitie         = data.opgave?.metadata?.notitie         || '';

        // Statische labels in topbalk bijwerken
        if (typeof updateMetaLabels === 'function') updateMetaLabels();

        // Classificatie inlezen (leeg blok als niet aanwezig)
        loadClassificatieFromJSON(data.opgave);
        showClassificatieSection(true);

        // Tellers (statistieken) bovenin classificatie-sectie vullen
        fillClStats(data.opgave);

        // Randvoorwaarden-sectie tonen en vullen vanuit JSON
        showRandvoorwaardenSection(true);
        fillRandvoorwaardenUI();

        // Mathblocks + klasses uit JSON
        const mbs = data.opgave?.mathblocks || [];
        // Map naar de summary-vorm die renderInspectorMathblocks verwacht
        const summary = mbs.map(m => ({
            id:        m.id,
            step:      m.step,
            symbool:   m.operatie?.symbool || '',
            heeft_breuken: (m.input || []).some(i =>
                typeof i?.waarde === 'string' && i.waarde.includes('/')),
            input_preview: (m.input || []).map(i => String(i.waarde ?? '')),
        }));
        for (const k of Object.keys(inspectorState.klasses))
            delete inspectorState.klasses[k];
        for (const m of mbs) {
            if (m.klasse) inspectorState.klasses[m.id] = m.klasse;
        }
        renderInspectorMathblocks(summary);
        // NIEUW: hints-editor vullen met de echte mathblocks uit de JSON
        renderHintsEditor(mbs);

        // SVG tonen
        svgInner.innerHTML = selectedOpgaveSvg;
        svgContainerEl.classList.remove('is-empty');
        requestAnimationFrame(() => zoomFit());

        // Pipeline info
        infoTekst.textContent = data.opgave?.metadata?.expressie?.tekst || '';
        infoLatex.textContent = latex;
        pipelineInfo.hidden = false;

        // Statusbar meta — uitgebreide info over geladen opgave
        const meta        = data.opgave?.metadata || {};
        const opgaveId    = meta.id || id;
        const auteur      = meta.auteur || 'onbekend';
        const niveau      = meta.niveau || '—';
        const nMathblocks = meta.aantal_mathblocks || 0;
        const nSteps      = meta.aantal_steps || 0;
        if (statusbarMeta) {
            statusbarMeta.innerHTML =
                `<span class="sb-key">ID</span> <span class="sb-val mono">${escapeHtml(opgaveId)}</span>` +
                `<span class="sep">·</span>` +
                `<span class="sb-key">auteur</span> <span class="sb-val">${escapeHtml(auteur)}</span>` +
                `<span class="sep">·</span>` +
                `<span class="sb-val">${nMathblocks} ${nMathblocks === 1 ? 'bewerking' : 'bewerkingen'}</span>` +
                `<span class="sep">·</span>` +
                `<span class="sb-val">${nSteps} ${nSteps === 1 ? 'stap' : 'stappen'}</span>` +
                `<span class="sep">·</span>` +
                `<span class="sb-key">niveau</span> <span class="sb-val">${escapeHtml(niveau)}</span>`;
        }

        // Onthoud voor export
        lastProcessed = {
            latex,
            tekst: data.opgave?.metadata?.expressie?.tekst || '',
            latex_display: latex,
            ast: data.opgave?.metadata?.expressie?.ast,
        };
        // Een geselecteerde opgave is niet 'dirty' — pas wijziging maakt dat zo
        hasUnparsedChanges = false;
        editSessionTouched = false;
        // justSaved blijft als hij was: bij selectie ná opslaan is hij true,
        // bij selectie vanuit lijst-klik is hij al false (geen save-actie)
        btnEdit.hidden = false;
        if (btnDelete) btnDelete.hidden = false;
        btnEdit.textContent = 'Edit toestaan';

        setStatus('Opgave <code class="mono">' + escapeHtml(id) + '</code> geladen.', 'info');

        // Update lijst-selectie visueel
        for (const el of olList.querySelectorAll('.ol-item')) {
            el.classList.toggle('is-selected', el.getAttribute('data-id') === id);
        }

        // Focus op het geselecteerde LI zodat pijltjes meteen werken voor
        // navigeren naar de volgende/vorige opgave. Zonder dit moet de
        // gebruiker eerst nog ergens in de lijst klikken voordat het toetsenbord
        // de lijst bedient.
        // We zetten de focus twee keer: nu (synchroon) én na een korte vertraging.
        // Dat tweede moment is nodig omdat MathLive bij setValue() de focus
        // naar zichzelf trekt — zonder de delayed re-focus zou de focus
        // direct weer wegvallen van de opgavenlijst en zouden pijltjes niet
        // werken nadat de gebruiker de muisknop loslaat.
        const selectedLi = olList.querySelector('.ol-item.is-selected');
        if (selectedLi) {
            selectedLi.focus({ preventScroll: true });
            setTimeout(() => {
                // Alleen herstellen als er ondertussen niet doelbewust elders
                // is geklikt of getypt.
                if (document.activeElement === document.body ||
                    document.activeElement === mathField ||
                    document.activeElement?.tagName === 'MATH-FIELD') {
                    selectedLi.focus({ preventScroll: true });
                }
            }, 100);
        }

        // Huidige view handhaven (SVG of JSON)
        setView(currentView);
        updateButtonStates();

        // Optioneel: na 'Opslaan' wil de gebruiker meteen Didactiek &
        // Classificatie en Randvoorwaarden kunnen aanpassen. Dan ontgrendelen
        // we die secties ondanks dat editMode op false staat.
        if (unlockClassificatieAfter) {
            applyClassificatieLock(false);
            applyRandvoorwaardenLock(false);
        }
    } catch (err) {
        setStatus('Verbindingsfout: ' + escapeHtml(err.message), 'error');
    }
}

/**
 * Wissel tussen SVG- en JSON-weergave in het result-panel.
 */
function setView(v) {
    currentView = v;
    const isSvg = v === 'svg';
    viewSvgBtn.classList.toggle('is-active', isSvg);
    viewJsonBtn.classList.toggle('is-active', !isSvg);
    svgContainerEl.hidden = !isSvg;
    jsonView.hidden = isSvg;

    if (!isSvg) {
        // Toon de JSON van de geselecteerde opgave, of van lastProcessed als die er is
        const data = selectedOpgaveJson || (lastProcessed ? {
            metadata: { expressie: { latex: lastProcessed.latex, tekst: lastProcessed.tekst } },
            note: 'Nog niet geëxporteerd — dit is een preview.',
        } : null);
        jsonView.textContent = data
            ? JSON.stringify(data, null, 2)
            : '(Geen opgave geselecteerd of geparsed.)';
    }
}

/**
 * Zet math-field read-only op/af afhankelijk van editMode en of er
 * een opgave geselecteerd is.
 */
function applyEditLock() {
    const locked = !!selectedOpgaveId && !editMode;
    try {
        // MathLive math-field leest meerdere signalen. Zowel het
        // `readonly`-attribuut (HTML-spec: aanwezig = read-only, los
        // van de waarde) als de `readOnly`-property op het element.
        //
        // Cruciale valkuil: setAttribute('readonly', 'false') betekent
        // NIET read-only-uit; de aanwezigheid van het attribuut telt
        // al. Dus we moeten het attribuut echt verwijderen.
        if (locked) {
            mathField.setAttribute('readonly', '');
            mathField.setAttribute('tabindex', '-1');
        } else {
            mathField.removeAttribute('readonly');
            mathField.removeAttribute('tabindex');
        }
        // Property-kant ook zetten voor zekerheid (MathLive-versies
        // reageren soms alleen op de property).
        mathField.readOnly = locked;
    } catch (e) { /* ignore — element bestaat niet of is nog niet upgrade'd */ }
    textInput.readOnly = locked;
    if (soortOpgaveSelect) soortOpgaveSelect.disabled = locked;
    if (productieSelect)   productieSelect.disabled   = locked;
    opdrachtSelect.disabled = locked;
    applyClassificatieLock(locked);
    applyRandvoorwaardenLock(locked);
    if (locked) {
        svgContainerEl.classList.add('is-locked');
    } else {
        svgContainerEl.classList.remove('is-locked');
    }
}

function toggleEdit() {
    if (!selectedOpgaveId) return;
    editMode = !editMode;
    justSaved = false;
    editSessionTouched = false;  // nieuwe edit-sessie: nog niets gebeurd
    applyEditLock();
    btnEdit.textContent = editMode ? 'Edit vergrendelen' : 'Edit toestaan';
    if (editMode) {
        setStatus('Bewerking toegestaan. Na <strong>Parse</strong> en <strong>Opslaan</strong> kun je kiezen om de bestaande opgave te overschrijven.', 'info');
        try { mathField.focus(); } catch (e) {}
    }
    updateButtonStates();
}

/**
 * Deselecteer de huidige opgave: terug naar "nieuwe opgave" modus.
 * Wordt aangeroepen vanuit clearAll.
 */
function deselectOpgave() {
    selectedOpgaveId = null;
    selectedOpgaveJson = null;
    selectedOpgaveSvg = null;
    editMode = false;
    applyEditLock();
    btnEdit.hidden = true;
    if (btnDelete) btnDelete.hidden = true;
    for (const el of olList.querySelectorAll('.ol-item.is-selected')) {
        el.classList.remove('is-selected');
        el.setAttribute('aria-selected', 'false');
    }
    // Reset statistiek-tellers
    fillClStats(null);
    // Randvoorwaarden-sectie verbergen
    showRandvoorwaardenSection(false);
    updateButtonStates();
}

/* Delete-flow */

/* ─── Contextmenu en prullenbak (sub-ronde D) ───────────────────────
 *
 * Verwijderen gebeurt voortaan via rechtsklik op een opgave. Het oude
 * 'Verwijderen'-knop in de top-balk is weg. De delete-dialog wordt
 * hergebruikt met aangepaste teksten.
 *
 * 'Verwijderen' betekent nu: verplaatsen naar de Prullenbak-folder
 * (direct onder de root). Permanent verwijderen kan in een latere ronde.
 *
 * State: pendingDeleteOpgave bevat {id, folder} van de opgave waarop
 * gewacht wordt op bevestiging. Onafhankelijk van selectedOpgaveId, want
 * een gebruiker kan rechtsklikken op een niet-geselecteerde opgave.
 */

const contextMenu = document.getElementById('opgave-contextmenu');
const ctxDeleteBtn = document.getElementById('ctx-delete');
let pendingDeleteOpgave = null;  // {id, folder} of null
const TRASH_FOLDER_NAME = 'Prullenbak';

/**
 * Toon het contextmenu op de gegeven schermpositie, voor de gegeven
 * opgave. opgaveData heeft tenminste {id, folder}.
 */
function showOpgaveContextMenu(clientX, clientY, opgaveData) {
    pendingDeleteOpgave = opgaveData;
    contextMenu.hidden = false;
    // Bereken positie zodat menu niet buiten scherm valt
    const rect = contextMenu.getBoundingClientRect();
    const maxX = window.innerWidth - rect.width - 8;
    const maxY = window.innerHeight - rect.height - 8;
    contextMenu.style.left = Math.min(clientX, maxX) + 'px';
    contextMenu.style.top  = Math.min(clientY, maxY) + 'px';
}

function hideContextMenu() {
    contextMenu.hidden = true;
    // pendingDeleteOpgave NIET resetten — de Verwijderen-klik moet hem nog
    // gebruiken. Reset gebeurt in confirmDelete of bij annuleren van dialog.
}

// Sluit contextmenu bij elke klik buiten het menu
document.addEventListener('click', (e) => {
    if (!contextMenu.contains(e.target)) hideContextMenu();
});

// Sluit bij Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') hideContextMenu();
});

// Klik op "Verwijderen" in contextmenu → open bevestigingsdialoog
ctxDeleteBtn.addEventListener('click', () => {
    hideContextMenu();
    if (!pendingDeleteOpgave) return;
    deleteIdEl.textContent = pendingDeleteOpgave.id;
    deleteDialog.hidden = false;
    requestAnimationFrame(() => deleteConfirmBtn.focus());
});

function closeDeleteDialog() {
    deleteDialog.hidden = true;
    pendingDeleteOpgave = null;
}

/**
 * Voer de verplaats-actie uit: opgave naar Prullenbak.
 * Naam blijft ongewijzigd, behalve bij conflict (suffix).
 */
async function confirmDelete() {
    if (!pendingDeleteOpgave) { closeDeleteDialog(); return; }
    const {id, folder} = pendingDeleteOpgave;
    deleteConfirmBtn.disabled = true;
    deleteConfirmBtn.textContent = 'Bezig…';
    try {
        const r = await fetch('/api/move_opgave', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: id,
                target_folder: TRASH_FOLDER_NAME,
                source_folder: folder || null,
            }),
        });
        const data = await r.json();
        if (data.success) {
            let msg = 'Opgave <code class="mono">' + escapeHtml(id) +
                      '</code> naar prullenbak verplaatst.';
            if (data.renamed_to) {
                msg += ' (hernoemd naar <code class="mono">' +
                       escapeHtml(data.renamed_to) + '</code> wegens naamconflict)';
            }
            setStatus(msg, 'success');
            // Als de verwijderde opgave de actieve was: schoonmaken
            if (selectedOpgaveId === id) {
                deselectOpgave();
                clearAll();
            }
            loadOpgavenLijst();
        } else {
            setStatus('Kon niet verplaatsen: ' +
                      escapeHtml(data.error || 'onbekend'), 'error');
        }
    } catch (err) {
        setStatus('Verbindingsfout: ' + escapeHtml(err.message), 'error');
    } finally {
        closeDeleteDialog();
        deleteConfirmBtn.disabled = false;
        deleteConfirmBtn.textContent = 'Ja, naar prullenbak';
    }
}

/* Keyboard: Escape sluit delete-dialog, klik-buiten ook */
deleteDialog.addEventListener('click', (e) => {
    if (e.target === deleteDialog) closeDeleteDialog();
});


/* ─── Metadata-modaal (Opslaan-formulier, sub-ronde D) ─────────────
 *
 * Opslaan opent voortaan eerst dit modaal. Daarin staan zes velden:
 * Soort opgave, Onderwijstype, Onderwijsniveau, Opdracht, Productietype,
 * Notitie. De huidige waarden worden vooringevuld (van de actieve opgave
 * óf van de laatst gebruikte set).
 *
 * Bij bevestiging:
 *   1. State (currentSoortOpgave etc.) bijwerken
 *   2. Hidden selects bijwerken zodat bestaande on*Change-handlers triggeren
 *   3. Statische labels in topbalk updaten
 *   4. requestExport() aanroepen — de oude export-flow doet de echte save
 */

const metadataDialog       = document.getElementById('metadata-dialog');
const metadataConfirmBtn   = document.getElementById('metadata-confirm');
const metadataStatusEl     = document.getElementById('metadata-status');

function openMetadataDialog() {
    // Eis: er moet een geparste expressie zijn (anders kan requestExport niets)
    if (!lastProcessed) {
        setStatus('Eerst parsen (druk op Parse) voordat je opslaat.', 'error');
        return;
    }
    // Vul velden vanuit de current-state (= huidige opgave of laatste defaults)
    document.getElementById('md-soort').value           = currentSoortOpgave;
    document.getElementById('md-onderwijstype').value   = currentOnderwijstype;
    document.getElementById('md-onderwijsniveau').value = currentOnderwijsniveau;
    document.getElementById('md-opdracht').value        = currentOpdracht;
    document.getElementById('md-productie').value       = currentProductie;
    document.getElementById('md-notitie').value         = currentNotitie;
    if (metadataStatusEl) metadataStatusEl.hidden = true;
    metadataConfirmBtn.disabled = false;
    metadataConfirmBtn.textContent = 'Opslaan';
    metadataDialog.hidden = false;
    setTimeout(() => {
        document.getElementById('md-soort').focus();
    }, 50);
}

function closeMetadataDialog() {
    metadataDialog.hidden = true;
}

async function confirmMetadataSave() {
    // 1. Lees waardes uit
    const soort         = document.getElementById('md-soort').value;
    const onderwijstype = document.getElementById('md-onderwijstype').value;
    const niveau        = document.getElementById('md-onderwijsniveau').value;
    const opdracht      = document.getElementById('md-opdracht').value;
    const productie     = document.getElementById('md-productie').value;
    const notitie       = document.getElementById('md-notitie').value;

    // 2. Update state
    currentSoortOpgave    = soort;
    currentOnderwijstype  = onderwijstype;
    currentOnderwijsniveau = niveau;
    currentOpdracht       = opdracht;
    currentProductie      = productie;
    currentNotitie        = notitie;

    // 3. Hidden selects bijwerken (backward-compat: bestaande onChange-handlers
    //    krijgen hierdoor de juiste waardes te zien).
    const soortSelect = document.getElementById('soort-opgave-select');
    const prodSelect  = document.getElementById('productie-select');
    const opdrSelect  = document.getElementById('opdracht-select');
    if (soortSelect && soortSelect.value !== soort) {
        soortSelect.value = soort;
        // Trigger zoals een echte change om pipeline-keuze door te zetten
        if (typeof onSoortOpgaveChange === 'function') {
            onSoortOpgaveChange(soort);
        }
    }
    if (prodSelect && prodSelect.value !== productie) {
        prodSelect.value = productie;
        if (typeof onProductieChange === 'function') {
            onProductieChange(productie);
        }
    }
    if (opdrSelect && opdrSelect.value !== opdracht) {
        opdrSelect.value = opdracht;
        if (typeof onOpdrachtChange === 'function') {
            onOpdrachtChange(opdracht);
        }
    }

    // 4. Statische labels updaten
    updateMetaLabels();

    // 5. Sluit het modaal en delegeer naar de bestaande export-flow
    closeMetadataDialog();
    await requestExport();
}

/**
 * Werk de statische labels in de topbalk bij. Wordt aangeroepen bij elke
 * wijziging van current* state en bij het laden van een opgave.
 */
function updateMetaLabels() {
    const fmt = (key, val) => META_LABEL_MAP[key]?.[val] || val || '—';
    const set = (id, txt) => {
        const el = document.getElementById(id);
        if (el) el.textContent = txt;
    };
    set('meta-soort',           fmt('soort', currentSoortOpgave));
    set('meta-onderwijstype',   fmt('onderwijstype', currentOnderwijstype));
    set('meta-onderwijsniveau', fmt('onderwijsniveau', currentOnderwijsniveau));
    set('meta-opdracht',        fmt('opdracht', currentOpdracht));
    set('meta-productie',       fmt('productie', currentProductie));
}

// Bij eerste laden: vul de labels met defaults
updateMetaLabels();

// Klik buiten modaal sluit het ook
metadataDialog.addEventListener('click', (e) => {
    if (e.target === metadataDialog) closeMetadataDialog();
});

// Escape sluit
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !metadataDialog.hidden) {
        closeMetadataDialog();
    }
});


/* ─── Integriteit-fout dialog ──────────────────────────────────────
 *
 * Wordt getoond wanneer de server-side JSON-validator structurele fouten
 * heeft gedetecteerd. Blokkerend: het opslaan is niet doorgegaan en de
 * gebruiker moet de fouten ofwel oplossen ofwel een issue indienen.
 */

const integrityDialog = document.getElementById('integrity-dialog');

function showIntegrityDialog(errors, warnings) {
    const errorList = document.getElementById('integrity-error-list');
    const warnList  = document.getElementById('integrity-warning-list');
    const warnWrap  = document.getElementById('integrity-warnings-wrap');

    errorList.innerHTML = '';
    for (const err of errors) {
        const li = document.createElement('li');
        li.textContent = err;
        errorList.appendChild(li);
    }

    if (warnings && warnings.length > 0) {
        warnList.innerHTML = '';
        for (const w of warnings) {
            const li = document.createElement('li');
            li.textContent = w;
            warnList.appendChild(li);
        }
        warnWrap.hidden = false;
    } else {
        warnWrap.hidden = true;
    }

    integrityDialog.hidden = false;
}

function closeIntegrityDialog() {
    integrityDialog.hidden = true;
}

// Klik buiten dialog sluit hem
if (integrityDialog) {
    integrityDialog.addEventListener('click', (e) => {
        if (e.target === integrityDialog) closeIntegrityDialog();
    });
}

// Escape sluit
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && integrityDialog && !integrityDialog.hidden) {
        closeIntegrityDialog();
    }
});


/* ─── Settings dialog ─────────────────────────────────────────────── */

const settingsDialog       = document.getElementById('settings-dialog');
const settingsInput        = document.getElementById('settings-output-dir');
const settingsStatus       = document.getElementById('settings-status');
const settingsConfirmBtn   = document.getElementById('settings-confirm');

const settingsCreateDialog   = document.getElementById('settings-create-dialog');
const settingsCreatePath     = document.getElementById('settings-create-path');
const settingsCreateConfirm  = document.getElementById('settings-create-confirm');

// Onthoud het pad waarvoor we om bevestiging vragen
let pendingCreatePath = '';

async function openSettingsDialog() {
    // Lees de huidige instellingen
    try {
        const r = await fetch('/api/settings');
        const data = await r.json();
        if (data.success && data.settings) {
            settingsInput.value = data.settings.output_dir_raw || data.settings.output_dir || '';
            _showSettingsStatus(data.settings);
        } else {
            settingsInput.value = '';
            hideSettingsStatus();
        }
    } catch (err) {
        settingsInput.value = '';
        hideSettingsStatus();
    }
    settingsConfirmBtn.disabled = false;
    settingsConfirmBtn.textContent = 'Opslaan';
    settingsDialog.hidden = false;
    settingsInput.focus();
}

function closeSettingsDialog() {
    settingsDialog.hidden = true;
    hideSettingsStatus();
}


/* ─── Settings: sectie-navigatie ──────────────────────────────────── */

/**
 * Switch tussen de vier secties in de Instellingen-modal.
 */
function switchSettingsSection(sectionName) {
    document.querySelectorAll('.settings-nav-item').forEach(el => {
        el.classList.toggle('is-active', el.getAttribute('data-section') === sectionName);
    });
    document.querySelectorAll('.settings-section').forEach(el => {
        el.classList.toggle('is-active', el.getAttribute('data-section') === sectionName);
    });
    if (sectionName === 'storage') {
        loadStorageFolders();
    }
}

document.querySelectorAll('.settings-nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
        switchSettingsSection(btn.getAttribute('data-section'));
    });
});


/* ─── Settings: Opslag Exercises Beheren ─────────────────────────── */

let storageSelectedFolder = null;

async function loadStorageFolders() {
    const listEl = document.getElementById('storage-folder-list');
    if (!listEl) return;
    try {
        const r = await fetch('/api/list_opgaven');
        const data = await r.json();
        if (!data.success) {
            listEl.innerHTML = '<div class="storage-folder-empty-list">Kon folders niet laden.</div>';
            return;
        }
        renderStorageFolders(data.folders || []);
    } catch (err) {
        listEl.innerHTML = '<div class="storage-folder-empty-list">Verbindingsfout: ' +
            escapeHtml(err.message) + '</div>';
    }
}

function renderStorageFolders(folders) {
    const listEl = document.getElementById('storage-folder-list');
    if (!listEl) return;
    listEl.innerHTML = '';

    if (folders.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'storage-folder-empty-list';
        empty.textContent = 'Er zijn nog geen folders. Klik op + Toevoegen om een eerste folder aan te maken.';
        listEl.appendChild(empty);
        storageSelectedFolder = null;
        updateStorageActionButtons(null, 0);
        return;
    }

    const sorted = [...folders].sort((a, b) =>
        a.name.toLowerCase().localeCompare(b.name.toLowerCase()));

    for (const f of sorted) {
        const row = document.createElement('div');
        row.className = 'storage-folder-row';
        row.setAttribute('data-name', f.name);
        if (storageSelectedFolder === f.name) row.classList.add('is-selected');

        const name = document.createElement('span');
        name.className = 'storage-folder-row-name';
        name.textContent = f.name;

        const count = document.createElement('span');
        count.className = 'storage-folder-row-count';
        count.textContent = `${f.opgave_count} opgave${f.opgave_count === 1 ? '' : 'n'}`;

        row.appendChild(name);
        row.appendChild(count);

        row.addEventListener('click', () => {
            storageSelectedFolder = (storageSelectedFolder === f.name) ? null : f.name;
            document.querySelectorAll('.storage-folder-row').forEach(r => {
                r.classList.toggle('is-selected',
                    r.getAttribute('data-name') === storageSelectedFolder);
            });
            updateStorageActionButtons(storageSelectedFolder, f.opgave_count);
        });

        listEl.appendChild(row);
    }

    if (storageSelectedFolder && !sorted.find(f => f.name === storageSelectedFolder)) {
        storageSelectedFolder = null;
    }
    updateStorageActionButtons(storageSelectedFolder,
        sorted.find(f => f.name === storageSelectedFolder)?.opgave_count ?? 0);
}

function updateStorageActionButtons(folderName, opgaveCount) {
    const hasSelection = folderName !== null && folderName !== undefined;
    document.getElementById('storage-rename').disabled = !hasSelection;
    document.getElementById('storage-delete').disabled = !hasSelection || opgaveCount > 0;
    document.getElementById('storage-move').disabled = true;  // sub-ronde C: alleen 1 niveau
    document.getElementById('storage-copy').disabled = !hasSelection;
    document.getElementById('storage-dedicated').disabled = true;  // placeholder
}

function showStorageStatus(msg, kind = 'info') {
    const el = document.getElementById('storage-status');
    if (!el) return;
    el.textContent = msg;
    el.className = 'dialog-status is-' + kind;
    el.hidden = false;
    if (kind !== 'error') {
        setTimeout(() => { el.hidden = true; }, 4000);
    }
}

async function storageActionAdd() {
    const name = prompt('Naam voor de nieuwe folder:');
    if (!name || !name.trim()) return;
    try {
        const r = await fetch('/api/folders/create', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name.trim()})
        });
        const data = await r.json();
        if (data.success) {
            showStorageStatus(`Folder '${name}' aangemaakt.`, 'success');
            await loadStorageFolders();
            loadOpgavenLijst();
        } else {
            showStorageStatus('Fout: ' + (data.error || 'onbekend'), 'error');
        }
    } catch (err) {
        showStorageStatus('Verbindingsfout: ' + err.message, 'error');
    }
}

async function storageActionRename() {
    if (!storageSelectedFolder) return;
    const newName = prompt(`Nieuwe naam voor '${storageSelectedFolder}':`, storageSelectedFolder);
    if (!newName || !newName.trim() || newName === storageSelectedFolder) return;
    try {
        const r = await fetch('/api/folders/rename', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                folder: storageSelectedFolder,
                new_name: newName.trim()
            })
        });
        const data = await r.json();
        if (data.success) {
            showStorageStatus(`Folder hernoemd naar '${newName}'.`, 'success');
            storageSelectedFolder = newName.trim();
            await loadStorageFolders();
            loadOpgavenLijst();
        } else {
            showStorageStatus('Fout: ' + (data.error || 'onbekend'), 'error');
        }
    } catch (err) {
        showStorageStatus('Verbindingsfout: ' + err.message, 'error');
    }
}

async function storageActionDelete() {
    if (!storageSelectedFolder) return;
    if (!confirm(`Folder '${storageSelectedFolder}' verwijderen?\n\nDit kan alleen als de folder leeg is.`)) return;
    try {
        const r = await fetch('/api/folders/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({folder: storageSelectedFolder})
        });
        const data = await r.json();
        if (data.success) {
            showStorageStatus(`Folder '${storageSelectedFolder}' verwijderd.`, 'success');
            storageSelectedFolder = null;
            await loadStorageFolders();
            loadOpgavenLijst();
        } else {
            showStorageStatus('Fout: ' + (data.error || 'onbekend'), 'error');
        }
    } catch (err) {
        showStorageStatus('Verbindingsfout: ' + err.message, 'error');
    }
}

async function storageActionCopy() {
    if (!storageSelectedFolder) return;
    const newName = prompt(
        `Naam voor de kopie van '${storageSelectedFolder}':`,
        `${storageSelectedFolder} (kopie)`
    );
    if (!newName || !newName.trim()) return;
    try {
        const r = await fetch('/api/folders/copy', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                folder: storageSelectedFolder,
                new_parent: '',  // root in sub-ronde C
                new_name: newName.trim()
            })
        });
        const data = await r.json();
        if (data.success) {
            showStorageStatus(`Folder gekopieerd naar '${data.name}'.`, 'success');
            await loadStorageFolders();
            loadOpgavenLijst();
        } else {
            showStorageStatus('Fout: ' + (data.error || 'onbekend'), 'error');
        }
    } catch (err) {
        showStorageStatus('Verbindingsfout: ' + err.message, 'error');
    }
}

/* ─── Randvoorwaarden harmonica-sectie ────────────────────────────────
 * Derde harmonica in de rechterkolom (mosterd, na Hints en Classificatie).
 * Bevat zeven instellingen die in de JSON terechtkomen.
 * Toggle-functie: openen/sluiten van de body. Vulling vanuit
 * inspectorState.randvoorwaarden. Validatie bij Opslaan.
 */

function showRandvoorwaardenSection(visible) {
    const sec = document.getElementById('rv-section');
    if (sec) sec.hidden = !visible;
}

function toggleRvSection() {
    const body = document.getElementById('rv-body');
    const chev = document.getElementById('rv-chevron');
    if (!body) return;
    const isOpen = !body.hidden;
    body.hidden = isOpen;
    if (chev) chev.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(180deg)';
    if (!isOpen) {
        // Bij openen: vul UI vanuit huidige state
        fillRandvoorwaardenUI();
    }
}

function fillRandvoorwaardenUI() {
    const rv = inspectorState.randvoorwaarden;
    _setRadio('rv-breuken',   rv.antwoord_in_breuken ? 'ja' : 'nee');
    _setRadio('rv-decimalen', rv.antwoord_in_decimalen ? 'ja' : 'nee');
    _setRadio('rv-gemengd',   rv.uitkomst_als_gemengd_getal ? 'ja' : 'nee');
    _setRadio('rv-hints',     rv.hints_aan ? 'ja' : 'nee');
    _setRadio('rv-feedback',  rv.feedback_aan ? 'ja' : 'nee');
    const decInp = document.getElementById('rv-input-decimalen-afronden');
    const piInp  = document.getElementById('rv-input-pi-decimalen');
    if (decInp) decInp.value = rv.decimalen_afronden ?? 2;
    if (piInp)  piInp.value  = rv.pi_decimalen ?? 2;
    _hideRandvoorwaardenError();
    _updateDecimalenSubVisibility();
}

function saveRandvoorwaarden() {
    // Lees alle waarden uit de UI
    const breuken   = _getRadio('rv-breuken') === 'ja';
    const decimalen = _getRadio('rv-decimalen') === 'ja';
    const gemengd   = _getRadio('rv-gemengd') === 'ja';
    const hints     = _getRadio('rv-hints') === 'ja';
    const feedback  = _getRadio('rv-feedback') === 'ja';
    const decAfr    = parseInt(document.getElementById('rv-input-decimalen-afronden').value, 10);
    const piDec     = parseInt(document.getElementById('rv-input-pi-decimalen').value, 10);

    // Validatie: tegenstrijdigheden detecteren
    const errors = [];
    if (breuken && decimalen) {
        errors.push('De uitkomst kan niet tegelijk in breuken én decimalen worden geëist. Kies één van beide.');
    }
    if (!breuken && !decimalen) {
        errors.push('Kies óf breuken óf decimalen voor de uitkomst.');
    }
    if (decimalen && gemengd) {
        errors.push('"Uitkomst als gemengd getal" en "antwoord in decimalen" zijn tegenstrijdig. Kies één van beide.');
    }
    if (Number.isNaN(decAfr) || decAfr < 0 || decAfr > 15) {
        errors.push('Aantal decimalen voor afronding moet tussen 0 en 15 liggen.');
    }
    if (Number.isNaN(piDec) || piDec < 0 || piDec > 15) {
        errors.push('Aantal decimalen voor π moet tussen 0 en 15 liggen.');
    }

    if (errors.length > 0) {
        _showRandvoorwaardenError(errors);
        return;
    }

    // Schrijf naar state
    const rv = inspectorState.randvoorwaarden;
    rv.antwoord_in_breuken = breuken;
    rv.antwoord_in_decimalen = decimalen;
    rv.decimalen_afronden = decAfr;
    rv.pi_decimalen = piDec;
    rv.uitkomst_als_gemengd_getal = gemengd;
    rv.hints_aan = hints;
    rv.feedback_aan = feedback;

    _hideRandvoorwaardenError();
    setStatus('Randvoorwaarden opgeslagen.', 'success');
}

function applyRandvoorwaardenLock(locked) {
    const sec = document.getElementById('rv-section');
    if (!sec) return;
    if (locked) sec.classList.add('rv-locked');
    else        sec.classList.remove('rv-locked');
}

/* Helpers voor radio-knoppen */
function _setRadio(name, val) {
    const radios = document.querySelectorAll(`input[name="${name}"]`);
    radios.forEach(r => { r.checked = (r.value === val); });
}
function _getRadio(name) {
    const r = document.querySelector(`input[name="${name}"]:checked`);
    return r ? r.value : null;
}
function _showRandvoorwaardenError(errors) {
    const el = document.getElementById('rv-error');
    if (!el) return;
    el.innerHTML = '<strong>Tegenstrijdigheden:</strong><ul>' +
        errors.map(e => '<li>' + e + '</li>').join('') + '</ul>';
    el.hidden = false;
}
function _hideRandvoorwaardenError() {
    const el = document.getElementById('rv-error');
    if (el) el.hidden = true;
}
/* Toon/verberg de "afronden op n decimalen"-rij afhankelijk van of "antwoord
   in decimalen" geselecteerd is. */
function _updateDecimalenSubVisibility() {
    const sub = document.getElementById('rv-row-decimalen-afronden');
    if (!sub) return;
    const isDec = _getRadio('rv-decimalen') === 'ja';
    sub.style.opacity = isDec ? '1' : '0.5';
    const inp = document.getElementById('rv-input-decimalen-afronden');
    if (inp) inp.disabled = !isDec;
}

// Live update wanneer "antwoord in decimalen" wordt aangepast
document.addEventListener('change', (e) => {
    if (e.target && e.target.name === 'rv-decimalen') {
        _updateDecimalenSubVisibility();
    }
});

function _showSettingsStatus(settings) {
    if (!settings) { hideSettingsStatus(); return; }
    const exp = settings.output_dir || '';
    const exists = !!settings.exists;
    const writable = !!settings.writable;
    let cls, txt;
    if (exists && writable) {
        cls = 'status-ok';
        txt = 'Directory bestaat en is schrijfbaar.';
    } else if (exists && !writable) {
        cls = 'status-warn';
        txt = 'Directory bestaat maar is niet schrijfbaar.';
    } else {
        cls = 'status-info';
        txt = 'Directory bestaat nog niet — wordt aangemaakt bij opslaan.';
    }
    settingsStatus.className = 'dialog-status ' + cls;
    settingsStatus.innerHTML =
        '<div class="mono">' + escapeHtml(exp) + '</div>' +
        '<div>' + escapeHtml(txt) + '</div>';
    settingsStatus.hidden = false;
}

function hideSettingsStatus() {
    settingsStatus.hidden = true;
    settingsStatus.innerHTML = '';
}

async function saveSettings(createIfMissing) {
    const newDir = (settingsInput.value || '').trim();
    if (!newDir) {
        settingsStatus.className = 'dialog-status status-warn';
        settingsStatus.textContent = 'Geef een pad op.';
        settingsStatus.hidden = false;
        return;
    }
    settingsConfirmBtn.disabled = true;
    settingsConfirmBtn.textContent = 'Bezig…';
    try {
        const r = await fetch('/api/settings', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                output_dir: newDir,
                create_if_missing: !!createIfMissing,
            }),
        });
        const data = await r.json();
        if (data.success && data.status === 'ok') {
            setStatus(
                'Output directory ingesteld op <code class="mono">' +
                escapeHtml(data.settings.output_dir) + '</code>' +
                (data.created ? ' (aangemaakt)' : ''),
                'success'
            );
            closeSettingsDialog();
            // Herlaad opgavenlijst uit nieuwe directory
            loadOpgavenLijst();
        } else if (data.status === 'needs_confirmation') {
            // Open bevestigingsdialoog
            pendingCreatePath = newDir;
            settingsCreatePath.textContent = data.output_dir || newDir;
            settingsCreateDialog.hidden = false;
        } else {
            // Echte fout
            settingsStatus.className = 'dialog-status status-error';
            settingsStatus.textContent = 'Fout: ' + (data.error || 'onbekend');
            settingsStatus.hidden = false;
        }
    } catch (err) {
        settingsStatus.className = 'dialog-status status-error';
        settingsStatus.textContent = 'Verbindingsfout: ' + err.message;
        settingsStatus.hidden = false;
    } finally {
        settingsConfirmBtn.disabled = false;
        settingsConfirmBtn.textContent = 'Opslaan';
    }
}

function closeSettingsCreateDialog() {
    settingsCreateDialog.hidden = true;
    pendingCreatePath = '';
    settingsCreateConfirm.disabled = false;
    settingsCreateConfirm.textContent = 'Ja, aanmaken';
}

async function confirmSettingsCreate() {
    if (!pendingCreatePath) {
        closeSettingsCreateDialog();
        return;
    }
    settingsCreateConfirm.disabled = true;
    settingsCreateConfirm.textContent = 'Bezig…';
    // Zet het pad terug in het input veld (voor de zekerheid) en sla op met create_if_missing
    settingsInput.value = pendingCreatePath;
    settingsCreateDialog.hidden = true;
    await saveSettings(true);
    pendingCreatePath = '';
    settingsCreateConfirm.disabled = false;
    settingsCreateConfirm.textContent = 'Ja, aanmaken';
}

/* Keyboard: Escape sluit settings dialogs, klik-buiten ook */
settingsDialog.addEventListener('click', (e) => {
    if (e.target === settingsDialog) closeSettingsDialog();
});
settingsCreateDialog.addEventListener('click', (e) => {
    if (e.target === settingsCreateDialog) closeSettingsCreateDialog();
});
// Enter in het inputveld = Opslaan
settingsInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); saveSettings(false); }
    if (e.key === 'Escape') { closeSettingsDialog(); }
});

/* Algemene Escape handler voor dialogs */
document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (!settingsCreateDialog.hidden) closeSettingsCreateDialog();
    else if (!settingsDialog.hidden) closeSettingsDialog();
});


/* ─── Initialisatie ───────────────────────────────────────────────── */

// Initiële knop-states (alles disabled tot er content of selectie is)
updateButtonStates();

// Quick-buttons: voeg LaTeX-snippet in op cursor-positie
// Gebruikt MathLive's executeCommand('insert', ...). De data-insert kan
// MathLive-placeholders bevatten: #0 = primaire cursor-positie,
// #? = secondaire placeholder (tab-navigeerbaar), #@ = vorige expressie.
document.querySelectorAll('#quick-buttons .qb').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.preventDefault();
        if (textMode) return;  // niet in tekst-modus
        const tex = btn.getAttribute('data-insert');
        if (!tex || !mathField) return;
        try {
            mathField.executeCommand(['insert', tex, {
                insertionMode: 'replaceSelection',
                selectionMode: 'placeholder',
                format: 'latex',
            }]);
        } catch (err) {
            // Fallback: probeer simpelere insert API
            try { mathField.insert(tex); } catch (e2) {}
        }
        // Focus terug naar math-field zodat gebruiker direct kan typen
        try { mathField.focus(); } catch (e3) {}
        // Markeer expressie als gewijzigd zodat Parse actief wordt
        _markDirty();
    });
});

// Keyboard-nav op UL-level zodat pijltjestoetsen ALTIJD werken zolang
// de focus ergens in de lijst ligt.
if (olList) {
    olList.addEventListener('keydown', onOpgavenListKey);
    // Maak de UL zelf focusable zodat klikken buiten een LI (bijv. op de witruimte
    // eronder) alsnog keyboard-navigatie toelaat.
    olList.setAttribute('tabindex', '0');
}

// Klik-om-te-kopiëren voor de "Expressie" en "LaTeX voor export" labels
// onderaan het scherm. Bij klik wordt de waarde van het bijbehorende
// <dd>-veld naar het klembord gekopieerd, met visuele bevestiging.
document.querySelectorAll('.info-label-copy').forEach(label => {
    label.addEventListener('click', async () => {
        const targetId = label.getAttribute('data-target');
        if (!targetId) return;
        const targetEl = document.getElementById(targetId);
        if (!targetEl) return;
        const text = targetEl.textContent || '';
        if (!text) return;  // niets om te kopiëren
        try {
            await navigator.clipboard.writeText(text);
            // Visuele bevestiging: voeg "is-copied" class toe en haal weg na 1.5s
            label.classList.add('is-copied');
            setTimeout(() => label.classList.remove('is-copied'), 1500);
        } catch (err) {
            // Fallback voor browsers zonder clipboard API of zonder permissie
            try {
                const ta = document.createElement('textarea');
                ta.value = text;
                ta.style.position = 'fixed';
                ta.style.opacity = '0';
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                label.classList.add('is-copied');
                setTimeout(() => label.classList.remove('is-copied'), 1500);
            } catch (e) {
                setStatus('Kopiëren mislukt: ' + escapeHtml(err.message), 'error');
            }
        }
    });
});

/* ─── Help-overlay (sub-ronde punt 2) ──────────────────────────────
 *
 * Klik op de ?-knop opent een waas over het scherm met labels die
 * naar UI-elementen wijzen. Klik ergens sluit het.
 *
 * Configuratie: HELP_TARGETS is een lijst van objecten met:
 *   - selector: CSS-selector om het doel-element te vinden
 *   - titel:    korte naam (small caps boven de tekst)
 *   - tekst:    één korte uitleg-zin
 *   - kant:     voorkeurszijde voor het label ('left'/'right'/'top'/'bottom')
 *
 * De kant wordt automatisch gewijzigd als het label buiten het scherm
 * zou vallen.
 */

const HELP_TARGETS = [
    {
        selector: '#opgave-lijst',
        titel: 'Opgavenlijst',
        tekst: 'Folders en opgaven. Klik driehoek om te klappen, klik op naam om te selecteren.',
        kant: 'right',
    },
    {
        selector: '#ol-list .ol-folder-contents .ol-item',
        titel: 'Opgave-item',
        tekst: 'Klik om te laden. Rechtsklik voor menu (Verwijderen).',
        kant: 'right',
    },
    {
        selector: '#meta-labels-row',
        titel: 'Metadata-balk',
        tekst: 'Toont de soort, het onderwijstype en de opdracht van de actieve opgave.',
        kant: 'bottom',
    },
    {
        selector: 'math-field#math-input',
        titel: 'MathField',
        tekst: 'Typ hier de wiskunde-expressie. LaTeX-snelkoppelingen werken.',
        kant: 'bottom',
    },
    {
        selector: '#btn-ok',
        titel: 'Parse',
        tekst: 'Verwerk de expressie tot een AST en toon de SVG-visualisatie.',
        kant: 'bottom',
    },
    {
        selector: '#btn-json',
        titel: 'Opslaan',
        tekst: 'Open het metadata-formulier en sla de opgave op als JSON + SVG.',
        kant: 'bottom',
    },
    {
        selector: '#btn-clear',
        titel: 'Nieuw',
        tekst: 'Leeg het werkveld om aan een nieuwe opgave te beginnen.',
        kant: 'bottom',
    },
    {
        selector: '#btn-header-help',
        titel: 'Help',
        tekst: 'Toont deze labels. (Klik ergens om te sluiten.)',
        kant: 'bottom',
    },
    {
        selector: '#btn-header-settings',
        titel: 'Instellingen',
        tekst: 'Output-pad, folder-beheer, en author-gegevens.',
        kant: 'bottom',
    },
    {
        selector: '#svg-container',
        titel: 'Visualisatie',
        tekst: 'De AST als SVG. Mathblocks staan in stappen (steps) gegroepeerd.',
        kant: 'top',
    },
    {
        selector: '.view-toggle',
        titel: 'SVG / JSON',
        tekst: 'Wissel tussen de visualisatie en de geëxporteerde JSON.',
        kant: 'top',
    },
    {
        selector: '#hints-section',
        titel: 'Hints',
        tekst: 'Bewerk de uitleg per mathblock: structureel, feedback, didactisch.',
        kant: 'left',
    },
    {
        selector: '#rv-section',
        titel: 'Randvoorwaarden',
        tekst: 'Hoe de student het antwoord mag presenteren (breuk, decimaal, gemengd getal).',
        kant: 'left',
    },
    {
        selector: '#inspector',
        titel: 'Inspector',
        tekst: 'Per opgave: hints, klassificatie, randvoorwaarden. Bewerkbaar in edit-modus.',
        kant: 'left',
    },
];

const helpOverlay = document.getElementById('help-overlay');
const helpOverlaySvg = document.getElementById('help-overlay-svg');
const helpOverlayLabels = document.getElementById('help-overlay-labels');

function openHelpOverlay() {
    if (!helpOverlay) return;
    helpOverlay.hidden = false;
    renderHelpLabels();
}

function closeHelpOverlay() {
    if (!helpOverlay) return;
    helpOverlay.hidden = true;
    if (helpOverlaySvg) helpOverlaySvg.innerHTML = '';
    if (helpOverlayLabels) helpOverlayLabels.innerHTML = '';
}

/**
 * Render labels en lijntjes voor alle HELP_TARGETS.
 * Wordt aangeroepen bij openen én bij resize.
 */
function renderHelpLabels() {
    if (!helpOverlay || helpOverlay.hidden) return;
    if (!helpOverlaySvg || !helpOverlayLabels) return;

    helpOverlaySvg.innerHTML = '';
    helpOverlayLabels.innerHTML = '';

    const vw = window.innerWidth;
    const vh = window.innerHeight;

    // Sizing van SVG zo dat coördinaten exact match'en met de viewport
    helpOverlaySvg.setAttribute('viewBox', `0 0 ${vw} ${vh}`);
    helpOverlaySvg.setAttribute('width', vw);
    helpOverlaySvg.setAttribute('height', vh);

    const PAD = 12;          // afstand tussen element-rand en lijn-start
    const LABEL_GAP = 50;    // afstand tussen element-rand en label-rand
    const MARGIN = 8;        // marge tot schermrand

    for (const t of HELP_TARGETS) {
        const el = document.querySelector(t.selector);
        if (!el) continue;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) continue;
        // Skip elementen die volledig buiten viewport vallen
        if (rect.right < 0 || rect.left > vw ||
            rect.bottom < 0 || rect.top > vh) continue;

        // Maak label-DOM zodat we breedte/hoogte kunnen meten vóór positionering
        const label = document.createElement('div');
        label.className = 'help-label';
        const key = document.createElement('span');
        key.className = 'help-label-key';
        key.textContent = t.titel;
        const txt = document.createElement('span');
        txt.textContent = t.tekst;
        label.appendChild(key);
        label.appendChild(txt);
        // Tijdelijk plaatsen om grootte te meten
        label.style.left = '0px';
        label.style.top = '0px';
        label.style.visibility = 'hidden';
        helpOverlayLabels.appendChild(label);
        const lbox = label.getBoundingClientRect();
        const lw = lbox.width;
        const lh = lbox.height;

        // Bepaal eerste kant op basis van voorkeur, switch bij overflow
        let kant = t.kant || 'bottom';
        kant = chooseFitSide(rect, lw, lh, kant, vw, vh, LABEL_GAP, MARGIN);

        // Bereken anchor (op het element) en label-positie
        const {anchor, labelXY} = positionForSide(
            rect, kant, lw, lh, LABEL_GAP, MARGIN, vw, vh
        );

        // Plaats label
        label.style.left = labelXY.x + 'px';
        label.style.top = labelXY.y + 'px';
        label.style.visibility = 'visible';

        // Lijn van anchor naar label-rand (dichtstbijzijnde punt op label-rand)
        const labelAnchor = getNearestEdgePoint(
            labelXY.x, labelXY.y, lw, lh, anchor.x, anchor.y
        );
        const line = appendLine(helpOverlaySvg, anchor, labelAnchor);
        appendDot(helpOverlaySvg, anchor);

        // Koppel het label aan zijn anchor en lijn, zodat de drag-handler
        // bij beweging het label-eind van de lijn kan herrekenen terwijl
        // het anchor-eind (op het UI-element) onveranderd blijft.
        label._helpInfo = {
            anchorX: anchor.x,
            anchorY: anchor.y,
            line: line,
            width: lw,
            height: lh,
        };

        attachDragHandler(label);
    }
}

/**
 * Kies de eerste kant die past binnen het scherm. Probeert de voorkeur,
 * en valt terug op andere kanten als dat niet past.
 */
function chooseFitSide(rect, lw, lh, prefer, vw, vh, gap, margin) {
    const fits = {
        bottom: rect.bottom + gap + lh + margin < vh,
        top:    rect.top - gap - lh - margin > 0,
        right:  rect.right + gap + lw + margin < vw,
        left:   rect.left - gap - lw - margin > 0,
    };
    if (fits[prefer]) return prefer;
    // Probeer in deze volgorde alternatieve kanten
    for (const k of ['bottom', 'top', 'right', 'left']) {
        if (k !== prefer && fits[k]) return k;
    }
    // Niets past — geef voorkeur terug (label valt mogelijk deels buiten scherm)
    return prefer;
}

/**
 * Bereken anchor (punt op element-rand) en label-positie (top-left
 * coordinaat van label-rect) voor een gegeven kant.
 */
function positionForSide(rect, kant, lw, lh, gap, margin, vw, vh) {
    const cx = (rect.left + rect.right) / 2;
    const cy = (rect.top + rect.bottom) / 2;
    let anchor, x, y;

    if (kant === 'bottom') {
        anchor = { x: cx, y: rect.bottom };
        x = cx - lw / 2;
        y = rect.bottom + gap;
    } else if (kant === 'top') {
        anchor = { x: cx, y: rect.top };
        x = cx - lw / 2;
        y = rect.top - gap - lh;
    } else if (kant === 'right') {
        anchor = { x: rect.right, y: cy };
        x = rect.right + gap;
        y = cy - lh / 2;
    } else { // left
        anchor = { x: rect.left, y: cy };
        x = rect.left - gap - lw;
        y = cy - lh / 2;
    }

    // Clamp binnen scherm met marge
    x = Math.max(margin, Math.min(x, vw - lw - margin));
    y = Math.max(margin, Math.min(y, vh - lh - margin));

    return { anchor, labelXY: { x, y } };
}

/**
 * Geef het punt op de label-rand dat het dichtst bij (ax, ay) ligt.
 * Daarvan trekken we de lijn vanaf het element-anchor naar toe.
 */
function getNearestEdgePoint(lx, ly, lw, lh, ax, ay) {
    // Clip (ax, ay) projectie op label-rect tot een randpunt
    const px = Math.max(lx, Math.min(ax, lx + lw));
    const py = Math.max(ly, Math.min(ay, ly + lh));
    // Als anchor binnen de rect zou liggen: pak dichtstbijzijnde rand
    const dl = px - lx;
    const dr = (lx + lw) - px;
    const dt = py - ly;
    const db = (ly + lh) - py;
    const min = Math.min(dl, dr, dt, db);
    if (ax < lx || ax > lx + lw || ay < ly || ay > ly + lh) {
        return { x: px, y: py };
    }
    if (min === dl) return { x: lx, y: py };
    if (min === dr) return { x: lx + lw, y: py };
    if (min === dt) return { x: px, y: ly };
    return { x: px, y: ly + lh };
}

function appendLine(svg, p1, p2) {
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', p1.x);
    line.setAttribute('y1', p1.y);
    line.setAttribute('x2', p2.x);
    line.setAttribute('y2', p2.y);
    svg.appendChild(line);
    return line;
}

function appendDot(svg, p) {
    const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    c.setAttribute('cx', p.x);
    c.setAttribute('cy', p.y);
    c.setAttribute('r', 3.5);
    svg.appendChild(c);
}

/**
 * Koppel drag-gedrag aan een help-label.
 *
 * Tijdens slepen wordt het label naar de muis verplaatst en het
 * label-eind van de lijn herrekend. Het anchor-eind (op het UI-element)
 * blijft staan.
 *
 * Belangrijke detail: we onderdrukken de daaropvolgende 'click' op de
 * overlay zodat een drag-actie de overlay niet sluit. We doen dat door
 * een vlag op de overlay te zetten die de click-handler checkt.
 */
function attachDragHandler(label) {
    label.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return;  // alleen linker muisknop
        const info = label._helpInfo;
        if (!info) return;
        e.preventDefault();           // voorkom tekst-selectie
        e.stopPropagation();          // klik op label gaat niet naar overlay

        const startX = e.clientX;
        const startY = e.clientY;
        const startLeft = parseFloat(label.style.left) || 0;
        const startTop  = parseFloat(label.style.top)  || 0;
        let didMove = false;

        label.classList.add('is-dragging');

        const onMove = (ev) => {
            const dx = ev.clientX - startX;
            const dy = ev.clientY - startY;
            if (!didMove && (Math.abs(dx) > 2 || Math.abs(dy) > 2)) {
                didMove = true;
            }
            const newLeft = startLeft + dx;
            const newTop  = startTop  + dy;
            label.style.left = newLeft + 'px';
            label.style.top  = newTop  + 'px';

            // Herrekend label-eind van de lijn: dichtstbijzijnde randpunt
            // op het label, vanaf de onveranderde anchor op het UI-element.
            const ep = getNearestEdgePoint(
                newLeft, newTop, info.width, info.height,
                info.anchorX, info.anchorY
            );
            if (info.line) {
                info.line.setAttribute('x2', ep.x);
                info.line.setAttribute('y2', ep.y);
            }
        };

        const onUp = () => {
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
            label.classList.remove('is-dragging');
            // Als er werkelijk gesleept is: onderdruk de volgende click
            // op de overlay zodat hij niet sluit.
            if (didMove && helpOverlay) {
                helpOverlay._suppressNextClick = true;
            }
        };

        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
    });
}

// Klik waar dan ook op de overlay → sluiten. Tenzij we net hebben gesleept
// (dan negeert deze handler één klik).
if (helpOverlay) {
    helpOverlay.addEventListener('click', () => {
        if (helpOverlay._suppressNextClick) {
            helpOverlay._suppressNextClick = false;
            return;
        }
        closeHelpOverlay();
    });
}

// Escape sluit ook
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && helpOverlay && !helpOverlay.hidden) {
        closeHelpOverlay();
    }
});

// Bij resize: herrender de labels (anders staan ze op oude posities)
window.addEventListener('resize', () => {
    if (helpOverlay && !helpOverlay.hidden) renderHelpLabels();
});


// Laad de lijst met opgaven meteen zodat docent ziet wat er is.
loadOpgavenLijst();
