document.addEventListener('DOMContentLoaded', function () {
    var toggle = document.getElementById('sidebarToggle');
    var sidebar = document.getElementById('studentSidebar');
    var overlay = document.getElementById('mobileOverlay');
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
    document.querySelectorAll('.animate-counter').forEach(function (el) {
        var target = parseInt(el.dataset.target || el.textContent, 10);
        if (isNaN(target)) return;
        var current = 0;
        var step = Math.ceil(target / 40);
        var timer = setInterval(function () {
            current += step;
            if (current >= target) { current = target; clearInterval(timer); }
            el.textContent = current + (el.dataset.suffix || '');
        }, 30);
    });
    setTimeout(function () {
        document.querySelectorAll('.toast').forEach(function (t) {
            t.style.opacity = '0';
            setTimeout(function () { t.remove(); }, 300);
        });
    }, 4000);
});
