# 大话算法 — 样例网站

《大话算法》配套的交互式样例网站，使用纯静态 HTML/CSS/JS 展示算法执行过程。

## 目录结构

```
样例网站/
├── index.html              # 学习地图首页（算法地图可视化）
├── chapters/               # 23 个章节页面（ch00.html ~ ch22.html）
├── js/
│   └── engine.js           # 共享 JS 执行引擎（TraceEngine 类）
├── templates/
│   └── chapter.html        # 章节页面 HTML 模板（generate.py 使用）
├── data/
│   └── traces/             # 111 个真实执行轨迹 JSON（其余主题使用概念动画）
└── scripts/
    ├── auto_instrument.py  # C 代码自动插桩器（插桩→编译→运行→JSON）
    ├── generate.py         # 章节页面生成器（traces + 模板 → HTML）
    └── run_batch_traces.sh # 一键批处理脚本
```

## 工作流程

```
C 源文件（随书源代码/）
    │
    ▼
auto_instrument.py          # 1. 插桩 + 编译 + 运行
    │                        每个 .c 生成为一个 .json 轨迹文件
    ▼
data/traces/*.json          # 2. 111 个真实轨迹文件
    │
    ▼
generate.py                 # 3. 读取 traces + 模板，也可生成概念动画演示
    │                        生成 23 个章节 HTML，当前共 124 个演示
    ▼
chapters/ch*.html           # 4. 可部署的静态页面
```

## 使用方法

### 一键构建

以下生成命令均在 `样例网站/` 目录执行，需要 Python 3 和 C 编译器（GCC 或 Clang）。生成脚本会从仓库根目录的 `随书源代码/` 读取示例，不依赖任何个人电脑路径。已提供可直接使用的静态页面，普通浏览无需构建。

```bash
bash scripts/run_batch_traces.sh
```

### 分步操作

```bash
# 第一步：从 C 源码生成执行轨迹 JSON
python3 scripts/auto_instrument.py --batch ../随书源代码 data/traces/

# 第二步：从轨迹 JSON 生成章节 HTML 页面
python3 scripts/generate.py
```

### 本地预览

在仓库根目录运行 `python3 -m http.server 8000 --directory "样例网站"`，然后访问 http://localhost:8000/ 。

### 轨迹体检

```bash
python3 scripts/audit_traces.py
```

这个脚本只读检查当前 `data/traces/`，用于确认 trace 数量、渲染器覆盖率、空 `initial_data` 和疑似原始地址变量。

## 技术要点

- **插桩器** (`auto_instrument.py`)：在 C 代码中注入 TRACE 宏（TRACE_ENTER/TRACE_EXEC/TRACE_COND/TRACE_EXIT），编译运行后得到逐步执行轨迹
- **引擎** (`engine.js`)：TraceEngine 类——加载轨迹 JSON，驱动代码高亮、变量面板、Canvas 可视化、播放/暂停/单步控制
- **生成器** (`generate.py`)：扫描 C 源码目录，匹配已有 trace JSON，通过模板渲染为章节 HTML
- **概念动画**：对没有确切 C 源码的内容，可在 `generate.py` 中用伪代码和手写步骤生成演示数据
- **模板** (`chapter.html`)：包含完整的 CSS 布局（代码面板 + Canvas 可视化区 + 变量面板 + 控制栏）+ engine.js 引用
