import { db } from '/lib/db';
import jwt from 'jsonwebtoken'; // 我们需要jsonwebtoken库来验证token

export default async function handler(req, res) {
    if (req.method !== 'GET') {
        return res.status(405).json({ error: 'Method Not Allowed' });
    }

    try {
        // 1. 从请求头中获取 Authorization token
        const authHeader = req.headers.authorization;
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({ error: 'Authorization token is missing or invalid.' });
        }

        const token = authHeader.split(' ')[1];
        const jwtSecret = process.env.JWT_SECRET;

        // 2. 验证并解码 token
        let decoded;
        try {
            decoded = jwt.verify(token, jwtSecret);
        } catch (error) {
            // 如果token过期或无效，返回401 Unauthorized
            return res.status(401).json({ error: 'Token is expired or invalid.' });
        }
        
        const username = decoded.username;
        if (!username) {
            return res.status(401).json({ error: 'Invalid token payload.' });
        }

        // 3. 从数据库中查询用户信息
        const result = await db.query(
            'SELECT username, subscription_expires_at FROM users WHERE username = $1',
            [username]
        );

        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'User not found.' });
        }

        const user = result.rows[0];

        // 4. 将安全的用户信息返回给前端
        res.status(200).json({
            username: user.username,
            subscription_expires_at: user.subscription_expires_at,
        });

    } catch (error) {
        console.error('Get User Status API Error:', error);
        res.status(500).json({ error: 'An internal server error occurred.' });
    }

}
