// 这是一个在Vercel上运行的Node.js无服务器函数

// TODO: 这是一个示例函数，在真实应用中，您需要从您的用户认证系统
// (例如通过解析cookie或token)来获取当前登录的用户信息。
// 目前，我们先用一个固定的虚拟用户数据来完成流程。
const getCurrentUser = async () => {
  return { id: 'usr_12345', email: 'customer@example.com', name: 'John Doe' };
};

// Vercel 会将这个文件作为一个API端点来处理
export default async function handler(req, res) {
  // 首先，检查请求方法是否为POST，确保安全
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Only POST requests are allowed' });
  }

  try {
    // 从Vercel环境变量中安全地读取我们的“钥匙”
    const apiKey = process.env.BILLPLZ_API_KEY;
    const collectionId = process.env.BILLPLZ_COLLECTION_ID;
    const appUrl = process.env.APP_URL;

    // 从前端发来的请求体(body)中，获取用户选择的套餐信息
    const { planId, planName, amount } = req.body;

    // 获取当前用户信息
    const user = await getCurrentUser();
    if (!user) {
      return res.status(401).json({ message: 'Authentication required' });
    }
    
    // 准备要发送给Billplz的数据包 (Payload)
    const billplzPayload = {
      collection_id: collectionId,
      email: user.email,
      name: user.name,
      amount: amount, // 从前端接收到的、以仙为单位的价格
      description: `PF Creative - ${planName}`,
      // 关键部分：设置回调和跳转URL
      callback_url: `${appUrl}/api/webhook-billplz`,
      redirect_url: `${appUrl}/payment-success`,
      // 将我们的内部用户ID传递给Billplz，以便后续识别
      reference_1_label: 'UserID',
      reference_1: user.id 
    };

    // 使用fetch函数，向Billplz的Staging(测试)环境API发送请求
    const billplzResponse = await fetch('https://www.billplz.com/api/v3/bills', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Billplz需要使用HTTP Basic Auth进行认证
        'Authorization': `Basic ${Buffer.from(apiKey + ':').toString('base64')}`
      },
      body: JSON.stringify(billplzPayload)
    });

    // 检查Billplz的响应是否成功
    if (!billplzResponse.ok) {
      const errorData = await billplzResponse.json();
      // 在服务器端打印详细错误，方便调试
      console.error('Billplz API Error:', errorData);
      throw new Error('Failed to create a bill with Billplz.');
    }

    const billplzResult = await billplzResponse.json();

    // 如果一切顺利，将从Billplz获取到的支付链接URL，以JSON格式返回给前端
    res.status(200).json({ url: billplzResult.url });

  } catch (error) {
    // 如果过程中出现任何错误，在服务器端打印错误，并向前端返回一个通用错误信息
    console.error('Create Bill API Error:', error);
    res.status(500).json({ message: error.message || 'An internal server error occurred.' });
  }
}
