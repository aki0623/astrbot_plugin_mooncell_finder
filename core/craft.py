import asyncio
import io

from playwright.async_api import async_playwright

from astrbot.api import logger

from .base import *


# === 截图模块：概念礼装主表 ===
async def screenshot_ce_main_table(page, safe_name):
    logger.info("[-] 正在截取 [概念礼装信息]...")
    try:
        # 定位桌面版的主表格
        # Mooncell 的礼装详情通常在一个 class 为 "wikitable nomobile" 的表格中
        locator = page.locator("table.wikitable.nomobile").first

        if await locator.count() > 0:
            await locator.scroll_into_view_if_needed()

            # --- 特殊处理：展开解说文本 ---
            # 礼装解说文本通常被限制了高度 (max-height: 350px) 并带有滚动条
            # 我们需要移除这些限制以截取完整文本
            await page.evaluate("""() => {
                const table = document.querySelector('table.wikitable.nomobile');
                if (table) {
                    // 查找表格内所有带有 overflow-y 的 div (通常是解说文本)
                    const scrollableDivs = table.querySelectorAll('div[style*="overflow-y"], div[class*="概念礼装_日文解说"]');
                    scrollableDivs.forEach(div => {
                        div.style.maxHeight = 'none';
                        div.style.overflowY = 'visible';
                        div.style.height = 'auto';
                    });
                }
            }""")
            # 等待渲染更新
            await asyncio.sleep(0.5)

            img_bytes = await locator.screenshot()
            logger.info("[√] 概念礼装截图完成")
            return LibImage.open(io.BytesIO(img_bytes))
        else:
            logger.info("[!] 未找到概念礼装表格")
    except Exception as e:
        logger.info(f"[x] 概念礼装截图失败: {e}")
    return None

async def find_in_mooncell_ce_2_imglist(keyword: str):
    """
    查找概念礼装信息的总函数
    返回截图 List (通常只有一张包含所有信息的长图)
    :param keyword: 搜索字段（礼装名字）
    """

    logger.info(f"[-] 正在启动浏览器搜索礼装: {keyword} ...")

    async with async_playwright() as p:
        # 使用辅助函数初始化浏览器，设置更宽的视口以适应礼装表格
        browser, context, page = await init_browser(p, viewport_width=1400, viewport_height=1200)
        img_list = []
        try:
            # 假设 fetch_wiki_page_raw 是你 base.py 里获取 Mooncell 搜索结果 URL 的函数
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
            await clean_page(page)

            # 5. 预滚动加载图片
            logger.info("[-] 正在预滚动以加载资源...")
            await pre_scroll(page)

            safe_name = "".join([c for c in keyword if c.isalpha() or c.isdigit() or c in "._-"]).strip()

            # === 执行截图任务 ===
            # 礼装通常只有这一张大表
            ce_img = await screenshot_ce_main_table(page, safe_name)
            if ce_img:
                img_list.append(ce_img)

            logger.info("[-] 礼装任务执行完毕")

        except Exception as e:
            logger.info(f"[x] 发生错误: {e}")
        finally:
            await browser.close()

        return img_list

# 测试入口
if __name__ == "__main__":
    # 为了测试方便，你可以取消注释下面这行来手动运行
    asyncio.run(find_in_mooncell_ce_2_imglist("桜色の風景"))
    pass
