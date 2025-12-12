/**
 * Semantic Search - AI-powered natural language search
 */

const SemanticSearch = {
    isEnabled: false,

    /**
     * Check if semantic search is available
     */
    async checkAvailability() {
        try {
            const response = await fetch(`${window.API_URL}/stats`);
            const data = await response.json();
            this.isEnabled = data.embedding_stats?.index_exists || false;
            return this.isEnabled;
        } catch (error) {
            console.error('Error checking semantic search availability:', error);
            return false;
        }
    },

    /**
     * Perform semantic search
     */
    async search(query, maxResults = 10, minSimilarity = 0.3) {
        if (!this.isEnabled) {
            throw new Error('Semantic search is not enabled. Run generate_embeddings.py first.');
        }

        const response = await fetch(`${window.API_URL}/semantic_search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                max_results: maxResults,
                min_similarity: minSimilarity
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Semantic search failed');
        }

        return await response.json();
    },

    /**
     * Get explanation for search results
     */
    async explain(query, maxResults = 10, maxVerses = 5, semantic = false) {
        const response = await fetch(`${window.API_URL}/explain`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                max_results: maxResults,
                max_verses: maxVerses,
                semantic: semantic
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Explain failed');
        }

        return await response.json();
    },

    /**
     * Display semantic search results with similarity scores
     */
    displayResults(verses, query) {
        const resultsList = document.getElementById('resultsList');
        const resultsCount = document.getElementById('resultsCount');
        const results = document.getElementById('results');

        if (verses.length === 0) {
            resultsList.innerHTML = `
                <div class="no-results">
                    <div class="no-results-icon">🤖</div>
                    <div class="no-results-text">No semantically similar verses found.</div>
                    <p style="margin-top: 10px; font-size: 0.9rem;">Try a different query or use keyword search.</p>
                </div>
            `;
        } else {
            resultsList.innerHTML = verses.map((verse, index) => {
                const similarity = verse.relevance_score || 0;
                let relevanceLabel = 'Relevant';
                let relevanceColor = '#0066cc';

                if (similarity > 0.7) {
                    relevanceLabel = 'Highly Relevant';
                    relevanceColor = '#00aa00';
                } else if (similarity > 0.5) {
                    relevanceLabel = 'Very Relevant';
                    relevanceColor = '#0088cc';
                } else if (similarity > 0.3) {
                    relevanceLabel = 'Relevant';
                    relevanceColor = '#666';
                }

                return `
                    <div class="verse-card" id="verse-${index}">
                        <div class="verse-header">
                            <div>
                                <span class="verse-reference">${verse.reference}</span>
                                <span class="verse-score" style="background: ${relevanceColor}20; color: ${relevanceColor};">
                                    ${relevanceLabel} (${(similarity * 100).toFixed(1)}%)
                                </span>
                            </div>
                            <div class="verse-actions">
                                <button class="btn-small" onclick="toggleVerse(${index})">
                                    <span id="toggle-btn-${index}">Expand</span>
                                </button>
                                <button class="btn-small secondary" onclick="viewChapter('${verse.book}', ${verse.chapter}, ${verse.verse})">
                                    View Chapter
                                </button>
                            </div>
                        </div>
                        <div class="verse-preview">${verse.text}</div>
                        <div class="verse-text">${verse.text}</div>
                    </div>
                `;
            }).join('');
        }

        resultsCount.textContent = `${verses.length} result${verses.length !== 1 ? 's' : ''} (semantic search)`;
        results.classList.remove('hidden');
    }
};

// Example usage (can be called from console or future UI buttons):
// SemanticSearch.checkAvailability().then(enabled => {
//     if (enabled) {
//         SemanticSearch.search('divine forgiveness and grace').then(verses => {
//             SemanticSearch.displayResults(verses, 'divine forgiveness and grace');
//         });
//     }
// });
