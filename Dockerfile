# 使用一个轻量级的 Python 3.11 镜像作为基础
FROM python:3.11-slim

# 在容器内设置工作目录
WORKDIR /app

# 复制并安装项目的依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 将您本地目录中所有剩余的代码复制到容器的工作目录中
COPY . ./

# 【核心修改】
# 在容器启动时，使用 Gunicorn 运行您的 Web 服务。
# 这个命令会告诉 Gunicorn 在 8080 端口上监听，这正是 Cloud Run 所期望的。
# 它会指向您 `main.py` 文件中的 `app` 对象 (app = Flask(__name__))。
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "main:app"]