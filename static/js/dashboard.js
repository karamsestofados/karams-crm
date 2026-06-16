(function () {
  'use strict';

  const ORANGE = '#FF9220';
  const ORANGE_LIGHT = '#FFB366';
  const ORANGE_GLOW = 'rgba(255, 146, 32, 0.3)';
  const GRID_COLOR = 'rgba(255, 255, 255, 0.05)';
  const TEXT_MUTED = '#9CA3AF';

  function readJson(id) {
    const el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : null;
  }

  function sparklineConfig(data, color) {
    return {
      type: 'line',
      data: {
        labels: data.map((_, i) => i),
        datasets: [{
          data: data,
          borderColor: color,
          backgroundColor: ORANGE_GLOW,
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        scales: {
          x: { display: false },
          y: { display: false },
        },
      },
    };
  }

  const categorias = readJson('chart-categorias-data');
  const estados = readJson('chart-estados-data');
  const sparkClientes = readJson('spark-clientes-data');
  const sparkContatos = readJson('spark-contatos-data');
  const sparkVendas = readJson('spark-vendas-data');

  if (sparkClientes) {
    new Chart(document.getElementById('sparkClientes'), sparklineConfig(sparkClientes, ORANGE));
  }
  if (sparkContatos) {
    new Chart(document.getElementById('sparkContatos'), sparklineConfig(sparkContatos, ORANGE_LIGHT));
  }
  if (sparkVendas) {
    new Chart(document.getElementById('sparkVendas'), sparklineConfig(sparkVendas, ORANGE));
  }

  if (categorias) {
    new Chart(document.getElementById('chartCategorias'), {
      type: 'line',
      data: {
        labels: categorias.labels,
        datasets: [{
          label: 'Clientes',
          data: categorias.values,
          borderColor: ORANGE,
          backgroundColor: ORANGE_GLOW,
          borderWidth: 2.5,
          fill: true,
          tension: 0.35,
          pointBackgroundColor: ORANGE,
          pointBorderColor: '#1A1A1E',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 7,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            grid: { color: GRID_COLOR },
            ticks: { color: TEXT_MUTED, font: { size: 11 } },
          },
          y: {
            beginAtZero: true,
            grid: { color: GRID_COLOR },
            ticks: { color: TEXT_MUTED, font: { size: 11 }, stepSize: 1 },
          },
        },
      },
    });
  }

  if (estados && estados.labels.length) {
    new Chart(document.getElementById('chartEstados'), {
      type: 'bar',
      data: {
        labels: estados.labels,
        datasets: [{
          label: 'Clientes',
          data: estados.values,
          backgroundColor: estados.values.map((_, i) =>
            i % 2 === 0 ? ORANGE : ORANGE_LIGHT
          ),
          borderRadius: 6,
          borderSkipped: false,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            beginAtZero: true,
            grid: { color: GRID_COLOR },
            ticks: { color: TEXT_MUTED, font: { size: 10 }, stepSize: 1 },
          },
          y: {
            grid: { display: false },
            ticks: { color: TEXT_MUTED, font: { size: 11 } },
          },
        },
      },
    });
  } else if (document.getElementById('chartEstados')) {
    const ctx = document.getElementById('chartEstados').getContext('2d');
    ctx.font = '13px Inter, sans-serif';
    ctx.fillStyle = TEXT_MUTED;
    ctx.textAlign = 'center';
    ctx.fillText('Sem dados de UF', ctx.canvas.width / 2, ctx.canvas.height / 2);
  }
})();
