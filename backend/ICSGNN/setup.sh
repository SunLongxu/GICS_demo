#!/bin/bash

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装 PyTorch 和 PyTorch Geometric
pip install torch torchvision torchaudio
pip install torch-geometric

# 安装其他依赖
pip install -r requirements.txt

echo "ICSGNN 环境设置完成！"
echo "使用 'source venv/bin/activate' 激活虚拟环境"
echo "使用 'python main.py' 运行主程序" 