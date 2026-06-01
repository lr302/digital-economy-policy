#!/usr/bin/env python3
"""
智能PDF下载器 - 根据CSV中的官方来源URL下载政策文件PDF原文
策略：
  1. 检查页面中是否有直接PDF链接 → 下载
  2. 提取HTML正文内容 → 用fpdf2生成干净PDF
"""

import csv
import os
import re
import time
import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF

# 配置
BASE = Path(r"D:\workbuddy\2026-05-29-task-1\数字经济政策知识库")
CSV_PATH = BASE / "政策文件元数据清单_修正_updated.csv"
PDF_DIR = BASE / "obsidian-vault" / "附件" / "原文PDF"
PDF_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SESSION.timeout = 30

# 记录日志
log_lines = []

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    log_lines.append(line)

def load_entries():
    """读取CSV，返回需要下载的条目列表（有URL的全部）"""
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    
    entries = []
    for r in rows:
        url = r.get('官方来源', '').strip()
        if url:
            entries.append({
                'pid': r['编号'].strip(),
                'title': r['文件名称'].strip(),
                'url': url,
                'org': r.get('发布机构', '').strip(),
            })
    return entries


def find_pdf_links(soup, base_url):
    """在HTML页面中查找直接指向PDF的链接"""
    pdf_links = []
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href.lower().endswith('.pdf'):
            full_url = urljoin(base_url, href)
            pdf_links.append((full_url, a.get_text(strip=True)))
    return pdf_links


def extract_content_govcn(soup, base_url):
    """从gov.cn页面提取正文内容"""
    # 尝试多个可能的正文容器
    candidates = [
        soup.find('div', class_='article'),
        soup.find('div', class_='pages_content'),
        soup.find('div', id='UCAP-CONTENT'),
        soup.find('div', class_='con_article'),
        soup.find('div', class_='article_con'),
        soup.find('div', class_='TRS_Editor'),
        soup.find('div', class_='content'),
        soup.find('div', id='content'),
        soup.find('article'),
    ]
    
    for c in candidates:
        if c and len(c.get_text(strip=True)) > 100:
            return c
    
    # 最后手段：取body
    body = soup.find('body')
    return body


def extract_content_cac(soup, base_url):
    """从cac.gov.cn页面提取正文"""
    candidates = [
        soup.find('div', class_='article'),
        soup.find('div', id='infoContent'),
        soup.find('div', class_='content'),
        soup.find('div', class_='con'),
        soup.find('div', class_='TRS_Editor'),
        soup.find('div', id='UCAP-CONTENT'),
    ]
    
    for c in candidates:
        if c and len(c.get_text(strip=True)) > 100:
            return c
    
    body = soup.find('body')
    return body


def fetch_page(url, retries=2):
    """获取URL内容"""
    for i in range(retries + 1):
        try:
            resp = SESSION.get(url, timeout=30)
            resp.raise_for_status()
            # 检测实际内容类型
            ct = resp.headers.get('Content-Type', '')
            return resp
        except Exception as e:
            log(f"  获取失败 ({i+1}/{retries+1}): {e}")
            if i < retries:
                time.sleep(2)
    return None


def create_pdf_from_html(content_elem, title, output_path):
    """从HTML元素提取文字并生成干净PDF"""
    if content_elem is None:
        return False
    
    # 提取纯文本，保留段落结构
    paragraphs = []
    for elem in content_elem.descendants:
        if elem.name == 'p' and elem.get_text(strip=True):
            text = elem.get_text(strip=True)
            if len(text) > 5:
                paragraphs.append(text)
    
    if not paragraphs:
        # Fallback: just get all text
        text = content_elem.get_text('\n', strip=True)
        paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 10]
    
    if not paragraphs:
        return False
    
    # 用fpdf2生成PDF
    pdf = FPDF()
    pdf.add_page()
    
    # 尝试使用中文字体
    try:
        # Windows 系统字体
        font_paths = [
            "C:/Windows/Fonts/simhei.ttf",  # 黑体
            "C:/Windows/Fonts/simsun.ttc",   # 宋体
            "C:/Windows/Fonts/msyh.ttc",     # 微软雅黑
        ]
        font_path = None
        for fp in font_paths:
            if os.path.exists(fp):
                font_path = fp
                break
        
        if font_path:
            pdf.add_font('CN', '', font_path, uni=True)
            pdf.add_font('CN', 'B', font_path, uni=True)
        else:
            log("  ⚠ 未找到中文字体，将使用内置字体")
            font_path = None
    except Exception:
        font_path = None
    
    if font_path:
        # 标题
        pdf.set_font('CN', 'B', 14)
        pdf.multi_cell(0, 10, title, align='C')
        pdf.ln(5)
        pdf.set_font('CN', '', 11)
        for para in paragraphs[:200]:  # 限制段落数
            try:
                pdf.multi_cell(0, 6, para)
                pdf.ln(2)
            except:
                pass  # 跳过编码异常的段落
    else:
        # 无中文字体时使用latin-1兼容的方法
        pdf.set_font('Helvetica', 'B', 14)
        pdf.multi_cell(0, 10, title[:100], align='C')
        pdf.ln(5)
        pdf.set_font('Helvetica', '', 10)
        for para in paragraphs[:200]:
            try:
                # 安全编码
                safe = para.encode('latin-1', errors='replace').decode('latin-1')
                pdf.multi_cell(0, 6, safe)
                pdf.ln(2)
            except:
                pass
    
    pdf.output(output_path)
    return True


def download_direct_pdf(url, output_path):
    """直接下载PDF文件"""
    try:
        resp = SESSION.get(url, timeout=60, stream=True)
        resp.raise_for_status()
        ct = resp.headers.get('Content-Type', '').lower()
        
        with open(output_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # 验证
        file_size = os.path.getsize(output_path)
        if file_size < 1000:  # 太小，可能不是有效PDF
            os.remove(output_path)
            return False, f"文件太小({file_size}字节)"
        
        # 检查PDF头
        with open(output_path, 'rb') as f:
            header = f.read(5)
        if header != b'%PDF-':
            os.remove(output_path)
            return False, "不是有效PDF"
            
        return True, f"下载成功({file_size//1024}KB)"
    except Exception as e:
        return False, str(e)


def process_entry(entry):
    """处理单个条目的PDF下载"""
    pid = entry['pid']
    title = entry['title']
    url = entry['url']
    output_path = PDF_DIR / f"{pid}_{title[:40]}.pdf"
    
    log(f"处理 {pid}: {title[:50]}")
    log(f"  URL: {url}")
    
    # 策略0：如果URL直接指向PDF
    if url.lower().endswith('.pdf'):
        log(f"  → 直接PDF下载")
        ok, msg = download_direct_pdf(url, output_path)
        if ok:
            log(f"  ✅ {msg}")
            return True
        else:
            log(f"  ❌ 直接下载失败: {msg}")
    
    # 策略1：获取页面并查找PDF链接
    log(f"  → 获取页面...")
    resp = fetch_page(url)
    if resp is None:
        log(f"  ❌ 无法获取页面")
        return False
    
    ct = resp.headers.get('Content-Type', '').lower()
    
    # 如果响应本身就是PDF
    if 'application/pdf' in ct or url.lower().endswith('.pdf'):
        ok, msg = download_direct_pdf(url, output_path)
        log(f"  {'✅' if ok else '❌'} {msg}")
        return ok
    
    # 解析HTML
    soup = BeautifulSoup(resp.content, 'html.parser')
    
    # 策略2：查找页面中的PDF链接
    pdf_links = find_pdf_links(soup, url)
    if pdf_links:
        log(f"  → 从页面找到 {len(pdf_links)} 个PDF链接")
        for pdf_url, link_text in pdf_links[:3]:  # 尝试前3个
            log(f"     尝试: {pdf_url[:80]}...")
            ok, msg = download_direct_pdf(pdf_url, output_path)
            if ok:
                log(f"     ✅ {msg}")
                return True
            log(f"     ❌ {msg}")
    
    # 策略3：提取页面正文内容生成PDF
    domain = urlparse(url).netloc
    log(f"  → 提取页面正文生成PDF")
    
    if 'gov.cn' in domain:
        content = extract_content_govcn(soup, url)
    elif 'cac.gov.cn' in domain:
        content = extract_content_cac(soup, url)
    else:
        # 通用提取
        content = extract_content_govcn(soup, url) or extract_content_cac(soup, url)
    
    ok = create_pdf_from_html(content, title, output_path)
    if ok:
        file_size = os.path.getsize(output_path)
        log(f"  ✅ 正文提取生成PDF ({file_size//1024}KB)")
        return True
    else:
        log(f"  ❌ 无法生成PDF")
        return False


def main():
    log("=" * 60)
    log("开始批量下载政策文件PDF")
    log("=" * 60)
    
    entries = load_entries()
    log(f"共 {len(entries)} 条有URL的条目")
    
    success = 0
    fail = 0
    skip = 0
    
    for i, entry in enumerate(entries):
        pid = entry['pid']
        output_path = PDF_DIR / f"{pid}_{entry['title'][:40]}.pdf"
        
        # 检查是否已有合格PDF（跳过之前标记为OK的）
        # 这里我们处理全部，用新下载覆盖旧文件
        
        log(f"\n[{i+1}/{len(entries)}] {pid}")
        
        try:
            if process_entry(entry):
                success += 1
            else:
                fail += 1
        except Exception as e:
            log(f"  ❌ 异常: {e}")
            fail += 1
        
        # 礼貌延迟
        if i < len(entries) - 1:
            time.sleep(1.5)
    
    log(f"\n{'=' * 60}")
    log(f"完成! 成功: {success}, 失败: {fail}, 跳过: {skip}")
    log(f"输出目录: {PDF_DIR}")
    
    # 保存日志
    log_path = BASE / "pdf下载日志_20260530.log"
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines))
    log(f"日志已保存: {log_path}")


if __name__ == '__main__':
    main()
