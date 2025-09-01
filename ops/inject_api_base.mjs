#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SERVICE_URL = process.env.SERVICE_URL || process.argv[2];

if (!SERVICE_URL) {
  console.error('Usage: SERVICE_URL=<url> node ops/inject_api_base.mjs');
  console.error('   or: node ops/inject_api_base.mjs <url>');
  process.exit(1);
}

console.log(`🔧 Injecting API base: ${SERVICE_URL}`);

const HTML_FILES = [
  'login.html',
  'register.html', 
  'chatroom.html',
  'admin.html',
  'dashboard.html',
  'pricing.html',
  'payment-success.html',
  'index.html',
  'privacy.html'
];

// Check if terms.html exists
if (fs.existsSync('terms.html')) {
  HTML_FILES.push('terms.html');
}

const META_TAG = `    <meta name="pf:apiBase" content="${SERVICE_URL}">`;

function injectApiBase(filePath) {
  if (!fs.existsSync(filePath)) {
    console.log(`⚠️  ${filePath}: File not found`);
    return 'missing';
  }

  const content = fs.readFileSync(filePath, 'utf8');
  
  // Check if meta tag already exists
  if (content.includes('name="pf:apiBase"')) {
    // Update existing meta tag
    const updatedContent = content.replace(
      /<meta name="pf:apiBase" content="[^"]*">/g,
      META_TAG
    );
    
    if (updatedContent !== content) {
      fs.writeFileSync(filePath, updatedContent);
      return 'updated';
    } else {
      return 'unchanged';
    }
  } else {
    // Insert new meta tag after <head>
    const headIndex = content.indexOf('<head>');
    if (headIndex === -1) {
      console.log(`❌ ${filePath}: No <head> tag found`);
      return 'error';
    }
    
    const insertIndex = headIndex + 6; // length of '<head>'
    const newContent = content.slice(0, insertIndex) + '\n' + META_TAG + content.slice(insertIndex);
    
    fs.writeFileSync(filePath, newContent);
    return 'inserted';
  }
}

console.log('\n📁 Processing HTML files...\n');

let summary = {
  inserted: 0,
  updated: 0,
  unchanged: 0,
  error: 0,
  missing: 0
};

HTML_FILES.forEach(file => {
  const result = injectApiBase(file);
  summary[result]++;
  
  const icon = {
    inserted: '➕',
    updated: '✏️',
    unchanged: '✅',
    error: '❌',
    missing: '⚠️'
  }[result];
  
  console.log(`${icon} ${file}: ${result}`);
});

console.log('\n📊 Summary:');
console.log(`   Inserted: ${summary.inserted}`);
console.log(`   Updated: ${summary.updated}`);
console.log(`   Unchanged: ${summary.unchanged}`);
console.log(`   Errors: ${summary.error}`);
console.log(`   Missing: ${summary.missing}`);

if (summary.error > 0) {
  process.exit(1);
}
