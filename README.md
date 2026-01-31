# MOONCELL Finder for Astrbot

AstrBot 插件，用于查询 FGO 相关的从者、礼装、纹章和特性信息。
## 说明：
本插件仍然处于测试阶段，请您谨慎使用。
后续将着重在 功能实现的安全性、代码规范性等方面进行完善

## 功能特性

- **从者查询**：通过命令查询 FGO 从者的详细信息
- **礼装查询**：通过命令查询 FGO 礼装的详细信息
- **纹章查询**：通过命令查询 FGO 纹章的详细信息
- **特性查询**：通过命令查询 FGO 特性的详细信息，支持特性一览表格
- **图片展示**：查询结果以图片形式通过合并转发的方式发送给用户

## 使用方法

### 命令格式

- **从者查询**：`MCF从者 [从者名称]`
- **礼装查询**：`MCF礼装 [礼装名称]`
- **纹章查询**：`MCF纹章 [纹章名称]`
- **特性查询**：`MCF特性 [特性名称]` 或 `MCF特性`（查询特性一览表格）

### 使用示例

- `MCF从者 C呆`：查询C呆的详细信息
- `MCF礼装 经典纹章巧克力`：查询经典纹章巧克力礼装的详细信息
- `MCF纹章 皇家兔女郎`：查询皇家兔女郎纹章的详细信息
- `MCF特性 秩序·善`：查询秩序·善特性的详细信息
- `MCF特性`：查询特性一览表格

## 插件结构

```
astrbot_plugin_mooncell_finder/
├── core/
│   ├── base.py
│   ├── ccode.py      # 纹章查询相关功能
│   ├── craft.py      # 礼装查询相关功能
│   ├── servant.py    # 从者查询相关功能
│   └── trait.py      # 特性查询相关功能
├── .gitignore
├── LICENSE
├── README.md
├── environment.yml
├── main.py          # 插件主入口
├── metadata.yaml    # 插件元数据
└── requirements.txt
```

## 插件信息

- **名称**：astrbot_plugin_mooncell_finder
- **版本**：v0.9
- **作者**：akidesuwa
- **描述**：MOONCELL机器人

## 支持

- [插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
