#!/bin/bash

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

echo "环境设置完成！"
echo "使用 'source venv/bin/activate' 激活虚拟环境"
echo "使用 'python app.py' 启动服务器" 