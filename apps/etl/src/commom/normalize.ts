/**
 * Robust normalization function for Portuguese and English slugs.
 * Converts to lowercase, removes accents/diacritics, filters out common connectives and articles,
 * and joins spaces with a hyphen.
 * 
 * Example: "Árvore de Natal" -> "arvore-natal"
 */
export function normalizeString(str: string): string {
    if (!str) return '';

    const stopwords = new Set([
        // Português
        'de', 'do', 'da', 'dos', 'das', 'em', 'um', 'uma', 'uns', 'umas', 
        'para', 'com', 'por', 'sem', 'sob', 'sobre', 'a', 'o', 'as', 'os', 'e',
        // Inglês
        'of', 'the', 'in', 'on', 'at', 'for', 'with', 'by', 'a', 'an', 'and', 'to', 'from', 'about'
    ]);

    const words = str
        .trim()
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '') // Remove accents
        .replace(/[^a-z0-9\s]/g, ' ') // Remove special chars/punctuation
        .replace(/\s+/g, ' ') // Collapse multiple spaces
        .split(' ');

    return words
        .filter(word => word.length > 0 && !stopwords.has(word))
        .join('-');
}

export function stripHtml(str: string): string {
    if (!str) return '';
    return str.replace(/<[^>]*>/g, '').trim();
}

