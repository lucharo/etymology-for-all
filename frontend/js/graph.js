/**
 * Graph rendering and Cytoscape functionality
 */

import { getLangName, buildNodeLabel } from './utils.js';

let cy = null;

export function getCy() {
    return cy;
}

export function getLayoutDirection() {
    return window.innerWidth > window.innerHeight ? 'LR' : 'TB';
}

export function initCytoscape(container, onNodeTap, onBackgroundTap, onNodeHover, onNodeOut) {
    cy = cytoscape({
        container,
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

    cy.on('tap', 'node', (e) => onNodeTap(e.target.data()));
    cy.on('tap', (e) => {
        if (e.target === cy) onBackgroundTap();
    });
    cy.on('mouseover', 'node', (e) => onNodeHover(e.target, container));
    cy.on('mouseout', 'node', () => onNodeOut(container));

    return cy;
}

// Compute depth of each node from the starting word using BFS
export function computeNodeDepths(nodes, edges, startWord) {
    const nodeDepths = new Map();
    const adjacency = new Map();

    edges.forEach(edge => {
        if (!adjacency.has(edge.source)) adjacency.set(edge.source, []);
        adjacency.get(edge.source).push(edge.target);
    });

    const startNode = nodes.find(n =>
        n.lexeme && n.lexeme.toLowerCase() === startWord.toLowerCase() && n.lang === 'en'
    );

    if (!startNode) {
        nodes.forEach(n => nodeDepths.set(n.id, 0));
        return nodeDepths;
    }

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

    // Handle disconnected nodes
    nodes.forEach(n => {
        if (!nodeDepths.has(n.id)) nodeDepths.set(n.id, 999);
    });

    return nodeDepths;
}

export function filterGraphByDepth(data, maxDepth, searchedWord) {
    const nodeDepths = computeNodeDepths(data.nodes, data.edges, searchedWord);
    const filteredNodes = data.nodes.filter(n => nodeDepths.get(n.id) <= maxDepth);
    const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = data.edges.filter(e =>
        filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)
    );
    return { nodes: filteredNodes, edges: filteredEdges };
}

export function calculateMaxGraphDepth(nodes, edges, startWord) {
    const nodeDepths = computeNodeDepths(nodes, edges, startWord);
    let maxDepth = 0;
    nodeDepths.forEach(depth => {
        if (depth < 999 && depth > maxDepth) maxDepth = depth;
    });
    return maxDepth;
}

export function calculateGraphDepth(startWord) {
    if (!cy || cy.nodes().length === 0) return 0;

    const startNode = cy.nodes().filter(n => {
        const word = n.data('word');
        const lang = n.data('lang');
        return word && word.toLowerCase() === startWord.toLowerCase() && lang === 'en';
    }).first();

    if (!startNode || startNode.length === 0) return 0;

    const visited = new Set();
    const queue = [{ node: startNode, depth: 0 }];
    let maxDepth = 0;

    while (queue.length > 0) {
        const { node, depth } = queue.shift();
        const nodeId = node.id();

        if (visited.has(nodeId)) continue;
        visited.add(nodeId);
        maxDepth = Math.max(maxDepth, depth);

        const outgoers = node.outgoers('node');
        outgoers.forEach(neighbor => {
            if (!visited.has(neighbor.id())) {
                queue.push({ node: neighbor, depth: depth + 1 });
            }
        });
    }

    return maxDepth;
}

export function renderGraphElements(displayData, directionIndicator) {
    const elements = [];
    const seenLangs = new Map();
    const langCounts = new Map();

    displayData.nodes.forEach((node) => {
        const langName = node.lang_name || getLangName(node.lang);
        const displayWord = node.lexeme || node.id;
        seenLangs.set(node.lang, langName);
        langCounts.set(langName, (langCounts.get(langName) || 0) + 1);

        elements.push({
            group: 'nodes',
            data: {
                id: node.id,
                word: displayWord,
                label: buildNodeLabel(node),
                lang: node.lang,
                langName: langName,
                sense: node.sense || null,
                hasSense: !!node.sense,
                family: node.family || null,
                branch: node.branch || null,
            },
        });
    });

    displayData.edges.forEach((edge) => {
        if (edge.source === edge.target) return;
        elements.push({
            group: 'edges',
            data: {
                id: `${edge.source}-${edge.target}`,
                source: edge.source,
                target: edge.target,
            },
        });
    });

    cy.elements().remove();
    cy.add(elements);

    const direction = getLayoutDirection();
    cy.layout({
        name: 'dagre',
        rankDir: direction,
        nodeSep: direction === 'LR' ? 40 : 30,
        rankSep: direction === 'LR' ? 80 : 60,
        padding: 30,
        animate: false,
    }).run();

    cy.fit(undefined, 40);

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

    return { seenLangs, langCounts };
}
