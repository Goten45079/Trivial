import { access, readFile } from 'node:fs/promises';
const files = ['index.html', 'src/main.js', 'src/styles.css', 'app/main.py', 'Dockerfile', 'k8s/deployment.yaml', 'k8s/service.yaml'];
for (const file of files) await access(file);
const html = await readFile('index.html', 'utf8');
const js = await readFile('src/main.js', 'utf8');
const py = await readFile('app/main.py', 'utf8');
for (const required of ['analytics', 'budgets', 'call-logs', 'ai-optimizer']) {
  if (!html.includes(required) && !js.includes(required)) throw new Error(`Missing section: ${required}`);
}
for (const route of ['/api/observability', '/api/budget', '/api/optimizations', '/api/health']) {
  if (!py.includes(route)) throw new Error(`Missing FastAPI route: ${route}`);
}
console.log('FastAPI dashboard validation passed.');
