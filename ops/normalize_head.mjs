#!/usr/bin/env node
import fs from 'fs';
import path from 'path';

const FILES = [
  'login.html','register.html','dashboard.html','chatroom.html','admin.html',
  'pricing.html','payment-success.html','index.html','privacy.html'
];

function normalizeHead(file) {
  if (!fs.existsSync(file)) return { file, changed: false, reason: 'missing' };
  let html = fs.readFileSync(file, 'utf8');

  // Remove duplicate includes first (runtime-config.js and api.js)
  html = html.replace(/<script[^>]+src=["']\/?runtime-config\.js["'][^>]*>\s*<\/script>\s*/gmi, '');
  html = html.replace(/<script[^>]+src=["']\/?api\.js["'][^>]*>\s*<\/script>\s*/gmi, '');
  // Remove duplicate pf:apiBase
  html = html.replace(/<meta[^>]+name=["']pf:apiBase["'][^>]*>\s*/gmi, '');

  const headOpenMatch = html.match(/<head[^>]*>/i);
  const headCloseIdx = html.search(/<\/head>/i);
  if (!headOpenMatch || headCloseIdx < 0) {
    return { file, changed: false, reason: 'no-head' };
  }

  const headOpenIdx = html.search(/<head[^>]*>/i);
  const headOpenTag = headOpenMatch[0];
  const before = html.slice(0, headOpenIdx);
  const headInner = html.slice(headOpenIdx + headOpenTag.length, headCloseIdx);
  const after = html.slice(headCloseIdx);

  // Extract standard tags (charset, viewport, title) and remove them from inner
  const charsetMatch = headInner.match(/<meta[^>]*charset=["'][^"']+["'][^>]*>\s*/i) || [''];
  const viewportMatch = headInner.match(/<meta[^>]*name=["']viewport["'][^>]*>\s*/i) || [''];
  const titleMatch = headInner.match(/<title[\s\S]*?<\/title>\s*/i) || [''];
  let remaining = headInner
    .replace(charsetMatch[0], '')
    .replace(viewportMatch[0], '')
    .replace(titleMatch[0], '');

  // Build required prelude in order: charset/viewport/title, pf:apiBase, runtime-config.js, api.js
  const meta = '<meta name="pf:apiBase" content="'+(process.env.CANONICAL_URL||'')+'">';
  const prelude = `${charsetMatch[0]}${viewportMatch[0]}${titleMatch[0]}    ${meta}\n    <script src="runtime-config.js"></script>\n    <script src="api.js"></script>\n`;
  const injectedHead = `${headOpenTag}\n    ${prelude}${remaining}`;
  const out = before + injectedHead + after;
  const changed = out !== html;
  if (changed) fs.writeFileSync(file, out);
  return { file, changed };
}

function rewriteCalls(file) {
  if (!fs.existsSync(file)) return { file, changed: false };
  let s = fs.readFileSync(file, 'utf8');
  const out = s.replace(/\bapiFetch\(/g, 'window.apiFetch(');
  const changed = out !== s;
  if (changed) fs.writeFileSync(file, out);
  return { file, changed };
}

const results = [];
for (const f of FILES) {
  results.push(normalizeHead(f));
  results.push(rewriteCalls(f));
}

const changed = results.filter(r => r.changed).map(r => r.file);
console.log('Normalized head and calls. Changed:', [...new Set(changed)].join(', ') || 'none');


