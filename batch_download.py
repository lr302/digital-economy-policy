#!/usr/bin/env python3
"""批量从gov.cn等政府网站提取政策正文并生成PDF"""
import csv, os, re, time, requests
from pathlib import Path
from bs4 import BeautifulSoup
from fpdf import FPDF

BASE = Path(r"D:\workbuddy\2026-05-29-task-1\数字经济政策知识库")
CSV = BASE / "政策文件元数据清单_修正_v2.csv"
PDF_DIR = BASE / "obsidian-vault" / "附件" / "原文PDF"
PDF_DIR.mkdir(parents=True, exist_ok=True)
LOG = []

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ============ 中文字体 ============
FONT_PATH = None
for fp in ["C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc", "C:/Windows/Fonts/msyh.ttc"]:
    if os.path.exists(fp):
        FONT_PATH = fp
        print(f"使用字体: {fp}")
        break

# ============ 正文提取 ============
def extract_content(soup, url):
    """智能提取政策正文"""
    domain = url.split('/')[2] if '//' in url else ''
    
    # gov.cn 常用选择器
    gov_selectors = [
        'div.article', '#UCAP-CONTENT', '.pages_content', '.con_article',
        '.article_con', '.TRS_Editor', 'div[class*="article"]', 'div[class*="content"]',
        'article', '.news_box', '.main-content'
    ]
    
    # cac.gov.cn 选择器
    cac_selectors = [
        'div.article', '#infoContent', '.TRS_Editor', '.content', '.con',
        'div.detail-content', 'div.text-content'
    ]
    
    all_selectors = gov_selectors + cac_selectors
    seen = set()
    for sel in all_selectors:
        if sel in seen: continue
        seen.add(sel)
        try:
            el = soup.select_one(sel)
            if el and len(el.get_text(strip=True)) > 200:
                return el
        except: pass
    
    # Fallback: body
    body = soup.find('body')
    return body

# ============ PDF生成 ============
def generate_pdf(content_elem, title, output_path):
    if content_elem is None:
        return False, "无内容"
    
    # 提取段落
    paragraphs = []
    for p in content_elem.find_all(['p', 'div']):
        text = p.get_text(strip=True)
        if len(text) > 10:
            paragraphs.append(text)
    
    if not paragraphs:
        text = content_elem.get_text('\n', strip=True)
        paragraphs = [t.strip() for t in text.split('\n') if len(t.strip()) > 10]
    
    if not paragraphs:
        return False, "无段落"
    
    # 创建PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    if FONT_PATH:
        pdf.add_font('CN', '', FONT_PATH, uni=True)
        pdf.add_font('CNB', '', FONT_PATH, uni=True)
        
        # 标题
        pdf.set_font('CNB', '', 14)
        pdf.multi_cell(0, 10, title, align='C')
        pdf.ln(5)
        
        # 正文
        pdf.set_font('CN', '', 10.5)
        for para in paragraphs[:300]:
            try:
                pdf.multi_cell(0, 5.5, para)
                pdf.ln(1.5)
            except:
                pass
    else:
        pdf.set_font('Helvetica', 'B', 12)
        pdf.multi_cell(0, 8, title[:80], align='C')
        pdf.ln(4)
        pdf.set_font('Helvetica', '', 9)
        for para in paragraphs[:300]:
            try:
                safe = para.encode('latin-1', errors='replace').decode('latin-1')
                pdf.multi_cell(0, 5, safe)
                pdf.ln(1)
            except:
                pass
    
    try:
        pdf.output(output_path)
        size_mb = os.path.getsize(output_path) / 1024
        if size_mb < 5:  # 太小，可能失败
            return False, f"PDF太小({size_mb:.0f}KB)"
        return True, f"{size_mb:.0f}KB"
    except Exception as e:
        return False, f"PDF写入失败: {e}"

# ============ 主流程 ============
def process_url(entry):
    pid = entry['pid']
    title = entry['title']
    url = entry['url']
    
    out_path = PDF_DIR / f"{pid}_{re.sub(r'[\\/:*?\"<>|]', '', title[:40])}.pdf"
    
    msg = f"[{pid}] {title[:40]}"
    print(msg)
    
    # 直接PDF下载
    if url.lower().endswith('.pdf'):
        try:
            resp = SESSION.get(url, timeout=60)
            ct = resp.headers.get('Content-Type', '').lower()
            if resp.status_code == 200:
                with open(out_path, 'wb') as f:
                    f.write(resp.content)
                size = os.path.getsize(out_path)
                if size > 5000:
                    LOG.append(f"✅ {pid} 直接PDF {size//1024}KB")
                    print(f"  ✅ 直接PDF下载 {size//1024}KB")
                    return True
        except Exception as e:
            pass
    
    # 获取HTML页面
    try:
        resp = SESSION.get(url, timeout=25, allow_redirects=True)
        if resp.status_code != 200:
            LOG.append(f"❌ {pid} HTTP {resp.status_code}")
            print(f"  ❌ HTTP {resp.status_code}")
            return False
        
        ct = resp.headers.get('Content-Type', '')
        if 'pdf' in ct.lower():
            with open(out_path, 'wb') as f:
                f.write(resp.content)
            return True
        
        # 提取内容
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # 先找PDF链接
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith('.pdf'):
                pdf_url = href if href.startswith('http') else f"{url.rsplit('/',1)[0]}/{href}"
                try:
                    pdf_resp = SESSION.get(pdf_url, timeout=30)
                    if pdf_resp.status_code == 200 and len(pdf_resp.content) > 5000:
                        with open(out_path, 'wb') as f:
                            f.write(pdf_resp.content)
                        LOG.append(f"✅ {pid} 页面PDF {os.path.getsize(out_path)//1024}KB")
                        print(f"  ✅ 从页面找到PDF")
                        return True
                except:
                    continue
        
        # 提取正文生成PDF
        content = extract_content(soup, url)
        ok, reason = generate_pdf(content, title, out_path)
        LOG.append(f"{'✅' if ok else '❌'} {pid} {reason}")
        print(f"  {'✅' if ok else '❌'} {reason}")
        return ok
        
    except Exception as e:
        LOG.append(f"❌ {pid} 异常: {str(e)[:60]}")
        print(f"  ❌ {str(e)[:60]}")
        return False

# ============ 主程序 ============
print("=" * 60)
print("批量PDF生成器 v2")
print("=" * 60)

with open(CSV, 'r', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

# 已有合格PDF
pdf_dir = BASE / "obsidian-vault/附件/原文PDF"
existing = set(f.name.split("_")[0] for f in pdf_dir.glob("P*.pdf"))
bad = {'P004','P006','P009','P015','P016','P017','P018','P019',
       'P021','P024','P026','P028','P030','P034','P035','P036',
       'P039','P040','P045','P047'}

entries_to_process = []
for r in rows:
    pid = r['编号']
    url = r.get('官方来源', '').strip()
    if not url:
        continue
    if pid not in existing or pid in bad:
        entries_to_process.append({
            'pid': pid,
            'title': r['文件名称'].strip(),
            'url': url,
        })

print(f"需处理: {len(entries_to_process)} 条\n")

success, fail = 0, 0
for i, entry in enumerate(entries_to_process):
    if process_url(entry):
        success += 1
    else:
        fail += 1
    if i < len(entries_to_process) - 1:
        time.sleep(2)

print(f"\n{'=' * 60}")
print(f"完成! 成功: {success}, 失败: {fail}")

# 保存日志
log_path = BASE / "pdf批量下载日志.log"
with open(log_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(LOG))
print(f"日志: {log_path}")
