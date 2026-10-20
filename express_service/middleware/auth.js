/**
 * Simple API-key guard for internal endpoints (called only by Django).
 */
module.exports = function apiKeyAuth(req, res, next) {
    const key = req.headers['x-api-key'];
    if (!key || key !== process.env.EXPRESS_API_KEY) {
        return res.status(401).json({ error: 'Invalid API key' });
    }
    next();
};