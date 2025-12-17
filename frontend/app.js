/**
 * Etymology Graph Explorer
 * Interactive visualization of word origins using Cytoscape.js
 */

// Language family color mapping
const LANG_COLORS = {
    // Modern languages
    en: '#0284c7',
    fr: '#0284c7',
    de: '#0284c7',
    es: '#0284c7',
    it: '#0284c7',
    pt: '#0284c7',
    nl: '#0284c7',
    sv: '#0284c7',
    da: '#0284c7',
    no: '#0284c7',

    // Latin and Romance
    la: '#7c3aed',
    lat: '#7c3aed',
    'old-french': '#7c3aed',
    'middle-french': '#7c3aed',
    'old-occitan': '#7c3aed',
    'vulgar-latin': '#7c3aed',

    // Greek
    grc: '#059669',
    'ancient-greek': '#059669',
    'greek': '#059669',
    el: '#059669',

    // Germanic
    'proto-germanic': '#ea580c',
    'old-english': '#ea580c',
    'middle-english': '#ea580c',
    'old-high-german': '#ea580c',
    'middle-high-german': '#ea580c',
    'old-norse': '#ea580c',
    'old-saxon': '#ea580c',
    ang: '#ea580c',
    enm: '#ea580c',
    goh: '#ea580c',
    gmh: '#ea580c',
    non: '#ea580c',
    osx: '#ea580c',
    gem: '#ea580c',

    // Proto-Indo-European
    'proto-indo-european': '#dc2626',
    ine: '#dc2626',
    'pie': '#dc2626',

    // Semitic
    ar: '#d97706',
    he: '#d97706',
    'arabic': '#d97706',
    'hebrew': '#d97706',
    'proto-semitic': '#d97706',
};

const DEFAULT_COLOR = '#64748b';

// Human-readable language names
const LANG_NAMES = {
    en: 'English',
    fr: 'French',
    de: 'German',
    es: 'Spanish',
    it: 'Italian',
    pt: 'Portuguese',
    nl: 'Dutch',
    la: 'Latin',
    lat: 'Latin',
    grc: 'Ancient Greek',
    'ancient-greek': 'Ancient Greek',
    el: 'Greek',
    'proto-germanic': 'Proto-Germanic',
    'proto-indo-european': 'Proto-Indo-European',
    'old-english': 'Old English',
    'middle-english': 'Middle English',
    'old-french': 'Old French',
    'middle-french': 'Middle French',
    'old-high-german': 'Old High German',
    'old-norse': 'Old Norse',
    ar: 'Arabic',
    he: 'Hebrew',
    ang: 'Old English',
    enm: 'Middle English',
    gem: 'Proto-Germanic',
    ine: 'Proto-Indo-European',
};

function getLangColor(lang) {
    if (!lang) return DEFAULT_COLOR;
    const normalized = lang.toLowerCase().replace(/_/g, '-');
    return LANG_COLORS[normalized] || DEFAULT_COLOR;
}

function getLangName(lang) {
    if (!lang) return 'Unknown';
    const normalized = lang.toLowerCase().replace(/_/g, '-');
    return LANG_NAMES[normalized] || lang;
}

// DOM elements
const wordInput = document.getElementById('word-input');
const searchBtn = document.getElementById('search-btn');
const randomBtn = document.getElementById('random-btn');
const graphContainer = document.getElementById('graph-container');
const cyContainer = document.getElementById('cy');
const loadingEl = document.getElementById('loading');
const emptyState = document.getElementById('empty-state');
const errorState = document.getElementById('error-state');
const errorMessage = document.getElementById('error-message');
const wordInfo = document.getElementById('word-info');
const currentWord = document.getElementById('current-word');
const legend = document.getElementById('legend');

let cy = null;

// Initialize Cytoscape
function initCytoscape() {
    cy = cytoscape({
        container: cyContainer,
        style: [
            {
                selector: 'node',
                style: {
                    'label': 'data(label)',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'background-color': 'data(color)',
                    'color': '#fff',
                    'font-size': '12px',
                    'font-weight': '500',
                    'text-outline-color': 'data(color)',
                    'text-outline-width': '2px',
                    'width': 'label',
                    'height': 'label',
                    'padding': '12px',
                    'shape': 'round-rectangle',
                    'border-width': '2px',
                    'border-color': 'data(color)',
                    'border-opacity': 0.3,
                },
            },
            {
                selector: 'node:selected',
                style: {
                    'border-width': '3px',
                    'border-color': '#1c1917',
                    'border-opacity': 1,
                },
            },
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': '#d6d3d1',
                    'target-arrow-color': '#d6d3d1',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'arrow-scale': 1.2,
                },
            },
            {
                selector: 'edge:selected',
                style: {
                    'line-color': '#78716c',
                    'target-arrow-color': '#78716c',
                },
            },
        ],
        layout: { name: 'preset' },
        minZoom: 0.3,
        maxZoom: 3,
        wheelSensitivity: 0.3,
    });

    // Add tooltip on node hover
    cy.on('mouseover', 'node', (e) => {
        const node = e.target;
        cyContainer.title = `${node.data('label')} (${getLangName(node.data('lang'))})`;
    });

    cy.on('mouseout', 'node', () => {
        cyContainer.title = '';
    });
}

// Show/hide states
function showLoading() {
    loadingEl.classList.remove('hidden');
    emptyState.classList.add('hidden');
    errorState.classList.add('hidden');
    wordInfo.classList.add('hidden');
    if (cy) cy.elements().remove();
}

function showError(message) {
    loadingEl.classList.add('hidden');
    emptyState.classList.add('hidden');
    errorState.classList.remove('hidden');
    errorMessage.textContent = message;
    wordInfo.classList.add('hidden');
}

function showGraph() {
    loadingEl.classList.add('hidden');
    emptyState.classList.add('hidden');
    errorState.classList.add('hidden');
}

// Fetch etymology data
async function fetchEtymology(word) {
    const response = await fetch(`/graph/${encodeURIComponent(word)}`);
    if (!response.ok) {
        if (response.status === 404) {
            throw new Error(`"${word}" not found in the database`);
        }
        throw new Error('Failed to fetch etymology data');
    }
    return response.json();
}

// Fetch random word
async function fetchRandomWord() {
    const response = await fetch('/random');
    if (!response.ok) {
        throw new Error('Failed to fetch random word');
    }
    const data = await response.json();
    return data.word;
}

// Build and render graph
function renderGraph(data, searchedWord) {
    if (!data.nodes || data.nodes.length === 0) {
        showError('No etymology data available for this word');
        return;
    }

    // Build Cytoscape elements
    const elements = [];
    const seenLangs = new Set();

    // Add nodes
    data.nodes.forEach((node) => {
        const color = getLangColor(node.lang);
        seenLangs.add(node.lang);
        elements.push({
            group: 'nodes',
            data: {
                id: node.id,
                label: node.id,
                lang: node.lang,
                color: color,
            },
        });
    });

    // Add edges
    data.edges.forEach((edge) => {
        elements.push({
            group: 'edges',
            data: {
                id: `${edge.source}-${edge.target}`,
                source: edge.source,
                target: edge.target,
            },
        });
    });

    // Update Cytoscape
    cy.elements().remove();
    cy.add(elements);

    // Apply dagre layout (hierarchical, top-to-bottom)
    cy.layout({
        name: 'dagre',
        rankDir: 'TB',
        nodeSep: 60,
        rankSep: 80,
        padding: 40,
        animate: true,
        animationDuration: 500,
        animationEasing: 'ease-out',
    }).run();

    // Fit to viewport
    setTimeout(() => {
        cy.fit(undefined, 40);
    }, 550);

    // Update word info
    currentWord.textContent = searchedWord;
    updateLegend(seenLangs);
    wordInfo.classList.remove('hidden');
    showGraph();
}

// Update legend with languages in current graph
function updateLegend(langs) {
    legend.innerHTML = '';
    const sortedLangs = Array.from(langs).sort();

    sortedLangs.forEach((lang) => {
        const item = document.createElement('div');
        item.className = 'legend-item';

        const dot = document.createElement('span');
        dot.className = 'legend-dot';
        dot.style.backgroundColor = getLangColor(lang);

        const label = document.createElement('span');
        label.textContent = getLangName(lang);

        item.appendChild(dot);
        item.appendChild(label);
        legend.appendChild(item);
    });
}

// Search handler
async function handleSearch() {
    const word = wordInput.value.trim();
    if (!word) return;

    showLoading();

    try {
        const data = await fetchEtymology(word);
        renderGraph(data, word);
    } catch (err) {
        showError(err.message);
    }
}

// Random word handler
async function handleRandom() {
    showLoading();

    try {
        const word = await fetchRandomWord();
        if (!word) {
            showError('Could not get a random word');
            return;
        }
        wordInput.value = word;
        const data = await fetchEtymology(word);
        renderGraph(data, word);
    } catch (err) {
        showError(err.message);
    }
}

// Event listeners
searchBtn.addEventListener('click', handleSearch);
randomBtn.addEventListener('click', handleRandom);

wordInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        handleSearch();
    }
});

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    initCytoscape();
});
