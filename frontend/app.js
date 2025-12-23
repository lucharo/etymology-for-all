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
const depthMinus = document.getElementById('depth-minus');
const depthPlus = document.getElementById('depth-plus');
const depthValue = document.getElementById('depth-value');
const graphOptions = document.getElementById('graph-options');
const expandBtn = document.getElementById('expand-btn');
const graphBackdrop = document.getElementById('graph-backdrop');
const statsToggle = document.getElementById('stats-toggle');
const statsPanel = document.getElementById('stats-panel');
const statNodes = document.getElementById('stat-nodes');
const statEdges = document.getElementById('stat-edges');
const statLangs = document.getElementById('stat-langs');
const statDepth = document.getElementById('stat-depth');

let cy = null;
let fullGraphData = null; // Full graph data (max depth)
let currentSearchedWord = null;
let currentDepth = 5; // Current display depth
let graphMaxDepth = 10; // Actual max depth of current graph
const FETCH_DEPTH = 10; // Depth to fetch from API
const MIN_DEPTH = 1;
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
    if (graphOptions) graphOptions.classList.add('hidden');
    if (statsPanel) statsPanel.classList.add('hidden');
    if (statsToggle) statsToggle.classList.remove('active');
    if (directionIndicator) directionIndicator.classList.add('hidden');
    if (expandBtn) expandBtn.classList.add('hidden');
    if (cy) cy.elements().remove();
}

function showError(message) {
    loadingEl.classList.add('hidden');
    emptyState.classList.add('hidden');
    errorState.classList.remove('hidden');
    errorMessage.textContent = message;
    wordInfo.classList.add('hidden');
    if (directionIndicator) directionIndicator.classList.add('hidden');
    if (expandBtn) expandBtn.classList.add('hidden');
    minimizeGraph(); // Ensure graph is not expanded when showing error
}

function showGraph() {
    loadingEl.classList.add('hidden');
    emptyState.classList.add('hidden');
    errorState.classList.add('hidden');
    if (expandBtn) expandBtn.classList.remove('hidden');
}

// Fetch etymology data (always fetch max depth for client-side filtering)
async function fetchEtymology(word) {
    const response = await fetch(`/graph/${encodeURIComponent(word)}?depth=${FETCH_DEPTH}`);
    await handleApiResponse(response, 'etymology lookup');
    return response.json();
}

// Calculate the maximum depth in the graph
function calculateMaxGraphDepth(nodes, edges, startWord) {
    const nodeDepths = computeNodeDepths(nodes, edges, startWord);
    let maxDepth = 0;
    nodeDepths.forEach(depth => {
        if (depth > maxDepth) maxDepth = depth;
    });
    return maxDepth;
}

// Compute depth of each node from the starting word using BFS
function computeNodeDepths(nodes, edges, startWord) {
    const nodeDepths = new Map();
    const adjacency = new Map(); // node id -> [connected node ids]

    // Build adjacency list from edges (source -> target means source derives from target)
    edges.forEach(edge => {
        if (!adjacency.has(edge.source)) adjacency.set(edge.source, []);
        adjacency.get(edge.source).push(edge.target);
    });

    // Find starting node (English node matching the word)
    const startNode = nodes.find(n =>
        n.lexeme && n.lexeme.toLowerCase() === startWord.toLowerCase() && n.lang === 'en'
    );

    if (!startNode) {
        // Fallback: use first node
        nodes.forEach(n => nodeDepths.set(n.id, 0));
        return nodeDepths;
    }

    // BFS from start node
    const queue = [{ id: startNode.id, depth: 0 }];
    nodeDepths.set(startNode.id, 0);

    while (queue.length > 0) {
        const { id, depth } = queue.shift();
        const neighbors = adjacency.get(id) || [];

        neighbors.forEach(neighborId => {
            if (!nodeDepths.has(neighborId)) {
                nodeDepths.set(neighborId, depth + 1);
                queue.push({ id: neighborId, depth: depth + 1 });
            }
        });
    }

    // Handle disconnected nodes (shouldn't happen but just in case)
    nodes.forEach(n => {
        if (!nodeDepths.has(n.id)) nodeDepths.set(n.id, MAX_DEPTH);
    });

    return nodeDepths;
}

// Filter graph data by depth
function filterGraphByDepth(data, maxDepth, searchedWord) {
    const nodeDepths = computeNodeDepths(data.nodes, data.edges, searchedWord);

    // Filter nodes within depth
    const filteredNodes = data.nodes.filter(n => nodeDepths.get(n.id) <= maxDepth);
    const filteredNodeIds = new Set(filteredNodes.map(n => n.id));

    // Filter edges where both endpoints are in filtered nodes
    const filteredEdges = data.edges.filter(e =>
        filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
    );

    return { nodes: filteredNodes, edges: filteredEdges };
}

// Update depth display and buttons
function updateDepthUI() {
    if (depthValue) depthValue.textContent = currentDepth;
    if (depthMinus) depthMinus.disabled = currentDepth <= MIN_DEPTH;
    if (depthPlus) depthPlus.disabled = currentDepth >= graphMaxDepth;
}

// Fetch random word
async function fetchRandomWord() {
    const response = await fetch(`/random`);
    await handleApiResponse(response, 'random word');
    const data = await response.json();
    return data.word;
}

// Build and render graph (with optional depth filtering)
function renderGraph(data, searchedWord, filterByDepth = true) {
    if (!data.nodes || data.nodes.length === 0) {
        showError('No etymology data available for this word');
        return;
    }

    // Store full data for client-side filtering
    if (!filterByDepth || !fullGraphData || currentSearchedWord !== searchedWord) {
        fullGraphData = data;
        currentSearchedWord = searchedWord;
        // Calculate actual max depth of this graph
        graphMaxDepth = calculateMaxGraphDepth(data.nodes, data.edges, searchedWord);
        // Default to max depth for new searches
        currentDepth = graphMaxDepth;
    }

    // Apply depth filter
    const displayData = filterByDepth
        ? filterGraphByDepth(fullGraphData, currentDepth, searchedWord)
        : data;

    // Show graph options when we have a graph
    if (graphOptions) graphOptions.classList.remove('hidden');
    updateDepthUI();

    // Hide any open detail panel
    hideNodeDetail();

    // Build Cytoscape elements
    const elements = [];
    const seenLangs = new Map(); // lang code -> display name
    const langCounts = new Map(); // lang name -> count

    // Add nodes
    displayData.nodes.forEach((node) => {
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
    displayData.edges.forEach((edge) => {
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

    // Apply dagre layout (responsive direction, no animation)
    const direction = getLayoutDirection();
    cy.layout({
        name: 'dagre',
        rankDir: direction,
        nodeSep: direction === 'LR' ? 40 : 30,
        rankSep: direction === 'LR' ? 80 : 60,
        padding: 30,
        animate: false,
    }).run();

    // Fit to viewport
    cy.fit(undefined, 40);

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

    // Update stats after layout completes
    setTimeout(() => {
        const graphDepth = calculateGraphDepth(cy, searchedWord);
        updateStats(displayData.nodes.length, displayData.edges.length, langCounts.size, graphDepth);
    }, 50);
}

// Calculate graph depth using BFS from the searched word
function calculateGraphDepth(cy, startWord) {
    if (!cy || cy.nodes().length === 0) return 0;

    // Find the starting node (English node matching the word)
    const startNode = cy.nodes().filter(n => {
        const word = n.data('word');
        const lang = n.data('lang');
        return word && word.toLowerCase() === startWord.toLowerCase() && lang === 'en';
    }).first();

    if (!startNode || startNode.length === 0) return 0;

    // BFS to find maximum depth
    const visited = new Set();
    const queue = [{ node: startNode, depth: 0 }];
    let maxDepth = 0;

    while (queue.length > 0) {
        const { node, depth } = queue.shift();
        const nodeId = node.id();

        if (visited.has(nodeId)) continue;
        visited.add(nodeId);
        maxDepth = Math.max(maxDepth, depth);

        // Get connected nodes via outgoing edges (source -> target means source is newer)
        const outgoers = node.outgoers('node');
        outgoers.forEach(neighbor => {
            if (!visited.has(neighbor.id())) {
                queue.push({ node: neighbor, depth: depth + 1 });
            }
        });
    }

    return maxDepth;
}

// Update stats panel
function updateStats(nodeCount, edgeCount, langCount, depth) {
    if (statNodes) statNodes.textContent = nodeCount;
    if (statEdges) statEdges.textContent = edgeCount;
    if (statLangs) statLangs.textContent = langCount;
    if (statDepth) statDepth.textContent = depth;
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
                <span class="suggestion-word">${r.word}</span>
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

// Depth +/- button event listeners
function changeDepth(delta) {
    const newDepth = currentDepth + delta;
    if (newDepth < MIN_DEPTH || newDepth > graphMaxDepth) return;

    currentDepth = newDepth;
    updateDepthUI();

    // Re-render with new depth (client-side, no fetch)
    if (fullGraphData && currentSearchedWord) {
        renderGraph(fullGraphData, currentSearchedWord, true);
    }
}

if (depthMinus) {
    depthMinus.addEventListener('click', () => changeDepth(-1));
}
if (depthPlus) {
    depthPlus.addEventListener('click', () => changeDepth(1));
}

// Stats toggle
if (statsToggle && statsPanel) {
    statsToggle.addEventListener('click', () => {
        const isHidden = statsPanel.classList.toggle('hidden');
        statsToggle.classList.toggle('active', !isHidden);
    });
}

// Expand/minimize graph functionality
let isExpanded = false;

function toggleExpandGraph() {
    isExpanded = !isExpanded;
    graphContainer.classList.toggle('expanded', isExpanded);
    if (graphBackdrop) graphBackdrop.classList.toggle('visible', isExpanded);

    // After CSS transition, resize and animate fit
    setTimeout(() => {
        if (cy) {
            cy.resize();
            cy.animate({
                fit: { eles: cy.elements(), padding: 40 }
            }, { duration: 200, easing: 'ease-out' });
        }
    }, 320);
}

function minimizeGraph() {
    if (isExpanded) {
        isExpanded = false;
        graphContainer.classList.remove('expanded');
        if (graphBackdrop) graphBackdrop.classList.remove('visible');

        // After CSS transition, resize and animate fit
        setTimeout(() => {
            if (cy) {
                cy.resize();
                cy.animate({
                    fit: { eles: cy.elements(), padding: 40 }
                }, { duration: 200, easing: 'ease-out' });
            }
        }, 320);
    }
}

// Expand button click handler
if (expandBtn) {
    expandBtn.addEventListener('click', toggleExpandGraph);
}

// Backdrop click to minimize
if (graphBackdrop) {
    graphBackdrop.addEventListener('click', minimizeGraph);
}

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

    // Escape key handler (modal and graph expand)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            // First priority: close modal if open
            if (aboutModal && !aboutModal.classList.contains('hidden')) {
                closeAboutModal();
            }
            // Second priority: minimize expanded graph
            else if (isExpanded) {
                minimizeGraph();
            }
        }
    });
});
