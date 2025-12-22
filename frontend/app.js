/**
 * Etymology Graph Explorer
 * Interactive visualization of word origins using Cytoscape.js
 */

// Human-readable language names (fallback when not provided by API)
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

function getLangName(lang) {
    if (!lang) return 'Unknown';
    const normalized = lang.toLowerCase().replace(/_/g, '-');
    return LANG_NAMES[normalized] || lang;
}

// Truncate text to a maximum length
function truncate(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.slice(0, maxLength).trim() + '…';
}

// Handle API errors with user-friendly messages
async function handleApiResponse(response, context = 'request') {
    if (response.ok) return response;

    if (response.status === 429) {
        const retryAfter = response.headers.get('Retry-After') || '60';
        throw new Error(`Too many requests. Please wait ${retryAfter} seconds and try again.`);
    }
    if (response.status === 404) {
        throw new Error(`Word not found in the database`);
    }
    if (response.status >= 500) {
        throw new Error(`Server is temporarily unavailable. Please try again in a moment.`);
    }
    throw new Error(`Failed to complete ${context}`);
}

// Build display label for node
function buildNodeLabel(node) {
    const langName = node.lang_name || getLangName(node.lang);
    const displayWord = node.lexeme || node.id;
    // Simple format for debugging: word (language)
    return displayWord + '\n(' + langName.toLowerCase() + ')';
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
const langBreakdown = document.getElementById('lang-breakdown');
const nodeDetail = document.getElementById('node-detail');
const detailWord = document.getElementById('detail-word');
const detailLang = document.getElementById('detail-lang');
const detailFamily = document.getElementById('detail-family');
const detailSense = document.getElementById('detail-sense');
const detailClose = document.getElementById('detail-close');
const suggestions = document.getElementById('suggestions');
const directionIndicator = document.getElementById('direction-indicator');

let cy = null;
let searchTimeout = null;
let selectedSuggestionIndex = -1;

// Get layout direction based on viewport
function getLayoutDirection() {
    return window.innerWidth > window.innerHeight ? 'LR' : 'TB';
}

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
                    'text-wrap': 'wrap',
                    'text-max-width': '140px',
                    'background-color': '#f8fafc',
                    'color': '#1c1917',
                    'font-size': '13px',
                    'font-family': 'system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
                    'width': 'label',
                    'height': 'label',
                    'padding': '12px',
                    'shape': 'round-rectangle',
                    'border-width': '1px',
                    'border-color': '#cbd5e1',
                },
            },
            {
                selector: 'node:selected',
                style: {
                    'border-width': '2px',
                    'border-color': '#0284c7',
                    'background-color': '#f0f9ff',
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

    // Show detail panel on node click
    cy.on('tap', 'node', (e) => {
        const node = e.target;
        showNodeDetail(node.data());
    });

    // Hide detail when clicking background
    cy.on('tap', (e) => {
        if (e.target === cy) {
            hideNodeDetail();
        }
    });

    // Add tooltip on node hover
    cy.on('mouseover', 'node', (e) => {
        const node = e.target;
        const sense = node.data('sense');
        const langName = node.data('langName') || getLangName(node.data('lang'));
        let tip = `${node.data('word')} (${langName})`;
        if (sense) tip += `\n"${sense}"`;
        cyContainer.title = tip;
        cyContainer.style.cursor = 'pointer';
    });

    cy.on('mouseout', 'node', () => {
        cyContainer.title = '';
        cyContainer.style.cursor = 'default';
    });
}

// Show node detail panel
function showNodeDetail(data) {
    if (!nodeDetail || !detailWord || !detailLang) return;

    detailWord.textContent = data.word;
    detailLang.textContent = data.langName || getLangName(data.lang);

    // Show family and branch if available
    if (detailFamily && detailFamily.parentElement) {
        if (data.family) {
            detailFamily.textContent = `${data.family}${data.branch ? ' → ' + data.branch : ''}`;
            detailFamily.parentElement.classList.remove('hidden');
        } else {
            detailFamily.parentElement.classList.add('hidden');
        }
    }

    // Show sense/definition if available (truncate long definitions)
    if (detailSense && detailSense.parentElement) {
        if (data.sense) {
            detailSense.textContent = truncate(data.sense, 150);
            detailSense.parentElement.classList.remove('hidden');
        } else {
            detailSense.parentElement.classList.add('hidden');
        }
    }

    nodeDetail.classList.remove('hidden');
}

// Hide node detail panel
function hideNodeDetail() {
    if (nodeDetail) {
        nodeDetail.classList.add('hidden');
    }
}

// Show/hide states
function showLoading() {
    loadingEl.classList.remove('hidden');
    emptyState.classList.add('hidden');
    errorState.classList.add('hidden');
    wordInfo.classList.add('hidden');
    if (directionIndicator) directionIndicator.classList.add('hidden');
    if (cy) cy.elements().remove();
}

function showError(message) {
    loadingEl.classList.add('hidden');
    emptyState.classList.add('hidden');
    errorState.classList.remove('hidden');
    errorMessage.textContent = message;
    wordInfo.classList.add('hidden');
    if (directionIndicator) directionIndicator.classList.add('hidden');
}

function showGraph() {
    loadingEl.classList.add('hidden');
    emptyState.classList.add('hidden');
    errorState.classList.add('hidden');
}

// Fetch etymology data
async function fetchEtymology(word) {
    const response = await fetch(`/graph/${encodeURIComponent(word)}`);
    await handleApiResponse(response, 'etymology lookup');
    return response.json();
}

// Fetch random word
async function fetchRandomWord() {
    const response = await fetch(`/random`);
    await handleApiResponse(response, 'random word');
    const data = await response.json();
    return data.word;
}

// Build and render graph
function renderGraph(data, searchedWord) {
    if (!data.nodes || data.nodes.length === 0) {
        showError('No etymology data available for this word');
        return;
    }

    // Hide any open detail panel
    hideNodeDetail();

    // Build Cytoscape elements
    const elements = [];
    const seenLangs = new Map(); // lang code -> display name
    const langCounts = new Map(); // lang name -> count

    // Add nodes
    data.nodes.forEach((node) => {
        const langName = node.lang_name || getLangName(node.lang);
        const displayWord = node.lexeme || node.id;
        seenLangs.set(node.lang, langName);
        langCounts.set(langName, (langCounts.get(langName) || 0) + 1);

        elements.push({
            group: 'nodes',
            data: {
                id: node.id,  // Unique ID (lexeme|lang)
                word: displayWord,  // Display word
                label: buildNodeLabel(node),
                lang: node.lang,
                langName: langName,
                sense: node.sense || null,
                hasSense: !!node.sense,  // Flag for CSS selector
                family: node.family || null,
                branch: node.branch || null,
            },
        });
    });

    // Add edges (filter out self-loops where source equals target)
    data.edges.forEach((edge) => {
        if (edge.source === edge.target) return; // Skip self-loops
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

    // Apply dagre layout (responsive direction)
    const direction = getLayoutDirection();
    cy.layout({
        name: 'dagre',
        rankDir: direction,
        nodeSep: direction === 'LR' ? 40 : 30,
        rankSep: direction === 'LR' ? 80 : 60,
        padding: 30,
        animate: true,
        animationDuration: 500,
        animationEasing: 'ease-out',
    }).run();

    // Fit to viewport
    setTimeout(() => {
        cy.fit(undefined, 40);
    }, 550);

    // Update direction indicator
    if (directionIndicator) {
        directionIndicator.classList.remove('hidden', 'vertical');
        const arrow = directionIndicator.querySelector('.direction-arrow');
        if (direction === 'TB') {
            directionIndicator.classList.add('vertical');
            if (arrow) arrow.textContent = '↓';
        } else {
            if (arrow) arrow.textContent = '→';
        }
    }

    // Update word info
    currentWord.textContent = searchedWord;
    updateInfoSummary(seenLangs, langCounts);
    wordInfo.classList.remove('hidden');
    showGraph();
}

// Update info summary with language breakdown
function updateInfoSummary(langMap, langCounts) {
    if (!langBreakdown) return;

    // Sort by count descending, then by name
    const sorted = Array.from(langCounts.entries()).sort((a, b) => {
        if (b[1] !== a[1]) return b[1] - a[1];
        return a[0].localeCompare(b[0]);
    });

    langBreakdown.innerHTML = sorted
        .map(([langName, count]) => `
            <span class="lang-chip">
                <span class="lang-chip-name">${langName}</span>
                <span class="lang-chip-count">${count}</span>
            </span>
        `)
        .join('');
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

// Autocomplete functions
async function fetchSuggestions(query) {
    if (query.length < 2) {
        hideSuggestions();
        return;
    }

    try {
        const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
        if (response.status === 429) {
            // Silently ignore rate limits for autocomplete (non-critical)
            return;
        }
        if (!response.ok) return;
        const data = await response.json();
        showSuggestions(data.results);
    } catch (err) {
        // Silently fail for autocomplete - don't disrupt typing
        console.error('Search error:', err);
    }
}

function showSuggestions(results) {
    if (!suggestions || results.length === 0) {
        hideSuggestions();
        return;
    }

    selectedSuggestionIndex = -1;
    suggestions.innerHTML = results
        .map(
            (r, i) => `
            <div class="suggestion-item" data-index="${i}" data-word="${r.word}">
                <div class="suggestion-main">
                    <span class="suggestion-word">${r.word}</span>
                    ${r.ancestors > 0 ? `<span class="suggestion-ancestors">${r.ancestors} ${r.ancestors === 1 ? 'link' : 'links'}</span>` : '<span class="suggestion-ancestors single">no etymology</span>'}
                </div>
                ${r.sense ? `<div class="suggestion-sense">${truncate(r.sense, 60)}</div>` : ''}
            </div>
        `
        )
        .join('');

    suggestions.classList.remove('hidden');

    // Add click handlers
    suggestions.querySelectorAll('.suggestion-item').forEach((item) => {
        item.addEventListener('click', () => {
            selectSuggestion(item.dataset.word);
        });
    });
}

function hideSuggestions() {
    if (suggestions) {
        suggestions.classList.add('hidden');
        suggestions.innerHTML = '';
    }
    selectedSuggestionIndex = -1;
}

function selectSuggestion(word) {
    wordInput.value = word;
    hideSuggestions();
    handleSearch();
}

function navigateSuggestions(direction) {
    const items = suggestions.querySelectorAll('.suggestion-item');
    if (items.length === 0) return;

    // Remove previous selection
    items.forEach((item) => item.classList.remove('selected'));

    // Update index
    selectedSuggestionIndex += direction;
    if (selectedSuggestionIndex < 0) selectedSuggestionIndex = items.length - 1;
    if (selectedSuggestionIndex >= items.length) selectedSuggestionIndex = 0;

    // Apply selection
    items[selectedSuggestionIndex].classList.add('selected');
    items[selectedSuggestionIndex].scrollIntoView({ block: 'nearest' });
}

// Event listeners
searchBtn.addEventListener('click', handleSearch);
randomBtn.addEventListener('click', handleRandom);

// Input event for autocomplete
wordInput.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        fetchSuggestions(e.target.value.trim());
    }, 150); // Debounce 150ms
});

wordInput.addEventListener('keydown', (e) => {
    const isOpen = suggestions && !suggestions.classList.contains('hidden');

    if (e.key === 'Enter') {
        if (isOpen && selectedSuggestionIndex >= 0) {
            const items = suggestions.querySelectorAll('.suggestion-item');
            if (items[selectedSuggestionIndex]) {
                selectSuggestion(items[selectedSuggestionIndex].dataset.word);
            }
        } else {
            hideSuggestions();
            handleSearch();
        }
        e.preventDefault();
    } else if (e.key === 'ArrowDown' && isOpen) {
        navigateSuggestions(1);
        e.preventDefault();
    } else if (e.key === 'ArrowUp' && isOpen) {
        navigateSuggestions(-1);
        e.preventDefault();
    } else if (e.key === 'Escape') {
        hideSuggestions();
    }
});

// Hide suggestions when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-wrapper')) {
        hideSuggestions();
    }
});

// Modal functionality
const aboutBtn = document.getElementById('about-btn');
const aboutModal = document.getElementById('about-modal');
const aboutClose = document.getElementById('about-close');
const modalBackdrop = aboutModal?.querySelector('.modal-backdrop');
const modalTabs = aboutModal?.querySelectorAll('.modal-tab');

function openAboutModal() {
    if (aboutModal) aboutModal.classList.remove('hidden');
}

function closeAboutModal() {
    if (aboutModal) aboutModal.classList.add('hidden');
}

function switchTab(tabName) {
    // Update tab buttons
    modalTabs?.forEach((tab) => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    // Update tab content
    document.querySelectorAll('.tab-content').forEach((content) => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    initCytoscape();

    // Close button for detail panel
    if (detailClose) {
        detailClose.addEventListener('click', hideNodeDetail);
    }

    // About modal
    if (aboutBtn) aboutBtn.addEventListener('click', openAboutModal);
    if (aboutClose) aboutClose.addEventListener('click', closeAboutModal);
    if (modalBackdrop) modalBackdrop.addEventListener('click', closeAboutModal);

    // Tab switching
    modalTabs?.forEach((tab) => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Close modal on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && aboutModal && !aboutModal.classList.contains('hidden')) {
            closeAboutModal();
        }
    });
});
