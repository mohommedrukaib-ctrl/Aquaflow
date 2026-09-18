/*
 * AquaFlow Theme Switcher + Sidebar Toggle
 * Powered by Quantum Axis
 */

(function () {
    const THEME_KEY = 'aquaflow-theme';

    function getTheme() {
        return localStorage.getItem(THEME_KEY) || 'light';
    }

    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(THEME_KEY, theme);
        updateToggleIcon(theme);
    }

    function toggleTheme() {
        const current = getTheme();
        setTheme(current === 'light' ? 'dark' : 'light');
    }

    function updateToggleIcon(theme) {
        const icon = document.querySelector('#themeToggle i');
        if (!icon) return;
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }

    // Apply theme on load
    setTheme(getTheme());

    document.addEventListener('DOMContentLoaded', function () {
        updateToggleIcon(getTheme());

        // Theme toggle
        const btn = document.getElementById('themeToggle');
        if (btn) {
            btn.addEventListener('click', toggleTheme);
        }

        // ─── Sidebar Toggle (responsive) ─────────────────
        const sidebarToggle = document.getElementById('sidebarToggle');

        function isMobile() {
            return window.innerWidth <= 992;
        }

        function toggleSidebar() {
            if (isMobile()) {
                // Mobile: toggle 'aq-sidebar-open' class
                document.body.classList.toggle('aq-sidebar-open');
            } else {
                // Desktop: toggle collapse
                document.body.classList.toggle('aq-sidebar-collapsed');
                localStorage.setItem(
                    'aquaflow-sidebar',
                    document.body.classList.contains('aq-sidebar-collapsed')
                        ? 'collapsed'
                        : 'open'
                );
            }
        }

        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', function (e) {
                e.stopPropagation();
                toggleSidebar();
            });
        }

        // Create overlay for mobile
        if (!document.getElementById('sidebarOverlay')) {
            const overlay = document.createElement('div');
            overlay.className = 'aq-sidebar-overlay';
            overlay.id = 'sidebarOverlay';
            overlay.addEventListener('click', () => {
                document.body.classList.remove('aq-sidebar-open');
            });
            document.body.appendChild(overlay);
        }

        // Close sidebar when clicking nav items on mobile
        document.querySelectorAll('.aq-nav-item').forEach(link => {
            link.addEventListener('click', () => {
                if (isMobile()) {
                    document.body.classList.remove('aq-sidebar-open');
                }
            });
        });

        // Restore sidebar state (desktop only)
        if (!isMobile()) {
            if (localStorage.getItem('aquaflow-sidebar') === 'collapsed') {
                document.body.classList.add('aq-sidebar-collapsed');
            }
        }

        // Handle window resize
        window.addEventListener('resize', function () {
            if (!isMobile()) {
                // Desktop: remove mobile open class
                document.body.classList.remove('aq-sidebar-open');
            } else {
                // Mobile: remove desktop collapsed class
                document.body.classList.remove('aq-sidebar-collapsed');
            }
        });

        // Fullscreen toggle
        const fsBtn = document.getElementById('fullscreenToggle');
        if (fsBtn) {
            fsBtn.addEventListener('click', function () {
                if (!document.fullscreenElement) {
                    document.documentElement.requestFullscreen();
                } else {
                    document.exitFullscreen();
                }
            });
        }
    });
})();