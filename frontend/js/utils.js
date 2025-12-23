/**
 * Utility functions for Etymology Explorer
 */

// Human-readable language names (fallback when not provided by API)
export const LANG_NAMES = {
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
    return displayWord + '\n(' + langName.toLowerCase() + ')';
}
