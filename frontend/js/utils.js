/**
 * Utility functions for Etymology Explorer
 */

// Fallback language names (API provides names from 2400+ code database)
// This is only used when API doesn't return lang_name
export const LANG_NAMES = {
    en: 'English',
    la: 'Latin',
    grc: 'Ancient Greek',
    ang: 'Old English',
    enm: 'Middle English',
    fro: 'Old French',
    'gem-pro': 'Proto-Germanic',
    'ine-pro': 'Proto-Indo-European',
};

export function getLangName(lang) {
    if (!lang) return 'Unknown';
    const normalized = lang.toLowerCase().replace(/_/g, '-');
    return LANG_NAMES[normalized] || lang;
}

export function truncate(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.slice(0, maxLength).trim() + '…';
}

export async function handleApiResponse(response, context = 'request') {
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

export function buildNodeLabel(node) {
    const langName = node.lang_name || getLangName(node.lang);
    const displayWord = node.lexeme || node.id;
    // Keep nodes clean: just word + language name
    return displayWord + '\n(' + langName.toLowerCase() + ')';
}
