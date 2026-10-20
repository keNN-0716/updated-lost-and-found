require('dotenv').config();
const express = require('express');
const http = require('http');
const cors = require('cors');
const helmet = require('helmet');
const { Server } = require('socket.io');

const internalRoutes = require('./routes/internal');
const searchRoutes = require('./routes/search');

const app = express();
const server = http.createServer(app);

// Socket.io: allow connections from the Django-served frontend
const io = new Server(server, {
    cors: {
        origin: process.env.DJANGO_URL || 'http://localhost:8000',
        methods: ['GET', 'POST'],
    },
});

// Make io accessible to route handlers via req.app.get('io')
app.set('io', io);

// ── Middleware ────────────────────────────────────────────
app.use(helmet({ crossOriginResourcePolicy: false }));
app.use(cors({
    origin: process.env.DJANGO_URL || 'http://localhost:8000',
    credentials: true,          // needed so cookies are forwarded on /api/search
}));
app.use(express.json({ limit: '10mb' }));

// ── Routes ────────────────────────────────────────────────
app.use('/internal', internalRoutes);   // Django → Express (API-key protected)
app.use('/api', searchRoutes);          // Browser → Express → Django

app.get('/health', (req, res) => res.json({ ok: true }));

// ── Socket lifecycle ──────────────────────────────────────
io.on('connection', (socket) => {
    console.log(`[socket] connected: ${socket.id}`);
    socket.on('disconnect', () => console.log(`[socket] disconnected: ${socket.id}`));
});

// ── Start ─────────────────────────────────────────────────
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`Express running on http://localhost:${PORT}`);
    console.log(`  Django URL: ${process.env.DJANGO_URL}`);
});