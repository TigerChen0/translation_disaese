# ==============================================================================
#  完整程式碼：使用上下文引導的本地模型進行多檔案、多詞條翻譯
# ==============================================================================

# ----------------------------------------------------
# 步驟 0: 匯入所有必要的函式庫
# ----------------------------------------------------
import os
import gc
import re
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from datetime import datetime  # 放到這裡

print("程式啟動，開始匯入函式庫...")

# ----------------------------------------------------
# 步驟 1: 設定與載入本地模型 (此部分保持不變)
# ----------------------------------------------------
#MODEL_PATH = "deepseek-ai/deepseek-llm-7b-chat"
MODEL_PATH = "/home/nculcwu/DeepSeek/deepseek-llm-7b-chat"


os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

print(f"準備從 '{MODEL_PATH}' 載入模型和分詞器...")
if not torch.cuda.is_available():
    print("錯誤：未偵測到 CUDA。此程式碼需要 NVIDIA GPU 才能執行。")
    exit()
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        #torch_dtype=torch.float16,
        torch_dtype="auto",
        device_map="auto",
        low_cpu_mem_usage=True,
        trust_remote_code=True
    )
    print("模型和分詞器已成功載入至 GPU！")
except Exception as e:
    print(f"模型載入失敗！錯誤訊息: {e}")
    exit()

# ----------------------------------------------------
# 步驟 2: 定義本地翻譯函式和上下文截斷函式
# ----------------------------------------------------
def truncate_context_if_needed(context_paragraph: str, term: str, max_tokens: int = 3800) -> str:
    """
    如果總的 prompt 會超過 token 限制，則截斷上下文段落
    """
    # 計算基礎 prompt 的 token 數量（不包含上下文）
    base_prompt = f"""我會先提供一段參考上下文，請你先理解它。然後，我會給你一段中醫文本，請你根據上下文的風格和知識，將文本翻譯成白話文。

--- 上下文開始 ---
--- 上下文結束 ---

現在，請將以下這段文本根據上文翻譯成白話文，請只輸出翻譯結果就好：
「{term}」"""

    base_tokens = len(tokenizer.encode(base_prompt))
    available_tokens = max_tokens - base_tokens

    # 如果上下文夠短，直接返回
    context_tokens = len(tokenizer.encode(context_paragraph))
    if context_tokens <= available_tokens:
        return context_paragraph

    # 截斷上下文以符合 token 限制
    print(f"⚠️  上下文過長 ({context_tokens} tokens)，截斷至 {available_tokens} tokens")

    # 編碼上下文並截斷
    context_token_ids = tokenizer.encode(context_paragraph)
    truncated_token_ids = context_token_ids[:available_tokens]
    truncated_context = tokenizer.decode(truncated_token_ids, skip_special_tokens=True)

    return truncated_context

def execute_translation_prompt(full_prompt: str) -> str:
    """
    接收一個已經構建好的完整 Prompt，並使用本地模型生成回應。
    """
    try:
        messages = [{'role': 'user', 'content': full_prompt}]
        input_ids = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt")

        # 檢查序列是否過長
        sequence_length = input_ids.shape[-1]
        if sequence_length > 4096:
            print(f"⚠️  輸入序列長度 ({sequence_length}) 超過模型限制 (4096)，可能導致錯誤")

        attention_mask = torch.ones_like(input_ids)
        outputs = model.generate(
            input_ids.to(model.device),
            attention_mask=attention_mask.to(model.device),
            max_new_tokens=256,  # 詞條翻譯通常不需要太長
            #do_sample=False,
            do_sample=True,        # 啟用隨機取樣
            temperature=0.7,       # 溫度參數，控制創意度
            top_p=0.95,            # Top-p 採樣
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id
        )
        response = tokenizer.decode(outputs[0][input_ids.shape[-1]:], skip_special_tokens=True)
        return response.strip()
    except Exception as e:
        print(f"!! 模型生成時發生錯誤: {e}")
        return "翻譯失敗：模型處理錯誤"

# ----------------------------------------------------
# 步驟 3: 主執行流程 - 匹配規則、構建複合 Prompt 並觸發翻譯
# ----------------------------------------------------
def main():
    """
    主執行函式
    """
    # --- 使用者設定區 ---
    FOLDER_PATH = '.'
    CONTROL_FILE = '/home/nculcwu/DeepSeek/7_附論段落.xlsx'
    TARGET_FILE_PATTERN = 'classified_section_卷'
    #OUTPUT_FILENAME = '上下文引導翻譯報告.xlsx'

    print("\n--- 開始執行翻譯流程 ---")

    # 1. 讀取主控檔案
    control_file_path = os.path.join(FOLDER_PATH, CONTROL_FILE)
    try:
        print(f"正在讀取主控檔案: {CONTROL_FILE}")
        control_df = pd.read_excel(control_file_path)
        if 'no' not in control_df.columns or 'disease_content' not in control_df.columns:
            print(f"錯誤：主控檔案 '{CONTROL_FILE}' 中缺少 'no' 或 'disease_content' 欄位。")
            return
    except FileNotFoundError:
        print(f"錯誤：找不到主控檔案 '{control_file_path}'。")
        return
    except Exception as e:
        print(f"讀取主控檔案時發生錯誤: {e}")
        return

    # 2. 掃描目標檔案，建立一個從編號到完整檔名的映射字典
    print("正在掃描資料夾以尋找目標檔案...")
    target_files_map = {}
    for filename in os.listdir(FOLDER_PATH):
        if filename.startswith(TARGET_FILE_PATTERN) and filename.endswith('.xlsx'):
            match = re.search(r'(\d+)\.xlsx$', filename)
            if match:
                number = int(match.group(1))
                target_files_map[number] = os.path.join(FOLDER_PATH, filename)

    if not target_files_map:
        print("警告：在資料夾中找不到任何符合 'classified_section_卷XXX.xlsx' 格式的目標檔案。")
    else:
        print(f"已找到的目標檔案映射: {list(target_files_map.keys())}")

    # 3. 過濾 control_df 只保留卷號存在於檔案清單的列
    available_nos = set(target_files_map.keys())
    control_df = control_df[control_df['no'].isin(available_nos)]
    print(f"過濾後，主控檔案只保留 {len(control_df)} 筆有對應檔案的卷號資料。")

    # 4. 遍歷目標檔案，進行基於 section 的匹配和翻譯
    print("\n--- 開始遍歷目標檔案並進行基於章節的匹配翻譯 ---")
    translation_results = []

    for volume_no, target_filename in target_files_map.items():
        print(f"\n處理檔案: {os.path.basename(target_filename)} (卷號: {volume_no})")

        try:
            # 載入目標檔案
            target_df = pd.read_excel(target_filename)
            if 'disease' not in target_df.columns:
                print(f"  -> 警告: 檔案 '{target_filename}' 中找不到 'disease' 欄位，跳過此卷。")
                continue
            if 'section' not in target_df.columns:
                print(f"  -> 警告: 檔案 '{target_filename}' 中找不到 'section' 欄位，跳過此卷。")
                continue

            # 取得有效的詞條-章節配對
            valid_rows = target_df[target_df['disease'].notna() & target_df['section'].notna()]
            print(f"  -> 在此卷中找到 {len(valid_rows)} 個有效的詞條-章節配對需要翻譯。")

            for index, row in valid_rows.iterrows():
                term = row['disease']
                section = row['section']

                if not str(term).strip() or not str(section).strip():
                    continue

                print(f"    -> 正在翻譯詞條: '{term}' (章節: '{section}')")

                # 使用 no + section 進行精確匹配
                context_row = control_df[
                    (control_df['no'] == volume_no) &
                    (control_df['section'] == section)
                ]

                context_paragraph = None
                actual_section_used = section
                fallback_used = False

                if context_row.empty:
                    # 嘗試回退：使用同卷號的任意章節
                    volume_fallback = control_df[control_df['no'] == volume_no]
                    if not volume_fallback.empty:
                        context_row = volume_fallback.iloc[[0]]  # 取第一個可用的
                        actual_section_used = context_row.iloc[0]['section']
                        fallback_used = True
                        print(f"      -> 警告: 卷{volume_no}+章節'{section}'無精確匹配，使用章節'{actual_section_used}'作為回退")
                    else:
                        # 最終回退：使用最接近的卷號
                        available_volumes = sorted(control_df['no'].unique())
                        if available_volumes:
                            nearest_volume = min(available_volumes, key=lambda x: abs(x - volume_no))
                            nearest_fallback = control_df[control_df['no'] == nearest_volume]
                            if not nearest_fallback.empty:
                                context_row = nearest_fallback.iloc[[0]]
                                actual_section_used = context_row.iloc[0]['section']
                                fallback_used = True
                                print(f"      -> 警告: 卷{volume_no}無可用上下文，使用卷{nearest_volume}+章節'{actual_section_used}'作為回退")
                            else:
                                print(f"      -> 錯誤: 詞條'{term}'找不到任何可用的上下文，跳過")
                                continue
                        else:
                            print(f"      -> 錯誤: 控制檔案中沒有可用的卷號，跳過詞條'{term}'")
                            continue

                context_paragraph = context_row.iloc[0]['disease_content']
                if pd.isna(context_paragraph):
                    print(f"      -> 警告: 卷{volume_no}+章節'{actual_section_used}'的上下文段落為空，跳過詞條'{term}'")
                    continue

                # 截斷上下文以避免超過 token 限制
                truncated_context = truncate_context_if_needed(context_paragraph, term)

                full_prompt = (
                    f"我會先提供一段參考上下文，請你先理解它。然後，我會給你一段中醫文本，請你根據上下文的風格和知識，將文本翻譯成白話文。\n\n"
                    f"--- 上下文開始 ---\n"
                    f"{truncated_context}\n"
                    f"--- 上下文結束 ---\n\n"
                    f"現在，請將以下這段文本根據上文翻譯成白話文，請只輸出翻譯結果就好：\n"
                    f"「{term}」"
                )

                translated_text = execute_translation_prompt(full_prompt)

                translation_results.append({
                    '卷號': volume_no,
                    '章節': section,
                    '原始文本': term,
                    '翻譯結果': translated_text,
                    '使用回退': '是' if fallback_used else '否',
                    '實際章節': actual_section_used if fallback_used else section
                })

                gc.collect()
                torch.cuda.empty_cache()

        except Exception as e:
            print(f"  -> 處理檔案 '{target_filename}' 時發生錯誤: {e}")

    # 5. 生成最終報告
    if not translation_results:
        print("\n處理完成，但沒有任何資料被成功翻譯。未生成報告。")
        return

    print("\n--- 所有翻譯已完成！正在產生 Excel 總結報告 ---")
    results_df = pd.DataFrame(translation_results)

    卷號列表 = sorted(set(r['卷號'] for r in translation_results))
    min_no, max_no = 卷號列表[0], 卷號列表[-1]

    today_str = datetime.now().strftime("%Y%m%d")

    output_filename = f"上下文引導翻譯報告_卷{str(min_no).zfill(3)}-卷{str(max_no).zfill(3)}_{today_str}.xlsx"
    output_path = os.path.join(FOLDER_PATH, output_filename)

    try:
        results_df.to_excel(output_path, index=False)
        print(f"\n成功！翻譯總結報告已儲存至: {os.path.abspath(output_path)}")
    except Exception as e:
        print(f"錯誤：儲存 Excel 報告時發生問題: {e}")
    
# ----------------------------------------------------
# 程式執行入口
# ----------------------------------------------------
if __name__ == "__main__":
    main()
    print("\n--- 所有流程執行完畢 ---")
