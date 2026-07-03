/* Bodhini AI - Admin Dashboard Charts */
document.addEventListener('DOMContentLoaded', function () {
    if (typeof Chart === 'undefined' || !window.adminChartData) return;

    const data = window.adminChartData;
    const gradient = function (ctx, c1, c2) {
        const g = ctx.createLinearGradient(0, 0, 0, 280);
        g.addColorStop(0, c1);
        g.addColorStop(1, c2);
        return g;
    };

    const defaults = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { display: false }, ticks: { font: { size: 11 } } },
            y: { grid: { color: '#f1f5f9' }, ticks: { font: { size: 11 } }, beginAtZero: true }
        }
    };

    function makeChart(id, type, labels, values, colors) {
        const el = document.getElementById(id);
        if (!el || !labels.length) return;
        const ctx = el.getContext('2d');
        new Chart(ctx, {
            type: type,
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors || '#2563eb',
                    borderColor: type === 'line' ? '#2563eb' : undefined,
                    borderWidth: type === 'line' ? 2 : 0,
                    fill: type === 'line',
                    tension: 0.4,
                    borderRadius: type === 'bar' ? 8 : 0,
                }]
            },
            options: defaults
        });
    }

    const mr = data.monthly_regs || {};
    makeChart('chartMonthlyRegs', 'bar',
        Object.keys(mr).sort(),
        Object.keys(mr).sort().map(function (k) { return mr[k]; }),
        '#2563eb'
    );

    const da = data.daily_active || {};
    makeChart('chartDailyActive', 'line',
        Object.keys(da).sort().slice(-14),
        Object.keys(da).sort().slice(-14).map(function (k) { return da[k]; })
    );

    const rt = data.resume_trends || {};
    makeChart('chartResumeTrends', 'bar',
        Object.keys(rt).sort().slice(-14),
        Object.keys(rt).sort().slice(-14).map(function (k) { return rt[k]; }),
        '#4f46e5'
    );

    const cu = data.chat_usage || {};
    makeChart('chartChatUsage', 'line',
        Object.keys(cu).sort().slice(-14),
        Object.keys(cu).sort().slice(-14).map(function (k) { return cu[k]; })
    );

    const mods = data.modules || {};
    const modLabels = Object.keys(mods);
    if (modLabels.length) {
        makeChart('chartModules', 'doughnut', modLabels, modLabels.map(function (k) { return mods[k]; }),
            ['#2563eb', '#4f46e5', '#8b5cf6', '#22c55e', '#f59e0b', '#ef4444']
        );
    }

    const ps = data.placement_scores || [];
    if (ps.length) {
        const buckets = { '0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0 };
        ps.forEach(function (s) {
            if (s <= 20) buckets['0-20']++;
            else if (s <= 40) buckets['21-40']++;
            else if (s <= 60) buckets['41-60']++;
            else if (s <= 80) buckets['61-80']++;
            else buckets['81-100']++;
        });
        makeChart('chartPlacement', 'bar', Object.keys(buckets), Object.values(buckets), '#22c55e');
    }

    const ip = data.interview_perf || [];
    if (ip.length) {
        makeChart('chartInterview', 'bar',
            ip.map(function (_, i) { return 'S' + (i + 1); }).slice(-10),
            ip.slice(-10), '#f59e0b'
        );
    }

    const tm = data.top_missing || [];
    if (tm.length) {
        makeChart('chartMissingSkills', 'bar',
            tm.map(function (x) { return x[0]; }),
            tm.map(function (x) { return x[1]; }),
            '#ef4444'
        );
    }

    const tc = data.top_careers || [];
    if (tc.length) {
        makeChart('chartCareers', 'doughnut',
            tc.map(function (x) { return x[0]; }),
            tc.map(function (x) { return x[1]; }),
            ['#2563eb', '#4f46e5', '#8b5cf6', '#22c55e', '#f59e0b', '#ec4899', '#14b8a6', '#f97316']
        );
    }

    const atsEl = document.getElementById('chartATS');
    if (atsEl && data.avg_ats) {
        new Chart(atsEl.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['ATS Score', 'Remaining'],
                datasets: [{
                    data: [data.avg_ats, 100 - data.avg_ats],
                    backgroundColor: ['#2563eb', '#e2e8f0'],
                    borderWidth: 0
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, cutout: '70%',
                plugins: { legend: { display: false } } }
        });
    }

    const colleges = data.top_colleges || [];
    if (colleges.length) {
        makeChart('chartColleges', 'bar',
            colleges.map(function (x) { return x[0]; }),
            colleges.map(function (x) { return x[1]; }),
            '#4f46e5'
        );
    }

    const atsDist = data.ats_distribution || {};
    if (Object.keys(atsDist).length) {
        makeChart('chartATSDist', 'doughnut',
            Object.keys(atsDist),
            Object.values(atsDist),
            ['#ef4444', '#f59e0b', '#22c55e', '#2563eb']
        );
    }
});
