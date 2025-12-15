/**
 * Search Module - Semantic search integration with modern UI
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
            resultsSection: document.getElementById('resultsSection'),
            resultsCount: document.getElementById('resultsCount'),
            resultsList: document.getElementById('resultsList')
        };

        this.setupEventListeners();
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Search on Enter key
        this.elements.queryInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });

        // Search button click
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
     * Display search results in modern card layout
     */
    displayResults(verses) {
        if (!verses || verses.length === 0) {
            this.elements.resultsList.innerHTML = `
                <div class="no-results">
                    <div class="no-results-icon">🔍</div>
                    <div class="no-results-text">No verses found. Try a different query.</div>
                </div>
            `;
            return;
        }

        this.elements.resultsList.innerHTML = verses.map((verse, index) => `
            <article class="verse-card" role="listitem">
                <div class="verse-header">
                    <div class="verse-meta">
                        <h3 class="verse-reference">${verse.reference}</h3>
                        ${verse.relevance_score ? `
                            <span class="verse-score" title="Semantic similarity score">
                                ${Math.round(verse.relevance_score * 100)}% match
                            </span>
                        ` : ''}
                    </div>
                    <div class="verse-actions">
                        <button 
                            class="btn btn-secondary" 
                            onclick="viewChapter('${verse.book}', ${verse.chapter}, ${verse.verse})"
                            aria-label="View full chapter">
                            View Chapter
                        </button>
                    </div>
                </div>
                <div class="verse-text">${this.highlightQuery(verse.text)}</div>
            </article>
        `).join('');

        this.elements.resultsCount.textContent = `${verses.length} result${verses.length !== 1 ? 's' : ''}`;
        this.elements.resultsSection.classList.add('visible');
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

        // Clear previous results and commentary
        this.elements.resultsSection.classList.remove('visible');
        if (window.commentaryManager) {
            commentaryManager.clear();
        }

        // Disable button and show loading
        this.elements.searchBtn.disabled = true;
        this.elements.searchBtn.textContent = 'Searching...';
        UI.showStatus('Searching with AI...', 'info');

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
            
            // Log search action
            if (window.frontendLogger) {
                frontendLogger.logSearch(query, 'semantic', verses.length);
            }
            
            UI.hideStatus();
            this.displayResults(verses);
            
            // Generate commentary if available
            if (window.commentaryManager && verses.length > 0) {
                commentaryManager.generateCommentary(query, maxResults);
            }

        } catch (error) {
            console.error('Search error:', error);
            
            // Log error
            if (window.frontendLogger) {
                frontendLogger.logError('search_error', error.message, { query });
            }
            
            UI.showStatus(`Error: ${error.message}`, 'error');
            this.elements.resultsSection.classList.remove('visible');
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
