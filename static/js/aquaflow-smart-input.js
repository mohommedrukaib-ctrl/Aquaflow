/*
 * AquaFlow Smart Searchable Input
 * Powered by Quantum Axis
 *
 * Features:
 *   - Live search dropdown
 *   - Click "+ Add" or press Enter → auto-save
 *   - Pending value support (auto-save on form submit)
 *   - Uppercase mode
 *   - Enable/disable state
 */

class SmartInput {
    constructor(container) {
        this.container = container;
        this.name = container.dataset.name;
        this.searchUrl = container.dataset.searchUrl;
        this.createUrl = container.dataset.createUrl || '';
        this.label = container.dataset.label || 'Item';
        this.required = container.dataset.required === 'true';
        this.uppercase = container.dataset.uppercase === 'true';
        this.disabled = container.dataset.disabled === 'true';
        this.placeholder = container.dataset.placeholder
            || `Search ${this.label.toLowerCase()}...`;
        this.value = container.dataset.value || '';
        this.displayText = container.dataset.displayText || '';
        this.extraParams = container.dataset.extraParams || '';
        this.resultsKey = container.dataset.resultsKey || 'results';
        this.searchTimer = null;
        this.isOpen = false;
        this.pendingCreate = false;   // true when user typed a new value
        this.currentResults = [];

        this.render();
        this.attachEvents();

        if (this.disabled) this.disable();
    }

    render() {
        this.container.innerHTML = `
            <div class="aq-si-wrapper">
                <div class="aq-si-input-group">
                    <input type="text"
                           class="form-control aq-si-search"
                           placeholder="${this.placeholder}"
                           value="${this.escape(this.displayText)}"
                           autocomplete="off"
                           ${this.disabled ? 'disabled' : ''}>
                    <input type="hidden"
                           name="${this.name}"
                           class="aq-si-value"
                           value="${this.value}">
                    <input type="hidden"
                           name="${this.name}_new"
                           class="aq-si-pending"
                           value="">
                    <button type="button"
                            class="btn btn-outline-secondary aq-si-clear"
                            style="display:${this.value ? 'block' : 'none'}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="aq-si-dropdown" style="display:none;">
                    <div class="aq-si-results"></div>
                </div>
                <div class="aq-si-pending-hint"
                     style="display:none;
                            font-size:11px;
                            color:var(--aq-warning);
                            margin-top:4px;">
                    <i class="fas fa-plus-circle"></i>
                    Will be added as new when form is saved.
                </div>
            </div>
        `;

        this.input = this.container.querySelector('.aq-si-search');
        this.hiddenInput = this.container.querySelector('.aq-si-value');
        this.pendingHidden = this.container.querySelector('.aq-si-pending');
        this.clearBtn = this.container.querySelector('.aq-si-clear');
        this.dropdown = this.container.querySelector('.aq-si-dropdown');
        this.results = this.container.querySelector('.aq-si-results');
        this.pendingHint = this.container.querySelector('.aq-si-pending-hint');

        if (this.uppercase) {
            this.input.style.textTransform = 'uppercase';
        }
    }

    attachEvents() {
        // Type → search
        this.input.addEventListener('input', () => {
    if (this.uppercase) {
        const pos = this.input.selectionStart;
        this.input.value = this.input.value.toUpperCase();
        this.input.setSelectionRange(pos, pos);
    }
    clearTimeout(this.searchTimer);
    const q = this.input.value.trim();

    if (this.hiddenInput.value && this.displayText !== q) {
        this.hiddenInput.value = '';
        this.clearBtn.style.display = 'none';
    }

    this.pendingHidden.value = '';
    this.pendingHint.style.display = 'none';
    this.pendingCreate = false;

    // Even for empty query, show all (with small delay)
    this.searchTimer = setTimeout(() => this.search(q), q.length === 0 ? 100 : 250);
});

        // Focus
        // Focus → show ALL items if input is empty, otherwise search
        this.input.addEventListener('focus', () => {
            const q = this.input.value.trim();
            if (q.length >= 1) {
                this.search(q);
            } else {
                // Show all items on empty focus
                this.search('');
            }
        });

        // Blur → mark pending if no selection
        this.input.addEventListener('blur', () => {
            setTimeout(() => {
                if (this.isOpen) return;   // clicked inside dropdown
                this.markPendingIfNeeded();
            }, 200);
        });

        // Clear button
        this.clearBtn.addEventListener('click', () => {
            this.input.value = '';
            this.hiddenInput.value = '';
            this.pendingHidden.value = '';
            this.displayText = '';
            this.pendingHint.style.display = 'none';
            this.pendingCreate = false;
            this.clearBtn.style.display = 'none';
            this.close();
            this.input.focus();

            this.container.dispatchEvent(new CustomEvent('aq:cleared', {
                bubbles: true,
            }));
        });

        // Click outside → close
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.close();
                this.markPendingIfNeeded();
            }
        });

        // Keyboard nav
        this.input.addEventListener('keydown', (e) => {
            const items = this.results.querySelectorAll('.aq-si-item');
            const current = this.results.querySelector('.aq-si-item.active');

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (!current && items.length > 0) {
                    items[0].classList.add('active');
                } else if (current) {
                    const next = current.nextElementSibling;
                    if (next && next.classList.contains('aq-si-item')) {
                        current.classList.remove('active');
                        next.classList.add('active');
                    }
                }
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (current) {
                    const prev = current.previousElementSibling;
                    if (prev && prev.classList.contains('aq-si-item')) {
                        current.classList.remove('active');
                        prev.classList.add('active');
                    }
                }
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (current) {
                    current.click();
                } else {
                    this.close();
                    this.markPendingIfNeeded();
                }
            } else if (e.key === 'Escape') {
                this.close();
                this.markPendingIfNeeded();
            }
        });
    }

    markPendingIfNeeded() {
        const q = this.input.value.trim();
        if (!q) return;
        if (this.hiddenInput.value) return;
      //  if (!this.createUrl) return;

        // Check if q matches existing result exactly
        const exactMatch = this.currentResults.find(item => {
            const label = item.label || item.name || '';
            return label.toUpperCase() === q.toUpperCase();
        });

        if (exactMatch) {
            this.select(exactMatch);
        } else {
            const value = this.uppercase ? q.toUpperCase() : q;

            // Only fire event if pending value actually changed
            if (this.pendingHidden.value === value) return;

            this.pendingHidden.value = value;
            this.pendingCreate = true;
            this.pendingHint.style.display = 'block';
            this.pendingHint.innerHTML =
                '<i class="fas fa-plus-circle"></i> "' + this.escape(value) + '" will be added as new when form is saved.';

            this.container.dispatchEvent(new CustomEvent('aq:pending', {
                detail: { value },
                bubbles: true,
            }));
        }
    }

    search(q) {
    const sep = this.searchUrl.includes('?') ? '&' : '?';
    const extra = this.extraParams ? '&' + this.extraParams : '';
    // Send q=&all=1 for empty searches to show everything
    const query = q || '';
    const showAll = q ? '' : '&all=1';
    const url = `${this.searchUrl}${sep}q=${encodeURIComponent(query)}${extra}${showAll}`;

    fetch(url)
        .then(r => r.json())
        .then(data => {
            const items = data[this.resultsKey] || [];
            this.currentResults = items;
            this.renderResults(items, q);
            this.open();
        })
        .catch(() => {
            this.results.innerHTML = '<div class="aq-si-empty">Search failed.</div>';
            this.open();
        });
}

    renderResults(items, query) {
        let html = '';
        const displayValue = this.uppercase ? query.toUpperCase() : query;

        if (items.length === 0) {
            html += `
                <div class="aq-si-empty">
                    <i class="fas fa-search me-2 text-muted"></i>
                    No matches for "<strong>${this.escape(displayValue)}</strong>"
                </div>
            `;
        } else {
            items.forEach(item => {
                const label = item.label || item.name || '';
                const meta = item.meta || '';
                html += `
                    <div class="aq-si-item"
                         data-id="${item.id}"
                         data-item='${this.escape(JSON.stringify(item))}'>
                        <div class="aq-si-item-label">${this.escape(label)}</div>
                        ${meta ? `<div class="aq-si-item-meta">${this.escape(meta)}</div>` : ''}
                    </div>
                `;
            });
        }

        // Add "Add new" hint (informative only — actual create happens on submit)
        if (this.createUrl && query.length > 0) {
            const exactExists = items.some(item => {
                const label = item.label || item.name || '';
                return label.toUpperCase() === query.toUpperCase();
            });
            if (!exactExists) {
                html += `
                    <div class="aq-si-add-new" data-query="${this.escape(displayValue)}">
                        <i class="fas fa-plus-circle me-2"></i>
                        Press <kbd>Enter</kbd> or click outside to add
                        "<strong>${this.escape(displayValue)}</strong>" as new ${this.label.toLowerCase()}
                    </div>
                `;
            }
        }

        this.results.innerHTML = html;

        // Item click
        this.results.querySelectorAll('.aq-si-item').forEach(el => {
            el.addEventListener('click', () => {
                const item = JSON.parse(el.dataset.item);
                this.select(item);
            });
            el.addEventListener('mouseover', () => {
                this.results.querySelectorAll('.aq-si-item.active')
                    .forEach(a => a.classList.remove('active'));
                el.classList.add('active');
            });
        });

        // "Add new" click → close dropdown and mark pending
        const addNew = this.results.querySelector('.aq-si-add-new');
        if (addNew) {
            addNew.addEventListener('click', () => {
                this.close();
                this.markPendingIfNeeded();
            });
        }
    }

    select(item) {
        const label = item.label || item.name || '';

        // Don't fire event if same item already selected
        if (String(this.hiddenInput.value) === String(item.id)) {
            this.close();
            return;
        }

        this.input.value = label;
        this.hiddenInput.value = item.id;
        this.pendingHidden.value = '';
        this.pendingCreate = false;
        this.pendingHint.style.display = 'none';
        this.displayText = label;
        this.clearBtn.style.display = 'block';
        this.close();

        this.container.dispatchEvent(new CustomEvent('aq:selected', {
            detail: item,
            bubbles: true,
        }));
    }

    setSelected(item) {
        this.select(item);
    }

    open() {
        this.dropdown.style.display = 'block';
        this.isOpen = true;
    }

    close() {
        this.dropdown.style.display = 'none';
        this.isOpen = false;
    }

    enable() {
        this.disabled = false;
        this.input.disabled = false;
        this.input.style.opacity = 1;
        this.input.style.cursor = 'text';
    }

    disable() {
        this.disabled = true;
        this.input.disabled = true;
        this.input.style.opacity = 0.5;
        this.input.style.cursor = 'not-allowed';
        this.input.value = '';
        this.hiddenInput.value = '';
        this.pendingHidden.value = '';
        this.displayText = '';
        this.clearBtn.style.display = 'none';
        this.pendingHint.style.display = 'none';
        this.close();
    }

    escape(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
}

// Auto-init
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.aq-smart-input').forEach(el => {
        if (!el._smartInput) el._smartInput = new SmartInput(el);
    });
});

window.initSmartInput = function (el) {
    if (!el._smartInput) el._smartInput = new SmartInput(el);
    return el._smartInput;
};