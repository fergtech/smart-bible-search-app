/**
 * Frontend Logging Module
 * Logs user actions for analytics and adaptive intelligence
 */

class FrontendLogger {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.apiUrl = window.API_BASE_URL || 'http://localhost:8000';
        this.logQueue = [];
        this.maxQueueSize = 10;
    }
    
    /**
     * Generate a unique session ID
     */
    generateSessionId() {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Log an action (sends to backend if available, otherwise console)
     */
    async logAction(action, context = {}) {
        const logEntry = {
            action,
            context: {
                ...context,
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent,
                viewport: {
                    width: window.innerWidth,
                    height: window.innerHeight
                }
            },
            session_id: this.sessionId
        };
        
        // Always log to console for development
        console.log('[Frontend Log]', logEntry);
        
        // Add to queue
        this.logQueue.push(logEntry);
        
        // Send to backend if queue is full or important action
        const importantActions = ['search_submitted', 'commentary_generated', 'error_occurred'];
        if (this.logQueue.length >= this.maxQueueSize || importantActions.includes(action)) {
            await this.flush();
        }
    }
    
    /**
     * Flush log queue to backend
     */
    async flush() {
        if (this.logQueue.length === 0) return;
        
        const logsToSend = [...this.logQueue];
        this.logQueue = [];
        
        try {
            // Send each log to backend
            for (const log of logsToSend) {
                await fetch(`${this.apiUrl}/log`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(log),
                    // Don't block on logging
                    keepalive: true
                }).catch(err => {
                    // Silent fail - logging shouldn't break the app
                    console.debug('Log send failed:', err);
                });
            }
        } catch (error) {
            console.debug('Log flush failed:', error);
        }
    }
    
    /**
     * Log search submission
     */
    logSearch(query, searchType = 'keyword', resultsCount = 0) {
        this.logAction('search_submitted', {
            query,
            searchType,
            resultsCount,
            queryLength: query.length
        });
    }
    
    /**
     * Log commentary display
     */
    logCommentary(query, commentaryLength = 0, versesUsed = 0) {
        this.logAction('commentary_displayed', {
            query,
            commentaryLength,
            versesUsed
        });
    }
    
    /**
     * Log chapter view
     */
    logChapterView(book, chapter, verse = null) {
        this.logAction('chapter_opened', {
            book,
            chapter,
            verse,
            reference: `${book} ${chapter}${verse ? `:${verse}` : ''}`
        });
    }
    
    /**
     * Log toggle action
     */
    logToggle(elementName, newState) {
        this.logAction('toggle_clicked', {
            element: elementName,
            newState  // 'expanded' or 'collapsed'
        });
    }
    
    /**
     * Log error
     */
    logError(errorType, errorMessage, context = {}) {
        this.logAction('error_occurred', {
            errorType,
            errorMessage,
            ...context
        });
    }
    
    /**
     * Log verse click
     */
    logVerseClick(reference) {
        this.logAction('verse_clicked', {
            reference
        });
    }
}

// Create global logger instance
const frontendLogger = new FrontendLogger();

// Flush logs before page unload
window.addEventListener('beforeunload', () => {
    frontendLogger.flush();
});
