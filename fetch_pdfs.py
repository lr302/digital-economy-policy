#!/usr/bin/env python3
"""
政策文件 PDF 批量采集脚本 (v3)
- 使用 Chrome Headless 打印 PDF
- 跳过已存在的 PDF
- 跳过无效 URL
- 每条页面最多等待 30 秒，超时强制跳过
"""

import csv
import os
import sys
import time
import subprocess
import signal
import logging
from datetime import datetime
from pathlib import Path

# ============ 配置 ============
CSV_PATH = Path(__file__).parent / "政策文件元数据清单.csv"
PDF_DIR = Path(__file__).parent / "obsidian-vault" / "附件" / "原文PDF"
REPORT_PATH = Path(__file__).parent / "pdf采集报告.md"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

DELAY = 2               # 每条之间间隔（秒）
PAGE_TIMEOUT = 30        # 单个页面超时（秒）
VIRTUAL_TIME = 15000     # Chrome 等待页面渲染（毫秒）

SKIP_DOMAINS = {
    "www.gov.cn", "npc.gov.cn", "www.cac.gov.cn", "www.mofcom.gov.cn",
    "www.miit.gov.cn", "www.samr.gov.cn", "www.tc260.org.cn",
    "www.pbc.gov.cn", "www.sasac.gov.cn", "openstd.samr.gov.cn",
    "www.most.gov.cn"
}

# ============ 日志 ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent / "pdf采集日志.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


def safe_name(doc_id: str, title: str) -> str:
    for c in '<>:"/\\|?*':
        title = title.replace(c, '')
    return f"{doc_id}_{title[:50]}"


def valid_url(url: str) -> bool:
    if not url or not url.strip() or url.strip() == "":
        return False
    from urllib.parse import urlparse
    p = urlparse(url.strip())
    if p.netloc in SKIP_DOMAINS and (not p.path or p.path in ("/", "")):
        return False
    return p.scheme in ("http", "https")


def fetch_pdf(url: str, out: Path) -> bool:
    """调用 Chrome headless 打印 PDF，超时强制终止"""
    out.parent.mkdir(parents=True, exist_ok=True)
    abs_path = str(out.resolve())

    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-software-rasterizer",
        f"--print-to-pdf={abs_path}",
        "--no-pdf-header-footer",
        f"--virtual-time-budget={VIRTUAL_TIME}",
        url.strip()
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PAGE_TIMEOUT,
            encoding="utf-8",
            errors="replace"
        )
        # Chrome 成功时把 "written to file" 写在 stderr
        success = (
            out.exists() and out.stat().st_size > 1024
        ) or (
            "written to file" in (result.stderr or "") and out.exists()
        )
        if not success and out.exists():
            out.unlink(missing_ok=True)
        return success
    except subprocess.TimeoutExpired:
        logger.warning("    ⏱️ Chrome 超时，终止进程")
        return False
    except Exception as e:
        logger.warning(f"    Chrome 异常: {e}")
        return False


def process(idx: int, total: int, row: dict) -> dict:
    doc_id = row["编号"].strip()
    title = row["文件名称"].strip()
    url = row["官方来源"].strip()
    stage = row.get("所属阶段", "").strip()

    res = {"编号": doc_id, "文件名称": title, "来源": url, "阶段": stage,
           "状态": "", "备注": ""}

    pdf = PDF_DIR / f"{safe_name(doc_id, title)}.pdf"

    # 已存在
    if pdf.exists() and pdf.stat().st_size > 1024:
        res["状态"] = "已存在"
        logger.info(f"[{idx:02d}/{total}] {doc_id} ✅ 已存在，跳过")
        return res

    if not valid_url(url):
        res["状态"] = "跳过"
        res["备注"] = "URL 不完整"
        logger.info(f"[{idx:02d}/{total}] {doc_id} ⏭️ 跳过（URL 不完整）")
        return res

    # 抓取
    t = title[:35] + ("..." if len(title) > 35 else "")
    logger.info(f"[{idx:02d}/{total}] {doc_id} | {t}")
    ok = fetch_pdf(url, pdf)
    if ok:
        res["状态"] = "成功"
        logger.info(f"    ✅ PDF 已生成 ({pdf.stat().st_size//1024} KB)")
    else:
        res["状态"] = "失败"
        res["备注"] = "Chrome 无法生成 PDF（页面不可访问或超时）"
        logger.warning(f"    ❌ 失败")
    return res


def write_report(results: list, elapsed: float):
    sc = sum(1 for r in results if r["状态"] == "成功")
    ex = sum(1 for r in results if r["状态"] == "已存在")
    fl = sum(1 for r in results if r["状态"] == "失败")
    sk = sum(1 for r in results if r["状态"] == "跳过")
    total = len(results)

    lines = [
        f"# 政策文件 PDF 采集报告",
        f"",
        f"**采集时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**总耗时**: {elapsed/60:.1f} 分钟  ",
        f"",
        f"## 总体统计",
        f"",
        f"| 状态 | 数量 | 占比 |",
        f"|------|------|------|",
        f"| ✅ 新成功 | {sc} | {sc/total*100:.1f}% |",
        f"| 🔄 已存在 | {ex} | {ex/total*100:.1f}% |",
        f"| ❌ 失败 | {fl} | {fl/total*100:.1f}% |",
        f"| ⏭️ 跳过 | {sk} | {sk/total*100:.1f}% |",
        f"",
        f"## PDF 存放位置",
        f"",
        f"```",
        f"obsidian-vault/附件/原文PDF/",
        f"```",
        f"",
        f"## 失败 / 跳过详情（需人工处理）",
        f"",
        f"| 编号 | 文件名称 | 来源 | 原因 |",
        f"|------|---------|------|------|",
    ]
    for r in results:
        if r["状态"] in ("失败", "跳过"):
            ts = r["文件名称"][:28] + "..." if len(r["文件名称"]) > 28 else r["文件名称"]
            us = r["来源"][:45] + "..." if len(r["来源"]) > 45 else r["来源"]
            lines.append(f"| {r['编号']} | {ts} | {us} | {r['备注']} |")

    lines += [
        f"",
        f"## 说明",
        f"",
        f"- **gov.cn / cac.gov.cn / mof.gov.cn 等**: 如失败，可能需要手动打开页面后 Ctrl+P → 另存为 PDF",
        f"- **flk.npc.gov.cn**: 人大法律数据库有反爬保护，建议手动从 https://flk.npc.gov.cn 搜索对应法律名称，直接另存为 PDF",
        f"- **URL 不完整**: 需要补充具体页面路径",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"📄 报告已保存: {REPORT_PATH.name}")


def main():
    t0 = time.time()
    print(f"{'='*60}")
    print(f"  政策文件 PDF 批量采集 (v3)")
    print(f"  引擎: Chrome Headless")
    print(f"  输出: {PDF_DIR}")
    print(f"{'='*60}")
    print()

    if not os.path.exists(CHROME):
        print(f"❌ 找不到 Chrome: {CHROME}")
        return

    PDF_DIR.mkdir(parents=True, exist_ok=True)

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    print(f"📋 共 {len(rows)} 条政策")
    print()

    results = []
    for i, row in enumerate(rows, 1):
        r = process(i, len(rows), row)
        results.append(r)
        # 进度
        if i % 10 == 0 or i == len(rows):
            sc = sum(1 for x in results if x["状态"] in ("成功", "已存在"))
            fl = sum(1 for x in results if x["状态"] == "失败")
            print(f"  ── 进度 {i}/{len(rows)} | ✅{sc} ❌{fl} ──")
        if i < len(rows):
            time.sleep(DELAY)

    elapsed = time.time() - t0
    print()
    write_report(results, elapsed)

    sc = sum(1 for r in results if r["状态"] in ("成功", "已存在"))
    print(f"{'='*60}")
    print(f"  📊 采集完成!")
    print(f"  PDF 文件数: {sc} / {len(results)}")
    print(f"  ⏱️  总耗时: {elapsed/60:.1f} 分钟")
    print(f"  📁 存放: {PDF_DIR}")
    print(f"  📄 报告: {REPORT_PATH}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
