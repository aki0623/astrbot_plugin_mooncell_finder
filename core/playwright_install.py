"""
Playwright Chromium 自动检测与安装。

- 使用 subprocess 调用 `python -m playwright install chromium`，不依赖未公开 API。
- 安装前可检查 Chromium 是否已存在，避免重复安装。
- 提供异步接口，用 asyncio.to_thread 避免阻塞事件循环。
- 推荐在「首次启动失败时」再安装，逻辑简单且只在需要时才下载。
"""

import asyncio
import subprocess
import sys
from typing import Optional

from astrbot.api import logger

# 用于「是否已安装」检测的一行脚本：启动并立即关闭 Chromium
_CHECK_SCRIPT = (
    "from playwright.sync_api import sync_playwright; "
    "p = sync_playwright().start(); "
    "b = p.chromium.launch(); "
    "b.close(); "
    "p.stop()"
)


def is_chromium_installed_sync() -> bool:
    """
    同步检查当前环境是否已安装 Playwright 的 Chromium。
    通过子进程执行一次 launch/close，根据退出码判断。
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", _CHECK_SCRIPT],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.debug(f"Playwright Chromium 检测异常: {e}")
        return False


async def is_chromium_installed() -> bool:
    """异步检查 Chromium 是否已安装（不阻塞事件循环）。"""
    return await asyncio.to_thread(is_chromium_installed_sync)


def install_playwright_chromium_sync(
    *,
    capture_output: bool = False,
    timeout: Optional[int] = 300,
) -> bool:
    """
    同步执行：python -m playwright install chromium。

    :param capture_output: True 时隐藏输出，False 时输出到用户（继承 stdout/stderr）。
    :param timeout: 超时秒数，None 表示不限制。
    :return: 是否成功（returncode == 0）。
    """
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=capture_output,
            timeout=timeout,
        )
        logger.info("Playwright Chromium 安装完成。")
        return True
    except subprocess.CalledProcessError as e:
        logger.warning(f"Playwright Chromium 安装失败（进程退出码 {e.returncode}）。")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("Playwright Chromium 安装超时。")
        return False
    except FileNotFoundError:
        logger.warning("未找到 Python 或 playwright 模块，请先安装 playwright。")
        return False
    except Exception as e:
        logger.warning(f"Playwright Chromium 安装异常: {e}")
        return False


async def install_playwright_chromium(
    *,
    capture_output: bool = False,
    timeout: Optional[int] = 300,
) -> bool:
    """
    异步执行安装，不阻塞事件循环。
    内部使用 asyncio.to_thread(subprocess.run, ...)。
    """
    return await asyncio.to_thread(
        install_playwright_chromium_sync,
        capture_output=capture_output,
        timeout=timeout,
    )


async def ensure_playwright_chromium(
    *,
    skip_check: bool = False,
    capture_output: bool = False,
    timeout: Optional[int] = 300,
) -> bool:
    """
    确保 Playwright Chromium 可用：若未安装则自动安装。

    :param skip_check: True 时不做「是否已安装」检测，直接执行 install（幂等）。
    :param capture_output: 安装时是否隐藏输出。
    :param timeout: 安装超时秒数。
    :return: 最终是否可用（已安装或安装成功）。
    """
    if not skip_check:
        if await is_chromium_installed():
            logger.debug("Playwright Chromium 已存在，跳过安装。")
            return True
    return await install_playwright_chromium(
        capture_output=capture_output,
        timeout=timeout,
    )
