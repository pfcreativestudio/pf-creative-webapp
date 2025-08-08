// 引入我们的数据库连接助手
import { db } from '/lib/db'; 
// 我们暂时不加密密码，但引入crypto为未来做准备
import crypto from 'crypto'; 

export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method Not Allowed' });
    }

    const { username, password } = req.body;

    if (!username || !password) {
        return res.status(400).json({ error: 'Username and password are required' });
    }
    
    // TODO: 在生产环境中，密码绝不能以明文存储。您应该使用像 bcrypt 这样的库来哈希密码。
    // const hashedPassword = await bcrypt.hash(password, 10);

    try {
        // 1. 检查用户名是否已存在
        const existingUser = await db.query('SELECT username FROM users WHERE username = $1', [username]);
        if (existingUser.rows.length > 0) {
            return res.status(409).json({ error: 'Username already exists.' }); // 409 Conflict
        }

        // 2. 将新用户插入数据库
        const createdAt = new Date().toISOString();
        await db.query(
            'INSERT INTO users (username, password, created_at) VALUES ($1, $2, $3)',
            [username, password, createdAt] // 在生产环境中，这里应该是 hashedPassword
        );
        
        console.log(`New user registered: ${username}`);
        return res.status(201).json({ success: true, message: 'User registered successfully.' });

    } catch (error) {
        console.error('Registration API Error:', error);
        return res.status(500).json({ error: 'An internal server error occurred.' });
    }
}
