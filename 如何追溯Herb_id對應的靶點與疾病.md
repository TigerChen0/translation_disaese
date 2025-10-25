# 如何從 Herb_id 追溯對應的靶點與疾病

## 問題描述

你執行了 `analyze_herb_associations_improved.py` 分析草藥關聯性，輸出檔案 `herb_association_analysis_improved.xlsx` 中只包含 **Herb_id 號碼**（如 41, 359, 304 等），但你想知道這些號碼對應的**靶點 (Target)** 和**疾病 (Disease)** 資訊。

## 快速解答

我已經為你建立了兩個查詢工具檔案：

### 1. **herb_id_lookup_table.xlsx** - Herb_id 快速對照表

**檔案路徑**: `/home/nculcwu/DeepSeek/herb_id_lookup_table.xlsx`

**內容範例**:
| Herb_id | Chinese_name | Pinyin_name | English_name | Ingredient_count | Sample_molecules |
|---------|--------------|-------------|--------------|------------------|------------------|
| 41 | 五味子 | Wuweizi | Schisandrae Chinensis Fructus | 0 | |
| 93 | 丹参 | Danshen | ... | 0 | |
| 216 | 桔梗 | Jiegeng | ... | 1 | Glucuronic Acid |

**用途**: 快速查詢 Herb_id 對應的中文名稱和基本資訊

---

### 2. **herb_ingredient_detailed_report.xlsx** - 詳細成分對照表

**檔案路徑**: `/home/nculcwu/DeepSeek/herb_ingredient_detailed_report.xlsx`

**內容欄位**:
- `Community`: 社群編號
- `Core_Index`: 核心組合編號
- `Core_Combo`: 核心草藥組合（中文）
- `Herb_id`: 草藥 ID
- `Chinese_name`: 中文名稱
- `Pinyin_name`: 拼音
- `English_name`: 英文名稱
- `Mol_id`: 成分分子 ID
- `Molecule_name`: 成分名稱
- `Molecule_formula`: 分子式

**用途**: 查看每個 Herb_id 關聯的化學成分資訊

---

## SymMap 資料庫結構說明

### 資料關聯路徑

```
Herb (草藥)
  ↓ Herb_id → TCMSP_id (SMHB)
  ↓
Ingredient (成分)
  ↓ Link_ingredient_id (SMIT) → Mol_id
  ↓
Target (靶點)
  ↓ Gene_id (SMTT)
  ↓
Disease (疾病)
  ↓ Disease_id (SMDE)
```

### 關鍵發現

1. **Herb_id 到成分的關聯**:
   - `SMHB.Herb_id` → `SMHB.TCMSP_id`
   - `SMHB.TCMSP_id` = `SMIT.Link_ingredient_id`
   - `SMIT.Link_ingredient_id` → `SMIT.Mol_id` (成分分子)

2. **成分到靶點的關聯** (尚未實作):
   - `SMIT.Mol_id` → `SMTT.Gene_id`
   - 需要另外的關聯表或 key file

3. **靶點到疾病的關聯** (尚未實作):
   - `SMTT.Gene_id` → `SMDE.Disease_id`
   - 需要查詢 key file 或另外的關聯表

---

## 當前限制

### 資料完整性問題

從分析結果來看，**60 個草藥中只有 5 個 (8.3%)** 有成分資料：

| Herb_id | Chinese_name | Ingredient_count | 說明 |
|---------|--------------|------------------|------|
| 15 | 白蔹 | 1 | 有成分資料 ✓ |
| 65 | 赤芍 | 1 | 有成分資料 ✓ |
| 90 | 大枣 | 1 | 有成分資料 ✓ |
| 216 | 桔梗 | 1 | 有成分資料 ✓ |
| 348 | 桑白皮 | 1 | 有成分資料 ✓ |
| 41 | 五味子 | 0 | **無成分資料** ✗ |
| 93 | 丹参 | 0 | **無成分資料** ✗ |
| 188 | 黄芩 | 0 | **無成分資料** ✗ |
| ... | ... | 0 | ... |

### 原因分析

1. **TCMSP_id 缺失**: 大部分草藥在 `SMHB.TCMSP_id` 欄位中沒有數值
2. **資料庫版本差異**: SymMap v2.0 可能對某些草藥的成分資料收錄不完整
3. **命名/簡繁轉換問題**: 部分草藥因簡繁體或別名問題未能正確匹配

---

## 使用流程示範

### 步驟 1: 從分析結果找到 Herb_id

打開 `herb_association_analysis_improved.xlsx`，找到你關心的記錄：

```
Community: 0
Core_Index: 1
Core_Combo: 五味子、山藥、牛膝、肉蓯蓉
core_herb_ids: 41, 359, 304, 338
```

### 步驟 2: 查詢草藥名稱

打開 `herb_id_lookup_table.xlsx`，查詢 Herb_id=41：

```
Herb_id: 41
Chinese_name: 五味子
Pinyin_name: Wuweizi
English_name: Schisandrae Chinensis Fructus
Ingredient_count: 0   ← 表示沒有成分資料
```

### 步驟 3: 查看詳細成分（如果有）

打開 `herb_ingredient_detailed_report.xlsx`，篩選 Herb_id=216（桔梗）：

```
Herb_id: 216
Chinese_name: 桔梗
Mol_id: 2567
Molecule_name: Glucuronic Acid
Molecule_formula: C6H10O7
```

### 步驟 4: 進一步追溯靶點和疾病（需額外開發）

目前 `lookup_herb_targets_diseases.py` 只實作到**成分層級**。如果需要追溯到**靶點**和**疾病**，需要：

1. 查詢 `SMTT file.xlsx` 中 `Gene_id` 與 `Mol_id` 的關聯
2. 查詢 `SMDE file.xlsx` 中 `Disease_id` 與 `Gene_id` 的關聯
3. 可能需要檢查 `SMTT key file.xlsx` 和 `SMDE key file.xlsx`

---

## 改進建議

### 1. 補充缺失的 TCMSP_id

**問題**: 55 個草藥 (91.7%) 缺少 TCMSP_id，導致無法查詢成分

**解決方案**:
- 使用 `TCMID_id` 或 `TCM-ID_id` 作為替代關聯欄位
- 透過草藥名稱（中文/拼音/英文）進行模糊匹配
- 整合其他中醫藥資料庫 (TCMSP, TCMID, HERB)

### 2. 實作成分-靶點關聯

需要研究 SymMap 的資料結構，找到 `Mol_id` 到 `Gene_id` 的關聯方式。

可能的路徑：
- 檢查 `SMTT key file.xlsx` 中是否有 Mol_id 相關記錄
- 查看 SymMap 官方文件或論文
- 使用 PubChem CID 作為中介關聯

### 3. 實作靶點-疾病關聯

需要找到 `Gene_id` 到 `Disease_id` 的對應表。

可能的資源：
- `SMTT key file.xlsx` 或 `SMDE key file.xlsx`
- DisGeNET、CTD 等疾病-基因關聯資料庫
- SymMap 網站的 API 或資料下載頁面

---

## 工具程式說明

### 使用方式

```bash
# 生成 Herb_id 查詢表和詳細報告
python3 lookup_herb_targets_diseases.py
```

### 輸出檔案

1. **herb_id_lookup_table.xlsx** - 所有 Herb_id 的快速查詢表
2. **herb_ingredient_detailed_report.xlsx** - 包含成分資訊的詳細報告

### 程式架構

```python
class HerbTargetDiseaseMapper:
    - load_data(): 載入 SymMap 資料庫
    - get_herb_info(herb_id): 查詢草藥基本資訊
    - get_targets_for_herb(herb_id): 查詢草藥的成分 (透過 TCMSP_id)
    - create_lookup_table(): 建立快速查詢表
    - create_detailed_report(): 建立詳細報告
```

---

## 下一步行動

### 短期目標

1. ✅ **建立 Herb_id 查詢表** - 已完成
2. ✅ **實作 Herb → 成分關聯** - 已完成 (8.3% 覆蓋率)
3. ⬜ **提高成分資料覆蓋率** - 補充缺失的 TCMSP_id
4. ⬜ **實作成分 → 靶點關聯** - 需研究資料結構
5. ⬜ **實作靶點 → 疾病關聯** - 需研究資料結構

### 中期目標

1. 整合 TCMSP、TCMID 等資料庫
2. 建立完整的 Herb → Ingredient → Target → Disease 追溯系統
3. 視覺化關聯網絡（使用 NetworkX 或 Cytoscape）

---

## 參考資料

- **SymMap 官網**: http://www.symmap.org/
- **SymMap 論文**: Wu, Y. et al. (2019). SymMap: an integrative database of traditional Chinese medicine enhanced by symptom mapping. *Nucleic Acids Research*, 47(D1), D1110-D1117.
- **資料檔案位置**: `/home/nculcwu/DeepSeek/SymMap/`

---

## 聯絡與協作

如果需要進一步開發**靶點追溯**或**疾病關聯**功能，請：

1. 提供 SymMap 的 Schema 文件或官方說明
2. 確認是否有其他關聯表檔案未被使用
3. 考慮使用 SymMap 網站 API 直接查詢

**程式檔案**: `/home/nculcwu/DeepSeek/lookup_herb_targets_diseases.py`
**生成日期**: 2025-10-20
