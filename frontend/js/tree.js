/**
 * Tree View Module
 * Renders etymology data as a text-based tree using Unicode box-drawing characters
 */

import { getLangName, escapeHtml } from './utils.js';

/**
 * Build a tree structure from nodes and edges
 * @param {Object[]} nodes - Array of node objects
 * @param {Object[]} edges - Array of edge objects (source → target means child → parent)
 * @param {string} startWord - The searched word to start from
 * @param {number} maxDepth - Maximum depth to traverse
 * @returns {Object|null} Tree structure or null if start node not found
 */
export function buildTree(nodes, edges, startWord, maxDepth) {
    if (!nodes || !edges || nodes.length === 0) return null;

    // Create lookup maps
    const nodeMap = new Map(nodes.map(n => [n.id, n]));

    // Build child → parents adjacency (edges go child → parent)
    const childToParents = new Map();
    for (const edge of edges) {
        if (!childToParents.has(edge.source)) {
            childToParents.set(edge.source, []);
        }
        childToParents.get(edge.source).push(edge.target);
    }

    // Find the starting node (English version of searched word)
    const startNodeId = `${startWord.toLowerCase()}|en`;
    let startNode = nodeMap.get(startNodeId);

    // Fallback: find any node with matching lexeme
    if (!startNode) {
        startNode = nodes.find(n =>
            n.lexeme && n.lexeme.toLowerCase() === startWord.toLowerCase()
        );
    }

    if (!startNode) return null;

    // Recursive tree builder
    function buildSubtree(nodeId, depth, visited) {
        if (depth > maxDepth || visited.has(nodeId)) {
            return null;
        }

        const node = nodeMap.get(nodeId);
        if (!node) return null;

        visited.add(nodeId);

        const children = [];
        const parentIds = childToParents.get(nodeId) || [];

        for (const parentId of parentIds) {
            const childTree = buildSubtree(parentId, depth + 1, new Set(visited));
            if (childTree) {
                children.push(childTree);
            }
        }

        return {
            id: nodeId,
            lexeme: node.lexeme,
            lang: node.lang,
            langName: node.lang_name || getLangName(node.lang),
            sense: node.sense,
            family: node.family,
            branch: node.branch,
            children,
        };
    }

    return buildSubtree(startNode.id, 0, new Set());
}

/**
 * Render a tree structure as Unicode text
 * @param {Object} tree - Tree structure from buildTree()
 * @returns {string} HTML string of the rendered tree
 */
export function renderTreeHTML(tree) {
    if (!tree) return '<div class="tree-empty">No tree data available</div>';

    const lines = [];

    function renderNode(node, prefix, isLast, isRoot) {
        // Build the connector prefix
        const connector = isRoot ? '' : (isLast ? '└── ' : '├── ');
        const langDisplay = node.langName || node.lang;

        // Create clickable node HTML
        const nodeId = `tree-node-${node.id.replace(/[^a-zA-Z0-9]/g, '-')}`;
        const senseAttr = node.sense ? ` data-sense="${escapeHtml(node.sense)}"` : '';
        const familyAttr = node.family ? ` data-family="${escapeHtml(node.family)}"` : '';
        const branchAttr = node.branch ? ` data-branch="${escapeHtml(node.branch)}"` : '';

        const nodeHtml = `<span class="tree-node" id="${nodeId}" data-lexeme="${escapeHtml(node.lexeme)}" data-lang="${escapeHtml(node.lang)}" data-lang-name="${escapeHtml(langDisplay)}"${senseAttr}${familyAttr}${branchAttr}><span class="tree-word">${escapeHtml(node.lexeme)}</span> <span class="tree-lang">(${escapeHtml(langDisplay)})</span></span>`;

        lines.push(`<div class="tree-line">${escapeHtml(prefix)}${connector}${nodeHtml}</div>`);

        // Render children
        const newPrefix = isRoot ? '' : (prefix + (isLast ? '    ' : '│   '));
        node.children.forEach((child, i) => {
            const childIsLast = i === node.children.length - 1;
            renderNode(child, newPrefix, childIsLast, false);
        });
    }

    renderNode(tree, '', true, true);

    return `<div class="tree-content">${lines.join('')}</div>`;
}


