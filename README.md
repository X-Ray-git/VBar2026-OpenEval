# VBar 2026 OpenEval

本项目是一个基于 Python 的自动化流水线，旨在将庞大且排版各异的 Excel 评分表格合并解析，并最终自动生成一份排版精美的 PDF 阅卷汇总报告。

数据来源：[在线瑞平评分表](https://docs.qq.com/sheet/DSmR1Y3NHaHp1S0tR)，截止 2026 年 3 月 25 日。

## 📁 目录结构

整理后的项目结构如下：

* **`.github/`**：自动化持续集成工作流。
  * `workflows/release.yml`：每次推送 `v*` 标签后，云端自动构建 PDF 并作为 Release 附件发布的 GitHub Actions。
* **`data/`**：数据存放区。
  * `26V8在线瑞平0325.xlsx`：原始 Excel 打分汇总表。
  * 以及程序生成的中间态缓存（`color_data.json`、`excel_data.json` 等）。
* **`src/`**：核心业务逻辑。
  * `models.py`：数据模型（歌曲、评分结构）。
  * `parser_registry.py`：解析器路由注册表。
  * `sheet_parsers.py`：**由机器动态生成**的各个子表解析代码。
  * `pdf_generator.py`：WeasyPrint 的 PDF 生成与排版逻辑。
* **`scripts/`**：流水线生成脚本。
  * `extract_data.py`：从 Excel 表提取出结构化文字 JSON 数据集。
  * `extract_colors.py`：通过底层 XML 暴力解析 Excel 单元格底色。
  * `config_builder.py`：构建识别表头的配置。
  * `generate_parsers.py`：**核心引擎**，动态生成 `src/sheet_parsers.py` 的元编程脚本。
* **`main.py`**：系统主入口，聚合所有解析出的数据并打包为 PDF。

## 🚀 开始使用

### 1. 环境配置

因为 `venv` 文件夹不会在发布项目时被打包携带，因此首次拿到项目后，您需要自己在机器上配置好隔离的运行环境：

```bash
# 进入项目根目录
cd vbar-openeval-2026

# 1. 创建名为 venv 的虚拟环境 (首次运行)
python3 -m venv venv

# 2. 激活虚拟环境 (macOS/Linux 下)
source venv/bin/activate
# Windows 下请运行: .\venv\Scripts\activate

# 3. 安装项目所需的全部依赖环境
pip install -r requirements.txt
```

### 2. 运行流水线

确保您在所需的运行环境下。如果 Excel 表格内容或表头结构发生了大幅增改，请先完整执行一遍流水线更新解析逻辑：

```bash
# 1. 依序运行流水线以重置/生成全新的解析器逻辑
python scripts/extract_data.py
python scripts/extract_colors.py
python scripts/config_builder.py
python scripts/generate_parsers.py

# 2. 运行主程序，聚合并自动导出最终 PDF
python main.py
```

执行完毕后，项目根目录会生成最新的 `evaluation_report.pdf` 汇总文件。
