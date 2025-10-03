# 使用 V100 相容 CUDA
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

# 安裝基礎工具
RUN apt-get update && apt-get install -y \
    git build-essential python3 python3-pip wget curl && \
    rm -rf /var/lib/apt/lists/*

# 建立工作目錄
WORKDIR /app

# 安裝 Python 套件（包含 transformers, torch 等）
RUN pip3 install --upgrade pip
RUN pip3 install torch==2.1.2 torchvision torchaudio \
    transformers accelerate bitsandbytes flask flask_cors sentencepiece

# 把 DeepSeek 模型掛載進容器
VOLUME ["/home/nculcwu/DeepSeek/deepseek-llm-7b-chat"]

# 預設啟動互動式 Shell
CMD ["bash"]

