#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
從 herb_association_analysis_improved.xlsx 中的 Herb_id 追溯對應的靶點和疾病

使用方式:
    python lookup_herb_targets_diseases.py
"""

import pandas as pd
import os
from typing import List, Dict


class HerbTargetDiseaseMapper:
    """草藥-靶點-疾病對應查詢工具"""

    def __init__(self, symmap_path: str, analysis_result_path: str):
        self.symmap_path = symmap_path
        self.analysis_result_path = analysis_result_path

        # 載入資料
        print("載入 SymMap 資料庫...")
        self.df_herbs = pd.read_excel(
            os.path.join(symmap_path, "SymMap v2.0, SMHB file.xlsx")
        )
        print(f"  ✓ SMHB (草藥): {len(self.df_herbs)} 筆")

        self.df_it = pd.read_excel(
            os.path.join(symmap_path, "SymMap v2.0, SMIT file.xlsx")
        )
        print(f"  ✓ SMIT (成分-靶點): {len(self.df_it)} 筆")

        self.df_targets = pd.read_excel(
            os.path.join(symmap_path, "SymMap v2.0, SMTT file.xlsx")
        )
        print(f"  ✓ SMTT (靶點): {len(self.df_targets)} 筆")

        self.df_diseases = pd.read_excel(
            os.path.join(symmap_path, "SymMap v2.0, SMDE file.xlsx")
        )
        print(f"  ✓ SMDE (疾病): {len(self.df_diseases)} 筆")

        self.df_analysis = pd.read_excel(analysis_result_path)
        print(f"  ✓ 草藥關聯分析結果: {len(self.df_analysis)} 筆\n")

    def parse_herb_ids(self, herb_ids_str: str) -> List[int]:
        """解析 Herb_id 字串 (例如 '41, 359, 304, 338')"""
        if pd.isna(herb_ids_str) or herb_ids_str == '':
            return []

        return [int(x.strip()) for x in str(herb_ids_str).split(',')]

    def get_herb_info(self, herb_id: int) -> Dict:
        """查詢草藥基本資訊"""
        herb_row = self.df_herbs[self.df_herbs['Herb_id'] == herb_id]

        if len(herb_row) == 0:
            return None

        herb_row = herb_row.iloc[0]
        return {
            'Herb_id': herb_id,
            'Chinese_name': herb_row.get('Chinese_name', ''),
            'Pinyin_name': herb_row.get('Pinyin_name', ''),
            'English_name': herb_row.get('English_name', '')
        }

    def get_targets_for_herb(self, herb_id: int) -> pd.DataFrame:
        """
        查詢指定草藥的所有成分

        SymMap 資料結構:
        Herb_id → TCMSP_id (SMHB) → Link_ingredient_id (SMIT) → Mol_id

        注意: SMIT.Link_ingredient_id 對應到 SMHB.TCMSP_id
        """
        # 先從 SMHB 取得該草藥的 TCMSP_id
        herb_row = self.df_herbs[self.df_herbs['Herb_id'] == herb_id]

        if len(herb_row) == 0:
            return pd.DataFrame()

        tcmsp_id = herb_row.iloc[0].get('TCMSP_id')

        if pd.isna(tcmsp_id):
            return pd.DataFrame()

        # 在 SMIT 中找到 Link_ingredient_id = TCMSP_id 的成分
        ingredients = self.df_it[
            self.df_it['Link_ingredient_id'] == tcmsp_id
        ]

        if len(ingredients) == 0:
            return pd.DataFrame()

        # 返回成分資訊
        return ingredients[['Mol_id', 'Molecule_name', 'Molecule_formula']].drop_duplicates()

    def get_diseases_for_target(self, gene_id: int) -> pd.DataFrame:
        """查詢指定靶點關聯的疾病"""
        # 注意: SymMap 中 Target-Disease 的關聯可能在 key file 中
        # 這裡先實作基本查詢框架
        return pd.DataFrame()

    def create_detailed_report(self, output_path: str):
        """生成詳細的草藥-靶點-疾病對照表"""
        print("="*80)
        print("生成草藥-靶點-疾病對照表")
        print("="*80 + "\n")

        all_results = []

        for idx, row in self.df_analysis.iterrows():
            community = row['community']
            core_index = row['core_index']
            core_combo = row['core_combo']
            core_herb_ids_str = row['core_herb_ids']

            print(f"處理 Community {community} - Core {core_index}: {core_combo}")

            # 解析 Herb IDs
            core_herb_ids = self.parse_herb_ids(core_herb_ids_str)

            for herb_id in core_herb_ids:
                # 查詢草藥資訊
                herb_info = self.get_herb_info(herb_id)
                if not herb_info:
                    print(f"  ⚠ 找不到 Herb_id={herb_id} 的資訊")
                    continue

                print(f"  ✓ {herb_info['Chinese_name']} (Herb_id={herb_id})")

                # 查詢成分/靶點
                ingredients = self.get_targets_for_herb(herb_id)

                if len(ingredients) > 0:
                    print(f"    → 找到 {len(ingredients)} 個關聯成分")

                    for _, ing in ingredients.head(5).iterrows():
                        result = {
                            'Community': community,
                            'Core_Index': core_index,
                            'Core_Combo': core_combo,
                            'Herb_id': herb_id,
                            'Chinese_name': herb_info['Chinese_name'],
                            'Pinyin_name': herb_info['Pinyin_name'],
                            'English_name': herb_info['English_name'],
                            'Mol_id': ing['Mol_id'],
                            'Molecule_name': ing['Molecule_name'],
                            'Molecule_formula': ing.get('Molecule_formula', '')
                        }
                        all_results.append(result)
                else:
                    print(f"    → 未找到關聯成分")

                    # 仍然記錄草藥資訊
                    result = {
                        'Community': community,
                        'Core_Index': core_index,
                        'Core_Combo': core_combo,
                        'Herb_id': herb_id,
                        'Chinese_name': herb_info['Chinese_name'],
                        'Pinyin_name': herb_info['Pinyin_name'],
                        'English_name': herb_info['English_name'],
                        'Mol_id': None,
                        'Molecule_name': None,
                        'Molecule_formula': None
                    }
                    all_results.append(result)

            print()

        # 生成 DataFrame
        df_report = pd.DataFrame(all_results)

        # 儲存
        df_report.to_excel(output_path, index=False, engine='openpyxl')
        print(f"✓ 對照表已儲存至: {output_path}")
        print(f"  共 {len(df_report)} 筆記錄\n")

        return df_report

    def create_lookup_table(self):
        """建立快速查詢表 (Herb_id → 詳細資訊)"""
        print("建立 Herb_id 快速查詢表...")

        lookup_data = []

        # 從分析結果中取得所有 Herb_id
        all_herb_ids = set()

        for _, row in self.df_analysis.iterrows():
            core_ids = self.parse_herb_ids(row['core_herb_ids'])
            sub_ids = self.parse_herb_ids(row['sub_herb_ids'])
            all_herb_ids.update(core_ids)
            all_herb_ids.update(sub_ids)

        print(f"  找到 {len(all_herb_ids)} 個獨特的 Herb_id")

        for herb_id in sorted(all_herb_ids):
            herb_info = self.get_herb_info(herb_id)
            if not herb_info:
                continue

            ingredients = self.get_targets_for_herb(herb_id)

            sample_molecules = ''
            if len(ingredients) > 0 and 'Molecule_name' in ingredients.columns:
                sample_molecules = ', '.join(
                    ingredients['Molecule_name'].head(3).dropna().astype(str).tolist()
                )

            lookup_data.append({
                'Herb_id': herb_id,
                'Chinese_name': herb_info['Chinese_name'],
                'Pinyin_name': herb_info['Pinyin_name'],
                'English_name': herb_info['English_name'],
                'Ingredient_count': len(ingredients),
                'Sample_molecules': sample_molecules
            })

        df_lookup = pd.DataFrame(lookup_data)

        output_path = "/home/nculcwu/DeepSeek/herb_id_lookup_table.xlsx"
        df_lookup.to_excel(output_path, index=False, engine='openpyxl')
        print(f"✓ 查詢表已儲存至: {output_path}\n")

        return df_lookup


def main():
    symmap_path = "/home/nculcwu/DeepSeek/SymMap"
    analysis_result_path = "/home/nculcwu/DeepSeek/herb_association_analysis_improved.xlsx"

    mapper = HerbTargetDiseaseMapper(symmap_path, analysis_result_path)

    # 1. 建立快速查詢表
    print("\n【步驟 1】建立 Herb_id 快速查詢表")
    print("-"*80)
    df_lookup = mapper.create_lookup_table()
    print(f"查詢表範例 (前10筆):")
    print(df_lookup.head(10).to_string())

    # 2. 建立詳細對照表
    print("\n【步驟 2】建立詳細草藥-成分對照表")
    print("-"*80)
    output_detailed = "/home/nculcwu/DeepSeek/herb_ingredient_detailed_report.xlsx"
    df_detailed = mapper.create_detailed_report(output_detailed)

    print("\n" + "="*80)
    print("完成!")
    print("="*80)
    print("\n生成的檔案:")
    print("  1. herb_id_lookup_table.xlsx - Herb_id 快速查詢表")
    print("  2. herb_ingredient_detailed_report.xlsx - 詳細草藥-成分對照表")
    print("\n使用方式:")
    print("  - 從 herb_association_analysis_improved.xlsx 找到 Herb_id (如 41)")
    print("  - 在 herb_id_lookup_table.xlsx 中查詢對應的中文名稱和成分數量")
    print("  - 在 herb_ingredient_detailed_report.xlsx 中查看詳細的成分資訊")


if __name__ == "__main__":
    main()
