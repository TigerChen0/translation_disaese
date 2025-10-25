#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改進版草藥關聯性驗證分析 - 支援簡繁體轉換

此腳本整合 SymMap 資料庫（簡體）與 core_index_all.csv（繁體），
透過簡繁轉換和別名對應來驗證核心草藥組合與配伍草藥的關聯性證據。
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, List, Set, Tuple
import re


# 常用中藥簡繁體對照表
HERB_NAME_MAPPING = {
    # 繁體 -> 簡體
    '當歸': '当归',
    '黃芩': '黄芩',
    '黃連': '黄连',
    '黃柏': '黄柏',
    '黃精': '黄精',
    '黃耆': '黄芪',
    '麥門冬': '麦门冬',
    '天門冬': '天门冬',
    '山藥': '山药',
    '乾薑': '干姜',
    '龍膽': '龙胆',
    '龍腦': '龙脑',
    '龍骨': '龙骨',
    '龍齒': '龙齿',
    '龍眼肉': '龙眼肉',
    '丹參': '丹参',
    '澤瀉': '泽泻',
    '肉蓯蓉': '肉苁蓉',
    '麝香': '麝香',
    '鬱金': '郁金',
    '厚朴': '厚朴',
    '貝母': '贝母',
    '細辛': '细辛',
    '遠志': '远志',
    '連翹': '连翘',
    '陳皮': '陈皮',
    '穀精草': '谷精草',
    '續斷': '续断',
    '豬苓': '猪苓',
    '麻黃': '麻黄',
    '薑黃': '姜黄',
    '蒼朮': '苍术',
    '術': '术',
    '熟地黃': '熟地黄',
    '熟地黄': '熟地黄',
    '生地黃': '生地黄',
    '枸杞子': '枸杞子',
    '構紙': '构纸',
    '萎蕤': '萎蕤',
    '釀': '酿',
    '鱉甲': '鳖甲',
    '龜板': '龟板',
    '酸棗仁': '酸枣仁',
    '柏子仁': '柏子仁',
    '紫蘇': '紫苏',
    '紫蘇子': '紫苏子',
    '紫蘇葉': '紫苏叶',
    '紫苑': '紫菀',
    '紫石英': '紫石英',
    '絲瓜絡': '丝瓜络',
    '络石藤': '络石藤',
    '赤芍': '赤芍',
    '赤小豆': '赤小豆',
    '赤茯苓': '赤茯苓',
    '赤石脂': '赤石脂',
    '白蘞': '白蔹',
    '白芍': '白芍',
    '白朮': '白术',
    '梔子': '栀子',
    '枳殼': '枳壳',
    '桔梗': '桔梗',
    '羌活': '羌活',
    '羚羊角': '羚羊角',
    '蜀椒': '蜀椒',
    '大黃': '大黄',
    '大棗': '大枣',
    '天竺黃': '天竺黄',
    '玄參': '玄参',
    '沙參': '沙参',
    '桑白皮': '桑白皮',
    '桂心': '桂',
    '杏仁': '杏仁',
    '生薑': '生姜',
    '乾地黃': '干地黄',
    '知母': '知母',
    '芒硝': '芒硝',
    '木通': '木通',
    '石膏': '石膏',
    '升麻': '升麻',
    '前胡': '前胡',
    '附子': '附子',
    '川芎': '川芎',
    '厚朴': '厚朴',
    '牛黃': '牛黄',
    '犀角': '犀角',
    '琥珀': '琥珀',
    '雄黃': '雄黄',
    '鐵粉': '铁粉',
    '鉛霜': '铅霜',
    '虎睛': '虎睛',
    '金箔': '金箔',
    '銀箔': '银箔',
    '硃砂': '朱砂',
    '茯苓': '茯苓',
    '半夏': '半夏',
    '柴胡': '柴胡',
    '牡丹皮': '牡丹皮',
    '木香': '木香',
    '地骨皮': '地骨皮',
    '沉香': '沉香',
    '葛根': '葛根',
    '肉桂': '肉桂',
    '杜仲': '杜仲',
    '山茱萸': '山茱萸',
    '牛膝': '牛膝',
    '秦艽': '秦艽',
    '五味子': '五味子',
    '珍珠': '珍珠',
}


def traditional_to_simplified(text: str) -> str:
    """
    繁體轉簡體（使用對照表）

    Args:
        text: 繁體中文文本

    Returns:
        簡體中文文本
    """
    if pd.isna(text):
        return text

    # 先檢查是否在對照表中
    if text in HERB_NAME_MAPPING:
        return HERB_NAME_MAPPING[text]

    # 逐字轉換常見繁體字
    simple_char_map = {
        '當': '当', '黃': '黄', '門': '门', '藥': '药', '薑': '姜',
        '龍': '龙', '參': '参', '澤': '泽', '瀉': '泻', '蓯': '苁',
        '貝': '贝', '細': '细', '遠': '远', '連': '连', '翹': '翘',
        '陳': '陈', '穀': '谷', '續': '续', '斷': '断', '豬': '猪',
        '麻': '麻', '蒼': '苍', '術': '术', '構': '构', '釀': '酿',
        '鱉': '鳖', '龜': '龟', '棗': '枣', '蘇': '苏', '葉': '叶',
        '苑': '菀', '絲': '丝', '絡': '络', '蘞': '蔹', '梔': '栀',
        '殼': '壳', '羚': '羚', '竺': '竺', '鐵': '铁', '鉛': '铅',
        '硃': '朱', '銀': '银', '麝': '麝', '鬱': '郁', '於': '于',
    }

    result = text
    for trad, simp in simple_char_map.items():
        result = result.replace(trad, simp)

    return result


class HerbAssociationAnalyzer:
    """草藥關聯性分析器（支援簡繁轉換）"""

    def __init__(self, symmap_path: str, core_index_path: str):
        self.symmap_path = symmap_path
        self.core_index_path = core_index_path

        self.df_herbs = None
        self.df_herbs_key = None
        self.df_core_index = None

        self.load_data()

    def load_data(self):
        """載入所有需要的資料檔案"""
        print("載入資料...")

        self.df_herbs = pd.read_excel(
            os.path.join(self.symmap_path, "SymMap v2.0, SMHB file.xlsx")
        )
        print(f"  ✓ 載入 SMHB: {len(self.df_herbs)} 筆草藥資料")

        self.df_herbs_key = pd.read_excel(
            os.path.join(self.symmap_path, "SymMap v2.0, SMHB key file.xlsx")
        )
        print(f"  ✓ 載入 SMHB key: {len(self.df_herbs_key)} 筆別名資料")

        self.df_core_index = pd.read_csv(self.core_index_path)
        print(f"  ✓ 載入 core_index_all: {len(self.df_core_index)} 筆核心組合")

        print("資料載入完成!\n")

    def build_herb_name_mapping(self) -> Dict[str, int]:
        """
        建立草藥名稱到 Herb_id 的對應字典
        同時支援繁體和簡體名稱

        Returns:
            草藥名稱 -> Herb_id 的映射字典
        """
        print("建立草藥名稱對應表（含簡繁轉換）...")
        name_to_id = {}

        # 從主檔案建立對應
        for _, row in self.df_herbs.iterrows():
            herb_id = row['Herb_id']

            # 簡體中文名稱（SymMap 原始）
            if pd.notna(row['Chinese_name']):
                simp_name = row['Chinese_name']
                name_to_id[simp_name] = herb_id

                # 也儲存可能的繁體形式
                for trad, simp in HERB_NAME_MAPPING.items():
                    if simp == simp_name:
                        name_to_id[trad] = herb_id

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
        """解析草藥組合字串"""
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
        將草藥名稱對應到 SymMap Herb_id（支援簡繁轉換）

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
            # 先嘗試直接匹配
            if name in name_mapping:
                matched_ids.append(name_mapping[name])
                matched_names.append(name)
            else:
                # 嘗試簡繁轉換
                simp_name = traditional_to_simplified(name)
                if simp_name in name_mapping:
                    matched_ids.append(name_mapping[simp_name])
                    matched_names.append(name)
                else:
                    unmatched_names.append(name)

        return matched_ids, matched_names, unmatched_names

    def analyze_core_combinations(self):
        """分析所有核心草藥組合與 SymMap 的對應關係"""
        print("="*80)
        print("分析核心草藥組合與 SymMap 對應關係（含簡繁轉換）")
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

        df_results = pd.DataFrame(results)
        return df_results

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
        print(f"  高匹配 (≥75%): {(df_results['core_matched_rate'] >= 0.75).sum()} 組")

        print(f"\n配伍草藥 SymMap 匹配率:")
        print(f"  平均: {df_results['sub_matched_rate'].mean()*100:.1f}%")
        print(f"  中位數: {df_results['sub_matched_rate'].median()*100:.1f}%")
        print(f"  完全匹配: {(df_results['sub_matched_rate'] == 1.0).sum()} 組")
        print(f"  高匹配 (≥75%): {(df_results['sub_matched_rate'] >= 0.75).sum()} 組")

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
            print(f"\n未匹配的草藥 (共 {len(unmatched_counts)} 種):")
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
    output_path = "/home/nculcwu/DeepSeek/herb_association_analysis_improved.csv"
    df_results.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n分析結果已儲存至: {output_path}")

    # 儲存 Excel 格式
    output_excel = "/home/nculcwu/DeepSeek/herb_association_analysis_improved.xlsx"
    df_results.to_excel(output_excel, index=False, engine='openpyxl')
    print(f"Excel 格式已儲存至: {output_excel}")


if __name__ == "__main__":
    main()
