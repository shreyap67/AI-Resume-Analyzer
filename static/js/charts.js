/* ============================================================
   charts.js – Chart.js setup for dashboard home charts.
   Functions are called from home.html with server-side data.
   ============================================================ */

/* ── Colour palette ─────────────────────────────────────────── */
var CHART_COLORS = {
  blue:    '#00D1FF',
  purple:  '#7C3AED',
  pink:    '#FF4D9D',
  green:   '#22C55E',
  amber:   '#F59E0B',
  indigo:  '#818CF8',
  teal:    '#2DD4BF',
  orange:  '#FB923C',
  gridLine: 'rgba(255, 255, 255, 0.04)',
  tickText: 'rgba(255, 255, 255, 0.35)',
};

/* ── Pie chart category colours (deterministic order) ─────── */
var PIE_COLORS = [
  '#00D1FF', '#7C3AED', '#FF4D9D', '#22C55E',
  '#F59E0B', '#818CF8', '#2DD4BF', '#FB923C',
];

/* ── Default Chart.js global options ─────────────────────── */
if (typeof Chart !== 'undefined') {
  Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";
  Chart.defaults.color       = CHART_COLORS.tickText;
}

/* ============================================================
   LINE CHART – ATS Score Over Time
   ============================================================ */
function initLineChart(canvasId, labels, scores) {
  var ctx = document.getElementById(canvasId);
  if (!ctx) return;

  // Build gradient fill
  var gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 200);
  gradient.addColorStop(0,   'rgba(0, 209, 255, 0.18)');
  gradient.addColorStop(1,   'rgba(0, 209, 255, 0)');

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'ATS Score (%)',
        data: scores,
        borderColor: CHART_COLORS.blue,
        backgroundColor: gradient,
        borderWidth: 2.5,
        fill: true,
        tension: 0.45,
        pointBackgroundColor: CHART_COLORS.blue,
        pointBorderColor: '#0B1026',
        pointBorderWidth: 2,
        pointRadius: 5,
        pointHoverRadius: 7,
        pointHoverBackgroundColor: '#fff',
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(11, 16, 38, 0.95)',
          borderColor: 'rgba(0, 209, 255, 0.2)',
          borderWidth: 1,
          padding: 12,
          titleColor: '#fff',
          bodyColor: CHART_COLORS.blue,
          callbacks: {
            label: function (ctx) {
              return ' ATS Score: ' + ctx.parsed.y.toFixed(1) + '%';
            },
          },
        },
      },
      scales: {
        x: {
          grid: { color: CHART_COLORS.gridLine },
          ticks: { color: CHART_COLORS.tickText, font: { size: 11 } },
        },
        y: {
          min: 0,
          max: 100,
          grid: { color: CHART_COLORS.gridLine },
          ticks: {
            color: CHART_COLORS.tickText,
            font: { size: 11 },
            callback: function (val) { return val + '%'; },
            stepSize: 20,
          },
        },
      },
    },
  });
}

/* ============================================================
   PIE / DONUT CHART – Skills Distribution
   ============================================================ */
function initPieChart(canvasId, labels, data) {
  var ctx = document.getElementById(canvasId);
  if (!ctx) return;

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: PIE_COLORS.slice(0, labels.length),
        borderWidth: 0,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(11, 16, 38, 0.95)',
          borderColor: 'rgba(124, 58, 237, 0.25)',
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: function (ctx) {
              var total = ctx.dataset.data.reduce(function (a, b) { return a + b; }, 0);
              var pct   = total > 0 ? Math.round((ctx.parsed / total) * 100) : 0;
              return ' ' + ctx.label + ': ' + ctx.parsed + ' (' + pct + '%)';
            },
          },
        },
      },
    },
  });
}

/* ============================================================
   BAR CHART – Job match scores (used on job_matcher if needed)
   ============================================================ */
function initBarChart(canvasId, labels, data) {
  var ctx = document.getElementById(canvasId);
  if (!ctx) return;

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Match %',
        data: data,
        backgroundColor: labels.map(function (_, i) {
          return PIE_COLORS[i % PIE_COLORS.length] + 'CC'; // add opacity
        }),
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',   // horizontal bars
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (ctx) { return ' ' + ctx.parsed.x.toFixed(1) + '%'; },
          },
        },
      },
      scales: {
        x: {
          min: 0,
          max: 100,
          grid: { color: CHART_COLORS.gridLine },
          ticks: {
            color: CHART_COLORS.tickText,
            callback: function (v) { return v + '%'; },
            font: { size: 11 },
          },
        },
        y: {
          grid: { color: 'transparent' },
          ticks: { color: CHART_COLORS.tickText, font: { size: 11 } },
        },
      },
    },
  });
}

/* ============================================================
   SCORE ARC – SVG circle animation on results page
   Triggered from results.html or upload.js after analysis
   ============================================================ */
function animateScoreArc(arcElement, score) {
  if (!arcElement) return;

  var circumference = 440; // 2π × r where r = 70
  var offset = circumference - (score / 100) * circumference;

  // Start at full offset (empty arc)
  arcElement.style.strokeDashoffset = circumference;
  arcElement.style.transition = 'stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1)';

  // Defer to next frame so transition fires
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      arcElement.style.strokeDashoffset = offset;
    });
  });
}
