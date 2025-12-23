/**
 * UI state management and controls
 */

import { getLangName, truncate } from './utils.js';
import { getCy } from './graph.js';

// Show node detail panel
export function showNodeDetail(data, elements) {
    const { nodeDetail, detailWord, detailLang, detailFamily, detailSense } = elements;
    if (!nodeDetail || !detailWord || !detailLang) return;

    detailWord.textContent = data.word;
    detailLang.textContent = data.langName || getLangName(data.lang);

    if (detailFamily && detailFamily.parentElement) {
        if (data.family) {
            detailFamily.textContent = `${data.family}${data.branch ? ' → ' + data.branch : ''}`;
            detailFamily.parentElement.classList.remove('hidden');
        } else {
            detailFamily.parentElement.classList.add('hidden');
        }
    }

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

export function hideNodeDetail(nodeDetail) {
    if (nodeDetail) nodeDetail.classList.add('hidden');
}

// State management
export function showLoading(elements) {
    const { loadingEl, emptyState, errorState, wordInfo, graphOptions, statsPanel, statsToggle, directionIndicator, expandBtn } = elements;
    const cy = getCy();

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

export function showError(message, elements, minimizeGraph) {
    const { loadingEl, emptyState, errorState, errorMessage, wordInfo, directionIndicator, expandBtn } = elements;

    loadingEl.classList.add('hidden');
    emptyState.classList.add('hidden');
    errorState.classList.remove('hidden');
    errorMessage.textContent = message;
    wordInfo.classList.add('hidden');
    if (directionIndicator) directionIndicator.classList.add('hidden');
    if (expandBtn) expandBtn.classList.add('hidden');
    minimizeGraph();
}

export function showGraph(elements) {
    const { loadingEl, emptyState, errorState, expandBtn } = elements;

    loadingEl.classList.add('hidden');
    emptyState.classList.add('hidden');
    errorState.classList.add('hidden');
    if (expandBtn) expandBtn.classList.remove('hidden');
}

// Stats
export function updateStats(nodeCount, edgeCount, langCount, depth, elements) {
    const { statNodes, statEdges, statLangs, statDepth } = elements;
    if (statNodes) statNodes.textContent = nodeCount;
    if (statEdges) statEdges.textContent = edgeCount;
    if (statLangs) statLangs.textContent = langCount;
    if (statDepth) statDepth.textContent = depth;
}

// Language breakdown
export function updateInfoSummary(langCounts, langBreakdown) {
    if (!langBreakdown) return;

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

// Depth UI
export function updateDepthUI(currentDepth, graphMaxDepth, elements) {
    const { depthValue, depthMinus, depthPlus } = elements;
    const MIN_DEPTH = 1;
    if (depthValue) depthValue.textContent = currentDepth;
    if (depthMinus) depthMinus.disabled = currentDepth <= MIN_DEPTH;
    if (depthPlus) depthPlus.disabled = currentDepth >= graphMaxDepth;
}

// Expand/minimize
export function createExpandHandlers(graphContainer, graphBackdrop) {
    let isExpanded = false;
    const cy = getCy;

    function toggleExpandGraph() {
        isExpanded = !isExpanded;
        graphContainer.classList.toggle('expanded', isExpanded);
        if (graphBackdrop) graphBackdrop.classList.toggle('visible', isExpanded);

        setTimeout(() => {
            const cyInstance = getCy();
            if (cyInstance) {
                cyInstance.resize();
                cyInstance.animate({
                    fit: { eles: cyInstance.elements(), padding: 40 }
                }, { duration: 200, easing: 'ease-out' });
            }
        }, 320);
    }

    function minimizeGraph() {
        if (isExpanded) {
            isExpanded = false;
            graphContainer.classList.remove('expanded');
            if (graphBackdrop) graphBackdrop.classList.remove('visible');

            setTimeout(() => {
                const cyInstance = getCy();
                if (cyInstance) {
                    cyInstance.resize();
                    cyInstance.animate({
                        fit: { eles: cyInstance.elements(), padding: 40 }
                    }, { duration: 200, easing: 'ease-out' });
                }
            }, 320);
        }
    }

    function getIsExpanded() {
        return isExpanded;
    }

    return { toggleExpandGraph, minimizeGraph, getIsExpanded };
}

// Modal
export function setupModal(aboutBtn, aboutModal, aboutClose, modalBackdrop, modalTabs) {
    function openAboutModal() {
        if (aboutModal) aboutModal.classList.remove('hidden');
    }

    function closeAboutModal() {
        if (aboutModal) aboutModal.classList.add('hidden');
    }

    function switchTab(tabName) {
        modalTabs?.forEach((tab) => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });
        document.querySelectorAll('.tab-content').forEach((content) => {
            content.classList.toggle('active', content.id === `tab-${tabName}`);
        });
    }

    if (aboutBtn) aboutBtn.addEventListener('click', openAboutModal);
    if (aboutClose) aboutClose.addEventListener('click', closeAboutModal);
    if (modalBackdrop) modalBackdrop.addEventListener('click', closeAboutModal);
    modalTabs?.forEach((tab) => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    return { openAboutModal, closeAboutModal };
}
