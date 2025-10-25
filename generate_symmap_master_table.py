#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SymMap 資料庫整合大表生成器

將 SymMap 的多個表格整合成一個完整的關聯大表，包含：
- Herb (草藥)
- Ingredient (成分/分子)
- Target (靶點/基因) - 需另外資料源
- Disease (疾病) - 需另外資料源
- Symptoms (症狀)
- Syndrome (證型)
"""

import pandas as pd
import os
import warnings
from typing import Dict, List
warnings.filterwarnings('ignore')


class SymMapIntegrator:
    """SymMap 資料庫整合器"""

    def __init__(self, symmap_path: str):
        self.symmap_path = symmap_path
        self.tables = {}

        print("="*80)
        print("SymMap 資料庫整合大表生成器")
        print("="*80 + "\n")

        self.load_all_tables()

    def load_all_tables(self):
        """載入所有 SymMap 表格"""
        print("載入 SymMap 資料庫...")

        table_files = {
            'herbs': 'SymMap v2.0, SMHB file.xlsx',
            'herbs_key': 'SymMap v2.0, SMHB key file.xlsx',
            'ingredients': 'SymMap v2.0, SMIT file.xlsx',
            'ingredients_key': 'SymMap v2.0, SMIT key file.xlsx',
            'targets': 'SymMap v2.0, SMTT file.xlsx',
            'targets_key': 'SymMap v2.0, SMTT key file.xlsx',
            'diseases': 'SymMap v2.0, SMDE file.xlsx',
            'diseases_key': 'SymMap v2.0, SMDE key file.xlsx',
            'mm_symptoms': 'SymMap v2.0, SMMS file.xlsx',
            'tcm_symptoms': 'SymMap v2.0, SMTS file.xlsx',
            'syndromes': 'SymMap v2.0, SMSY file.xlsx',
        }

        for table_name, filename in table_files.items():
            filepath = os.path.join(self.symmap_path, filename)
            if os.path.exists(filepath):
                self.tables[table_name] = pd.read_excel(filepath)
                print(f"  ✓ {table_name}: {len(self.tables[table_name]):,} 筆")
            else:
                print(f"  ✗ {table_name}: 檔案不存在")

        print()

    def build_herb_ingredient_master(self) -> pd.DataFrame:
        """
        建立 Herb-Ingredient 主表

        關聯方式: Herb.TCMSP_id = Ingredient.Link_ingredient_id
        """
        print("【步驟 1】建立 Herb-Ingredient 關聯表")
        print("-"*80)

        df_herbs = self.tables['herbs'].copy()
        df_ingredients = self.tables['ingredients'].copy()

        # 準備 Herb 資料
        herb_cols = [
            'Herb_id', 'Chinese_name', 'Pinyin_name', 'Latin_name', 'English_name',
            'Properties_Chinese', 'Properties_English',
            'Meridians_Chinese', 'Meridians_English',
            'Class_Chinese', 'Class_English',
            'TCMSP_id'
        ]
        df_herbs_clean = df_herbs[herb_cols].copy()
        df_herbs_clean = df_herbs_clean.rename(columns={
            'Chinese_name': 'Herb_Chinese',
            'Pinyin_name': 'Herb_Pinyin',
            'Latin_name': 'Herb_Latin',
            'English_name': 'Herb_English',
        })

        # 準備 Ingredient 資料 - 只保留有 Link_ingredient_id 的成分
        ingredient_cols = [
            'Mol_id', 'Molecule_name', 'Molecule_formula', 'Molecule_weight',
            'PubChem_CID', 'CAS_id', 'OB_score', 'Type', 'Link_ingredient_id'
        ]
        df_ingredients_clean = df_ingredients[ingredient_cols].copy()
        # 關鍵：過濾掉 Link_ingredient_id 為 NaN 的記錄
        df_ingredients_clean = df_ingredients_clean[df_ingredients_clean['Link_ingredient_id'].notna()]

        # 先執行 INNER JOIN 取得有成分的草藥
        df_with_ingredients = pd.merge(
            df_herbs_clean,
            df_ingredients_clean,
            left_on='TCMSP_id',
            right_on='Link_ingredient_id',
            how='inner'
        )

        # 找出沒有成分的草藥
        herbs_with_data = df_with_ingredients['Herb_id'].unique()
        df_without_ingredients = df_herbs_clean[~df_herbs_clean['Herb_id'].isin(herbs_with_data)].copy()

        # 合併
        df_master = pd.concat([df_with_ingredients, df_without_ingredients], ignore_index=True)

        print(f"  總 Herb 數量: {df_herbs_clean['Herb_id'].nunique():,}")
        print(f"  有成分的 Herb: {df_master[df_master['Mol_id'].notna()]['Herb_id'].nunique():,}")
        print(f"  總成分記錄數: {df_master[df_master['Mol_id'].notna()].shape[0]:,}")
        print()

        return df_master

    def add_herb_aliases(self, df_master: pd.DataFrame) -> pd.DataFrame:
        """添加草藥別名"""
        print("【步驟 2】添加草藥別名資訊")
        print("-"*80)

        df_herb_key = self.tables['herbs_key'].copy()

        # 提取別名 (多個別名合併成一個字串)
        alias_records = df_herb_key[df_herb_key['Field_name'] == 'Chinese_name']
        alias_dict = {}
        for herb_id, group in alias_records.groupby('Herb_id'):
            aliases = group['Field_context'].tolist()
            alias_dict[herb_id] = '; '.join(aliases)

        df_master['Herb_Aliases'] = df_master['Herb_id'].map(alias_dict)

        print(f"  添加了 {len(alias_dict):,} 個草藥的別名資訊")
        print()

        return df_master

    def add_ingredient_aliases(self, df_master: pd.DataFrame) -> pd.DataFrame:
        """添加成分別名"""
        print("【步驟 3】添加成分別名資訊")
        print("-"*80)

        df_ingredient_key = self.tables['ingredients_key'].copy()

        # 提取別名 (限制每個成分最多5個別名，避免過長)
        alias_records = df_ingredient_key[df_ingredient_key['Field_name'] == 'Alias']
        alias_dict = {}
        for mol_id, group in alias_records.groupby('Mol_id'):
            aliases = group['Field_context'].head(5).dropna().astype(str).tolist()
            alias_dict[mol_id] = '; '.join(aliases)

        df_master['Molecule_Aliases'] = df_master['Mol_id'].map(alias_dict)

        print(f"  添加了 {len(alias_dict):,} 個成分的別名資訊")
        print()

        return df_master

    def add_disease_info(self, df_master: pd.DataFrame) -> pd.DataFrame:
        """
        添加疾病資訊（基於現有資料的統計）

        注意: SymMap 中沒有直接的 Herb-Disease 或 Ingredient-Disease 關聯表
        這裡我們只添加疾病表的基本資訊作為參考
        """
        print("【步驟 4】準備疾病資訊表（獨立）")
        print("-"*80)

        df_diseases = self.tables['diseases'].copy()

        disease_info = f"SymMap 包含 {len(df_diseases):,} 種疾病資料"
        print(f"  {disease_info}")
        print(f"  注意: 當前版本無法建立 Ingredient-Disease 直接關聯")
        print(f"  建議: 使用外部資料庫 (DisGeNET, CTD) 進行關聯\n")

        # 將疾病表儲存為獨立檔案
        return df_master

    def add_symptoms_info(self, df_master: pd.DataFrame) -> pd.DataFrame:
        """添加症狀資訊統計"""
        print("【步驟 5】準備症狀資訊表（獨立）")
        print("-"*80)

        df_mm_symptoms = self.tables['mm_symptoms']
        df_tcm_symptoms = self.tables['tcm_symptoms']

        print(f"  現代醫學症狀: {len(df_mm_symptoms):,} 種")
        print(f"  中醫症狀: {len(df_tcm_symptoms):,} 種")
        print(f"  注意: 當前版本無法建立 Herb-Symptom 直接關聯\n")

        return df_master

    def generate_statistics(self, df_master: pd.DataFrame):
        """生成統計資訊"""
        print("="*80)
        print("資料統計摘要")
        print("="*80 + "\n")

        total_herbs = df_master['Herb_id'].nunique()
        herbs_with_ingredients = df_master[df_master['Mol_id'].notna()]['Herb_id'].nunique()
        total_ingredients = df_master['Mol_id'].nunique()
        total_records = len(df_master)

        print(f"草藥統計:")
        print(f"  總草藥數量: {total_herbs:,}")
        print(f"  有成分資料的草藥: {herbs_with_ingredients:,} ({herbs_with_ingredients/total_herbs*100:.1f}%)")
        print(f"  無成分資料的草藥: {total_herbs - herbs_with_ingredients:,}")
        print()

        print(f"成分統計:")
        print(f"  總成分數量: {total_ingredients:,}")
        print(f"  平均每草藥的成分數: {df_master[df_master['Mol_id'].notna()].groupby('Herb_id').size().mean():.1f}")
        print()

        print(f"整合表統計:")
        print(f"  總記錄數: {total_records:,}")
        print(f"  含成分的記錄: {df_master['Mol_id'].notna().sum():,}")
        print(f"  僅草藥資訊的記錄: {df_master['Mol_id'].isna().sum():,}")
        print()

        # 藥性統計
        if 'Properties_Chinese' in df_master.columns:
            print("藥性分布 (Top 10):")
            props = df_master[df_master['Properties_Chinese'].notna()]['Properties_Chinese'].value_counts().head(10)
            for prop, count in props.items():
                print(f"  {prop}: {count:,}")
            print()

        # 成分類型統計
        if 'Type' in df_master.columns:
            print("成分類型分布:")
            types = df_master[df_master['Type'].notna()]['Type'].value_counts().head(10)
            for typ, count in types.items():
                print(f"  {typ}: {count:,}")
            print()

    def generate_master_table(self):
        """生成完整的整合大表"""
        # 建立基礎關聯
        df_master = self.build_herb_ingredient_master()

        # 添加額外資訊
        df_master = self.add_herb_aliases(df_master)
        df_master = self.add_ingredient_aliases(df_master)
        df_master = self.add_disease_info(df_master)
        df_master = self.add_symptoms_info(df_master)

        # 生成統計
        self.generate_statistics(df_master)

        return df_master

    def save_master_table(self, df_master: pd.DataFrame, output_path: str):
        """儲存整合大表"""
        print("="*80)
        print("儲存整合大表")
        print("="*80 + "\n")

        # 儲存主表
        df_master.to_excel(output_path, index=False, engine='openpyxl')
        print(f"✓ 主表已儲存: {output_path}")
        print(f"  檔案大小: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")

        # 也儲存 CSV 格式 (更小，更快)
        csv_path = output_path.replace('.xlsx', '.csv')
        df_master.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"✓ CSV 格式已儲存: {csv_path}")
        print(f"  檔案大小: {os.path.getsize(csv_path) / 1024 / 1024:.2f} MB")
        print()

    def save_reference_tables(self):
        """儲存參考表 (疾病、症狀、靶點等獨立表格)"""
        print("儲存參考資料表...")

        reference_dir = "/home/nculcwu/DeepSeek/SymMap_Reference_Tables"
        os.makedirs(reference_dir, exist_ok=True)

        # 疾病表
        if 'diseases' in self.tables:
            diseases_path = os.path.join(reference_dir, "diseases_reference.xlsx")
            self.tables['diseases'].to_excel(diseases_path, index=False, engine='openpyxl')
            print(f"  ✓ 疾病表: {diseases_path}")

        # 靶點表
        if 'targets' in self.tables:
            targets_path = os.path.join(reference_dir, "targets_reference.xlsx")
            self.tables['targets'].to_excel(targets_path, index=False, engine='openpyxl')
            print(f"  ✓ 靶點表: {targets_path}")

        # 現代醫學症狀
        if 'mm_symptoms' in self.tables:
            mm_path = os.path.join(reference_dir, "modern_symptoms_reference.xlsx")
            self.tables['mm_symptoms'].to_excel(mm_path, index=False, engine='openpyxl')
            print(f"  ✓ 現代症狀表: {mm_path}")

        # 中醫症狀
        if 'tcm_symptoms' in self.tables:
            tcm_path = os.path.join(reference_dir, "tcm_symptoms_reference.xlsx")
            self.tables['tcm_symptoms'].to_excel(tcm_path, index=False, engine='openpyxl')
            print(f"  ✓ 中醫症狀表: {tcm_path}")

        # 證型
        if 'syndromes' in self.tables:
            syn_path = os.path.join(reference_dir, "syndromes_reference.xlsx")
            self.tables['syndromes'].to_excel(syn_path, index=False, engine='openpyxl')
            print(f"  ✓ 證型表: {syn_path}")

        print()


def main():
    """主程式"""
    symmap_path = "/home/nculcwu/DeepSeek/SymMap"
    output_path = "/home/nculcwu/DeepSeek/SymMap_Master_Table.xlsx"

    # 建立整合器
    integrator = SymMapIntegrator(symmap_path)

    # 生成整合大表
    df_master = integrator.generate_master_table()

    # 儲存結果
    integrator.save_master_table(df_master, output_path)

    # 儲存參考表
    integrator.save_reference_tables()

    print("="*80)
    print("完成！")
    print("="*80)
    print("\n生成的檔案:")
    print("  1. SymMap_Master_Table.xlsx - 草藥-成分整合大表 (Excel)")
    print("  2. SymMap_Master_Table.csv - 草藥-成分整合大表 (CSV)")
    print("  3. SymMap_Reference_Tables/ - 參考資料表目錄")
    print("     - diseases_reference.xlsx (14,434 種疾病)")
    print("     - targets_reference.xlsx (20,965 個靶點)")
    print("     - modern_symptoms_reference.xlsx (1,148 種現代症狀)")
    print("     - tcm_symptoms_reference.xlsx (2,364 種中醫症狀)")
    print("     - syndromes_reference.xlsx (233 種證型)")
    print()
    print("使用說明:")
    print("  - 主表包含 Herb_id → Mol_id 的完整關聯")
    print("  - 每筆記錄代表一個草藥-成分配對")
    print("  - 無成分的草藥也會保留 (Mol_id 為空)")
    print("  - 參考表可用於進一步的關聯分析")


if __name__ == "__main__":
    main()
