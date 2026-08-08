const calls = [
  { id: 'req_7fa1', time: '09:05', model: 'gpt-4.1', env: 'Production', prompt: 1280, completion: 640, latency: 920, status: 'success', endpoint: '/chat/respond' },
  { id: 'req_81bd', time: '09:20', model: 'gpt-4.1-mini', env: 'Production', prompt: 820, completion: 280, latency: 510, status: 'success', endpoint: '/support/summarize' },
  { id: 'req_92ac', time: '10:00', model: 'gpt-4.1-mini', env: 'Staging', prompt: 460, completion: 190, latency: 440, status: 'success', endpoint: '/qa/classify' },
  { id: 'req_13cc', time: '10:35', model: 'gpt-4.1', env: 'Production', prompt: 2400, completion: 970, latency: 1380, status: 'error', endpoint: '/chat/respond' },
  { id: 'req_56ed', time: '11:15', model: 'gpt-4.1-nano', env: 'Development', prompt: 360, completion: 90, latency: 220, status: 'success', endpoint: '/dev/extract' },
  { id: 'req_66aa', time: '12:10', model: 'gpt-4.1-mini', env: 'Production', prompt: 1360, completion: 420, latency: 690, status: 'success', endpoint: '/support/summarize' },
  { id: 'req_34be', time: '13:35', model: 'gpt-4.1', env: 'Staging', prompt: 1760, completion: 880, latency: 1120, status: 'success', endpoint: '/batch/generate' },
  { id: 'req_09df', time: '14:50', model: 'gpt-4.1-mini', env: 'Production', prompt: 720, completion: 310, latency: 530, status: 'error', endpoint: '/qa/classify' },
];
const rates = { 'gpt-4.1': 0.0075, 'gpt-4.1-mini': 0.0016, 'gpt-4.1-nano': 0.00045 };
let budget = { monthly: 1200, warning: 75, errorRate: 3, latency: 900 };
const $ = id => document.getElementById(id);
const money = n => `$${n.toFixed(2)}`;
const cost = c => ((c.prompt + c.completion) / 1000) * rates[c.model];
function option(value) { return `<option value="${value}">${value}</option>`; }
function filteredCalls() {
  const model = $('modelFilter').value;
  const env = $('envFilter').value;
  return calls.filter(c => (model === 'All' || c.model === model) && (env === 'All' || c.env === env));
}
function totals(rows) {
  const tokens = rows.reduce((s, c) => s + c.prompt + c.completion, 0);
  const spend = rows.reduce((s, c) => s + cost(c), 0);
  const avgLatency = Math.round(rows.reduce((s, c) => s + c.latency, 0) / Math.max(rows.length, 1));
  const errorRate = rows.filter(c => c.status === 'error').length / Math.max(rows.length, 1) * 100;
  return { tokens, spend, avgLatency, errorRate };
}
function render() {
  const rows = filteredCalls();
  const t = totals(rows);
  const projected = t.spend * 30;
  $('metrics').innerHTML = [
    ['📊', 'Tokens', t.tokens.toLocaleString(), '+12.4% vs previous period'],
    ['💵', 'Estimated spend', money(t.spend), `${money(projected)} monthly projection`],
    ['⏱️', 'Avg latency', `${t.avgLatency}ms`, t.avgLatency > budget.latency ? 'Above threshold' : 'Healthy'],
    ['⚠️', 'Error rate', `${t.errorRate.toFixed(1)}%`, t.errorRate > budget.errorRate ? 'Alert triggered' : 'Within target'],
  ].map(([icon, label, value, delta]) => `<article class="metric"><i>${icon}</i><span>${label}</span><strong>${value}</strong><small>${delta}</small></article>`).join('');
  const maxTokens = Math.max(...rows.map(c => c.prompt + c.completion), 1);
  $('chart').innerHTML = rows.map(c => `<div class="barWrap"><div class="bar" style="height:${((c.prompt + c.completion) / maxTokens) * 100}%"><span>${money(cost(c))}</span></div><small>${c.time}</small></div>`).join('');
  $('modelMix').innerHTML = Object.keys(rates).map(m => { const pct = rows.filter(c => c.model === m).length / Math.max(rows.length, 1) * 100; return `<div class="mix"><span>${m}</span><b>${pct.toFixed(0)}%</b><progress value="${pct}" max="100"></progress></div>`; }).join('');
  $('health').textContent = `🖥️ ${rows.length} calls observed across ${new Set(rows.map(c => c.env)).size} environment(s)`;
  $('alerts').innerHTML = [
    [projected < budget.monthly * budget.warning / 100, `Projected monthly spend ${money(projected)} vs warning level ${money(budget.monthly * budget.warning / 100)}`],
    [t.errorRate <= budget.errorRate, `Error rate ${t.errorRate.toFixed(1)}% vs threshold ${budget.errorRate}%`],
    [t.avgLatency <= budget.latency, `Average latency ${t.avgLatency}ms vs threshold ${budget.latency}ms`],
  ].map(([ok, text]) => `<div class="alert ${ok ? 'ok' : 'bad'}">${ok ? '✓' : '!'} ${text}</div>`).join('');
  $('logs').innerHTML = rows.map(c => `<tr><td><b>${c.id}</b><small>${c.endpoint}</small></td><td>${c.time}</td><td>${c.model}</td><td>${c.env}</td><td>${(c.prompt + c.completion).toLocaleString()}</td><td>${money(cost(c))}</td><td>${c.latency}ms</td><td><span class="${c.status}">${c.status}</span></td></tr>`).join('');
}
function renderBudgetFields() {
  $('budgetFields').innerHTML = Object.entries(budget).map(([key, val]) => `<label class="field">${key.replace(/([A-Z])/g, ' $1')}<input data-budget="${key}" type="number" value="${val}" /></label>`).join('');
  document.querySelectorAll('[data-budget]').forEach(input => input.addEventListener('input', e => { budget = { ...budget, [e.target.dataset.budget]: Number(e.target.value) }; render(); }));
}
function init() {
  $('modelFilter').innerHTML = ['All', ...Object.keys(rates)].map(option).join('');
  $('envFilter').innerHTML = ['All', 'Production', 'Staging', 'Development'].map(option).join('');
  $('suggestions').innerHTML = [
    ['Route classification traffic to nano', 'Save ~72% on low-complexity QA calls', 'The /qa/classify endpoint has short completions and predictable outputs. Use gpt-4.1-nano with stricter schemas.'],
    ['Trim prompt context for chat', 'Reduce 1.2k prompt tokens per slow call', 'Chat requests above 2k prompt tokens correlate with latency spikes. Summarize older turns before sending.'],
    ['Cache support summaries', 'Avoid repeated summarization spend', 'Production summary calls share similar endpoint patterns. Cache by ticket revision and invalidate on updates.'],
  ].map(([title, impact, text]) => `<article class="suggestion"><h3>${title}</h3><b>${impact}</b><p>${text}</p></article>`).join('');
  $('modelFilter').addEventListener('change', render);
  $('envFilter').addEventListener('change', render);
  renderBudgetFields();
  render();
}
init();
