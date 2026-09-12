#!/usr/bin/env python3
"""
Flash Player 离线包版本自动检测脚本
功能：
1. 从官方 API 获取最新在线安装器版本
2. 从最新版本开始递减，检测哪个版本有完整离线包
3. 获取离线包大小和发布日期
4. 更新 index.html 中的嵌入数据
"""

import json
import re
import sys
import urllib.request
from datetime import datetime

API_URL = "http://api.flash.cn/config/flashVersion/"
FLASH_CDN = "https://www.flash.cn/flashplayer"
INDEX_HTML = "index.html"

# 离线包文件名映射
FILENAMES = {
    "activex": "install_flash_player_ax_cn.exe",
    "ppapi": "install_flash_player_ppapi_cn.exe",
    "npapi": "install_flash_player_cn.exe",
}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def fetch_api():
    """从官方 API 获取最新版本数据（JSONP 格式）"""
    req = urllib.request.Request(API_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        text = resp.read().decode("utf-8", errors="ignore")
    # 解析 JSONP: _flash_install_packages_({...})
    match = re.search(r"_flash_install_packages_\((.*)\)", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return json.loads(text)


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """禁止自动跟随重定向"""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_offline_url(url, timeout=10):
    """检测离线包 URL 是否可访问，返回 (status, size, last_modified)"""
    try:
        opener = urllib.request.build_opener(NoRedirectHandler)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                "Referer": "https://www.flash.cn/",
                "Range": "bytes=0-0",
            },
        )
        with opener.open(req, timeout=timeout) as resp:
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            # 必须是 exe 文件类型，且不是重定向
            if "application/x-msdownload" not in content_type and "application/octet-stream" not in content_type:
                return False, None, None
            size = None
            last_modified = None
            # 从 Content-Range 获取完整大小: bytes 0-0/22781416
            content_range = resp.headers.get("Content-Range", "")
            if "/" in content_range:
                size = int(content_range.split("/")[-1])
            last_modified = resp.headers.get("Last-Modified", "")
            # 大小必须大于 1MB 才是真正的离线包
            if size and size < 1048576:
                return False, None, None
            return status == 206 or status == 200, size, last_modified
    except urllib.error.HTTPError as e:
        # 302/301 重定向说明离线包不存在
        return False, None, None
    except Exception as e:
        return False, None, None


def version_to_num(version_str):
    """34.0.0.384 -> 3400384"""
    return version_str.replace(".", "")


def num_to_version(num_str):
    """3400384 -> 34.0.0.384"""
    s = num_str
    if len(s) == 7:
        return f"{s[0:2]}.{s[2]}.{s[3]}.{s[4:7]}"
    return s


def find_latest_offline_version(start_version_num, max_check=50):
    """从 start_version_num 开始递减，找到第一个有离线包的版本"""
    start = int(start_version_num)
    for i in range(max_check):
        ver_num = str(start - i)
        # 只检查合理的版本号（7位数字）
        if len(ver_num) != 7:
            continue
        url = f"{FLASH_CDN}/{ver_num}/{FILENAMES['activex']}"
        available, size, last_modified = check_offline_url(url)
        if available:
            print(f"  找到可用离线包版本: {num_to_version(ver_num)} ({ver_num})")
            return ver_num, size, last_modified
        if i % 10 == 0:
            print(f"  正在检测 {num_to_version(ver_num)}...")
    return None, None, None


def get_all_offline_sizes(version_num):
    """获取三个版本的离线包大小"""
    sizes = {}
    dates = {}
    for ptype, fname in FILENAMES.items():
        url = f"{FLASH_CDN}/{version_num}/{fname}"
        available, size, last_modified = check_offline_url(url)
        if available and size:
            sizes[ptype] = format_size(size)
            dates[ptype] = last_modified
    return sizes, dates


def format_size(bytes_val):
    """字节数转可读格式"""
    if bytes_val >= 1048576:
        return f"{bytes_val / 1048576:.1f}MB"
    if bytes_val >= 1024:
        return f"{bytes_val / 1024:.1f}KB"
    return f"{bytes_val}B"


def parse_date(last_modified_str):
    """解析 Last-Modified 头为 YYYY-MM-DD 格式"""
    if not last_modified_str:
        return ""
    try:
        # Tue, 09 Jun 2026 05:40:17 GMT
        dt = datetime.strptime(last_modified_str.strip(), "%a, %d %b %Y %H:%M:%S %Z")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


def update_index_html(data):
    """更新 index.html 中的 EMBEDDED_DATA"""
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    # 构建新的 EMBEDDED_DATA JSON
    new_data = {
        "version": data["online_version"],
        "versionNum": data["online_version_num"],
        "date": data["online_date"],
        "offlineVersion": data["offline_version"],
        "offlineVersionNum": data["offline_version_num"],
        "offlineVersionDate": data["offline_date"],
        "activex": {
            "size": data["online_sizes"].get("activex", "-"),
            "offlineSize": data["offline_sizes"].get("activex", "-"),
            "downloadURL": data["online_urls"].get("activex", ""),
        },
        "ppapi": {
            "size": data["online_sizes"].get("ppapi", "-"),
            "offlineSize": data["offline_sizes"].get("ppapi", "-"),
            "downloadURL": data["online_urls"].get("ppapi", ""),
        },
        "npapi": {
            "size": data["online_sizes"].get("npapi", "-"),
            "offlineSize": data["offline_sizes"].get("npapi", "-"),
            "downloadURL": data["online_urls"].get("npapi", ""),
        },
    }

    # 格式化 JSON 为 JS 对象字面量
    json_str = json.dumps(new_data, indent=2, ensure_ascii=False)
    # 替换 EMBEDDED_DATA
    pattern = r"var EMBEDDED_DATA = \{.*?\};"
    replacement = f"var EMBEDDED_DATA = {json_str};"
    new_html = re.sub(pattern, replacement, html, flags=re.DOTALL)

    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"已更新 {INDEX_HTML}")


def main():
    print("=" * 60)
    print("Flash Player 离线包版本自动检测")
    print("=" * 60)

    # 1. 获取 API 最新版本
    print("\n[1/4] 从官方 API 获取最新在线版本...")
    api_data = fetch_api()
    online_version = api_data["activex"]["version"]
    online_version_num = version_to_num(online_version)
    online_date = api_data["activex"].get("date", "")
    print(f"  在线安装器最新版本: v{online_version} ({online_version_num})")
    print(f"  发布日期: {online_date}")

    # 提取在线安装器 URL 和大小
    online_urls = {}
    online_sizes = {}
    for ptype in ["activex", "ppapi", "npapi"]:
        if ptype in api_data:
            online_urls[ptype] = api_data[ptype].get("downloadURL", "")
            online_sizes[ptype] = api_data[ptype].get("size", "-")

    # 2. 查找最新可用离线包版本
    print(f"\n[2/4] 从 v{online_version} 开始递减检测离线包...")
    offline_version_num, ax_size, ax_date = find_latest_offline_version(online_version_num)

    if not offline_version_num:
        print("  错误：未找到可用的离线包版本！")
        sys.exit(1)

    offline_version = num_to_version(offline_version_num)

    # 3. 获取所有离线包大小
    print(f"\n[3/4] 获取离线包 v{offline_version} 的详细信息...")
    offline_sizes, offline_dates = get_all_offline_sizes(offline_version_num)
    offline_date = parse_date(offline_dates.get("activex", ax_date or ""))
    print(f"  离线包版本: v{offline_version} ({offline_version_num})")
    print(f"  发布日期: {offline_date}")
    for ptype in ["activex", "ppapi", "npapi"]:
        print(f"  {ptype}: {offline_sizes.get(ptype, '-')}")

    # 4. 更新 index.html
    print(f"\n[4/4] 更新 {INDEX_HTML}...")
    data = {
        "online_version": online_version,
        "online_version_num": online_version_num,
        "online_date": online_date,
        "offline_version": offline_version,
        "offline_version_num": offline_version_num,
        "offline_date": offline_date,
        "online_urls": online_urls,
        "online_sizes": online_sizes,
        "offline_sizes": offline_sizes,
    }
    update_index_html(data)

    print("\n" + "=" * 60)
    print("检测完成！")
    print(f"  在线版: v{online_version}")
    print(f"  离线包: v{offline_version}")
    print("=" * 60)


if __name__ == "__main__":
    main()
