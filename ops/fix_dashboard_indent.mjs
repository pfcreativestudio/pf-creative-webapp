#!/usr/bin/env node

import fs from 'fs';

const filePath = 'dashboard.html';
let content = fs.readFileSync(filePath, 'utf8');

// Find the start of the IIFE (after the canvas background IIFE)
const iifeStart = content.indexOf('// ========= Main application logic (wrapped in IIFE) =========');
if (iifeStart === -1) {
  console.error('Could not find IIFE start marker');
  process.exit(1);
}

// Find the end of the IIFE (before the closing script tag)
const scriptEnd = content.lastIndexOf('</script>');
if (scriptEnd === -1) {
  console.error('Could not find script end');
  process.exit(1);
}

// Extract the content before the IIFE
const beforeIife = content.substring(0, iifeStart);

// Extract the content after the IIFE
const afterIife = content.substring(scriptEnd);

// Extract the IIFE content and fix indentation
const iifeContent = content.substring(iifeStart, scriptEnd);

// Fix indentation: add 2 spaces to all lines inside the IIFE
const fixedIifeContent = iifeContent
  .split('\n')
  .map(line => {
    // Skip empty lines and lines that are already properly indented
    if (line.trim() === '' || line.startsWith('      ')) {
      return line;
    }
    // Add 2 spaces to lines that need indentation
    if (line.startsWith('    ')) {
      return '      ' + line.substring(4);
    }
    return line;
  })
  .join('\n');

// Reconstruct the file
const newContent = beforeIife + fixedIifeContent + afterIife;

// Write back to file
fs.writeFileSync(filePath, newContent);

console.log('✅ Dashboard indentation fixed!');
