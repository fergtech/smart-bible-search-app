/**
 * SidePanel - reusable off-canvas drawer behavior (open/close/collapse,
 * mobile backdrop dimming, collapsed-by-default on mobile), extracted from
 * WorkspaceLayout, which used to hardcode this against exactly one sidebar
 * (#historySidebar). Both the Study workspace's history sidebar and Bible
 * Reading Mode's book-navigation sidebar are instances of this class,
 * sharing the same .history-sidebar-panel / .sidebar-handle /
 * .panel-backdrop CSS - none of it references "history", so no CSS
 * changes were needed to make it generic, only this behavior extraction.
 */
class SidePanel {
    static isMobile() {
        return window.innerWidth <= 900;
    }

    constructor({ panelEl, toggleEl, backdropEl }) {
        this.panelEl = panelEl;
        this.toggleEl = toggleEl;
        this.backdropEl = backdropEl;

        // Collapsed by default on mobile - an always-open overlay on first
        // load would just block the content behind it on a phone.
        if (SidePanel.isMobile()) {
            this.panelEl.classList.add('collapsed');
        }

        this.toggleEl.addEventListener('click', () => this.toggle());
        this.backdropEl.addEventListener('click', () => this.close());
    }

    isOpen() {
        return !this.panelEl.classList.contains('collapsed');
    }

    toggle() {
        this.panelEl.classList.toggle('collapsed');
        this.updateBackdrop();
    }

    open() {
        this.panelEl.classList.remove('collapsed');
        this.updateBackdrop();
    }

    close() {
        this.panelEl.classList.add('collapsed');
        this.updateBackdrop();
    }

    updateBackdrop() {
        if (!SidePanel.isMobile()) {
            this.backdropEl.classList.remove('visible');
            return;
        }
        this.backdropEl.classList.toggle('visible', this.isOpen());
    }
}

window.SidePanel = SidePanel;
