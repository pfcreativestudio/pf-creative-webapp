import { Pool } from 'pg';

let pool;

// 这是一种防止在开发环境中因热重载而创建过多数据库连接池的技巧。
// 它检查全局变量中是否已存在连接池，如果存在则复用，否则创建新的。
if (!global._pgPool) {
  global._pgPool = new Pool({
    // 它会自动读取您在Vercel或.env.local文件中设置的POSTGRES_URL环境变量
    connectionString: process.env.POSTGRES_URL, 
    ssl: {
      // 某些云数据库（如Vercel Postgres, Heroku）需要这个SSL设置
      rejectUnauthorized: false
    }
  });
}
pool = global._pgPool;

// 我们导出一个对象，以后所有API文件都通过这个对象进行数据库查询
export const db = {
  query: (text, params) => pool.query(text, params),
};
