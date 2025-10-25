#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
將 PubChem 查詢的靶點資料映射到 SymMap Gene_id

透過 NCBI API 將 NCBI Gene_ID 轉換成 Gene_symbol，
再與 SymMap SMTT 的 Gene_symbol 進行匹配

作者：Claude Code
日期：2025-10-22
"""

import pandas as pd
import requests
import time
import json
import os
from tqdm import tqdm


class GeneSymbolMapper:
    """NCBI Gene_ID → Gene_symbol 映射器"""

    def __init__(self, cache_dir="/home/nculcwu/DeepSeek/NCBI_Gene_Cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        self.session = requests.Session()

    def get_gene_symbol(self, ncbi_gene_id: int, use_cache: bool = True) -> dict:
        """查詢 NCBI Gene_ID 對應的 Gene_symbol"""

        # 檢查快取
        cache_file = os.path.join(self.cache_dir, f"gene_{ncbi_gene_id}.json")
        if use_cache and os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                return json.load(f)

        # API 查詢
        params = {
            'db': 'gene',
            'id': ncbi_gene_id,
            'retmode': 'json'
        }

        try:
            response = self.session.get(self.base_url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if 'result' in data and str(ncbi_gene_id) in data['result']:
                    gene_info = data['result'][str(ncbi_gene_id)]

                    result = {
                        'NCBI_Gene_ID': ncbi_gene_id,
                        'Gene_symbol': gene_info.get('name', ''),
                        'Gene_description': gene_info.get('description', ''),
                        'Organism': gene_info.get('organism', {}).get('scientificname', '')
                    }

                    # 儲存快取
                    with open(cache_file, 'w') as f:
                        json.dump(result, f, indent=2)

                    return result

        except Exception as e:
            print(f"⚠️ Gene_ID {ncbi_gene_id} 查詢失敗: {str(e)}")

        return None

    def batch_fetch_symbols(self, gene_ids: list, delay: float = 0.34) -> dict:
        """
        批次查詢多個 Gene_ID 的 symbol

        Args:
            gene_ids: NCBI Gene_ID 列表
            delay: 延遲（NCBI E-utilities 限制每秒3個請求）

        Returns:
            {NCBI_Gene_ID: Gene_symbol} 映射字典
        """
        print(f"批次查詢 {len(gene_ids)} 個 NCBI Gene_ID...")

        gene_id_to_symbol = {}

        for gene_id in tqdm(gene_ids, desc="NCBI API 查詢"):
            gene_info = self.get_gene_symbol(gene_id)

            if gene_info and gene_info['Gene_symbol']:
                gene_id_to_symbol[gene_id] = gene_info['Gene_symbol']

            time.sleep(delay)  # NCBI 限制每秒3個請求

        return gene_id_to_symbol


def main():
    """主程式"""
    print("="*80)
    print("將 PubChem 靶點資料映射到 SymMap Gene_id")
    print("="*80)

    # 載入 PubChem 查詢結果
    pubchem_file = "/home/nculcwu/DeepSeek/ingredient_target_pubchem_raw.csv"
    if not os.path.exists(pubchem_file):
        print(f"❌ 找不到檔案: {pubchem_file}")
        print("請先執行 fetch_ingredient_targets_pubchem.py")
        return

    df_pubchem = pd.read_csv(pubchem_file)
    print(f"\n步驟 1: 載入 PubChem 資料")
    print(f"✓ 記錄數: {len(df_pubchem)}")
    print(f"✓ 唯一 Gene_ID 數量: {df_pubchem['Target_GeneID'].nunique()}")

    # 載入 SymMap SMTT
    df_smtt = pd.read_excel("/home/nculcwu/DeepSeek/SymMap/SymMap v2.0, SMTT file.xlsx")
    print(f"\n步驟 2: 載入 SymMap SMTT")
    print(f"✓ SymMap 靶點數量: {len(df_smtt)}")

    # 建立 SymMap Gene_symbol → Gene_id 映射
    symmap_symbol_to_id = {}
    for _, row in df_smtt.iterrows():
        symbol = str(row['Gene_symbol']).strip().upper()
        symmap_symbol_to_id[symbol] = {
            'Gene_id': row['Gene_id'],
            'Gene_name': row['Gene_name'],
            'Protein_name': row['Protein_name']
        }

    print(f"✓ SymMap Gene_symbol 數量: {len(symmap_symbol_to_id)}")

    # 提取唯一的 NCBI Gene_ID
    unique_gene_ids = df_pubchem['Target_GeneID'].dropna().unique().tolist()

    # 批次查詢 Gene_symbol
    print(f"\n步驟 3: 透過 NCBI API 查詢 Gene_symbol")
    mapper = GeneSymbolMapper()
    gene_id_to_symbol = mapper.batch_fetch_symbols(unique_gene_ids)

    print(f"\n✓ 成功查詢: {len(gene_id_to_symbol)}/{len(unique_gene_ids)} 個 Gene_symbol")

    # 映射到 SymMap
    print(f"\n步驟 4: 映射到 SymMap Gene_id")
    mapped_records = []

    for _, row in df_pubchem.iterrows():
        ncbi_gene_id = row['Target_GeneID']

        # 取得 Gene_symbol
        if ncbi_gene_id in gene_id_to_symbol:
            gene_symbol = gene_id_to_symbol[ncbi_gene_id].upper()

            # 映射到 SymMap
            if gene_symbol in symmap_symbol_to_id:
                symmap_info = symmap_symbol_to_id[gene_symbol]

                mapped_record = row.to_dict()
                mapped_record['NCBI_Gene_symbol'] = gene_symbol
                mapped_record['SymMap_Gene_id'] = symmap_info['Gene_id']
                mapped_record['SymMap_Gene_name'] = symmap_info['Gene_name']
                mapped_record['SymMap_Protein_name'] = symmap_info['Protein_name']

                mapped_records.append(mapped_record)

    df_mapped = pd.DataFrame(mapped_records)

    print(f"\n映射結果:")
    print(f"  ✓ 成功映射: {len(df_mapped)}/{len(df_pubchem)} 筆記錄 ({len(df_mapped)/len(df_pubchem)*100:.1f}%)")
    print(f"  ✓ 涉及成分數: {df_mapped['Mol_id'].nunique() if len(df_mapped) > 0 else 0}")
    print(f"  ✓ 涉及 SymMap 靶點數: {df_mapped['SymMap_Gene_id'].nunique() if len(df_mapped) > 0 else 0}")

    if len(df_mapped) > 0:
        # 儲存結果
        print(f"\n步驟 5: 儲存結果")

        output_csv = "/home/nculcwu/DeepSeek/ingredient_target_mapping_final.csv"
        output_excel = "/home/nculcwu/DeepSeek/ingredient_target_mapping_final.xlsx"

        df_mapped.to_csv(output_csv, index=False, encoding='utf-8-sig')
        df_mapped.to_excel(output_excel, index=False, engine='openpyxl')

        print(f"✓ CSV: {output_csv}")
        print(f"✓ Excel: {output_excel}")

        # 顯示範例
        print(f"\n【對應表範例】")
        display_cols = ['Mol_id', 'NCBI_Gene_symbol', 'SymMap_Gene_id', 'Activity_Outcome', 'Activity_Value_uM']
        print(df_mapped[display_cols].head(15))

        # 統計報告
        print(f"\n【統計報告】")
        print(f"成分-靶點關聯總數: {len(df_mapped)}")
        print(f"涉及成分數: {df_mapped['Mol_id'].nunique()}")
        print(f"涉及 SymMap 靶點數: {df_mapped['SymMap_Gene_id'].nunique()}")

        # 載入 Master Table 取得成分名稱
        df_master = pd.read_csv("/home/nculcwu/DeepSeek/SymMap_Master_Table.csv")

        # Top 10 成分
        top_mols = df_mapped['Mol_id'].value_counts().head(10)
        print(f"\n靶點數量最多的成分 Top 10:")
        for mol_id, count in top_mols.items():
            mol_info = df_master[df_master['Mol_id'] == mol_id]
            if len(mol_info) > 0:
                mol_name = mol_info.iloc[0]['Molecule_name']
                print(f"  Mol_id={mol_id} ({mol_name}): {count} 個靶點")
            else:
                print(f"  Mol_id={mol_id}: {count} 個靶點")

        # Top 10 靶點
        top_genes = df_mapped['NCBI_Gene_symbol'].value_counts().head(10)
        print(f"\n被最多成分作用的靶點 Top 10:")
        for gene_symbol, count in top_genes.items():
            print(f"  {gene_symbol}: {count} 個成分")

        # 只保留 Active 的關聯
        df_active = df_mapped[df_mapped['Activity_Outcome'] == 'Active']
        if len(df_active) > 0:
            output_active = "/home/nculcwu/DeepSeek/ingredient_target_mapping_active_only.csv"
            df_active.to_csv(output_active, index=False, encoding='utf-8-sig')
            print(f"\n✓ 僅 Active 的關聯 ({len(df_active)} 筆): {output_active}")

    else:
        print(f"\n❌ 映射失敗，可能原因:")
        print(f"  1. NCBI API 查詢失敗")
        print(f"  2. Gene_symbol 不匹配")
        print(f"  3. SymMap 資料庫未收錄這些靶點")

    print(f"\n" + "="*80)
    print(f"映射完成！")
    print(f"="*80)


if __name__ == "__main__":
    main()
