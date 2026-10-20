const express = require('express');
const router = express.Router();
const apiKeyAuth = require('../middleware/auth');

// Every route here requires the shared API key
router.use(apiKeyAuth);

/**
 * POST /internal/notify
 * Body: { event: string, data: object }
 * Broadcasts the event to every connected Socket.io client.
 */
router.post('/notify', (req, res) => {
    const { event, data } = req.body;
    if (!event) {
        return res.status(400).json({ error: 'event is required' });
    }

    const io = req.app.get('io');
    io.emit(event, data || {});
    console.log(`[notify] ${event}`, data);

    res.status(202).json({ ok: true });
});

module.exports = router;