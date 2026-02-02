from get_html import fetch_servant_table_httpx
from html_test import raw_html1

import asyncio

html_test = raw_html1
def optimize_html_for_rendering(partial_html):
    """
    处理 HTML 片段以便生成图片。
    1. 去除 loading="lazy" (解决图片不显示问题)
    2. 注入 wikitable 的 CSS 样式 (解决没有底色和边框的问题)
    3. 封装为完整 HTML 结构 (解决中文乱码风险)
    """

    # --- 1. 去除 Lazy Loading 和异步解码 ---
    # 替换掉 loading="lazy"，强制图片立即加载
    processed_html = partial_html.replace('loading="lazy"', '')
    # 顺手去掉 decoding="async"，防止旧版渲染内核出现时序问题
    processed_html = processed_html.replace('decoding="async"', '')

    # --- 2. 定义 CSS 样式 (复刻 FGO Wiki 样式) ---
    css_styles = """
    <style>
        body {
            font-family: "Microsoft YaHei", "Heiti SC", sans-serif; /* 确保中文显示正常 */
            background-color: white;
            margin: 10px;
        }

        /* Wiki 表格基础样式 */
        .wikitable {
            background-color: #f8f9fa;
            color: #202122;
            margin: 1em 0;
            border: 1px solid #a2a9b1;
            border-collapse: collapse; /* 关键：合并边框 */
            width: 100%;
            font-size: 14px;
            line-height: 1.5;
        }

        /* 表头 (th) - 这里定义了那个灰色的背景 */
        .wikitable th {
            background-color: #eaecf0;
            border: 1px solid #a2a9b1;
            padding: 8px;
            font-weight: bold;
            text-align: center;
        }

        /* 单元格 (td) */
        .wikitable td {
            border: 1px solid #a2a9b1;
            padding: 8px;
            background-color: #ffffff;
            text-align: center;
        }

        /* 针对特殊的内嵌图片调整 */
        .wikitable img {
            vertical-align: middle;
        }

        /* 修复右上角“期间限定”标签的定位 */
        /* 确保父级元素有 relative 定位，否则 absolute 子元素会乱跑 */
        th[style*="position: relative"] {
            position: relative !important;
        }
    </style>
    """

    # --- 3. 组装完整 HTML ---
    # 添加 <meta charset="UTF-8"> 防止生成的图片中文乱码
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        {css_styles}
    </head>
    <body>
        {processed_html}
    </body>
    </html>
    """

    return full_html

# --- 使用示例 ---
if __name__ == "__main__":
    # 假设这是你从 jinja2 渲染出来的原始 html 字符串
    # raw_html_4_jinja2 = html_test
    raw_html_4_jinja2 = asyncio.run(fetch_servant_table_httpx("https://fgo.wiki/w/%E5%BE%90%E7%A6%8F(Avenger)"))
    if raw_html_4_jinja2:
        # 调用函数
        final_html = optimize_html_for_rendering(raw_html_4_jinja2)
        
        # 打印查看，或者直接传给 imgkit
        print("转换完成，由于篇幅过长，仅展示头部：")
        # print(final_html[:500])

        import imgkit

        # 1. 定义 wkhtmltoimage.exe 的绝对路径
        # 注意：路径中可能有空格，也就是 'Program Files'，这没关系
        # 请根据你实际安装的位置修改下面这行路径
        path_wkthmltoimage = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltoimage.exe'

        # 2. 创建配置对象
        config = imgkit.config(wkhtmltoimage=path_wkthmltoimage)

        # 3. 在调用 from_string 时传入 config 参数
        # final_html 是你上一那个函数生成的 HTML 字符串
        try:
            imgkit.from_string(final_html, 'output.jpg', config=config)
            print("图片生成成功！")
        except OSError as e:
            print(f"仍然报错: {e}")
            print("请检查 path_wkthmltoimage 变量里的路径是否真的存在该文件。")
