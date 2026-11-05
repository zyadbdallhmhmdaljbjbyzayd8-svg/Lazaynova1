/**
 * Lazaynova1 - Internal Memory Module (OpenViking Integration)
 * Owner: zyadbda
 */

const http = require('http');

const CONFIG = {
    host: '127.0.0.1',
    port: 1933
};

function recallMemory(queryText) {
    return new Promise((resolve, reject) => {
        const payload = JSON.stringify({ query: queryText });
        
        const options = {
            hostname: CONFIG.host,
            port: CONFIG.port,
            path: '/api/recall',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(payload)
            }
        };

        const req = http.request(options, (res) => {
            let responseData = '';
            res.on('data', (chunk) => {
                responseData += chunk;
            });
            res.on('end', () => {
                try {
                    resolve(JSON.parse(responseData));
                } catch (e) {
                    resolve({ success: true, data: responseData });
                }
            });
        });

        req.on('error', (error) => {
            reject({ success: false, error: error.message });
        });

        req.write(payload);
        req.end();
    });
}

module.exports = {
    recallMemory
};
