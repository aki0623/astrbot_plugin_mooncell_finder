# MOONCELL Finder（FGO-WIKI 搜索）

AstrBot 插件，基于 [FGO Wiki（Mooncell）](https://fgo.wiki) 查询《Fate/Grand Order》的从者、礼装、纹章与特性信息，并以合并转发消息的形式返回截图结果。

> **说明**：本插件仍处于测试阶段，请谨慎使用。后续将着重完善功能安全性及代码规范性。

---

## 功能特性

| 功能     | 说明 |
|----------|------|
| **从者查询** | 按名称查询从者详情（含基础数值、宝具等） |
| **礼装查询** | 按名称查询概念礼装详情 |
| **纹章查询** | 按名称查询指令纹章详情 |
| **特性查询** | 按名称查询特性详情，或发送特性一览表格 |
| **结果展示** | 查询结果以网页截图图片形式，通过合并转发消息发送 |

---

## 安装与依赖

- 需已安装 [AstrBot](https://docs.astrbot.app/) 并正常运行。
- 本插件依赖 **Playwright Chromium** 进行页面渲染与截图：
  - **自动安装**：插件加载时仅做轻量检查，不会阻塞启动。若检测到未安装，会在后台尝试预安装；**首次使用**从者/礼装/纹章/特性命令时，若启动失败会自动安装并重试。若命令仍报错，可**稍后再试**或手动执行下方命令。
  - **手动安装**（可选）：`python -m playwright install chromium`
- 其余依赖见 `requirements.txt`（由 AstrBot 或插件环境管理时一般会自动安装）。

---

## 使用方法

### 默认命令格式

| 类型   | 命令格式 | 示例 |
|--------|----------|------|
| 从者   | `MCF从者 [从者名称]` | `MCF从者 C呆` |
| 礼装   | `MCF礼装 [礼装名称]` | `MCF礼装 经典纹章巧克力` |
| 纹章   | `MCF纹章 [纹章名称]` | `MCF纹章 皇家兔女郎` |
| 特性   | `MCF特性 [特性名称]` 或 `MCF特性` | `MCF特性 秩序·善` / `MCF特性`（特性一览） |

- 带参数时：查询对应关键词的详情并返回截图。
- **特性**：仅发送 `MCF特性` 时，返回特性一览表格截图。

### 自定义命令前缀

在 AstrBot 的插件配置中，可为各功能设置自定义命令前缀（见下方「配置」），未填写时使用上表中的默认前缀。

---

## 配置

插件支持在 AstrBot 配置界面中修改「子配置」`sub_config`，用于自定义命令前缀：

| 配置项   | 说明               | 默认值   |
|----------|--------------------|----------|
| `servant` | 从者查询命令前缀   | `MCF从者` |
| `ce`      | 礼装查询命令前缀   | `MCF礼装` |
| `cc`      | 纹章查询命令前缀   | `MCF纹章` |
| `trait`   | 特性查询命令前缀   | `MCF特性` |

配置结构参见 `_conf_schema.json`。

---

## 项目结构

```
astrbot_plugin_mooncell_finder/
├── core/
│   ├── base.py      # 公共逻辑：Wiki API 搜索、浏览器初始化、页面截图等
│   ├── ccode.py     # 纹章（Command Code）查询
│   ├── craft.py     # 礼装（Craft Essence）查询
│   ├── servant.py   # 从者查询
│   └── trait.py     # 特性查询与特性一览
├── main.py          # 插件入口：命令注册与消息处理
├── _conf_schema.json # 配置项定义
├── metadata.yaml    # 插件元数据
├── requirements.txt
├── environment.yml
├── LICENSE
└── README.md
```

---

## 插件信息

| 项目   | 内容 |
|--------|------|
| 名称   | astrbot_plugin_mooncell_finder |
| 展示名 | FGO-WIKI_MOONCELL搜索 |
| 版本   | v0.9 |
| 作者   | akidesuwa |
| 仓库   | [GitHub](https://github.com/aki0623/astrbot_plugin_mooncell_finder) |

---

## 参考

- [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
- [FGO Wiki（Mooncell）](https://fgo.wiki)
