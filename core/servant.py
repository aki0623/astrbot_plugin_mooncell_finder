import asyncio

from playwright.async_api import async_playwright

from astrbot.api import logger

from .base import *


# === 截图模块：基础数值 ===
async def screenshot_base_stats(page, prefix):

    logger.info("[-] 正在截取 [基础数值]...")
    try:
        locator = locator_finder(page,"servant","base_stats")
        if await locator.count() > 0:
            await locator.scroll_into_view_if_needed()
            img_bytes = await locator.screenshot()
            logger.info("[√] 基础数值截图完成")
            return LibImage.open(io.BytesIO(img_bytes))
        else:
            logger.info("[!] 未找到基础数值表格")
    except Exception as e:
        logger.info(f"[x] 基础数值截图失败: {e}")
    return None

# === 截图模块：宝具 ===
async def screenshot_noble_phantasm(page, prefix):
    logger.info("[-] 正在截取 [宝具]...")
    try:
        locator = locator_finder(page,"servant","noble_phantasm")
        if await locator.count() > 0:
            await locator.scroll_into_view_if_needed()
            img_bytes = await locator.screenshot()
            logger.info("[√] 宝具截图完成")
            return LibImage.open(io.BytesIO(img_bytes))
        else:
            logger.info("[!] 未找到宝具表格")
    except Exception as e:
        logger.info(f"[x] 宝具截图失败: {e}")
    return None
async def find_in_mooncell_servant_2_imglist(keyword: str):
    """
    查找从者的信息的总函数
    返回从者信息截图Img：
        基础数值、宝具、技能（持有技能、职阶技能、追加技能）、素材需求
    :param keyword: 搜索字段（从者名字）
    :type keyword: str
    """


    logger.info(f"[-] 正在启动浏览器搜索: {keyword} ...")

    async with async_playwright() as p:
        # 使用辅助函数初始化浏览器
        browser, context, page = await init_browser(p)
        img_list = []
        try:
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

            # 4. 页面清洗与重构
            logger.info("[-] 正在处理页面结构...")
            # 先使用通用的页面清洗
            await clean_page(page)
            # 再执行从者页面特有的处理
            await page.evaluate("""
            () => {
                // 1. 强制展开所有 Tabber
                document.querySelectorAll('.tabber__panel').forEach(tab => {
                    tab.style.display = 'block'; 
                    tab.style.opacity = '1';
                    tab.classList.remove('tabber__panel--hidden'); 
                });
                
                // 2. 移除 Tab 父容器固定高度
                document.querySelectorAll('.tabber__section').forEach(sec => {
                    sec.style.height = 'auto'; 
                    sec.style.maxHeight = 'none';
                });

                // 3. 隐藏 Tab 切换按钮
                document.querySelectorAll('ul.tabber__tabs').forEach(h => h.style.display = 'none');
            }
            """)

            # 5. 预滚动
            logger.info("[-] 正在预滚动以加载资源...")
            await pre_scroll(page)

            safe_name = "".join([c for c in keyword if c.isalpha() or c.isdigit() or c in "._-"]).strip()




            # === 执行截图任务 ===
            base_stats_img = await screenshot_base_stats(page, safe_name)
            img_list.append(base_stats_img)
            noble_phantasm_img = await screenshot_noble_phantasm(page, safe_name)
            img_list.append(noble_phantasm_img)
            # === 三大技能分类截图 ===

            # 1. 持有技能 (H3)
            # 停止条件: 下一个 H2 或 H3
            j1_img = await capture_section_smart(
                page, safe_name, "03_持有技能",
                start_text="持有技能",
                stop_levels=["H2", "H3"]
            )
            img_list.append(j1_img)
            # 2. 职阶技能 (H3)
            # 停止条件: 下一个 H2 或 H3
            j2_img = await capture_section_smart(
                page, safe_name, "04_职阶技能",
                start_text="职阶技能",
                stop_levels=["H2", "H3"]
            )
            img_list.append(j2_img)
            # 3. 追加技能 (H3)
            # 停止条件: 下一个 H2 (通常是"素材需求") 或 H3
            j3_img = await capture_section_smart(
                page, safe_name, "05_追加技能",
                start_text="追加技能",
                stop_levels=["H2", "H3"]
            )
            img_list.append(j3_img)
            # 4. 素材需求 (H2)
            # 注意：这里 stop_levels 只有 ['H2']，表示会包含内部的 H3 小标题（灵基再临等）
            marerial_img = await capture_section_smart(
                page, safe_name, "06_素材需求",
                start_text="素材需求",
                stop_levels=["H2"]
            )
            img_list.append(marerial_img)
            logger.info("[-] 所有任务执行完毕")

        except Exception as e:
            logger.info(f"[x] 发生错误: {e}")
        finally:
            await browser.close()

        return img_list

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        try:
            query = input("请输入搜索关键词 (例如 'C呆'): ").strip()
        except UnicodeDecodeError:
            return
    if not query:
        return
    asyncio.run(find_in_mooncell_servant_2_imglist(query))

if __name__ == "__main__":
    main()
