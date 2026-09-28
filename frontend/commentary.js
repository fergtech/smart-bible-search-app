/**
 * Conversation Manager - persistent chat-style thread for the workspace.
 *
 * Redesign note: this used to hold a SINGLE commentary answer that got
 * replaced on every follow-up (see FEATURE_UPDATES.md-era behavior). It
 * now holds an array of turns and renders the full thread, ChatGPT-style -
 * that was the explicit ask behind this redesign ("No More Replacing
 * Answers"). The global name `commentaryManager` and its public method
 * `generateCommentary(query, maxResults)` are kept as-is because
 * highlight.js's "Ask" flow calls into KeywordSearch.performSearch(), which
 * calls this - changing the name would mean touching highlight.js too for
 * no functional reason.
 */

class CommentaryManager {
    constructor() {
        this.elements = {
            thread: document.getElementById('conversationThread'),
            followupInput: document.getElementById('followupInput'),
            followupBtn: document.getElementById('followupBtn'),
            referencePanel: document.getElementById('referencePanel'),
            referenceList: document.getElementById('referenceList'),
            referenceSubtitle: document.getElementById('referenceSubtitle')
        };

        // Each turn: { query, data (raw /commentary response), messageEl }
        this.turns = [];
        this.activeTurnIndex = -1;

        this.icons = {
            thumbsUp: '<svg class="inline-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>',
            check: '<svg class="inline-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>'
        };

        this.init();
    }

    init() {
        if (this.elements.followupBtn) {
            this.elements.followupBtn.addEventListener('click', () => this.handleFollowup());
        }

        if (this.elements.followupInput) {
            this.elements.followupInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.handleFollowup();
                }
            });
        }

        this.renderEmptyThread();
    }

    handleFollowup() {
        const query = this.elements.followupInput?.value.trim();
        if (!query) return;

        this.elements.followupInput.value = '';

        if (window.frontendLogger) {
            frontendLogger.logSearch(query, 'followup_from_workspace');
        }

        if (window.KeywordSearch) {
            window.KeywordSearch.performSearch(query);
        }
    }

    /**
     * Submit a query and append the resulting turn to the thread.
     *
     * Internally this replaces what used to be two independent calls (a
     * results-list search plus a separate commentary generation) with a
     * single /commentary call. Its response already carries both the
     * answer AND the verses used to produce it - rendering both from that
     * one object is exactly what removes the mismatch between what the
     * conversation says and what the reference panel shows.
     */
    async generateCommentary(query, maxResults = 10) {
        if (!query || query.trim() === '') return;

        this.appendUserMessage(query);
        const loadingEl = this.appendLoadingMessage();

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 120000);

            const response = await fetch(`${window.API_BASE_URL}/commentary`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
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
            loadingEl.remove();
            this.appendAssistantMessage(query, data);

            if (window.frontendLogger) {
                frontendLogger.logCommentary(query, data.commentary.length, data.metadata?.verses_used || 0);
            }

            if (window.historyManager) {
                window.historyManager.addInteraction(
                    query,
                    data.verses || [],
                    data.commentary,
                    this.turns.length > 1,
                    { memory_id: data.metadata?.memory_id, pending_review: data.metadata?.pending_review, commentary_mode: data.commentary_mode }
                );
            }
        } catch (error) {
            console.error('Commentary error:', error);
            loadingEl.remove();

            const message = error.name === 'AbortError'
                ? 'Commentary generation timed out. Please try again.'
                : error.message;
            this.appendErrorMessage(message);

            if (window.frontendLogger) {
                frontendLogger.logError('commentary_error', message, { query });
            }
        }
    }

    // ---- Thread rendering ----

    renderEmptyThread() {
        if (this.turns.length > 0) return;
        this.elements.thread.innerHTML = `
            <div class="conversation-empty">
                <div class="conversation-empty-icon"><svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg></div>
                <p>Ask a question to begin your study.</p>
            </div>
        `;
    }

    appendUserMessage(query) {
        this.clearEmptyState();

        const wrapper = document.createElement('div');
        wrapper.className = 'message message-user';
        wrapper.innerHTML = `<div class="message-user-bubble">${this.escapeHtml(query)}</div>`;
        this.elements.thread.appendChild(wrapper);
        this.scrollToBottom();
    }

    appendLoadingMessage() {
        const wrapper = document.createElement('div');
        wrapper.className = 'commentary-loading';
        wrapper.innerHTML = `<div class="spinner"></div><p>Generating commentary...</p>`;
        this.elements.thread.appendChild(wrapper);
        this.scrollToBottom();
        return wrapper;
    }

    appendErrorMessage(message) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message';
        wrapper.innerHTML = `
            <div class="message-assistant crisis">
                <p><svg class="inline-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg> Unable to generate a response.</p>
                <p style="font-size: var(--font-size-sm); margin-top: var(--space-sm);">${this.escapeHtml(message)}</p>
            </div>
        `;
        this.elements.thread.appendChild(wrapper);
        this.scrollToBottom();
    }

    appendAssistantMessage(query, data) {
        const turnIndex = this.turns.length;
        this.turns.push({ query, data });

        const wrapper = document.createElement('div');
        wrapper.className = 'message';

        const isCrisis = data.commentary_mode === 'crisis';
        const bubble = document.createElement('div');
        bubble.className = `message-assistant${isCrisis ? ' crisis' : ''}`;
        bubble.dataset.turnIndex = String(turnIndex);

        const formattedCommentary = this.formatCommentary(data.commentary);
        const verseCount = data.metadata?.verses_used ?? (data.verses ? data.verses.length : 0);
        const pendingReview = data.metadata?.pending_review;
        const memoryId = data.metadata?.memory_id;

        bubble.innerHTML = `
            ${!isCrisis ? `<div class="message-index">Response ${turnIndex + 1}</div>` : ''}
            <div class="message-text">${formattedCommentary}</div>
            ${!isCrisis ? `
                <div class="message-meta-row">
                    <span>Based on ${verseCount} verse${verseCount === 1 ? '' : 's'}</span>
                    <span class="message-sources-hint">View sources →</span>
                </div>
            ` : ''}
            ${pendingReview && memoryId ? `
                <div class="message-approval">
                    <span class="message-approval-note">This is an interpretive answer awaiting review before it's reused for similar future questions.</span>
                    <button class="approve-memory-btn" onclick="window.commentaryManager.approveMemory('${memoryId}', this)">${this.icons.thumbsUp} Approve this answer</button>
                </div>
            ` : ''}
        `;

        bubble.addEventListener('click', (e) => {
            // Only "View sources" opens the reference drawer now - the
            // whole card being clickable meant an accidental click anywhere
            // in the answer (e.g. selecting text) could yank the drawer
            // open.
            if (!e.target.closest('.message-sources-hint')) return;
            this.setActiveTurn(turnIndex);
        });

        wrapper.appendChild(bubble);
        this.elements.thread.appendChild(wrapper);

        this.setActiveTurn(turnIndex);
        this.scrollToBottom();
    }

    setActiveTurn(turnIndex) {
        this.activeTurnIndex = turnIndex;

        this.elements.thread.querySelectorAll('.message-assistant').forEach(el => {
            el.classList.toggle('active', Number(el.dataset.turnIndex) === turnIndex);
        });

        const turn = this.turns[turnIndex];
        if (turn) {
            // The evidence rail is a permanent fixed column on desktop now
            // (no open/closed state to manage) and hidden outright on
            // mobile until that gets its own design pass, so this just
            // updates its content - nothing needs to "show" it anymore.
            this.updateReferencePanel(turn, turnIndex);
        }
    }

    /**
     * Conditionally RENDERED, not conditionally populated - with no verses
     * for this turn, the rail itself (background, border, shadow) is
     * hidden entirely rather than showing an empty "no sources" card. An
     * evidence rail with nothing to show isn't a smaller version of the
     * rail; it's the absence of one, same as ChatGPT/Perplexity never
     * showing a citations panel when an answer cites nothing.
     */
    updateReferencePanel(turn, turnIndex) {
        const verses = turn.data.verses || [];

        if (verses.length === 0) {
            this.elements.referencePanel.classList.add('hidden');
            this.elements.referenceList.innerHTML = '';
            this.elements.referenceSubtitle.textContent = '';
            return;
        }

        this.elements.referencePanel.classList.remove('hidden');

        // "Sources for Response N" (not "Sources" + a query string) is the
        // whole header now - it reads as evidence attached to a specific
        // answer, not a global search-results list you happen to be
        // looking at alongside the conversation.
        this.elements.referenceSubtitle.textContent = turnIndex !== undefined
            ? `Sources for Response ${turnIndex + 1}`
            : 'Sources';

        // Verses arrive pre-sorted by relevance (search_semantic.py), so the
        // first one is reliably the strongest match - split it out as a
        // "Primary Source" ahead of the rest, instead of a flat list of
        // identical-looking cards where nothing stands out.
        const [primary, ...supporting] = verses;
        let html = `<div class="reference-tier-label">Primary Source</div>${this.renderVerseCard(primary)}`;
        if (supporting.length > 0) {
            html += `<div class="reference-tier-label">Supporting Sources</div>`;
            html += supporting.map(v => this.renderVerseCard(v)).join('');
        }
        this.elements.referenceList.innerHTML = html;
    }

    /**
     * A citation chip, not a content card - reference + a couple lines of
     * preview text, the whole thing clickable (no separate button, no
     * score badge cluttering the view). The match score isn't gone, just
     * de-emphasized into a hover tooltip - this is a design change, not a
     * data change. Guards against firing navigation when the click is
     * really the end of a text selection (see highlight.js's "Ask about
     * this" flow, which needs to select text inside these chips).
     */
    renderVerseCard(v) {
        const score = (v.relevance_score !== null && v.relevance_score !== undefined)
            ? `${Math.round(v.relevance_score * 100)}% match`
            : '';
        return `
            <article class="verse-card" role="listitem" title="${score}" onclick="if (!window.getSelection().toString()) UI.viewChapter('${v.book}', ${v.chapter}, ${v.verse})">
                <h3 class="verse-reference">${v.reference}</h3>
                <div class="verse-text">${this.escapeHtml(v.text)}</div>
            </article>
        `;
    }

    /**
     * Restore a full past session (from history.js) as the active thread -
     * a real improvement over the old behavior, which only redisplayed the
     * LAST interaction's text as a static recap. Turns loaded this way
     * won't have a working Approve button if they predate that metadata
     * being stored, which is an acceptable degradation for old data.
     */
    loadThread(interactions) {
        this.turns = [];
        this.activeTurnIndex = -1;
        this.elements.thread.innerHTML = '';

        interactions.forEach(interaction => {
            this.appendUserMessage(interaction.query);
            const data = {
                commentary: interaction.commentary,
                commentary_mode: interaction.metadata?.commentary_mode || 'full',
                verses: interaction.results || [],
                metadata: {
                    verses_used: (interaction.results || []).length,
                    memory_id: interaction.metadata?.memory_id,
                    pending_review: interaction.metadata?.pending_review
                }
            };
            this.appendAssistantMessage(interaction.query, data);
        });

        this.scrollToBottom();
    }

    clear() {
        this.turns = [];
        this.activeTurnIndex = -1;
        this.elements.thread.innerHTML = '';
        this.elements.referencePanel.classList.add('hidden');
        this.elements.referenceList.innerHTML = '';
        this.elements.referenceSubtitle.textContent = '';
        this.renderEmptyThread();
    }

    /**
     * Human approval of an interpretive answer, promoting it into reusable
     * memory (see backend/memory_store.py). The only path to promotion for
     * interpretive answers - there's no automated confidence score for
     * theological soundness.
     */
    async approveMemory(memoryId, buttonEl) {
        buttonEl.disabled = true;
        buttonEl.textContent = 'Approving...';

        try {
            const response = await fetch(`${window.API_BASE_URL}/commentary/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ memory_id: memoryId })
            });

            if (!response.ok) throw new Error('Approval failed');

            buttonEl.innerHTML = `${this.icons.check} Approved`;
            buttonEl.closest('.message-approval').style.opacity = '0.7';
        } catch (error) {
            console.error('Approve memory error:', error);
            buttonEl.disabled = false;
            buttonEl.innerHTML = `${this.icons.thumbsUp} Approve this answer (retry)`;
        }
    }

    // ---- Strong's number popup (unchanged behavior, new layout) ----

    formatCommentary(text) {
        // The LLM sometimes writes markdown-style **bold** headings (e.g.
        // "**Key Verse Analysis**") that were previously shown to the user
        // as raw literal asterisks since nothing rendered them - render as
        // real bold text instead.
        let formatted = this.escapeHtml(text).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

        // Same idea for "* item" list lines - render a real <ul> instead of
        // leaving the literal asterisk in the text. Each list block is
        // built as one unbroken string (no internal newlines) so it drops
        // cleanly into the surrounding pre-line text without the browser
        // treating whitespace between <li> tags as extra blank lines.
        const lines = formatted.split('\n');
        const parts = [];
        let listBuffer = null;
        for (const line of lines) {
            const bulletMatch = line.match(/^\s*\*\s+(.+)$/);
            if (bulletMatch) {
                if (listBuffer === null) listBuffer = [];
                listBuffer.push(`<li>${bulletMatch[1]}</li>`);
            } else {
                if (listBuffer !== null) {
                    parts.push(`<ul class="commentary-list">${listBuffer.join('')}</ul>`);
                    listBuffer = null;
                }
                parts.push(line);
            }
        }
        if (listBuffer !== null) {
            parts.push(`<ul class="commentary-list">${listBuffer.join('')}</ul>`);
        }
        formatted = parts.join('\n');

        const versePattern = /([1-3]?\s?[A-Z][a-z]+)\s+(\d+):(\d+)(?:-(\d+))?/g;
        formatted = formatted.replace(versePattern, (match, book, chapter, verse) => {
            const cleanBook = book.trim();
            return `<span class="verse-reference-link" onclick="UI.viewChapter('${cleanBook}', ${chapter}, ${verse})" title="Click to view ${cleanBook} ${chapter}">${match}</span>`;
        });

        const strongsPattern = /\b([GH]\d{1,4})\b/g;
        formatted = formatted.replace(strongsPattern, (match, number) => {
            return `<span class="strongs-link" onclick="window.commentaryManager.showStrongsDefinition('${number}', event)" title="Click to see definition">${match}</span>`;
        });

        return formatted;
    }

    async showStrongsDefinition(number, event) {
        event.stopPropagation();
        this.hideStrongsPopup();

        const popup = document.createElement('div');
        popup.className = 'strongs-popup';
        popup.innerHTML = `<div class="strongs-popup-loading">Loading...</div>`;
        document.body.appendChild(popup);
        this.positionStrongsPopup(popup, event.target);

        try {
            const response = await fetch(`${window.API_BASE_URL}/strongs/${number}`);
            if (!response.ok) throw new Error('Not found');
            const data = await response.json();

            const headerParts = [data.strongs];
            if (data.lemma) headerParts.push(data.lemma);
            if (data.xlit) headerParts.push(`(${data.xlit})`);

            popup.innerHTML = `
                <button class="strongs-popup-close" onclick="window.commentaryManager.hideStrongsPopup()" aria-label="Close">&times;</button>
                <div class="strongs-popup-header">${headerParts.join(' &middot; ')}</div>
                <div class="strongs-popup-definition">${data.definition}</div>
                ${data.kjv_translations ? `<div class="strongs-popup-kjv">KJV translations: ${data.kjv_translations}</div>` : ''}
            `;
        } catch (error) {
            popup.innerHTML = `
                <button class="strongs-popup-close" onclick="window.commentaryManager.hideStrongsPopup()" aria-label="Close">&times;</button>
                <div class="strongs-popup-error">No definition found for ${number}</div>
            `;
        }

        setTimeout(() => {
            this._dismissStrongsPopupHandler = () => this.hideStrongsPopup();
            document.addEventListener('click', this._dismissStrongsPopupHandler, { once: true });
        }, 0);
    }

    positionStrongsPopup(popup, targetEl) {
        const rect = targetEl.getBoundingClientRect();
        const popupWidth = 300;
        popup.style.position = 'fixed';
        popup.style.left = `${Math.max(8, Math.min(rect.left, window.innerWidth - popupWidth - 8))}px`;
        popup.style.top = `${rect.bottom + 8}px`;
        popup.style.width = `${popupWidth}px`;
        popup.style.zIndex = '10000';
    }

    hideStrongsPopup() {
        const existing = document.querySelector('.strongs-popup');
        if (existing) existing.remove();
        if (this._dismissStrongsPopupHandler) {
            document.removeEventListener('click', this._dismissStrongsPopupHandler);
            this._dismissStrongsPopupHandler = null;
        }
    }

    // ---- Utilities ----

    clearEmptyState() {
        const empty = this.elements.thread.querySelector('.conversation-empty');
        if (empty) empty.remove();
    }

    scrollToBottom() {
        this.elements.thread.scrollTop = this.elements.thread.scrollHeight;
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

window.commentaryManager = null;
document.addEventListener('DOMContentLoaded', () => {
    window.commentaryManager = new CommentaryManager();
});
