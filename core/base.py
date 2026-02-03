import asyncio
import io
import sys

import httpx

from astrbot.api import logger

# 1. 先保存原始路径，确保能找到真正的第三方库
original_path = sys.path.copy()
# 2. 导入真正的 Pillow 库并起别名
if "" in sys.path:
    sys.path.remove("") # 临时移除当前目录，防止干扰
from PIL import Image as LibImage

# === 辅助函数：处理 URL ===
def filt_url(results):
    """
    在搜索到的一组页面中选择最佳页面（最短标题页面）
    :param results: 搜索到的一组页面
    """

    best_match = min(results, key=lambda x: len(x["title"]))
    title = best_match["title"]
    page_url = f"https://fgo.wiki/w/{title}"
    return page_url

# === 获取 Wiki URL ===
async def fetch_wiki_page_raw(keyword: str):
    """
    在mooncell中使用搜索功能查找
    得到关于关键词keyword的一组页面
    :param keyword: 搜索关键词
    :type keyword: str
    """

    API_URL = "https://fgo.wiki/api.php"
    async with httpx.AsyncClient(trust_env=False) as client:
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": keyword,
            "format": "json",
            "utf8": 1,
            "srlimit": 5
        }
        try:
            search_resp = await client.get(API_URL, params=search_params)
            search_data = search_resp.json()
        except Exception as e:
            return {"found": False, "error": f"网络请求失败: {str(e)}"}

        results = search_data.get("query", {}).get("search", [])
        if not results:
            return {"found": False, "error": f"抱歉，在 Mooncell 上没找到关于 '{keyword}' 的内容。"}

        page_url = filt_url(results)
    return page_url

# === 获取 locator ===
def locator_finder(page,key1,key2):
    """
    根据目标在page中查找合适的关键词
    :param page: 网页
    :param key1: 大类，如从者、礼装等
    :param key2: 小类，如基础数值、宝具
    """

    if key1 == "servant":
        if key2 == "base_stats":
            return page.locator("table.nomobile").filter(has_text="筋力").filter(has_text="耐久").first
        elif key2 == "noble_phantasm":
            return page.locator("//h2[contains(., '宝具')]/following::table[contains(@class, 'nomobile')][1]").first
        else:
            return None
    else:
        return None

# === 辅助函数：浏览器初始化 ===
async def init_browser(playwright, viewport_width=1280, viewport_height=1200):
    """
    初始化浏览器实例
    :param playwright: playwright 实例
    :param viewport_width: 视口宽度
    :param viewport_height: 视口高度
    :return: browser, context, page
    """
    browser = await playwright.chromium.launch(
        headless=True,
        args=["--no-proxy-server"],
    )
    context = await browser.new_context(
        viewport={"width": viewport_width, "height": viewport_height},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    page = await context.new_page()
    return browser, context, page

# === 辅助函数：页面清洗 ===
async def clean_page(page):
    """
    清洗页面，移除广告和干扰元素
    :param page: 页面实例
    """
    await page.evaluate("""
    () => {
        // 1. 隐藏广告和杂项
        const selectors = [
            '.ads', '#siteNotice', '#mw-panel', '#mw-head', '#footer',
            '.mw-editsection', '#p-personal', '#mw-navigation',
            '.mp-shadiao', 'ins.adsbygoogle', '#MenuSidebar',
            '#toc', '.toc', '#jump-to-nav'
        ];
        selectors.forEach(s => {
            document.querySelectorAll(s).forEach(e => e.style.display = 'none');
        });

        const content = document.querySelector('#content');
        if(content) {
            content.style.marginLeft = '0px';
            content.style.padding = '10px';
        }
    }
    """)

# === 辅助函数：预滚动加载 ===
async def pre_scroll(page):
    """
    预滚动页面以加载资源
    :param page: 页面实例
    """
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(0.5)
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(0.5)

# === 智能截图函数：包含标题与表格，并修正标题宽度 ===
async def capture_section_smart(page, prefix, section_filename, start_text, stop_levels):
    """
    start_text: 开始标题的文本（例如 '持有技能'）
    stop_levels: 一个列表，定义遇到哪些标签时停止（例如 ['H2', 'H3']）
    """
    print(f"[-] 正在处理 [{section_filename}] (锚点: {start_text})...")

    # JS逻辑：收集元素的同时，计算表格宽度，并强制调整标题宽度
    selectors = await page.evaluate("""([startText, stopLevels]) => {
        // 1. 寻找包含特定文本的 h2 或 h3 标题
        const headers = Array.from(document.querySelectorAll('h2, h3'));
        // 优先匹配完全相等的
        let startHeader = headers.find(h => h.innerText.trim() === startText);
        // 其次尝试包含匹配
        if (!startHeader) {
            startHeader = headers.find(h => h.innerText.includes(startText));
        }

        if (!startHeader) return null;

        const capturedNodes = [];
        const capturedIds = [];

        // 辅助：添加元素ID到列表
        const addEl = (node) => {
            if (node.offsetParent !== null) { // 确保可见
                if (!node.id) node.id = 'mcp_' + Math.random().toString(36).substr(2, 9);
                capturedIds.push('#' + node.id);
                capturedNodes.push(node);
            }
        };

        // 先把起始标题加进去
        addEl(startHeader);

        let curr = startHeader.nextElementSibling;
        while (curr) {
            // 2. 检查是否遇到停止标志
            if (stopLevels.includes(curr.tagName) && curr.innerText.trim().length > 0) {
                break;
            }

            // 3. 收集目标元素 (H3标题 或 表格)

            // 如果是 H3 标题 (例如"灵基再临")，且不在停止列表中
            if (curr.tagName === 'H3' && !stopLevels.includes('H3')) {
                addEl(curr);
            }
            // 如果是目标表格
            else if (curr.tagName === 'TABLE' && curr.classList.contains('nomobile')) {
                addEl(curr);
            }
            // 如果是容器 (Tabber等)，递归查找内部
            else if (curr.children.length > 0) {
                const findInside = (node) => {
                    if (node.tagName === 'H3') {
                        addEl(node);
                    }
                    else if (node.tagName === 'TABLE' && node.classList.contains('nomobile')) {
                        addEl(node);
                    }
                    else if (node.children) {
                        Array.from(node.children).forEach(c => findInside(c));
                    }
                };
                findInside(curr);
            }

            curr = curr.nextElementSibling;
        }

        // === 【新增逻辑】计算最大宽度并调整标题 ===
        let maxWidth = 0;
        capturedNodes.forEach(node => {
            if (node.tagName === 'TABLE') {
                const rect = node.getBoundingClientRect();
                if (rect.width > maxWidth) maxWidth = rect.width;
            }
        });

        // 如果找到了表格，且宽度有效，则强制调整所有被捕获的标题宽度
        if (maxWidth > 0) {
            capturedNodes.forEach(node => {
                if (node.tagName === 'H2' || node.tagName === 'H3') {
                    // 强制修改样式
                    node.style.width = maxWidth + 'px';
                    node.style.minWidth = '0px'; // 清除可能存在的最小宽度
                    node.style.boxSizing = 'border-box'; // 防止padding导致溢出
                    node.style.display = 'block'; // 确保块级显示
                }
            });
        }

        return capturedIds;
    }""", [start_text, stop_levels])

    if selectors is None:
        print(f"    [!] 未找到标题包含 '{start_text}' 的区域")
        return

    if not selectors:
        print("    [!] 该区域下没有找到可见的内容")
        return

    print(f"    - 找到 {len(selectors)} 个相关元素，准备截图...")

    captured_images = []
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if await loc.is_visible():
                img_bytes = await loc.screenshot()
                captured_images.append(LibImage.open(io.BytesIO(img_bytes)))
        except Exception as e:
            logger.info(f"[x] 截图失败: {e}")

    if not captured_images:
        return None

    # 合并图片逻辑
    total_height = sum(img.height for img in captured_images)
    max_width = max(img.width for img in captured_images)
    padding = 5
    total_height += padding * (len(captured_images) - 1)

    merged_image = LibImage.new("RGB", (max_width, total_height), (255, 255, 255))
    current_y = 0
    for img in captured_images:
        x_offset = (max_width - img.width) // 2
        merged_image.paste(img, (x_offset, current_y))
        current_y += img.height + padding

    return merged_image # 直接返回 PIL 对象
