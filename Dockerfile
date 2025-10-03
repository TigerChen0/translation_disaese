

# 使用與 V100 相容的 CUDA 版本（11.8）+ cuDNN 8
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

# 安裝 Python 3.12 
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.12 python3.12-venv python3-pip \
        build-essential \
        git \
        curl \
        vim \
        wget && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /home/nculcwu/DeepSeek

COPY . /home/nculcwu/DeepSeek


RUN python3.12 -m pip install --upgrade pip && \
    python3.12 -m pip install --no-cache-dir \
        pandas \
        numpy \
        torch \
        transformers

CMD ["bash"]
