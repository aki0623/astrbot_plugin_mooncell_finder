import asyncio
import io
import sys
from playwright.async_api import async_playwright
# 假设这是你的基础库
from .base import * 
from astrbot.api import logger

# === 截图模块：指令纹章主表 ===
async def screenshot_cc_main_table(page, safe_name):
    logger.info("[-] 正在截取 [指令纹章信息]...")
    try:
        # 定位主表格
        # Mooncell 的纹章详情在 class 为 "wikitable nomobile" 的表格中
        locator = page.locator("table.wikitable.nomobile").first
        
        if await locator.count() > 0:
            await locator.scroll_into_view_if_needed()
            
            # --- 特殊处理：展开解说文本 ---
            # 纹章的解说文本类名通常是 "指令纹章_日文解说_ID_1"
            # 我们需要匹配这个类名并移除 max-height 限制
            await page.evaluate("""() => {
                const table = document.querySelector('table.wikitable.nomobile');
                if (table) {
                    // 1. 查找表格内所有带有 overflow-y 的 div 或者类名包含 '指令纹章_日文解说' 的 div
                    const scrollableDivs = table.querySelectorAll('div[style*="overflow-y"], div[class*="指令纹章_日文解说"]');
                    scrollableDivs.forEach(div => {
                        div.style.maxHeight = 'none';   // 移除高度限制
                        div.style.overflowY = 'visible'; // 移除滚动条
                        div.style.height = 'auto';      // 自适应高度
                    });
                    
                    // 2. 确保中文解说可见 (通常以 _1 结尾的是中文)
                    const cnDivs = table.querySelectorAll('div[class*="_1"]');
                    cnDivs.forEach(div => div.style.display = 'block');
                }
            }""")
            
            # 等待页面重新布局
            await asyncio.sleep(0.5)
            
            img_bytes = await locator.screenshot() 
            logger.info(f"[√] 指令纹章截图完成")
            return LibImage.open(io.BytesIO(img_bytes))
        else:
            logger.info("[!] 未找到指令纹章表格")
    except Exception as e:
        logger.info(f"[x] 指令纹章截图失败: {e}")
    return None

async def find_in_mooncell_cc_2_imglist(keyword: str):
    '''
    查找指令纹章信息的总函数
    返回截图 List
    :param keyword: 搜索字段（纹章名字）
    '''
    
    logger.info(f"[-] 正在启动浏览器搜索纹章: {keyword} ...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 纹章表格宽度适中，标准宽度即可
        context = await browser.new_context(
            viewport={"width": 1200, "height": 1200}, 
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        img_list = []
        try:
            # 获取 URL (假设复用之前的 fetch_wiki_page_raw 逻辑)
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

            # 4. 页面清洗 (隐藏广告和无关元素)
            logger.info("[-] 正在处理页面结构...")
            await page.evaluate("""() => {
                const selectors = [
                    '.ads', '#siteNotice', '#mw-panel', '#mw-head', '#footer', 
                    '.mw-editsection', '#p-personal', '#mw-navigation', 
                    '.mp-shadiao', 'ins.adsbygoogle', '#MenuSidebar',
                    '.mw-indicators', '#jump-to-nav'
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
            
            # 5. 预滚动加载图片
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.5)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.5)
            
            safe_name = "".join([c for c in keyword if c.isalpha() or c.isdigit() or c in "._-"]).strip()
            
            # === 执行截图任务 ===
            cc_img = await screenshot_cc_main_table(page, safe_name)
            if cc_img:
                img_list.append(cc_img)
            
            logger.info("[-] 纹章任务执行完毕")
            
        except Exception as e:
            logger.info(f"[x] 发生错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
        
        return img_list

if __name__ == "__main__":
    # asyncio.run(find_in_mooncell_cc_2_imglist("藤香御局"))
    pass