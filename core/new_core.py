# 1. 定义 CSS (复用之前的样式，保证表格美观)
CSS_STYLE = """
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