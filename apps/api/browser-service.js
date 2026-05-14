const http = require('http');
const { chromium } = require('playwright');

const port = process.env.PORT || 3001;

let browser;

async function getBrowser() {
    if (!browser) {
        browser = await chromium.launch({
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
    }
    return browser;
}

const server = http.createServer(async (req, res) => {
    if (req.method === 'POST' && req.url === '/capture') {
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString();
        });
        req.on('end', async () => {
            try {
                const { url } = JSON.parse(body);
                if (!url) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'URL is required' }));
                    return;
                }

                const browser = await getBrowser();
                const context = await browser.newContext();
                const page = await context.newPage();
                await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
                const screenshot = await page.screenshot();
                await context.close();

                res.writeHead(200, { 'Content-Type': 'image/png' });
                res.end(screenshot);
            } catch (error) {
                console.error('Capture error:', error);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: error.message }));
            }
        });
    } else if (req.method === 'GET' && req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok' }));
    } else {
        res.writeHead(404);
        res.end();
    }
});

server.listen(port, () => {
    console.log(`Browser service listening at http://localhost:${port}`);
});
