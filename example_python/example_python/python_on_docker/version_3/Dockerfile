#####################
# 编译依赖的配置文件#
#####################
FROM python:3.7.4-alpine as builder
# 设置工作目录
WORKDIR /data/app
# 复制本地依赖
COPY . .

# 设置环境变量
# 不要生成pyc文件
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 安装依赖并编译文件到/data/python_wheels
RUN apk add --update gcc musl-dev python3-dev libffi-dev openssl-dev build-base && pip install --upgrade pip && pip wheel --no-cache-dir --no-deps --wheel-dir /data/python_wheels -r requirements.txt

#####################
# 线上使用的配置文件#
#####################

# 拉取python的基础镜像, 具体使用python -V查看刚才自己是哪个版本的
FROM python:3.7.4-alpine
# 设置当前镜像的维护者
LABEL maintainer="so1nxxxx@gmail.com"
# 设置工作目录
WORKDIR /data/app
# 复制本地依赖
COPY . .

COPY --from=builder /data/python_wheels /data/python_wheels
RUN pip install --no-cache /data/python_wheels/*

# 指明监听的端口
EXPOSE 8080

# 运行的命令
CMD sh -c 'sleep 5 && uvicorn --host 0.0.0.0 example:app'
# CMD ["uvicorn", "--host", "0.0.0.0", "example:app"]
