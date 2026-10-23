import { timingSafeEqual } from 'node:crypto';

export function internalTokenGuard(req, res, next) {
  const token = process.env.CHATBOT_INTERNAL_TOKEN || '';
  if (process.env.NODE_ENV !== 'production' && !token) return next();
  const supplied = req.headers['x-internal-token'];
  const expected = Buffer.from(token);
  const actual = Buffer.from(typeof supplied === 'string' ? supplied : '');
  if (expected.length < 32 || actual.length !== expected.length || !timingSafeEqual(actual, expected)) {
    return res.status(403).json({ error: { code: 'PRIVATE_SERVICE', message: 'Access denied.' } });
  }
  return next();
}
