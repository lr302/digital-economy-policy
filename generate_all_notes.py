#!/usr/bin/env python3
"""为所有有PDF的政策文件生成Obsidian笔记"""

import csv
import os
import glob
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
VAULT_DIR = BASE_DIR / "obsidian-vault"
PDF_DIR = VAULT_DIR / "附件" / "原文PDF"
CSV_PATH = BASE_DIR / "政策文件元数据清单_修正_v3.csv"

# 专题分类 -> 文件夹映射
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
    "算法治理": "03-产业政策/人工智能",
    "数字政府": "03-产业政策/产业数字化",
    "数字消费": "03-产业政策/产业数字化",
    "数字金融": "03-产业政策/产业数字化",
    "数字普惠": "03-产业政策/产业数字化",
    "产业数字化": "03-产业政策/产业数字化",
    "数字产业": "03-产业政策/产业数字化",
}

# 阶段标签映射
STAGE_TAG = {
    "阶段一：萌芽起步期": "阶段一",
    "阶段二：加速构建期": "阶段二",
    "阶段三：规制重构期": "阶段三",
    "阶段四：高质量发展期": "阶段四",
}

# 效力层级标签映射
LEVEL_TAG = {
    "全国人大常委会立法": "立法",
    "党中央/国务院文件": "党中央国务院文件",
    "行政法规": "行政法规",
    "国务院规范性文件": "国务院文件",
    "国务院办公厅规范性文件": "国务院文件",
    "部门规章": "部门规章",
    "部门规章/指南": "部门规章",
    "部门规范性文件": "部门规范性文件",
    "部门规章（草案）": "部门规章",
    "国家标准": "国家标准",
    "行业标准/指南": "行业标准",
    "部门报告/规范性文件": "部门规范性文件",
    "行政机构": "行政机构",
    "党中央文件": "党中央国务院文件",
    "立法进程中": "立法进程中",
    "国际条约/协定": "国际条约",
    "国际条约/谈判": "国际条约",
    "地方试点文件": "地方试点",
    "立法草案/研究报告": "立法进程中",
    "规范性文件": "规范性文件",
    "技术文件/白皮书": "技术文件",
    "部门指南": "部门指南",
    "部门公告": "部门规范性文件",
}


def read_csv():
    """读取CSV，返回政策列表"""
    policies = []
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            policies.append(row)
    return policies


def get_existing_notes():
    """返回已有笔记的P编号集合"""
    notes = set()
    for md_file in VAULT_DIR.rglob("*.md"):
        # 跳过模板和主页
        if "模板" in md_file.name or "知识库主页" in md_file.name or "Dataview" in md_file.name:
            continue
        match = re.match(r'(P\d{3})_', md_file.name)
        if match:
            notes.add(match.group(1))
    return notes


def get_existing_pdfs():
    """返回已有PDF的P编号集合"""
    pdfs = set()
    for pdf_file in PDF_DIR.glob("P*.pdf"):
        match = re.match(r'(P\d{3})_', pdf_file.name)
        if match:
            pdfs.add(match.group(1))
    return pdfs


def sanitize_filename(name):
    """清理文件名中的非法字符"""
    name = name.replace('"', '').replace('*', '').replace(':', '：')
    name = name.replace('<', '').replace('>', '').replace('|', '')
    name = name.replace('?', '').replace('\\', '').replace('/', '')
    return name


def get_tag_for_level(level):
    """获取效力层级对应的标签"""
    for key, tag in LEVEL_TAG.items():
        if key in level:
            return tag
    return "其他"


def generate_note(policy, pdf_filename):
    """生成单个笔记的Markdown内容"""
    pid = policy['编号'].strip()
    title = policy['文件名称'].strip()
    doc_num = policy.get('发文号', '无').strip()
    org = policy.get('发布机构', '').strip()
    date_str = policy.get('发布日期', '').strip()
    level = policy.get('效力层级', '').strip()
    stage = policy.get('所属阶段', '').strip()
    category = policy.get('专题分类', '').strip()
    summary = policy.get('核心内容摘要', '').strip()
    url = policy.get('官方来源', '').strip()
    # 多URL取第一个
    if ',' in url:
        url = url.split(',')[0].strip()

    # 处理日期
    date_clean = date_str
    # 尝试提取YYYY-MM-DD
    date_match = re.match(r'(\d{4}-\d{2}-\d{2})', date_str)
    if date_match:
        date_clean = date_match.group(1)
    else:
        date_clean = date_str.split(',')[0]

    stage_tag = STAGE_TAG.get(stage, stage)
    level_tag = get_tag_for_level(level)

    # PDF路径
    pdf_path = f"附件/原文PDF/{pdf_filename}"

    note = f'''---
文件编号: "{pid}"
文件名称: "{title}"
发文号: "{doc_num}"
发布机构: "{org}"
发布日期: {date_clean}
效力层级: "{level}"
演进阶段: "{stage}"
专题分类: "{category}"
tags:
  - {category}
  - {stage_tag}
  - {level_tag}
上位法: []
配套文件: []
替代文件: ""
修订自: ""
官方来源: "{url}"
PDF本地路径: "{pdf_path}"
重要程度: ⭐⭐⭐
阅读状态: "未读"
研究价值: ""
---

# {title}

## 核心摘要

> **一句话概括**：{summary}

**颁布背景**：
（待补充）

**主要内容**：
（{summary}）

**历史意义**：
（待补充）

---

## 关键条款摘录

> （待从原文PDF摘录）

---

## 研究笔记

### 制度创新点
（待补充）

### 与其他法律的关系
（待补充）

### 实施效果评估
（待补充）

### 待深入研究的问题
- [ ] 

---

## 相关政策文件

### 上位法
- [[]]

### 配套文件
- [[]]

### 相关案例
- [[]]

---

## 教学应用

**适合课程**：

**教学重点**：

**案例延伸**：

---

## 参考文献

1. 
'''
    return note


def main():
    policies = read_csv()
    existing_notes = get_existing_notes()
    existing_pdfs = get_existing_pdfs()

    print(f"CSV政策总数: {len(policies)}")
    print(f"已有笔记: {len(existing_notes)}")
    print(f"已有PDF: {len(existing_pdfs)}")

    # 找出PDF文件名映射
    pdf_name_map = {}
    for pdf_file in PDF_DIR.glob("P*.pdf"):
        match = re.match(r'(P\d{3})_', pdf_file.name)
        if match:
            pdf_name_map[match.group(1)] = pdf_file.name

    created = 0
    skipped = 0

    for policy in policies:
        pid = policy['编号'].strip()
        if not pid.startswith('P'):
            continue

        # 跳过已有笔记的
        if pid in existing_notes:
            skipped += 1
            continue

        # 跳过没有PDF的
        if pid not in existing_pdfs:
            print(f"  ⚠ {pid} 无PDF，跳过")
            continue

        category = policy.get('专题分类', '').strip()
        folder_rel = CATEGORY_TO_FOLDER.get(category, f"03-产业政策")
        folder_path = VAULT_DIR / folder_rel
        folder_path.mkdir(parents=True, exist_ok=True)

        pdf_filename = pdf_name_map[pid]
        title = policy['文件名称'].strip()
        safe_title = sanitize_filename(title)
        note_filename = f"{pid}_{safe_title}.md"
        note_path = folder_path / note_filename

        content = generate_note(policy, pdf_filename)
        note_path.write_text(content, encoding='utf-8')
        created += 1
        print(f"  ✅ {pid} → {folder_rel}/{note_filename}")

    print(f"\n=== 完成 ===")
    print(f"新增笔记: {created}")
    print(f"已有笔记(跳过): {skipped}")
    print(f"总计: {created + skipped}")
    print(f"缺口(无PDF): {len(policies) - len(existing_pdfs)}")


if __name__ == '__main__':
    main()
