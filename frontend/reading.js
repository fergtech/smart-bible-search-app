/**
 * Reading - Bible Reading Mode: browse books -> browse chapters -> read
 * scripture -> see study tools for the current chapter.
 *
 * Reuses, rather than duplicates: UI.renderChapterVersesHTML (same verse
 * markup as the chapter modal, so highlight.js's existing "Ask" flow works
 * unmodified), the SidePanel class (same drawer behavior as the Study
 * workspace's history sidebar), and the .reference-panel/.verse-card CSS
 * family (same "citation chip" look as the evidence rail) for the study
 * rail. Chat-session history and book/chapter navigation are different
 * enough data shapes that this is its own renderer rather than trying to
 * force history.js's HistoryManager to also understand books - see the
 * Reading Mode plan for why that tradeoff was made deliberately.
 */
const Reading = {
    elements: null,
    bookPanel: null,
    books: null,
    lastLocationKey: 'bible_reading_last_location',
    lastLocation: null,
    expandedBook: null,

    init() {
        this.elements = {
            workspace: document.getElementById('readWorkspace'),
            bookSidebar: document.getElementById('bookSidebar'),
            bookSidebarToggle: document.getElementById('bookSidebarToggle'),
            bookSidebarBackdrop: document.getElementById('bookSidebarBackdrop'),
            bookList: document.getElementById('bookList'),
            readingContent: document.getElementById('readingContent'),
            readingTitle: document.getElementById('readingTitle'),
            prevChapterBtn: document.getElementById('prevChapterBtn'),
            nextChapterBtn: document.getElementById('nextChapterBtn'),
            studyPanel: document.getElementById('studyPanel'),
            studySubtitle: document.getElementById('studySubtitle'),
            studyList: document.getElementById('studyList'),
            goReadFromLanding: document.getElementById('goReadFromLanding'),
            goReadFromStudy: document.getElementById('goReadFromStudy'),
            goHomeFromRead: document.getElementById('goHomeFromRead'),
            goStudyFromRead: document.getElementById('goStudyFromRead')
        };

        this.bookPanel = new SidePanel({
            panelEl: this.elements.bookSidebar,
            toggleEl: this.elements.bookSidebarToggle,
            backdropEl: this.elements.bookSidebarBackdrop
        });

        this.loadLastLocation();

        if (this.elements.prevChapterBtn) {
            this.elements.prevChapterBtn.addEventListener('click', () => this.stepChapter(-1));
        }
        if (this.elements.nextChapterBtn) {
            this.elements.nextChapterBtn.addEventListener('click', () => this.stepChapter(1));
        }

        [this.elements.goReadFromLanding, this.elements.goReadFromStudy].forEach(btn => {
            if (btn) btn.addEventListener('click', () => this.enter());
        });
        [this.elements.goHomeFromRead].forEach(btn => {
            if (btn) btn.addEventListener('click', () => ModeManager.show('home'));
        });
        [this.elements.goStudyFromRead].forEach(btn => {
            if (btn) btn.addEventListener('click', () => ModeManager.show('study'));
        });
    },

    /** Entry point from any "Read" icon - switches mode and loads the
     * book list (once) plus whichever chapter was last read, defaulting
     * to Genesis 1 the very first time. */
    async enter() {
        ModeManager.show('read');

        if (!this.books) {
            await this.loadBooks();
        }

        if (!this.currentBook) {
            const start = this.lastLocation || { book: 'Genesis', chapter: 1 };
            this.loadChapter(start.book, start.chapter);
        }
    },

    async loadBooks() {
        try {
            const response = await fetch(`${window.API_BASE_URL}/books`);
            if (!response.ok) throw new Error('Failed to load books');
            this.books = await response.json();
            this.renderBookList();
        } catch (error) {
            console.error('Failed to load book list:', error);
            this.elements.bookList.innerHTML = `
                <div class="history-empty">
                    <p>Unable to load the book list.</p>
                </div>
            `;
        }
    },

    renderBookList() {
        const section = (title, books) => `
            <div class="history-group">
                <div class="history-group-date">${title}</div>
                ${books.map(b => this.renderBookItem(b)).join('')}
            </div>
        `;

        const ot = this.books.filter(b => b.testament === 'OT');
        const nt = this.books.filter(b => b.testament === 'NT');
        this.elements.bookList.innerHTML = section('Old Testament', ot) + section('New Testament', nt);

        this.elements.bookList.querySelectorAll('.book-item').forEach(item => {
            item.addEventListener('click', () => this.toggleBook(item.dataset.book));
        });
    },

    renderBookItem(book) {
        return `
            <div class="history-item book-item" data-book="${book.name}">
                <div class="history-item-content">
                    <div class="history-item-text">
                        <div class="history-item-query">${book.name}</div>
                    </div>
                </div>
            </div>
            <div class="chapter-grid" data-chapters-for="${book.name}" style="display: none;"></div>
        `;
    },

    toggleBook(bookName) {
        const grid = this.elements.bookList.querySelector(`.chapter-grid[data-chapters-for="${CSS.escape(bookName)}"]`);
        if (!grid) return;

        const opening = grid.style.display === 'none';

        // Only one book's chapter grid open at a time - a 66-item drawer
        // with several expanded chapter grids at once would be unusable.
        this.elements.bookList.querySelectorAll('.chapter-grid').forEach(g => { g.style.display = 'none'; });

        if (opening) {
            const book = this.books.find(b => b.name === bookName);
            if (book && grid.children.length === 0) {
                grid.innerHTML = Array.from({ length: book.chapter_count }, (_, i) => i + 1)
                    .map(n => `<button class="chapter-grid-btn" data-book="${book.name}" data-chapter="${n}">${n}</button>`)
                    .join('');
                grid.querySelectorAll('.chapter-grid-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        this.loadChapter(btn.dataset.book, Number(btn.dataset.chapter));
                        if (SidePanel.isMobile()) this.bookPanel.close();
                    });
                });
            }
            grid.style.display = 'flex';
        }
    },

    async loadChapter(book, chapter) {
        this.currentBook = book;
        this.currentChapter = chapter;
        this.saveLastLocation(book, chapter);
        this.activeWord = null;
        this.wordIndex = {};
        this.studyExtras = { commentary: [], concepts: [] };

        if (this.elements.readingTitle) {
            this.elements.readingTitle.textContent = `${book} ${chapter}`;
        }

        this.elements.readingContent.innerHTML = `
            <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                <div class="spinner" style="margin: 0 auto 1rem;"></div>
                <div>Loading chapter...</div>
            </div>
        `;
        // Conditionally rendered, same as the evidence rail: nothing is
        // selected yet, so there's nothing to show. It reappears the
        // moment the user clicks an interactive word in the text below,
        // not before - see showWordStudy().
        this.elements.studyPanel.classList.add('hidden');

        try {
            const response = await fetch(`${window.API_BASE_URL}/chapter/${encodeURIComponent(book)}/${chapter}`);
            if (!response.ok) throw new Error('Chapter not found');
            const verses = await response.json();

            this.elements.readingContent.innerHTML = window.UI.renderChapterVersesHTML(verses);
            this.elements.readingContent.scrollTop = 0;

            if (window.frontendLogger) {
                frontendLogger.logChapterView(book, chapter);
            }
        } catch (error) {
            console.error('Failed to load chapter:', error);
            this.elements.readingContent.innerHTML = `
                <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                    <p style="color: #ef4444;">Unable to load ${book} ${chapter}.</p>
                </div>
            `;
        }

        this.loadStudyData(book, chapter);
    },

    stepChapter(direction) {
        if (!this.currentBook || !this.books) return;
        const book = this.books.find(b => b.name === this.currentBook);
        if (!book) return;

        let nextChapter = this.currentChapter + direction;
        if (nextChapter >= 1 && nextChapter <= book.chapter_count) {
            this.loadChapter(this.currentBook, nextChapter);
        }
    },

    /**
     * Fetches this chapter's study data and makes its key words clickable
     * in the reading text - it does NOT populate or show the rail itself
     * anymore. The rail is a response to curiosity (see showWordStudy()),
     * not a preloaded dump: word_studies/commentary/concepts are fetched
     * once per chapter and held in memory so clicking a word is instant,
     * but nothing renders until that click happens.
     */
    async loadStudyData(book, chapter) {
        try {
            const response = await fetch(`${window.API_BASE_URL}/chapter/${encodeURIComponent(book)}/${chapter}/study`);
            if (!response.ok) throw new Error('Study data unavailable');
            const data = await response.json();

            this.studyExtras = {
                commentary: data.commentary || [],
                concepts: data.concepts || []
            };

            // Group by word (lowercased) rather than leaving a flat list -
            // get_word_studies() deliberately returns up to 4 Strong's
            // SENSES per English word (e.g. "earth" can map to 4 different
            // Hebrew words), which is correct data but reads as duplicate
            // noise as a flat list. Grouped, it's "here are earth's actual
            // senses," which is the point.
            this.wordIndex = {};
            (data.word_studies || []).forEach(w => {
                const key = w.word.toLowerCase();
                (this.wordIndex[key] ||= []).push(w);
            });

            this.annotateStudyWords();
        } catch (error) {
            console.error('Failed to load study data:', error);
            this.wordIndex = {};
        }
    },

    /**
     * Makes the chapter's significant words (exactly the ones
     * get_word_studies() already identified - not every word in the text)
     * clickable in place, dotted-underlined like a dictionary lookup. This
     * is the discovery mechanism instead of a persistent "select a word"
     * placeholder in the rail: the text itself signals what's explorable.
     */
    annotateStudyWords() {
        const words = Object.keys(this.wordIndex);
        if (words.length === 0) return;

        const escapeRegex = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const pattern = new RegExp(`\\b(${words.map(escapeRegex).join('|')})\\b`, 'gi');

        this.elements.readingContent.querySelectorAll('.chapter-verse-text').forEach(el => {
            el.innerHTML = el.textContent.replace(pattern, (match) =>
                `<span class="study-word" data-word="${match.toLowerCase()}">${match}</span>`
            );
        });

        this.elements.readingContent.querySelectorAll('.study-word').forEach(span => {
            span.addEventListener('click', () => this.showWordStudy(span.dataset.word));
        });
    },

    /**
     * The rail is driven entirely by this - clicking a different word
     * replaces its contents rather than adding to them, so it always
     * reflects only the current selection, never an accumulating dump.
     */
    showWordStudy(word) {
        const senses = this.wordIndex[word];
        if (!senses || senses.length === 0) return;

        this.activeWord = word;
        this.elements.readingContent.querySelectorAll('.study-word').forEach(span => {
            span.classList.toggle('active', span.dataset.word === word);
        });

        const label = word.charAt(0).toUpperCase() + word.slice(1);
        this.elements.studySubtitle.textContent = `Word Study: ${label}`;

        let html = `<div class="reference-tier-label">Strong's References</div>`;
        html += senses.map(s => this.renderStrongsSense(s)).join('');

        if (this.studyExtras.commentary.length) {
            html += `<div class="reference-tier-label">Commentary for This Passage</div>`;
            html += this.studyExtras.commentary.map(c => this.renderTextChip(c.source || 'Commentary', c.text)).join('');
        }
        if (this.studyExtras.concepts.length) {
            html += `<div class="reference-tier-label">Related Concepts</div>`;
            html += this.studyExtras.concepts.map(c => this.renderTextChip(c.concept || 'Concept', c.text)).join('');
        }

        this.elements.studyList.innerHTML = html;
        this.elements.studyPanel.classList.remove('hidden');

        this.elements.studyList.querySelectorAll('.study-sense').forEach(chip => {
            chip.addEventListener('click', () => this.expandStrongsSense(chip));
        });
        this.elements.studyList.querySelectorAll('.expandable-chip').forEach(chip => {
            chip.addEventListener('click', () => chip.classList.toggle('expanded'));
        });
    },

    renderStrongsSense(s) {
        return `
            <article class="verse-card study-sense" role="listitem" data-strongs="${s.strongs}">
                <h3 class="verse-reference">${this.escapeHtml(s.word)} <span style="font-weight: 400; color: var(--text-tertiary);">${s.strongs}${s.xlit ? ' · ' + this.escapeHtml(s.xlit) : ''}</span></h3>
                <div class="verse-text">${this.escapeHtml(s.definition || '')}</div>
                <div class="study-sense-detail"></div>
            </article>
        `;
    },

    /**
     * Every item in the rail is actionable, per the redesign brief -
     * clicking a Strong's sense fetches its FULL entry (pronunciation,
     * root word, KJV usage stats) instead of just the short gloss already
     * shown, expanding in place. Toggles closed on a second click without
     * re-fetching.
     */
    async expandStrongsSense(chipEl) {
        const detail = chipEl.querySelector('.study-sense-detail');
        if (!detail) return;

        if (detail.classList.contains('open')) {
            detail.classList.remove('open');
            detail.innerHTML = '';
            return;
        }

        detail.classList.add('open');
        detail.innerHTML = `<div class="study-detail-loading">Loading full entry...</div>`;

        try {
            const response = await fetch(`${window.API_BASE_URL}/strongs/${chipEl.dataset.strongs}`);
            if (!response.ok) throw new Error('Not found');
            const data = await response.json();

            detail.innerHTML = `
                ${data.pronunciation ? `<div class="study-detail-row"><strong>Pronunciation:</strong> ${this.escapeHtml(data.pronunciation)}</div>` : ''}
                ${data.lemma ? `<div class="study-detail-row"><strong>Root word:</strong> ${this.escapeHtml(data.lemma)}</div>` : ''}
                <div class="study-detail-row">${this.escapeHtml(data.definition || '')}</div>
                ${data.kjv_translations ? `<div class="study-detail-row"><strong>KJV usage:</strong> ${this.escapeHtml(data.kjv_translations)}</div>` : ''}
            `;
        } catch (error) {
            detail.innerHTML = `<div class="study-detail-row">Unable to load full entry.</div>`;
        }
    },

    /** Commentary/concept chips start clamped to 2 lines (see .verse-text
     * in style.css) - clicking expands to the full passage in place. */
    renderTextChip(title, text) {
        return `
            <article class="verse-card expandable-chip" role="listitem">
                <h3 class="verse-reference">${this.escapeHtml(title)}</h3>
                <div class="verse-text">${this.escapeHtml(text || '')}</div>
            </article>
        `;
    },

    saveLastLocation(book, chapter) {
        this.lastLocation = { book, chapter };
        try {
            localStorage.setItem(this.lastLocationKey, JSON.stringify(this.lastLocation));
        } catch (error) {
            console.error('Failed to save reading location:', error);
        }
    },

    loadLastLocation() {
        try {
            const stored = localStorage.getItem(this.lastLocationKey);
            if (stored) this.lastLocation = JSON.parse(stored);
        } catch (error) {
            this.lastLocation = null;
        }
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

window.Reading = Reading;

document.addEventListener('DOMContentLoaded', () => {
    Reading.init();
});
