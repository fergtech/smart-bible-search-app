/**
 * Keyword Search - Traditional text-based verse search
 */

const KeywordSearch = {
    elements: null,

    /**
     * Initialize search functionality
     */
    init() {
        this.elements = {
            queryInput: document.getElementById('queryInput'),
            searchBtn: document.getElementById('searchBtn'),
            maxResults: document.getElementById('maxResults'),
            results: document.getElementById('results'),
            resultsCount: document.getElementById('resultsCount'),
            resultsList: document.getElementById('resultsList')
        };

        // Event listeners
        this.elements.queryInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });

        this.elements.searchBtn.addEventListener('click', () => {
            this.performSearch();
        });
    },

    /**
     * Highlight query terms in text
     */
    highlightQuery(text) {
        const query = this.elements.queryInput.value.trim();
        if (!query) return text;

        // Escape special regex characters
        const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedQuery})`, 'gi');
        
        return text.replace(regex, '<strong style="background: #fff3cd; padding: 2px 4px; border-radius: 3px;">$1</strong>');
    },

    /**
     * Display search results
     */
    displayResults(verses) {
        if (verses.length === 0) {
            this.elements.resultsList.innerHTML = `
                <div class="no-results">
                    <div class="no-results-icon">🔍</div>
                    <div class="no-results-text">No verses found matching your search.</div>
                </div>
            `;
        } else {
            this.elements.resultsList.innerHTML = verses.map((verse, index) => `
                <div class="verse-card" id="verse-${index}">
                    <div class="verse-header">
                        <div>
                            <span class="verse-reference">${verse.reference}</span>
                            ${verse.relevance_score ? `<span class="verse-score">${(verse.relevance_score * 100).toFixed(0)}% match</span>` : ''}
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
                    <div class="verse-preview">${this.highlightQuery(verse.text)}</div>
                    <div class="verse-text">${this.highlightQuery(verse.text)}</div>
                </div>
            `).join('');
        }

        this.elements.resultsCount.textContent = `${verses.length} result${verses.length !== 1 ? 's' : ''}`;
        this.elements.results.classList.remove('hidden');
    },

    /**
     * Perform semantic search via AI
     */
    async performSearch() {
        const query = this.elements.queryInput.value.trim();
        
        if (!query) {
            UI.showStatus('Please enter a search query', 'error');
            return;
        }

        const maxResults = parseInt(this.elements.maxResults.value) || 10;

        // Disable button and show loading
        this.elements.searchBtn.disabled = true;
        this.elements.searchBtn.textContent = 'Searching...';
        UI.showStatus('Searching with AI...', 'loading');
        this.elements.results.classList.add('hidden');

        try {
            const response = await fetch(`${window.API_URL}/semantic_search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    max_results: maxResults,
                    min_similarity: 0.3
                })
            });

            if (!response.ok) {
                throw new Error(`Search failed: ${response.statusText}`);
            }

            const verses = await response.json();
            
            UI.hideStatus();
            this.displayResults(verses);

        } catch (error) {
            console.error('Search error:', error);
            UI.showStatus(`Error: ${error.message}`, 'error');
            this.elements.results.classList.add('hidden');
        } finally {
            this.elements.searchBtn.disabled = false;
            this.elements.searchBtn.textContent = 'Search';
        }
    },

    /**
     * Check backend health
     */
    async checkHealth() {
        try {
            const response = await fetch(`${window.API_URL}/`);
            const data = await response.json();
            console.log('Backend status:', data);
            UI.showStatus(`Connected to backend (${data.verses_loaded.toLocaleString()} verses loaded)`, 'success');
            setTimeout(() => UI.hideStatus(), 3000);
        } catch (error) {
            console.error('Backend connection error:', error);
            UI.showStatus('Cannot connect to backend. Make sure the API is running on port 8000.', 'error');
        }
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    KeywordSearch.init();
    KeywordSearch.checkHealth();
});
