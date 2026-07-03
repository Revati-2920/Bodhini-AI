const form = document.getElementById('predictor-form');
const button = document.getElementById('predict-btn');
const downloadPdfButton = document.getElementById('download-pdf-btn');
const shareReportButton = document.getElementById('share-report-btn');
const messages = [
  'Reading academic profile...',
  'Evaluating technical skills...',
  'Analyzing projects and internships...',
  'Comparing industry standards...',
  'Generating personalized advice...'
];

if (form) {
  form.addEventListener('submit', function () {
    if (button) {
      button.disabled = true;
      button.textContent = 'Generating Report...';
    }
  });
}

if (downloadPdfButton) {
  downloadPdfButton.addEventListener('click', function () {
    window.print();
  });
}

if (shareReportButton) {
  shareReportButton.addEventListener('click', async function () {
    const shareUrl = window.location.href;
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Bodhini AI Placement Report',
          text: 'Check out my AI placement readiness report.',
          url: shareUrl
        });
      } catch (error) {
        console.error('Share cancelled', error);
      }
    } else if (navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(shareUrl);
        alert('Report link copied to clipboard.');
      } catch (error) {
        alert('Unable to copy link automatically.');
      }
    } else {
      alert('Sharing is not supported in this browser.');
    }
  });
}

if (typeof Chart !== 'undefined') {
  const ctx = document.getElementById('radarChart');
  if (ctx) {
    new Chart(ctx, {
      type: 'radar',
      data: {
        labels: ['Coding', 'Communication', 'Projects', 'Academics', 'Leadership', 'Problem Solving', 'Technical Skills'],
        datasets: [{
          label: 'Placement Readiness',
          data: [78, 72, 76, 82, 74, 70, 80],
          backgroundColor: 'rgba(37,99,235,0.25)',
          borderColor: '#2563eb',
          borderWidth: 2
        }]
      },
      options: {
        scales: { r: { min: 0, max: 100 } },
        plugins: { legend: { labels: { color: '#fff' } } }
      }
    });
  }
}
