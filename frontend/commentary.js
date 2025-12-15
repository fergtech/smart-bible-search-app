/**
 * Commentary Module - AI-powered Biblical commentary generation
 * Integrates with backend GPU-accelerated summarization
 */

class CommentaryManager {
    constructor() {
        this.elements = {
            section: document.getElementById('commentarySection'),
            content: document.getElementById('commentaryContent'),
            toggle: document.getElementById('commentaryToggle')
        };
        
        this.isCollapsed = false;
        this.currentQuery = null;
        
        this.init();
    }
    
    init() {
        // Toggle collapse/expand
        if (this.elements.toggle) {
            this.elements.toggle.addEventListener('click', () => this.toggleCollapse());
        }
    }
    
    /**
     * Generate commentary for a search query
     */
    async generateCommentary(query, maxResults = 10) {
        if (!query || query.trim() === '') {
            return;
        }
        
        this.currentQuery = query;
        this.showSection();
        this.showLoading();
        
        try {
            // Create abort controller for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout
            
            const response = await fetch(`${window.API_BASE_URL}/commentary`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    max_results: maxResults,
                    use_cache: true
                }),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`Commentary generation failed: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.displayCommentary(data);
            
        } catch (error) {
            console.error('Commentary error:', error);
            
            if (error.name === 'AbortError') {
                this.displayError('Commentary generation timed out. The AI model may be downloading (first time only, ~3GB). Please try again in a few minutes.');
            } else {
                this.displayError(error.message);
            }
        }
    }
    
    /**
     * Display generated commentary
     */
    displayCommentary(data) {
        const { commentary, metadata } = data;
        
        // Log commentary display
        if (window.frontendLogger) {
            frontendLogger.logCommentary(
                this.currentQuery,
                commentary.length,
                metadata?.verses_used || 0
            );
        }
        
        // Format commentary with verse references emphasized
        const formattedCommentary = this.formatCommentary(commentary);
        
        this.elements.content.innerHTML = `
            <div class="commentary-text">
                <p>${formattedCommentary}</p>
            </div>
            ${metadata && metadata.model_info ? `
                <div class="commentary-meta" style="margin-top: var(--space-md); font-size: var(--font-size-sm); color: var(--text-tertiary);">
                    <span>Based on ${metadata.verses_used} verses</span>
                    ${metadata.model_info.device ? `
                        <span style="margin-left: var(--space-md);">
                            ${metadata.model_info.device === 'cuda' ? '⚡ GPU' : '💻 CPU'}
                        </span>
                    ` : ''}
                </div>
            ` : ''}
        `;
    }
    
    /**
     * Format commentary text with clickable verse references
     */
    formatCommentary(text) {
        // Make verse references clickable (e.g., "Genesis 1:1", "John 3:16")
        const versePattern = /([1-3]?\s?[A-Z][a-z]+)\s+(\d+):(\d+)(?:-(\d+))?/g;
        
        return text.replace(versePattern, (match, book, chapter, verse, endVerse) => {
            const cleanBook = book.trim();
            return `<span class="verse-reference-link" onclick="UI.viewChapter('${cleanBook}', ${chapter}, ${verse})" title="Click to view ${cleanBook} ${chapter}">${match}</span>`;
        });
    }
    
    /**
     * Show loading state
     */
    showLoading() {
        this.elements.content.innerHTML = `
            <div class="commentary-loading">
                <div class="spinner"></div>
                <p>Generating AI commentary...</p>
                <p style="font-size: var(--font-size-sm); color: var(--text-tertiary); margin-top: var(--space-sm);">
                    First time may take 1-2 minutes while model downloads
                </p>
            </div>
        `;
    }
    
    /**
     * Display error message
     */
    displayError(message) {
        // Log error
        if (window.frontendLogger) {
            frontendLogger.logError('commentary_error', message, { query: this.currentQuery });
        }
        
        this.elements.content.innerHTML = `
            <div style="text-align: center; color: var(--text-tertiary); padding: var(--space-xl);">
                <p>⚠️ Unable to generate commentary</p>
                <p style="font-size: var(--font-size-sm); margin-top: var(--space-sm);">${message}</p>
            </div>
        `;
    }
    
    /**
     * Show commentary section
     */
    showSection() {
        this.elements.section.classList.remove('hidden');
        this.elements.section.classList.add('visible');
        
        // Expand if collapsed
        if (this.isCollapsed) {
            this.toggleCollapse();
        }
    }
    
    /**
     * Hide commentary section
     */
    hideSection() {
        this.elements.section.classList.remove('visible');
        this.elements.section.classList.add('hidden');
    }
    
    /**
     * Toggle collapse/expand
     */
    toggleCollapse() {
        this.isCollapsed = !this.isCollapsed;
        
        // Log toggle action
        if (window.frontendLogger) {
            frontendLogger.logToggle('commentary', this.isCollapsed ? 'collapsed' : 'expanded');
        }
        
        if (this.isCollapsed) {
            this.elements.content.classList.add('collapsed');
            this.elements.toggle.classList.add('collapsed');
            this.elements.toggle.querySelector('span').textContent = '+';
        } else {
            this.elements.content.classList.remove('collapsed');
            this.elements.toggle.classList.remove('collapsed');
            this.elements.toggle.querySelector('span').textContent = '−';
        }
    }
    
    /**
     * Clear commentary
     */
    clear() {
        this.hideSection();
        this.elements.content.innerHTML = '';
        this.currentQuery = null;
    }
}

// Initialize on DOM load and expose globally
window.commentaryManager = null;
document.addEventListener('DOMContentLoaded', () => {
    window.commentaryManager = new CommentaryManager();
});
