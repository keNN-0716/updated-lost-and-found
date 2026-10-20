const express = require('express');
const axios = require('axios');
const router = express.Router();

const DJANGO_URL = process.env.DJANGO_URL || 'http://localhost:8000';

/**
 * GET /api/search?q=...
 *
 * Proxies to Django's /api/search/ while forwarding the browser's
 * session cookie so @login_required still works on the Django side.
 *
 * Frontend must call with `credentials: 'include'` (fetch) or
 * `withCredentials: true` (axios).
 */
router.get('/search', async (req, res) => {
    try {
        const response = await axios.get(`${DJANGO_URL}/api/search/`, {
            params: { q: req.query.q || '' },
            headers: { Cookie: req.headers.cookie || '' },
            timeout: 5000,
        });
        res.json(response.data);
    } catch (err) {
        const status = err.response?.status || 500;
        console.error('[search]', err.message);
        res.status(status).json({ error: 'Search failed' });
    }
});

module.exports = router;