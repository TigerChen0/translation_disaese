# Ingredient-Target 關聯資料獲取完整報告

## 📋 問題描述

**問題**: 為什麼 SymMap 本地檔案缺少 Ingredient → Target 關聯？

**原因確認**:

經過完整檢查，確認 SymMap v2.0 下載檔案中 **確實缺少** Mol_id ↔ Gene_id 的直接關聯：

1. ✅ **SMIT file (成分表)**: 有 Mol_id，但沒有 Gene_id 欄位
2. ✅ **SMTT file (靶點表)**: 有 Gene_id，但沒有 Mol_id 欄位
3. ✅ **SMIT key file**: 只包含 Molecule_name, CAS_id, Alias
4. ✅ **SMTT key file**: 只包含 Gene_symbol, Gene_name, Protein_name, Ensembl_id
5. ❌ **其他檔案**: 全部檢查完畢，無任何中介關聯表

**結論**: 這不是下載問題，而是 **SymMap v2.0 公開資料集的設計限制**。需要透過 API 或其他資料庫補充此關聯。

---

## 🎯 解決方案

### 最終採用: 透過 PubChem API + NCBI Gene API

**技術路線**:
```
Mol_id (SymMap)
  ↓ [查詢 SymMap_Master_Table.csv]
PubChem_CID
  ↓ [PubChem BioAssay API]
NCBI Gene_ID
  ↓ [NCBI E-utilities API]
Gene_symbol
  ↓ [與 SymMap SMTT 的 Gene_symbol 匹配]
Gene_id (SymMap)
```

### 為什麼選這個方法？

| 方法 | 優點 | 缺點 | 結果 |
|------|------|------|------|
| SymMap 官方 API | 直接、準確 | API 文件不完整，端點未知 | ❌ 未實作 |
| 網頁爬蟲 | 資料完整 | 違反使用條款、維護困難 | ❌ 不建議 |
| **PubChem API** | **公開、穩定、資料豐富** | **需要兩次 API 查詢** | ✅ **成功** |
| 本地檔案分析 | 不需網路 | 本地檔案確實缺少關聯 | ❌ 不可行 |

---

## 🛠️ 實作工具

### 工具 1: `fetch_ingredient_targets_pubchem.py`

**功能**: 透過 PubChem BioAssay API 獲取成分對應的生物檢測資料和靶點。

**使用方式**:
```bash
python3 fetch_ingredient_targets_pubchem.py
# 輸入要查詢的成分數量（建議先測試少量）
```

**輸出檔案**:
- `ingredient_target_pubchem_raw.csv`: 原始 PubChem 資料（包含 NCBI Gene_ID）

**關鍵參數**:
- `delay`: 請求延遲（預設 0.5 秒，避免速率限制）
- `max_per_compound`: 每個化合物最多保留的靶點數量（預設 10）

### 工具 2: `map_pubchem_to_symmap.py`

**功能**: 將 PubChem 查詢的 NCBI Gene_ID 映射到 SymMap Gene_id。

**技術細節**:
1. 透過 NCBI E-utilities API 將 NCBI Gene_ID 轉換成 Gene_symbol
2. 與 SymMap SMTT 的 Gene_symbol 進行大小寫不敏感匹配
3. 成功映射率: **90.7%** (39/43 筆記錄)

**使用方式**:
```bash
python3 map_pubchem_to_symmap.py
```

**輸出檔案**:
- `ingredient_target_mapping_final.csv`: 完整對應表
- `ingredient_target_mapping_final.xlsx`: Excel 格式
- `ingredient_target_mapping_active_only.csv`: 僅包含 Active 的關聯

### 工具 3: `symmap_api_fetcher.py`

**功能**: 多方法測試工具，包含：
1. SymMap API 查詢（端點未知，未成功）
2. 網頁爬蟲（僅框架）
3. PubChem 查詢（已整合到工具 1）
4. 本地檔案分析（已確認無關聯）

**使用方式**:
```bash
python3 symmap_api_fetcher.py
# 選擇測試方法 (1-5)
```

---

## 📊 成果統計 (基於 5 個成分的測試)

### 查詢結果

| 項目 | 數量 | 說明 |
|------|------|------|
| **查詢成分數** | 5 | Beta-Caryophyllene, Daucosterol, Protocatechuic Acid 等 |
| **獲得關聯總數** | 43 筆 | PubChem BioAssay 原始資料 |
| **成功映射到 SymMap** | 39 筆 | **90.7% 成功率** |
| **涉及 SymMap 靶點** | 26 個 | 包含 CNR2, PPARA, CYP3A4 等 |
| **Active 關聯** | 20 筆 | 具有明確藥理活性的關聯 |

### 靶點數量最多的成分 Top 5

1. **Beta-Caryophyllene** (Mol_id=2498): 10 個靶點
   - 主要靶點: CNR2, PPARA, CYP3A4
   - 活性: 包含多個 Active 關聯

2. **Beta-Caryophyllene** (Mol_id=2500): 10 個靶點
   - 重複成分（不同來源草藥）

3. **Daucosterol** (Mol_id=2655): 10 個靶點

4. **Protocatechuic Acid** (Mol_id=2489): 6 個靶點

5. **Atractylone** (Mol_id=2682): 3 個靶點

### 被最多成分作用的靶點 Top 5

1. **CNR2** (Cannabinoid Receptor 2): 4 個成分作用
2. **CYP3A4** (Cytochrome P450 3A4): 4 個成分作用
3. **PPARA** (Peroxisome Proliferator Activated Receptor Alpha): 2 個成分
4. **RGS12** (Regulator of G Protein Signaling 12): 2 個成分
5. **GNAI1** (G Protein Subunit Alpha I1): 2 個成分

---

## 📁 生成的資料檔案

### 主要輸出檔案

| 檔案名稱 | 記錄數 | 說明 |
|---------|--------|------|
| `ingredient_target_pubchem_raw.csv` | 43 | PubChem 原始查詢結果 |
| `ingredient_target_mapping_final.csv` | 39 | **最終對應表（推薦使用）** |
| `ingredient_target_mapping_final.xlsx` | 39 | Excel 格式 |
| `ingredient_target_mapping_active_only.csv` | 20 | 僅包含 Active 關聯 |

### 快取目錄

- `/home/nculcwu/DeepSeek/PubChem_Cache/`: PubChem API 查詢快取
- `/home/nculcwu/DeepSeek/NCBI_Gene_Cache/`: NCBI Gene API 查詢快取

---

## 🔍 資料欄位說明

### ingredient_target_mapping_final.csv

| 欄位名稱 | 資料類型 | 說明 | 範例 |
|---------|---------|------|------|
| **Mol_id** | Integer | SymMap 分子 ID | 2498 |
| **Target_GeneID** | Integer | NCBI Gene ID | 1269 |
| **NCBI_Gene_symbol** | String | 基因符號 | CNR2 |
| **SymMap_Gene_id** | Integer | SymMap 靶點 ID | 5658 |
| **SymMap_Gene_name** | String | 基因全名 | cannabinoid receptor 2 |
| **SymMap_Protein_name** | String | 蛋白質名稱 | Cannabinoid receptor 2 |
| **Activity_Outcome** | String | 活性結果 | Active / Inactive |
| **Activity_Value_uM** | Float | 活性數值 (µM) | 0.15 |
| **Activity_Name** | String | 活性類型 | Ki, EC50, IC50 |
| **Assay_Name** | String | 檢測名稱 | Displacement of [3H]CP55940... |
| **Assay_Type** | String | 檢測類型 | Confirmatory |
| **PubMed_ID** | Integer | 文獻 PubMed ID | 30096653 |
| **AID** | Integer | PubChem Assay ID | 1612079 |
| **CID** | Integer | PubChem Compound ID | 5281515 |

---

## 🚀 下一步行動

### 擴展到所有成分

目前只測試了 5 個成分，要擴展到所有 54 個有 PubChem_CID 的成分：

```bash
# 方法 1: 全部查詢（需要約 30 分鐘）
python3 fetch_ingredient_targets_pubchem.py
# 輸入: 54

# 方法 2: 分批查詢（避免超時）
python3 fetch_ingredient_targets_pubchem.py
# 第一批: 20 個
# 第二批: 20 個
# 第三批: 14 個

# 每批完成後執行映射
python3 map_pubchem_to_symmap.py
```

### 補充更多成分資料

SymMap_Master_Table 中有 54 個成分有 PubChem_CID，佔總成分數的 **54/711 = 7.6%**。

**提升覆蓋率的方法**:

1. **使用 CAS_id 查詢 PubChem**
   ```python
   # 透過 CAS_id 查詢 PubChem CID
   # 然後使用相同流程
   ```

2. **整合 STITCH 資料庫**
   - STITCH: Chemical-Protein 交互作用資料庫
   - 網址: http://stitch.embl.de/
   - 可透過化合物名稱或 CAS_id 查詢

3. **使用 ChEMBL API**
   - ChEMBL: 歐洲生物資訊研究所的化合物資料庫
   - API: https://www.ebi.ac.uk/chembl/api/data/docs

4. **查詢 TCMSP 資料庫**
   - TCMSP: 中藥系統藥理學資料庫
   - 已有部分成分的 TCMSP_id

---

## 📖 使用範例

### 範例 1: 查詢特定成分的靶點

```python
import pandas as pd

# 載入對應表
df = pd.read_csv("/home/nculcwu/DeepSeek/ingredient_target_mapping_final.csv")

# 查詢 Beta-Caryophyllene (Mol_id=2498) 的所有靶點
mol_2498 = df[df['Mol_id'] == 2498]

print(f"Beta-Caryophyllene 作用的靶點:")
for _, row in mol_2498.iterrows():
    print(f"  {row['NCBI_Gene_symbol']}: {row['Activity_Outcome']} (Activity: {row['Activity_Value_uM']} µM)")
```

### 範例 2: 查詢特定靶點的成分

```python
# 查詢作用於 CNR2 的所有成分
cnr2_mols = df[df['NCBI_Gene_symbol'] == 'CNR2']

# 載入 Master Table 取得成分名稱
df_master = pd.read_csv("/home/nculcwu/DeepSeek/SymMap_Master_Table.csv")

print(f"作用於 CNR2 的成分:")
for mol_id in cnr2_mols['Mol_id'].unique():
    mol_info = df_master[df_master['Mol_id'] == mol_id].iloc[0]
    print(f"  {mol_info['Molecule_name']} (Mol_id={mol_id})")
```

### 範例 3: 驗證草藥配伍的共同靶點

```python
import pandas as pd

# 載入資料
df_mapping = pd.read_csv("/home/nculcwu/DeepSeek/ingredient_target_mapping_final.csv")
df_master = pd.read_csv("/home/nculcwu/DeepSeek/SymMap_Master_Table.csv")

# 假設要驗證兩個草藥的配伍
herb_id_1 = 41   # 五味子
herb_id_2 = 304  # 牛膝

# 取得兩個草藥的成分
mols_1 = set(df_master[df_master['Herb_id'] == herb_id_1]['Mol_id'].dropna())
mols_2 = set(df_master[df_master['Herb_id'] == herb_id_2]['Mol_id'].dropna())

# 取得各自的靶點
targets_1 = set(df_mapping[df_mapping['Mol_id'].isin(mols_1)]['SymMap_Gene_id'])
targets_2 = set(df_mapping[df_mapping['Mol_id'].isin(mols_2)]['SymMap_Gene_id'])

# 計算共同靶點
common_targets = targets_1 & targets_2

print(f"五味子靶點數: {len(targets_1)}")
print(f"牛膝靶點數: {len(targets_2)}")
print(f"共同靶點數: {len(common_targets)}")
print(f"Jaccard 相似度: {len(common_targets) / len(targets_1 | targets_2):.3f}")
```

---

## ⚠️ 注意事項

### API 速率限制

1. **PubChem API**
   - 無明確速率限制文件
   - 建議延遲: 0.5 秒/請求
   - 測試結果: 5 個成分需約 20 秒

2. **NCBI E-utilities API**
   - 官方限制: **每秒 3 個請求**
   - 程式已設定: 0.34 秒/請求
   - 27 個 Gene_ID 需約 25 秒

### 快取機制

- 所有 API 查詢結果都會快取
- 重複執行不會重新查詢
- 快取位置:
  - PubChem: `/home/nculcwu/DeepSeek/PubChem_Cache/`
  - NCBI: `/home/nculcwu/DeepSeek/NCBI_Gene_Cache/`

### 資料品質

- **映射成功率: 90.7%** (基於測試資料)
- 未成功映射的原因:
  1. NCBI Gene_ID 在 SymMap 中不存在 (4.7%)
  2. Gene_symbol 不匹配 (4.6%)

---

## 🔬 技術細節

### PubChem BioAssay API

**端點**:
```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{pubchem_cid}/assaysummary/JSON
```

**回應格式**:
```json
{
  "Table": {
    "Columns": {
      "Column": ["AID", "SID", "CID", "Activity Outcome", "Target GeneID", ...]
    },
    "Row": [
      {
        "Cell": [1612079, 103581571, 5281515, "Active", "P34972", 1269, 0.15, ...]
      }
    ]
  }
}
```

### NCBI E-utilities API

**端點**:
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gene&id={gene_id}&retmode=json
```

**回應格式**:
```json
{
  "result": {
    "1269": {
      "name": "CNR2",
      "description": "cannabinoid receptor 2",
      "organism": {"scientificname": "Homo sapiens"}
    }
  }
}
```

---

## 📊 對比：查詢前 vs. 查詢後

### 查詢前

```
SymMap 資料:
- Herb: 703 個
- Ingredient: 55 個（在 Master Table 中）
- Target: 20,965 個
- Herb-Ingredient 關聯: 55 筆
- Ingredient-Target 關聯: ❌ 0 筆
```

### 查詢後 (5 個成分測試)

```
新增資料:
- Ingredient-Target 關聯: ✅ 39 筆 (mapped to SymMap)
- 涉及成分: 5 個
- 涉及靶點: 26 個
- Active 關聯: 20 筆

覆蓋率提升:
- Ingredient 覆蓋率: 5/55 = 9.1%
- 預估全部 54 個有 PubChem_CID 的成分可獲得: ~400 筆關聯
```

---

## 🎓 學習要點

### 為什麼需要兩次 API 查詢？

1. **PubChem 使用 NCBI Gene_ID** (數值型別)
   - 範例: 1269, 5465, 6002

2. **SymMap 使用自己的 Gene_id** (數值型別)
   - 範例: 5658, 2679, 9899

3. **兩者不是同一個 ID 系統！**
   - 需要透過 Gene_symbol 作為橋樑
   - NCBI Gene_ID 1269 → Gene_symbol "CNR2" → SymMap Gene_id 5658

### 為什麼不直接用 NCBI_id 匹配？

檢查發現 SymMap SMTT 的 NCBI_id 欄位：
- 數值範圍與 PubChem 的 NCBI Gene_ID 不一致
- 可能是不同的 ID 系統或版本

---

## 📚 參考資料

- **PubChem**: https://pubchem.ncbi.nlm.nih.gov/
- **PubChem API 文件**: https://pubchemdocs.ncbi.nlm.nih.gov/pug-rest
- **NCBI E-utilities**: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- **SymMap**: http://www.symmap.org/
- **STITCH**: http://stitch.embl.de/
- **ChEMBL**: https://www.ebi.ac.uk/chembl/

---

## ✅ 完成檢查清單

- [x] 確認 SymMap 本地檔案確實缺少 Ingredient-Target 關聯
- [x] 測試多種替代方案
- [x] 實作 PubChem API 查詢工具
- [x] 實作 NCBI Gene API 映射工具
- [x] 成功獲取 39 筆 Ingredient-Target 關聯
- [x] 生成最終對應表 (CSV + Excel)
- [x] 建立快取機制
- [x] 撰寫完整文件

---

## 🔄 後續維護

### 定期更新建議

1. **每季度更新一次**
   - PubChem 資料持續增加
   - 可獲得更多生物檢測資料

2. **擴展到所有成分**
   - 目前只測試 5 個成分
   - 建議分批處理所有 54 個有 PubChem_CID 的成分

3. **整合其他資料庫**
   - STITCH, ChEMBL, TCMSP
   - 提升成分覆蓋率到 50% 以上

---

**生成日期**: 2025-10-22
**作者**: Claude Code
**版本**: v1.0
**工具**: PubChem API + NCBI E-utilities API
