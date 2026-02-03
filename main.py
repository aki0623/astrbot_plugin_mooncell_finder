import io

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Node, Nodes, Plain
from astrbot.api.star import Context, Star, register
from astrbot.core.message.components import Image
from .core import ccode, craft, servant, trait
from .core.new_core import *
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from .core.base import *
from bs4 import BeautifulSoup, Tag
from astrbot.api import AstrBotConfig

# 与 _conf_schema.json 中 sub_config 的 default 保持一致，仅当配置为空时使用
DEFAULT_CMD_PREFIXES = {
    "servant": "MCF从者",
    "servant_new": "MCF从者new",
    "cc": "MCF纹章",
    "ce": "MCF礼装",
    "trait": "MCF特性",
    "test": "MCF测试",
}

@register("Mooncell Finder", "akidesuwa", "mooncell 网页查询", "0.9")
class MCF_plugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        # 从 config 只读获取自定义命令前缀（空串时使用 schema 默认值）
        sub = config.get("sub_config") or {}
        self._prefixes = {
            k: (sub.get(k) or DEFAULT_CMD_PREFIXES.get(k, ""))
            for k in DEFAULT_CMD_PREFIXES
        }
        # 定义一个字典，用于存储不同类型的图片列表获取函数
        self.img_list_func_dict = {
            "从者": servant.find_in_mooncell_servant_2_imglist,
            "礼装": craft.find_in_mooncell_ce_2_imglist,
            "纹章": ccode.find_in_mooncell_cc_2_imglist,
            "特性": trait.find_in_mooncell_trait_2_imglist,
            "特性表格": trait.find_in_mooncell_trait_2_imglist_table,
        }
        self.CSS_STYLE = """
        <style>
            body { font-family: "Microsoft YaHei", sans-serif; padding: 20px; background-color: white; }
            .wikitable {
                background-color: #f8f9fa; color: #202122; margin: 0 auto; /* 居中 */
                border: 1px solid #a2a9b1; border-collapse: collapse; width: 100%; max-width: 1000px;
            }
            .wikitable th { background-color: #eaecf0; border: 1px solid #a2a9b1; padding: 8px; font-weight: bold; text-align: center; }
            .wikitable td { border: 1px solid #a2a9b1; padding: 8px; background-color: #ffffff; text-align: center; }
            th[style*="position: relative"] { position: relative !important; }
            /* 去除可能的移动端隐藏样式 */
            .nomobile { display: table-cell !important; }
        </style>
        """
        self.render_options = {
                        # "width": 1000,          # 限制宽度，防止表格过宽
                        "device_scale_factor": 2, # 2倍缩放，图片更清晰
                        "element": ".wikitable"
                    }
        
    async def _replace_img_to_b64(self, client, element):
        """
        遍历 element 中的所有 img 标签，下载图片并转换为 base64 嵌入
        """
        if not element: return

        tasks = []
        # 查找所有图片
        imgs = element.find_all('img')
        
        async def process_one_img(img):
            # 1. 获取 URL
            src = img.get('src', '')
            if not src: return
            
            # 修复相对路径
            if src.startswith('/'):
                src = 'https://fgo.wiki' + src
            
            # 2. 移除 srcset (防止渲染器优先使用 srcset 中的外部链接)
            if 'srcset' in img.attrs:
                del img['srcset']
            if 'loading' in img.attrs:
                del img['loading']

            try:
                # 3. 使用已有的 client 下载图片
                # 注意：这里复用了 headers，能通过防盗链检查
                resp = await client.get(src, timeout=5)
                if resp.status_code == 200:
                    # 4. 转 Base64
                    b64_data = base64.b64encode(resp.content).decode('utf-8')
                    # 获取图片类型，默认为 png
                    content_type = resp.headers.get('content-type', 'image/png')
                    # 5. 替换 src
                    img['src'] = f"data:{content_type};base64,{b64_data}"
            except Exception as e:
                # 下载失败则保留原链接，不报错
                pass

        # 创建并发任务
        for img in imgs:
            tasks.append(process_one_img(img))
        
        # 并发执行所有图片下载，加快速度
        if tasks:
            await asyncio.gather(*tasks)
              
    def get_full_html_tmpl(self, table_html: str) -> str:
        full_html_tmpl = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        {self.CSS_STYLE}
                    </head>
                    <body>
                        {table_html}
                    </body>
                    </html>
                    """
        return full_html_tmpl
    
    def extract_section_content(self,soup, section_id):
        # 1. 尝试找到目标 span
        target_span = soup.find('span', id=section_id)
        if not target_span:
            return ""

        # 2. 找到父级 h3 作为起点
        start_h3 = target_span.find_parent('h3')
        if not start_h3:
            return ""

        content_buffer = []
        
        # 手动加一个带样式的标题，方便看图
        content_buffer.append(f'<h3 style="background:#eaecf0; padding:5px; border:1px solid #a2a9b1; margin-top:10px;">{section_id}</h3>')

        # 3. 遍历兄弟节点
        for sibling in start_h3.next_siblings:
            # 遇到下一个 h3 标题就停止
            if sibling.name == 'h3':
                break
            
            # 忽略非 Tag 节点 (如换行符)
            if not isinstance(sibling, Tag):
                continue

            # --- 【关键修改】 过滤掉手机版表格 ---
            # 获取当前标签的 class 列表
            css_classes = sibling.get('class', [])
            
            # 如果 class 里包含 'nodesktop'，说明这是手机版表格，直接跳过
            if 'nodesktop' in css_classes:
                continue
                
            # (可选) 如果你想更严格，可以只保留含有 'nomobile' 的 table
            if sibling.name == 'table' and 'nomobile' not in css_classes:
                continue
            # -----------------------------------

            # 4. 图片清洗逻辑 (复用之前的)
            for img in sibling.find_all('img'):
                if 'loading' in img.attrs: del img['loading']
                
                # src 修复
                if img.attrs.get('src', '').startswith('/'):
                    img['src'] = 'https://fgo.wiki' + img['src']
                
                # srcset 修复
                if 'srcset' in img.attrs:
                    new_srcset = []
                    for src_part in img['srcset'].split(','):
                        src_part = src_part.strip()
                        parts = src_part.split(' ')
                        url = parts[0]
                        if url.startswith('/'):
                            url = 'https://fgo.wiki' + url
                        
                        if len(parts) > 1:
                            new_srcset.append(f"{url} {parts[1]}")
                        else:
                            new_srcset.append(url)
                    img['srcset'] = ', '.join(new_srcset)

            # 添加到缓冲区
            content_buffer.append(str(sibling))

        return "".join(content_buffer)
    
    def extract_material_requirements(self, soup):
        # 1. 定位 "素材需求" 的 H2 标题
        # 注意：Wiki 中 id 通常在 span 上，例如 <span id="素材需求"></span>
        target_span = soup.find('span', id='素材需求')
        if not target_span:
            return ""
        
        # 获取父级 h2 标签作为起点
        start_h2 = target_span.find_parent('h2')
        if not start_h2:
            return ""

        content_buffer = []
        
        # 手动添加一个大标题
        content_buffer.append('<h2 style="border-bottom: 2px solid #a2a9b1; margin-top:20px;">素材需求</h2>')

        # 2. 遍历 H2 之后的兄弟节点
        for sibling in start_h2.next_siblings:
            # 遇到下一个 H2 标题（例如 "资料" 或 "相关礼装"）就停止
            if sibling.name == 'h2':
                break
            
            # 忽略空白字符和非 Tag 节点
            if not isinstance(sibling, Tag):
                continue

            # --- 处理子标题 (H3) ---
            if sibling.name == 'h3':
                # 获取标题文本（去除编辑按钮等杂质）
                header_text = sibling.get_text(strip=True)
                # 给子标题加个样式，使其在图片中更明显
                content_buffer.append(f'<h3 style="background:#eaecf0; padding:5px; border-left:5px solid #4487DF; margin-top:15px;">{header_text}</h3>')
                continue

            # --- 处理表格 (Table) ---
            if sibling.name == 'table':
                css_classes = sibling.get('class', [])
                
                # 【关键】过滤掉手机版表格 (nodesktop)
                # 如果不加这个，每个表格都会出现两次（一次电脑版，一次手机版）
                if 'nodesktop' in css_classes:
                    continue
                
                # (可选) 确保只抓取 class 包含 wikitable 的表格，避免抓到布局用的隐藏表格
                if 'wikitable' not in css_classes:
                    continue

                # --- 图片清洗逻辑 ---
                for img in sibling.find_all('img'):
                    # 去除懒加载
                    if 'loading' in img.attrs: del img['loading']
                    if 'decoding' in img.attrs: del img['decoding']
                    
                    # 修复 src 相对路径
                    if img.attrs.get('src', '').startswith('/'):
                        img['src'] = 'https://fgo.wiki' + img['src']
                    
                    # 修复 srcset 相对路径 (高清屏适配)
                    if 'srcset' in img.attrs:
                        new_srcset = []
                        for src_part in img['srcset'].split(','):
                            src_part = src_part.strip()
                            parts = src_part.split(' ')
                            url = parts[0]
                            if url.startswith('/'):
                                url = 'https://fgo.wiki' + url
                            
                            if len(parts) > 1:
                                new_srcset.append(f"{url} {parts[1]}")
                            else:
                                new_srcset.append(url)
                        img['srcset'] = ', '.join(new_srcset)
                
                # 将处理好的表格加入缓冲区
                content_buffer.append(str(sibling))

        return "".join(content_buffer)
    
    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        # 按配置中的命令前缀注册指令（仅读取 config，不修改）
        star_name = "Mooncell Finder"
        cmd_handlers = [
            ("servant", self.MCF_servant, "从者查询"),
            ("servant_new", self.MCF_servant_new, "从者查询(新版Wiki)"),
            ("ce", self.MCF_craft, "礼装查询"),
            ("cc", self.MCF_ccode, "纹章查询"),
            ("trait", self.MCF_event, "特性查询"),
        ]
        for key, handler, desc in cmd_handlers:
            prefix = self._prefixes.get(key, "")
            if prefix:
                self.context.register_commands(
                    star_name, prefix, desc, 5, handler,
                )
        logger.info("Mooncell Finder插件已初始化")

    async def fetch_wiki_htmls_servant(self, url: str):
        '''
        抓取从者界面基础信息、宝具、技能、培养材料
        '''
        str_tables = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            try:
                resp = await client.get(url, timeout=20)
                if resp.status_code != 200: return None
                
                soup = BeautifulSoup(resp.text, 'html.parser')

                # ================= 1. 基础信息 =================
                table1 = soup.find('table', class_='wikitable nomobile graphpicker-container')
                if not table1: 
                    # logger.info(f"抓取基本信息失败。")
                    pass
                else:
                    # 【关键】调用 Base64 转换
                    await self._replace_img_to_b64(client, table1)
                    str_tables.append(str(table1))

                # ================= 2. 宝具信息 =================
                core_table = soup.find('table', class_='wikitable nomobile logo')
                np_section = None
                
                # 定位宝具所在的 Tab 区域
                if core_table:
                    np_section = core_table.find_parent('section', class_='tabber__section')
                if not np_section:
                    np_section = soup.find('section', class_='tabber__section')
                
                if not np_section:
                    # logger.info(f"抓取宝具信息失败。")
                    pass
                else:
                    # 提取样式
                    styles = "".join([str(tag) for tag in np_section.find_all('style')])
                    # 筛选电脑版表格
                    target_tables = np_section.find_all('table', class_=lambda x: x and 'nomobile' in x)
                    
                    cleaned_html_parts = [styles]
                    for table in target_tables:
                        # 【关键】调用 Base64 转换
                        await self._replace_img_to_b64(client, table)
                        cleaned_html_parts.append(str(table))
                        cleaned_html_parts.append("<br>") 
                    
                    final_np_html = "".join(cleaned_html_parts)
                    str_tables.append(final_np_html)
                    
                # ================= 3. 技能信息 =================
                # 注意：extract_section_content 返回的是字符串，我们需要先处理 SOUP 再提取，或者修改那个函数
                # 为了不改动太多，这里建议直接在 soup 上处理完再提取，或者临时处理
                
                # 方案：先找到技能的 DOM 节点，转 Base64，再转字符串
                # 但由于你之前的 extract_section_content 逻辑是遍历兄弟节点，比较复杂
                # 这里推荐修改 extract_section_content 让其接受 client 并执行 await self._replace_img_to_b64
                
                # 既然之前的函数是同步的，这里我们手动处理一下：
                # 简单的做法是：技能部分图片较少，我们可以在这里直接对 soup 中特定的 ID 区域做一次全量转换
                # 但为了性能，我们假设你在 extract_section_content 里返回的是 html 字符串
                # 那么图片就会裂。所以必须把 extract_section_content 改成异步或者在这里处理。
                
                # 推荐：简单粗暴地对整个 soup 里的技能部分进行预处理（如果性能允许）
                # 或者：
                
                # 3.1 持有技能
                skill_doms = self.extract_section_dom(soup, "持有技能") # 需要你稍微改写一下原来的函数，让它返回 DOM 列表而不是 str
                if skill_doms:
                    for tag in skill_doms: await self._replace_img_to_b64(client, tag)
                    str_tables.append("".join([str(t) for t in skill_doms]))
                
                # 3.2 职阶技能
                class_skill_doms = self.extract_section_dom(soup, "职阶技能")
                if class_skill_doms:
                    for tag in class_skill_doms: await self._replace_img_to_b64(client, tag)
                    str_tables.append("".join([str(t) for t in class_skill_doms]))

                # 3.3 追加技能
                innate_doms = self.extract_section_dom(soup, "追加技能")
                if innate_doms:
                    for tag in innate_doms: await self._replace_img_to_b64(client, tag)
                    str_tables.append("".join([str(t) for t in innate_doms]))

                # ================= 4. 素材需求 =================
                # 同样建议修改 extract_material_requirements 返回 DOM
                mats_dom = self.extract_material_requirements_dom(soup)
                if mats_dom:
                     await self._replace_img_to_b64(client, mats_dom)
                     str_tables.append(str(mats_dom))

                return str_tables
            except Exception as e:
                # logger.info(f"爬取错误: {e}")
                print(f"爬取错误: {e}") # 调试用
                return None
    
    def extract_section_dom(self, soup, section_id):
        """返回 DOM 列表而不是字符串"""
        target_span = soup.find('span', id=section_id)
        if not target_span: return []
        start_h3 = target_span.find_parent('h3')
        if not start_h3: return []

        dom_list = []
        # 添加标题头（手动创建 Tag）
        header = soup.new_tag('h3', style="background:#eaecf0; padding:5px; border:1px solid #a2a9b1; margin-top:10px;")
        header.string = section_id
        dom_list.append(header)

        from bs4 import Tag
        for sibling in start_h3.next_siblings:
            if sibling.name == 'h3': break
            if not isinstance(sibling, Tag): continue
            
            css_classes = sibling.get('class', [])
            if 'nodesktop' in css_classes: continue # 过滤手机版
            
            dom_list.append(sibling)
        return dom_list

    def extract_material_requirements_dom(self, soup):
        """返回一个包裹了所有素材内容的 div Tag"""
        target_span = soup.find('span', id='素材需求')
        if not target_span: return None
        start_h2 = target_span.find_parent('h2')
        if not start_h2: return None

        # 创建一个容器 div 来装所有内容
        container = soup.new_tag('div')
        
        # 添加大标题
        header = soup.new_tag('h2', style="border-bottom: 2px solid #a2a9b1; margin-top:20px;")
        header.string = "素材需求"
        container.append(header)

        from bs4 import Tag
        for sibling in start_h2.next_siblings:
            if sibling.name == 'h2': break
            if not isinstance(sibling, Tag): continue

            # 复制节点以防修改原 DOM 结构破坏迭代（虽然这里是一次性读取）
            # 但为了安全，直接 append sibling 会把它从原树中移动过来，这也是可以的
            
            # 过滤手机版
            if sibling.name == 'table':
                if 'nodesktop' in sibling.get('class', []): continue
            
            # 美化 H3
            if sibling.name == 'h3':
                sibling['style'] = "background:#eaecf0; padding:5px; border-left:5px solid #4487DF; margin-top:15px;"
            
            container.append(sibling)
            
        return container
    
    async def _send_msg_func(self,event,image_list,key,keyword):
        """消息发送指令,用于发送合并转发消息。"""
        if keyword:
            msg1 = f"正在查找{key}:{keyword}。"
            msg2 = f"已为您找到{key}-{keyword}的详细信息如下："
        else:
            if key == "特性":
                msg1 = "正在查找【特性一览】表格。"
                msg2 = "已为您找到【特性一览】表格如下："

        yield event.plain_result(msg1)
        # 准备合并转发的节点列表
        nodes = []
        # 1. 创建第一个节点：文字说明
        text_node = Node(
            uin=event.get_self_id(),
            name="Mooncell 查找结果",
            content=[Plain(msg2)]
        )
        nodes.append(text_node)
        # 2. 遍历图片并放入节点
        if image_list:
            for img in image_list:
                if img is None:
                    continue

                # PIL Image -> Bytes
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                img_bytes = buf.getvalue()

                # 创建图片节点
                # 注意：content 列表里直接放 Image 对象，不要套在 Plain 里面
                img_node = Node(
                    uin=event.get_self_id(),
                    name="Mooncell 数据截图",
                    content=[Image.fromBytes(img_bytes)]
                )
                nodes.append(img_node)
        else:
            # 如果没搜到，添加一个提示节点
            nodes.append(Node(
                uin=event.get_self_id(),
                name="查找失败",
                content=[Plain(f"抱歉，未能在 Mooncell 找到该{key}的相关截图。")]
            ))

        # 3. 封装并发送合并转发消息
        merge_forward_message = Nodes(nodes)
        yield event.chain_result([merge_forward_message])
        yield event.plain_result("查找完毕。")

    async def _send_msg_func_new(self,event,img_urls,key,keyword):
        """消息发送指令,用于发送合并转发消息。"""
        if keyword:
            msg1 = f"正在查找{key}:{keyword}。"
            msg2 = f"已为您找到{key}-{keyword}的详细信息如下："
        else:
            if key == "特性":
                msg1 = "正在查找【特性一览】表格。"
                msg2 = "已为您找到【特性一览】表格如下："

        yield event.plain_result(msg1)
        # 准备合并转发的节点列表
        nodes = []
        # 1. 创建第一个节点：文字说明
        text_node = Node(
            uin=event.get_self_id(),
            name="Mooncell 查找结果",
            content=[Plain(msg2)]
        )
        nodes.append(text_node)
        # 2. 遍历图片并放入节点
        if img_urls:
            for img_url in img_urls:
                if img_url is None:
                    continue
                img_node = Node(
                    uin=event.get_self_id(),
                    name="Mooncell 数据截图",
                    content=[Image.fromURL(img_url)]
                )
                nodes.append(img_node)
        else:
            # 如果没搜到，添加一个提示节点
            nodes.append(Node(
                uin=event.get_self_id(),
                name="查找失败",
                content=[Plain(f"抱歉，未能在 Mooncell 找到该{key}的相关截图。")]
            ))

        # 3. 封装并发送合并转发消息
        merge_forward_message = Nodes(nodes)
        yield event.chain_result([merge_forward_message])
        yield event.plain_result("查找完毕。")

    async def MCF_servant(self, event: AstrMessageEvent):
        """从者查询指令,用于查询FGO相关的从者信息。"""
        prefix = self._prefixes.get("servant", "MCF从者")
        message_str = event.message_str
        message_chain = event.get_messages()
        logger.info(message_chain)
        keyword = message_str.replace(prefix, "", 1).strip()
        if keyword:
            image_list = await self.img_list_func_dict["从者"](keyword)
            logger.info("得到image_list")
            async for msg in self._send_msg_func(event, image_list, "从者", keyword):
                yield msg
            logger.info("成功发送")
        else:
            yield event.plain_result("从者查询关键词不可为空。")

    async def MCF_servant_new(self, event: AstrMessageEvent):
        """从者查询指令,用于查询FGO相关的从者信息。"""
        prefix = self._prefixes.get("servant_new", "MCF从者new")
        message_str = event.message_str
        message_chain = event.get_messages()
        logger.info(message_chain)
        keyword = message_str.replace(prefix, "", 1).strip()
        if keyword:
            logger.info(f"[-] 正在启动浏览器搜索: {keyword} ...")
            async with async_playwright() as p:
                # 使用辅助函数初始化浏览器
                browser, context, page = await init_browser(p)
                try:
                    result = await fetch_wiki_page_raw(keyword)
                    if isinstance(result, dict) and "error" in result:
                        logger.info(f"[x] 获取 URL 失败: {result['error']}")
                        return
                    target_url = result
                    logger.info(f"[-] 访问 URL: {target_url}")
                    raw_table_htmls = await self.fetch_wiki_htmls_servant(target_url)
                    img_urls = []
                    if not raw_table_htmls:
                        yield event.plain_result("未找到相关数据或解析失败。")
                        return
                    try:
                        for raw_table_html in raw_table_htmls:
                            img_url = await self.html_render(self.get_full_html_tmpl(raw_table_html), {}, options=self.render_options)
                            img_urls.append(img_url)
                    except Exception as e:
                        yield event.plain_result(f"渲染图片出错: {e}")
                    async for msg in self._send_msg_func_new(event, img_urls, "从者", keyword):
                        yield msg
                except Exception as e:
                    logger.info(f"[x] 发生错误: {e}")
                finally:
                    await browser.close()

    async def MCF_craft(self, event: AstrMessageEvent):
        """礼装查询指令,用于查询FGO相关的礼装信息。"""
        prefix = self._prefixes.get("ce", "MCF礼装")
        message_str = event.message_str
        message_chain = event.get_messages()
        logger.info(message_chain)
        keyword = message_str.replace(prefix, "", 1).strip()
        if keyword:
            image_list = await self.img_list_func_dict["礼装"](keyword)
            logger.info("得到image_list")
            async for msg in self._send_msg_func(event, image_list, "礼装", keyword):
                yield msg
            logger.info("成功发送")
        else:
            yield event.plain_result("礼装查询关键词不可为空。")

    async def MCF_ccode(self, event: AstrMessageEvent):
        """纹章查询指令,用于查询FGO相关的纹章信息。"""
        prefix = self._prefixes.get("cc", "MCF纹章")
        message_str = event.message_str
        message_chain = event.get_messages()
        logger.info(message_chain)
        keyword = message_str.replace(prefix, "", 1).strip()
        if keyword:
            image_list = await self.img_list_func_dict["纹章"](keyword)
            logger.info("得到image_list")
            async for msg in self._send_msg_func(event, image_list, "纹章", keyword):
                yield msg
            logger.info("成功发送")
        else:
            yield event.plain_result("纹章查询关键词不可为空。")

    async def MCF_event(self, event: AstrMessageEvent):
        """特性查询指令,用于查询FGO相关的特性信息。"""
        prefix = self._prefixes.get("trait", "MCF特性")
        message_str = event.message_str
        message_chain = event.get_messages()
        logger.info(message_chain)
        keyword = message_str.replace(prefix, "", 1).strip()
        if keyword:
            image_list = await self.img_list_func_dict["特性"](keyword)
        else:
            image_list = await self.img_list_func_dict["特性表格"]("属性：秩序·善")
        logger.info("得到image_list")
        async for msg in self._send_msg_func(event, image_list, "特性", keyword):
            yield msg
        logger.info("成功发送")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        logger.info("Mooncell Finder插件已停用。")
