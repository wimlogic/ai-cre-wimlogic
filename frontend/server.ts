import express from 'express';
import path from 'path';
import http from 'http';
import { spawn } from 'child_process';
import { createServer as createViteServer } from 'vite';

async function startServer() {
  const app = express();
  const PORT = 3000;

  console.log('[WIMLOGIC Proxy] Starting Python FastAPI backend on port 8000...');
  const pythonProcess = spawn('python3', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'], {
    cwd: path.join(process.cwd(), 'backend'),
    stdio: 'inherit',
  });

  pythonProcess.on('error', (err) => {
    console.error('[WIMLOGIC Proxy] Failed to start Python FastAPI backend:', err);
  });

  pythonProcess.on('exit', (code) => {
    console.log(`[WIMLOGIC Proxy] Python FastAPI backend exited with code ${code}`);
  });

  process.on('exit', () => {
    pythonProcess.kill();
  });
  process.on('SIGINT', () => {
    pythonProcess.kill();
    process.exit();
  });

  // Proxy requests to the live Python FastAPI backend
  const proxyPaths = ['/api/v1', '/docs', '/openapi.json'];

  app.use((req, res, next) => {
    const isProxy = proxyPaths.some(p => req.url.startsWith(p));
    if (isProxy) {
      const options = {
        hostname: '127.0.0.1',
        port: 8000,
        path: req.url,
        method: req.method,
        headers: req.headers,
      };

      const proxyReq = http.request(options, (proxyRes) => {
        res.writeHead(proxyRes.statusCode || 500, proxyRes.headers);
        proxyRes.pipe(res, { end: true });
      });

      req.pipe(proxyReq, { end: true });

      proxyReq.on('error', (err) => {
        console.error(`[WIMLOGIC Proxy] Error forwarding request ${req.method} ${req.url}:`, err);
        if (!res.headersSent) {
          res.status(502).json({ error: 'FastAPI Backend Connection Failed', details: err.message });
        }
      });
    } else {
      next();
    }
  });

  // Vite Integration
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[WIMLOGIC Proxy] Frontend container running on port ${PORT}`);
  });
}

startServer();
