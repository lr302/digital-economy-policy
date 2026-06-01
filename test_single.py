#!/usr/bin/env python3
"""测试单条政策 URL 是否能用 Chrome headless 打印为 PDF"""

import subprocess
from pathlib import Path

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = "https://www.mof.gov.cn/zhengwuxinxi/caizhengwengao/2023/2023wd10/202310/t20231009_3908762.htm"
OUT = Path(r"D:\workbuddy\2026-05-29-task-1\数字经济政策知识库\obsidian-vault\附件\原文PDF\_test2.pdf")

cmd = [
    CHROME,
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-software-rasterizer",
    f"--print-to-pdf={OUT}",
    "--no-pdf-header-footer",
    "--virtual-time-budget=15000",
    URL,
]

print(f"测试 URL: {URL}")
print(f"输出文件: {OUT}")
print(f"运行 Chrome...")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
print(f"返回码: {result.returncode}")
print(f"stdout: {result.stdout[:300]}")
print(f"stderr: {result.stderr[:300]}")
if OUT.exists():
    print(f"✅ 成功! PDF 大小: {OUT.stat().st_size // 1024} KB")
else:
    print(f"❌ 失败: PDF 未生成")
