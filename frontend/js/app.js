/**
 * Etymology Graph Explorer - Main Application
 * Interactive visualization of word origins using Cytoscape.js
 */

import { getLangName, checkNoEtymology } from './utils.js';
import {
    initCytoscape,
    getCy,
    filterGraphByDepth,
    filterCompoundEdges,
    calculateMaxGraphDepth,
    calculateGraphDepth,
    renderGraphElements,
    setShowLinkTypes,
} from './graph.js';
import {
    fetchEtymology,
    fetchRandomWord,
    fetchSuggestions,
    hideSuggestions,
    navigateSuggestions,
    getSelectedSuggestion,
} from './search.js';
import {
    showNodeDetail,
    hideNodeDetail,
    showLoading,
    showError,
    showGraph,
    updateStats,
    updateInfoSummary,
    updateDepthUI,
    createExpandHandlers,
    setupModal,
} from './ui.js';
import { buildTree, renderTreeHTML } from './tree.js';

// DOM elements
const elements = {
    wordInput: document.getElementById('word-input'),
    searchBtn: document.getElementById('search-btn'),
    randomBtn: document.getElementById('random-btn'),
    includeCompound: document.getElementById('include-compound'),
    graphContainer: document.getElementById('graph-container'),
    cyContainer: document.getElementById('cy'),
    loadingEl: document.getElementById('loading'),
    emptyState: document.getElementById('empty-state'),
    errorState: document.getElementById('error-state'),
    errorMessage: document.getElementById('error-message'),
    wordInfo: document.getElementById('word-info'),
    currentWord: document.getElementById('current-word'),
    langBreakdown: document.getElementById('lang-breakdown'),
    nodeDetail: document.getElementById('node-detail'),
    detailWord: document.getElementById('detail-word'),
    detailLang: document.getElementById('detail-lang'),
    detailFamily: document.getElementById('detail-family'),
    detailSense: document.getElementById('detail-sense'),
    detailClose: document.getElementById('detail-close'),
    suggestions: document.getElementById('suggestions'),
    graphLegend: document.getElementById('graph-legend'),
    directionIndicator: document.getElementById('direction-indicator'),
    depthMinus: document.getElementById('depth-minus'),
    depthPlus: document.getElementById('depth-plus'),
    depthValue: document.getElementById('depth-value'),
    graphOptions: document.getElementById('graph-options'),
    expandBtn: document.getElementById('expand-btn'),
    graphBackdrop: document.getElementById('graph-backdrop'),
    statsToggle: document.getElementById('stats-toggle'),
    statsPanel: document.getElementById('stats-panel'),
    statNodes: document.getElementById('stat-nodes'),
    statEdges: document.getElementById('stat-edges'),
    statLangs: document.getElementById('stat-langs'),
    statDepth: document.getElementById('stat-depth'),
    viewGraphBtn: document.getElementById('view-graph'),
    viewTreeBtn: document.getElementById('view-tree'),
    treeView: document.getElementById('tree-view'),
};

// State
let fullGraphData = null;
let currentSearchedWord = null;
let currentDepth = 5;
let graphMaxDepth = 10;
const MIN_DEPTH = 1;
let searchTimeout = null;
let serverReady = false;
let graphAvailable = false;
let currentView = 'graph'; // 'graph' or 'tree'

// Server health check with retry (HF Spaces sleep after inactivity)
async function checkServerHealth(maxWaitMs = 120000) {
    const startTime = Date.now();
    const emptyState = document.getElementById('empty-state');
    const originalText = emptyState?.querySelector('p')?.textContent;
    let attempt = 0;

    while (Date.now() - startTime < maxWaitMs) {
        try {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 5000);

            const response = await fetch('/health', { signal: controller.signal });
            clearTimeout(timeout);

            if (response.ok) {
                // Server is ready
                if (emptyState?.querySelector('p')) {
                    emptyState.querySelector('p').textContent = originalText || 'Search for a word to see its etymological journey.';
                }
                serverReady = true;
                return true;
            }
        } catch (e) {
            // Server not ready yet
        }

        attempt++;
        const elapsed = Math.round((Date.now() - startTime) / 1000);
        const remaining = Math.round((maxWaitMs - (Date.now() - startTime)) / 1000);

        if (emptyState?.querySelector('p')) {
            emptyState.querySelector('p').innerHTML =
                `<span style="color: var(--accent);">Server waking up...</span><br>` +
                `<small style="color: var(--text-muted);">Free tier sleeps after inactivity. Please wait (~${remaining}s remaining)</small>`;
        }

        // Wait before retry (1s, then 2s intervals)
        await new Promise(r => setTimeout(r, attempt === 1 ? 1000 : 2000));
    }

    // Timeout reached
    if (emptyState?.querySelector('p')) {
        emptyState.querySelector('p').innerHTML =
            `<span style="color: var(--error);">Server unavailable</span><br>` +
            `<small>Please try refreshing the page.</small>`;
    }
    return false;
}

// Expand handlers
const { toggleExpandGraph, minimizeGraph, getIsExpanded } = createExpandHandlers(
    elements.graphContainer,
    elements.graphBackdrop
);

// View toggle
function setView(view) {
    currentView = view;

    // Update button states
    if (elements.viewGraphBtn) {
        elements.viewGraphBtn.classList.toggle('active', view === 'graph');
    }
    if (elements.viewTreeBtn) {
        elements.viewTreeBtn.classList.toggle('active', view === 'tree');
    }

    // Toggle visibility
    if (view === 'tree') {
        elements.cyContainer.classList.add('hidden');
        elements.treeView.classList.remove('hidden');
        if (elements.graphLegend) {
            elements.graphLegend.classList.add('hidden');
        }
        renderTreeView();
    } else {
        elements.treeView.classList.add('hidden');
        elements.cyContainer.classList.remove('hidden');
        // Re-render graph fully (may have been skipped while in tree view)
        if (fullGraphData && currentSearchedWord) {
            renderGraph(fullGraphData, currentSearchedWord, true);
        }
    }
}

// Render tree view
function renderTreeView() {
    if (!fullGraphData || !currentSearchedWord) {
        elements.treeView.innerHTML = '<div class="tree-empty">Search for a word to see its etymology tree</div>';
        return;
    }

    // Apply filters: depth first, then compound
    const includeCompound = elements.includeCompound?.checked ?? true;
    let displayData = filterGraphByDepth(fullGraphData, currentDepth, currentSearchedWord);
    displayData = filterCompoundEdges(displayData, includeCompound, currentSearchedWord);

    const tree = buildTree(displayData.nodes, displayData.edges, currentSearchedWord, currentDepth);
    const treeHTML = renderTreeHTML(tree);
    elements.treeView.innerHTML = treeHTML;

    // Add click handlers for tree nodes
    elements.treeView.querySelectorAll('.tree-node').forEach(node => {
        node.addEventListener('click', () => {
            const data = {
                word: node.dataset.lexeme,
                lang: node.dataset.lang,
                langName: node.dataset.langName,
                sense: node.dataset.sense || null,
                family: node.dataset.family || null,
                branch: node.dataset.branch || null,
            };
            showNodeDetail(data, elements);
        });
    });
}

// Render graph with current depth
function renderGraph(data, searchedWord, filterByDepth = true) {
    // Check for no-etymology response
    const noEtym = checkNoEtymology(data);
    if (noEtym) {
        const word = noEtym.lexeme || searchedWord;
        showError(
            `'${word}' was found but has no etymology data in EtymDB`,
            elements,
            minimizeGraph,
            { wiktionaryWord: word, searchedWord: word }
        );
        return;
    }

    if (!data.nodes || data.nodes.length === 0) {
        showError('No etymology data available for this word', elements, minimizeGraph, { searchedWord });
        return;
    }

    if (!filterByDepth || !fullGraphData || currentSearchedWord !== searchedWord) {
        fullGraphData = data;
        currentSearchedWord = searchedWord;
        graphMaxDepth = calculateMaxGraphDepth(data.nodes, data.edges, searchedWord);
        currentDepth = graphMaxDepth;
    }

    // Apply filters: depth first, then compound
    const includeCompound = elements.includeCompound?.checked ?? true;
    let displayData = filterByDepth
        ? filterGraphByDepth(fullGraphData, currentDepth, searchedWord)
        : data;
    displayData = filterCompoundEdges(displayData, includeCompound, searchedWord);

    if (elements.graphOptions) elements.graphOptions.classList.remove('hidden');
    updateDepthUI(currentDepth, graphMaxDepth, elements);

    hideNodeDetail(elements.nodeDetail);

    elements.currentWord.textContent = searchedWord;
    elements.wordInfo.classList.remove('hidden');
    showGraph(elements);

    if (currentView === 'tree') {
        // In tree view, only render tree — skip expensive graph layout
        renderTreeView();
    } else {
        // Render graph and legend
        const { seenLangs, langCounts, langCodes } = renderGraphElements(displayData, elements.graphLegend, elements.directionIndicator);
        updateInfoSummary(langCounts, langCodes, elements.langBreakdown);

        // Re-fit after browser has reflowed layout (double-RAF ensures reflow is complete)
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                const cy = getCy();
                if (cy) {
                    cy.resize();
                    cy.fit(undefined, 40);
                }
            });
        });

        setTimeout(() => {
            const graphDepth = calculateGraphDepth(searchedWord);
            updateStats(displayData.nodes.length, displayData.edges.length, langCounts.size, graphDepth, elements);
        }, 50);
    }
}

// Search handler
async function handleSearch() {
    const word = elements.wordInput.value.trim();
    if (!word) return;

    if (!graphAvailable) {
        showError('Graph engine is not available. Try refreshing the page.', elements, minimizeGraph);
        return;
    }

    showLoading(elements);

    try {
        const data = await fetchEtymology(word);
        renderGraph(data, word);
    } catch (err) {
        showError(err.message, elements, minimizeGraph, { searchedWord: word });
    }
}

// Random word handler
async function handleRandom() {
    if (!graphAvailable) {
        showError('Graph engine is not available. Try refreshing the page.', elements, minimizeGraph);
        return;
    }

    showLoading(elements);

    try {
        const includeCompound = elements.includeCompound?.checked ?? true;
        const word = await fetchRandomWord(includeCompound);
        if (!word) {
            showError('Could not get a random word', elements, minimizeGraph);
            return;
        }
        elements.wordInput.value = word;
        const data = await fetchEtymology(word);
        renderGraph(data, word);
    } catch (err) {
        showError(err.message, elements, minimizeGraph, { searchedWord: elements.wordInput.value.trim() });
    }
}

// Depth change
function changeDepth(delta) {
    const newDepth = currentDepth + delta;
    if (newDepth < MIN_DEPTH || newDepth > graphMaxDepth) return;

    currentDepth = newDepth;
    updateDepthUI(currentDepth, graphMaxDepth, elements);

    if (fullGraphData && currentSearchedWord) {
        renderGraph(fullGraphData, currentSearchedWord, true);
    }
}

// Suggestion selection
function selectSuggestion(word) {
    elements.wordInput.value = word;
    hideSuggestions(elements.suggestions);
    handleSearch();
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', async () => {
    // Check server health first (HF Spaces may be sleeping)
    checkServerHealth(120000); // 2 minutes max wait, runs in background

    // Initialize Cytoscape (wrapped so UI still works if CDN scripts failed to load)
    try {
        initCytoscape(
            elements.cyContainer,
            (data) => showNodeDetail(data, elements),
            () => hideNodeDetail(elements.nodeDetail),
            (node, container) => {
                const sense = node.data('sense');
                const langName = node.data('langName') || getLangName(node.data('lang'));
                let tip = `${node.data('word')} (${langName})`;
                if (sense) tip += `\n"${sense}"`;
                container.title = tip;
                container.style.cursor = 'pointer';
            },
            (container) => {
                container.title = '';
                container.style.cursor = 'default';
            }
        );
        graphAvailable = true;
    } catch (e) {
        console.error('Failed to initialize graph engine:', e);
        showError(
            'Graph engine failed to load. Try refreshing the page.',
            elements,
            minimizeGraph
        );
    }

    // Detail panel close
    if (elements.detailClose) {
        elements.detailClose.addEventListener('click', () => hideNodeDetail(elements.nodeDetail));
    }

    // Search buttons
    elements.searchBtn.addEventListener('click', handleSearch);
    elements.randomBtn.addEventListener('click', handleRandom);

    // Depth buttons
    if (elements.depthMinus) {
        elements.depthMinus.addEventListener('click', () => changeDepth(-1));
    }
    if (elements.depthPlus) {
        elements.depthPlus.addEventListener('click', () => changeDepth(1));
    }

    // Compound filter checkbox - re-renders graph when toggled
    if (elements.includeCompound) {
        elements.includeCompound.addEventListener('change', () => {
            const mobileCompound = document.getElementById('mobile-include-compound');
            if (mobileCompound) mobileCompound.checked = elements.includeCompound.checked;
            if (fullGraphData && currentSearchedWord) {
                renderGraph(fullGraphData, currentSearchedWord, true);
            }
        });
    }

    // Stats toggle
    if (elements.statsToggle && elements.statsPanel) {
        elements.statsToggle.addEventListener('click', () => {
            const isHidden = elements.statsPanel.classList.toggle('hidden');
            elements.statsToggle.classList.toggle('active', !isHidden);
        });
    }

    // View toggle buttons
    if (elements.viewGraphBtn) {
        elements.viewGraphBtn.addEventListener('click', () => setView('graph'));
    }
    if (elements.viewTreeBtn) {
        elements.viewTreeBtn.addEventListener('click', () => setView('tree'));
    }

    // Expand button
    if (elements.expandBtn) {
        elements.expandBtn.addEventListener('click', toggleExpandGraph);
    }
    if (elements.graphBackdrop) {
        elements.graphBackdrop.addEventListener('click', minimizeGraph);
    }

    // Autocomplete input
    elements.wordInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            fetchSuggestions(e.target.value.trim(), elements.suggestions, selectSuggestion);
        }, 150);
    });

    // Keyboard navigation
    elements.wordInput.addEventListener('keydown', (e) => {
        const isOpen = elements.suggestions && !elements.suggestions.classList.contains('hidden');

        if (e.key === 'Enter') {
            if (isOpen) {
                const selected = getSelectedSuggestion(elements.suggestions);
                if (selected) {
                    selectSuggestion(selected);
                } else {
                    hideSuggestions(elements.suggestions);
                    handleSearch();
                }
            } else {
                handleSearch();
            }
            e.preventDefault();
        } else if (e.key === 'ArrowDown' && isOpen) {
            navigateSuggestions(elements.suggestions, 1);
            e.preventDefault();
        } else if (e.key === 'ArrowUp' && isOpen) {
            navigateSuggestions(elements.suggestions, -1);
            e.preventDefault();
        } else if (e.key === 'Escape') {
            if (isOpen) {
                hideSuggestions(elements.suggestions);
            } else if (getIsExpanded()) {
                minimizeGraph();
            }
        }
    });

    // Hide suggestions on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-wrapper')) {
            hideSuggestions(elements.suggestions);
        }
    });

    // Settings popover toggle
    const settingsBtn = document.getElementById('settings-btn');
    const settingsPopover = document.getElementById('settings-popover');
    if (settingsBtn && settingsPopover) {
        settingsBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            settingsPopover.classList.toggle('hidden');
        });
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.settings-wrapper')) {
                settingsPopover.classList.add('hidden');
            }
        });
    }

    // Setup modal
    const aboutBtn = document.getElementById('about-btn');
    const aboutModal = document.getElementById('about-modal');
    const aboutClose = document.getElementById('about-close');
    const modalBackdrop = aboutModal?.querySelector('.modal-backdrop');
    const modalTabs = aboutModal?.querySelectorAll('.modal-tab');

    const { closeAboutModal } = setupModal(aboutBtn, aboutModal, aboutClose, modalBackdrop, modalTabs);

    // Escape for modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && aboutModal && !aboutModal.classList.contains('hidden')) {
            closeAboutModal();
        }
    });

    // Version info in footer
    const versionDetails = document.getElementById('version-details');
    const versionContent = document.getElementById('version-content');
    const versionSummary = document.getElementById('version-summary');
    if (versionDetails && versionContent) {
        async function fetchVersion() {
            try {
                const response = await fetch('/version');
                if (!response.ok) return;
                const data = await response.json();
                const version = data.version || 'unknown';
                const stats = data.db_stats || {};
                versionSummary.textContent = `v${version}`;
                versionContent.innerHTML =
                    `<span>Version: ${version}</span>` +
                    (stats.words ? `<span>Words: ${stats.words.toLocaleString()}</span>` : '') +
                    (stats.definitions ? `<span>Definitions: ${stats.definitions.toLocaleString()}</span>` : '');
            } catch (e) {
                versionContent.textContent = 'Could not load version info';
            }
        }
        // Fetch on toggle or on load
        versionDetails.addEventListener('toggle', () => {
            if (versionDetails.open) fetchVersion();
        });
        // Also fetch eagerly so the summary shows the version
        fetchVersion();
    }

    // Link types toggle - shared handler for both desktop and mobile checkboxes
    const showLinkTypesCheckbox = document.getElementById('show-link-types');
    const mobileShowLinkTypes = document.getElementById('mobile-show-link-types');
    const simpleLegend = document.getElementById('edge-legend-simple');
    const detailedLegend = document.getElementById('edge-legend-detailed');

    function handleLinkTypesToggle(enabled) {
        setShowLinkTypes(enabled);
        if (simpleLegend) simpleLegend.classList.toggle('hidden', enabled);
        if (detailedLegend) detailedLegend.classList.toggle('hidden', !enabled);
        // Re-render to apply/remove link type colors
        if (fullGraphData && currentSearchedWord) {
            renderGraph(fullGraphData, currentSearchedWord, true);
        }
    }

    if (showLinkTypesCheckbox) {
        showLinkTypesCheckbox.addEventListener('change', () => {
            const enabled = showLinkTypesCheckbox.checked;
            if (mobileShowLinkTypes) mobileShowLinkTypes.checked = enabled;
            handleLinkTypesToggle(enabled);
        });
    }

    // Mobile menu
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    const mobileAboutBtn = document.getElementById('mobile-about-btn');
    const mobileIncludeCompound = document.getElementById('mobile-include-compound');

    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            mobileMenu.classList.toggle('hidden');
        });
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.mobile-menu-wrapper')) {
                mobileMenu.classList.add('hidden');
            }
        });
    }

    if (mobileAboutBtn) {
        mobileAboutBtn.addEventListener('click', () => {
            mobileMenu?.classList.add('hidden');
            if (aboutModal) aboutModal.classList.remove('hidden');
        });
    }

    // Sync mobile compound checkbox with desktop
    if (mobileIncludeCompound && elements.includeCompound) {
        mobileIncludeCompound.addEventListener('change', () => {
            elements.includeCompound.checked = mobileIncludeCompound.checked;
            elements.includeCompound.dispatchEvent(new Event('change'));
        });
    }

    // Sync mobile link types checkbox with desktop
    if (mobileShowLinkTypes) {
        mobileShowLinkTypes.addEventListener('change', () => {
            const enabled = mobileShowLinkTypes.checked;
            if (showLinkTypesCheckbox) showLinkTypesCheckbox.checked = enabled;
            handleLinkTypesToggle(enabled);
        });
    }
});
