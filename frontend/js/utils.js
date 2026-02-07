/**
 * Utility functions for Etymology Explorer
 */

export function getLangName(lang) {
    // API provides lang_name from 2400+ code database
    // This is only called as fallback when API doesn't return lang_name
    if (!lang) return 'Unknown';
    return lang;  // Return raw code if no name available
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

/**
 * Check if a graph API response indicates the word exists but has no etymology.
 * Returns { noEtymology: true, lexeme } if so, null otherwise.
 */
export function checkNoEtymology(data) {
    if (data && data.no_etymology === true) {
        return { noEtymology: true, lexeme: data.lexeme || '' };
    }
    return null;
}

export function buildNodeLabel(node) {
    const langName = node.lang_name || getLangName(node.lang);
    const displayWord = node.lexeme || node.id;
    // Keep nodes clean: just word + language name
    return displayWord + '\n(' + langName.toLowerCase() + ')';
}
