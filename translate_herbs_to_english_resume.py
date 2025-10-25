#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
草藥名稱英文翻譯腳本 - 支援斷點續傳
使用 DeepSeek 7B 模型將中文藥材名稱翻譯成英文標準化名稱
"""

import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import gc
import os
from datetime import datetime
import json

# 配置
MODEL_PATH = "/home/nculcwu/DeepSeek/deepseek-llm-7b-chat"
INPUT_FILE = "/home/nculcwu/DeepSeek/對照表_已清理.xlsx"
OUTPUT_FILE = f"/home/nculcwu/DeepSeek/對照表_含英文_{datetime.now().strftime('%Y%m%d')}.xlsx"
PROGRESS_FILE = "/home/nculcwu/DeepSeek/translation_progress.json"
BATCH_SIZE = 100  # 每批處理筆數

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

def load_progress():
    """載入進度檔案"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"completed": [], "last_index": -1}

def save_progress(progress):
    """儲存進度檔案"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def translate_to_english(herb_name, tokenizer, model):
    """將中文藥材名稱翻譯成英文"""
    # 建立 prompt
    prompt = f"""你是一位中醫藥專業翻譯專家。請將以下中文藥材名稱翻譯成標準英文名稱（使用拉丁學名或常用英文名稱）。

翻譯規則：
1. 優先使用國際通用的拉丁學名或藥典標準英文名稱
2. 如果是複方或加工藥材，翻譯成對應的英文描述
3. 保持專業性和準確性
4. 只輸出英文翻譯結果，不要添加任何解釋或額外內容

中文藥材名稱：{herb_name}

英文翻譯："""

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
            return "[ERROR: Input too long]"

        # 生成翻譯
        with torch.no_grad():
            outputs = model.generate(
                inputs,
                max_new_tokens=80,
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

        # 移除常見的前綴
        prefixes_to_remove = ['英文翻譯：', '英文名稱：', 'English translation: ', 'English name: ']
        for prefix in prefixes_to_remove:
            if result.startswith(prefix):
                result = result[len(prefix):].strip()

        return result if result else "[ERROR: Empty result]"

    except Exception as e:
        print(f"翻譯錯誤: {e}")
        return "[ERROR: Translation failed]"

def main():
    """主程式"""
    print(f"開始處理草藥名稱英文翻譯")
    print(f"輸入檔案: {INPUT_FILE}")
    print(f"輸出檔案: {OUTPUT_FILE}")

    # 讀取資料
    print("\n正在讀取資料...")
    df = pd.read_excel(INPUT_FILE)
    print(f"共 {len(df)} 筆資料需要翻譯")

    # 載入進度
    progress = load_progress()
    start_idx = progress["last_index"] + 1

    if start_idx > 0:
        print(f"\n從第 {start_idx + 1} 筆開始繼續處理...")
        english_names = progress["completed"]
    else:
        print("\n開始新的翻譯作業...")
        english_names = []

    # 載入模型
    tokenizer, model = load_model()

    # 批次翻譯
    print(f"\n開始翻譯... (每 {BATCH_SIZE} 筆保存一次)")
    total = len(df)

    for idx in range(start_idx, total):
        herb_name = df.iloc[idx]['標準化名稱']

        # 顯示進度
        if (idx + 1) % 10 == 0 or idx == start_idx:
            print(f"進度: {idx + 1}/{total} ({(idx + 1) / total * 100:.1f}%)")

        # 翻譯
        english_name = translate_to_english(herb_name, tokenizer, model)
        english_names.append(english_name)

        # 顯示結果
        print(f"  {herb_name} -> {english_name}")

        # 定期保存進度
        if (idx + 1) % BATCH_SIZE == 0:
            progress["completed"] = english_names
            progress["last_index"] = idx
            save_progress(progress)
            print(f"\n進度已保存 (完成 {idx + 1}/{total})")

            # 清理記憶體
            gc.collect()
            torch.cuda.empty_cache()

    # 新增英文欄位
    df['英文標準化名稱'] = english_names

    # 儲存結果
    print(f"\n正在儲存結果到 {OUTPUT_FILE}...")
    df.to_excel(OUTPUT_FILE, index=False)

    # 顯示統計
    error_count = sum(1 for name in english_names if '[ERROR' in name)
    success_count = total - error_count

    print(f"\n翻譯完成!")
    print(f"成功: {success_count} 筆")
    print(f"失敗: {error_count} 筆")
    print(f"成功率: {success_count / total * 100:.1f}%")

    # 清理進度檔案
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        print("\n進度檔案已清理")

    # 清理記憶體
    del model
    del tokenizer
    gc.collect()
    torch.cuda.empty_cache()

    print("\n輸出檔案欄位:")
    print(df.columns.tolist())
    print("\n前10筆結果:")
    print(df.head(10))

if __name__ == "__main__":
    main()
