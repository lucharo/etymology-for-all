/**
 * Search and autocomplete functionality
 */

import { handleApiResponse, truncate } from './utils.js';

const FETCH_DEPTH = 10;

export async function fetchEtymology(word) {
    const response = await fetch(`/graph/${encodeURIComponent(word)}?depth=${FETCH_DEPTH}`);
    await handleApiResponse(response, 'etymology lookup');
    return response.json();
}

export async function fetchRandomWord() {
    const response = await fetch(`/random`);
    await handleApiResponse(response, 'random word');
    const data = await response.json();
    return data.word;
}

export async function fetchSuggestions(query, suggestionsEl, onSelect) {
    if (query.length < 2) {
        hideSuggestions(suggestionsEl);
        return;
    }

    try {
        const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
        if (response.status === 429) return;
        if (!response.ok) return;
        const data = await response.json();
        showSuggestions(data.results, suggestionsEl, onSelect);
    } catch (err) {
        console.error('Search error:', err);
    }
}

let selectedSuggestionIndex = -1;

export function showSuggestions(results, suggestionsEl, onSelect) {
    if (!suggestionsEl || results.length === 0) {
        hideSuggestions(suggestionsEl);
        return;
    }

    selectedSuggestionIndex = -1;
    suggestionsEl.innerHTML = results
        .map(
            (r, i) => `
            <div class="suggestion-item" data-index="${i}" data-word="${r.word}">
                <span class="suggestion-word">${r.word}</span>
                ${r.sense ? `<div class="suggestion-sense">${truncate(r.sense, 60)}</div>` : ''}
            </div>
        `
        )
        .join('');

    suggestionsEl.classList.remove('hidden');

    suggestionsEl.querySelectorAll('.suggestion-item').forEach((item) => {
        item.addEventListener('click', () => onSelect(item.dataset.word));
    });
}

export function hideSuggestions(suggestionsEl) {
    if (suggestionsEl) {
        suggestionsEl.classList.add('hidden');
        suggestionsEl.innerHTML = '';
    }
    selectedSuggestionIndex = -1;
}

export function navigateSuggestions(suggestionsEl, direction) {
    const items = suggestionsEl.querySelectorAll('.suggestion-item');
    if (items.length === 0) return;

    items.forEach((item) => item.classList.remove('selected'));

    selectedSuggestionIndex += direction;
    if (selectedSuggestionIndex < 0) selectedSuggestionIndex = items.length - 1;
    if (selectedSuggestionIndex >= items.length) selectedSuggestionIndex = 0;

    items[selectedSuggestionIndex].classList.add('selected');
    items[selectedSuggestionIndex].scrollIntoView({ block: 'nearest' });
}

export function getSelectedSuggestion(suggestionsEl) {
    if (selectedSuggestionIndex < 0) return null;
    const items = suggestionsEl.querySelectorAll('.suggestion-item');
    return items[selectedSuggestionIndex]?.dataset.word || null;
}
