import asyncio
import io
import sys
from playwright.async_api import async_playwright
# 假设这是你的基础库
from .base import * 
from astrbot.api import logger

# === 截图模块：特性一览表格 ===
async def screenshot_trait_table(page):
    logger.info("[-] 正在截取 [特性一览]...")
    try:
        # 策略：寻找 class 为 wikitable 且包含文本 "特性一览" 的表格
        # Mooncell 的属性页面中，这个表格包含了所有该属性相关的交叉特性
        target_table = page.locator("table.wikitable").filter(has_text="特性一览").first
        
        if await target_table.count() > 0:
            await target_table.scroll_into_view_if_needed()
            
            # === 关键步骤：强制展开折叠内容 ===
            # 你的 HTML 显示行带有 id="mw-customcollapsible-000" 和 class="mw-collapsible"
            # 默认情况下它们可能是折叠的 (display: none)。
            # 我们通过 JS 强制将该表格内的所有行设置为可见，防止截图内容缺失。
            await page.evaluate("""(table) => {
                // 1. 找到表格内所有被标记为可折叠的行
                const rows = table.querySelectorAll('tr.mw-collapsible');
                rows.forEach(row => {
                    // 强制显示
                    row.style.display = 'table-row';
                    row.classList.remove('mw-collapsed');
                });
                
                // 2. (可选) 隐藏原本的 [展开/折叠] 按钮文字，让截图更干净
                const toggle = table.querySelector('.mw-customtoggle');
                if(toggle) {
                    const spans = toggle.querySelectorAll('span.mw-collapsible');
                    spans.forEach(s => s.style.display = 'none');
                }
            }""", await target_table.element_handle())
            
            # 等待渲染更新（防止展开动画未完成）
            await asyncio.sleep(0.5)
            
            img_bytes = await target_table.screenshot() 
            logger.info(f"[√] 特性一览截图完成")
            return LibImage.open(io.BytesIO(img_bytes))
        else:
            logger.info("[!] 未找到特性一览表格")
    except Exception as e:
        logger.info(f"[x] 特性一览截图失败: {e}")
    return None

async def find_in_mooncell_trait_2_imglist_table(keyword: str):
    '''
    查找属性/特性的总函数
    :param keyword: 搜索字段（例如 "秩序·善", "龙", "神性"）
    '''
    
    # Mooncell 的属性页面通常是以 "属性：" 或 "特性：" 开头，或者直接是特性名
    # 这里建议在调用前处理一下关键词，或者直接搜索让 Wiki 重定向
    logger.info(f"[-] 正在启动浏览器搜索特性: {keyword} ...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 属性表格通常比较宽，设置宽一点的视口
        context = await browser.new_context(
            viewport={"width": 1200, "height": 1200}, 
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        img_list = []
        try:
            # 这里的 fetch_wiki_page_raw 应该返回类似 https://fgo.wiki/w/属性：秩序·善 的 URL
            result = await fetch_wiki_page_raw(keyword)
            if isinstance(result, dict) and "error" in result:
                logger.info(f"[x] 获取 URL 失败: {result['error']}")
                return
            url = result
            logger.info(f"[-] 访问 URL: {url}")
            
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            try:
                await page.wait_for_selector("#bodyContent", state="visible", timeout=10000)
            except:
                logger.info("[!] 警告: 等待内容区域超时")

            # 4. 页面清洗
            logger.info("[-] 正在处理页面结构...")
            await page.evaluate("""() => {
                const selectors = [
                    '.ads', '#siteNotice', '#mw-panel', '#mw-head', '#footer', 
                    '.mw-editsection', '#p-personal', '#mw-navigation', 
                    '.mp-shadiao', 'ins.adsbygoogle', '#MenuSidebar',
                    '#toc', '.toc' // 目录通常不需要
                ];
                selectors.forEach(s => {
                    document.querySelectorAll(s).forEach(e => e.style.display = 'none');
                });
                
                const content = document.querySelector('#content');
                if(content) {
                    content.style.marginLeft = '0px';
                    content.style.padding = '10px';
                }
            }""")
            
            # 5. 预滚动
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.5)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.5)
            
            # === 执行截图任务 ===
            trait_img = await screenshot_trait_table(page)
            if trait_img:
                img_list.append(trait_img)
            
            logger.info("[-] 特性任务执行完毕")
            
        except Exception as e:
            logger.info(f"[x] 发生错误: {e}")
        finally:
            await browser.close()
        
        return img_list

# === 截图模块：特性页面特定部分 ===
async def screenshot_trait_sections(page):
    img_list = []
    
    # --- 任务 1: 截取 [基础统计表格] (保持不变) ---
    logger.info("[-] 正在截取 [基础统计表格]...")
    try:
        stats_table = page.locator("table.wikitable").first
        if await stats_table.count() > 0:
            await stats_table.scroll_into_view_if_needed()
            img_bytes = await stats_table.screenshot()
            img_list.append(LibImage.open(io.BytesIO(img_bytes)))
            logger.info("[√] 基础统计表格截图完成")
    except Exception as e:
        logger.info(f"[x] 基础统计表格截图失败: {e}")

    # --- 任务 2: 截取 [完整从者列表] ---
    logger.info("[-] 正在截取 [完整从者列表]...")
    try:
        # === 核心修改：JS 注入 ===
        await page.evaluate("""() => {
            // 1. 处理半折叠容器：去高度限制 + 【去遮罩渐变】
            const wrappers = document.querySelectorAll('.template-semicollapse-content');
            wrappers.forEach(div => {
                div.style.maxHeight = 'none';     // 移除高度限制
                div.style.overflowY = 'visible';  // 移除滚动条
                div.style.height = 'auto';        // 自适应高度
                
                // [关键修改] 移除白色渐变遮罩
                div.style.webkitMaskImage = 'none'; 
                div.style.maskImage = 'none';
            });

            // 2. 隐藏 "显示全部内容" 按钮
            document.querySelectorAll('.template-semicollapse-button').forEach(b => b.style.display = 'none');

            // 3. 强制展开底部的 "在部分条件时持有..." 行
            const condRow = document.getElementById('mw-customcollapsible-cond');
            if (condRow) {
                condRow.style.display = 'table-row';
                condRow.classList.remove('mw-collapsed');
            }
            
            // 4. 暴力展开表格内其他可能存在的折叠行
            const allHiddenRows = document.querySelectorAll('tr.mw-collapsible.mw-collapsed');
            allHiddenRows.forEach(row => {
                row.style.display = 'table-row';
                row.classList.remove('mw-collapsed');
            });

            // 5. 移除 [展开/折叠] 的文字按钮，让表格看起来更干净
            const toggles = document.querySelectorAll('.mw-customtoggle, .mw-collapsible-toggle');
            toggles.forEach(t => t.style.display = 'none'); // 直接隐藏点击区域，防止残留文字

            // 6. 强制触发图片懒加载
            const images = document.querySelectorAll('img[loading="lazy"]');
            images.forEach(img => img.removeAttribute('loading'));
        }""")
        
        # 等待页面重绘和图片加载
        await asyncio.sleep(0.8)

        # 定位目标表格
        target_table = page.locator("#tabber-持有该属性的从者 table.wikitable.logo").first
        
        # 容错：如果找不到特定 ID，尝试模糊匹配
        if await target_table.count() == 0:
            target_table = page.locator("table.wikitable.logo").filter(has_text="Saber").first

        if await target_table.count() > 0:
            await target_table.scroll_into_view_if_needed()
            # 再次等待，确保底部文字渲染清晰
            await asyncio.sleep(0.5)
            
            img_bytes = await target_table.screenshot()
            img_list.append(LibImage.open(io.BytesIO(img_bytes)))
            logger.info("[√] 完整从者列表截图完成")
        else:
            logger.info("[!] 未找到从者列表表格")
            
    except Exception as e:
        logger.info(f"[x] 从者列表截图失败: {e}")

    return img_list
async def find_in_mooncell_trait_2_imglist(keyword: str):
    logger.info(f"[-] 正在启动浏览器搜索特性: {keyword} ...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 1200}, # 宽度适中
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        img_list = []
        try:
            result = await fetch_wiki_page_raw(keyword)
            if isinstance(result, dict) and "error" in result:
                return
            url = result
            logger.info(f"[-] 访问 URL: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 基础页面清洗
            await page.evaluate("""() => {
                const selectors = ['.ads', '#siteNotice', '#mw-panel', '#mw-head', '#footer', '.mw-editsection', '#p-personal', '#mw-navigation', '.mp-shadiao', 'ins.adsbygoogle', '#MenuSidebar', '#toc'];
                selectors.forEach(s => document.querySelectorAll(s).forEach(e => e.style.display = 'none'));
                const content = document.querySelector('#content');
                if(content) { content.style.marginLeft = '0px'; content.style.padding = '10px'; }
            }""")
            
            # 截图
            screenshots = await screenshot_trait_sections(page)
            if screenshots:
                img_list.extend(screenshots)
                
        except Exception as e:
            logger.info(f"[x] 发生错误: {e}")
        finally:
            await browser.close()
        return img_list

if __name__ == "__main__":
    # 测试代码
    asyncio.run(find_in_mooncell_trait_2_imglist("属性：秩序·善"))
    asyncio.run(find_in_mooncell_trait_2_imglist_table("属性：秩序·善"))
    pass