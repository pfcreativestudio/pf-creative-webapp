import fs from 'fs';
const url = 'https://pfsystem-api-app-902383636494.asia-southeast1.run.app';

const htmlFiles = fs.readdirSync('.').filter(x => x.endsWith('.html'));

for (const file of htmlFiles) {
    let content = fs.readFileSync(file, 'utf8');
    
    // Remove existing pf:apiBase meta tag
    content = content.replace(/<meta name="pf:apiBase"[^>]*>/g, '');
    
    // Add new pf:apiBase meta tag after <head>
    content = content.replace(/<head>/i, `<head>\n<meta name="pf:apiBase" content="${url}">`);
    
    fs.writeFileSync(file, content);
    console.log('Updated:', file);
}

console.log('All HTML files updated with new API base URL:', url);
