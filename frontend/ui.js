/**
 * UI Utilities - Modal, verse expansion, and UI interactions
 */

const UI = {
    /**
     * Toggle verse expansion
     */
    toggleVerse(index) {
        const card = document.getElementById(`verse-${index}`);
        const btn = document.getElementById(`toggle-btn-${index}`);
        
        if (card.classList.contains('expanded')) {
            card.classList.remove('expanded');
            btn.textContent = 'Expand';
        } else {
            card.classList.add('expanded');
            btn.textContent = 'Collapse';
        }
    },

    /**
     * View full chapter in modal
     */
    async viewChapter(book, chapter, highlightVerse) {
        const modal = document.getElementById('chapterModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalBody = document.getElementById('modalBody');

        // Show modal with loading state
        modalTitle.textContent = `${book} ${chapter}`;
        modalBody.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">Loading chapter...</div>';
        modal.classList.add('active');

        try {
            const response = await fetch(`${window.API_URL}/chapter/${encodeURIComponent(book)}/${chapter}`);
            
            if (!response.ok) {
                throw new Error(`Failed to load chapter: ${response.statusText}`);
            }

            const verses = await response.json();
            
            // Display chapter verses
            modalBody.innerHTML = verses.map(v => `
                <div class="chapter-verse ${v.verse === highlightVerse ? 'highlighted' : ''}" id="chapter-verse-${v.verse}">
                    <span class="chapter-verse-num">${v.verse}</span>
                    <span>${v.text}</span>
                </div>
            `).join('');

            // Scroll to highlighted verse
            setTimeout(() => {
                const highlightedVerse = document.getElementById(`chapter-verse-${highlightVerse}`);
                if (highlightedVerse) {
                    highlightedVerse.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }, 100);

        } catch (error) {
            console.error('Error loading chapter:', error);
            modalBody.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #cc0000;">
                    <p>Error loading chapter: ${error.message}</p>
                    <button class="btn-small" onclick="UI.closeChapterModal()" style="margin-top: 20px;">Close</button>
                </div>
            `;
        }
    },

    /**
     * Close chapter modal
     */
    closeChapterModal() {
        document.getElementById('chapterModal').classList.remove('active');
    },

    /**
     * Show status message
     */
    showStatus(message, type) {
        const status = document.getElementById('status');
        status.className = `status ${type}`;
        status.textContent = message;
        status.style.display = 'block';
    },

    /**
     * Hide status message
     */
    hideStatus() {
        const status = document.getElementById('status');
        status.className = 'status';
        status.style.display = 'none';
    }
};

// Event listeners for modal
document.addEventListener('DOMContentLoaded', () => {
    // Close modal when clicking outside
    const modal = document.getElementById('chapterModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target.id === 'chapterModal') {
                UI.closeChapterModal();
            }
        });
    }

    // Close modal with Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            UI.closeChapterModal();
        }
    });
});

// Expose functions globally for inline onclick handlers
window.toggleVerse = UI.toggleVerse.bind(UI);
window.viewChapter = UI.viewChapter.bind(UI);
window.closeChapterModal = UI.closeChapterModal.bind(UI);
