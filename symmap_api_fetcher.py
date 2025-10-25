#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SymMap API 資料獲取工具

用途：透過 SymMap 網站 API 獲取 Ingredient → Target 關聯資料
解決問題：本地 SymMap 檔案缺少 Mol_id ↔ Gene_id 的直接關聯

作者：Claude Code
日期：2025-10-22
"""

import requests
import pandas as pd
import time
import json
import os
from typing import Dict, List, Set, Optional
from tqdm import tqdm


class SymMapAPIFetcher:
    """SymMap API 查詢器"""

    def __init__(self):
        self.base_url = "http://www.symmap.org"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # 快取機制
        self.cache_dir = "/home/nculcwu/DeepSeek/SymMap_API_Cache"
        os.makedirs(self.cache_dir, exist_ok=True)

        print("SymMap API Fetcher 初始化完成")
        print(f"快取目錄: {self.cache_dir}")

    def get_ingredient_targets(self, mol_id: int, use_cache: bool = True) -> Optional[Dict]:
        """
        查詢成分對應的靶點

        Args:
            mol_id: SymMap 分子 ID
            use_cache: 是否使用快取

        Returns:
            包含靶點資訊的字典，若失敗則返回 None
        """
        # 檢查快取
        cache_file = os.path.join(self.cache_dir, f"mol_{mol_id}_targets.json")
        if use_cache and os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        # API 查詢
        # 注意：以下是推測的 API 端點，可能需要根據實際情況調整
        api_endpoints = [
            f"{self.base_url}/api/ingredient/{mol_id}/targets",
            f"{self.base_url}/api/molecule/{mol_id}/targets",
            f"{self.base_url}/api/ingredient/targets?mol_id={mol_id}",
        ]

        for endpoint in api_endpoints:
            try:
                response = self.session.get(endpoint, timeout=10)

                if response.status_code == 200:
                    data = response.json()

                    # 儲存快取
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    return data

            except Exception as e:
                continue

        # 如果所有端點都失敗，記錄並返回 None
        print(f"⚠️ Mol_id {mol_id} 查詢失敗")
        return None

    def get_herb_targets(self, herb_id: int, use_cache: bool = True) -> Optional[Dict]:
        """
        查詢草藥對應的靶點（透過其成分）

        Args:
            herb_id: SymMap 草藥 ID
            use_cache: 是否使用快取

        Returns:
            包含靶點資訊的字典
        """
        cache_file = os.path.join(self.cache_dir, f"herb_{herb_id}_targets.json")
        if use_cache and os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        api_endpoints = [
            f"{self.base_url}/api/herb/{herb_id}/targets",
            f"{self.base_url}/api/herb/targets?herb_id={herb_id}",
        ]

        for endpoint in api_endpoints:
            try:
                response = self.session.get(endpoint, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    return data
            except Exception as e:
                continue

        return None

    def batch_fetch_ingredient_targets(
        self,
        mol_ids: List[int],
        delay: float = 0.5,
        max_retries: int = 3
    ) -> pd.DataFrame:
        """
        批次查詢多個成分的靶點

        Args:
            mol_ids: 分子 ID 列表
            delay: 每次請求之間的延遲（秒）
            max_retries: 最大重試次數

        Returns:
            包含 Mol_id, Gene_id, Gene_symbol 等欄位的 DataFrame
        """
        results = []

        print(f"開始批次查詢 {len(mol_ids)} 個成分的靶點資料...")

        for mol_id in tqdm(mol_ids, desc="查詢進度"):
            retry_count = 0
            success = False

            while retry_count < max_retries and not success:
                try:
                    data = self.get_ingredient_targets(mol_id)

                    if data:
                        # 解析回應資料（需根據實際 API 回應格式調整）
                        if isinstance(data, dict) and 'targets' in data:
                            for target in data['targets']:
                                results.append({
                                    'Mol_id': mol_id,
                                    'Gene_id': target.get('gene_id'),
                                    'Gene_symbol': target.get('gene_symbol'),
                                    'Gene_name': target.get('gene_name'),
                                    'Interaction_score': target.get('score'),
                                })
                        success = True

                    # 延遲以避免過度請求
                    time.sleep(delay)

                except Exception as e:
                    retry_count += 1
                    print(f"  錯誤 (Mol_id={mol_id}, 嘗試 {retry_count}/{max_retries}): {str(e)}")
                    time.sleep(delay * 2)

        df_results = pd.DataFrame(results)
        return df_results

    def save_ingredient_target_mapping(self, df: pd.DataFrame, output_path: str):
        """儲存成分-靶點對應表"""
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        df.to_excel(output_path.replace('.csv', '.xlsx'), index=False, engine='openpyxl')
        print(f"✅ 對應表已儲存:")
        print(f"  CSV: {output_path}")
        print(f"  Excel: {output_path.replace('.csv', '.xlsx')}")


def method_1_symmap_api():
    """方法 1: 使用 SymMap 官方 API"""
    print("="*80)
    print("方法 1: 使用 SymMap API 獲取 Ingredient-Target 資料")
    print("="*80)

    # 載入現有的成分資料
    df_master = pd.read_csv("/home/nculcwu/DeepSeek/SymMap_Master_Table.csv")
    mol_ids = df_master['Mol_id'].dropna().astype(int).unique().tolist()

    print(f"需要查詢的成分數量: {len(mol_ids)}")
    print(f"範例 Mol_id: {mol_ids[:10]}")

    # 建立 API 查詢器
    fetcher = SymMapAPIFetcher()

    # 批次查詢
    df_ingredient_targets = fetcher.batch_fetch_ingredient_targets(
        mol_ids[:10],  # 先測試前 10 個
        delay=1.0
    )

    print(f"\n查詢結果:")
    print(df_ingredient_targets.head(20))

    # 儲存結果
    if len(df_ingredient_targets) > 0:
        output_path = "/home/nculcwu/DeepSeek/ingredient_target_mapping_api.csv"
        fetcher.save_ingredient_target_mapping(df_ingredient_targets, output_path)
    else:
        print("⚠️ 未獲取到任何資料，可能需要調整 API 端點")


def method_2_web_scraping():
    """方法 2: 從 SymMap 網站爬取資料"""
    print("="*80)
    print("方法 2: 從 SymMap 網站爬取資料")
    print("="*80)

    print("此方法需要分析 SymMap 網站結構...")
    print("建議先訪問以下網址了解資料格式:")
    print("  - http://www.symmap.org/browse/")
    print("  - http://www.symmap.org/detail/ingredient/")

    # 範例：查詢單一成分
    mol_id = 2498  # Beta-Caryophyllene
    url = f"http://www.symmap.org/detail/ingredient/{mol_id}"
    print(f"\n範例網址: {url}")

    # 這裡需要實作爬蟲邏輯
    print("⚠️ 需要實作網頁爬蟲（BeautifulSoup/Selenium）")


def method_3_pubchem_bridge():
    """方法 3: 使用 PubChem 作為橋樑"""
    print("="*80)
    print("方法 3: 透過 PubChem CID 查詢靶點資料")
    print("="*80)

    # 載入現有的成分資料
    df_master = pd.read_csv("/home/nculcwu/DeepSeek/SymMap_Master_Table.csv")

    # 提取有 PubChem_CID 的成分
    df_with_pubchem = df_master[df_master['PubChem_CID'].notna()]
    print(f"有 PubChem_CID 的成分數量: {len(df_with_pubchem['Mol_id'].unique())}")

    # PubChem API 範例
    pubchem_cid = int(df_with_pubchem.iloc[0]['PubChem_CID'])
    print(f"\n範例 PubChem_CID: {pubchem_cid}")

    # PubChem BioAssay API
    pubchem_api = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{pubchem_cid}/assaysummary/JSON"
    print(f"PubChem API: {pubchem_api}")

    try:
        response = requests.get(pubchem_api, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("\n✅ PubChem API 可用！")
            print(f"資料範例: {json.dumps(data, indent=2)[:500]}...")
        else:
            print(f"⚠️ PubChem API 回應代碼: {response.status_code}")
    except Exception as e:
        print(f"❌ PubChem API 查詢失敗: {str(e)}")

    print("\n其他可用資源:")
    print("  - STITCH: http://stitch.embl.de/")
    print("  - ChEMBL: https://www.ebi.ac.uk/chembl/")
    print("  - DrugBank: https://go.drugbank.com/")


def method_4_local_analysis():
    """方法 4: 深入分析本地 SymMap 檔案"""
    print("="*80)
    print("方法 4: 深入分析本地 SymMap 檔案結構")
    print("="*80)

    symmap_path = "/home/nculcwu/DeepSeek/SymMap"

    # 載入所有表格
    df_smit = pd.read_excel(os.path.join(symmap_path, "SymMap v2.0, SMIT file.xlsx"))
    df_smit_key = pd.read_excel(os.path.join(symmap_path, "SymMap v2.0, SMIT key file.xlsx"))
    df_smtt = pd.read_excel(os.path.join(symmap_path, "SymMap v2.0, SMTT file.xlsx"))
    df_smhb = pd.read_excel(os.path.join(symmap_path, "SymMap v2.0, SMHB file.xlsx"))

    print("\n檢查可能的間接關聯路徑:")

    # 路徑 1: Herb → TCMSP_id → ??? → Target
    print("\n1. Herb.TCMSP_id 與 Target.TCMSP_id 比對")
    herb_tcmsp = set(df_smhb['TCMSP_id'].dropna())
    # Target TCMSP_id 可能是字串格式（如 'TAR00092'）
    target_tcmsp = set(df_smtt['TCMSP_id'].dropna())
    overlap = herb_tcmsp & target_tcmsp
    print(f"   Herb 中的 TCMSP_id 數量: {len(herb_tcmsp)}")
    print(f"   Herb TCMSP_id 範例: {list(herb_tcmsp)[:5]}")
    print(f"   Target 中的 TCMSP_id 數量: {len(target_tcmsp)}")
    print(f"   Target TCMSP_id 範例: {list(target_tcmsp)[:5]}")
    print(f"   重疊數量: {len(overlap)}")
    if len(overlap) > 0:
        print(f"   重疊範例: {list(overlap)[:5]}")

    # 路徑 2: 透過 HIT_id
    print("\n2. 檢查 Target.HIT_id")
    hit_ids = df_smtt['HIT_id'].dropna().unique()
    print(f"   HIT_id 數量: {len(hit_ids)}")
    print(f"   HIT_id 範例: {list(hit_ids[:5])}")

    # 路徑 3: 檢查 SMIT_key 中是否有隱藏資訊
    print("\n3. 檢查 SMIT key file 的 Field_name")
    field_names = df_smit_key['Field_name'].unique()
    print(f"   唯一 Field_name: {list(field_names)}")

    # 搜尋任何可能包含 Target/Gene 資訊的記錄
    for field in field_names:
        sample = df_smit_key[df_smit_key['Field_name'] == field].head(3)
        print(f"\n   {field} 範例:")
        for _, row in sample.iterrows():
            print(f"     Mol_id={row['Mol_id']}: {row['Field_context']}")


def main():
    """主程式"""
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                 SymMap Ingredient-Target 資料獲取工具                    ║
    ╚══════════════════════════════════════════════════════════════════════════╝

    確認問題：
    ✅ 本地 SymMap 檔案中 **確實缺少** Mol_id ↔ Gene_id 的直接關聯

    原因分析：
    - SMIT file (成分表) 沒有 Gene_id 欄位
    - SMTT file (靶點表) 沒有 Mol_id 欄位
    - SMIT key file 和 SMTT key file 也沒有交叉關聯

    解決方案（4 種方法）：
    """)

    print("\n請選擇獲取資料的方法:")
    print("  1. 使用 SymMap 官方 API（推薦）")
    print("  2. 從 SymMap 網站爬取資料")
    print("  3. 透過 PubChem CID 查詢靶點")
    print("  4. 深入分析本地檔案尋找隱藏關聯")
    print("  5. 執行所有方法進行測試")

    choice = input("\n請輸入選項 (1-5): ").strip()

    if choice == '1':
        method_1_symmap_api()
    elif choice == '2':
        method_2_web_scraping()
    elif choice == '3':
        method_3_pubchem_bridge()
    elif choice == '4':
        method_4_local_analysis()
    elif choice == '5':
        print("\n執行所有測試方法...\n")
        method_4_local_analysis()
        print("\n" + "="*80 + "\n")
        method_3_pubchem_bridge()
        print("\n" + "="*80 + "\n")
        print("⚠️ 方法 1 和 2 需要網路連線，請單獨執行")
    else:
        print("無效選項，執行方法 4（本地分析）")
        method_4_local_analysis()


if __name__ == "__main__":
    main()
