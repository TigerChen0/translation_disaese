# SymMap 資料庫整合大表使用說明

## 概述

已成功建立基於 SymMap v2.0 的資料庫整合大表，將多個獨立的資料表整合成一個易於查詢和分析的主表。

**生成日期**: 2025-10-20
**資料來源**: SymMap v2.0 (http://www.symmap.org/)
**生成工具**: `generate_symmap_master_table.py`

---

## 生成的檔案

### 1. 主要整合表

#### `SymMap_Master_Table.xlsx` (Excel 格式)
- **記錄數**: 711 筆
- **檔案大小**: 0.10 MB
- **格式**: Excel (.xlsx)

#### `SymMap_Master_Table.csv` (CSV 格式)
- **記錄數**: 711 筆
- **檔案大小**: 0.15 MB
- **格式**: CSV (UTF-8-SIG 編碼)
- **優點**: 更小、載入更快、適合大資料分析

### 2. 參考資料表 (位於 `SymMap_Reference_Tables/` 目錄)

| 檔案名稱 | 內容 | 記錄數 |
|---------|------|--------|
| `diseases_reference.xlsx` | 疾病資訊 | 14,434 |
| `targets_reference.xlsx` | 靶點/基因資訊 | 20,965 |
| `modern_symptoms_reference.xlsx` | 現代醫學症狀 | 1,148 |
| `tcm_symptoms_reference.xlsx` | 中醫症狀 | 2,364 |
| `syndromes_reference.xlsx` | 中醫證型 | 233 |

---

## 主表結構

### 資料模型

```
主表 (SymMap_Master_Table)
├── Herb 資訊 (草藥基本資料)
│   ├── Herb_id
│   ├── Herb_Chinese (中文名稱)
│   ├── Herb_Pinyin (拼音)
│   ├── Herb_Latin (拉丁名)
│   ├── Herb_English (英文名)
│   ├── Herb_Aliases (別名)
│   ├── Properties_Chinese (藥性，如: 苦,寒)
│   ├── Properties_English
│   ├── Meridians_Chinese (歸經)
│   ├── Meridians_English
│   ├── Class_Chinese (藥物類別)
│   └── Class_English
│
├── Ingredient 資訊 (化學成分)
│   ├── Mol_id (分子 ID)
│   ├── Molecule_name (分子名稱)
│   ├── Molecule_formula (分子式)
│   ├── Molecule_weight (分子量)
│   ├── Molecule_Aliases (別名)
│   ├── PubChem_CID
│   ├── CAS_id
│   ├── OB_score (口服生物利用度評分)
│   └── Type (成分類型)
│
└── 關聯欄位
    ├── TCMSP_id (TCMSP 資料庫 ID)
    └── Link_ingredient_id (成分關聯 ID)
```

### 欄位說明 (共 23 個欄位)

| # | 欄位名稱 | 資料類型 | 說明 | 範例 |
|---|---------|----------|------|------|
| 1 | Herb_id | Integer | 草藥唯一識別碼 | 7 |
| 2 | Herb_Chinese | String | 草藥中文名稱 | 巴戟天 |
| 3 | Herb_Pinyin | String | 草藥拼音 | Bajitian |
| 4 | Herb_Latin | String | 拉丁學名 | Radix Morindae Officinalis |
| 5 | Herb_English | String | 英文名稱 | root of Medicinal Indianmulberry |
| 6 | Properties_Chinese | String | 中醫藥性 | 辛,温 |
| 7 | Properties_English | String | 藥性英文 | Acrid, Warm |
| 8 | Meridians_Chinese | String | 歸經 | 肝经,肾经 |
| 9 | Meridians_English | String | 歸經英文 | Liver, Kidney |
| 10 | Class_Chinese | String | 藥物類別 | 补阳药 |
| 11 | Class_English | String | 類別英文 | Yang-reinforcing |
| 12 | TCMSP_id | Float | TCMSP 資料庫 ID | 7.0 |
| 13 | Mol_id | Float | 分子 ID (可能為空) | 2498.0 |
| 14 | Molecule_name | String | 分子名稱 | Beta-Caryophyllene |
| 15 | Molecule_formula | String | 分子式 | C15H24 |
| 16 | Molecule_weight | Float | 分子量 | 204.35 |
| 17 | PubChem_CID | Float | PubChem 資料庫 ID | 5281515 |
| 18 | CAS_id | String | CAS 編號 | 87-44-5 |
| 19 | OB_score | Float | 口服生物利用度評分 | 32.75 |
| 20 | Type | String | 成分類型 | Blood ingredients |
| 21 | Link_ingredient_id | Float | 成分關聯 ID | 7.0 |
| 22 | Herb_Aliases | String | 草藥別名 (分號分隔) | 巴戟天; 巴戟 |
| 23 | Molecule_Aliases | String | 分子別名 (分號分隔) | Caryophyllene; ... |

---

## 資料統計

### 覆蓋率

| 項目 | 數量 | 百分比 |
|------|------|--------|
| **總草藥數** | 703 | 100% |
| 有成分資料的草藥 | 47 | 6.7% |
| 無成分資料的草藥 | 656 | 93.3% |
| **總成分數** | 55 | - |
| **總記錄數** | 711 | - |

### 資料類型分布

**藥性 (Properties_Chinese) Top 10:**
1. 苦,寒 (54 筆)
2. 辛,温 (40 筆)
3. 甘,平 (36 筆)
4. 甘,寒 (22 筆)
5. 甘,温 (19 筆)

**有成分的草藥範例:**
- 巴戟天 (Herb_id=7): 2 個成分
- 菝葜 (Herb_id=8): 1 個成分
- 白花菜子 (Herb_id=12): 1 個成分
- 白及 (Herb_id=14): 1 個成分
- 白蔹 (Herb_id=15): 1 個成分

---

## 使用方式

### 1. Excel 中直接查詢

```excel
# 篩選特定草藥
=FILTER(Table, Table[Herb_Chinese]="當歸")

# 統計每個草藥的成分數
=COUNTIF(Table[Herb_id], A2)
```

### 2. Python Pandas 分析

```python
import pandas as pd

# 載入主表
df = pd.read_excel("SymMap_Master_Table.xlsx")
# 或使用 CSV (更快)
df = pd.read_csv("SymMap_Master_Table.csv")

# 查詢特定草藥的所有成分
herb_id = 7  # 巴戟天
herb_data = df[df['Herb_id'] == herb_id]
print(herb_data[['Herb_Chinese', 'Molecule_name', 'Molecule_formula']])

# 查詢特定藥性的草藥
cold_herbs = df[df['Properties_Chinese'].str.contains('寒', na=False)]
print(f"寒性草藥數量: {cold_herbs['Herb_id'].nunique()}")

# 統計每個草藥的成分數
ingredient_counts = df[df['Mol_id'].notna()].groupby('Herb_Chinese').size()
print(ingredient_counts.sort_values(ascending=False))
```

### 3. 與參考表聯合查詢

```python
import pandas as pd

# 載入主表和靶點表
df_master = pd.read_csv("SymMap_Master_Table.csv")
df_targets = pd.read_excel("SymMap_Reference_Tables/targets_reference.xlsx")
df_diseases = pd.read_excel("SymMap_Reference_Tables/diseases_reference.xlsx")

# 查詢特定基因
gene_symbol = 'TP53'
target_info = df_targets[df_targets['Gene_symbol'] == gene_symbol]
print(target_info[['Gene_id', 'Gene_name', 'Chromosome']])

# 查詢特定疾病
disease_name = 'Diabetes'
disease_info = df_diseases[df_diseases['Disease_Name'].str.contains(disease_name, case=False, na=False)]
print(disease_info[['Disease_id', 'Disease_Name', 'OMIM_id']])
```

### 4. 草藥-成分網絡分析

```python
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

df = pd.read_csv("SymMap_Master_Table.csv")

# 只保留有成分的記錄
df_with_mol = df[df['Mol_id'].notna()]

# 建立草藥-成分網絡
G = nx.Graph()

for _, row in df_with_mol.iterrows():
    herb = row['Herb_Chinese']
    molecule = row['Molecule_name']
    G.add_edge(herb, molecule)

# 視覺化 (需要 matplotlib)
plt.figure(figsize=(12, 8))
pos = nx.spring_layout(G)
nx.draw(G, pos, with_labels=True, node_color='lightblue',
        node_size=500, font_size=8)
plt.title("Herb-Ingredient Network")
plt.savefig("herb_ingredient_network.png")
```

---

## 局限性與改進方向

### 當前局限

1. **成分資料覆蓋率低 (6.7%)**
   - 原因: SymMap 中只有 47 個草藥有 TCMSP_id 且能與成分表關聯
   - 影響: 大部分草藥 (656/703) 只有基本資訊，沒有化學成分資料

2. **缺少 Ingredient → Target 直接關聯**
   - SymMap 的 SMIT 檔案雖名為 "Ingredient-Target"，但實際沒有 Target 欄位
   - 無法直接追溯成分作用於哪些靶點基因

3. **缺少 Target → Disease 直接關聯**
   - 靶點和疾病表為獨立資料，沒有直接關聯欄位
   - 需要外部資料庫 (如 DisGeNET, CTD) 補充

4. **缺少 Herb → Symptom/Disease 直接關聯**
   - 無法直接查詢某草藥治療哪些疾病或症狀

### 改進建議

#### 短期改進 (資料補充)

1. **提高成分覆蓋率**
   ```python
   # 使用其他 ID 欄位進行關聯
   # - TCMID_id
   # - TCM-ID_id
   # - 草藥名稱模糊匹配
   ```

2. **整合外部資料庫**
   - TCMSP (Traditional Chinese Medicine Systems Pharmacology)
   - TCMID (Traditional Chinese Medicine Integrated Database)
   - HERB Database
   - CTD (Comparative Toxicogenomics Database)
   - DisGeNET (基因-疾病關聯資料庫)

#### 中期改進 (關聯建立)

3. **建立 Ingredient-Target 關聯**
   ```
   方法 1: 透過 PubChem_CID 查詢 PubChem BioAssay
   方法 2: 使用 STITCH 資料庫 (化學物-蛋白質交互作用)
   方法 3: 文獻挖掘 + 人工標註
   ```

4. **建立 Target-Disease 關聯**
   ```
   資料源:
   - DisGeNET: 基因-疾病關聯評分
   - OMIM: 基因-疾病關聯
   - CTD: 化學物-基因-疾病網絡
   ```

5. **建立 Herb-Disease 關聯**
   ```
   資料源:
   - 中醫古籍文獻挖掘
   - 臨床處方資料庫
   - TCMID 中醫藥綜合資料庫
   ```

#### 長期改進 (智能分析)

6. **藥對 (Herb Pair) 分析**
   - 基於 `core_index_all.csv` 進行配伍規律分析
   - 計算草藥組合的協同作用

7. **網絡藥理學分析**
   - 建立 Herb-Ingredient-Target-Disease 多層網絡
   - 計算網絡拓撲特徵 (度、介數中心性等)
   - 預測潛在作用機制

8. **機器學習預測**
   - 訓練模型預測草藥-疾病關聯
   - 預測草藥的未知成分或靶點

---

## 常見問題 (FAQ)

### Q1: 為什麼只有 6.7% 的草藥有成分資料？

**A**: SymMap 資料庫中用於關聯草藥和成分的關鍵欄位 (`TCMSP_id` 和 `Link_ingredient_id`) 資料覆蓋率較低。建議整合 TCMSP、TCMID 等其他資料庫來補充。

### Q2: 如何追溯草藥的靶點和疾病？

**A**: 當前版本無法直接追溯。建議：
1. 使用參考表中的 `targets_reference.xlsx` 和 `diseases_reference.xlsx` 進行手動查詢
2. 整合外部資料庫 (DisGeNET, CTD) 建立關聯
3. 使用 SymMap 網站的 API 進行線上查詢

### Q3: CSV 和 Excel 格式有什麼區別？

**A**:
- **CSV**: 檔案較小 (0.15 MB)、載入更快、適合程式分析
- **Excel**: 支援格式化、篩選、公式等功能，適合人工查詢

建議用 CSV 進行程式分析，用 Excel 進行探索性查詢。

### Q4: 如何更新整合表？

**A**:
```bash
# 重新執行生成腳本
python3 generate_symmap_master_table.py
```

如果 SymMap 資料庫有更新，先替換 `SymMap/` 目錄中的檔案，再執行腳本。

### Q5: 可以擴展整合表嗎？

**A**: 可以！修改 `generate_symmap_master_table.py` 中的 `build_herb_ingredient_master()` 函數：
- 添加更多欄位
- 使用其他 ID 欄位進行關聯
- 整合外部資料源

---

## 參考資料

- **SymMap 官網**: http://www.symmap.org/
- **SymMap 論文**: Wu, Y. et al. (2019). SymMap: an integrative database of traditional Chinese medicine enhanced by symptom mapping. *Nucleic Acids Research*, 47(D1), D1110-D1117.
- **TCMSP 資料庫**: http://tcmspw.com/tcmsp.php
- **TCMID 資料庫**: http://www.megabionet.org/tcmid/
- **DisGeNET**: https://www.disgenet.org/
- **CTD (Comparative Toxicogenomics Database)**: http://ctdbase.org/

---

## 版本歷史

| 版本 | 日期 | 更新內容 |
|------|------|---------|
| v1.0 | 2025-10-20 | 初始版本，整合草藥-成分資料 |

---

## 聯絡與支援

如有問題或建議，請：
1. 檢查 SymMap 官方文件
2. 查閱相關論文
3. 提交 Issue 到專案儲存庫

**生成工具**: `/home/nculcwu/DeepSeek/generate_symmap_master_table.py`
**資料位置**: `/home/nculcwu/DeepSeek/`
