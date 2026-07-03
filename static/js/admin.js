/* Bodhini AI - Admin Panel JavaScript */
document.addEventListener('DOMContentLoaded', function () {
    initSidebar();
    initToasts();
    initModals();
    initTabs();
    initTableLoading();
});

function initSidebar() {
    const toggle = document.getElementById('adminMenuToggle');
    const sidebar = document.getElementById('adminSidebar');
    const overlay = document.getElementById('adminOverlay');

    if (toggle && sidebar) {
        toggle.addEventListener('click', function () {
            sidebar.classList.toggle('open');
            if (overlay) overlay.classList.toggle('active');
        });
    }
    if (overlay) {
        overlay.addEventListener('click', function () {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        });
    }
}

function initToasts() {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const flashes = document.querySelectorAll('[data-flash]');
    flashes.forEach(function (el) {
        showToast(el.dataset.flash, el.textContent.trim());
        el.remove();
    });
}

function showToast(type, message) {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'admin-toast-container';
        document.body.appendChild(container);
    }

    const icons = { success: 'fa-check-circle', error: 'fa-times-circle', warning: 'fa-exclamation-triangle', info: 'fa-info-circle' };
    const toast = document.createElement('div');
    toast.className = 'admin-toast ' + (type || 'info');
    toast.innerHTML = '<i class="fas ' + (icons[type] || icons.info) + '"></i><span>' + message + '</span>';
    container.appendChild(toast);

    setTimeout(function () {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        toast.style.transition = 'all 0.3s';
        setTimeout(function () { toast.remove(); }, 300);
    }, 4000);
}

function initModals() {
    document.querySelectorAll('[data-confirm]').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const form = btn.closest('form');
            const message = btn.dataset.confirm || 'Are you sure?';
            showConfirmModal(message, function () {
                if (form) form.submit();
            });
        });
    });
}

function showConfirmModal(message, onConfirm) {
    let overlay = document.getElementById('confirmModal');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'confirmModal';
        overlay.className = 'admin-modal-overlay';
        overlay.innerHTML = '<div class="admin-modal"><h3>Confirm Action</h3><p id="confirmMessage"></p><div class="admin-modal-actions"><button class="admin-btn admin-btn-outline" id="confirmCancel">Cancel</button><button class="admin-btn admin-btn-danger" id="confirmOk">Confirm</button></div></div>';
        document.body.appendChild(overlay);
    }
    document.getElementById('confirmMessage').textContent = message;
    overlay.classList.add('active');

    const cancel = document.getElementById('confirmCancel');
    const ok = document.getElementById('confirmOk');

    const cleanup = function () { overlay.classList.remove('active'); };
    cancel.onclick = cleanup;
    ok.onclick = function () { cleanup(); if (onConfirm) onConfirm(); };
}

function initTabs() {
    document.querySelectorAll('.admin-tab').forEach(function (tab) {
        tab.addEventListener('click', function () {
            const target = tab.dataset.tab;
            document.querySelectorAll('.admin-tab').forEach(function (t) { t.classList.remove('active'); });
            document.querySelectorAll('.admin-tab-panel').forEach(function (p) { p.classList.remove('active'); });
            tab.classList.add('active');
            const panel = document.getElementById(target);
            if (panel) panel.classList.add('active');
        });
    });
}

function initTableLoading() {
    document.querySelectorAll('form.admin-search-form').forEach(function (form) {
        form.addEventListener('submit', function () {
            const loader = document.getElementById('tableLoader');
            if (loader) loader.style.display = 'flex';
        });
    });
}

function exportTable(fmt) {
    const path = window.location.pathname + '/export/' + fmt + window.location.search;
    window.location.href = path;
}
