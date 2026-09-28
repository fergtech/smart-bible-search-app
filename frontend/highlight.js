/**
 * Highlight Module - Interactive text selection with AI questioning
 * Allows users to highlight portions of verses and ask AI for biblical interpretation
 * Philosophy: Self-referential Bible interpretation (Bible explains itself)
 */

class HighlightManager {
    constructor() {
        this.tooltip = null;
        this.askButton = null;
        this.selectedText = '';
        this.selectedContext = null;
        this.isActive = false;
        
        this.init();
    }
    
    /**
     * Initialize the highlight manager
     */
    init() {
        this.tooltip = document.getElementById('highlightTooltip');
        this.askButton = document.getElementById('askHighlight');
        
        if (!this.tooltip || !this.askButton) {
            console.error('Highlight tooltip elements not found');
            return;
        }
        
        this.setupEventListeners();
    }
    
    /**
     * Setup event listeners for text selection
     */
    setupEventListeners() {
        // Listen for text selection on the entire document
        document.addEventListener('mouseup', (e) => this.handleSelection(e));
        document.addEventListener('touchend', (e) => this.handleSelection(e));
        
        // Listen for selection change (for keyboard selection)
        document.addEventListener('selectionchange', () => {
            // Debounce to avoid excessive calls
            clearTimeout(this.selectionTimeout);
            this.selectionTimeout = setTimeout(() => {
                const selection = window.getSelection();
                if (selection && selection.toString().trim().length > 0) {
                    // Only show tooltip if selection is complete (mouseup will handle positioning)
                    this.updateSelectedText();
                }
            }, 100);
        });
        
        // Ask button click
        this.askButton.addEventListener('click', () => this.handleAskClick());
        
        // Hide tooltip when clicking outside
        document.addEventListener('mousedown', (e) => {
            if (!this.tooltip.contains(e.target) && !this.isTextSelected()) {
                this.hideTooltip();
            }
        });
        
        // Hide tooltip on scroll (optional, for better UX)
        window.addEventListener('scroll', () => {
            if (this.isActive) {
                this.positionTooltip();
            }
        });
    }
    
    /**
     * Handle text selection
     */
    handleSelection(e) {
        // Small delay to ensure selection is complete
        setTimeout(() => {
            const selection = window.getSelection();
            const text = selection.toString().trim();
            
            // Only show tooltip for meaningful selections (at least 3 characters)
            if (text.length >= 3) {
                // Check if selection is within verse content
                const isInVerse = this.isSelectionInVerse(selection);
                
                if (isInVerse) {
                    this.selectedText = text;
                    this.selectedContext = this.getSelectionContext(selection);
                    this.showTooltip(selection);
                } else {
                    this.hideTooltip();
                }
            } else {
                this.hideTooltip();
            }
        }, 10);
    }
    
    /**
     * Check if selection is within a verse element
     */
    isSelectionInVerse(selection) {
        if (!selection.rangeCount) return false;
        
        const range = selection.getRangeAt(0);
        const container = range.commonAncestorContainer;
        
        // Check if we're inside verse content
        const verseElement = container.nodeType === Node.TEXT_NODE 
            ? container.parentElement 
            : container;
        
        // Check for verse-related classes or modal content
        return verseElement.closest('.verse-text') ||
               verseElement.closest('.chapter-verse-text') ||
               verseElement.closest('.modal-body') ||
               verseElement.closest('.results-list');
    }
    
    /**
     * Get context information about the selection
     */
    getSelectionContext(selection) {
        if (!selection.rangeCount) return null;
        
        const range = selection.getRangeAt(0);
        const container = range.commonAncestorContainer;
        const element = container.nodeType === Node.TEXT_NODE 
            ? container.parentElement 
            : container;
        
        // Try to find verse reference information
        const verseCard = element.closest('.verse-card');
        const chapterVerse = element.closest('.chapter-verse');
        
        let context = {
            book: null,
            chapter: null,
            verse: null,
            fullText: null
        };
        
        if (verseCard) {
            // From search results
            const refElement = verseCard.querySelector('.verse-reference');
            if (refElement) {
                const refText = refElement.textContent.trim();
                const match = refText.match(/^(.+?)\s+(\d+):(\d+)$/);
                if (match) {
                    context.book = match[1];
                    context.chapter = match[2];
                    context.verse = match[3];
                }
            }
            const textElement = verseCard.querySelector('.verse-text');
            if (textElement) {
                context.fullText = textElement.textContent.trim();
            }
        } else if (chapterVerse) {
            // From chapter modal
            const modalTitle = document.getElementById('modalTitle');
            if (modalTitle) {
                const titleMatch = modalTitle.textContent.match(/^(.+?)\s+(\d+)$/);
                if (titleMatch) {
                    context.book = titleMatch[1];
                    context.chapter = titleMatch[2];
                }
            }
            const verseNum = chapterVerse.querySelector('.chapter-verse-num');
            if (verseNum) {
                context.verse = verseNum.textContent.trim();
            }
            const verseText = chapterVerse.querySelector('.chapter-verse-text');
            if (verseText) {
                context.fullText = verseText.textContent.trim();
            }
        }
        
        return context;
    }
    
    /**
     * Show the tooltip near the selection
     */
    showTooltip(selection) {
        if (!selection.rangeCount) return;
        
        this.isActive = true;
        this.tooltip.classList.add('visible');
        this.positionTooltip();
        
        // Log highlight action
        if (window.frontendLogger) {
            frontendLogger.logAction('text_highlighted', {
                text: this.selectedText.substring(0, 100),
                length: this.selectedText.length,
                hasContext: !!this.selectedContext?.book
            });
        }
    }
    
    /**
     * Position tooltip above the selection
     */
    positionTooltip() {
        const selection = window.getSelection();
        if (!selection.rangeCount) return;
        
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        
        // Position above the selection, centered
        const tooltipRect = this.tooltip.getBoundingClientRect();
        
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
        let top = rect.top - tooltipRect.height - 12; // 12px gap above selection
        
        // Keep tooltip within viewport
        const padding = 16;
        if (left < padding) {
            left = padding;
        } else if (left + tooltipRect.width > window.innerWidth - padding) {
            left = window.innerWidth - tooltipRect.width - padding;
        }
        
        // If tooltip would go above viewport, show below selection instead
        if (top < padding) {
            top = rect.bottom + 12;
        }
        
        // Apply positioning
        this.tooltip.style.left = `${left + window.scrollX}px`;
        this.tooltip.style.top = `${top + window.scrollY}px`;
    }
    
    /**
     * Hide the tooltip
     */
    hideTooltip() {
        this.isActive = false;
        this.tooltip.classList.remove('visible');
        this.selectedText = '';
        this.selectedContext = null;
    }
    
    /**
     * Check if text is currently selected
     */
    isTextSelected() {
        const selection = window.getSelection();
        return selection && selection.toString().trim().length > 0;
    }
    
    /**
     * Update selected text reference
     */
    updateSelectedText() {
        const selection = window.getSelection();
        if (selection) {
            this.selectedText = selection.toString().trim();
        }
    }
    
    /**
     * Handle "Ask" button click
     */
    async handleAskClick() {
        if (!this.selectedText) return;
        
        // Log ask action
        if (window.frontendLogger) {
            frontendLogger.logAction('highlight_ask_clicked', {
                text: this.selectedText.substring(0, 100),
                hasContext: !!this.selectedContext?.book
            });
        }
        
        // Build contextual query
        const query = this.buildContextualQuery();

        // Not recorded to history here - historyManager.addQuery() was a
        // pre-existing dead reference (that method no longer exists on
        // HistoryManager, only addInteraction/startNewSession), which threw
        // and aborted this whole handler before ever reaching
        // performSearch() below. Recording already happens the normal way:
        // performSearch() -> generateCommentary() calls
        // historyManager.addInteraction() once the response comes back,
        // regardless of whether the query originated from typing or from
        // this highlight-to-ask flow.

        // Hide tooltip and clear selection
        this.hideTooltip();
        window.getSelection().removeAllRanges();
        
        // Close modal if open (seamless transition)
        if (UI && UI.closeModal) {
            UI.closeModal();
        }
        
        // Scroll to top smoothly
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        // Update search input with the full contextual query
        const queryInput = document.getElementById('queryInput');
        if (queryInput) {
            queryInput.value = query;
        }
        
        // Perform full search (results + commentary) for seamless experience
        if (window.KeywordSearch && window.KeywordSearch.performSearch) {
            // This will update results list AND generate commentary using 20 results
            await KeywordSearch.performSearch();
        } else {
            console.error('Search functionality not available');
            if (UI && UI.showStatus) {
                UI.showStatus('Search feature is not available', 'error');
            }
        }
    }
    
    /**
     * Build contextual query for AI
     */
    buildContextualQuery() {
        const highlighted = this.selectedText;
        const context = this.selectedContext;
        
        // Build query based on available context
        if (context?.book && context?.chapter && context?.verse) {
            // We have full verse reference
            return `What does the Bible mean when it says "${highlighted}" in ${context.book} ${context.chapter}:${context.verse}? Please explain using other Bible verses.`;
        } else if (context?.fullText && context.fullText.includes(highlighted)) {
            // We have the full verse text
            return `What does the Bible mean when it says "${highlighted}"? The full verse is: "${context.fullText}". Please explain using other Bible verses.`;
        } else {
            // Just the highlighted text
            return `What does the Bible mean when it says "${highlighted}"? Please explain this using other Bible verses and biblical context.`;
        }
    }
}

// Initialize on page load
let highlightManager;

document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for other modules to load
    setTimeout(() => {
        highlightManager = new HighlightManager();
        console.log('Highlight-to-Ask feature initialized');
    }, 500);
});

// Export for global access
window.highlightManager = highlightManager;
