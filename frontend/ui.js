/**
 * UI Module - Modern interface interactions and theme management
 * Handles: modals, status messages, theme toggle, accessibility
 */

const UI = {
    elements: {},

    /**
     * Initialize UI module
     */
    init() {
        this.elements = {
            statusMessage: document.getElementById('statusMessage'),
            modal: document.getElementById('chapterModal'),
            modalTitle: document.getElementById('modalTitle'),
            modalBody: document.getElementById('chapterContent'),
            closeModalBtn: document.getElementById('closeModal')
        };

        this.setupEventListeners();
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Modal close button
        if (this.elements.closeModalBtn) {
            this.elements.closeModalBtn.addEventListener('click', () => this.closeModal());
        }

        // Close modal on background click
        if (this.elements.modal) {
            this.elements.modal.addEventListener('click', (e) => {
                if (e.target === this.elements.modal) {
                    this.closeModal();
                }
            });
        }

        // Close modal with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.elements.modal.classList.contains('visible')) {
                this.closeModal();
            }
        });
    },

    /**
     * Show status message
     */
    showStatus(message, type = 'info') {
        if (!this.elements.statusMessage) return;

        this.elements.statusMessage.textContent = message;
        this.elements.statusMessage.className = `status-message visible ${type}`;

        // Auto-hide after 5 seconds for success/info messages
        if (type !== 'error') {
            setTimeout(() => this.hideStatus(), 5000);
        }
    },

    /**
     * Hide status message
     */
    hideStatus() {
        if (this.elements.statusMessage) {
            this.elements.statusMessage.classList.remove('visible');
        }
    },

    /**
     * View full chapter in modal
     */
    async viewChapter(book, chapter, highlightVerse) {
        if (!this.elements.modal) return;

        // Log chapter view
        if (window.frontendLogger) {
            frontendLogger.logChapterView(book, chapter, highlightVerse);
        }

        // Show modal with loading state
        this.elements.modalTitle.textContent = `${book} ${chapter}`;
        this.elements.modalBody.innerHTML = `
            <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                <div style="display: flex; justify-content: center; margin-bottom: 1rem;"><svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg></div>
                <div>Loading chapter...</div>
            </div>
        `;
        this.elements.modal.classList.add('visible');

        try {
            const response = await fetch(`${window.API_URL}/chapter/${encodeURIComponent(book)}/${chapter}`);
            
            if (!response.ok) {
                throw new Error(`Failed to load chapter: ${response.statusText}`);
            }

            const verses = await response.json();
            
            // Display chapter verses
            this.elements.modalBody.innerHTML = `
                <div class="chapter-verses">
                    ${verses.map(v => `
                        <div class="chapter-verse ${v.verse === highlightVerse ? 'highlighted' : ''}" 
                             id="chapter-verse-${v.verse}">
                            <span class="chapter-verse-num">${v.verse}</span>
                            <span class="chapter-verse-text">${v.text}</span>
                        </div>
                    `).join('')}
                </div>
            `;

            // Add chapter verse styles dynamically
            this.addChapterStyles();

            // Scroll to highlighted verse
            setTimeout(() => {
                const highlightedVerse = document.getElementById(`chapter-verse-${highlightVerse}`);
                if (highlightedVerse) {
                    highlightedVerse.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }, 100);

        } catch (error) {
            console.error('Error loading chapter:', error);
            this.elements.modalBody.innerHTML = `
                <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                    <div style="display: flex; justify-content: center; margin-bottom: 1rem; color: #ef4444;"><svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg></div>
                    <p style="color: #ef4444; margin-bottom: 1rem;">Error loading chapter</p>
                    <p style="font-size: 0.875rem;">${error.message}</p>
                    <button class="btn btn-secondary" onclick="UI.closeModal()" style="margin-top: 1.5rem;">
                        Close
                    </button>
                </div>
            `;
        }
    },

    /**
     * Add chapter verse styles
     */
    addChapterStyles() {
        if (document.getElementById('chapter-styles')) return;

        const style = document.createElement('style');
        style.id = 'chapter-styles';
        style.textContent = `
            .chapter-verses {
                line-height: 1.8;
            }
            .chapter-verse {
                padding: 0.75rem 1rem;
                border-radius: 0.5rem;
                transition: background-color 0.2s;
                margin-bottom: 0.25rem;
            }
            .chapter-verse:hover {
                background-color: var(--bg-tertiary);
            }
            .chapter-verse.highlighted {
                background-color: rgba(215, 194, 168, 0.1);
            }
            .chapter-verse-num {
                display: inline-block;
                width: 2.5rem;
                font-weight: 600;
                color: var(--text-tertiary);
                font-size: 0.875rem;
            }
            .chapter-verse-text {
                color: var(--text-primary);
            }
        `;
        document.head.appendChild(style);
    },

    /**
     * Close modal
     */
    closeModal() {
        if (this.elements.modal) {
            this.elements.modal.classList.remove('visible');
        }
    }
};

/**
 * Theme Manager - Handle dark/light mode toggle
 */
const ThemeManager = {
    /**
     * Theme always tracks the OS/browser's prefers-color-scheme, live -
     * no persisted override. The previous version wrote the user's choice
     * to localStorage on every toggle click, which then permanently
     * disabled system-following forever (a single test click during dev
     * was enough to leave a real test session stuck on the wrong theme,
     * with no way back short of manually clearing site data). The toggle
     * button still works, but only as a same-session preview - it resets
     * to whatever the system says on the next load, by design.
     */
    init() {
        // Two toggle buttons now (workspace topbar + landing screen), both
        // sharing these classes so this doesn't need separate wiring for
        // each new one added later.
        this.themeToggles = document.querySelectorAll('.theme-toggle-btn');
        this.themeIcons = document.querySelectorAll('.theme-icon-target');

        // Clean up any theme pinned by the old localStorage-based logic
        // so previously-affected sessions (including this app's own dev/
        // test sessions) immediately resume following system preference.
        localStorage.removeItem('theme');

        this.mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        this.applySystemTheme();

        this.themeToggles.forEach(btn => {
            btn.addEventListener('click', () => this.toggleTheme());
        });

        this.mediaQuery.addEventListener('change', () => this.applySystemTheme());
    },

    applySystemTheme() {
        this.setTheme(this.mediaQuery.matches ? 'dark' : 'light');
    },

    /** Session-only preview - intentionally not persisted, see init(). */
    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    },

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);

        this.themeIcons.forEach(icon => {
            icon.innerHTML = theme === 'dark' ? this.icons.sun : this.icons.moon;
        });
    },

    icons: {
        sun: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>',
        moon: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>'
    }
};

// Expose functions globally for inline handlers if needed
window.UI = UI;
window.viewChapter = (book, chapter, verse) => UI.viewChapter(book, chapter, verse);

/* ============================================================
   TEMPORARY DEBUG LOGGING - mobile scroll investigation.
   DELETE THIS BLOCK once the mobile scrolling issue is confirmed
   fixed (or root-caused further) on a real device. Not meant to
   ship long-term - it exists only so scroll events can be read
   from a real phone's remote-debugging console (Safari Web
   Inspector over USB for iOS, chrome://inspect for Android) to see
   which container (if any) is actually receiving touch-scroll
   events, since this can't be verified from here.

   Each listener is passive (won't itself affect scroll performance
   or block the browser's own gesture handling) and throttled to
   roughly once every 300ms per element so a long scroll doesn't
   flood the console.
   ============================================================ */
(function setupMobileScrollDebugLogging() {
    const targets = [
        { label: 'document/body', el: document },
        { label: 'conversation-thread', el: document.getElementById('conversationThread') },
        { label: 'reference-list (evidence rail)', el: document.getElementById('referenceList') },
        { label: 'history-list', el: document.getElementById('historyList') }
    ];

    targets.forEach(({ label, el }) => {
        if (!el) {
            console.log(`[SCROLL-DEBUG] ${label}: element not found in DOM at setup time`);
            return;
        }

        let lastLogged = 0;
        el.addEventListener('scroll', () => {
            const now = Date.now();
            if (now - lastLogged < 300) return;
            lastLogged = now;

            const scrollTop = el.scrollTop ?? window.scrollY;
            const scrollHeight = el.scrollHeight ?? document.documentElement.scrollHeight;
            const clientHeight = el.clientHeight ?? window.innerHeight;
            console.log(`[SCROLL-DEBUG] ${label}: scrollTop=${scrollTop} scrollHeight=${scrollHeight} clientHeight=${clientHeight}`);
        }, { passive: true });
    });

    console.log('[SCROLL-DEBUG] Mobile scroll debug logging active. Watching:', targets.map(t => t.label).join(', '));
})();
