let calls = [];
let rates = {};
let budget = { monthly: 1200, warning: 75, errorRate: 3, latency: 900 };
let environments = ['Production', 'Staging', 'Development'];
const $ = id => document.getElementById(id);
const money = n => `$${n.toFixed(2)}`;
function option(value) { return `<option value="${value}">${value}</option>`; }
async function api(path, options) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
  if (!response.ok) throw new Error(`API request failed: ${response.status}`);
  return response.json();
}
async function loadObservability() {
  const params = new URLSearchParams({ model: $('modelFilter').value || 'All', env: $('envFilter').value || 'All' });
  const data = await api(`/api/observability?${params}`);
  calls = data.calls;
  rates = data.modelRates;
  environments = data.environments;
  if (data.models?.length) $('modelFilter').innerHTML = ['All', ...data.models].map(option).join('');
  render(data.metrics);
}
async function loadBudget() {
  budget = await api('/api/budget');
  renderBudgetFields();
}
async function updateBudget(key, value) {
  budget = { ...budget, [key]: Number(value) };
  await api('/api/budget', { method: 'PUT', body: JSON.stringify(budget) });
  renderBudgetFields();
  await loadObservability();
}
function render(metrics) {
  const t = metrics || { tokens: 0, spend: 0, projectedMonthlySpend: 0, avgLatency: 0, errorRate: 0 };
  $('metrics').innerHTML = [
    ['📊', 'Tokens', t.tokens.toLocaleString(), '+12.4% vs previous period'],
    ['💵', 'Estimated spend', money(t.spend), `${money(t.projectedMonthlySpend)} monthly projection`],
    ['⏱️', 'Avg latency', `${t.avgLatency}ms`, t.avgLatency > budget.latency ? 'Above threshold' : 'Healthy'],
    ['⚠️', 'Error rate', `${t.errorRate.toFixed(1)}%`, t.errorRate > budget.errorRate ? 'Alert triggered' : 'Within target'],
  ].map(([icon, label, value, delta]) => `<article class="metric"><i>${icon}</i><span>${label}</span><strong>${value}</strong><small>${delta}</small></article>`).join('');
  const maxTokens = Math.max(...calls.map(c => c.tokens), 1);
  $('chart').innerHTML = calls.map(c => `<div class="barWrap"><div class="bar" style="height:${(c.tokens / maxTokens) * 100}%"><span>${money(c.cost)}</span></div><small>${c.time}</small></div>`).join('');
  $('modelMix').innerHTML = Object.keys(rates).map(m => { const pct = calls.filter(c => c.model === m).length / Math.max(calls.length, 1) * 100; return `<div class="mix"><span>${m}</span><b>${pct.toFixed(0)}%</b><progress value="${pct}" max="100"></progress></div>`; }).join('');
  $('health').textContent = `🖥️ ${calls.length} calls observed across ${new Set(calls.map(c => c.env)).size} environment(s)`;
  $('alerts').innerHTML = [
    [t.projectedMonthlySpend < budget.monthly * budget.warning / 100, `Projected monthly spend ${money(t.projectedMonthlySpend)} vs warning level ${money(budget.monthly * budget.warning / 100)}`],
    [t.errorRate <= budget.errorRate, `Error rate ${t.errorRate.toFixed(1)}% vs threshold ${budget.errorRate}%`],
    [t.avgLatency <= budget.latency, `Average latency ${t.avgLatency}ms vs threshold ${budget.latency}ms`],
  ].map(([ok, text]) => `<div class="alert ${ok ? 'ok' : 'bad'}">${ok ? '✓' : '!'} ${text}</div>`).join('');
  $('logs').innerHTML = calls.map(c => `<tr><td><b>${c.id}</b><small>${c.endpoint}</small></td><td>${c.time}</td><td>${c.model}</td><td>${c.env}</td><td>${c.tokens.toLocaleString()}</td><td>${money(c.cost)}</td><td>${c.latency}ms</td><td><span class="${c.status}">${c.status}</span></td></tr>`).join('');
}
function renderBudgetFields() {
  $('budgetFields').innerHTML = Object.entries(budget).map(([key, val]) => `<label class="field">${key.replace(/([A-Z])/g, ' $1')}<input data-budget="${key}" type="number" value="${val}" /></label>`).join('');
  document.querySelectorAll('[data-budget]').forEach(input => input.addEventListener('change', e => updateBudget(e.target.dataset.budget, e.target.value)));
}
async function init() {
  const seed = await api('/api/observability');
  rates = seed.modelRates;
  environments = seed.environments;
  $('modelFilter').innerHTML = ['All', ...(seed.models?.length ? seed.models : Object.keys(rates))].map(option).join('');
  $('envFilter').innerHTML = ['All', ...environments].map(option).join('');
  const suggestions = await api('/api/optimizations');
  $('suggestions').innerHTML = suggestions.map(({ title, impact, text }) => `<article class="suggestion"><h3>${title}</h3><b>${impact}</b><p>${text}</p></article>`).join('');
  $('modelFilter').addEventListener('change', loadObservability);
  $('envFilter').addEventListener('change', loadObservability);
  await loadBudget();
  await loadObservability();
}
init().catch(error => {
  document.querySelector('.content').insertAdjacentHTML('afterbegin', `<div class="alert bad">! ${error.message}</div>`);
});
