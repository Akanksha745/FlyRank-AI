const http = require('http');
const PORT = 3000;

const server = http.createServer((req, res) => {
    // Set response headers for JSON content
    res.setHeader('Content-Type', 'application/json');

    if (req.url === '/' && req.method === 'GET') {
        res.writeHead(200);
        res.end(JSON.stringify({ message: "Welcome to the minimal backend!" }));
    } else if (req.url === '/status' && req.method === 'GET') {
        res.writeHead(200);
        res.end(JSON.stringify({ status: "online", timestamp: new Date() }));
    } else {
        res.writeHead(404);
        res.end(JSON.stringify({ error: "Endpoint not found" }));
    }
});

server.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
});