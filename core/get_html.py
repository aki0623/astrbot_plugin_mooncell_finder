import asyncio
import httpx
from bs4 import BeautifulSoup

async def fetch_servant_table_httpx(url: str):
    """
    使用 httpx 异步获取页面并提取目标 HTML
    """
    # 1. 构造请求头 (伪装成浏览器)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        # 2. 异步上下文管理器发送请求
        # follow_redirects=True 类似于 requests 的默认行为
        async with httpx.AsyncClient(http2=True, headers=headers, follow_redirects=True) as client:
            print(f"正在通过 httpx 请求: {url}")
            resp = await client.get(url, timeout=10.0)
            
            # 检查 HTTP 状态码
            resp.raise_for_status()
            
            # 3. 解析 HTML
            html_text = resp.text
            soup = BeautifulSoup(html_text, 'html.parser')
            
            # 4. 定位目标表格
            # class_ 参数可以接受一个字符串，包含多个类名
            target_table = soup.find('table', class_='wikitable nomobile graphpicker-container')
            
            if target_table:
                # --- 可选：清理数据以便渲染 ---
                # 移除 lazy loading，否则图片生成工具可能无法加载图片
                for img in target_table.find_all('img'):
                    if 'loading' in img.attrs:
                        del img['loading']
                    if 'decoding' in img.attrs:
                        del img['decoding']
                
                return str(target_table)
            else:
                print("未找到目标表格")
                return None

    except httpx.HTTPStatusError as e:
        print(f"HTTP 错误: {e.response.status_code} - {e.response.url}")
    except httpx.RequestError as e:
        print(f"网络请求错误: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")
    
    return None

# --- 运行测试 ---
if __name__ == "__main__":
    target_url = "https://fgo.wiki/w/徐福(Avenger)"
    
    # 运行异步主函数
    html_content = asyncio.run(fetch_servant_table_httpx(target_url))
    
    if html_content:
        print("获取成功！前 200 个字符：")
        print(html_content[:200])
        
        # 保存测试
        with open("result_httpx.html", "w", encoding="utf-8") as f:
            f.write(html_content)