#!/usr/bin/env node

import { execSync } from 'child_process';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';

function getGitRemote() {
  try {
    // Try git remote get-url origin first
    const origin = execSync('git remote get-url origin', { encoding: 'utf8' }).trim();
    return origin;
  } catch (error) {
    try {
      // Fallback: parse .git/config
      const configPath = join('.git', 'config');
      if (existsSync(configPath)) {
        const config = readFileSync(configPath, 'utf8');
        const match = config.match(/\[remote "origin"\][\s\S]*?url\s*=\s*(.+)/);
        if (match) {
          return match[1].trim();
        }
      }
    } catch (fallbackError) {
      // Ignore fallback errors
    }
    return null;
  }
}

function extractOwnerRepo(remoteUrl) {
  if (!remoteUrl) return null;
  
  // Normalize to https format
  let normalized = remoteUrl;
  if (normalized.startsWith('git@github.com:')) {
    normalized = normalized.replace('git@github.com:', 'https://github.com/');
  }
  
  // Extract owner/repo
  const match = normalized.match(/https:\/\/github\.com\/([^\/]+)\/([^\/]+?)(?:\.git)?$/);
  if (match) {
    return {
      owner: match[1],
      repo: match[2]
    };
  }
  
  return null;
}

function updateReadmeBadge(owner, repo) {
  const readmePath = 'README.md';
  const badgeMarkdown = `[![QA](https://github.com/${owner}/${repo}/actions/workflows/qa.yml/badge.svg)](https://github.com/${owner}/${repo}/actions/workflows/qa.yml)`;
  
  if (!existsSync(readmePath)) {
    // Create README.md if it doesn't exist
    const content = `# PF Creative AI Studio\n\n${badgeMarkdown}\n\nDirector-Grade AI for Film Production Scripts\n`;
    writeFileSync(readmePath, content);
    console.log(`✓ Created ${readmePath} with badge for ${owner}/${repo}`);
    return;
  }
  
  let content = readFileSync(readmePath, 'utf8');
  
  // Check if badge already exists
  if (content.includes('/actions/workflows/qa.yml/badge.svg')) {
    // Replace existing badge
    const badgeRegex = /\[!\[QA\]\(https:\/\/github\.com\/[^\/]+\/[^\/]+\/actions\/workflows\/qa\.yml\/badge\.svg\)\]\(https:\/\/github\.com\/[^\/]+\/[^\/]+\/actions\/workflows\/qa\.yml\)/g;
    content = content.replace(badgeRegex, badgeMarkdown);
    console.log(`✓ Updated existing badge in ${readmePath} for ${owner}/${repo}`);
  } else {
    // Insert badge at the top
    const lines = content.split('\n');
    lines.splice(1, 0, badgeMarkdown, '');
    content = lines.join('\n');
    console.log(`✓ Inserted badge at top of ${readmePath} for ${owner}/${repo}`);
  }
  
  writeFileSync(readmePath, content);
}

function main() {
  console.log('🔍 Detecting GitHub remote...');
  
  const remoteUrl = getGitRemote();
  if (!remoteUrl) {
    console.log('⚠️  No origin remote configured.');
    console.log('   The badge will remain unchanged until after the first push.');
    console.log('   Run this script again after setting up the remote.');
    return;
  }
  
  console.log(`📡 Found remote: ${remoteUrl}`);
  
  const ownerRepo = extractOwnerRepo(remoteUrl);
  if (!ownerRepo) {
    console.log('❌ Could not parse owner/repo from remote URL');
    return;
  }
  
  console.log(`👤 Owner: ${ownerRepo.owner}`);
  console.log(`📦 Repo: ${ownerRepo.repo}`);
  
  updateReadmeBadge(ownerRepo.owner, ownerRepo.repo);
  
  console.log(`\n✅ Badge updated for ${ownerRepo.owner}/${ownerRepo.repo}`);
  console.log(`🔗 Actions URL: https://github.com/${ownerRepo.owner}/${ownerRepo.repo}/actions/workflows/qa.yml`);
}

main();
