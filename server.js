// Minimal static server for Railway (same pattern as is8-promo-playbook).
// Serves the Newsletter Studio dashboard: index.html + dashboard-data.json.
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const ROOT = __dirname;
const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
};

http.createServer((req, res) => {
  const urlPath = decodeURIComponent(req.url.split('?')[0]);
  let rel = urlPath === '/' ? 'index.html' : urlPath.replace(/^\/+/, '');
  const file = path.join(ROOT, rel);
  const ext = path.extname(file).toLowerCase();

  // only serve known static types from the repo root; no dotfiles, no traversal
  if (!file.startsWith(ROOT) || rel.startsWith('.') || rel.includes('..') || !TYPES[ext]) {
    res.writeHead(404); res.end('Not found'); return;
  }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404); res.end('Not found'); return; }
    res.writeHead(200, { 'Content-Type': TYPES[ext], 'Cache-Control': 'no-cache' });
    res.end(data);
  });
}).listen(PORT, '0.0.0.0', () => console.log(`Newsletter Studio on :${PORT}`));
