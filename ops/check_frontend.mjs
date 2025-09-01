#!/usr/bin/env node

import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

console.log('=== Frontend Static Assertions ===\n');

let failed = 0;
let warnings = 0;

function fail(message) {
    console.log(`❌ FAIL: ${message}`);
    failed++;
}

function warn(message) {
    console.log(`⚠️  WARN: ${message}`);
    warnings++;
}

function pass(message) {
    console.log(`✅ PASS: ${message}`);
}

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

// Check 1: runtime-config.js inclusion and ordering
console.log('1. Checking runtime-config.js inclusion and ordering...');

for (const file of HTML_FILES) {
    if (!existsSync(file)) {
        warn(`File ${file} not found`);
        continue;
    }
    
    const content = readFileSync(file, 'utf8');
    
    // Check if runtime-config.js is included
    if (!content.includes('runtime-config.js')) {
        fail(`${file}: Missing runtime-config.js inclusion`);
        continue;
    }
    
    // Extract head section
    const headMatch = content.match(/<head[^>]*>([\s\S]*?)<\/head>/i);
    if (!headMatch) {
        fail(`${file}: No <head> section found`);
        continue;
    }
    
    const headContent = headMatch[1];
    
    // Check if runtime-config.js is in head
    if (!headContent.includes('runtime-config.js')) {
        fail(`${file}: runtime-config.js not in <head> section`);
        continue;
    }
    
    // Check ordering - runtime-config.js should come early
    const scriptTags = [...headContent.matchAll(/<script[^>]*>/gi)];
    const runtimeIndex = scriptTags.findIndex(match => 
        match[0].includes('runtime-config.js')
    );
    
    if (runtimeIndex === -1) {
        fail(`${file}: runtime-config.js script tag not found in head`);
        continue;
    }
    
    // Check if there are potentially problematic scripts before runtime-config.js
    const beforeRuntime = scriptTags.slice(0, runtimeIndex);
    const problematicScripts = beforeRuntime.filter(match => {
        const scriptTag = match[0];
        return !scriptTag.includes('tailwindcss') && 
               !scriptTag.includes('fonts.googleapis') &&
               !scriptTag.includes('env.js') &&
               !scriptTag.includes('cdn.') &&
               !scriptTag.includes('external');
    });
    
    if (problematicScripts.length > 0) {
        warn(`${file}: ${problematicScripts.length} potentially problematic script(s) before runtime-config.js`);
    }
    
    // Ensure api.js present in <head>
    if (!headContent.includes('api.js')) {
        fail(`${file}: api.js not included in <head>`);
    }

    pass(`${file}: runtime-config.js properly included in <head>`);
}

console.log();

// Check 2: Look for fetch calls with absolute URLs
console.log('2. Checking for absolute fetch calls...');

for (const file of HTML_FILES) {
    if (!existsSync(file)) continue;
    
    const content = readFileSync(file, 'utf8');
    
    // Look for fetch calls with absolute URLs
    const absoluteFetchPattern = /fetch\s*\(\s*["']https?:\/\//g;
    const matches = [...content.matchAll(absoluteFetchPattern)];
    
    if (matches.length > 0) {
        warn(`${file}: Found ${matches.length} fetch call(s) with absolute URLs - should use apiFetch with relative paths`);
    }
}

console.log();

// Check 3: Look for API calls that might bypass apiFetch
console.log('3. Checking for potential API bypasses...');

const apiPaths = ['/login', '/get-user-status', '/v1/', '/admin/', '/create-bill', '/register', '/activity/log'];

for (const file of HTML_FILES) {
    if (!existsSync(file)) continue;
    
    const content = readFileSync(file, 'utf8');
    
    for (const path of apiPaths) {
        // Look for direct fetch calls to API paths
        const directFetchPattern = new RegExp(`fetch\\s*\\([^)]*["']${path.replace('/', '\\/')}`, 'g');
        const matches = [...content.matchAll(directFetchPattern)];
        
        if (matches.length > 0) {
            // Check if these are actually using apiFetch
            const hasApiFetch = matches.some(match => {
                const fullMatch = match[0];
                return fullMatch.includes('apiFetch');
            });
            
            if (!hasApiFetch) {
                warn(`${file}: Found potential direct fetch to ${path} - ensure it uses apiFetch()`);
            }
        }
    }
}

console.log();

// Check 4: Verify apiFetch is available
console.log('4. Checking apiFetch availability...');

if (!existsSync('api.js')) {
    fail('api.js file not found - apiFetch wrapper missing');
} else {
    const apiContent = readFileSync('api.js', 'utf8');
    
    if (!apiContent.includes('function apiFetch') && !apiContent.includes('apiFetch =')) {
        fail('api.js does not export apiFetch function');
    } else if (!apiContent.includes('credentials: "include"')) {
        fail('apiFetch does not set credentials: "include"');
    } else {
        pass('apiFetch properly configured in api.js');
    }
}

console.log();

// Summary
console.log('=== FRONTEND CHECK SUMMARY ===');
if (failed === 0) {
    console.log('🎉 ALL FRONTEND CHECKS PASSED');
    if (warnings > 0) {
        console.log(`⚠️  ${warnings} warning(s) - review recommended`);
    }
    process.exit(0);
} else {
    console.log(`❌ ${failed} check(s) failed`);
    if (warnings > 0) {
        console.log(`⚠️  ${warnings} warning(s)`);
    }
    process.exit(1);
}
