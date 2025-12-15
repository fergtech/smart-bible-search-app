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

        // Show modal with loading state
        this.elements.modalTitle.textContent = `${book} ${chapter}`;
        this.elements.modalBody.innerHTML = `
            <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                <div style="font-size: 2rem; margin-bottom: 1rem;">📖</div>
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
                    <div style="font-size: 2rem; margin-bottom: 1rem; color: #ef4444;">⚠️</div>
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
                background-color: rgba(16, 163, 127, 0.1);
                border-left: 3px solid var(--accent-primary);
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
    init() {
        this.themeToggle = document.getElementById('themeToggle');
        this.themeIcon = document.getElementById('themeIcon');
        
        // Load saved theme or use system preference
        const savedTheme = localStorage.getItem('theme');
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const initialTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
        
        this.setTheme(initialTheme);
        
        // Setup toggle button
        if (this.themeToggle) {
            this.themeToggle.addEventListener('click', () => this.toggleTheme());
        }

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('theme')) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });
    },

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    },

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        
        if (this.themeIcon) {
            this.themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
        }
    }
};

// Expose functions globally for inline handlers if needed
window.UI = UI;
window.viewChapter = (book, chapter, verse) => UI.viewChapter(book, chapter, verse);
