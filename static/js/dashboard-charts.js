document.addEventListener('DOMContentLoaded', function () {
    if (typeof Chart === 'undefined' || !window.dashboardCharts) return;
    var d = window.dashboardCharts;
    var opts = {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#94a3b8' } } },
        scales: {
            x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
            y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' }, beginAtZero: true }
        }
    };
    function chart(id, type, labels, data, color) {
        var el = document.getElementById(id);
        if (!el || !labels.length) return;
        new Chart(el.getContext('2d'), {
            type: type,
            data: { labels: labels, datasets: [{ data: data, backgroundColor: color || '#2563eb',
                borderColor: color || '#2563eb', tension: 0.4, fill: type === 'line' }] },
            options: opts
        });
    }
    var rt = d.resume_trend || [];
    chart('chartResume', 'line', rt.map(function (x) { return x.date; }), rt.map(function (x) { return x.score; }), '#2563eb');
    var pt = d.placement_trend || [];
    chart('chartPlacement', 'line', pt.map(function (x) { return x.date; }), pt.map(function (x) { return x.score; }), '#22c55e');
    var it = d.interview_trend || [];
    chart('chartInterview', 'bar', it.map(function (x) { return x.date; }), it.map(function (x) { return x.score; }), '#f59e0b');
    var st = d.skill_trend || [];
    chart('chartSkill', 'line', st.map(function (x) { return x.date; }), st.map(function (x) { return x.score; }), '#8b5cf6');
    var ct = d.career_trend || [];
    chart('chartCareer', 'line', ct.map(function (x) { return x.date; }), ct.map(function (x) { return x.score; }), '#4f46e5');
});
