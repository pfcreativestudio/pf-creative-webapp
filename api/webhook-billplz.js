// 引入我们之前创建的数据库连接助手
import { db } from './db.js';
// 引入Node.js内置的加密模块，用于安全验证
import crypto from 'crypto';

// 这个配置告诉Vercel，这个API端点可以接收并解析 x-www-form-urlencoded 格式的数据
export const config = {
  api: {
    bodyParser: true,
  },
};

// 【重要】这是一个示例验证函数。在生产环境中，您需要根据Billplz的官方文档，
// 确认并使用完全正确的参数顺序来构建签名字符串。
const verifyBillplzSignature = (data, xSignatureKey) => {
    const { x_signature, ...otherData } = data;
    if (!x_signature) return false;

    // 根据Billplz的习惯，通常是按字母顺序排列key来构建签名
    const keys = Object.keys(otherData).sort();
    let signatureString = '';
    for (const key of keys) {
        signatureString += key + otherData[key];
    }

    const generatedSignature = crypto
      .createHmac('sha256', xSignatureKey)
      .update(signatureString)
      .digest('hex');
    
    return generatedSignature === x_signature;
}

// 这是Vercel处理我们Webhook请求的主函数
export default async function handler(req, res) {
  // 只接受POST请求
  if (req.method !== 'POST') {
    return res.status(405).send({ message: 'Only POST requests allowed' });
  }

  const data = req.body;
  const xSignatureKey = process.env.BILLPLZ_X_SIGNATURE_KEY;

  try {
    // ！！安全第一：在生产环境中，必须启用并严格验证签名
    // const isValid = verifyBillplzSignature(data, xSignatureKey);
    // if (!isValid) {
    //   throw new Error('Invalid X-Signature. Request might be fraudulent.');
    // }
    
    // 检查支付状态是否为 'true'，这是Billplz表示支付成功的字段
    if (data.paid === 'true') {
      
      // 我们使用之前传递的 reference_1 (即我们的 user_id) 来识别用户
      const userId = data.reference_1;
      const userEmail = data.email; // 同时获取email，方便记录日志

      if (!userId) {
        throw new Error('UserID (reference_1) not found in webhook payload.');
      }

      console.log(`Processing successful payment for UserID: ${userId}, Email: ${userEmail}`);

      // 从数据库获取该用户当前的订阅到期日
      const result = await db.query('SELECT subscription_expires_at FROM users WHERE id = $1', [userId]);
      const user = result.rows[0];

      if (!user) {
        throw new Error(`User with ID ${userId} not found in database.`);
      }

      // 核心逻辑：计算新的到期日
      const currentExpiry = user.subscription_expires_at ? new Date(user.subscription_expires_at) : new Date();
      const now = new Date();
      
      // 如果用户订阅还未过期，就在原基础上续期；如果已过期，就从今天开始重新计算。
      const startDate = currentExpiry > now ? currentExpiry : now;
      
      const newExpiryDate = new Date(startDate.getTime());
      
      // TODO: 您需要根据用户购买的套餐来决定增加多长时间
      // 这里我们暂时硬编码增加30天作为示例
      newExpiryDate.setDate(newExpiryDate.getDate() + 30);

      // 将新的到期日更新到数据库
      await db.query(
        'UPDATE users SET subscription_expires_at = $1 WHERE id = $2',
        [newExpiryDate.toISOString(), userId]
      );

      console.log(`SUCCESS: Subscription for user ${userId} has been extended to ${newExpiryDate.toISOString()}`);
    }

    // 无论处理成功与否，都必须返回200 OK给Billplz，否则它会不停地重试发送这个通知
    res.status(200).send('OK');

  } catch (error) {
    console.error('Webhook Error:', error.message);
    // 即使内部出错，也向Billplz返回成功，但要在后台记录详细错误供您调试
    res.status(200).send('Internal error processed');
  }
}
