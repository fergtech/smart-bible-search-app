/**
 * ModeManager - generalizes the app's screen visibility from the old
 * binary landing/workspace toggle (WorkspaceLayout.enterWorkspace() /
 * backToLanding()) into three coequal modes: Home (landing), Study (the
 * AI conversation workspace), Read (Bible Reading Mode). Switching modes
 * just shows/hides the three top-level screens - each mode's own internal
 * state (conversation thread, reading location) is owned and persisted by
 * that mode's own module, not by ModeManager.
 */
const ModeManager = {
    current: 'home',
    elements: null,

    init() {
        this.elements = {
            home: document.getElementById('landingScreen'),
            study: document.getElementById('workspace'),
            read: document.getElementById('readWorkspace')
        };
    },

    show(mode) {
        if (!this.elements) this.init();
        if (this.current === mode) return;

        Object.entries(this.elements).forEach(([name, el]) => {
            if (!el) return;
            el.classList.toggle('hidden', name !== mode);
        });

        // The leather background (body::before/::after) is suppressed for
        // ANY non-home mode, not just Study - Reading Mode wants the same
        // plain background, not leather texture bleeding through behind
        // its reading pane.
        document.body.classList.toggle('workspace-active', mode !== 'home');

        this.current = mode;

        if (window.frontendLogger) {
            frontendLogger.logAction('mode_switch', { mode });
        }
    }
};

window.ModeManager = ModeManager;
