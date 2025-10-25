#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
透過 PubChem API 獲取 Ingredient-Target 關聯資料

解決 SymMap 本地檔案缺少 Mol_id → Gene_id 關聯的問題

作者：Claude Code
日期：2025-10-22
"""

import requests
import pandas as pd
import time
import json
import os
from typing import Dict, List, Optional
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')


class PubChemTargetFetcher:
    """PubChem 靶點資料獲取器"""

    def __init__(self, cache_dir: str = "/home/nculcwu/DeepSeek/PubChem_Cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        self.base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; AcademicResearch/1.0)'
        })

        print(f"PubChem Target Fetcher 初始化完成")
        print(f"快取目錄: {self.cache_dir}")

    def get_assay_summary(self, pubchem_cid: int, use_cache: bool = True) -> Optional[Dict]:
        """
        查詢 PubChem CID 對應的生物檢測摘要

        Args:
            pubchem_cid: PubChem Compound ID
            use_cache: 是否使用快取

        Returns:
            生物檢測摘要資料
        """
        # 檢查快取
        cache_file = os.path.join(self.cache_dir, f"cid_{pubchem_cid}_assay.json")
        if use_cache and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass

        # API 查詢
        url = f"{self.base_url}/compound/cid/{pubchem_cid}/assaysummary/JSON"

        try:
            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()

                # 儲存快取
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                return data
            elif response.status_code == 404:
                # 該化合物沒有生物檢測資料
                return None
            else:
                print(f"⚠️ PubChem CID {pubchem_cid} 查詢失敗: HTTP {response.status_code}")
                return None

        except requests.Timeout:
            print(f"⚠️ PubChem CID {pubchem_cid} 查詢超時")
            return None
        except Exception as e:
            print(f"⚠️ PubChem CID {pubchem_cid} 查詢錯誤: {str(e)}")
            return None

    def parse_assay_targets(self, assay_data: Dict) -> List[Dict]:
        """
        解析生物檢測資料，提取靶點資訊

        Args:
            assay_data: PubChem assay summary 資料

        Returns:
            靶點資訊列表
        """
        targets = []

        if not assay_data or 'Table' not in assay_data:
            return targets

        table = assay_data['Table']

        if 'Row' not in table:
            return targets

        rows = table['Row']
        if not isinstance(rows, list):
            rows = [rows]

        for row in rows:
            cells = row.get('Cell', [])

            # 根據 PubChem API 文件，Cell 的順序為:
            # AID, Panel Member ID, SID, CID, Activity Outcome, Target Accession,
            # Target GeneID, Activity Value [uM], Activity Name, Assay Name, Assay Type, PubMed ID, RNAi

            if len(cells) >= 13:
                target_info = {
                    'AID': cells[0],                    # Assay ID
                    'SID': cells[2],                    # Substance ID
                    'CID': cells[3],                    # Compound ID
                    'Activity_Outcome': cells[4],       # Active/Inactive
                    'Target_Accession': cells[5],       # UniProt/GenBank ID
                    'Target_GeneID': cells[6],          # NCBI Gene ID
                    'Activity_Value_uM': cells[7],      # IC50, EC50 等
                    'Activity_Name': cells[8],          # 活性名稱
                    'Assay_Name': cells[9],             # 檢測名稱
                    'Assay_Type': cells[10],            # 檢測類型
                    'PubMed_ID': cells[11],             # 文獻 ID
                }

                # 只保留有靶點資訊的記錄
                if target_info['Target_GeneID'] and target_info['Target_GeneID'] != '':
                    targets.append(target_info)

        return targets

    def batch_fetch_targets(
        self,
        mol_id_to_pubchem: Dict[int, int],
        delay: float = 0.3,
        max_per_compound: int = 10
    ) -> pd.DataFrame:
        """
        批次查詢多個化合物的靶點資料

        Args:
            mol_id_to_pubchem: {Mol_id: PubChem_CID} 映射字典
            delay: 每次請求之間的延遲（秒）
            max_per_compound: 每個化合物最多保留的靶點數量

        Returns:
            Ingredient-Target 對應表 DataFrame
        """
        results = []

        print(f"開始批次查詢 {len(mol_id_to_pubchem)} 個化合物的靶點資料...")
        print("注意：PubChem API 有速率限制，查詢可能需要較長時間\n")

        for mol_id, pubchem_cid in tqdm(mol_id_to_pubchem.items(), desc="查詢進度"):
            try:
                # 查詢生物檢測資料
                assay_data = self.get_assay_summary(int(pubchem_cid))

                if assay_data:
                    # 解析靶點
                    targets = self.parse_assay_targets(assay_data)

                    # 限制每個化合物的靶點數量（只保留活性最高的）
                    if len(targets) > max_per_compound:
                        # 優先保留 Active 的結果
                        active_targets = [t for t in targets if t['Activity_Outcome'] == 'Active']
                        if len(active_targets) >= max_per_compound:
                            targets = active_targets[:max_per_compound]
                        else:
                            targets = active_targets + targets[:max_per_compound - len(active_targets)]

                    # 添加 Mol_id
                    for target in targets:
                        target['Mol_id'] = mol_id
                        results.append(target)

                # 延遲以避免超過速率限制
                time.sleep(delay)

            except Exception as e:
                print(f"\n錯誤 (Mol_id={mol_id}, PubChem_CID={pubchem_cid}): {str(e)}")
                continue

        df_results = pd.DataFrame(results)
        return df_results

    def map_geneid_to_symmap(self, df_targets: pd.DataFrame, df_symmap_targets: pd.DataFrame) -> pd.DataFrame:
        """
        將 PubChem 的 Gene_id 映射到 SymMap 的 Gene_id

        Args:
            df_targets: PubChem 靶點資料
            df_symmap_targets: SymMap SMTT 資料

        Returns:
            包含 SymMap Gene_id 的 DataFrame
        """
        print("\n映射 PubChem Gene_id 到 SymMap Gene_id...")

        # SymMap 的 Gene_id 映射（透過 NCBI_id）
        ncbi_to_symmap = {}
        for _, row in df_symmap_targets.iterrows():
            if pd.notna(row['NCBI_id']):
                # NCBI_id 可能是字串格式
                ncbi_id = str(row['NCBI_id']).strip()
                ncbi_to_symmap[ncbi_id] = {
                    'Gene_id': row['Gene_id'],
                    'Gene_symbol': row['Gene_symbol'],
                    'Gene_name': row['Gene_name']
                }

        # 映射
        mapped_results = []
        for _, row in df_targets.iterrows():
            ncbi_id = str(row['Target_GeneID']).strip()

            if ncbi_id in ncbi_to_symmap:
                mapped_row = row.to_dict()
                mapped_row['SymMap_Gene_id'] = ncbi_to_symmap[ncbi_id]['Gene_id']
                mapped_row['SymMap_Gene_symbol'] = ncbi_to_symmap[ncbi_id]['Gene_symbol']
                mapped_row['SymMap_Gene_name'] = ncbi_to_symmap[ncbi_id]['Gene_name']
                mapped_results.append(mapped_row)

        df_mapped = pd.DataFrame(mapped_results)

        print(f"映射成功: {len(df_mapped)}/{len(df_targets)} 個靶點")
        return df_mapped


def main():
    """主程式"""
    print("="*80)
    print("透過 PubChem API 獲取 Ingredient-Target 關聯資料")
    print("="*80)

    # 載入 SymMap 資料
    print("\n步驟 1: 載入 SymMap 資料")
    df_master = pd.read_csv("/home/nculcwu/DeepSeek/SymMap_Master_Table.csv")
    df_smtt = pd.read_excel("/home/nculcwu/DeepSeek/SymMap/SymMap v2.0, SMTT file.xlsx")

    # 提取有 PubChem_CID 的成分
    df_with_pubchem = df_master[df_master['PubChem_CID'].notna()][
        ['Mol_id', 'Molecule_name', 'PubChem_CID']
    ].drop_duplicates()

    print(f"✓ 有 PubChem_CID 的成分數量: {len(df_with_pubchem)}")

    # 建立 Mol_id → PubChem_CID 映射
    mol_to_pubchem = {}
    for _, row in df_with_pubchem.iterrows():
        mol_id = int(row['Mol_id'])
        pubchem_cid_str = str(row['PubChem_CID'])

        # 處理多個 PubChem_CID 的情況（用 | 分隔）
        if '|' in pubchem_cid_str:
            # 只使用第一個 CID
            pubchem_cid = int(pubchem_cid_str.split('|')[0].strip())
        else:
            pubchem_cid = int(float(pubchem_cid_str))

        mol_to_pubchem[mol_id] = pubchem_cid

    # 建立查詢器
    print("\n步驟 2: 初始化 PubChem 查詢器")
    fetcher = PubChemTargetFetcher()

    # 詢問使用者要查詢多少個成分
    print(f"\n總共有 {len(mol_to_pubchem)} 個成分可查詢")
    print("建議先測試少量成分（如 10 個）確認 API 正常運作")

    try:
        num_to_fetch = input(f"請輸入要查詢的成分數量 (1-{len(mol_to_pubchem)}，Enter=全部): ").strip()
        if num_to_fetch == '':
            num_to_fetch = len(mol_to_pubchem)
        else:
            num_to_fetch = int(num_to_fetch)
            num_to_fetch = min(num_to_fetch, len(mol_to_pubchem))
    except:
        num_to_fetch = 10
        print(f"輸入錯誤，預設查詢 {num_to_fetch} 個")

    # 選取要查詢的成分
    mol_ids_to_fetch = list(mol_to_pubchem.keys())[:num_to_fetch]
    fetch_dict = {mol_id: mol_to_pubchem[mol_id] for mol_id in mol_ids_to_fetch}

    # 批次查詢
    print(f"\n步驟 3: 批次查詢 {num_to_fetch} 個成分的靶點資料")
    df_targets = fetcher.batch_fetch_targets(fetch_dict, delay=0.5, max_per_compound=10)

    print(f"\n查詢結果:")
    print(f"  總共獲得 {len(df_targets)} 筆 Ingredient-Target 關聯")
    print(f"  涉及成分數: {df_targets['Mol_id'].nunique() if len(df_targets) > 0 else 0}")
    print(f"  涉及靶點數: {df_targets['Target_GeneID'].nunique() if len(df_targets) > 0 else 0}")

    if len(df_targets) > 0:
        # 映射到 SymMap Gene_id
        print("\n步驟 4: 映射 NCBI Gene_id 到 SymMap Gene_id")
        df_mapped = fetcher.map_geneid_to_symmap(df_targets, df_smtt)

        print(f"\n映射結果:")
        print(f"  成功映射的關聯數: {len(df_mapped)}")
        print(f"  涉及 SymMap Gene 數: {df_mapped['SymMap_Gene_id'].nunique() if len(df_mapped) > 0 else 0}")

        # 儲存結果
        print("\n步驟 5: 儲存結果")

        # 原始 PubChem 資料
        output_raw = "/home/nculcwu/DeepSeek/ingredient_target_pubchem_raw.csv"
        df_targets.to_csv(output_raw, index=False, encoding='utf-8-sig')
        print(f"✓ 原始資料: {output_raw}")

        if len(df_mapped) > 0:
            # 映射後的資料
            output_mapped = "/home/nculcwu/DeepSeek/ingredient_target_mapping_final.csv"
            df_mapped.to_csv(output_mapped, index=False, encoding='utf-8-sig')

            # Excel 格式
            output_excel = "/home/nculcwu/DeepSeek/ingredient_target_mapping_final.xlsx"
            df_mapped.to_excel(output_excel, index=False, engine='openpyxl')

            print(f"✓ 最終對應表 (CSV): {output_mapped}")
            print(f"✓ 最終對應表 (Excel): {output_excel}")

            # 顯示範例
            print("\n【對應表範例】")
            print(df_mapped.head(10)[['Mol_id', 'Activity_Outcome', 'SymMap_Gene_id', 'SymMap_Gene_symbol', 'Assay_Name']])

            # 統計報告
            print("\n【統計報告】")
            print(f"成分-靶點關聯總數: {len(df_mapped)}")
            print(f"涉及成分數: {df_mapped['Mol_id'].nunique()}")
            print(f"涉及 SymMap 靶點數: {df_mapped['SymMap_Gene_id'].nunique()}")

            # Top 10 成分（靶點最多）
            top_mols = df_mapped['Mol_id'].value_counts().head(10)
            print("\n靶點數量最多的成分 Top 10:")
            for mol_id, count in top_mols.items():
                mol_name = df_master[df_master['Mol_id'] == mol_id]['Molecule_name'].iloc[0]
                print(f"  Mol_id={mol_id} ({mol_name}): {count} 個靶點")

            # Top 10 靶點（成分最多）
            top_genes = df_mapped['SymMap_Gene_symbol'].value_counts().head(10)
            print("\n被最多成分作用的靶點 Top 10:")
            for gene_symbol, count in top_genes.items():
                print(f"  {gene_symbol}: {count} 個成分")

        else:
            print("⚠️ 沒有成功映射到 SymMap Gene_id，可能是 NCBI_id 格式不匹配")
            print("   請檢查 SymMap SMTT file 的 NCBI_id 欄位格式")

    else:
        print("\n⚠️ 未獲取到任何靶點資料")
        print("可能原因:")
        print("  1. 這些化合物在 PubChem 沒有生物檢測資料")
        print("  2. API 速率限制")
        print("  3. 網路連線問題")

    print("\n" + "="*80)
    print("程式執行完成！")
    print("="*80)


if __name__ == "__main__":
    main()
