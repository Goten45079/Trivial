import { access, readFile } from 'node:fs/promises';
const files = ['index.html', 'src/main.js', 'src/styles.css'];
for (const file of files) await access(file);
const html = await readFile('index.html', 'utf8');
const js = await readFile('src/main.js', 'utf8');
for (const required of ['analytics', 'budgets', 'call-logs', 'ai-optimizer']) {
  if (!html.includes(required) && !js.includes(required)) throw new Error(`Missing section: ${required}`);
}
console.log('Static dashboard validation passed.');
