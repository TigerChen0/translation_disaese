#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
草藥名稱英文翻譯腳本
使用 DeepSeek 7B 模型將中文藥材名稱翻譯成英文標準化名稱
"""

import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import gc
import os
from datetime import datetime

# 配置
MODEL_PATH = "/home/nculcwu/DeepSeek/deepseek-llm-7b-chat"
INPUT_FILE = "/home/nculcwu/DeepSeek/對照表_已清理.xlsx"
OUTPUT_FILE = f"/home/nculcwu/DeepSeek/對照表_含英文_{datetime.now().strftime('%Y%m%d')}.xlsx"

# 設定 CUDA 記憶體分配
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'

def load_model():
    """載入 DeepSeek 模型和 tokenizer"""
    print("正在載入模型...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype="auto",
        device_map="auto"
    )
    print("模型載入完成")
    return tokenizer, model

def translate_to_english(herb_name, tokenizer, model, max_retries=3):
    """
    將中文藥材名稱翻譯成英文

    Args:
        herb_name: 中文藥材名稱
        tokenizer: DeepSeek tokenizer
        model: DeepSeek model
        max_retries: 最大重試次數

    Returns:
        英文翻譯結果
    """
    # 建立 prompt
    prompt = f"""你是一位中醫藥專業翻譯專家。請將以下中文藥材名稱翻譯成標準英文名稱（使用拉丁學名或常用英文名稱）。

翻譯規則：
1. 優先使用國際通用的拉丁學名或藥典標準英文名稱
2. 如果是複方或加工藥材，翻譯成對應的英文描述
3. 保持專業性和準確性
4. 只輸出英文翻譯結果，不要添加任何解釋或額外內容

中文藥材名稱：{herb_name}

英文翻譯："""

    for attempt in range(max_retries):
        try:
            # Tokenize
            messages = [{"role": "user", "content": prompt}]
            inputs = tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt"
            ).to(model.device)

            # 檢查輸入長度
            if inputs.shape[1] > 4096:
                print(f"警告: {herb_name} 的 prompt 超過模型限制，跳過")
                return "[ERROR: Input too long]"

            # 生成翻譯
            with torch.no_grad():
                outputs = model.generate(
                    inputs,
                    max_new_tokens=100,
                    temperature=0.3,
                    top_p=0.85,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )

            # 解碼結果
            response = tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)

            # 清理結果
            result = response.strip()

            # 移除可能的多餘文字
            if '\n' in result:
                result = result.split('\n')[0].strip()

            # 基本驗證
            if result and len(result) > 0 and not result.startswith('[ERROR'):
                return result
            else:
                print(f"嘗試 {attempt + 1}/{max_retries}: {herb_name} 翻譯結果無效，重試...")

        except Exception as e:
            print(f"翻譯 {herb_name} 時發生錯誤 (嘗試 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return "[ERROR: Translation failed]"

    return "[ERROR: Max retries exceeded]"

def main():
    """主程式"""
    print(f"開始處理草藥名稱英文翻譯")
    print(f"輸入檔案: {INPUT_FILE}")
    print(f"輸出檔案: {OUTPUT_FILE}")

    # 讀取資料
    print("\n正在讀取資料...")
    df = pd.read_excel(INPUT_FILE)
    print(f"共 {len(df)} 筆資料需要翻譯")

    # 載入模型
    tokenizer, model = load_model()

    # 建立英文欄位
    english_names = []

    # 批次翻譯
    print("\n開始翻譯...")
    total = len(df)

    for idx, row in df.iterrows():
        herb_name = row['標準化名稱']

        # 顯示進度
        if (idx + 1) % 10 == 0 or idx == 0:
            print(f"進度: {idx + 1}/{total} ({(idx + 1) / total * 100:.1f}%)")

        # 翻譯
        english_name = translate_to_english(herb_name, tokenizer, model)
        english_names.append(english_name)

        # 顯示結果
        print(f"  {herb_name} -> {english_name}")

        # 定期清理記憶體
        if (idx + 1) % 50 == 0:
            gc.collect()
            torch.cuda.empty_cache()

    # 新增英文欄位
    df['英文標準化名稱'] = english_names

    # 儲存結果
    print(f"\n正在儲存結果到 {OUTPUT_FILE}...")
    df.to_excel(OUTPUT_FILE, index=False)

    # 顯示統計
    error_count = sum(1 for name in english_names if name.startswith('[ERROR'))
    success_count = total - error_count

    print(f"\n翻譯完成!")
    print(f"成功: {success_count} 筆")
    print(f"失敗: {error_count} 筆")
    print(f"成功率: {success_count / total * 100:.1f}%")

    # 清理記憶體
    del model
    del tokenizer
    gc.collect()
    torch.cuda.empty_cache()

    print("\n輸出檔案欄位:")
    print(df.columns.tolist())
    print("\n前5筆結果:")
    print(df.head())

if __name__ == "__main__":
    main()
