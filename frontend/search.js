/**
 * Workspace Layout - top bar controls, side-panel toggling, and the
 * one-way landing -> workspace transition.
 */
const WorkspaceLayout = {
    elements: null,
    isMobile() {
        return window.innerWidth <= 900;
    },

    init() {
        this.elements = {
            landing: document.getElementById('landingScreen'),
            workspace: document.getElementById('workspace'),
            sidebarToggle: document.getElementById('sidebarToggle'),
            sidebar: document.getElementById('historySidebar'),
            sidebarBackdrop: document.getElementById('sidebarBackdrop'),
            referenceToggle: document.getElementById('referenceToggle'),
            referencePanel: document.getElementById('referencePanel'),
            referenceBackdrop: document.getElementById('referenceBackdrop'),
            newConversationBtn: document.getElementById('newConversationBtn'),
            landingHistoryBtn: document.getElementById('landingHistoryBtn')
        };

        // Sidebar open by default on desktop, collapsed by default on
        // mobile (an always-open overlay on first load would just block
        // the conversation on a phone).
        if (this.isMobile()) {
            this.elements.sidebar.classList.add('collapsed');
            this.elements.referencePanel.classList.add('collapsed');
        }

        this.elements.sidebarToggle.addEventListener('click', () => this.toggleSidebar());
        this.elements.referenceToggle.addEventListener('click', () => this.toggleReferences());
        this.elements.sidebarBackdrop.addEventListener('click', () => this.closeSidebar());
        this.elements.referenceBackdrop.addEventListener('click', () => this.closeReferences());

        this.elements.newConversationBtn.addEventListener('click', () => {
            if (window.commentaryManager) window.commentaryManager.clear();
            if (window.historyManager) window.historyManager.endCurrentSession();
            if (window.frontendLogger) frontendLogger.logAction('new_conversation');
            this.backToLanding();
        });

        if (this.elements.landingHistoryBtn) {
            this.elements.landingHistoryBtn.addEventListener('click', () => this.openHistoryFromLanding());
        }

        this.resumeInProgressSession();
    },

    /**
     * The landing screen's history icon - lets a guest jump straight to a
     * prior conversation without needing to search first, but without
     * putting a whole sidebar/history UI on the landing screen itself
     * (which would compete with its clean, single-focus search moment).
     * It just does the one thing the landing screen can't: opens the
     * workspace with the history drawer already pulled out.
     */
    openHistoryFromLanding() {
        this.enterWorkspace();
        if (this.isMobile()) this.elements.referencePanel.classList.add('collapsed');
        this.elements.sidebar.classList.remove('collapsed');
        this.updateBackdrop();
    },

    /**
     * Resume an in-progress session across a hard refresh. Previously a
     * refresh silently orphaned it: historyManager reloads
     * currentSession from localStorage either way, so it was still there
     * and still accumulating interactions, but nothing put it back on
     * screen (the landing screen showed again) or in the sidebar (which
     * only renders ENDED sessions) - it just looked like the conversation
     * had vanished. That mismatch also broke the "N follow-ups" count: the
     * next query after a refresh started from an empty in-memory
     * CommentaryManager.turns, so it was tagged as a fresh opening
     * question instead of a followup on the session already in storage.
     * Restoring the thread here keeps both in sync again.
     */
    resumeInProgressSession() {
        const session = window.historyManager?.currentSession;
        if (!session || !session.interactions || session.interactions.length === 0) return;

        this.enterWorkspace();
        if (window.commentaryManager) {
            window.commentaryManager.loadThread(session.interactions);
        }
    },

    /** One-way transition from the leather landing screen into the
     * persistent conversation shell - a search never bounces the user back
     * to the landing screen mid-session. The one deliberate exception is
     * "New conversation" in the topbar (see backToLanding()), which is
     * explicitly a request to start over from that landing moment. */
    enterWorkspace() {
        if (!this.elements.workspace.classList.contains('hidden')) return;
        this.elements.landing.classList.add('hidden');
        this.elements.workspace.classList.remove('hidden');
        document.body.classList.add('workspace-active');
    },

    /**
     * The "New conversation" exception to the one-way landing->workspace
     * rule above: rather than just clearing the thread and leaving the
     * user in an empty workspace, this returns them to the landing screen
     * (restoring the leather background too, via workspace-active coming
     * off) with the search box focused, ready to type immediately.
     */
    backToLanding() {
        this.elements.workspace.classList.add('hidden');
        this.elements.landing.classList.remove('hidden');
        document.body.classList.remove('workspace-active');

        const queryInput = window.KeywordSearch?.elements?.queryInput;
        if (queryInput) queryInput.focus();
    },

    /**
     * On mobile, the two drawers are wide enough (280px/320px) to overlap
     * each other on top of a phone-width viewport if both were open at
     * once, not just overlap the conversation - so only one may be open at
     * a time there. On desktop there's room for both side by side (an
     * already-established, tested layout), so this is a no-op there.
     */
    closeOtherPanelOnMobile(keepOpenEl) {
        if (!this.isMobile()) return;
        const other = keepOpenEl === this.elements.sidebar ? this.elements.referencePanel : this.elements.sidebar;
        other.classList.add('collapsed');
    },

    toggleSidebar() {
        const opening = this.elements.sidebar.classList.contains('collapsed');
        if (opening) this.closeOtherPanelOnMobile(this.elements.sidebar);
        this.elements.sidebar.classList.toggle('collapsed');
        this.updateBackdrop();
    },

    closeSidebar() {
        this.elements.sidebar.classList.add('collapsed');
        this.updateBackdrop();
    },

    toggleReferences() {
        const opening = this.elements.referencePanel.classList.contains('collapsed');
        if (opening) this.closeOtherPanelOnMobile(this.elements.referencePanel);
        this.elements.referencePanel.classList.toggle('collapsed');
        this.updateBackdrop();
    },

    closeReferences() {
        this.elements.referencePanel.classList.add('collapsed');
        this.updateBackdrop();
    },

    /** Auto-open the reference drawer when a message is selected - it's a
     * collapsible overlay at every screen size now (see style.css), so this
     * used to be needed only on mobile but now also matters on desktop if
     * the user had closed it. */
    showReferences() {
        this.closeOtherPanelOnMobile(this.elements.referencePanel);
        this.elements.referencePanel.classList.remove('collapsed');
        this.updateBackdrop();
    },

    updateBackdrop() {
        if (!this.isMobile()) {
            this.elements.sidebarBackdrop.classList.remove('visible');
            this.elements.referenceBackdrop.classList.remove('visible');
            return;
        }
        const sidebarOpen = !this.elements.sidebar.classList.contains('collapsed');
        const referencesOpen = !this.elements.referencePanel.classList.contains('collapsed');
        this.elements.sidebarBackdrop.classList.toggle('visible', sidebarOpen);
        this.elements.referenceBackdrop.classList.toggle('visible', referencesOpen);
    }
};

/**
 * KeywordSearch - the single entry point for submitting a query, used by
 * the landing search button, the workspace follow-up input (via
 * commentary.js), history item clicks, and highlight.js's "Ask" flow.
 *
 * Redesign note: this used to run its OWN /hybrid_search call to populate
 * a standalone results list, entirely separate from commentary generation
 * - the root cause of results/commentary mismatches found during testing.
 * It now just hands off to commentaryManager.generateCommentary(), whose
 * single /commentary response drives both the conversation bubble and the
 * reference panel. There is no separate "results list" anymore.
 */
const KeywordSearch = {
    elements: null,

    init() {
        this.elements = {
            queryInput: document.getElementById('queryInput'),
            searchBtn: document.getElementById('searchBtn'),
            feelingHolyBtn: document.getElementById('feelingHolyBtn'),
            blessingModal: document.getElementById('blessingModal'),
            blessingContent: document.getElementById('blessingContent'),
            closeBlessingModal: document.getElementById('closeBlessingModal')
        };

        WorkspaceLayout.init();
        this.setupEventListeners();
    },

    setupEventListeners() {
        this.elements.queryInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });

        this.elements.searchBtn.addEventListener('click', () => this.performSearch());

        if (this.elements.feelingHolyBtn) {
            this.elements.feelingHolyBtn.addEventListener('click', () => this.showBlessing());
        }

        if (this.elements.closeBlessingModal) {
            this.elements.closeBlessingModal.addEventListener('click', () => {
                this.elements.blessingModal.classList.remove('visible');
            });
        }

        if (this.elements.blessingModal) {
            this.elements.blessingModal.addEventListener('click', (e) => {
                if (e.target === this.elements.blessingModal) {
                    this.elements.blessingModal.classList.remove('visible');
                }
            });
        }
    },

    performSearch(queryOverride, maxResultsOverride) {
        const query = (queryOverride ?? this.elements.queryInput.value).trim();
        if (!query) return;

        WorkspaceLayout.enterWorkspace();

        if (window.historyManager && !window.historyManager.currentSession) {
            window.historyManager.startNewSession(query);
        }

        if (window.commentaryManager) {
            window.commentaryManager.generateCommentary(query, maxResultsOverride || 10);
        }

        this.elements.queryInput.value = '';
    },

    /** "I'm Feeling Blessed" - previously a button with no handler at all. */
    async showBlessing() {
        this.elements.blessingModal.classList.add('visible');
        this.elements.blessingContent.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                <div class="spinner" style="margin: 0 auto 1rem;"></div>
                <div>Finding today's blessing...</div>
            </div>
        `;

        try {
            const response = await fetch(`${window.API_URL}/blessing`);
            if (!response.ok) throw new Error('Failed to load blessing');
            const data = await response.json();
            this.currentBlessing = data;

            this.elements.blessingContent.innerHTML = `
                <h3 style="color: var(--accent-primary); margin-bottom: var(--space-sm);">${data.reference}</h3>
                <p style="font-style: italic; line-height: 1.7; margin-bottom: var(--space-lg);">"${data.text}"</p>
                <h4 style="margin-bottom: var(--space-xs);">Reflection</h4>
                <p style="line-height: 1.7; margin-bottom: var(--space-lg);">${data.reflection}</p>
                <h4 style="margin-bottom: var(--space-xs);">Prayer</h4>
                <p style="line-height: 1.7; font-style: italic; margin-bottom: var(--space-lg);">${data.prayer}</p>
                <div class="blessing-share-row">
                    <button class="btn btn-secondary" id="shareEmailBtn">
                        <svg class="inline-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>
                        Email
                    </button>
                    <button class="btn btn-secondary" id="shareTextBtn">
                        <svg class="inline-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
                        Text
                    </button>
                    <button class="btn btn-secondary" id="shareCopyBtn">
                        <svg class="inline-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                        Copy
                    </button>
                </div>
            `;

            document.getElementById('shareEmailBtn').addEventListener('click', () => this.shareBlessing('email'));
            document.getElementById('shareTextBtn').addEventListener('click', () => this.shareBlessing('text'));
            document.getElementById('shareCopyBtn').addEventListener('click', () => this.shareBlessing('copy'));

            if (window.frontendLogger) {
                frontendLogger.logAction('blessing_viewed', { reference: data.reference });
            }
        } catch (error) {
            console.error('Blessing error:', error);
            this.elements.blessingContent.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                    <p style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg> Unable to load today's blessing.</p>
                </div>
            `;
        }
    },

    /**
     * Share the currently displayed blessing via the user's own email or
     * messaging app (mailto:/sms: links), or copy it for pasting into
     * whatever else they use (WhatsApp, Telegram, etc.). No backend
     * email/SMS sending involved - this just hands off to apps already on
     * the user's own device, so there's no server-side mail/SMS
     * infrastructure, API keys, or cost to add for what's a nice-to-have.
     */
    shareBlessing(method) {
        const b = this.currentBlessing;
        if (!b) return;

        const body = `${b.reference}\n"${b.text}"\n\nReflection: ${b.reflection}\n\nPrayer: ${b.prayer}`;

        if (method === 'email') {
            const subject = `Today's Blessing: ${b.reference}`;
            window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
        } else if (method === 'text') {
            window.location.href = `sms:?body=${encodeURIComponent(body)}`;
        } else if (method === 'copy') {
            navigator.clipboard.writeText(body).then(() => {
                const btn = document.getElementById('shareCopyBtn');
                if (!btn) return;
                const original = btn.innerHTML;
                btn.textContent = 'Copied!';
                setTimeout(() => { btn.innerHTML = original; }, 1500);
            }).catch(error => console.error('Copy failed:', error));
        }

        if (window.frontendLogger) {
            frontendLogger.logAction('blessing_shared', { method, reference: b.reference });
        }
    }
};

window.KeywordSearch = KeywordSearch;
window.WorkspaceLayout = WorkspaceLayout;
