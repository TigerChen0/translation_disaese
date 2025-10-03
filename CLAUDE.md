# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

這是一個中醫文獻翻譯系統，使用 DeepSeek 7B 模型將傳統中醫文本翻譯成現代繁體白話文，支援上下文引導的翻譯方式。

## Model Information

- **Model Path**: `/home/nculcwu/DeepSeek/deepseek-llm-7b-chat`
- **Model Type**: DeepSeek LLM 7B Chat model (fine-tuned for Chinese text processing)
- **Hardware Requirements**: NVIDIA GPU with CUDA support

## Core Components

### Translation System Architecture

系統提供兩種獨立的批次處理模式：

#### 1. 原始批次處理 (Legacy Batch Mode)
- **File**: `translation_disaese.py`
- **Purpose**: 硬編碼路徑的獨立批次翻譯程式
- **特點**: 不使用 config.yaml，直接在程式碼中指定模型路徑
- **Key Functions**:
  - `execute_translation_prompt()`: 使用本地模型執行翻譯
  - `truncate_context_if_needed()`: 截斷過長的上下文
  - `main()`: 主控流程，批量處理檔案和詞條

#### 2. 配置驅動批次處理 (Config-driven Batch Mode)
- **File**: `disaese_server.py`
- **Class**: `DiseaseTranslationBatch`
- **Purpose**: 自動搜尋並處理當前資料夾中所有符合條件的 xlsx 檔案
- **特點**:
  - 使用 `config.yaml` 進行參數管理
  - 自動搜尋 `classified_section_卷*.xlsx` 檔案
  - 支援智能降級處理：缺失上下文時自動使用最近卷號的上下文
  - 生成合併的翻譯報告
- **Key Methods**:
  - `find_classified_section_files()`: 搜尋待處理檔案
  - `process_all_files()`: 批次處理所有檔案
  - `_process_file_core_translation()`: 核心翻譯邏輯
  - `generate_merged_output()`: 生成合併報告

### Logging System
- **配置**: 內建於 `config.yaml` 的 `logging.server` 區塊
- **Log File**: `server.log` (最大10MB，保留2個備份)
- **Log Level**: DEBUG (可在 config.yaml 調整)

## Configuration

⚠️ **重要**: `disaese_server.py` 要求 `config.yaml` 文件存在且格式正確，否則程式會立即退出。

### 配置文件結構 (config.yaml)
- **model**: 模型路徑和生成參數 (max_new_tokens, temperature, top_p 等)
- **translation**: 翻譯配置 (token 限制、prompt 模板)
- **files**: 檔案路徑和輸出格式 (control_file, folder_path, volume_regex, 輸出檔案命名格式)
- **logging.server**: 日誌配置 (檔案名稱、大小限制、備份數量)
- **system**: 系統參數 (CUDA 設定、記憶體清理開關)

## Common Commands

### Running the Translation System

```bash
# 方式 1: 原始批次處理 (硬編碼路徑)
python translation_disaese.py

# 方式 2: 配置驅動批次處理 (自動搜尋當前資料夾所有 xlsx 檔案)
python disaese_server.py

# 使用自訂配置檔案
python disaese_server.py custom_config.yaml
```

### 語法檢查
```bash
python3 -m py_compile disaese_server.py
python3 -m py_compile translation_disaese.py
```

### Python Dependencies
核心套件：pandas, torch, transformers, pyyaml

## File Structure Patterns

### Input Data Files
- **Control File**: `7_附論段落.xlsx` (提供上下文段落)
- **Target Files**: `classified_section_卷XXX.xlsx` (包含待翻譯的中醫詞條)
- **Reference Data**: `草藥名稱標準化對照表.csv`

### Output Files
- **多檔案格式**: `上下文引導翻譯報告_卷XXX-卷XXX_YYYYMMDD.xlsx` (合併多卷)
- **單檔案格式**: `上下文引導翻譯報告_卷XXX_YYYYMMDD.xlsx`
- **位置**: 當前工作目錄（可在 config.yaml 中設定 `files.folder_path`）

## Development Guidelines

⚠️ **重要注意事項**:
- `translation_disaese.py` 是原始獨立批次處理程式，應保持不變
- 所有新功能和改進應在 `disaese_server.py` 中實作
- `disaese_server.py` 已改為批次處理模式，不再使用 TCP socket

### Model Usage Patterns
- 使用 `AutoTokenizer` 和 `AutoModelForCausalLM` 載入模型
- 設定 `torch_dtype="auto"` 和 `device_map="auto"` 進行最佳化配置
- 翻譯後執行 `gc.collect()` 和 `torch.cuda.empty_cache()` 清理記憶體（可在 config.yaml 中透過 `system.memory_cleanup` 控制）
- 支援智能模型路徑處理：本地路徑不存在時自動從 HuggingFace 下載

### Token Length Management
- **Model Limit**: 最大序列長度為 4096 tokens
- **自動截斷**: 系統自動檢測並截斷過長的上下文段落
- **截斷策略**: 保留最大 3800 tokens 供上下文使用（可在 config.yaml 中透過 `translation.max_context_tokens` 調整）
- **警告機制**: 當上下文被截斷或序列超長時會記錄警告訊息

### Prompt Engineering
Prompt 模板定義於 `config.yaml` 的 `translation.prompt_template`，包含：
- 上下文引導指示
- 翻譯規則（嚴格按原文翻譯、不添加額外內容、使用繁體白話文輸出）
- 變數：`{context_paragraph}` 和 `{term}`

### Data Processing
- Excel 檔案使用 pandas 進行讀取和處理
- 使用正則表達式匹配卷號（定義於 `config.yaml` 的 `files.volume_regex`）
- 詞條前處理：自動移除開頭的 "治療" 或 "治" 字元
- 輸出檔案命名包含日期戳記和卷號範圍

## Architecture Notes

### 批次處理流程
1. **初始化**：載入模型到 GPU、讀取控制檔案（`7_附論段落.xlsx`）
2. **檔案搜尋**：使用 glob 搜尋所有 `classified_section_卷*.xlsx` 檔案
3. **逐檔處理**：
   - 從檔名提取卷號
   - 匹配對應的上下文段落（支援智能降級：優先同卷同章節 → 同卷不同章節 → 最近卷號）
   - 讀取詞條並執行翻譯
   - 收集翻譯結果
4. **輸出合併**：將所有翻譯結果合併成單一 Excel 報告

### 智能降級機制
當控制檔案缺少特定卷號+章節的上下文時：
- **Level 1**: 使用相同卷號、不同章節的上下文
- **Level 2**: 使用數值最接近的卷號的上下文
- 所有降級操作都會記錄警告訊息到 log 中

系統設計為單機 GPU 環境，使用本地模型避免 API 調用的網路依賴。