#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
草藥關聯性驗證分析

此腳本整合 SymMap 資料庫與 core_index_all.csv，
透過草藥名稱對應來驗證核心草藥組合與配伍草藥的關聯性證據。

SymMap 資料庫結構:
- SMHB: 草藥基本資訊 (Herb_id, Chinese_name, ...)
- SMIT: 成分資訊 (Mol_id, Molecule_name, ...)
- SMTT: 標靶基因/蛋白質資訊 (Gene_id, Gene_symbol, ...)
- SMDE: 疾病資訊 (Disease_id, Disease_Name, ...)

串連邏輯:
1. core_index_all.csv 中的草藥名稱 -> SymMap SMHB (透過 Chinese_name)
2. SMHB (Herb_id) -> 需要額外的 Herb-Ingredient 關聯表
3. Ingredient (Mol_id) -> Target (Gene_id) 透過 SMIT 相關資料
4. 分析共同靶點來驗證草藥配伍的合理性
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, List, Set, Tuple
import re


class HerbAssociationAnalyzer:
    """草藥關聯性分析器"""

    def __init__(self, symmap_path: str, core_index_path: str):
        """
        初始化分析器

        Args:
            symmap_path: SymMap 資料庫資料夾路徑
            core_index_path: core_index_all.csv 檔案路徑
        """
        self.symmap_path = symmap_path
        self.core_index_path = core_index_path

        # 載入資料
        self.df_herbs = None
        self.df_herbs_key = None
        self.df_core_index = None

        self.load_data()

    def load_data(self):
        """載入所有需要的資料檔案"""
        print("載入資料...")

        # 載入 SymMap 草藥資料
        self.df_herbs = pd.read_excel(
            os.path.join(self.symmap_path, "SymMap v2.0, SMHB file.xlsx")
        )
        print(f"  ✓ 載入 SMHB: {len(self.df_herbs)} 筆草藥資料")

        # 載入草藥別名資料
        self.df_herbs_key = pd.read_excel(
            os.path.join(self.symmap_path, "SymMap v2.0, SMHB key file.xlsx")
        )
        print(f"  ✓ 載入 SMHB key: {len(self.df_herbs_key)} 筆別名資料")

        # 載入核心草藥索引
        self.df_core_index = pd.read_csv(self.core_index_path)
        print(f"  ✓ 載入 core_index_all: {len(self.df_core_index)} 筆核心組合")

        print("資料載入完成!\n")

    def build_herb_name_mapping(self) -> Dict[str, int]:
        """
        建立草藥名稱到 Herb_id 的對應字典
        包含中文名稱、拼音、別名等

        Returns:
            草藥名稱 -> Herb_id 的映射字典
        """
        print("建立草藥名稱對應表...")
        name_to_id = {}

        # 從主檔案建立對應
        for _, row in self.df_herbs.iterrows():
            herb_id = row['Herb_id']

            # 中文名稱
            if pd.notna(row['Chinese_name']):
                name_to_id[row['Chinese_name']] = herb_id

            # 拼音名稱
            if pd.notna(row['Pinyin_name']):
                name_to_id[row['Pinyin_name']] = herb_id

            # 英文名稱
            if pd.notna(row['English_name']):
                name_to_id[row['English_name']] = herb_id

        # 從別名檔案補充
        chinese_names = self.df_herbs_key[
            self.df_herbs_key['Field_name'] == 'Chinese_name'
        ]
        for _, row in chinese_names.iterrows():
            herb_id = row['Herb_id']
            name = row['Field_context']
            if pd.notna(name) and name not in name_to_id:
                name_to_id[name] = herb_id

        print(f"  ✓ 建立了 {len(name_to_id)} 個草藥名稱對應\n")
        return name_to_id

    def parse_herb_combo(self, combo_str: str) -> List[str]:
        """
        解析草藥組合字串

        Args:
            combo_str: 草藥組合字串，如 "五味子、山藥、牛膝、肉蓯蓉"

        Returns:
            草藥名稱列表
        """
        if pd.isna(combo_str):
            return []

        # 使用頓號分割
        herbs = [h.strip() for h in combo_str.split('、')]
        return herbs

    def match_herbs_to_symmap(
        self,
        herb_names: List[str],
        name_mapping: Dict[str, int]
    ) -> Tuple[List[int], List[str], List[str]]:
        """
        將草藥名稱對應到 SymMap Herb_id

        Args:
            herb_names: 草藥名稱列表
            name_mapping: 名稱到 ID 的映射字典

        Returns:
            (匹配的 Herb_id 列表, 匹配的草藥名稱, 未匹配的草藥名稱)
        """
        matched_ids = []
        matched_names = []
        unmatched_names = []

        for name in herb_names:
            if name in name_mapping:
                matched_ids.append(name_mapping[name])
                matched_names.append(name)
            else:
                unmatched_names.append(name)

        return matched_ids, matched_names, unmatched_names

    def analyze_core_combinations(self):
        """分析所有核心草藥組合與 SymMap 的對應關係"""
        print("="*80)
        print("分析核心草藥組合與 SymMap 對應關係")
        print("="*80 + "\n")

        name_mapping = self.build_herb_name_mapping()

        results = []

        for idx, row in self.df_core_index.iterrows():
            community = row['community']
            core_index = row['core_index']
            core_combo = row['core_combo']
            top_substitutes = row['top_substitutes']

            # 解析核心草藥組合
            core_herbs = self.parse_herb_combo(core_combo)
            core_ids, core_matched, core_unmatched = self.match_herbs_to_symmap(
                core_herbs, name_mapping
            )

            # 解析配伍草藥
            substitute_herbs = self.parse_herb_combo(top_substitutes)
            sub_ids, sub_matched, sub_unmatched = self.match_herbs_to_symmap(
                substitute_herbs, name_mapping
            )

            result = {
                'community': community,
                'core_index': core_index,
                'core_combo': core_combo,
                'core_herbs_count': len(core_herbs),
                'core_matched_count': len(core_matched),
                'core_matched_rate': len(core_matched) / len(core_herbs) if core_herbs else 0,
                'core_matched_names': ', '.join(core_matched),
                'core_unmatched_names': ', '.join(core_unmatched),
                'core_herb_ids': ', '.join(map(str, core_ids)),
                'top_substitutes': top_substitutes,
                'sub_herbs_count': len(substitute_herbs),
                'sub_matched_count': len(sub_matched),
                'sub_matched_rate': len(sub_matched) / len(substitute_herbs) if substitute_herbs else 0,
                'sub_matched_names': ', '.join(sub_matched),
                'sub_unmatched_names': ', '.join(sub_unmatched),
                'sub_herb_ids': ', '.join(map(str, sub_ids))
            }

            results.append(result)

            # 輸出分析結果
            print(f"【Community {community} - Core {core_index}】")
            print(f"核心組合: {core_combo}")
            print(f"  草藥數量: {len(core_herbs)}")
            print(f"  匹配 SymMap: {len(core_matched)}/{len(core_herbs)} ({len(core_matched)/len(core_herbs)*100:.1f}%)")
            if core_matched:
                print(f"  ✓ 匹配草藥: {', '.join(core_matched)}")
                print(f"    Herb IDs: {', '.join(map(str, core_ids))}")
            if core_unmatched:
                print(f"  ✗ 未匹配: {', '.join(core_unmatched)}")

            print(f"\n配伍草藥: {top_substitutes}")
            print(f"  草藥數量: {len(substitute_herbs)}")
            print(f"  匹配 SymMap: {len(sub_matched)}/{len(substitute_herbs)} ({len(sub_matched)/len(substitute_herbs)*100:.1f}%)")
            if sub_matched:
                print(f"  ✓ 匹配草藥: {', '.join(sub_matched)}")
                print(f"    Herb IDs: {', '.join(map(str, sub_ids))}")
            if sub_unmatched:
                print(f"  ✗ 未匹配: {', '.join(sub_unmatched)}")

            print("\n" + "-"*80 + "\n")

        # 生成結果 DataFrame
        df_results = pd.DataFrame(results)

        return df_results

    def get_herb_details(self, herb_ids: List[int]) -> pd.DataFrame:
        """
        獲取草藥的詳細資訊

        Args:
            herb_ids: Herb_id 列表

        Returns:
            包含草藥詳細資訊的 DataFrame
        """
        details = self.df_herbs[self.df_herbs['Herb_id'].isin(herb_ids)].copy()
        return details

    def generate_summary_report(self, df_results: pd.DataFrame):
        """生成摘要報告"""
        print("\n" + "="*80)
        print("摘要報告")
        print("="*80 + "\n")

        print(f"總核心組合數量: {len(df_results)}")
        print(f"平均核心草藥數量: {df_results['core_herbs_count'].mean():.2f}")
        print(f"平均配伍草藥數量: {df_results['sub_herbs_count'].mean():.2f}")

        print(f"\n核心草藥 SymMap 匹配率:")
        print(f"  平均: {df_results['core_matched_rate'].mean()*100:.1f}%")
        print(f"  中位數: {df_results['core_matched_rate'].median()*100:.1f}%")
        print(f"  完全匹配: {(df_results['core_matched_rate'] == 1.0).sum()} 組")

        print(f"\n配伍草藥 SymMap 匹配率:")
        print(f"  平均: {df_results['sub_matched_rate'].mean()*100:.1f}%")
        print(f"  中位數: {df_results['sub_matched_rate'].median()*100:.1f}%")
        print(f"  完全匹配: {(df_results['sub_matched_rate'] == 1.0).sum()} 組")

        # 未匹配的草藥統計
        all_unmatched = []
        for names in df_results['core_unmatched_names']:
            if names:
                all_unmatched.extend([n.strip() for n in names.split(',')])
        for names in df_results['sub_unmatched_names']:
            if names:
                all_unmatched.extend([n.strip() for n in names.split(',')])

        if all_unmatched:
            from collections import Counter
            unmatched_counts = Counter(all_unmatched)
            print(f"\n未匹配的草藥 (出現次數 > 1):")
            for herb, count in sorted(unmatched_counts.items(), key=lambda x: x[1], reverse=True):
                if count > 1:
                    print(f"  {herb}: {count} 次")


def main():
    """主程式"""
    symmap_path = "/home/nculcwu/DeepSeek/SymMap"
    core_index_path = "/home/nculcwu/DeepSeek/core_index_all.csv"

    # 建立分析器
    analyzer = HerbAssociationAnalyzer(symmap_path, core_index_path)

    # 分析核心組合
    df_results = analyzer.analyze_core_combinations()

    # 生成摘要報告
    analyzer.generate_summary_report(df_results)

    # 儲存結果
    output_path = "/home/nculcwu/DeepSeek/herb_association_analysis.csv"
    df_results.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n分析結果已儲存至: {output_path}")

    # 儲存 Excel 格式（更易讀）
    output_excel = "/home/nculcwu/DeepSeek/herb_association_analysis.xlsx"
    df_results.to_excel(output_excel, index=False, engine='openpyxl')
    print(f"Excel 格式已儲存至: {output_excel}")


if __name__ == "__main__":
    main()
