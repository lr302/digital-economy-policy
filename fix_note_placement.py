#!/usr/bin/env python3
"""修正笔记位置：根据正确的专题分类将笔记移动到对应子文件夹"""

import os
import re
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent
VAULT_DIR = BASE_DIR / "obsidian-vault"
SRC_DIR = VAULT_DIR / "03-产业政策"  # 所有错误放置的笔记都在这里

# 从CSV原文中提取的正确专题分类 (P编号 → 专题分类)
CORRECT_CATEGORY = {
    "P011": "战略规划",
    "P013": "数据要素",
    "P037": "网络安全",
    "P041": "数字金融",
    "P042": "战略规划",
    "P043": "数字贸易",
    "P044": "数字贸易",
    "P048": "数据安全",
    "P049": "网络安全",
    "P050": "数据安全",
    "P051": "平台经济",
    "P052": "数据安全",
    "P053": "个人信息保护",
    "P054": "个人信息保护",
    "P055": "个人信息保护",
    "P056": "数据要素",
    "P057": "数据要素",
    "P058": "数据要素",
    "P060": "人工智能",
    "P061": "电子商务",
    "P062": "个人信息保护",
    "P064": "网络安全",
    "P065": "数据安全",
    "P066": "平台经济",
    "P067": "数字贸易",
    "P068": "网络安全",
    "P069": "网络安全",
    "P072": "数字普惠",
    "P073": "产业数字化",
    "P074": "产业数字化",
    "P075": "网络安全",
    "P076": "数据跨境",
    "P077": "数据跨境",
    "P078": "个人信息保护",
    "P079": "人工智能",
    "P080": "人工智能",
    "P081": "数据安全",
    "P082": "数字贸易",
    "P083": "电子商务",
    "P084": "数字产业",
}

CATEGORY_TO_FOLDER = {
    "网络安全": "01-基础立法/网络安全",
    "数据安全": "01-基础立法/数据安全",
    "个人信息保护": "01-基础立法/个人信息保护",
    "电子商务": "01-基础立法/电子商务",
    "战略规划": "02-战略规划",
    "人工智能": "03-产业政策/人工智能",
    "平台经济": "03-产业政策/平台经济",
    "数据要素": "03-产业政策/数据要素",
    "数据跨境": "04-跨境监管/数据出境",
    "数字贸易": "04-跨境监管/数字贸易",
    "数字金融": "03-产业政策/产业数字化",
    "数字普惠": "03-产业政策/产业数字化",
    "产业数字化": "03-产业政策/产业数字化",
    "数字产业": "03-产业政策/产业数字化",
}


def fix_yaml_category(note_path, correct_category):
    """修正笔记YAML中的专题分类"""
    content = note_path.read_text(encoding='utf-8')
    # 修正专题分类字段
    content = re.sub(
        r'专题分类: ".*"',
        f'专题分类: "{correct_category}"',
        content
    )
    # 修正第一个tag（专题分类tag）
    content = re.sub(
        r'^  - .+$',
        f'  - {correct_category}',
        content,
        count=1,
        flags=re.MULTILINE
    )
    note_path.write_text(content, encoding='utf-8')


def main():
    moved = 0
    fixed_only = 0
    
    for pid, category in CORRECT_CATEGORY.items():
        folder_rel = CATEGORY_TO_FOLDER.get(category)
        if not folder_rel:
            print(f"  ⚠ {pid}: 未找到分类[{category}]的文件夹映射")
            continue
        
        # 查找笔记文件
        pattern = f"{pid}_*.md"
        candidates = list(SRC_DIR.glob(pattern))
        
        if not candidates:
            # 可能已经在正确位置
            dest_dir = VAULT_DIR / folder_rel
            already_there = list(dest_dir.glob(f"{pid}_*.md")) if dest_dir.exists() else []
            if already_there:
                print(f"  ✓ {pid}: 已在正确位置 {folder_rel}/")
                continue
            print(f"  ⚠ {pid}: 未找到笔记文件")
            continue
        
        src = candidates[0]
        dest_dir = VAULT_DIR / folder_rel
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        
        if src.parent == dest_dir:
            print(f"  ✓ {pid}: 已在正确文件夹")
            continue
        
        print(f"  📦 {pid}: {src.name} → {folder_rel}/")
        shutil.move(str(src), str(dest))
        moved += 1
        
        # 修正YAML中的专题分类
        fix_yaml_category(dest, category)
    
    print(f"\n=== 完成 ===")
    print(f"移动笔记: {moved}")
    print(f"就地修正: {fixed_only}")


if __name__ == '__main__':
    main()
