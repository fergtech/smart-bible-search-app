/**
 * History Module - track and display full search sessions.
 *
 * Redesign note: this used to build its own slide-in overlay sidebar and
 * floating toggle FAB via JS (createHistoryUI()), appended straight to
 * document.body. The new workspace shell already provides the sidebar
 * markup in-page (#historySidebar / #historyList), always visible by
 * default in its own column - this module now just renders into that
 * existing markup instead of creating and positioning its own.
 *
 * Session data model is unchanged (localStorage, grouped by date), with
 * one addition: addInteraction() now also stores memory_id/pending_review
 * metadata per turn, so a restored session's Approve buttons still work,
 * not just its text.
 */

class HistoryManager {
    constructor() {
        this.storageKey = 'bible_search_sessions';
        this.currentSessionKey = 'bible_current_session';
        this.maxSessions = 50;
        this.sessions = [];
        this.currentSession = null;

        this.init();
    }

    init() {
        this.loadSessions();
        this.loadCurrentSession();

        this.elements = {
            list: document.getElementById('historyList'),
            clearBtn: document.getElementById('clearHistory')
        };

        if (this.elements.clearBtn) {
            this.elements.clearBtn.addEventListener('click', () => this.clearHistory());
        }

        this.renderHistory();
    }

    loadSessions() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            if (stored) this.sessions = JSON.parse(stored);
        } catch (error) {
            console.error('Failed to load sessions:', error);
            this.sessions = [];
        }
    }

    loadCurrentSession() {
        try {
            const stored = localStorage.getItem(this.currentSessionKey);
            if (stored) this.currentSession = JSON.parse(stored);
        } catch (error) {
            console.error('Failed to load current session:', error);
            this.currentSession = null;
        }
    }

    saveSessions() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.sessions));
        } catch (error) {
            console.error('Failed to save sessions:', error);
        }
    }

    saveCurrentSession() {
        try {
            if (this.currentSession) {
                localStorage.setItem(this.currentSessionKey, JSON.stringify(this.currentSession));
            } else {
                localStorage.removeItem(this.currentSessionKey);
            }
        } catch (error) {
            console.error('Failed to save current session:', error);
        }
    }

    startNewSession(query) {
        if (this.currentSession && this.currentSession.interactions.length > 0) {
            this.endCurrentSession();
        }

        this.currentSession = {
            id: Date.now(),
            startTime: new Date().toISOString(),
            initialQuery: query,
            title: query, // replaced once generateTitle() resolves, below
            interactions: [],
            metadata: {
                date: new Date().toLocaleDateString(),
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            }
        };

        this.saveCurrentSession();
        this.generateTitle(this.currentSession, query);
    }

    /**
     * Fire-and-forget short title for the sidebar, generated once per
     * session from its opening question (e.g. "Grace in Scripture" instead
     * of the raw question truncated mid-sentence). Never blocks anything -
     * the session already renders with the raw query as its title, and this
     * just patches it in whenever the (local, free-model) call resolves. If
     * it fails, the raw query stays as the title - not a real error.
     */
    async generateTitle(session, query) {
        try {
            const response = await fetch(`${window.API_BASE_URL}/session/title`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            if (!response.ok) return;

            const data = await response.json();
            if (!data.title) return;
            session.title = data.title;

            if (this.currentSession === session) {
                this.saveCurrentSession();
            } else if (this.sessions.includes(session)) {
                this.saveSessions();
                this.renderHistory();
            }
        } catch (error) {
            console.error('Session title generation failed:', error);
        }
    }

    /** metadata: optional { memory_id, pending_review, commentary_mode } */
    addInteraction(query, results, commentary, isFollowup = false, metadata = null) {
        if (!this.currentSession) {
            this.startNewSession(query);
        }

        const interaction = {
            timestamp: new Date().toISOString(),
            query: query,
            isFollowup: isFollowup,
            results: (results || []).map(r => ({
                book: r.book,
                chapter: r.chapter,
                verse: r.verse,
                reference: r.reference,
                text: r.text,
                relevance_score: r.relevance_score
            })),
            commentary: commentary,
            metadata: metadata || null
        };

        this.currentSession.interactions.push(interaction);
        this.saveCurrentSession();
    }

    endCurrentSession() {
        if (!this.currentSession || this.currentSession.interactions.length === 0) {
            this.currentSession = null;
            this.saveCurrentSession();
            return;
        }

        this.currentSession.endTime = new Date().toISOString();

        this.sessions = this.sessions.filter(
            s => s.initialQuery !== this.currentSession.initialQuery
        );
        this.sessions.unshift(this.currentSession);

        if (this.sessions.length > this.maxSessions) {
            this.sessions = this.sessions.slice(0, this.maxSessions);
        }

        this.saveSessions();
        this.renderHistory();

        this.currentSession = null;
        this.saveCurrentSession();
    }

    renderHistory() {
        if (!this.elements.list) return;

        if (this.sessions.length === 0) {
            this.elements.list.innerHTML = `
                <div class="history-empty">
                    <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                    <p>No sessions yet</p>
                    <small>Your study sessions will appear here</small>
                </div>
            `;
            return;
        }

        const groupedSessions = this.groupByDate();

        let html = '';
        for (const [date, items] of Object.entries(groupedSessions)) {
            html += `
                <div class="history-group">
                    <div class="history-group-date">${date}</div>
                    ${items.map(session => this.renderSessionItem(session)).join('')}
                </div>
            `;
        }

        this.elements.list.innerHTML = html;

        this.elements.list.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', () => {
                const sessionId = parseInt(item.dataset.sessionId);
                this.loadSession(sessionId);
            });
        });
    }

    renderSessionItem(session) {
        const followupCount = session.interactions.filter(i => i.isFollowup).length;

        return `
            <div class="history-item" data-session-id="${session.id}">
                <div class="history-item-content">
                    <div class="history-item-text">
                        <div class="history-item-query">${this.escapeHtml(this.truncate(session.title || session.initialQuery, 60))}</div>
                        <div class="history-item-meta">
                            <span class="history-item-time">${session.metadata.time}</span>
                            ${followupCount > 0 ? `<span class="history-item-badge">${followupCount} follow-up${followupCount > 1 ? 's' : ''}</span>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    groupByDate() {
        const grouped = {};
        const today = new Date().toLocaleDateString();
        const yesterday = new Date(Date.now() - 86400000).toLocaleDateString();

        for (const session of this.sessions) {
            let dateLabel = session.metadata.date;
            if (session.metadata.date === today) {
                dateLabel = 'Today';
            } else if (session.metadata.date === yesterday) {
                dateLabel = 'Yesterday';
            }

            if (!grouped[dateLabel]) grouped[dateLabel] = [];
            grouped[dateLabel].push(session);
        }

        return grouped;
    }

    /**
     * Restore a past session as the CURRENT active thread, replaying every
     * turn (not just the last one) into the conversation panel via
     * commentaryManager.loadThread() - a real improvement over the old
     * single-message recap.
     */
    loadSession(sessionId) {
        const session = this.sessions.find(s => s.id === sessionId);
        if (!session) return;

        this.sessions = this.sessions.filter(s => s.id !== sessionId);
        this.saveSessions();

        this.currentSession = session;
        this.saveCurrentSession();

        if (window.WorkspaceLayout) {
            window.WorkspaceLayout.enterWorkspace();
            window.WorkspaceLayout.closeSidebar();
        }

        if (window.commentaryManager) {
            window.commentaryManager.loadThread(session.interactions);
        }

        if (window.frontendLogger) {
            frontendLogger.logAction('session_resumed', {
                sessionId: sessionId,
                interactions: session.interactions.length
            });
        }
    }

    clearHistory() {
        if (confirm('Are you sure you want to clear all session history?')) {
            this.sessions = [];
            this.currentSession = null;
            this.saveSessions();
            this.saveCurrentSession();
            this.renderHistory();

            if (window.frontendLogger) {
                frontendLogger.logAction('sessions_cleared');
            }
        }
    }

    truncate(text, length) {
        if (text.length <= length) return text;
        return text.substring(0, length) + '...';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

let historyManager;
document.addEventListener('DOMContentLoaded', () => {
    historyManager = new HistoryManager();
    window.historyManager = historyManager;
});
