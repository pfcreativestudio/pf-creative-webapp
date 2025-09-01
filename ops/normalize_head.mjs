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

  // Prepend required tags to head: runtime-config.js then api.js
  const injectedHead = `${headOpenTag}\n    <script src="runtime-config.js"></script>\n    <script src="api.js"></script>\n${headInner}`;
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


