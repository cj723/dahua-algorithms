#!/usr/bin/env python3
"""
大话算法 v2 — 批量生成章节页面和轨迹框架
用法: python3 generate.py [--with-traces]
  不加 --with-traces: 只生成页面框架（源代码+元数据，步骤为空）
  加 --with-traces: 同时运行插桩器生成真实轨迹
"""
import json, os, re, sys, subprocess
from html import escape
from pathlib import Path

BASE = Path(__file__).parent.parent  # prototype 根目录
SRC_DIR = BASE.parent / "生成源代码"
OUT_DIR = BASE / "chapters"
TRACE_DIR = BASE / "data" / "traces"
TEMPLATE = BASE / "templates" / "chapter.html"

# ===== 章节元数据 =====
CHAPTERS = [
    {"num": 0,  "dir": "第00章_第0章_引言_算法是什么",                "title": "引言——算法是什么？"},
    {"num": 1,  "dir": "第01章_第1章_算法__你每天都在用",             "title": "算法——你每天都在用"},
    {"num": 2,  "dir": "第02章_第2章_算法的度量衡",                   "title": "算法的度量衡"},
    {"num": 3,  "dir": "第03章_第3章_分而治之",                       "title": "分而治之"},
    {"num": 4,  "dir": "第04章_第4章_搜索的艺术",                     "title": "搜索的艺术"},
    {"num": 5,  "dir": "第05章_第5章_线性排序",                     "title": "线性排序"},
    {"num": 6,  "dir": "第06章_第6章_排序的哲学",                     "title": "排序的哲学"},
    {"num": 7,  "dir": "第07章_第7章_贪心算法",                       "title": "贪心算法"},
    {"num": 8,  "dir": "第08章_第8章_动态规划(上)",                   "title": "动态规划（上）"},
    {"num": 9,  "dir": "第09章_第9章_动态规划(下)",                   "title": "动态规划（下）"},
    {"num": 10, "dir": "第10章_第10章_回溯法",                        "title": "回溯法"},
    {"num": 11, "dir": "第11章_第11章_分支限界",                      "title": "分支限界"},
    {"num": 12, "dir": "第12章_第12章_图的进阶",                      "title": "图的进阶"},
    {"num": 13, "dir": "第13章_第13章_最短路径的升级版",              "title": "最短路径的升级版"},
    {"num": 14, "dir": "第14章_第14章_字符串匹配",                    "title": "字符串匹配"},
    {"num": 15, "dir": "第15章_第15章_高级数据结构",                  "title": "高级数据结构"},
    {"num": 16, "dir": "第16章_第16章_位运算魔法",                    "title": "位运算魔法"},
    {"num": 17, "dir": "第17章_第17章_概率算法",                      "title": "概率算法"},
    {"num": 18, "dir": "第18章_第18章_算法在现实世界",                "title": "算法在现实世界"},
    {"num": 19, "dir": "第19章_第19章_链表与树的指尖舞蹈",            "title": "链表与树的指尖舞蹈"},
    {"num": 20, "dir": "第20章_第20章_动态规划的降维打击",            "title": "动态规划的降维打击"},
    {"num": 21, "dir": "第21章_第21章_数组与字符串的灵活技巧",        "title": "数组与字符串的灵活技巧"},
    {"num": 22, "dir": "第22章_第22章_结语_封老师的最后一课",         "title": "结语 · 封老师的最后一课"},
]


def read_source(path):
    """读取C源代码"""
    try:
        return path.read_text(encoding='utf-8')
    except:
        return path.read_text(encoding='gbk')


def guess_algo_name(filename):
    """从文件名猜算法名称"""
    name = filename.stem
    # 去掉序号前缀
    name = re.sub(r'^\d+_', '', name)
    # 去掉"C语言实现"等前缀
    name = re.sub(r'^C语言[：:]?\s*', '', name)
    name = re.sub(r'^C代码[：:]?\s*', '', name)
    # 去掉章节引用
    name = re.sub(r'^\d+\.\d+\.\d+[_\s]*', '', name)
    # 清理
    name = name.strip('_').strip()
    return name or filename.stem


def display_algo_name(name):
    """把源码文件名转换为适合学习界面展示的自然名称。"""
    replacements = {
        "BrianKernighan": "Brian Kernighan",
        "BellmanFord": "Bellman–Ford",
        "FloydWarshall": "Floyd–Warshall",
        "RabinKarp": "Rabin–Karp",
        "EdmondsKarp": "Edmonds–Karp",
        "Karatsuba": "Karatsuba",
        "AStar": "A*",
    }
    for raw, display in replacements.items():
        name = name.replace(raw, display)
    name = name.replace("空间O1", "空间 O(1)").replace("空间On", "空间 O(n)")
    name = name.replace("统计1的个数", "统计 1 的个数").replace("第k小", "第 k 小")
    name = name.replace("nextval", "nextval ").replace("next数组", "next 数组")
    parts = [part.strip() for part in name.split("_") if part.strip()]
    if len(parts) > 1:
        return f"{parts[0]}（{' · '.join(parts[1:])}）"
    return parts[0] if parts else name


def guess_important_vars(source):
    """从源代码猜测重要变量"""
    vars_map = {}
    # 常见的索引变量
    for m in re.finditer(r'\b(int|float|double)\s+(\w+)\s*=', source):
        v = m.group(2)
        if v in ('i','j','k','idx','index','pos','p','q','l','r','lo','hi'):
            vars_map[v] = '索引'
        elif v in ('left','right','mid','low','high','start','end','first','last','lt','gt'):
            vars_map[v] = '索引'
        elif v in ('prev','curr','next','head','tail','slow','fast','s','t','u','v','w'):
            vars_map[v] = '指针'
        elif v in ('n','m','len','size','count','target','key','val','value','k','x'):
            vars_map[v] = '参数'
        elif v in ('result','ans','res','sum','max','min','cnt','ret'):
            vars_map[v] = '变量'
    # 数组
    for m in re.finditer(r'\b(int|float|double)\s+(\w+)\s*\[', source):
        v = m.group(2)
        if v not in ('stack','queue','buffer','temp','tmp','buf'):
            vars_map[v] = '数据'
    return vars_map


def generate_chapter_html(ch, algos_json):
    """生成章节HTML"""
    tmpl = TEMPLATE.read_text(encoding='utf-8')
    ch_num = f"第{ch['num']}章"
    prev_link = (
        f'<a href="ch{ch["num"] - 1:02d}.html" aria-label="上一章：{escape(CHAPTERS[ch["num"] - 1]["title"])}" title="上一章：{escape(CHAPTERS[ch["num"] - 1]["title"])}">上一章</a>'
        if ch["num"] > 0 else
        '<span class="disabled" aria-disabled="true" title="已经是第一章">上一章</span>'
    )
    next_link = (
        f'<a href="ch{ch["num"] + 1:02d}.html" aria-label="下一章：{escape(CHAPTERS[ch["num"] + 1]["title"])}" title="下一章：{escape(CHAPTERS[ch["num"] + 1]["title"])}">下一章</a>'
        if ch["num"] < len(CHAPTERS) - 1 else
        '<span class="disabled" aria-disabled="true" title="已经是最后一章">下一章</span>'
    )
    html = tmpl.replace('__PAGE_TITLE__', f"{ch_num} {ch['title']} · 大话算法")
    html = html.replace('__CHAPTER_TITLE__', escape(ch['title']))
    html = html.replace('__CH_NUM__', ch_num)
    html = html.replace('__CHAPTER_NUM__', str(ch['num']))
    html = html.replace('__PREV_LINK__', prev_link)
    html = html.replace('__NEXT_LINK__', next_link)
    html = html.replace('__ALGOS_JSON__', algos_json)
    return html


def scan_chapter(ch):
    """扫描一个章节的所有.c文件，返回算法数据"""
    if ch['num'] == 22:
        return concept_demos_ch22()

    src_path = SRC_DIR / ch['dir']
    if not src_path.exists():
        return {}
    algos = {}
    c_files = sorted(src_path.glob('*.c'))
    for i, c_file in enumerate(c_files):
        source = read_source(c_file)
        algo_id = c_file.stem.replace(' ', '_')
        if algo_id in hidden_algo_ids():
            continue
        algo_name = display_algo_name(guess_algo_name(c_file))
        important_vars = guess_important_vars(source)
        # 尝试加载已有的轨迹
        trace_file = TRACE_DIR / f"{algo_id}.json"
        if trace_file.exists():
            trace = json.loads(trace_file.read_text(encoding='utf-8'))
            steps = trace.get('steps', [])
        else:
            steps = []
        # 优先使用插桩器生成的 meta 数据
        use_new_format = trace_file.exists() and trace.get('meta', {}).get('track_vars')
        if use_new_format:
            meta = trace['meta']
            algos[algo_id] = {
                'title': algo_name,
                'source': meta.get('source_lines', source.split('\n')),
                'important_vars': important_vars,  # 旧格式兼容
                'track_vars': meta.get('track_vars', {}),
                'var_classes': meta.get('var_classes', {}),
                'initial_data': meta.get('initial_data', {}),
                'program_output': meta.get('program_output', []),
                'steps': steps
            }
        else:
            algos[algo_id] = {
                'title': algo_name,
                'source': source.split('\n'),
                'important_vars': important_vars,
                'steps': steps
            }
        # 已逐章校准的页面必须展示磁盘上的定稿源码，而不是旧轨迹缓存的 source_lines。
        if 8 <= ch['num'] <= 21:
            algos[algo_id]['source'] = source.split('\n')
        if ch['num'] == 0:
            algos[algo_id] = curate_ch00_code_demo(algo_id, algos[algo_id])
        if ch['num'] == 2:
            algos[algo_id] = curate_ch02_code_demo(algo_id, algos[algo_id])
        if ch['num'] == 6:
            algos[algo_id] = curate_ch06_code_demo(algo_id, algos[algo_id])
        if ch['num'] == 8:
            algos[algo_id] = curate_ch08_code_demo(algo_id, algos[algo_id])
        if ch['num'] == 9:
            algos[algo_id] = curate_ch09_code_demo(algo_id, algos[algo_id])
        if ch['num'] == 10:
            algos[algo_id] = curate_ch10_code_demo(algo_id, algos[algo_id])
        if ch['num'] == 11:
            algos[algo_id] = curate_ch11_code_demo(algo_id, algos[algo_id])
        if ch['num'] == 12:
            algos[algo_id] = curate_ch12_code_demo(algo_id, algos[algo_id])
        if ch['num'] == 13:
            algos[algo_id] = curate_ch13_code_demo(algo_id, algos[algo_id])
        if ch['num'] == 14:
            algos[algo_id] = curate_ch14_code_demo(algo_id, algos[algo_id])
            algos[algo_id] = enrich_string_match_demo(algo_id, algos[algo_id])
        if ch['num'] == 15:
            algos[algo_id] = curate_ch15_code_demo(algo_id, algos[algo_id])
        if 16 <= ch['num'] <= 21:
            algos[algo_id] = curate_late_chapter_code_demo(algos[algo_id])
        concept_override = concept_demo_override(algo_id)
        if concept_override:
            if algo_id in concept_only_algo_ids():
                algos[algo_id] = concept_override
            else:
                algos[algo_id] = make_dual_mode_algo(algos[algo_id], concept_override)
    if ch['num'] == 15 and "05_红黑树_理解动画" not in algos:
        with_red_black = {}
        inserted = False
        for key, value in algos.items():
            with_red_black[key] = value
            if key == "04_并查集_社交圈示例":
                with_red_black["05_红黑树_理解动画"] = concept_demo_red_black_tree()
                inserted = True
        if not inserted:
            with_red_black["05_红黑树_理解动画"] = concept_demo_red_black_tree()
        algos = with_red_black
    for algo in algos.values():
        algo["title"] = display_algo_name(algo.get("title", ""))
        for mode_data in (algo.get("modes") or {}).values():
            mode_data["title"] = display_algo_name(mode_data.get("title", algo["title"]))
    return algos


def make_dual_mode_algo(trace_algo, concept_algo):
    """默认给初学者看概念动画，同时保留真实 C 执行细节。"""
    return {
        "title": concept_algo.get("title") or trace_algo.get("title"),
        "defaultMode": "concept",
        "modeLabels": {
            "concept": "理解动画",
            "trace": "代码执行",
        },
        "modes": {
            "concept": concept_algo,
            "trace": trace_algo,
        },
    }


def concept_demo_override(algo_id):
    """把过长或不适合逐行调试的算法替换为概念动画。"""
    overrides = {
        "01_循环累加": concept_demo_sum_loop,
        "02_高斯公式求和": concept_demo_sum_formula,
        "01_顺序查找": concept_demo_linear_search,
        "02_冒泡排序": concept_demo_bubble_sort,
        "03_冒泡排序_优化版": concept_demo_bubble_sort_optimized,
        "04_选择排序": concept_demo_selection_sort,
        "01_顺序查找_复杂度分析": concept_demo_search_complexity,
        "02_快排_最坏与平均": concept_demo_quick_complexity,
        "03_原地反转_空间O1": concept_demo_in_place_reverse_space,
        "04_归并_空间On": concept_demo_merge_space,
        "05_动态数组_摊还分析": concept_demo_dynamic_array_amortized,
        "07_停机问题_反证法": concept_demo_halting_problem,
        "08_复杂度阶层全景图": concept_demo_complexity_ladder,
        "01_二分查找_经典版": concept_demo_binary_search,
        "02_二分查找_找第一个目标": concept_demo_binary_first,
        "03_二分查找_找最后目标": concept_demo_binary_last,
        "04_二分查找_旋转数组": concept_demo_rotated_binary_search,
        "05_插值查找": concept_demo_interpolation_search,
        "01_爬楼梯_暴力递归": concept_demo_climb_recursive,
        "01_归并排序": concept_demo_merge_sort,
        "02_快速排序": concept_demo_quick_sort,
        "03_Karatsuba快速乘法": concept_demo_karatsuba,
        "01_计数排序": concept_demo_counting_sort,
        "02_计数排序_稳定版": concept_demo_counting_sort_stable,
        "03_基数排序": concept_demo_radix_sort,
        "04_桶排序": concept_demo_bucket_sort,
        "01_冒泡与选择_稳定性对比": concept_demo_sort_stability,
        "02_归并排序_空间对比": concept_demo_merge_space,
        "03_外部排序_多路归并": concept_demo_external_sort,
        "04_希尔排序": concept_demo_shell_sort,
        "05_堆排序": concept_demo_heap_sort,
        "06_工程版快速排序": concept_demo_engineered_quick_sort,
        "07_插入排序": concept_demo_insertion_sort,
        "01_活动选择": concept_demo_activity_selection,
        "02_哈夫曼编码": concept_demo_huffman_coding,
        "03_Kruskal最小生成树": concept_demo_kruskal_mst,
        "06_跳表_定义与节点": concept_demo_skip_list_structure,
        "08_跳表_插入逻辑": concept_demo_skip_list_insert,
        "07_斐波那契查找": concept_demo_fibonacci_search,
        "08_二分答案_运送包裹": concept_demo_binary_answer_shipping,
        "03_爬楼梯_自底向上": concept_demo_climb_bottom_up,
        "04_爬楼梯_双变量优化": concept_demo_climb_optimized,
        "05_硬币找零_记忆化搜索": concept_demo_coin_memo,
        "06_硬币找零_自底向上填表": concept_demo_coin_dp,
        "07_零一背包": concept_demo_knapsack_table,
        "08_最长公共子序列": concept_demo_lcs_table,
        "09_LCS方案还原": concept_demo_lcs_restore,
        "01_编辑距离": concept_demo_edit_distance_table,
        "02_矩阵链乘法": concept_demo_matrix_chain_table,
        "03_最长递增子序列_DP": concept_demo_lis_dp,
        "04_最长递增子序列_二分优化": concept_demo_lis_binary,
        "05_滚动数组": concept_demo_rolling_array,
        "04_蒙特卡洛_求圆周率": concept_demo_monte_carlo_pi,
        "01_BFS搜索框架": concept_demo_bfs_islands,
        "02_全排列_基础版": concept_demo_permutation_used,
        "03_全排列_优化版": concept_demo_permutation_swap,
        "04_子集生成": concept_demo_subset_generation,
        "05_N皇后_基础版": concept_demo_n_queens_basic,
        "06_N皇后_空间优化": concept_demo_n_queens_space_check,
        "07_N皇后_对角线优化": concept_demo_n_queens_diagonal,
        "08_数独求解": concept_demo_sudoku,
        "09_剪枝技巧": concept_demo_pruning_techniques,
        "01_零一背包_分支限界": concept_demo_branch_bound_knapsack,
        "02_旅行商_分支限界": concept_demo_branch_bound_tsp,
        "01_Tarjan强连通分量": concept_demo_tarjan_scc,
        "02_EdmondsKarp最大流": concept_demo_edmonds_karp,
        "03_匈牙利算法_二分匹配": concept_demo_hungarian_matching,
        "02_KMP_next数组": concept_demo_kmp_next,
        "01_暴力匹配_BF": concept_demo_bf_match,
        "03_KMP_匹配过程": concept_demo_kmp_match,
        "04_KMP_nextval优化": concept_demo_kmp_nextval,
        "05_RabinKarp_哈希匹配": concept_demo_rabin_karp,
        "06_Trie字典树": concept_demo_trie,
        "07_AC自动机": concept_demo_ac_automaton,
        "01_并查集_朴素版": concept_demo_union_find_basic,
        "02_并查集_路径压缩": concept_demo_union_find_compress,
        "03_并查集_按秩合并": concept_demo_union_find_rank,
        "04_并查集_社交圈示例": concept_demo_union_find_social,
        "05_红黑树_理解动画": concept_demo_red_black_tree,
        "05_线段树_建树": concept_demo_segment_build,
        "06_线段树_单点修改": concept_demo_segment_update,
        "07_线段树_区间查询": concept_demo_segment_query,
        "08_线段树_完整示例": concept_demo_segment_full,
        "09_树状数组_lowbit": concept_demo_fenwick_lowbit,
        "10_树状数组_实现": concept_demo_fenwick_ops,
        "11_树状数组_完整示例": concept_demo_fenwick_full,
        "01_BrianKernighan_统计1的个数": concept_demo_brian_kernighan,
        "02_判断2的幂": concept_demo_power_of_two,
        "03_异或交换": concept_demo_xor_swap,
        "04_位图_Bitmap": concept_demo_bitmap,
        "01_生日悖论_模拟验证": concept_demo_birthday_paradox,
        "02_随机化快排": concept_demo_randomized_quick_sort,
        "03_蓄水池抽样": concept_demo_reservoir_sampling,
        "05_随机化选择_第k小": concept_demo_randomized_select,
        "05_布隆过滤器": concept_demo_bloom_filter,
        "01_反转链表": concept_demo_reverse_list,
        "02_快慢指针_环检测": concept_demo_cycle_detection,
        "03_层序遍历": concept_demo_level_order,
        "04_最近公共祖先": concept_demo_lca,
        "01_滑动窗口_最短子数组": concept_demo_sliding_window_min_subarray,
        "02_双指针_两数之和": concept_demo_two_sum_two_pointers,
        "03_快慢指针_中点与倒数": concept_demo_fast_slow_variants,
        "04_双指针_三数之和": concept_demo_three_sum,
        "05_单调栈_下一个更大": concept_demo_next_greater_stack,
        "06_前缀和": concept_demo_prefix_sum,
        "07_差分数组": concept_demo_difference_array,
        "06_权限管理_位运算": concept_demo_permission_bits,
        "06_状态压缩_位运算": concept_demo_bitmask_ops,
        "07_状态压缩DP_TSP": concept_demo_bitmask_tsp,
        "01_皮尔逊相似度": concept_demo_pearson_similarity,
        "03_LZ77压缩": concept_demo_lz77,
        "02_PageRank_简化版": concept_demo_pagerank,
        "04_Dijkstra导航_现实版": concept_demo_navigation_dijkstra,
        "05_梯度下降_一元函数": concept_demo_gradient_descent,
        "06_学习率_步长对比": concept_demo_learning_rate_compare,
        "01_打家劫舍": concept_demo_house_robber,
        "02_股票买卖_一次交易": concept_demo_stock_profit,
        "03_零钱兑换_完全背包": concept_demo_coin_change_rolling,
        "01_Dijkstra_朴素版": concept_demo_dijkstra,
        "02_Dijkstra_堆优化版": concept_demo_dijkstra_heap,
        "03_BellmanFord_负权边": concept_demo_bellman_ford,
        "04_SPFA_队列优化": concept_demo_spfa,
        "05_FloydWarshall_核心": concept_demo_floyd_core,
        "06_FloydWarshall_初始化": concept_demo_floyd_init,
        "07_AStar_启发搜索": concept_demo_astar,
    }
    maker = overrides.get(algo_id)
    return maker() if maker else None


def hidden_algo_ids():
    """源码可保留为补充材料, 但不一定都适合成为网站入口。"""
    return {
        "06_动态数组_完整示例",
    }


def concept_only_algo_ids():
    """这些主题重在理解, 不让初学者误以为要逐行调试才能学懂。"""
    return {
        "07_停机问题_反证法",
        "08_复杂度阶层全景图",
    }


def _extract_c_string(source, var_name):
    m = re.search(r'\b(?:char\s+\*|char\s+)\s*' + re.escape(var_name) + r'\s*(?:\[\])?\s*=\s*"([^"]*)"', source)
    return m.group(1) if m else ""


def enrich_string_match_demo(algo_id, algo):
    """给字符串匹配类算法补专用可视化状态：上主串、下模式串。"""
    if algo_id not in {
        "01_暴力匹配_BF",
        "03_KMP_匹配过程",
        "05_RabinKarp_哈希匹配",
    }:
        return algo

    source_text = "\n".join(algo.get("source") or [])
    text = _extract_c_string(source_text, "text")
    pattern = _extract_c_string(source_text, "pattern")
    if not text or not pattern:
        return algo

    mode = "bf" if algo_id.startswith("01_") else "kmp" if algo_id.startswith("03_") else "rk"
    state = {}
    steps = []
    for step in algo.get("steps", []):
        new_step = dict(step)
        vars_snapshot = dict(step.get("vars") or {})
        state.update(vars_snapshot)
        i = state.get("i")
        j = state.get("j")
        line = step.get("line") or 0
        show = False
        if mode == "bf":
            show = i is not None and line >= 7 and line <= 15
            offset = int(i or 0)
        elif mode == "kmp":
            show = i is not None and j is not None and line >= 24 and line <= 33
            offset = int(i or 0) - max(int(j or 0), 0)
        else:
            show = i is not None and line >= 24 and line <= 34
            offset = int(i or 0)

        if show:
            jj = int(j if j is not None else 0)
            compare_text_idx = offset + jj
            mismatch = (
                0 <= jj < len(pattern)
                and 0 <= compare_text_idx < len(text)
                and line in {10, 29, 30}
                and text[compare_text_idx] != pattern[jj]
            )
            success = (mode in {"bf", "rk"} and line in {14, 31}) or (mode == "kmp" and jj >= len(pattern))
            vars_snapshot["stringMatch"] = {
                "text": text,
                "pattern": pattern,
                "i": int(i or 0),
                "j": jj,
                "offset": max(0, offset),
                "mode": mode,
                "mismatch": mismatch,
                "success": success,
                "windowOnly": mode == "rk" and line not in {26, 27, 28, 29, 30, 31},
            }
            new_step["vars"] = vars_snapshot
        steps.append(new_step)

    algo = dict(algo)
    algo["steps"] = steps
    algo.setdefault("var_classes", {})
    algo["var_classes"] = dict(algo["var_classes"])
    algo["var_classes"]["stringMatch"] = {"category": "secondary", "type": "string_match"}
    track = dict(algo.get("track_vars") or {})
    secondary = list(track.get("secondary") or [])
    if "stringMatch" not in secondary:
      secondary.append("stringMatch")
    track["secondary"] = secondary
    track.setdefault("primary", list((algo.get("important_vars") or {}).keys()))
    algo["track_vars"] = track
    return algo


def concept_demo_sum_loop():
    source = [
        "算法: 循环累加",
        "输入: n",
        "输出: 1 + 2 + ... + n",
        "",
        "sum = 0",
        "for i = 1..n:",
        "    sum = sum + i",
        "返回 sum",
    ]
    return _build_sum_demo(
        "循环累加",
        source,
        "loop",
        [
            (5, "从 0 开始准备累加", 0, 0),
            (6, "加上第 1 项", 1, 1),
            (6, "继续加第 2、3 项", 3, 6),
            (6, "一直走到第 6 项", 6, 21),
            (8, "答案 21 是一步步累出来的", 6, 21),
        ],
        "概念动画：循环累加要走 n 次，n 越大，步骤越多。",
    )


def curate_ch00_code_demo(algo_id, algo):
    """Keep chapter 0 code execution faithful without tracing a million loop iterations."""
    if algo_id == "01_循环累加":
        rows = [
            ("enter", 11, "main", {"count": 4, "phase": "程序准备依次测试 10、100、10000、1000000"}),
            ("exec", 14, None, {"count": 4, "phase": "先说明循环累加的时间复杂度是 O(n)"}),
            ("cond", 15, None, {"k": 0, "n": 10, "phase": "第一组样例 n=10, 展开观察每次累加"}),
            ("enter", 4, "sum_loop", {"n": 10, "sum": 0, "phase": "进入 sum_loop, sum 从 0 开始"}),
            ("cond", 6, None, {"n": 10, "i": 1, "sum": 0, "phase": "i 从 1 开始"}),
            ("exec", 7, None, {"n": 10, "i": 1, "sum": 1, "phase": "sum += 1, 得到 1"}),
            ("exec", 7, None, {"n": 10, "i": 2, "sum": 3, "phase": "sum += 2, 得到 3"}),
            ("exec", 7, None, {"n": 10, "i": 3, "sum": 6, "phase": "sum += 3, 得到 6"}),
            ("exec", 7, None, {"n": 10, "i": 9, "sum": 45, "phase": "省略中间相同循环, 累加到 9 得到 45"}),
            ("exec", 7, None, {"n": 10, "i": 10, "sum": 55, "phase": "最后加 10, 得到 55"}),
            ("exit", 9, "sum_loop", {"n": 10, "_return": 55, "phase": "返回第一组结果 55"}),
            ("cond", 15, None, {"k": 1, "n": 100, "phase": "n=100 仍执行同一循环, 中间步骤省略"}),
            ("exit", 9, "sum_loop", {"n": 100, "_return": 5050, "phase": "循环 100 次, 结果 5050"}),
            ("cond", 15, None, {"k": 2, "n": 10000, "phase": "n=10000 时循环次数随 n 增长"}),
            ("exit", 9, "sum_loop", {"n": 10000, "_return": 50005000, "phase": "循环 10000 次, 结果 50005000"}),
            ("cond", 15, None, {"k": 3, "n": 1000000, "phase": "n=1000000 时要做一百万次累加"}),
            ("exit", 9, "sum_loop", {"n": 1000000, "_return": 500000500000, "phase": "使用 long long 安全保存最终结果"}),
            ("exit", 19, "main", {"_return": 0, "phase": "四组样例全部完成"}),
        ]
        steps = []
        for idx, (kind, line, func, vars_) in enumerate(rows):
            step = {"step": idx, "line": line, "type": kind, "vars": vars_}
            if func:
                step["func"] = func
            if kind == "cond":
                step["result"] = True
            steps.append(step)
        algo["steps"] = steps
        algo["program_output"] = [
            {"after_step": 1, "text": "方法一：循环累加（O(n)）"},
            {"after_step": 11, "text": "1 + 2 + ... + 10      = 55"},
            {"after_step": 13, "text": "1 + 2 + ... + 100     = 5050"},
            {"after_step": 15, "text": "1 + 2 + ... + 10000   = 50005000"},
            {"after_step": 17, "text": "1 + 2 + ... + 1000000 = 500000500000"},
        ]
        algo["track_vars"] = {
            "primary": ["n", "i", "sum", "phase"],
            "secondary": ["k", "count", "_return"],
        }
        algo["var_classes"] = {
            "n": {"category": "primary", "type": "scalar"},
            "i": {"category": "primary", "type": "scalar"},
            "sum": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "k": {"category": "secondary", "type": "scalar"},
            "count": {"category": "secondary", "type": "scalar"},
            "_return": {"category": "secondary", "type": "scalar"},
        }
    return algo


def curate_ch02_code_demo(algo_id, algo):
    """归并排序只保留递归边界与数组变化，避免重复条件检查淹没主线。"""
    if algo_id != "04_归并_空间On":
        return algo

    steps = algo.get("steps", [])
    if len(steps) <= 200:
        return algo

    kept = []
    last_arr = None
    saw_arr = False
    for index, step in enumerate(steps):
        variables = step.get("vars", {})
        arr_changed = False
        if "arr" in variables:
            current_arr = variables["arr"]
            arr_changed = not saw_arr or current_arr != last_arr
            last_arr = current_arr
            saw_arr = True

        if (
            index == 0
            or index == len(steps) - 1
            or step.get("type") in {"enter", "exit"}
            or arr_changed
        ):
            kept.append(dict(step))

    if kept:
        first_vars = dict(kept[0].get("vars", {}))
        first_vars["phase"] = "已省略重复条件检查，保留递归进出与数组变化"
        kept[0]["vars"] = first_vars
        for step_number, step in enumerate(kept):
            step["step"] = step_number

    curated = dict(algo)
    curated["steps"] = kept
    return curated


def curate_ch06_code_demo(algo_id, algo):
    """压缩排序哲学章中重复度很高的递归与循环轨迹。"""
    watched_by_algo = {
        "02_归并排序_空间对比": ("arr",),
        "06_工程版快速排序": ("arr", "low", "high", "pivotPos"),
    }
    watched = watched_by_algo.get(algo_id)
    if watched is None:
        return algo

    steps = algo.get("steps", [])
    if len(steps) <= 200:
        return algo

    previous = {}
    kept = []
    for index, step in enumerate(steps):
        variables = step.get("vars", {})
        changed = False
        for name in watched:
            if name in variables and previous.get(name) != variables[name]:
                previous[name] = variables[name]
                changed = True

        if (
            index == 0
            or index == len(steps) - 1
            or step.get("type") in {"enter", "exit"}
            or changed
        ):
            kept.append(dict(step))

    if kept:
        first_vars = dict(kept[0].get("vars", {}))
        first_vars["phase"] = "已省略重复检查，保留函数进出与关键状态变化"
        kept[0]["vars"] = first_vars
        for step_number, step in enumerate(kept):
            step["step"] = step_number

    curated = dict(algo)
    curated["steps"] = kept
    return curated


def curate_ch08_code_demo(algo_id, algo):
    """DP 章保留关键状态，避免递归爆炸和大二维数组轨迹。"""
    source = algo.get("source", [])

    def normalize_output_steps(curated):
        steps = curated.get("steps", [])
        outputs = curated.get("program_output", [])
        if not steps or not outputs:
            return curated
        if all(0 <= item.get("after_step", 0) <= len(steps) for item in outputs):
            return curated

        result = dict(curated)
        output_start = max(1, len(steps) - len(outputs) + 1)
        result["program_output"] = [
            {**item, "after_step": output_start + index}
            for index, item in enumerate(outputs)
        ]
        return result

    def line_of(fragment, fallback=1):
        for index, line in enumerate(source, start=1):
            if fragment in line:
                return index
        return fallback

    manual = {
        "07_零一背包": [
            ("enter", "int main(void)", {"n": 4, "W": 4, "phase": "准备 4 件物品和容量 4 的背包"}),
            ("enter", "int knapsack01", {"i": 0, "w": 0, "phase": "进入 0-1 背包函数"}),
            ("exec", "dp[i][w] = 0", {"i": 0, "w": 0, "best": 0, "phase": "初始化第 0 行和第 0 列"}),
            ("exec", "dp[i][w] = max(", {"i": 1, "w": 4, "best": 1500, "phase": "考虑吉他后, 容量 4 的最优值是 1500"}),
            ("exec", "dp[i][w] = max(", {"i": 2, "w": 4, "best": 3000, "phase": "音响单独放入, 最优值变成 3000"}),
            ("exec", "dp[i][w] = max(", {"i": 3, "w": 4, "best": 3500, "phase": "笔记本加吉他得到 3500"}),
            ("exec", "dp[i][w] = max(", {"i": 4, "w": 4, "best": 4000, "phase": "手机加笔记本得到最终答案 4000"}),
            ("exit", "return dp[n][W]", {"_return": 4000, "phase": "返回最大价值 4000"}),
        ],
        "08_最长公共子序列": [
            ("enter", "int main(void)", {"X": "ABCB", "Y": "BDCAB", "phase": "准备两个字符串"}),
            ("enter", "int lcs_length", {"m": 4, "n": 5, "phase": "建立前缀 DP 表"}),
            ("exec", "dp[i][0] = 0", {"i": 0, "j": 0, "best": 0, "phase": "空串与任意字符串的 LCS 长度为 0"}),
            ("exec", "dp[i][j] = dp[i - 1][j - 1] + 1", {"i": 1, "j": 4, "best": 1, "phase": "A 与 A 匹配, 左上角加 1"}),
            ("exec", "dp[i][j] = dp[i - 1][j - 1] + 1", {"i": 2, "j": 5, "best": 2, "phase": "B 与 B 匹配, 长度推进到 2"}),
            ("exec", "dp[i][j] = dp[i - 1][j - 1] + 1", {"i": 4, "j": 5, "best": 3, "phase": "最后一个 B 匹配, 得到长度 3"}),
            ("exit", "return dp[m][n]", {"_return": 3, "phase": "返回 LCS 长度 3"}),
        ],
        "09_LCS方案还原": [
            ("enter", "int main(void)", {"X": "ABCB", "Y": "BDCAB", "phase": "先填完整 DP 表"}),
            ("enter", "int lcs_restore", {"m": 4, "n": 5, "phase": "DP 表右下角的答案是 3"}),
            ("exec", "int len = dp[m][n]", {"i": 4, "j": 5, "len": 3, "phase": "从右下角开始倒着找"}),
            ("exec", "result[--pos] = X[i - 1]", {"i": 4, "j": 5, "result": "B", "phase": "B 与 B 相同, 收集 B 并走向左上"}),
            ("exec", "result[--pos] = X[i - 1]", {"i": 3, "j": 3, "result": "CB", "phase": "C 与 C 相同, 收集 C"}),
            ("exec", "result[--pos] = X[i - 1]", {"i": 2, "j": 1, "result": "BCB", "phase": "B 与 B 相同, 收集最后一个 B"}),
            ("exit", "return len", {"_return": 3, "result": "BCB", "phase": "还原出一种 LCS: BCB"}),
        ],
    }

    if algo_id in manual:
        function_names = {
            "07_零一背包": "knapsack01",
            "08_最长公共子序列": "lcs_length",
            "09_LCS方案还原": "lcs_restore",
        }
        current_function = "main"
        steps = []
        for step_number, (step_type, fragment, variables) in enumerate(manual[algo_id]):
            if step_type == "enter" and fragment != "int main(void)":
                current_function = function_names[algo_id]
            step_function = current_function
            steps.append({
                "step": step_number,
                "line": line_of(fragment),
                "type": step_type,
                "func": step_function,
                "vars": variables,
            })
        curated = dict(algo)
        curated["steps"] = steps
        curated["program_output"] = {
            "07_零一背包": [{"after_step": len(steps), "text": "最大价值：4000"}],
            "08_最长公共子序列": [{"after_step": len(steps), "text": "LCS 长度：3"}],
            "09_LCS方案还原": [
                {"after_step": len(steps) - 1, "text": "LCS 长度：3"},
                {"after_step": len(steps), "text": "一种 LCS：BCB"},
            ],
        }[algo_id]
        curated["track_vars"] = {
            "primary": ["i", "j", "w", "best", "len", "result", "phase"],
            "secondary": ["X", "Y", "m", "n", "W", "_return"],
        }
        return normalize_output_steps(curated)

    steps = algo.get("steps", [])
    if len(steps) <= 180:
        return normalize_output_steps(algo)

    head = steps[:35]
    tail = steps[-15:]
    kept = head + tail
    if kept:
        first_vars = dict(kept[0].get("vars", {}))
        first_vars["phase"] = "已省略大量重复递归或循环, 保留开头与最终结果"
        kept[0]["vars"] = first_vars
        for step_number, step in enumerate(kept):
            step["step"] = step_number

    curated = dict(algo)
    curated["steps"] = kept
    return normalize_output_steps(curated)


def curate_ch09_code_demo(algo_id, algo):
    """空间优化和状压 DP 只保留能解释状态变化的关键执行步骤。"""
    source = algo.get("source", [])

    def line_of(fragment, fallback=1):
        if fragment.startswith("LAST:"):
            target = fragment[5:].strip()
            for reverse_index, line in enumerate(reversed(source)):
                if line.strip() == target:
                    return len(source) - reverse_index
        target = fragment.strip()
        for index, line in enumerate(source, start=1):
            if line.strip() == target:
                return index
        for index, line in enumerate(source, start=1):
            if fragment in line:
                return index
        return fallback

    manual = {
        "05_滚动数组": [
            ("enter", "int main(void)", "main", {"phase": "准备 4 件物品和容量 4 的背包"}),
            ("enter", "int knapsack_2d", "knapsack_2d", {"phase": "原始方案保存完整二维表"}),
            ("exec", "dp[i][w] = MAX", "knapsack_2d", {"i": 4, "w": 4, "best": 4000, "phase": "二维表得到最大价值 4000"}),
            ("exit", "return dp[n][W]", "knapsack_2d", {"_return": 4000, "phase": "二维版本完成"}),
            ("exec", "printf(\"二维 DP", "main", {"best": 4000, "phase": "输出二维版本结果"}),
            ("enter", "int knapsack_rolling", "knapsack_rolling", {"phase": "第一层优化只保留 pre 和 cur 两行"}),
            ("exec", "int cur = i % 2", "knapsack_rolling", {"i": 1, "pre": 0, "cur": 1, "phase": "第 1 轮: 第 0 行是 pre, 第 1 行是 cur"}),
            ("exec", "int cur = i % 2", "knapsack_rolling", {"i": 2, "pre": 1, "cur": 0, "phase": "第 2 轮: 两行身份交换"}),
            ("exit", "return dp[n % 2][W]", "knapsack_rolling", {"_return": 4000, "best": 4000, "phase": "两行滚动仍得到 4000"}),
            ("exec", "printf(\"两行滚动", "main", {"best": 4000, "phase": "输出两行滚动结果"}),
            ("enter", "int knapsack_1d", "knapsack_1d", {"phase": "第二层优化压成一维数组"}),
            ("exec", "for (int w = W; w >= wt[i]; w--)", "knapsack_1d", {"i": 0, "w": 4, "phase": "容量倒序, 先处理右侧格子"}),
            ("exec", "dp[w] = MAX", "knapsack_1d", {"i": 3, "w": 4, "best": 4000, "phase": "倒序保证读到上一轮旧值"}),
            ("exit", "return dp[W]", "knapsack_1d", {"_return": 4000, "best": 4000, "phase": "一维版本仍得到 4000"}),
            ("exec", "printf(\"一维压缩", "main", {"best": 4000, "phase": "三个版本结果完全一致"}),
            ("exit", "return 0", "main", {"_return": 0, "phase": "程序结束"}),
        ],
        "06_状态压缩_位运算": [
            ("enter", "int main(void)", "main", {"phase": "打印 4 个城市的距离矩阵"}),
            ("exec", "printf(\"城市距离矩阵", "main", {"phase": "距离矩阵准备完成"}),
            ("enter", "int tsp(void)", "tsp", {"phase": "进入状态压缩 DP"}),
            ("exec", "dp[1][0] = 0", "tsp", {"mask": "0001", "i": 0, "cost": 0, "phase": "只访问城市 0, 当前也在城市 0"}),
            ("exec", "int nextMask = mask | (1 << j)", "tsp", {"mask": "0011", "i": 1, "cost": 10, "phase": "从 0 到 1, 打开第 1 个 bit"}),
            ("exec", "int nextMask = mask | (1 << j)", "tsp", {"mask": "0101", "i": 2, "cost": 15, "phase": "另一条状态从 0 到 2"}),
            ("exec", "int nextMask = mask | (1 << j)", "tsp", {"mask": "1011", "i": 3, "cost": 35, "phase": "状态记录已访问 0、1、3"}),
            ("exec", "dp[nextMask][j] = newDist", "tsp", {"mask": "1111", "i": 2, "cost": 65, "phase": "四个城市都已访问"}),
            ("exec", "int total = dp[all][i] + dist[i][0]", "tsp", {"mask": "1111", "i": 2, "cost": 80, "phase": "最后从城市 2 回到起点 0"}),
            ("exit", "return answer", "tsp", {"_return": 80, "cost": 80, "phase": "最短环路长度是 80"}),
            ("exec", "printf(\"\\nTSP", "main", {"best": 80, "phase": "输出最短路径长度和状态规模"}),
            ("exit", "return 0", "main", {"_return": 0, "phase": "程序结束"}),
        ],
    }

    if algo_id not in manual:
        return algo

    steps = []
    for step_number, (step_type, fragment, function_name, variables) in enumerate(manual[algo_id]):
        steps.append({
            "step": step_number,
            "line": line_of(fragment),
            "type": step_type,
            "func": function_name,
            "vars": variables,
        })

    curated = dict(algo)
    curated["steps"] = steps
    curated["program_output"] = {
        "05_滚动数组": [
            {"after_step": 5, "text": "二维 DP（O(nW) 空间）：最大价值 = 4000"},
            {"after_step": 10, "text": "两行滚动（O(W) 空间）：最大价值 = 4000"},
            {"after_step": 15, "text": "一维压缩（O(W) 空间）：最大价值 = 4000"},
        ],
        "06_状态压缩_位运算": [
            {"after_step": 2, "text": "城市距离矩阵：0 10 15 20 / 10 0 35 25 / 15 35 0 30 / 20 25 30 0"},
            {"after_step": 11, "text": "TSP 最短路径（状态压缩DP）：80；状态总数：16"},
        ],
    }[algo_id]
    curated["track_vars"] = {
        "primary": ["i", "w", "mask", "cost", "best", "phase"],
        "secondary": ["pre", "cur", "_return"],
    }
    return curated


def curate_ch10_code_demo(algo_id, algo):
    """回溯章展示选择、冲突、撤销和结果，不机械播放整棵搜索树。"""
    if algo_id == "04_子集生成":
        curated = dict(algo)
        curated["program_output"] = [
            {"after_step": 9, "text": "{}"},
            {"after_step": 13, "text": "{3}"},
            {"after_step": 18, "text": "{2}"},
            {"after_step": 21, "text": "{2, 3}"},
            {"after_step": 30, "text": "{1}"},
            {"after_step": 33, "text": "{1, 3}"},
            {"after_step": 40, "text": "{1, 2}"},
            {"after_step": 45, "text": "{1, 2, 3}"},
        ]
        return curated

    source = algo.get("source", [])

    def line_of(fragment, fallback=1):
        if fragment.startswith("LAST:"):
            target = fragment[5:].strip()
            for reverse_index, line in enumerate(reversed(source)):
                if line.strip() == target:
                    return len(source) - reverse_index
        target = fragment.strip()
        for index, line in enumerate(source, start=1):
            if line.strip() == target:
                return index
        for index, line in enumerate(source, start=1):
            if fragment in line:
                return index
        return fallback

    queen_steps = [
        ("enter", "int main(void)", "main", {"phase": "从第 0 行开始放置 4 个皇后"}),
        ("enter", "void backtrack", "backtrack", {"row": 0, "phase": "每一行尝试一个列位置"}),
        ("exec", "pos[row] = col;", "backtrack", {"row": 0, "col": 0, "phase": "第 0 行先尝试第 0 列"}),
        ("exec", "continue", "backtrack", {"row": 1, "col": 0, "phase": "同列冲突, 剪掉这个位置"}),
        ("exec", "pos[row] = col;", "backtrack", {"row": 1, "col": 2, "phase": "第 1 行尝试第 2 列"}),
        ("exec", "backtrack(row + 1)", "backtrack", {"row": 2, "phase": "继续深入后发现无处可放, 回退换列"}),
        ("exec", "print_board();", "backtrack", {"row": 4, "solution_count": 1, "pos": [1, 3, 0, 2], "phase": "找到第 1 组解"}),
        ("exec", "print_board();", "backtrack", {"row": 4, "solution_count": 2, "pos": [2, 0, 3, 1], "phase": "找到第 2 组解"}),
        ("exit", "return;", "backtrack", {"_return": None, "phase": "搜索树遍历完成"}),
        ("exec", "printf(\"总解数", "main", {"solution_count": 2, "phase": "输出 4 皇后的总解数"}),
        ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "程序结束"}),
    ]

    manual = {
        "05_N皇后_基础版": queen_steps,
        "07_N皇后_对角线优化": [
            ("enter", "int main(void)", "main", {"phase": "用三张标记表加速冲突判断"}),
            ("enter", "void backtrack", "backtrack", {"row": 0, "phase": "从第 0 行开始"}),
            ("exec", "int d1 = row - col + n", "backtrack", {"row": 0, "col": 0, "d1": 4, "d2": 0, "phase": "把列和两条对角线换成数组下标"}),
            ("exec", "col_used[col] = 1", "backtrack", {"row": 0, "col": 1, "phase": "做选择时同时标记列和对角线"}),
            ("exec", "continue", "backtrack", {"row": 1, "col": 1, "phase": "标记表命中, O(1) 判断冲突"}),
            ("exec", "print_board();", "backtrack", {"row": 4, "solution_count": 1, "pos": [1, 3, 0, 2], "phase": "找到第 1 组解"}),
            ("exec", "diag2_used[d2] = 0", "backtrack", {"row": 2, "phase": "回溯时撤销三张标记表"}),
            ("exec", "print_board();", "backtrack", {"row": 4, "solution_count": 2, "pos": [2, 0, 3, 1], "phase": "找到第 2 组解"}),
            ("exit", "return;", "backtrack", {"_return": None, "phase": "搜索完成"}),
            ("exec", "printf(\"总解数", "main", {"solution_count": 2, "phase": "输出总解数 2"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "程序结束"}),
        ],
        "08_数独求解": [
            ("enter", "int main(void)", "main", {"phase": "载入书稿中的 9×9 数独"}),
            ("enter", "bool solve_sudoku", "solve_sudoku", {"row": 0, "col": 2, "phase": "按顺序找到第一个空格"}),
            ("exec", "for (int num = 1", "solve_sudoku", {"row": 0, "col": 2, "num": 1, "phase": "从 1 开始尝试候选数字"}),
            ("exec", "continue", "solve_sudoku", {"row": 0, "col": 2, "num": 1, "phase": "1 与当前列冲突, 立即跳过"}),
            ("exec", "board[i][j] = num", "solve_sudoku", {"row": 0, "col": 2, "num": 4, "phase": "4 合法, 写入格子并递归深入"}),
            ("exec", "if (solve_sudoku())", "solve_sudoku", {"row": 0, "col": 3, "phase": "继续寻找下一个空格"}),
            ("exec", "board[i][j] = 0", "solve_sudoku", {"row": 0, "col": 3, "num": 2, "phase": "后续走不通, 撤销刚才的选择"}),
            ("exec", "board[i][j] = num", "solve_sudoku", {"row": 0, "col": 3, "num": 6, "phase": "换一个候选后继续深入"}),
            ("exit", "LAST:return true;", "solve_sudoku", {"_return": 1, "phase": "所有空格填完, 找到可行解"}),
            ("exec", "printf(\"解出的数独", "main", {"phase": "打印完整数独"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "程序结束"}),
        ],
    }

    if algo_id not in manual:
        return algo

    specs = manual[algo_id]
    steps = []
    for step_number, (step_type, fragment, function_name, variables) in enumerate(specs):
        steps.append({
            "step": step_number,
            "line": line_of(fragment),
            "type": step_type,
            "func": function_name,
            "vars": variables,
        })

    solution_one = "第 1 组解：. Q . . / . . . Q / Q . . . / . . Q ."
    solution_two = "第 2 组解：. . Q . / Q . . . / . . . Q / . Q . ."
    sudoku_output = (
        "解出的数独：5 3 4 6 7 8 9 1 2 / 6 7 2 1 9 5 3 4 8 / "
        "1 9 8 3 4 2 5 6 7 / 8 5 9 7 6 1 4 2 3 / 4 2 6 8 5 3 7 9 1 / "
        "7 1 3 9 2 4 8 5 6 / 9 6 1 5 3 7 2 8 4 / 2 8 7 4 1 9 6 3 5 / "
        "3 4 5 2 8 6 1 7 9"
    )
    if algo_id == "08_数独求解":
        outputs = [{"after_step": 10, "text": sudoku_output}]
    else:
        outputs = [
            {"after_step": 7 if algo_id == "05_N皇后_基础版" else 6, "text": solution_one},
            {"after_step": 8 if algo_id == "05_N皇后_基础版" else 8, "text": solution_two},
            {"after_step": 10, "text": "总解数：2"},
        ]

    curated = dict(algo)
    curated["steps"] = steps
    curated["program_output"] = outputs
    curated["track_vars"] = {
        "primary": ["row", "col", "num", "solution_count", "phase"],
        "secondary": ["d1", "d2", "pos", "_return"],
    }
    return curated


def curate_ch11_code_demo(algo_id, algo):
    """分支限界只展示界、队列、更新最优值和剪枝的关键节点。"""
    source = algo.get("source", [])

    def line_of(fragment, fallback=1):
        if fragment.startswith("LAST:"):
            target = fragment[5:].strip()
            for reverse_index, line in enumerate(reversed(source)):
                if line.strip() == target:
                    return len(source) - reverse_index
        target = fragment.strip()
        for index, line in enumerate(source, start=1):
            if line.strip() == target:
                return index
        for index, line in enumerate(source, start=1):
            if fragment in line:
                return index
        return fallback

    manual = {
        "01_零一背包_分支限界": [
            ("enter", "int main(void)", "main", {"phase": "按单位价值从高到低整理 4 件物品"}),
            ("exec", "qsort(items", "main", {"phase": "排序后才能用分数背包计算紧上界"}),
            ("enter", "int knapsack_bb", "knapsack_bb", {"best": 0, "phase": "建立按上界从大到小的优先队列"}),
            ("exec", "root->ub = calc_ub", "knapsack_bb", {"level": 0, "weight": 0, "value": 0, "ub": 38, "phase": "根节点上界为 38"}),
            ("exec", "Node *cur = pq_pop", "knapsack_bb", {"level": 0, "queue": "root", "ub": 38, "phase": "先扩展上界最大的节点"}),
            ("exec", "yes->selected[i] = 1", "knapsack_bb", {"level": 1, "weight": 2, "value": 10, "ub": 38, "phase": "选择物品 1, 该分支仍有希望达到 38"}),
            ("exec", "yes->selected[i] = 1", "knapsack_bb", {"level": 2, "weight": 6, "value": 20, "ub": 38, "phase": "继续选择物品 2"}),
            ("exec", "no->selected[i] = 0", "knapsack_bb", {"level": 3, "weight": 6, "value": 20, "ub": 38, "phase": "物品 3 不选, 给物品 4 留容量"}),
            ("exec", "yes->selected[i] = 1", "knapsack_bb", {"level": 4, "weight": 15, "value": 38, "ub": 38, "phase": "加入物品 4, 找到真实价值 38"}),
            ("exec", "best_value = cur->value", "knapsack_bb", {"best": 38, "phase": "更新当前最优解为 38"}),
            ("exec", "if (cur->ub <= best_value)", "knapsack_bb", {"ub": 36, "best": 38, "phase": "其他分支上界不超过 38, 整棵子树剪掉"}),
            ("exit", "return (int)best_value", "knapsack_bb", {"_return": 38, "best": 38, "phase": "返回最大价值 38"}),
            ("exec", "printf(\"最大价值", "main", {"best": 38, "phase": "输出物品 1、2、4 和总重量 15 kg"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "程序结束"}),
        ],
        "02_旅行商_分支限界": [
            ("enter", "int main(void)", "main", {"phase": "载入书稿中的 5 城市距离矩阵"}),
            ("enter", "double tsp_bb", "tsp_bb", {"best": "∞", "phase": "建立按下界从小到大的优先队列"}),
            ("exec", "root->lb = calc_lb", "tsp_bb", {"path": "A", "cost": 0, "lb": 18, "phase": "根节点安全下界为 18"}),
            ("exec", "Node *cur = pq_pop", "tsp_bb", {"path": "A", "lb": 18, "phase": "优先扩展下界最小的路线"}),
            ("exec", "child->path[cur->level] = next", "tsp_bb", {"path": "A-D", "cost": 2, "lb": 15, "phase": "第一站去 D 的节点最有希望"}),
            ("exec", "child->path[cur->level] = next", "tsp_bb", {"path": "A-D-E", "cost": 8, "lb": 18, "phase": "继续扩展到 E"}),
            ("exec", "child->path[cur->level] = next", "tsp_bb", {"path": "A-D-E-B", "cost": 11, "lb": 18, "phase": "再走到 B, 只剩 C"}),
            ("exec", "double total = cur->cost + dist[last][0]", "tsp_bb", {"path": "A-D-E-B-C-A", "cost": 21, "phase": "补上回到 A 的边, 得到完整回路 21"}),
            ("exec", "best_cost = total", "tsp_bb", {"best": 21, "path": "A-D-E-B-C-A", "phase": "更新当前最短距离为 21"}),
            ("exec", "if (cur->lb >= best_cost)", "tsp_bb", {"lb": 22, "best": 21, "phase": "下界不小于 21 的路线不可能更短, 剪枝"}),
            ("exit", "return best_cost", "tsp_bb", {"_return": 21, "best": 21, "phase": "优先队列清空, 最短距离确定"}),
            ("exec", "printf(\"TSP最优路径", "main", {"path": "A-D-E-B-C-A", "best": 21, "phase": "输出一种最优回路"}),
            ("exec", "printf(\"最短距离", "main", {"best": 21, "phase": "输出最短距离 21"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "程序结束"}),
        ],
    }

    if algo_id not in manual:
        return algo

    steps = []
    for step_number, (step_type, fragment, function_name, variables) in enumerate(manual[algo_id]):
        steps.append({
            "step": step_number,
            "line": line_of(fragment),
            "type": step_type,
            "func": function_name,
            "vars": variables,
        })

    curated = dict(algo)
    curated["steps"] = steps
    curated["program_output"] = {
        "01_零一背包_分支限界": [
            {"after_step": 2, "text": "按单位价值排序：物品1、物品2、物品3、物品4"},
            {"after_step": 13, "text": "最大价值：38 万元；选择物品：1、2、4；总重量：15 kg / 15 kg"},
        ],
        "02_旅行商_分支限界": [
            {"after_step": 13, "text": "TSP最优路径：A -> D -> E -> B -> C -> A；最短距离：21"},
        ],
    }[algo_id]
    curated["track_vars"] = {
        "primary": ["level", "weight", "value", "ub", "lb", "cost", "best", "phase"],
        "secondary": ["path", "queue", "_return"],
    }
    return curated


def curate_ch12_code_demo(algo_id, algo):
    """图论进阶用书中样例展示关键状态，输入代码仍保持通用。"""
    source = algo.get("source", [])

    def line_of(fragment, fallback=1):
        if fragment.startswith("LAST:"):
            target = fragment[5:].strip()
            for reverse_index, line in enumerate(reversed(source)):
                if line.strip() == target:
                    return len(source) - reverse_index
        target = fragment.strip()
        for index, line in enumerate(source, start=1):
            if line.strip() == target:
                return index
        for index, line in enumerate(source, start=1):
            if fragment in line:
                return index
        return fallback

    manual = {
        "01_Tarjan强连通分量": [
            ("enter", "int main(void)", "main", {"phase": "输入 5 个节点和 5 条有向边"}),
            ("enter", "void tarjan", "tarjan", {"u": 1, "phase": "从节点 1 开始 DFS"}),
            ("exec", "dfn[u] = low[u]", "tarjan", {"u": 1, "dfn": 1, "low": 1, "phase": "给节点 1 打时间戳并入栈"}),
            ("exec", "tarjan(v)", "tarjan", {"u": 2, "stack": [1, 2, 3, 4, 5], "phase": "沿 1→2→3→4→5 深入"}),
            ("exec", "low[u] = dfn[v]", "tarjan", {"u": 5, "v": 2, "low": 2, "phase": "5→2 是返祖边, low[5] 更新为 2"}),
            ("exec", "if (dfn[u] == low[u])", "tarjan", {"u": 2, "scc": [5, 4, 3, 2], "phase": "节点 2 收口, 弹出一个强连通分量"}),
            ("exec", "if (dfn[u] == low[u])", "tarjan", {"u": 1, "scc": [1], "phase": "节点 1 单独形成一个强连通分量"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "共找到 2 个强连通分量"}),
        ],
        "02_EdmondsKarp最大流": [
            ("enter", "int main(void)", "main", {"phase": "输入书稿中的 5 节点、6 条边网络"}),
            ("enter", "long long edmonds_karp", "edmonds_karp", {"max_flow": 0, "phase": "在残余图中反复用 BFS 找增广路"}),
            ("exec", "while (bfs(s, t, n))", "edmonds_karp", {"path": "s→B→t", "path_flow": 3, "phase": "第一轮 BFS 先找到边数更少的 s→B→t"}),
            ("exec", "max_flow += path_flow", "edmonds_karp", {"max_flow": 3, "phase": "瓶颈 3, 累计最大流 3"}),
            ("exec", "while (bfs(s, t, n))", "edmonds_karp", {"path": "s→A→C→t", "path_flow": 2, "phase": "第二轮增广 s→A→C→t"}),
            ("exec", "max_flow += path_flow", "edmonds_karp", {"max_flow": 5, "phase": "瓶颈 2, 累计最大流 5"}),
            ("exec", "while (bfs(s, t, n))", "edmonds_karp", {"path": "s→B→C→t", "path_flow": 2, "phase": "第三轮增广 s→B→C→t"}),
            ("exec", "max_flow += path_flow", "edmonds_karp", {"max_flow": 7, "phase": "再送 2, 最大流达到 7"}),
            ("exit", "return max_flow", "edmonds_karp", {"_return": 7, "max_flow": 7, "phase": "BFS 再也找不到增广路"}),
            ("enter", "void find_min_cut", "find_min_cut", {"phase": "在最终残余图中从 s 再做一次 BFS"}),
            ("exec", "LAST:if (!visited[v] && capacity[u][v] - flow[u][v] > 0) {", "find_min_cut", {"S": [0, 1], "T": [2, 3, 4], "phase": "可达集合 S={s,A}, 其余属于 T"}),
            ("exec", "cut_capacity += capacity[u][v]", "find_min_cut", {"cut_edges": ["s→B(5)", "A→C(2)"], "cut_capacity": 7, "phase": "回到原图统计 S→T 的割边"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "最大流与最小割容量都等于 7"}),
        ],
        "03_匈牙利算法_二分匹配": [
            ("enter", "int main(void)", "main", {"phase": "输入 3 名学生、3 门课程和 4 条关系"}),
            ("enter", "int hungarian(void)", "hungarian", {"count": 0, "phase": "依次为每名学生寻找课程"}),
            ("enter", "int dfs(int u)", "dfs", {"u": 1, "phase": "学生 1 直接匹配课程 1"}),
            ("exec", "match[v] = u", "dfs", {"u": 1, "v": 1, "match": "1↔1", "phase": "课程 1 还空着, 匹配成功"}),
            ("exec", "match[v] = u", "dfs", {"u": 2, "v": 2, "match": "2↔2", "phase": "学生 2 先匹配课程 2"}),
            ("exec", "if (match[v] == 0 || dfs(match[v]))", "dfs", {"u": 3, "v": 2, "phase": "学生 3 也想选课程 2, 递归请学生 2 让位"}),
            ("exec", "match[v] = u", "dfs", {"u": 2, "v": 3, "match": "2↔3", "phase": "学生 2 改选课程 3"}),
            ("exec", "match[v] = u", "dfs", {"u": 3, "v": 2, "match": "3↔2", "phase": "课程 2 腾出, 学生 3 匹配成功"}),
            ("exit", "return count", "hungarian", {"_return": 3, "count": 3, "phase": "最大匹配数为 3"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "输出完整匹配方案"}),
        ],
    }

    if algo_id not in manual:
        return algo

    steps = []
    for step_number, (step_type, fragment, function_name, variables) in enumerate(manual[algo_id]):
        steps.append({
            "step": step_number,
            "line": line_of(fragment),
            "type": step_type,
            "func": function_name,
            "vars": variables,
        })

    curated = dict(algo)
    curated["steps"] = steps
    curated["program_output"] = {
        "01_Tarjan强连通分量": [
            {"after_step": 7, "text": "强连通分量 #1：5 4 3 2；强连通分量 #2：1；共找到 2 个强连通分量"},
        ],
        "02_EdmondsKarp最大流": [
            {"after_step": 9, "text": "最大流：7"},
            {"after_step": 13, "text": "S={0,1}，T={2,3,4}；最小割边：0→2(5)、1→3(2)；最小割容量：7"},
        ],
        "03_匈牙利算法_二分匹配": [
            {"after_step": 9, "text": "最大匹配数：3；学生1↔课程1，学生3↔课程2，学生2↔课程3"},
        ],
    }[algo_id]
    curated["track_vars"] = {
        "primary": ["u", "v", "dfn", "low", "max_flow", "path_flow", "count", "phase"],
        "secondary": ["stack", "scc", "path", "S", "T", "cut_edges", "match", "_return"],
    }
    return curated


def curate_ch13_code_demo(algo_id, algo):
    """最短路径代码执行只保留算法发生变化的关键节点。"""
    source = algo.get("source", [])

    def line_of(fragment, fallback=1):
        if fragment.startswith("LAST:"):
            target = fragment[5:].strip()
            for reverse_index, line in enumerate(reversed(source)):
                if line.strip() == target:
                    return len(source) - reverse_index
        target = fragment.strip()
        for index, line in enumerate(source, start=1):
            if line.strip() == target:
                return index
        for index, line in enumerate(source, start=1):
            if fragment in line:
                return index
        return fallback

    manual = {
        "01_Dijkstra_朴素版": [
            ("enter", "int main(void)", "main", {"phase": "载入 5 个顶点、9 条非负有向边"}),
            ("enter", "void dijkstra", "dijkstra", {"src": 0, "phase": "起点 0 距离为 0, 其余为 INF"}),
            ("exec", "visited[u] = 1", "dijkstra", {"u": 0, "dist": [0, "INF", "INF", "INF", "INF"], "phase": "选出当前最近的顶点 0 并定案"}),
            ("exec", "dist[v] = newDist", "dijkstra", {"u": 0, "v": 2, "dist": [0, 10, 3, "INF", "INF"], "phase": "由 0 松弛得到 dist[1]=10、dist[2]=3"}),
            ("exec", "visited[u] = 1", "dijkstra", {"u": 2, "dist": [0, 10, 3, "INF", "INF"], "phase": "未确定点中顶点 2 最近, 下一步处理它"}),
            ("exec", "dist[v] = newDist", "dijkstra", {"u": 2, "v": 4, "dist": [0, 7, 3, 11, 5], "phase": "顶点 2 把 1、3、4 的距离继续改短"}),
            ("exec", "dist[v] = newDist", "dijkstra", {"u": 1, "v": 3, "dist": [0, 7, 3, 9, 5], "phase": "经顶点 1 到 3 只需 9, 替换原来的 11"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "dist": [0, 7, 3, 9, 5], "phase": "所有顶点的最短距离确定"}),
        ],
        "02_Dijkstra_堆优化版": [
            ("enter", "int main(void)", "main", {"phase": "邻接表只保存真实存在的 9 条边"}),
            ("enter", "void dijkstra_heap", "dijkstra_heap", {"src": 0, "phase": "把起点 0:0 压入最小堆"}),
            ("exec", "HeapNode cur = pop_min()", "dijkstra_heap", {"u": 0, "heap": "[]", "phase": "从堆顶直接取出当前最近点 0"}),
            ("exec", "push(v, dist[v])", "dijkstra_heap", {"u": 0, "heap": ["2:3", "1:10"], "dist": [0, 10, 3, "INF", "INF"], "phase": "松弛后把新距离压入堆"}),
            ("exec", "push(v, dist[v])", "dijkstra_heap", {"u": 2, "heap": ["4:5", "1:7", "3:11", "1:10"], "dist": [0, 7, 3, 11, 5], "phase": "顶点 2 产生更短的候选距离"}),
            ("exec", "if (visited[u]) continue", "dijkstra_heap", {"u": 1, "phase": "旧的 1:10 以后弹出时会被跳过"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "dist": [0, 7, 3, 9, 5], "phase": "答案与朴素版一致, 但不再反复扫描全部顶点"}),
        ],
        "03_BellmanFord_负权边": [
            ("enter", "int main(void)", "main", {"phase": "边集含 8 条边, 其中有负权边"}),
            ("enter", "void bellman_ford", "bellman_ford", {"src": 0, "phase": "起点为 0, 开始逐边松弛"}),
            ("exec", "dist[v] = dist[u] + w", "bellman_ford", {"round": 1, "dist": [0, -1, 4, "INF", "INF"], "phase": "先由 0 得到顶点 1 和 2 的距离"}),
            ("exec", "dist[v] = dist[u] + w", "bellman_ford", {"round": 1, "dist": [0, -1, 2, 1, 1], "phase": "继续扫描边, 传播到 2、3、4"}),
            ("exec", "dist[v] = dist[u] + w", "bellman_ford", {"round": 1, "dist": [0, -1, 2, -2, 1], "phase": "负权边 4→3=-3 把 dist[3] 改成 -2"}),
            ("exec", "if (!updated) break", "bellman_ford", {"round": 3, "phase": "一整轮没有更新, 可以提前结束"}),
            ("exec", "for (int j = 0; j < E; j++)", "bellman_ford", {"phase": "额外扫描一轮, 确认没有可达负权环"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "dist": [0, -1, 2, -2, 1], "phase": "输出稳定的最短距离"}),
        ],
        "04_SPFA_队列优化": [
            ("enter", "int main(void)", "main", {"phase": "使用与 Bellman-Ford 相同的负权边样例"}),
            ("enter", "void spfa", "spfa", {"src": 0, "queue": [0], "phase": "起点 0 入队"}),
            ("exec", "int u = queue[front]", "spfa", {"u": 0, "queue": [], "phase": "顶点 0 出队, 只通知自己的邻居"}),
            ("exec", "dist[v] = dist[u] + w", "spfa", {"u": 0, "dist": [0, -1, 4, "INF", "INF"], "phase": "顶点 1、2 的距离变短"}),
            ("exec", "queue[rear] = v", "spfa", {"queue": [1, 2], "phase": "只有发生变化的顶点才入队"}),
            ("exec", "dist[v] = dist[u] + w", "spfa", {"u": 1, "dist": [0, -1, 2, 1, 1], "phase": "顶点 1 把变化继续传给 2、3、4"}),
            ("exec", "dist[v] = dist[u] + w", "spfa", {"u": 4, "dist": [0, -1, 2, -2, 1], "phase": "负权边 4→3=-3 生效"}),
            ("exec", "while (qSize > 0)", "spfa", {"queue": [], "phase": "队列清空, 没有更多变化"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "dist": [0, -1, 2, -2, 1], "phase": "输出与 Bellman-Ford 相同的答案"}),
        ],
        "05_FloydWarshall_核心": [
            ("enter", "int main(void)", "main", {"phase": "初始化 4×4 距离矩阵"}),
            ("enter", "void floyd", "floyd", {"phase": "按顺序开放中转站 k"}),
            ("exec", "dist[i][j] = dist[i][k] + dist[k][j]", "floyd", {"k": 1, "i": 0, "j": 2, "value": 8, "phase": "经顶点 1, 0→2 从不可达变成 8"}),
            ("exec", "dist[i][j] = dist[i][k] + dist[k][j]", "floyd", {"k": 2, "i": 0, "j": 3, "value": 9, "phase": "经顶点 2, 0→3 从 10 改成 9"}),
            ("exec", "dist[i][j] = dist[i][k] + dist[k][j]", "floyd", {"k": 2, "i": 1, "j": 3, "value": 4, "phase": "经顶点 2, 1→3 从不可达变成 4"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "得到任意两点之间的最短距离矩阵"}),
        ],
        "06_FloydWarshall_初始化": [
            ("enter", "int main(void)", "main", {"phase": "准备 5×5 的图和距离矩阵"}),
            ("exec", "dist[i][j] = 0", "main", {"i": 2, "j": 2, "value": 0, "phase": "自己到自己填 0"}),
            ("exec", "dist[i][j] = graph[i][j]", "main", {"i": 0, "j": 4, "value": -4, "phase": "有直达边就复制边权"}),
            ("exec", "dist[i][j] = INF", "main", {"i": 0, "j": 3, "value": "INF", "phase": "没有直达边的位置填 INF"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "Floyd 的初始距离矩阵准备完成"}),
        ],
        "07_AStar_启发搜索": [
            ("enter", "int main(void)", "main", {"phase": "载入 5 个带坐标的顶点"}),
            ("enter", "void a_star", "a_star", {"src": 0, "dest": 4, "phase": "g 记录已走代价, h 估计剩余距离"}),
            ("exec", "f[src] = heuristic", "a_star", {"u": 0, "g": 0, "h": 6, "f": 6, "phase": "起点的优先级 f=g+h=6"}),
            ("exec", "closed[u] = 1", "a_star", {"u": 0, "phase": "取 f 最小的顶点 0 并展开"}),
            ("exec", "f[v] = newG + heuristic", "a_star", {"u": 0, "v": 1, "g": 2, "h": 4, "f": 6, "phase": "顶点 1 兼顾已走距离和目标方向"}),
            ("exec", "f[v] = newG + heuristic", "a_star", {"u": 1, "v": 2, "g": 3, "h": 2, "f": 5, "phase": "经 1 到 2 的路线更有希望"}),
            ("exec", "parent[v] = u", "a_star", {"u": 2, "v": 4, "g": 8, "h": 0, "f": 8, "phase": "到达目标 4, 同时记录父节点"}),
            ("exec", "for (int v = dest; v != -1; v = parent[v])", "a_star", {"path": [0, 1, 2, 4], "phase": "沿 parent 反向还原路径"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "distance": 8, "phase": "最短距离为 8, 路径为 0→1→2→4"}),
        ],
    }

    if algo_id not in manual:
        return algo

    steps = []
    for step_number, (step_type, fragment, function_name, variables) in enumerate(manual[algo_id]):
        steps.append({
            "step": step_number,
            "line": line_of(fragment),
            "type": step_type,
            "func": function_name,
            "vars": variables,
        })

    outputs = {
        "01_Dijkstra_朴素版": "从顶点 0 出发：0=0，1=7，2=3，3=9，4=5",
        "02_Dijkstra_堆优化版": "堆优化 Dijkstra：0=0，1=7，2=3，3=9，4=5",
        "03_BellmanFord_负权边": "Bellman-Ford：0=0，1=-1，2=2，3=-2，4=1",
        "04_SPFA_队列优化": "SPFA：0=0，1=-1，2=2，3=-2，4=1",
        "05_FloydWarshall_核心": "Floyd：0 5 8 9 / INF 0 3 4 / INF INF 0 1 / INF INF INF 0",
        "06_FloydWarshall_初始化": "初始化矩阵：0 3 8 INF -4 / INF 0 INF 1 7 / INF 4 0 INF INF / 2 INF -5 0 INF / INF INF INF 6 0",
        "07_AStar_启发搜索": "从 0 到 4 的最短距离：8；路径：0→1→2→4",
    }

    curated = dict(algo)
    curated["steps"] = steps
    curated["program_output"] = [{"after_step": len(steps), "text": outputs[algo_id]}]
    curated["track_vars"] = {
        "primary": ["u", "v", "dist", "queue", "heap", "k", "i", "j", "g", "h", "f", "phase"],
        "secondary": ["round", "path", "value", "distance", "_return"],
    }
    return curated


def curate_ch14_code_demo(algo_id, algo):
    """字符串匹配保留对齐、失配、跳转和命中的关键步骤。"""
    source = algo.get("source", [])

    def line_of(fragment, fallback=1):
        if fragment.startswith("LAST:"):
            target = fragment[5:].strip()
            for reverse_index, line in enumerate(reversed(source)):
                if line.strip() == target:
                    return len(source) - reverse_index
        target = fragment.strip()
        for index, line in enumerate(source, start=1):
            if line.strip() == target:
                return index
        for index, line in enumerate(source, start=1):
            if fragment in line:
                return index
        return fallback

    manual = {
        "01_暴力匹配_BF": [
            ("enter", "int main(void)", "main", {"phase": "文本长度 19, 模式串长度 9"}),
            ("enter", "int bf_search", "bf_search", {"i": 0, "j": 0, "phase": "先把模式串与文本开头对齐"}),
            ("exec", "if (text[i + j] != pattern[j])", "bf_search", {"i": 0, "j": 4, "compare": "D≠C", "phase": "前 4 个字符相同, 第 5 个字符失配"}),
            ("exec", "for (int i = 0; i <= n - m; i++)", "bf_search", {"i": 1, "phase": "BF 只向右移动一格, 再从模式串开头比较"}),
            ("exec", "if (text[i + j] != pattern[j])", "bf_search", {"i": 5, "j": 3, "phase": "继续逐个起点尝试, 已匹配信息不会被保留"}),
            ("exec", "if (j == m)", "bf_search", {"i": 10, "j": 9, "phase": "移动到位置 10 时, 9 个字符全部匹配"}),
            ("exit", "return i", "bf_search", {"_return": 10, "phase": "返回首次出现位置 10"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "程序结束"}),
        ],
        "02_KMP_next数组": [
            ("enter", "int main(void)", "main", {"pattern": "ABABCABAB", "phase": "为模式串构建哨兵版 next 数组"}),
            ("enter", "void build_next", "build_next", {"i": 0, "j": -1, "next": [-1], "phase": "next[0]=-1 表示已经无处可退"}),
            ("exec", "next[i] = j", "build_next", {"i": 1, "j": 0, "next": [-1, 0], "phase": "得到 next[1]=0"}),
            ("exec", "j = next[j]", "build_next", {"i": 1, "j": -1, "phase": "B≠A, 候选前缀退到哨兵"}),
            ("exec", "next[i] = j", "build_next", {"i": 4, "j": 2, "next": [-1, 0, 0, 1, 2], "phase": "ABAB 的最长相等真前后缀是 AB"}),
            ("exec", "j = next[j]", "build_next", {"i": 4, "j": 0, "phase": "C 与候选前缀失配, 连续缩短候选"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "next": [-1, 0, 0, 1, 2, 0, 1, 2, 3], "phase": "完整 next 数组构建完成"}),
        ],
        "03_KMP_匹配过程": [
            ("enter", "int main(void)", "main", {"phase": "文本和模式串与 BF 使用同一组样例"}),
            ("enter", "int kmp_search", "kmp_search", {"i": 0, "j": 0, "phase": "先构建 next, 再开始匹配"}),
            ("exec", "i++;", "kmp_search", {"i": 4, "j": 4, "phase": "文本前 4 个字符 ABAB 匹配"}),
            ("exec", "j = next[j]", "kmp_search", {"i": 4, "j": 2, "compare": "D≠C", "phase": "失配时 i 不回退, j 从 4 跳到 next[4]=2"}),
            ("exec", "j = next[j]", "kmp_search", {"i": 4, "j": 0, "phase": "仍不匹配, 模式串继续按 next 回退"}),
            ("exec", "i++;", "kmp_search", {"i": 19, "j": 9, "phase": "文本指针始终向前, 最终模式串全部匹配"}),
            ("exit", "return i - m", "kmp_search", {"_return": 10, "phase": "匹配起点为 19-9=10"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "程序结束"}),
        ],
        "04_KMP_nextval优化": [
            ("enter", "int main(void)", "main", {"pattern": "ABABCABAB", "phase": "同时构建 next 与 nextval"}),
            ("enter", "void build_nextval", "build_nextval", {"i": 0, "j": -1, "nextval": [-1], "phase": "nextval[0] 同样使用 -1 哨兵"}),
            ("exec", "nextval[i] = j", "build_nextval", {"i": 1, "j": 0, "nextval": [-1, 0], "phase": "字符不同, 保留普通回退位置"}),
            ("exec", "nextval[i] = nextval[j]", "build_nextval", {"i": 2, "j": 0, "nextval": [-1, 0, -1], "phase": "字符相同, 直接跳过必然再次失败的位置"}),
            ("exec", "nextval[i] = nextval[j]", "build_nextval", {"i": 8, "j": 3, "phase": "重复结构继续沿优化后的回退链跳转"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "next": [-1, 0, 0, 1, 2, 0, 1, 2, 3], "nextval": [-1, 0, -1, 0, 2, -1, 0, -1, 0], "phase": "nextval 减少重复失配, 不改变 O(n+m)"}),
        ],
        "05_RabinKarp_哈希匹配": [
            ("enter", "int main(void)", "main", {"phase": "文本和模式串沿用同一匹配样例"}),
            ("enter", "void rabin_karp", "rabin_karp", {"phase": "先计算模式串和首个窗口的哈希"}),
            ("exec", "hash_p = (hash_p * BASE", "rabin_karp", {"window": 0, "phase": "把 9 个字符压缩成数字指纹"}),
            ("exec", "if (hash_p == hash_t)", "rabin_karp", {"window": 0, "phase": "哈希不同, 不必逐字符比较"}),
            ("exec", "hash_t = (hash_t -", "rabin_karp", {"window": 1, "phase": "删掉窗口最左字符, 加入右侧新字符"}),
            ("exec", "if (hash_p == hash_t)", "rabin_karp", {"window": 10, "phase": "位置 10 的窗口哈希与模式串相同"}),
            ("exec", "if (j == m)", "rabin_karp", {"window": 10, "j": 9, "phase": "再逐字符确认, 排除哈希冲突"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "position": 10, "phase": "匹配成功, 起始位置为 10"}),
        ],
        "06_Trie字典树": [
            ("enter", "int main(void)", "main", {"phase": "准备插入 apple、app、ape、bat"}),
            ("enter", "void trie_insert", "trie_insert", {"word": "apple", "phase": "从根节点逐字符建立分支"}),
            ("exec", "cur->children[idx] = create_node()", "trie_insert", {"prefix": "app", "phase": "公共前缀 app 只创建一次"}),
            ("exec", "cur->is_end = true", "trie_insert", {"word": "app", "phase": "app 本身也是完整单词, 标记结尾"}),
            ("enter", "bool trie_search", "trie_search", {"word": "apple", "phase": "沿字符路径查找 apple"}),
            ("exit", "return cur->is_end", "trie_search", {"_return": True, "word": "apple", "phase": "路径存在且是单词结尾"}),
            ("exit", "return false", "trie_search", {"_return": False, "word": "apex", "phase": "apex 的 x 分支不存在"}),
            ("enter", "bool trie_starts_with", "trie_starts_with", {"prefix": "ap", "phase": "前缀查询只要求路径存在"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "查找与前缀查询全部完成"}),
        ],
        "07_AC自动机": [
            ("enter", "int main(void)", "main", {"patterns": ["abc", "bcd", "cde"], "text": "xabcdex", "phase": "三个模式串共享一棵 Trie"}),
            ("enter", "void insert", "insert", {"word": "abc", "phase": "依次插入 abc、bcd、cde"}),
            ("enter", "void build_fail", "build_fail", {"phase": "用 BFS 从浅到深构建 fail 指针"}),
            ("exec", "root->children[i]->fail = root", "build_fail", {"phase": "第一层 a、b、c 失配后都回到 root"}),
            ("exec", "child->fail = p->children[i]", "build_fail", {"state": "abc", "fail": "bc", "phase": "abc 的最长有效后缀 bc 仍是 Trie 前缀"}),
            ("enter", "int ac_search", "ac_search", {"text": "xabcdex", "phase": "文本指针只向前扫描一次"}),
            ("exec", "total += cur->count", "ac_search", {"read": "xabc", "matches": ["abc"], "total": 1, "phase": "读到 c 时命中 abc"}),
            ("exec", "cur = cur->fail", "ac_search", {"read": "xabcd", "state": "bc", "phase": "没有 d 边, 沿 fail 保留后缀 bc"}),
            ("exec", "total += cur->count", "ac_search", {"read": "xabcd", "matches": ["bcd"], "total": 2, "phase": "沿 bc→d 命中 bcd"}),
            ("exec", "total += cur->count", "ac_search", {"read": "xabcde", "matches": ["cde"], "total": 3, "phase": "继续利用后缀 cd 命中 cde"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "total": 3, "phase": "一次扫描命中 3 个模式串"}),
        ],
    }

    if algo_id not in manual:
        return algo

    steps = []
    for step_number, (step_type, fragment, function_name, variables) in enumerate(manual[algo_id]):
        steps.append({
            "step": step_number,
            "line": line_of(fragment),
            "type": step_type,
            "func": function_name,
            "vars": variables,
        })

    outputs = {
        "01_暴力匹配_BF": "匹配成功！起始位置：10",
        "02_KMP_next数组": "模式串：ABABCABAB；next：-1 0 0 1 2 0 1 2 3",
        "03_KMP_匹配过程": "KMP 匹配成功！起始位置：10",
        "04_KMP_nextval优化": "next：-1 0 0 1 2 0 1 2 3；nextval：-1 0 -1 0 2 -1 0 -1 0",
        "05_RabinKarp_哈希匹配": "Rabin-Karp 匹配成功！起始位置：10",
        "06_Trie字典树": "apple：找到；app：找到；apex：未找到；前缀 ap：存在",
        "07_AC自动机": "match count = 3（abc、bcd、cde）",
    }

    curated = dict(algo)
    curated["steps"] = steps
    curated["program_output"] = [{"after_step": len(steps), "text": outputs[algo_id]}]
    curated["track_vars"] = {
        "primary": ["i", "j", "window", "pattern", "word", "prefix", "state", "fail", "total", "phase"],
        "secondary": ["next", "nextval", "matches", "text", "position", "_return"],
    }
    return curated


def curate_ch15_code_demo(algo_id, algo):
    """高级数据结构突出结构变化，隐藏重复递归和初始化。"""
    source = algo.get("source", [])

    def line_of(fragment, fallback=1):
        if fragment.startswith("LAST:"):
            target = fragment[5:].strip()
            for reverse_index, line in enumerate(reversed(source)):
                if line.strip() == target:
                    return len(source) - reverse_index
        target = fragment.strip()
        for index, line in enumerate(source, start=1):
            if line.strip() == target:
                return index
        for index, line in enumerate(source, start=1):
            if fragment in line:
                return index
        return fallback

    manual = {
        "01_并查集_朴素版": [
            ("enter", "int main(void)", "main", {"phase": "6 个元素开始时各自成组"}),
            ("enter", "void unite", "unite", {"x": 1, "y": 2, "phase": "先找两边的代表元"}),
            ("exec", "parent[rx] = ry", "unite", {"parent": "1→2", "phase": "把 1 所在集合挂到 2 的代表元下"}),
            ("exec", "parent[rx] = ry", "unite", {"parent": "1→2→3", "phase": "合并 2 和 3, 形成同一集合"}),
            ("enter", "int is_same", "is_same", {"x": 1, "y": 3, "phase": "代表元相同, 1 和 3 是一伙"}),
            ("enter", "int is_same", "is_same", {"x": 1, "y": 4, "phase": "代表元不同, 1 和 4 还未连通"}),
            ("exec", "parent[rx] = ry", "unite", {"x": 3, "y": 4, "phase": "合并两个集合后, 1 到 5 连通"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "三次查询结果输出完成"}),
        ],
        "02_并查集_路径压缩": [
            ("enter", "int main(void)", "main", {"phase": "故意构造长链 5→4→3→2→1"}),
            ("enter", "int find", "find", {"x": 5, "phase": "从 5 沿父指针寻找根 1"}),
            ("exec", "parent[x] = find(parent[x])", "find", {"x": 5, "path": [5, 4, 3, 2, 1], "phase": "递归返回时把沿途节点直接挂到根"}),
            ("exit", "return parent[x]", "find", {"_return": 1, "parent": "2,3,4,5→1", "phase": "一次查找把长链压成星形"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "后续查询接近常数时间"}),
        ],
        "03_并查集_按秩合并": [
            ("enter", "int main(void)", "main", {"phase": "先形成 {1,2}、{3,4}、{5,6} 三组"}),
            ("enter", "void unite", "unite", {"x": 1, "y": 3, "phase": "比较两棵树的秩"}),
            ("exec", "parent[ry] = rx", "unite", {"root": 1, "rank": 2, "phase": "等高时合并, 新根的秩加 1"}),
            ("enter", "int is_same", "is_same", {"x": 1, "y": 4, "phase": "1 和 4 的代表元都是 1"}),
            ("enter", "void unite", "unite", {"x": 1, "y": 5, "phase": "较矮的 {5,6} 挂到较高集合下"}),
            ("exec", "parent[ry] = rx", "unite", {"root": 1, "phase": "避免把大树挂到小树下面"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "2 和 6 也属于同一集合"}),
        ],
        "04_并查集_社交圈示例": [
            ("enter", "int main(void)", "main", {"phase": "4 个人最初互不相连"}),
            ("enter", "void unite", "unite", {"x": 1, "y": 2, "phase": "1 和 2 成为朋友"}),
            ("enter", "void unite", "unite", {"x": 2, "y": 3, "phase": "2 和 3 成为朋友, 三人连成一圈"}),
            ("enter", "int is_same", "is_same", {"x": 1, "y": 3, "answer": "Yes", "phase": "通过共同代表元判断 1 和 3 连通"}),
            ("enter", "int is_same", "is_same", {"x": 1, "y": 4, "answer": "No", "phase": "4 仍是独立集合"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "社交圈检测完成"}),
        ],
        "05_线段树_建树": [
            ("enter", "int main(void)", "main", {"array": [3, 1, 4, 1, 5, 9, 2, 6], "phase": "8 个数作为叶子节点"}),
            ("enter", "void build", "build", {"p": 1, "l": 1, "r": 8, "phase": "根节点负责整个区间 [1,8]"}),
            ("exec", "tree[p] = a[l]", "build", {"interval": "[1,1]", "sum": 3, "phase": "叶子节点直接保存原数组值"}),
            ("exec", "tree[p] = tree[2 * p] + tree[2 * p + 1]", "build", {"interval": "[1,4]", "sum": 9, "phase": "父节点等于左右子区间之和"}),
            ("exec", "tree[p] = tree[2 * p] + tree[2 * p + 1]", "build", {"interval": "[5,8]", "sum": 22, "phase": "右半区汇总为 22"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "sum": 31, "phase": "根节点 [1,8] 的区间和为 31"}),
        ],
        "06_线段树_单点修改": [
            ("enter", "int main(void)", "main", {"array": [3, 1, 4, 1, 5, 9, 2, 6], "phase": "先建好区间和线段树"}),
            ("enter", "long long query", "query", {"ql": 3, "qr": 7, "phase": "查询 [3,7]"}),
            ("exit", "return sum", "query", {"_return": 21, "parts": ["[3,4]=5", "[5,6]=14", "[7,7]=2"], "phase": "三块标准区间拼出答案 21"}),
            ("enter", "void update", "update", {"x": 6, "delta": 3, "phase": "位置 6 从 9 增加到 12"}),
            ("exec", "tree[p] += d", "update", {"interval": "[6,6]", "sum": 12, "phase": "先修改叶子节点"}),
            ("exec", "tree[p] = tree[2 * p] + tree[2 * p + 1]", "update", {"path": "[6,6]→[5,6]→[5,8]→[1,8]", "phase": "只沿一条祖先链向上重算"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "sum": 24, "phase": "再次查询 [3,7], 结果变为 24"}),
        ],
        "07_线段树_区间查询": [
            ("enter", "int main(void)", "main", {"array": [3, 1, 4, 1, 5, 9, 2, 6], "phase": "线段树已经保存各层区间和"}),
            ("enter", "long long query", "query", {"ql": 3, "qr": 7, "phase": "查询区间 [3,7]"}),
            ("exec", "return tree[p]", "query", {"interval": "[3,4]", "sum": 5, "phase": "完全包含的节点直接取值"}),
            ("exec", "return tree[p]", "query", {"interval": "[5,6]", "sum": 14, "phase": "另一块完整区间也直接取值"}),
            ("exec", "return tree[p]", "query", {"interval": "[7,7]", "sum": 2, "phase": "边界位置落到叶子"}),
            ("exit", "return sum", "query", {"_return": 21, "phase": "5+14+2=21, 无需逐项扫描"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "另外两次查询得到 9 和 17"}),
        ],
        "08_线段树_完整示例": [
            ("enter", "int main(void)", "main", {"array": [3, 1, 4, 1, 5, 9, 2, 6], "phase": "完整演示建树、查询和修改"}),
            ("enter", "void build", "build", {"interval": "[1,8]", "phase": "递归建立区间和"}),
            ("enter", "long long query", "query", {"ql": 3, "qr": 7, "phase": "第一次查询 [3,7]"}),
            ("exit", "return sum", "query", {"_return": 21, "phase": "区间和为 21"}),
            ("enter", "long long query", "query", {"ql": 1, "qr": 4, "phase": "[1,4] 正好对应一个节点"}),
            ("exit", "return tree[p]", "query", {"_return": 9, "phase": "完整覆盖时直接返回 9"}),
            ("enter", "void update", "update", {"x": 6, "delta": 3, "phase": "a[6] 加 3"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "sum": 24, "phase": "更新后 [3,7] 的和为 24"}),
        ],
        "09_树状数组_lowbit": [
            ("enter", "int main(void)", "main", {"phase": "lowbit 取二进制最低位的 1"}),
            ("enter", "int lowbit", "lowbit", {"x": 6, "binary": "110", "phase": "6 的最低位 1 代表 2"}),
            ("exit", "return x & (-x)", "lowbit", {"_return": 2, "phase": "lowbit(6)=2"}),
            ("enter", "int lowbit", "lowbit", {"x": 8, "binary": "1000", "phase": "8 本身就是 2 的幂"}),
            ("exit", "return x & (-x)", "lowbit", {"_return": 8, "phase": "lowbit(8)=8"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "phase": "c[x] 管理 [x-lowbit(x)+1, x]"}),
        ],
        "10_树状数组_实现": [
            ("enter", "int main(void)", "main", {"array": [1, 2, 3, 4, 5, 6, 7, 8], "phase": "用 update 逐项建立树状数组"}),
            ("enter", "long long query", "query", {"x": 7, "phase": "查询书中案例 sum(7)"}),
            ("exec", "sum += c[i]", "query", {"i": 7, "sum": 7, "phase": "先取 c[7], 它管理 [7,7]"}),
            ("exec", "sum += c[i]", "query", {"i": 6, "sum": 18, "phase": "再取 c[6], 它管理 [5,6]"}),
            ("exec", "sum += c[i]", "query", {"i": 4, "sum": 28, "phase": "最后取 c[4], 它管理 [1,4]"}),
            ("exit", "return sum", "query", {"_return": 28, "path": "7→6→4→0", "phase": "sum(7)=7+11+10=28"}),
            ("enter", "void update", "update", {"x": 5, "delta": 10, "phase": "a[5] 从 5 增加到 15"}),
            ("exec", "c[i] += v", "update", {"path": "5→6→8", "phase": "通知所有覆盖位置 5 的仓库"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "sum7": 38, "range37": 35, "phase": "更新后 sum(7)=38, [3,7]=35"}),
        ],
        "11_树状数组_完整示例": [
            ("enter", "int main(void)", "main", {"array": [1, 2, 3, 4, 5, 6, 7, 8], "phase": "完整演示单点修改与区间和"}),
            ("enter", "long long query", "query", {"x": 7, "phase": "沿 7→6→4 查询前缀和"}),
            ("exit", "return s", "query", {"_return": 28, "phase": "sum(7)=28"}),
            ("enter", "long long query", "query", {"x": 2, "phase": "区间 [3,7] = sum(7)-sum(2)"}),
            ("exit", "return s", "query", {"_return": 3, "range": 25, "phase": "28-3=25"}),
            ("enter", "void update", "update", {"x": 5, "delta": 10, "phase": "a[5] 加 10"}),
            ("exit", "LAST:return 0;", "main", {"_return": 0, "sum7": 38, "range37": 35, "phase": "更新后的两个查询分别为 38 和 35"}),
        ],
    }

    if algo_id not in manual:
        return algo

    steps = []
    for step_number, (step_type, fragment, function_name, variables) in enumerate(manual[algo_id]):
        steps.append({
            "step": step_number,
            "line": line_of(fragment),
            "type": step_type,
            "func": function_name,
            "vars": variables,
        })

    outputs = {
        "01_并查集_朴素版": "1和3：是；1和4：不是；合并3和4后，1和5：是",
        "02_并查集_路径压缩": "find(5) 后 parent[5]=1，长链被压成星形",
        "03_并查集_按秩合并": "合并后：1和4同组，2和6同组",
        "04_并查集_社交圈示例": "1和3：Yes；1和4：No",
        "05_线段树_建树": "根 [1,8]=31；左半区=9；右半区=22",
        "06_线段树_单点修改": "修改前 [3,7]=21；位置6加3后 [3,7]=24",
        "07_线段树_区间查询": "[3,7]=21；[1,4]=9；[6,8]=17",
        "08_线段树_完整示例": "[3,7]=21；[1,4]=9；a[6]+3 后 [3,7]=24",
        "09_树状数组_lowbit": "lowbit(6)=2，lowbit(8)=8，lowbit(12)=4，lowbit(7)=1",
        "10_树状数组_实现": "sum(7)=28；sum(8)=36；[3,7]=25；更新后 sum(7)=38，[3,7]=35",
        "11_树状数组_完整示例": "sum(7)=28；[3,7]=25；更新后 sum(7)=38，[3,7]=35",
    }

    curated = dict(algo)
    curated["steps"] = steps
    curated["program_output"] = [{"after_step": len(steps), "text": outputs[algo_id]}]
    curated["track_vars"] = {
        "primary": ["x", "y", "parent", "root", "rank", "interval", "sum", "ql", "qr", "i", "phase"],
        "secondary": ["array", "path", "parts", "delta", "range", "answer", "_return"],
    }
    return curated


def curate_late_chapter_code_demo(algo, max_steps=14):
    """后半册代码执行保留代表性事件，避免把循环逐次展开成上百步。"""
    steps = algo.get("steps", [])
    if len(steps) <= max_steps:
        curated = dict(algo)
        outputs = curated.get("program_output", [])
        if outputs and any(item.get("after_step", 0) > len(steps) for item in outputs):
            text = "；".join(item.get("text", "") for item in outputs if item.get("text"))
            curated["program_output"] = [{"after_step": len(steps), "text": text}]
        return curated

    required = {0, len(steps) - 1}
    for index, step in enumerate(steps):
        if step.get("type") in {"enter", "exit"}:
            required.add(index)

    # 进入/退出事件太多时也要抽样，否则递归程序仍会膨胀。
    required = sorted(required)
    if len(required) > max_steps:
        required = [
            required[round(i * (len(required) - 1) / (max_steps - 1))]
            for i in range(max_steps)
        ]

    chosen = set(required)
    remaining = max_steps - len(chosen)
    if remaining > 0:
        candidates = [i for i in range(len(steps)) if i not in chosen]
        if candidates:
            for slot in range(remaining):
                pos = round(slot * (len(candidates) - 1) / max(1, remaining - 1))
                chosen.add(candidates[pos])

    sampled = []
    for new_number, old_index in enumerate(sorted(chosen)):
        step = dict(steps[old_index])
        step["step"] = new_number
        sampled.append(step)

    # 最后一步只表示程序已完成；不要让某个中间循环快照与最终输出并排出现。
    if sampled:
        final_vars = sampled[-1].get("vars", {})
        seen_vars = {
            key
            for step in sampled
            for key in step.get("vars", {})
            if key not in {"phase", "concept", "_return"}
        }
        clean_vars = {key: "-" for key in seen_vars}
        clean_vars["phase"] = "程序执行完成，结果见下方输出"
        if "_return" in final_vars:
            clean_vars["_return"] = final_vars["_return"]
        sampled[-1]["vars"] = clean_vars

    outputs = algo.get("program_output", [])
    output_text = "；".join(item.get("text", "") for item in outputs if item.get("text"))

    curated = dict(algo)
    curated["steps"] = sampled
    curated["program_output"] = (
        [{"after_step": len(sampled), "text": output_text}] if output_text else []
    )
    return curated


def concept_demo_sum_formula():
    source = [
        "算法: 高斯公式求和",
        "输入: n",
        "输出: 1 + 2 + ... + n",
        "",
        "把数列首尾配对:",
        "(1+n), (2+n-1), ...",
        "每一对都是 n+1",
        "sum = n * (n + 1) / 2",
    ]
    return _build_sum_demo(
        "高斯公式求和",
        source,
        "formula",
        [
            (5, "观察 1 到 6 的数列", 0, 0),
            (5, "首尾配对: 1+6", 1, 7),
            (6, "继续配对: 2+5, 3+4", 3, 21),
            (7, "每一对都是 7", 3, 21),
            (8, "6 个数就是 3 对, 结果 6×7÷2=21", 3, 21),
        ],
        "概念动画：公式法不需要逐个累加，直接利用结构得到答案。",
    )


def _build_sum_demo(title, source, mode, states, output):
    steps = []
    for idx, (line, phase, progress, total) in enumerate(states):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "n": 6,
                "sum": total,
                "phase": phase,
                "concept": {
                    "kind": "sum_demo",
                    "mode": mode,
                    "n": 6,
                    "progress": progress,
                    "sum": total,
                },
            },
        })
    return {
        "title": title,
        "source": source,
        "important_vars": {"n": "规模", "sum": "累加和", "phase": "阶段"},
        "track_vars": {"primary": ["n", "sum", "phase"], "secondary": []},
        "var_classes": {
            "n": {"category": "primary", "type": "scalar"},
            "sum": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": output}],
        "steps": steps,
    }


def concept_demo_linear_search():
    source = [
        "算法: 顺序查找",
        "输入: 数组 arr, 目标 target",
        "输出: 目标下标, 找不到返回 -1",
        "",
        "从第一个元素开始",
        "逐个比较 arr[i] 和 target",
        "如果相等, 立即返回 i",
        "如果全部看完还没有, 返回 -1",
    ]
    values = [50, 10, 90, 30, 70, 40, 80, 60, 20]
    rows = [
        (5, 0, 70, "先从下标 0 开始找 70", [0], False),
        (6, 1, 70, "50 不是 70, 继续往右", [0, 1], False),
        (6, 2, 70, "10 也不是, 顺序查找不会跳跃", [0, 1, 2], False),
        (6, 3, 70, "90 不是, 继续一个个看", [0, 1, 2, 3], False),
        (7, 4, 70, "命中 70, 立即返回下标 4", [0, 1, 2, 3, 4], True),
        (6, 8, 99, "换一个目标 99: 必须看到最后", list(range(9)), False),
        (8, 9, 99, "全部检查完仍未命中, 返回 -1", list(range(9)), False),
    ]
    steps = []
    for idx, (line, i, target, phase, visited, found) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "i": i if i < len(values) else "-",
                "target": target,
                "result": i if found else -1,
                "phase": phase,
                "concept": {
                    "kind": "array_process",
                    "mode": "linear_search",
                    "title": "顺序查找",
                    "values": values,
                    "target": target,
                    "current": i if i < len(values) else None,
                    "visited": visited,
                    "found": found,
                    "phase": phase,
                },
            },
        })
    return _build_array_process_demo(
        "顺序查找",
        source,
        steps,
        {"i": "当前位置", "target": "目标值", "result": "结果", "phase": "阶段"},
        ["i", "target", "result", "phase"],
        "概念动画：顺序查找不要求数组有序, 代价是只能从左到右一个个看。",
    )


def concept_demo_bubble_sort():
    source = [
        "算法: 冒泡排序",
        "输入: 无序数组 arr",
        "输出: 升序数组",
        "",
        "重复 n-1 轮:",
        "    从左到右比较相邻元素",
        "    如果左边大于右边, 交换",
        "每一轮结束, 最大值沉到右侧已排序区",
    ]
    frames = [
        (5, [5, 3, 8, 4, 2], [0, 1], [], "比较 5 和 3: 左边更大, 交换"),
        (6, [3, 5, 8, 4, 2], [1, 2], [], "比较 5 和 8: 顺序对, 不动"),
        (6, [3, 5, 8, 4, 2], [2, 3], [], "比较 8 和 4: 交换"),
        (6, [3, 5, 4, 8, 2], [3, 4], [], "比较 8 和 2: 交换"),
        (8, [3, 5, 4, 2, 8], [], [4], "第一轮结束, 最大的 8 已就位"),
        (6, [3, 5, 4, 2, 8], [1, 2], [4], "第二轮继续, 5 和 4 交换"),
        (8, [3, 4, 2, 5, 8], [], [3, 4], "第二轮结束, 5 也就位"),
        (8, [2, 3, 4, 5, 8], [], [0, 1, 2, 3, 4], "最终有序: 大数一轮轮冒到右边"),
    ]
    return _sort_process_demo("冒泡排序", source, "bubble", frames, "概念动画：冒泡排序靠相邻比较和交换, 每轮确定一个最大值。")


def concept_demo_bubble_sort_optimized():
    source = [
        "算法: 冒泡排序优化版",
        "输入: 可能已经有序的数组 arr",
        "输出: 升序数组",
        "",
        "每轮开始 swapped = false",
        "如果发生交换, swapped = true",
        "一整轮没有交换:",
        "    说明数组已经有序, 提前结束",
    ]
    frames = [
        (5, [10, 20, 30, 40, 50, 60], [], [], "这组数据本来就是有序的"),
        (5, [10, 20, 30, 40, 50, 60], [0, 1], [], "比较 10 和 20: 不交换"),
        (5, [10, 20, 30, 40, 50, 60], [1, 2], [], "比较 20 和 30: 不交换"),
        (5, [10, 20, 30, 40, 50, 60], [2, 3], [], "继续比较, 仍然没有交换"),
        (5, [10, 20, 30, 40, 50, 60], [4, 5], [], "这一轮走完, swapped 仍然是 false"),
        (8, [10, 20, 30, 40, 50, 60], [], [0, 1, 2, 3, 4, 5], "提前结束: 最好情况从 O(n²) 变成 O(n)"),
    ]
    return _sort_process_demo("冒泡排序_优化版", source, "bubble_opt", frames, "概念动画：优化版的关键不是换得更快, 而是发现不用再换时立刻停。")


def concept_demo_selection_sort():
    source = [
        "算法: 选择排序",
        "输入: 无序数组 arr",
        "输出: 升序数组",
        "",
        "从左到右确定位置 i",
        "在未排序区寻找最小值 minIdx",
        "把 minIdx 和 i 交换",
        "左侧已排序区逐步扩大",
    ]
    frames = [
        (5, [5, 3, 8, 4, 2], [0], [], 0, "第 0 位还没确定, 先假设 5 最小"),
        (6, [5, 3, 8, 4, 2], [0, 1], [], 1, "看到 3, 更新最小值"),
        (6, [5, 3, 8, 4, 2], [0, 1, 2, 3, 4], [], 4, "扫描完整个未排序区, 最小值是 2"),
        (7, [2, 3, 8, 4, 5], [], [0], 0, "把 2 换到第 0 位"),
        (6, [2, 3, 8, 4, 5], [2, 3, 4], [0, 1], 3, "下一轮从未排序区找最小, 现在是 4"),
        (7, [2, 3, 4, 8, 5], [], [0, 1, 2], 2, "把 4 放到第 2 位"),
        (7, [2, 3, 4, 5, 8], [], [0, 1, 2, 3, 4], 3, "选择排序完成, 交换次数比冒泡少"),
    ]
    steps = []
    for idx, (line, values, compare, sorted_idx, min_idx, phase) in enumerate(frames):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "i": min(sorted_idx) if sorted_idx else 0,
                "minIdx": min_idx,
                "phase": phase,
                "concept": {
                    "kind": "array_process",
                    "mode": "selection",
                    "title": "选择排序",
                    "values": values,
                    "compare": compare,
                    "sorted": sorted_idx,
                    "minIdx": min_idx,
                    "phase": phase,
                },
            },
        })
    return _build_array_process_demo(
        "选择排序",
        source,
        steps,
        {"i": "本轮位置", "minIdx": "最小值下标", "phase": "阶段"},
        ["i", "minIdx", "phase"],
        "概念动画：选择排序每轮只做一次最终交换, 但仍要扫描完整个未排序区。",
    )


def concept_demo_sort_stability():
    source = [
        "算法: 稳定性对比",
        "输入: 按交卷顺序排列的学生",
        "只按 score 从小到大排序",
        "",
        "冒泡排序:",
        "    只在左边分数 > 右边分数时交换",
        "    同分不交换, 所以不插队",
        "",
        "选择排序:",
        "    找到最小值后直接换到前面",
        "    这一跳可能跨过同分元素",
    ]
    rows = [
        (5, "原始顺序", ["张三 658", "李四 658", "王五 600", "赵六 701"], ["张三 658", "李四 658", "王五 600", "赵六 701"], [], [], "先看原始队伍: 张三在李四前面"),
        (6, "冒泡比较", ["张三 658", "李四 658", "王五 600", "赵六 701"], ["张三 658", "李四 658", "王五 600", "赵六 701"], [0, 1], [], "658 和 658 相等, 冒泡不会交换"),
        (7, "稳定结果", ["王五 600", "张三 658", "李四 658", "赵六 701"], ["张三 658", "李四 658", "王五 600", "赵六 701"], [1, 2], [1, 2], "冒泡排完后, 张三仍在李四前面"),
        (9, "选择找到最小", ["张三 658", "李四 658", "王五 600", "赵六 701"], ["张三 658", "李四 658", "王五 600", "赵六 701"], [0, 2], [], "选择排序找到王五最小, 准备直接换到第 0 位"),
        (10, "不稳定结果", ["王五 600", "李四 658", "张三 658", "赵六 701"], ["王五 600", "李四 658", "张三 658", "赵六 701"], [1, 2], [1, 2], "王五这一跳跨过张三, 658 分里李四跑到了张三前面"),
    ]
    steps = []
    for idx, (line, stage, bubble, selection, active, unstable, phase) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "stage": stage,
                "bubble": " → ".join(bubble),
                "selection": " → ".join(selection),
                "concept": {
                    "kind": "stability_compare",
                    "title": "稳定性对比",
                    "bubble": bubble,
                    "selection": selection,
                    "active": active,
                    "unstable": unstable,
                    "phase": phase,
                },
            },
        })
    return _build_simple_concept_algo(
        "冒泡与选择_稳定性对比",
        source,
        steps,
        ["stage", "bubble", "selection"],
        "概念动画：稳定性不是排序对错, 而是同值元素是否保持原来的相对顺序。",
    )


def concept_demo_insertion_sort():
    source = [
        "算法: 插入排序",
        "输入: 数组 arr",
        "把左侧看成已经排好的手牌",
        "每次取一个新元素 key",
        "从右向左移动比 key 大的元素",
        "把 key 插入空出来的位置",
        "有序区逐步扩大",
    ]
    frames = [
        (3, [5, 2, 4, 6, 1, 3], [0], [0], 1, "左侧第一个元素天然有序"),
        (4, [5, 2, 4, 6, 1, 3], [1], [0], 1, "拿到 key=2, 准备插入左侧有序区"),
        (5, [5, 5, 4, 6, 1, 3], [0, 1], [], 1, "5 比 2 大, 先向右挪一格"),
        (6, [2, 5, 4, 6, 1, 3], [0, 1], [0, 1], 0, "空位放入 2, 左侧两个元素有序"),
        (4, [2, 5, 4, 6, 1, 3], [2], [0, 1], 2, "拿到 key=4, 插入 [2,5]"),
        (6, [2, 4, 5, 6, 1, 3], [1, 2], [0, 1, 2], 1, "5 后移, 4 插到 2 后面"),
        (6, [1, 2, 3, 4, 5, 6], [], list(range(6)), 0, "不断扩大有序区, 最终完成排序"),
    ]
    steps = []
    for idx, (line, values, compare, sorted_idx, insert_pos, phase) in enumerate(frames):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "insertPos": insert_pos,
                "sortedEnd": max(sorted_idx) if sorted_idx else "-",
                "phase": phase,
                "concept": {
                    "kind": "array_process",
                    "mode": "insertion",
                    "title": "插入排序",
                    "values": values,
                    "compare": compare,
                    "sorted": sorted_idx,
                    "current": insert_pos,
                    "phase": phase,
                },
            },
        })
    return _build_array_process_demo(
        "插入排序",
        source,
        steps,
        {"insertPos": "插入位置", "sortedEnd": "有序区末尾", "phase": "阶段"},
        ["insertPos", "sortedEnd", "phase"],
        "概念动画：插入排序像整理手牌, 每次把新牌插到左侧有序区的正确位置。",
    )


def concept_demo_shell_sort():
    source = [
        "算法: 希尔排序",
        "输入: 数组 arr",
        "gap = n / 2",
        "按 gap 分组做插入排序",
        "gap /= 2",
        "重复直到 gap == 1",
        "最后一轮普通插入排序, 但数组已大致有序",
    ]
    frames = [
        (3, [50, 10, 90, 30, 70, 40, 80, 60, 20], [0, 4, 8], [], 4, "gap=4, 先让远距离元素快速归位"),
        (4, [20, 10, 80, 30, 50, 40, 90, 60, 70], [0, 4, 8], [0, 4, 8], 4, "同一组隔着 4 个位置做插入排序"),
        (5, [20, 10, 80, 30, 50, 40, 90, 60, 70], [0, 2, 4, 6, 8], [], 2, "gap 缩小到 2, 数组继续接近有序"),
        (4, [20, 10, 50, 30, 70, 40, 80, 60, 90], [0, 2, 4, 6, 8], [0, 2, 4, 6, 8], 2, "大数和小数已经大致来到正确区域"),
        (6, [10, 20, 30, 40, 50, 60, 70, 80, 90], list(range(9)), list(range(9)), 1, "gap=1, 最后一轮普通插入排序很快完成"),
    ]
    steps = []
    for idx, (line, values, compare, sorted_idx, gap, phase) in enumerate(frames):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "gap": gap,
                "focus": "-".join(str(i) for i in compare),
                "phase": phase,
                "concept": {
                    "kind": "array_process",
                    "mode": "shell",
                    "title": "希尔排序",
                    "values": values,
                    "compare": compare,
                    "sorted": sorted_idx,
                    "phase": phase,
                },
            },
        })
    return _build_array_process_demo(
        "希尔排序",
        source,
        steps,
        {"gap": "间隔", "focus": "当前组", "phase": "阶段"},
        ["gap", "focus", "phase"],
        "概念动画：希尔排序先粗调, 再细调; gap 越小, 数组越接近完全有序。",
    )


def concept_demo_heap_sort():
    source = [
        "算法: 堆排序",
        "输入: 数组 arr",
        "先把数组调整成大根堆",
        "堆顶是当前最大值",
        "交换堆顶和末尾",
        "缩小堆范围, 重新 heapify",
        "重复直到全部有序",
    ]
    frames = [
        (3, [50, 10, 90, 30, 70, 40, 80, 60, 20], [0, 2], [], 0, "把数组看成一棵完全二叉树"),
        (3, [90, 70, 80, 60, 50, 40, 20, 10, 30], [0, 1, 2], [], 0, "建成大根堆: 最大值来到堆顶"),
        (5, [30, 70, 80, 60, 50, 40, 20, 10, 90], [0, 8], [8], 0, "把堆顶最大值换到末尾, 末尾确定"),
        (6, [80, 70, 40, 60, 50, 30, 20, 10, 90], [0, 2], [8], 0, "对剩余区间重新 heapify"),
        (7, [10, 20, 30, 40, 50, 60, 70, 80, 90], [], list(range(9)), 0, "最大值一个个沉到右侧, 排序完成"),
    ]
    steps = []
    for idx, (line, values, compare, sorted_idx, root, phase) in enumerate(frames):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "root": root,
                "heapSize": len(values) - len(sorted_idx),
                "phase": phase,
                "concept": {
                    "kind": "array_process",
                    "mode": "heap",
                    "title": "堆排序",
                    "values": values,
                    "compare": compare,
                    "sorted": sorted_idx,
                    "current": root if idx < 4 else None,
                    "phase": phase,
                },
            },
        })
    return _build_array_process_demo(
        "堆排序",
        source,
        steps,
        {"root": "堆顶", "heapSize": "堆大小", "phase": "阶段"},
        ["root", "heapSize", "phase"],
        "概念动画：堆排序先建堆, 再反复把最大值送到数组末尾。",
    )


def concept_demo_external_sort():
    source = [
        "算法: 外部排序",
        "输入: 磁盘上的大文件",
        "内存一次只能放一小段",
        "每次读一段进内存并排序",
        "写成多个有序归并段",
        "从每个归并段读当前最小值",
        "多路归并写入输出文件",
    ]
    rows = [
        (3, "分段读取", [[42, 15, 73, 28, 61], [9, 34, 88, 17, 55], [3, 67, 21, 49, 82]], [], [], "大文件装不进内存, 只能一段一段读"),
        (4, "内存排序", [[15, 28, 42, 61, 73], [9, 17, 34, 55, 88], [3, 21, 49, 67, 82]], [], [], "每段在内存里先排好, 写成有序小文件"),
        (5, "形成归并段", [[15, 28, 42, 61, 73], [9, 17, 34, 55, 88], [3, 21, 49, 67, 82]], [15, 9, 3], [], "每个归并段只露出当前最小候选"),
        (6, "多路归并", [[15, 28, 42, 61, 73], [9, 17, 34, 55, 88], [21, 49, 67, 82]], [15, 9, 21], [3], "选出最小的 3 写入输出, 该段指针后移"),
        (7, "输出完成", [[], [], []], [], [3, 9, 15, 17, 21, 28, 34, 42, 49, 55, 61, 67, 73, 82, 88], "所有归并段读完, 大文件整体有序"),
    ]
    steps = []
    for idx, (line, stage, runs, heads, output, phase) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "stage": stage,
                "runs": len([r for r in runs if r]),
                "output": ",".join(str(v) for v in output) if output else "-",
                "concept": {
                    "kind": "external_sort",
                    "title": "外部排序",
                    "runs": runs,
                    "heads": heads,
                    "output": output,
                    "phase": phase,
                },
            },
        })
    return _build_simple_concept_algo(
        "外部排序_多路归并",
        source,
        steps,
        ["stage", "runs", "output"],
        "概念动画：外部排序把大文件拆成有序小段, 再像拉拉链一样多路归并。",
    )


def concept_demo_activity_selection():
    source = [
        "算法: 活动选择",
        "输入: 若干活动 [start, end)",
        "按结束时间从早到晚排序",
        "先选择结束最早的活动",
        "继续扫描后续活动",
        "如果 start >= last_end, 就选择它",
        "否则跳过它",
    ]
    activities = [
        {"id": "A", "start": 1, "end": 4}, {"id": "B", "start": 3, "end": 5},
        {"id": "C", "start": 0, "end": 6}, {"id": "D", "start": 5, "end": 7},
        {"id": "E", "start": 3, "end": 9}, {"id": "F", "start": 5, "end": 9},
        {"id": "G", "start": 6, "end": 10}, {"id": "H", "start": 8, "end": 11},
        {"id": "I", "start": 8, "end": 12}, {"id": "J", "start": 2, "end": 14},
        {"id": "K", "start": 12, "end": 16},
    ]
    rows = [
        (3, "按结束时间排序", None, [], 0, "结束越早, 留给后面的时间越多"),
        (4, "选 A", "A", ["A"], 4, "A 结束最早, 先选它"),
        (7, "跳过 B/C", "C", ["A"], 4, "B、C 都在 A 结束前开始, 冲突"),
        (6, "选 D", "D", ["A", "D"], 7, "D 从 5 开始, 不和 A 冲突"),
        (7, "跳过 E/F/G", "G", ["A", "D"], 7, "它们都早于 7 开始, 会撞上 D"),
        (6, "选 H", "H", ["A", "D", "H"], 11, "H 从 8 开始, 可以接在 D 后面"),
        (6, "选 K", "K", ["A", "D", "H", "K"], 16, "K 从 12 开始, 最终安排 4 场"),
    ]
    steps = []
    for idx, (line, stage, current, selected, last_end, phase) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "stage": stage,
                "last_end": last_end,
                "selected": ",".join(selected) if selected else "-",
                "concept": {
                    "kind": "activity_selection",
                    "title": "活动选择",
                    "activities": activities,
                    "current": current,
                    "selected": selected,
                    "lastEnd": last_end,
                    "phase": phase,
                },
            },
        })
    return _build_simple_concept_algo(
        "活动选择",
        source,
        steps,
        ["stage", "last_end", "selected"],
        "概念动画：活动选择的贪心关键是“每次选结束最早的可兼容活动”。",
    )


def concept_demo_huffman_coding():
    source = [
        "算法: 哈夫曼编码",
        "输入: 字符及出现频率",
        "把所有字符放入最小堆",
        "重复:",
        "    取出频率最小的两个节点",
        "    合并成一个新节点",
        "    新节点放回最小堆",
        "只剩一个节点时, 哈夫曼树完成",
    ]
    rows = [
        (2, "初始频率", ["a45", "b13", "c12", "d16", "e9", "f5"], [], "高频字符应该靠近根, 低频字符可以走短编码"),
        (4, "合并 f5 和 e9", ["c12", "b13", "d16", "ef14", "a45"], ["f5", "e9"], "每次只拿最小的两个, 合成 14"),
        (4, "合并 c12 和 b13", ["ef14", "d16", "bc25", "a45"], ["c12", "b13"], "第二次仍然只看当前最小的两个"),
        (4, "合并 ef14 和 d16", ["bc25", "efd30", "a45"], ["ef14", "d16"], "低频组合逐渐被挂到更深的位置"),
        (4, "合并 bc25 和 efd30", ["a45", "bc-efd55"], ["bc25", "efd30"], "两棵小树继续合并"),
        (8, "最终根节点 100", ["root100"], ["a45", "bc-efd55"], "根节点代表所有频率之和, 编码树完成"),
    ]
    steps = []
    for idx, (line, stage, heap, picked, phase) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "stage": stage,
                "heap": " ".join(heap),
                "picked": " + ".join(picked) if picked else "-",
                "concept": {
                    "kind": "huffman",
                    "title": "哈夫曼编码",
                    "heap": heap,
                    "picked": picked,
                    "phase": phase,
                },
            },
        })
    return _build_simple_concept_algo(
        "哈夫曼编码",
        source,
        steps,
        ["stage", "heap", "picked"],
        "概念动画：哈夫曼编码的贪心策略是反复合并当前频率最小的两个节点。",
    )


def concept_demo_kruskal_mst():
    source = [
        "算法: Kruskal 最小生成树",
        "输入: 带权无向图",
        "把所有边按权重升序排序",
        "从最便宜的边开始扫描",
        "如果加入这条边不会成环, 就选择",
        "如果会成环, 就跳过",
        "选到 V-1 条边时结束",
    ]
    nodes = ["0", "1", "2", "3"]
    edges = [["0", "1", 1], ["2", "3", 2], ["1", "2", 3], ["0", "2", 4], ["1", "3", 5], ["0", "3", 6]]
    rows = [
        (3, "边按造价从小到大排序", None, [], [], 0, "先看最便宜的路"),
        (5, "选择 0-1", ["0", "1"], [["0", "1"]], [], 1, "0 和 1 尚未连通, 加入"),
        (5, "选择 2-3", ["2", "3"], [["0", "1"], ["2", "3"]], [], 3, "2 和 3 尚未连通, 加入"),
        (5, "选择 1-2", ["1", "2"], [["0", "1"], ["2", "3"], ["1", "2"]], [], 6, "1-2 把两个连通块接起来, MST 完成"),
        (6, "更贵的边都不需要", ["0", "2"], [["0", "1"], ["2", "3"], ["1", "2"]], [["0", "2"], ["1", "3"], ["0", "3"]], 6, "再加入会成环或更贵, 跳过"),
    ]
    steps = []
    for idx, (line, stage, current, chosen, rejected, total, phase) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "stage": stage,
                "total": total,
                "chosen": len(chosen),
                "concept": {
                    "kind": "kruskal",
                    "title": "Kruskal 最小生成树",
                    "nodes": nodes,
                    "edges": edges,
                    "current": current,
                    "chosen": chosen,
                    "rejected": rejected,
                    "total": total,
                    "phase": phase,
                },
            },
        })
    return _build_simple_concept_algo(
        "Kruskal最小生成树",
        source,
        steps,
        ["stage", "total", "chosen"],
        "概念动画：Kruskal 总是先看最便宜的边, 但用并查集防止成环。",
    )


def _sort_process_demo(title, source, mode, frames, output):
    steps = []
    for idx, (line, values, compare, sorted_idx, phase) in enumerate(frames):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "round": idx,
                "compare": "-".join(str(i) for i in compare) if compare else "-",
                "phase": phase,
                "concept": {
                    "kind": "array_process",
                    "mode": mode,
                    "title": title,
                    "values": values,
                    "compare": compare,
                    "sorted": sorted_idx,
                    "phase": phase,
                },
            },
        })
    return _build_array_process_demo(
        title,
        source,
        steps,
        {"round": "轮次", "compare": "比较下标", "phase": "阶段"},
        ["round", "compare", "phase"],
        output,
    )


def _build_array_process_demo(title, source, steps, important_vars, primary_vars, output):
    var_classes = {
        key: {"category": "primary", "type": "scalar"}
        for key in primary_vars
    }
    var_classes["concept"] = {"category": "secondary", "type": "concept"}
    return {
        "title": title,
        "source": source,
        "important_vars": important_vars,
        "track_vars": {"primary": primary_vars, "secondary": []},
        "var_classes": var_classes,
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": output}],
        "steps": steps,
    }


def concept_demo_search_complexity():
    source = [
        "算法: 顺序查找复杂度分析",
        "输入: 数组 arr 和目标 target",
        "从第 0 个元素开始逐个比较",
        "如果命中, 立即返回当前位置",
        "如果扫完整个数组还没命中, 返回 -1",
        "",
        "最好情况: 第 1 步命中 -> O(1)",
        "最坏情况: 最后一步命中或失败 -> O(n)",
        "平均情况: 大约检查 n/2 个元素 -> O(n)",
    ]
    rows = [
        (3, 3, 0, [0], [0], "最好情况: 第一个元素就是 3, 只走 1 步"),
        (3, 0, 0, [0], [0], "最坏情况开始: 要找 0, 前面都不是"),
        (3, 0, 4, [4], [0, 1, 2, 3, 4], "已经检查到中间, 步数随 n 线性增加"),
        (4, 0, 9, [9], list(range(10)), "最后一个才命中: 10 个数检查 10 次"),
        (8, "随机目标", 5, [5], list(range(6)), "平均大约检查一半, 但大 O 仍然是 O(n)"),
    ]
    steps = []
    values = [3, 7, 1, 9, 5, 2, 8, 4, 6, 0]
    for idx, (line, target, current, compare, visited, phase) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "target": target,
                "steps": len(visited),
                "case": phase.split(":")[0],
                "concept": {
                    "kind": "array_process",
                    "mode": "linear_search",
                    "title": "顺序查找复杂度",
                    "values": values,
                    "target": target,
                    "current": current,
                    "compare": compare,
                    "visited": visited,
                    "found": current == 0 or current == 9,
                    "phase": phase,
                },
            },
        })
    return _build_array_process_demo(
        "顺序查找_复杂度分析",
        source,
        steps,
        {"target": "目标", "steps": "步数", "case": "情况"},
        ["target", "steps", "case"],
        "概念动画：顺序查找的最好情况很幸运, 工程上更要关心最坏情况这条保底线。",
    )


def concept_demo_quick_complexity():
    source = [
        "算法: 快排最坏与平均情况",
        "输入: 一个数组 arr",
        "每次选择 pivot 做分区",
        "如果 pivot 比较居中, 递归树接近平衡",
        "如果 pivot 总是最大/最小, 递归树会退化成链",
        "平衡时约 O(n log n)",
        "退化时约 O(n^2)",
    ]
    rows = [
        (3, "选择 pivot", "平均情况", "pivot 把数组分得比较均匀", "balanced", 1),
        (4, "左右两边规模接近", "平均情况", "每层总工作量约 n, 层数约 log n", "balanced", 2),
        (6, "O(n log n)", "平均情况", "树不高, 所以快排通常很快", "balanced", 3),
        (3, "选择最后一个元素", "最坏情况", "有序数组里, 最后一个总是最大值", "skew", 1),
        (5, "一边空, 一边 n-1", "最坏情况", "递归树变成一条长链", "skew", 2),
        (7, "O(n^2)", "最坏情况", "每一层只少一个元素, 总工作量会爆炸", "skew", 3),
    ]
    steps = []
    for idx, (line, pivot, case, phase, shape, depth) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "pivot": pivot,
                "case": case,
                "phase": phase,
                "concept": {
                    "kind": "complexity_tree",
                    "title": "快排复杂度对比",
                    "shape": shape,
                    "depth": depth,
                    "phase": phase,
                },
            },
        })
    return _build_simple_concept_algo(
        "快排_最坏与平均",
        source,
        steps,
        ["pivot", "case", "phase"],
        "概念动画：快排不是永远 O(n log n), pivot 选得太偏会退化成 O(n^2)。",
    )


def concept_demo_in_place_reverse_space():
    source = [
        "算法: 原地反转数组",
        "输入: arr",
        "left 指向开头, right 指向末尾",
        "交换 arr[left] 和 arr[right]",
        "left++, right--",
        "直到两个指针相遇",
        "额外变量只有 left/right/temp -> O(1) 空间",
    ]
    values_list = [
        [50, 10, 90, 30, 70, 40, 80, 60, 20],
        [20, 10, 90, 30, 70, 40, 80, 60, 50],
        [20, 60, 90, 30, 70, 40, 80, 10, 50],
        [20, 60, 80, 30, 70, 40, 90, 10, 50],
        [20, 60, 80, 40, 70, 30, 90, 10, 50],
        [20, 60, 80, 40, 70, 30, 90, 10, 50],
    ]
    pairs = [(0, 8), (1, 7), (2, 6), (3, 5), (4, 4), (4, 4)]
    steps = []
    for idx, values in enumerate(values_list):
        left, right = pairs[idx]
        done = idx == len(values_list) - 1
        steps.append({
            "step": idx,
            "line": 6 if done else 4,
            "type": "exec",
            "vars": {
                "left": left,
                "right": right,
                "space": "O(1)",
                "concept": {
                    "kind": "array_process",
                    "mode": "reverse",
                    "title": "原地反转: O(1) 空间",
                    "values": values,
                    "compare": [left, right],
                    "sorted": list(range(idx)) + list(range(len(values) - idx, len(values))),
                    "phase": "指针相遇, 反转完成; 额外空间仍是常数级" if done else "只用 left/right/temp 三个变量, 不复制整份数组",
                },
            },
        })
    return _build_array_process_demo(
        "原地反转_空间O1",
        source,
        steps,
        {"left": "左指针", "right": "右指针", "space": "空间"},
        ["left", "right", "space"],
        "概念动画：数组再大, 原地反转额外需要的变量数量也不跟着变大。",
    )


def concept_demo_merge_space():
    source = [
        "算法: 归并排序空间分析",
        "输入: 两个有序子数组",
        "申请临时数组 L 和 R",
        "把左右两半复制进去",
        "比较 L[i] 和 R[j]",
        "把较小值写回原数组",
        "临时空间规模随 n 增长 -> O(n)",
    ]
    rows = [
        (2, [38, 27, 43, 3, 9, 82, 10], [], [], "原数组在这里, 但归并不能只靠几个指针完成"),
        (3, [38, 27, 43, 3, 9, 82, 10], [3, 27, 38, 43], [9, 10, 82], "申请 L/R 临时数组, 额外空间跟数据规模一起长"),
        (5, [38, 27, 43, 3, 9, 82, 10], [3, 27, 38, 43], [9, 10, 82], "比较两个临时数组的头部元素"),
        (6, [3, 9, 10, 27, 38, 43, 82], [3, 27, 38, 43], [9, 10, 82], "合并完成, 时间稳定, 代价是 O(n) 额外空间"),
    ]
    steps = []
    for idx, (line, arr, left, right, phase) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "extra": len(left) + len(right),
                "space": "O(n)" if left or right else "准备申请",
                "phase": phase,
                "concept": {
                    "kind": "space_compare",
                    "title": "归并排序: O(n) 空间",
                    "array": arr,
                    "left": left,
                    "right": right,
                    "phase": phase,
                },
            },
        })
    return _build_simple_concept_algo(
        "归并_空间On",
        source,
        steps,
        ["extra", "space", "phase"],
        "概念动画：归并排序的稳定速度来自额外临时数组, 空间复杂度是 O(n)。",
    )


def _dynamic_array_demo(title):
    source = [
        "算法: 动态数组摊还分析",
        "初始 capacity = 2",
        "每次 push_back 一个元素",
        "如果 size == capacity, 先翻倍扩容",
        "扩容会复制已有元素, 单次可能 O(n)",
        "但扩容不常发生, 总账摊下来仍是 O(1)",
    ]
    rows = [
        (2, 0, 2, [], 0, "一开始容量只有 2"),
        (3, 1, 2, [1], 1, "普通插入: 只写入一个格子"),
        (3, 2, 2, [1, 2], 1, "容量刚好填满, 下一次要扩容"),
        (4, 3, 4, [1, 2, 3], 3, "插入 3 前先扩容, 复制 2 个旧元素"),
        (3, 4, 4, [1, 2, 3, 4], 1, "扩容后又能连续便宜插入"),
        (4, 5, 8, [1, 2, 3, 4, 5], 5, "插入 5 前扩容到 8, 这次复制 4 个旧元素"),
        (3, 8, 8, [1, 2, 3, 4, 5, 6, 7, 8], 1, "后面几次又都是 O(1)"),
        (6, 10, 16, list(range(1, 11)), 10, "10 次插入只扩容 3 次, 摊还后每次仍接近常数"),
    ]
    steps = []
    for idx, (line, size, capacity, items, cost, phase) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "size": size,
                "capacity": capacity,
                "cost": cost,
                "concept": {
                    "kind": "dynamic_array",
                    "title": title,
                    "items": items,
                    "capacity": capacity,
                    "cost": cost,
                    "phase": phase,
                },
            },
        })
    return _build_simple_concept_algo(
        title,
        source,
        steps,
        ["size", "capacity", "cost"],
        "概念动画：扩容那一下很贵, 但把总成本摊到整串插入上, push_back 仍是摊还 O(1)。",
    )


def concept_demo_dynamic_array_amortized():
    return _dynamic_array_demo("动态数组_摊还分析")


def concept_demo_dynamic_array_full():
    return _dynamic_array_demo("动态数组_完整示例")


def concept_demo_halting_problem():
    source = [
        "算法: 停机问题反证法",
        "假设存在 halts(program, input)",
        "它能判断任意程序是否会停机",
        "构造 paradox(P):",
        "    如果 halts(P, P) 说会停",
        "        paradox 就故意死循环",
        "    如果 halts(P, P) 说不停",
        "        paradox 就立刻停机",
        "把 paradox 自己交给 paradox",
        "无论 halts 怎么回答, 都会矛盾",
    ]
    rows = [
        (2, "假设", "万能检测器 halts 存在"),
        (4, "构造", "写一个专门唱反调的 paradox"),
        (5, "回答: 会停", "如果 halts 说会停, paradox 就进入死循环"),
        (7, "回答: 不停", "如果 halts 说不停, paradox 就立刻返回"),
        (9, "自指", "现在运行 paradox(paradox)"),
        (10, "矛盾", "两种回答都会被 paradox 反着打脸"),
        (10, "结论", "万能停机检测器不可能存在"),
    ]
    steps = []
    for idx, (line, state, phase) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "state": state,
                "phase": phase,
                "concept": {
                    "kind": "halting",
                    "title": "停机问题反证法",
                    "state": state,
                    "phase": phase,
                    "index": idx,
                },
            },
        })
    return _build_simple_concept_algo(
        "停机问题_反证法",
        source,
        steps,
        ["state", "phase"],
        "概念动画：停机问题的关键是自指和反着做, 不是运行一段真的万能检测代码。",
    )


def concept_demo_complexity_ladder():
    source = [
        "算法: 复杂度阶层全景图",
        "把常见复杂度从快到慢排成一张地图",
        "观察 n 从 10 增长到 1000 时, 步数怎样拉开",
        "O(1), O(log n), O(n) 通常比较从容",
        "O(n log n) 是很多排序算法的理想区间",
        "O(n^2) 往后, 数据一大就会明显吃力",
        "O(2^n) 和 O(n!) 通常只适合很小的规模",
    ]
    levels = [
        {"order": "O(1)", "name": "常数时间", "example": "数组下标访问", "n10": "1步", "n100": "1步", "n1000": "1步", "weight": 0.18},
        {"order": "O(log n)", "name": "对数时间", "example": "二分查找", "n10": "~3步", "n100": "~7步", "n1000": "~10步", "weight": 0.28},
        {"order": "O(n)", "name": "线性时间", "example": "遍历数组", "n10": "10步", "n100": "100步", "n1000": "1000步", "weight": 0.42},
        {"order": "O(n log n)", "name": "线性对数", "example": "归并/堆排序", "n10": "~33步", "n100": "~664步", "n1000": "~9966步", "weight": 0.56},
        {"order": "O(n^2)", "name": "平方时间", "example": "两两比较", "n10": "100步", "n100": "1万步", "n1000": "100万步", "weight": 0.72},
        {"order": "O(2^n)", "name": "指数时间", "example": "穷举子集", "n10": "1024步", "n100": "天文数字", "n1000": "别想了", "weight": 0.88},
        {"order": "O(n!)", "name": "阶乘时间", "example": "穷举排列", "n10": "362万步", "n100": "宇宙级", "n1000": "不可想象", "weight": 1.0},
    ]
    rows = [
        (2, 0, "先看 O(1): 数据变大, 步数仍然不变"),
        (3, 1, "O(log n) 增长很慢, 每次把范围砍半"),
        (4, 2, "O(n) 随数据规模同步增长, 直观但可控"),
        (5, 3, "O(n log n) 是高效比较排序常见的天花板"),
        (6, 4, "O(n^2) 开始危险: n=1000 已经到百万级"),
        (7, 5, "O(2^n) 会爆炸, 通常要靠剪枝或动态规划改写"),
        (7, 6, "O(n!) 更夸张, 只能处理很小规模或换思路"),
    ]
    steps = []
    for idx, (line, active, phase) in enumerate(rows):
        level = levels[active]
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "complexity": level["order"],
                "example": level["example"],
                "scale": level["n1000"],
                "concept": {
                    "kind": "complexity_ladder",
                    "title": "复杂度阶层全景图",
                    "levels": levels,
                    "active": active,
                    "phase": phase,
                },
            },
        })
    return _build_simple_concept_algo(
        "复杂度阶层全景图",
        source,
        steps,
        ["complexity", "example", "scale"],
        "概念动画：复杂度不是背符号, 而是建立数据变大时的危险直觉。",
    )


def _search_array_steps(title, source, mode, values, target, rows, output):
    steps = []
    for idx, row in enumerate(rows):
        line, left, right, mid, result, phase = row[:6]
        extra = row[6] if len(row) > 6 else {}
        sorted_idx = extra.get("sorted", [])
        compare = [] if mid is None else [mid]
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "left": left,
                "right": right,
                "mid": "-" if mid is None else mid,
                "result": result,
                "concept": {
                    "kind": "array_process",
                    "mode": mode,
                    "title": title,
                    "values": values,
                    "target": target,
                    "current": mid,
                    "compare": compare,
                    "range": [] if left is None or right is None else [left, right],
                    "sorted": sorted_idx,
                    "phase": phase,
                    **extra,
                },
            },
        })
    return _build_array_process_demo(
        title,
        source,
        steps,
        {"left": "左边界", "right": "右边界", "mid": "中点", "result": "结果"},
        ["left", "right", "mid", "result"],
        output,
    )


def concept_demo_binary_search():
    source = [
        "算法: 经典二分查找",
        "输入: 有序数组 arr, 目标 target",
        "left = 0, right = n - 1",
        "当 left <= right:",
        "    mid = left + (right-left)/2",
        "    如果 arr[mid] == target: 返回 mid",
        "    如果 arr[mid] < target: left = mid + 1",
        "    否则 right = mid - 1",
    ]
    values = [2, 5, 8, 12, 16, 23, 38, 45, 56, 67, 78, 89]
    rows = [
        (5, 0, 11, 5, "-", "目标 45 比 23 大, 左边一半全部排除"),
        (5, 6, 11, 8, "-", "目标 45 比 56 小, 右边缩回来"),
        (5, 6, 7, 6, "-", "目标 45 比 38 大, 继续向右"),
        (6, 7, 7, 7, 7, "命中 45, 二分只用了 4 次比较", {"sorted": [7]}),
    ]
    return _search_array_steps("二分查找_经典版", source, "binary", values, 45, rows, "概念动画：二分查找每次排除一半候选。")


def concept_demo_binary_first():
    source = [
        "算法: 二分查找第一个目标",
        "如果 arr[mid] == target:",
        "    result = mid",
        "    right = mid - 1",
        "否则按普通二分缩小区间",
        "循环结束后返回 result",
    ]
    values = [1, 2, 2, 2, 3, 3, 4, 5, 5, 5, 5, 6]
    rows = [
        (2, 0, 11, 5, "-", "mid=5 是 3, 目标 2 在左边"),
        (2, 0, 4, 2, 2, "命中一个 2, 先记下 result=2, 继续往左找"),
        (2, 0, 1, 0, 2, "mid=0 是 1, 目标还在右边"),
        (2, 1, 1, 1, 1, "再次命中 2, 更新 result=1, 这就是第一个 2", {"sorted": [1]}),
    ]
    return _search_array_steps("二分查找_找第一个目标", source, "binary_first", values, 2, rows, "概念动画：命中后不停, 往左压缩才能找到第一个。")


def concept_demo_binary_last():
    source = [
        "算法: 二分查找最后一个目标",
        "如果 arr[mid] == target:",
        "    result = mid",
        "    left = mid + 1",
        "否则按普通二分缩小区间",
        "循环结束后返回 result",
    ]
    values = [1, 2, 2, 2, 3, 3, 4, 5, 5, 5, 5, 6]
    rows = [
        (2, 0, 11, 5, "-", "mid=5 是 3, 目标 5 在右边"),
        (2, 6, 11, 8, 8, "命中一个 5, 先记下 result=8, 继续往右找"),
        (2, 9, 11, 10, 10, "再次命中 5, 更新 result=10"),
        (4, 11, 11, 11, 10, "右侧没有更多 5, 最后一个位置是 10", {"sorted": [10]}),
    ]
    return _search_array_steps("二分查找_找最后目标", source, "binary_last", values, 5, rows, "概念动画：命中后不停, 往右压缩才能找到最后一个。")


def concept_demo_rotated_binary_search():
    source = [
        "算法: 旋转数组二分查找",
        "每次看 mid",
        "判断左半边还是右半边有序",
        "如果 target 落在有序半边, 保留它",
        "否则保留另一半",
    ]
    values = [4, 5, 6, 7, 0, 1, 2]
    rows = [
        (2, 0, 6, 3, "-", "mid=3 是 7, 左半边 [4,5,6,7] 有序"),
        (4, 4, 6, 5, "-", "目标 0 不在左半边, 去右半边; mid=5 是 1"),
        (4, 4, 4, 4, 4, "右侧继续缩小后命中 0", {"sorted": [4]}),
    ]
    return _search_array_steps("二分查找_旋转数组", source, "rotated", values, 0, rows, "概念动画：旋转数组二分的关键是先判断哪一半有序。")


def concept_demo_interpolation_search():
    source = [
        "算法: 插值查找",
        "输入: 均匀分布的有序数组",
        "mid = left + (target-arr[left])*(right-left)/(arr[right]-arr[left])",
        "根据 target 的大小估算更接近的位置",
        "适合均匀分布, 不适合奇怪分布",
    ]
    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    rows = [
        (3, 0, 9, 7, 7, "目标 80 在 10..100 的 7/9 位置附近, 直接估到下标 7", {"sorted": [7]}),
        (3, 0, 9, 2, 2, "目标 30 会估到更靠左的位置, 不必固定从中间开始", {"sorted": [2]}),
        (5, 0, 9, 4, -1, "如果分布不均匀, 这个估算就可能不稳定"),
    ]
    return _search_array_steps("插值查找", source, "interpolation", values, 80, rows, "概念动画：插值查找不是砍中间, 而是按数值比例猜位置。")


def concept_demo_fibonacci_search():
    source = [
        "算法: 斐波那契查找",
        "用斐波那契数确定切分点",
        "分割比例接近 61.8% : 38.2%",
        "比较后把 fibK/fib1/fib2 向下推进",
        "只用加减法调整边界",
    ]
    values = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    rows = [
        (2, 0, 9, 4, "-", "先用斐波那契数找到一个接近黄金比例的切点"),
        (3, 5, 9, 7, "-", "13 比 9 大, 去右侧较大的斐波那契区间"),
        (3, 5, 6, 6, 6, "命中 13, 位置是 6", {"sorted": [6]}),
    ]
    return _search_array_steps("斐波那契查找", source, "fibonacci", values, 13, rows, "概念动画：斐波那契查找用黄金比例切分区间。")


def concept_demo_binary_answer_shipping():
    source = [
        "算法: 二分答案 - 运送包裹",
        "答案空间: [max(weights), sum(weights)]",
        "check(mid): mid 能否在 D 天内运完",
        "可行: right = mid, 继续尝试更小值",
        "不可行: left = mid + 1, 排除更小值",
        "left == right 时, 就是最小可行载重量",
    ]
    rows = [
        (2, 10, 55, 32, 2, "答案范围是 [10,55], 先试 mid=32: 2 天可行"),
        (3, 10, 32, 20, 4, "mid=20 可行, 临界点还可能更小"),
        (4, 10, 20, 14, 6, "mid=14 不可行, 14 以及更小都排除"),
        (3, 15, 20, 17, 4, "mid=17 可行, 继续向左逼近临界点"),
        (3, 15, 17, 15, 5, "mid=15 刚好可行, 保留这个候选答案"),
        (5, 15, 15, 15, 5, "left == right == 15, 找到最小可行载重量"),
    ]
    steps = []
    weights = [1,2,3,4,5,6,7,8,9,10]
    for idx, (line, left, right, mid, days, phase) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "left": left,
                "right": right,
                "capacity": mid,
                "days": days,
                "concept": {
                    "kind": "answer_search",
                    "title": "二分答案: 运送包裹",
                    "weights": weights,
                    "left": left,
                    "right": right,
                    "capacity": mid,
                    "days": days,
                    "D": 5,
                    "critical": 15,
                    "phase": phase,
                },
            },
        })
    return _build_simple_concept_algo(
        "二分答案_运送包裹",
        source,
        steps,
        ["left", "right", "capacity", "days"],
        "概念动画：二分答案是在“可能答案的数轴”上搜索刚刚好的临界点。",
    )


def concept_demo_climb_recursive():
    source = [
        "算法: 爬楼梯暴力递归",
        "输入: 台阶数 n",
        "输出: 到达第 n 阶的方法数",
        "",
        "函数 climb(n):",
        "    如果 n <= 2: 返回 n",
        "    返回 climb(n-1) + climb(n-2)",
        "",
        "问题: 同一个子问题会被反复计算",
    ]
    steps = _recursion_tree_steps([
        (5, "从 climb(5) 开始, 拆成两个子问题", ["c5"], ["c5"], 0, "root"),
        (7, "climb(5) = climb(4) + climb(3)", ["c5", "c4", "c3a"], ["c4", "c3a"], 0, "expand"),
        (7, "climb(4) 又拆成 climb(3) + climb(2)", ["c5", "c4", "c3a", "c3b", "c2a"], ["c3b", "c2a"], 0, "expand"),
        (7, "同样的 climb(3) 出现了两次", ["c5", "c4", "c3a", "c3b", "c2a"], ["c3a", "c3b"], 0, "repeat"),
        (6, "边界问题直接返回, 叶子开始汇总", ["c5", "c4", "c3a", "c3b", "c2a", "c2b", "c1"], ["c2a", "c2b", "c1"], 2, "return"),
        (7, "最终得到 8 种走法, 但中间做了很多重复工作", ["c5", "c4", "c3a", "c3b", "c2a", "c2b", "c1"], ["c5"], 8, "done"),
    ], "爬楼梯暴力递归")
    return _build_recursion_demo("爬楼梯_暴力递归", source, steps, "概念动画：暴力递归的问题不是答案错，而是重复子问题太多。")


def concept_demo_merge_sort():
    source = [
        "算法: 归并排序",
        "输入: 一个无序数组 arr",
        "输出: 排好序的数组",
        "",
        "函数 merge_sort(arr):",
        "    如果数组长度 <= 1: 直接返回",
        "    把数组从中间分成左右两半",
        "    分别递归排序左半和右半",
        "    把两个有序数组合并成一个有序数组",
    ]
    nodes = [
        {"id": "root", "values": [10, 5, 13, 3, 8, 15, 6], "x": 0.50, "y": 0.05, "phase": "split"},
        {"id": "L", "values": [10, 5, 13, 3], "x": 0.30, "y": 0.22, "phase": "split"},
        {"id": "R", "values": [8, 15, 6], "x": 0.70, "y": 0.22, "phase": "split"},
        {"id": "LL", "values": [10, 5], "x": 0.20, "y": 0.39, "phase": "split"},
        {"id": "LR", "values": [13, 3], "x": 0.40, "y": 0.39, "phase": "split"},
        {"id": "RL", "values": [8, 15], "x": 0.62, "y": 0.39, "phase": "split"},
        {"id": "RR", "values": [6], "x": 0.82, "y": 0.39, "phase": "leaf"},
        {"id": "A10", "values": [10], "x": 0.15, "y": 0.56, "phase": "leaf"},
        {"id": "A5", "values": [5], "x": 0.25, "y": 0.56, "phase": "leaf"},
        {"id": "A13", "values": [13], "x": 0.35, "y": 0.56, "phase": "leaf"},
        {"id": "A3", "values": [3], "x": 0.45, "y": 0.56, "phase": "leaf"},
        {"id": "A8", "values": [8], "x": 0.57, "y": 0.56, "phase": "leaf"},
        {"id": "A15", "values": [15], "x": 0.67, "y": 0.56, "phase": "leaf"},
        {"id": "A6", "values": [6], "x": 0.82, "y": 0.56, "phase": "leaf"},
        {"id": "M1", "values": [5, 10], "x": 0.20, "y": 0.72, "phase": "merge"},
        {"id": "M2", "values": [3, 13], "x": 0.40, "y": 0.72, "phase": "merge"},
        {"id": "M3", "values": [8, 15], "x": 0.62, "y": 0.72, "phase": "merge"},
        {"id": "M4", "values": [6], "x": 0.82, "y": 0.72, "phase": "merge"},
        {"id": "M5", "values": [3, 5, 10, 13], "x": 0.30, "y": 0.87, "phase": "merge"},
        {"id": "M6", "values": [6, 8, 15], "x": 0.70, "y": 0.87, "phase": "merge"},
        {"id": "DONE", "values": [3, 5, 6, 8, 10, 13, 15], "x": 0.50, "y": 1.02, "phase": "done"},
    ]
    split_edges = [
        ["root", "L"], ["root", "R"], ["L", "LL"], ["L", "LR"], ["R", "RL"], ["R", "RR"],
        ["LL", "A10"], ["LL", "A5"], ["LR", "A13"], ["LR", "A3"], ["RL", "A8"], ["RL", "A15"], ["RR", "A6"],
    ]
    merge_edges = [
        ["A10", "M1"], ["A5", "M1"], ["A13", "M2"], ["A3", "M2"], ["A8", "M3"], ["A15", "M3"], ["A6", "M4"],
        ["M1", "M5"], ["M2", "M5"], ["M3", "M6"], ["M4", "M6"], ["M5", "DONE"], ["M6", "DONE"],
    ]
    states = [
        (6, "先从完整数组开始, 归并排序的第一步是分成两半", ["root"], [], ["root"], [], []),
        (6, "从中间切开: 左边 4 个数, 右边 3 个数", ["root", "L", "R"], [["root", "L"], ["root", "R"]], ["L", "R"], [], []),
        (7, "继续向下分, 直到每组只剩 1 个元素", ["root", "L", "R", "LL", "LR", "RL", "RR"], [["L", "LL"], ["L", "LR"], ["R", "RL"], ["R", "RR"]], ["LL", "LR", "RL", "RR"], [], []),
        (5, "单个元素天然有序, 分解阶段到达叶子", ["root", "L", "R", "LL", "LR", "RL", "RR", "A10", "A5", "A13", "A3", "A8", "A15", "A6"], [["LL", "A10"], ["LL", "A5"], ["LR", "A13"], ["LR", "A3"], ["RL", "A8"], ["RL", "A15"], ["RR", "A6"]], ["A10", "A5", "A13", "A3", "A8", "A15", "A6"], [], []),
        (8, "开始合并: 两个单元素比较后排成有序小数组", ["A10", "A5", "A13", "A3", "A8", "A15", "A6", "M1", "M2", "M3", "M4"], [], ["M1", "M2", "M3", "M4"], [["A10", "M1"], ["A5", "M1"], ["A13", "M2"], ["A3", "M2"], ["A8", "M3"], ["A15", "M3"], ["A6", "M4"]], []),
        (8, "继续把有序小数组合并成更大的有序数组", ["A10", "A5", "A13", "A3", "A8", "A15", "A6", "M1", "M2", "M3", "M4", "M5", "M6"], [], ["M5", "M6"], [["M1", "M5"], ["M2", "M5"], ["M3", "M6"], ["M4", "M6"]], [["M1", "M2"], ["M3", "M4"]]),
        (8, "最后合并左右两边, 得到完整有序数组", ["M1", "M2", "M3", "M4", "M5", "M6", "DONE"], [], ["DONE"], [["M5", "DONE"], ["M6", "DONE"]], [["M5", "M6"]]),
        (9, "归并排序完成: 先分到足够小, 再一路有序地合回来", ["root", "L", "R", "LL", "LR", "RL", "RR", "A10", "A5", "A13", "A3", "A8", "A15", "A6", "M1", "M2", "M3", "M4", "M5", "M6", "DONE"], [], ["DONE"], [], []),
    ]
    steps = []
    for idx, (line, phase, visible, active_split, active_nodes, active_merge, compare_groups) in enumerate(states):
        visible_set = set(visible)
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "phase": phase,
                "array": "10,5,13,3,8,15,6",
                "concept": {
                    "kind": "merge_sort",
                    "title": "归并排序",
                    "nodes": [node for node in nodes if node["id"] in visible_set],
                    "splitEdges": [edge for edge in split_edges if edge[0] in visible_set and edge[1] in visible_set],
                    "mergeEdges": [edge for edge in merge_edges if edge[0] in visible_set and edge[1] in visible_set],
                    "activeSplit": active_split,
                    "activeMerge": active_merge,
                    "activeNodes": active_nodes,
                    "compareGroups": compare_groups,
                },
            },
        })
    return _build_simple_concept_algo(
        "归并排序",
        source,
        steps,
        ["phase", "array"],
        "概念动画：归并排序先不断拆分, 再把有序小段一路合并成完整有序数组。",
    )


def concept_demo_quick_sort():
    source = [
        "算法: 快速排序",
        "输入: 一个无序数组 arr",
        "输出: 排好序的数组",
        "",
        "函数 quick_sort(arr):",
        "    选择一个 pivot",
        "    把小于 pivot 的元素放到左边",
        "    把大于 pivot 的元素放到右边",
        "    pivot 已经到达最终位置",
        "    分别递归排序左右两边",
    ]
    rows = [
        (5, [10, 5, 13, 3, 8, 15, 6], 6, [0, 6], [], [], [0, 6], "选择最后一个元素 6 做 pivot, 开始从左到右分区"),
        (7, [5, 10, 13, 3, 8, 15, 6], 6, [1, 6], [0], [], [0, 6], "5 小于 6, 被交换到左侧小区"),
        (7, [5, 3, 13, 10, 8, 15, 6], 6, [3, 6], [0, 1], [], [0, 6], "继续扫描, 3 也进入左侧小区"),
        (8, [5, 3, 6, 10, 8, 15, 13], 2, [], [0, 1], [2], [0, 6], "把 pivot 放到中间: 6 已经在最终位置"),
        (10, [3, 5, 6, 10, 8, 15, 13], 1, [0, 1], [0], [1, 2], [0, 1], "递归处理左边 [5, 3], 小数组很快排好"),
        (5, [3, 5, 6, 10, 8, 15, 13], 6, [3, 6], [3, 4], [0, 1, 2], [3, 6], "递归处理右边, 这次 pivot 是 13"),
        (8, [3, 5, 6, 10, 8, 13, 15], 5, [], [3, 4], [0, 1, 2, 5, 6], [3, 6], "13 归位后, 右侧只剩 15"),
        (9, [3, 5, 6, 8, 10, 13, 15], None, [], [], [0, 1, 2, 3, 4, 5, 6], [], "所有 pivot 陆续归位, 数组完成排序"),
    ]
    steps = []
    for idx, (line, values, pivot_idx, compare, left_zone, fixed, active_range, phase) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "pivot": "-" if pivot_idx is None else values[pivot_idx],
                "range": "-" if not active_range else f"{active_range[0]}..{active_range[1]}",
                "phase": phase,
                "concept": {
                    "kind": "array_process",
                    "mode": "quick",
                    "title": "快速排序",
                    "values": values,
                    "pivotIdx": pivot_idx,
                    "compare": compare,
                    "leftZone": left_zone,
                    "sorted": fixed,
                    "range": active_range,
                    "phase": phase,
                },
            },
        })
    return _build_array_process_demo(
        "快速排序",
        source,
        steps,
        {"pivot": "基准值", "range": "当前区间", "phase": "阶段"},
        ["pivot", "range", "phase"],
        "概念动画：快排的关键不是一次排完, 而是让 pivot 一次次站到最终位置。",
    )


def concept_demo_engineered_quick_sort():
    source = [
        "算法: 工程版快速排序",
        "输入: 真实世界里的数组 arr",
        "输出: 排好序的数组",
        "",
        "1. 三数取中选择 pivot, 避免太偏",
        "2. 只递归较小的一边, 较大的一边用循环处理",
        "3. 递归深度太深时切换堆排序兜底",
        "4. 小数组交给插入排序收尾",
    ]
    rows = [
        (5, [50, 10, 90, 30, 70, 40, 80, 60, 20], 4, [0, 4, 8], [], [], [0, 8], "三数取中: 左=50, 中=70, 右=20, 选更居中的 50/70/20 组合"),
        (5, [20, 10, 90, 30, 50, 40, 80, 60, 70], 4, [0, 4, 8], [], [], [0, 8], "把三数排一排, 让 pivot 不容易落到极端"),
        (6, [20, 10, 30, 40, 50, 90, 80, 60, 70], 4, [0, 8], [0, 1, 2, 3], [4], [0, 8], "partition 后, pivot 归位, 左右两边分开"),
        (6, [20, 10, 30, 40, 50, 90, 80, 60, 70], None, [0, 3], [0, 1, 2, 3], [4], [0, 3], "只递归较小的一边, 控制调用栈高度"),
        (6, [20, 10, 30, 40, 50, 90, 80, 60, 70], None, [5, 8], [], [4], [5, 8], "较大的一边不用再压栈, 交给 while 循环继续"),
        (7, [10, 20, 30, 40, 50, 60, 70, 80, 90], None, list(range(0, 4)), list(range(9)), [4], [0, 8], "小区间不再快排递归, 直接用插入排序收尾"),
        (8, [10, 20, 30, 40, 50, 60, 70, 80, 90], None, [], list(range(9)), list(range(9)), [], "工程快排不是换掉快排, 而是给它装上保险和加速器"),
    ]
    steps = []
    for idx, (line, values, pivot_idx, compare, left_zone, fixed, active_range, phase) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "pivot": "-" if pivot_idx is None else values[pivot_idx],
                "range": "-" if not active_range else f"{active_range[0]}..{active_range[1]}",
                "phase": phase,
                "concept": {
                    "kind": "array_process",
                    "mode": "quick_engineered",
                    "title": "工程版快速排序",
                    "values": values,
                    "pivotIdx": pivot_idx,
                    "compare": compare,
                    "leftZone": left_zone,
                    "sorted": fixed,
                    "range": active_range,
                    "phase": phase,
                },
            },
        })
    return _build_array_process_demo(
        "工程版快速排序",
        source,
        steps,
        {"pivot": "基准值", "range": "当前区间", "phase": "工程策略"},
        ["pivot", "range", "phase"],
        "概念动画：第6章不再重复基础快排, 而是展示工程里如何让快排更稳、更省栈。",
    )


def concept_demo_karatsuba():
    source = [
        "算法: Karatsuba 快速乘法",
        "输入: x = 1234, y = 5678",
        "把 x 拆成 a=12, b=34",
        "把 y 拆成 c=56, d=78",
        "只算三次乘法: ac、bd、(a+b)(c+d)",
        "ad+bc = (a+b)(c+d) - ac - bd",
        "按位权合并: ac×10000 + (ad+bc)×100 + bd",
        "得到最终乘积",
    ]
    states = [
        (2, "先把两个四位数摆出来", [], {}),
        (3, "把 1234 拆成高位 12 和低位 34", ["splitX"], {}),
        (4, "把 5678 拆成高位 56 和低位 78", ["splitX", "splitY"], {}),
        (5, "第一次乘法: ac = 12 × 56 = 672", ["ac"], {"ac": 672}),
        (5, "第二次乘法: bd = 34 × 78 = 2652", ["bd"], {"ac": 672, "bd": 2652}),
        (5, "第三次乘法: (a+b)(c+d) = 46 × 134 = 6164", ["sum"], {"ac": 672, "bd": 2652, "sum": 6164}),
        (6, "用减法补出中间项: ad+bc = 6164 - 672 - 2652 = 2840", ["middle"], {"ac": 672, "bd": 2652, "sum": 6164, "middle": 2840}),
        (7, "合并: 672×10000 + 2840×100 + 2652 = 7006652", ["result"], {"ac": 672, "bd": 2652, "sum": 6164, "middle": 2840, "result": 7006652}),
    ]
    steps = []
    for idx, (line, phase, active, values) in enumerate(states):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "phase": phase,
                "x": 1234,
                "y": 5678,
                "concept": {
                    "kind": "karatsuba",
                    "title": "Karatsuba 快速乘法",
                    "x": 1234,
                    "y": 5678,
                    "a": 12,
                    "b": 34,
                    "c": 56,
                    "d": 78,
                    "active": active,
                    "values": values,
                    "phase": phase,
                },
            },
        })
    return _build_simple_concept_algo(
        "Karatsuba快速乘法",
        source,
        steps,
        ["phase", "x", "y"],
        "概念动画：Karatsuba 用一次加法乘积替代两次交叉乘法, 把 4 次乘法降成 3 次。",
    )


def _build_distribution_sort_demo(title, source, rows, output):
    steps = []
    for idx, row in enumerate(rows):
        steps.append({
            "step": idx,
            "line": row.get("line", 1),
            "type": "exec",
            "vars": {
                "phase": row["phase"],
                "focus": row.get("focus", "-"),
                "result": row.get("result", "-"),
                "concept": {"kind": "distribution_sort", "title": title, **row},
            },
        })
    return {
        "title": title,
        "source": source,
        "important_vars": {"phase": "阶段", "focus": "关注点", "result": "当前结果"},
        "track_vars": {"primary": ["phase", "focus", "result"], "secondary": []},
        "var_classes": {
            "phase": {"category": "primary", "type": "scalar"},
            "focus": {"category": "primary", "type": "scalar"},
            "result": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": output}],
        "steps": steps,
    }


def concept_demo_counting_sort():
    source = [
        "算法: 计数排序",
        "输入: 小范围整数数组",
        "",
        "建立 count[0..max]",
        "扫描原数组, 对应数字的桶 +1",
        "从小到大读取 count",
        "每个数字出现几次, 就写回几次",
    ]
    rows = [
        {"line": 4, "phase": "原数组里只有 0..5 这些小整数", "mode": "count", "items": [4, 2, 2, 5, 3, 3, 1], "buckets": [["0", []], ["1", []], ["2", []], ["3", []], ["4", []], ["5", []]], "focus": "准备计数", "result": "-"},
        {"line": 5, "phase": "扫描数组, 每遇到一个数, 对应计数桶加 1", "mode": "count", "items": [4, 2, 2, 5, 3, 3, 1], "buckets": [["0", []], ["1", [1]], ["2", [2, 2]], ["3", [3, 3]], ["4", [4]], ["5", [5]]], "focus": "count[x]++", "result": "-"},
        {"line": 6, "phase": "计数桶天然按数字从小到大排好", "mode": "count", "items": [], "buckets": [["0", []], ["1", [1]], ["2", [2, 2]], ["3", [3, 3]], ["4", [4]], ["5", [5]]], "focus": "从小到大读桶", "result": "1,2,2,3,3,4,5"},
        {"line": 7, "phase": "把桶里的次数展开, 排序完成", "mode": "count", "items": [1, 2, 2, 3, 3, 4, 5], "buckets": [["0", []], ["1", []], ["2", []], ["3", []], ["4", []], ["5", []]], "focus": "写回数组", "result": "1,2,2,3,3,4,5"},
    ]
    return _build_distribution_sort_demo("计数排序", source, rows, "概念动画：计数排序不是比较大小, 而是统计每个数出现了几次。")


def concept_demo_counting_sort_stable():
    source = [
        "算法: 稳定版计数排序",
        "输入: 分数数组, 原下标代表交卷顺序",
        "",
        "统计每个分数出现次数",
        "把 count 改成前缀和",
        "从右往左扫描原数组",
        "放到 count[value]-1 的位置",
        "count[value]--",
    ]
    original = [
        {"value": 2, "id": "0"},
        {"value": 0, "id": "1"},
        {"value": 1, "id": "2"},
        {"value": 2, "id": "3"},
        {"value": 1, "id": "4"},
        {"value": 0, "id": "5"},
        {"value": 2, "id": "6"},
        {"value": 1, "id": "7"},
        {"value": 0, "id": "8"},
        {"value": 0, "id": "9"},
    ]
    rows = [
        {"line": 4, "phase": "先数每个分数出现几次: 0有4个, 1有3个, 2有3个", "scan": "-", "focus": "计数", "result": "-", "counts": [4, 3, 3], "prefix": [], "output": [None] * 10},
        {"line": 5, "phase": "前缀和给出每个分数的右边界: 0到下标3, 1到下标6, 2到下标9", "scan": "-", "focus": "前缀和", "result": "-", "counts": [4, 3, 3], "prefix": [4, 7, 10], "output": [None] * 10},
        {"line": 6, "phase": "从右往左看第9个元素: 0 放到 0 分区最右侧", "scan": 9, "focus": "0 -> 3", "result": "0(9)", "counts": [3, 7, 10], "prefix": [4, 7, 10], "output": [None, None, None, {"value": 0, "id": "9"}, None, None, None, None, None, None]},
        {"line": 7, "phase": "继续向左看第8个元素: 0 放到第2格, 原来的第9个同学还在它右边", "scan": 8, "focus": "0 -> 2", "result": "0(8),0(9)", "counts": [2, 7, 10], "prefix": [4, 7, 10], "output": [None, None, {"value": 0, "id": "8"}, {"value": 0, "id": "9"}, None, None, None, None, None, None]},
        {"line": 6, "phase": "第7个元素是1, 放进1分区的最右侧", "scan": 7, "focus": "1 -> 6", "result": "1(7)", "counts": [2, 6, 10], "prefix": [4, 7, 10], "output": [None, None, {"value": 0, "id": "8"}, {"value": 0, "id": "9"}, None, None, {"value": 1, "id": "7"}, None, None, None]},
        {"line": 6, "phase": "第6个元素是2, 放进2分区的最右侧", "scan": 6, "focus": "2 -> 9", "result": "2(6)", "counts": [2, 6, 9], "prefix": [4, 7, 10], "output": [None, None, {"value": 0, "id": "8"}, {"value": 0, "id": "9"}, None, None, {"value": 1, "id": "7"}, None, None, {"value": 2, "id": "6"}]},
        {"line": 8, "phase": "全部放完后, 同分学生仍按原下标从小到大排列", "scan": "-", "focus": "稳定完成", "result": "0(1),0(5),0(8),0(9),1(2),1(4),1(7),2(0),2(3),2(6)", "counts": [0, 4, 7], "prefix": [4, 7, 10], "output": [
            {"value": 0, "id": "1"}, {"value": 0, "id": "5"}, {"value": 0, "id": "8"}, {"value": 0, "id": "9"},
            {"value": 1, "id": "2"}, {"value": 1, "id": "4"}, {"value": 1, "id": "7"},
            {"value": 2, "id": "0"}, {"value": 2, "id": "3"}, {"value": 2, "id": "6"},
        ]},
    ]
    steps = []
    for idx, row in enumerate(rows):
        steps.append({
            "step": idx,
            "line": row["line"],
            "type": "exec",
            "vars": {
                "phase": row["phase"],
                "scan": row["scan"],
                "focus": row["focus"],
                "result": row["result"],
                "concept": {
                    "kind": "stable_counting",
                    "title": "稳定版计数排序",
                    "original": original,
                    **row,
                },
            },
        })
    return {
        "title": "稳定版计数排序",
        "source": source,
        "important_vars": {"phase": "阶段", "scan": "扫描下标", "focus": "放置位置", "result": "当前结果"},
        "track_vars": {"primary": ["phase", "scan", "focus", "result"], "secondary": []},
        "var_classes": {
            "phase": {"category": "primary", "type": "scalar"},
            "scan": {"category": "primary", "type": "scalar"},
            "focus": {"category": "primary", "type": "scalar"},
            "result": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": "概念动画：稳定版计数排序靠“从右往左放置”保住同分元素的原顺序。"}],
        "steps": steps,
    }


def concept_demo_radix_sort():
    source = [
        "算法: 基数排序",
        "输入: 多位整数数组",
        "",
        "从个位开始:",
        "    按当前位数字放入 0..9 号桶",
        "    按桶顺序收集回数组",
        "再处理十位、百位...",
        "所有位处理完, 数组有序",
    ]
    rows = [
        {"line": 4, "phase": "先看个位: 170 的个位是 0, 802 的个位是 2", "mode": "radix", "digit": "个位", "items": [170, 45, 75, 90, 802, 24, 2, 66], "buckets": [["0", [170, 90]], ["2", [802, 2]], ["4", [24]], ["5", [45, 75]], ["6", [66]]], "focus": "个位", "result": "170,90,802,2,24,45,75,66"},
        {"line": 6, "phase": "按桶收集后, 个位已经有序, 但整体还没排完", "mode": "radix", "digit": "个位收集", "items": [170, 90, 802, 2, 24, 45, 75, 66], "buckets": [], "focus": "收集", "result": "170,90,802,2,24,45,75,66"},
        {"line": 5, "phase": "再看十位: 802 和 2 的十位都是 0", "mode": "radix", "digit": "十位", "items": [170, 90, 802, 2, 24, 45, 75, 66], "buckets": [["0", [802, 2]], ["2", [24]], ["4", [45]], ["6", [66]], ["7", [170, 75]], ["9", [90]]], "focus": "十位", "result": "802,2,24,45,66,170,75,90"},
        {"line": 5, "phase": "最后看百位, 大数字自然落到后面", "mode": "radix", "digit": "百位", "items": [802, 2, 24, 45, 66, 170, 75, 90], "buckets": [["0", [2, 24, 45, 66, 75, 90]], ["1", [170]], ["8", [802]]], "focus": "百位", "result": "2,24,45,66,75,90,170,802"},
        {"line": 8, "phase": "所有位都处理完, 排序完成", "mode": "radix", "digit": "完成", "items": [2, 24, 45, 66, 75, 90, 170, 802], "buckets": [], "focus": "完成", "result": "2,24,45,66,75,90,170,802"},
    ]
    return _build_distribution_sort_demo("基数排序", source, rows, "概念动画：基数排序一位一位分桶, 稳定收集后高位会接管最终顺序。")


def concept_demo_bucket_sort():
    source = [
        "算法: 桶排序",
        "输入: 分布比较均匀的数",
        "",
        "按数值范围准备多个桶",
        "把每个元素放入对应范围的桶",
        "每个桶内部排序",
        "从左到右拼接所有桶",
    ]
    rows = [
        {"line": 4, "phase": "先按范围切出几个桶", "mode": "bucket", "items": [29, 25, 3, 49, 9, 37, 21, 43], "buckets": [["0-9", []], ["10-19", []], ["20-29", []], ["30-39", []], ["40-49", []]], "focus": "分范围", "result": "-"},
        {"line": 5, "phase": "每个数进入自己所属的范围桶", "mode": "bucket", "items": [], "buckets": [["0-9", [3, 9]], ["10-19", []], ["20-29", [29, 25, 21]], ["30-39", [37]], ["40-49", [49, 43]]], "focus": "分发", "result": "-"},
        {"line": 6, "phase": "桶内部各自排序, 小问题更容易处理", "mode": "bucket", "items": [], "buckets": [["0-9", [3, 9]], ["10-19", []], ["20-29", [21, 25, 29]], ["30-39", [37]], ["40-49", [43, 49]]], "focus": "桶内排序", "result": "-"},
        {"line": 7, "phase": "按桶的范围顺序拼接, 整体就有序了", "mode": "bucket", "items": [3, 9, 21, 25, 29, 37, 43, 49], "buckets": [], "focus": "拼接", "result": "3,9,21,25,29,37,43,49"},
    ]
    return _build_distribution_sort_demo("桶排序", source, rows, "概念动画：桶排序先按范围分组, 再把每个小组排好后拼起来。")


def _skip_list_base_nodes(include_new=False):
    positions = {
        1: 0.17, 2: 0.25, 3: 0.33, 4: 0.41, 5: 0.49,
        6: 0.57, 7: 0.65, 8: 0.73, 9: 0.81, 10: 0.89,
    }
    nodes = [
        {"id": "H0", "value": "HEAD", "level": 0, "x": 0.07},
        {"id": "H1", "value": "HEAD", "level": 1, "x": 0.07},
        {"id": "H2", "value": "HEAD", "level": 2, "x": 0.07},
    ]
    for value in range(1, 10):
        nodes.append({"id": f"{value}_0", "value": value, "level": 0, "x": positions[value]})
    for value in [1, 4, 7, 9]:
        nodes.append({"id": f"{value}_1", "value": value, "level": 1, "x": positions[value]})
    for value in [1, 9]:
        nodes.append({"id": f"{value}_2", "value": value, "level": 2, "x": positions[value]})
    if include_new:
        nodes.extend([
            {"id": "10_0", "value": 10, "level": 0, "x": positions[10], "new": True},
        ])
    return nodes


def _skip_list_edges(include_new=False):
    edges = [
        ["H0", "1_0"], ["1_0", "2_0"], ["2_0", "3_0"], ["3_0", "4_0"], ["4_0", "5_0"],
        ["5_0", "6_0"], ["6_0", "7_0"], ["7_0", "8_0"], ["8_0", "9_0"],
        ["H1", "1_1"], ["1_1", "4_1"], ["4_1", "7_1"], ["7_1", "9_1"],
        ["H2", "1_2"], ["1_2", "9_2"],
        ["1_0", "1_1"], ["1_1", "1_2"],
        ["4_0", "4_1"], ["7_0", "7_1"],
        ["9_0", "9_1"], ["9_1", "9_2"],
    ]
    if include_new:
        edges = [edge for edge in edges if edge != ["8_0", "9_0"]]
        edges.extend([["8_0", "9_0"], ["9_0", "10_0"]])
    return edges


def _skip_list_algo(title, source, states, output):
    steps = []
    for idx, (line, phase, include_new, active_path, active_nodes, update_nodes, level_note, target) in enumerate(states):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "target": target,
                "level": level_note,
                "phase": phase,
                "concept": {
                    "kind": "skip_list",
                    "title": title,
                    "nodes": _skip_list_base_nodes(include_new),
                    "edges": _skip_list_edges(include_new),
                    "activePath": active_path,
                    "activeNodes": active_nodes,
                    "updateNodes": update_nodes,
                    "target": target,
                    "levelNote": level_note,
                },
            },
        })
    return _build_simple_concept_algo(title, source, steps, ["target", "level", "phase"], output)


def concept_demo_skip_list_structure():
    source = [
        "算法: 跳表结构",
        "输入: 书稿 4.4.3 中的有序数据 1~9",
        "输出: 多层索引结构",
        "",
        "L1 保存全部节点: 1 到 9",
        "L2 抽取 1、4、7、9 做索引",
        "L3 只保留 1、9 两个远距离索引",
        "查找 8 时, 先在 L3 判断 9 已经过大",
        "下降到 L2, 走到 7 后发现 9 仍然过大",
        "下降到 L1, 从 7 走到 8 并命中",
    ]
    states = [
        (4, "L1 是完整有序链表, 所有数据都能在这里找到", False, [["H0", "1_0"], ["1_0", "2_0"], ["2_0", "3_0"], ["3_0", "4_0"], ["4_0", "5_0"], ["5_0", "6_0"], ["6_0", "7_0"], ["7_0", "8_0"], ["8_0", "9_0"]], ["H0", "1_0", "2_0", "3_0", "4_0", "5_0", "6_0", "7_0", "8_0", "9_0"], [], "L1: 全量链表", 8),
        (5, "L2 只保留 1、4、7、9, 先用少量节点快速定位区域", False, [["H1", "1_1"], ["1_1", "4_1"], ["4_1", "7_1"], ["7_1", "9_1"]], ["H1", "1_1", "4_1", "7_1", "9_1"], [], "L2: 稀疏索引", 8),
        (6, "L3 更稀疏, 只留下 1 和 9 作为最高层索引", False, [["H2", "1_2"], ["1_2", "9_2"]], ["H2", "1_2", "9_2"], [], "L3: 最高索引", 8),
        (7, "查找 8: 在 L3 从 HEAD 到 1, 看到下一个 9 已经大于 8", False, [["H2", "1_2"], ["1_2", "1_1"]], ["H2", "1_2", "1_1"], ["9_2"], "L3: 9 > 8, 向下", 8),
        (8, "下降到 L2 后, 从 1 走到 4, 再走到 7, 下一个 9 仍然过大", False, [["1_1", "4_1"], ["4_1", "7_1"], ["7_1", "7_0"]], ["1_1", "4_1", "7_1", "7_0"], ["9_1"], "L2: 停在 7", 8),
        (9, "最后降到 L1, 从 7 向右一步到 8, 命中目标", False, [["7_0", "8_0"]], ["7_0", "8_0"], [], "L1: 找到 8", 8),
    ]
    return _skip_list_algo(
        "跳表_定义与节点",
        source,
        states,
        "概念动画：跳表用多层稀疏索引, 把普通链表的线性查找变成向右、向下的快速搜索。",
    )


def concept_demo_skip_list_insert():
    source = [
        "算法: 跳表插入",
        "输入: 要插入的值 value",
        "输出: 插入后的跳表",
        "",
        "从最高层开始搜索插入位置",
        "记录每一层最后一个小于 value 的节点 update[i]",
        "随机决定新节点高度",
        "从底层到新高度逐层改指针",
        "新节点出现在若干层中",
    ]
    states = [
        (4, "准备插入 15, 仍然从最高层 HEAD 开始", False, [], ["H2"], [], "value=15", 15),
        (5, "最高层下一个是 19, 已经超过 15, 这一层停在 HEAD", False, [], ["H2"], ["H2"], "update[2]=HEAD", 15),
        (5, "下降到第 1 层, 先向右走到 7, 再发现 19 超过 15", False, [["H1", "7_1"]], ["H1", "7_1"], ["H1", "7_1"], "update[1]=7", 15),
        (5, "下降到底层, 走到 12 后停住, 插入位置在 12 和 19 之间", False, [["H1", "7_1"], ["7_0", "12_0"]], ["12_0", "19_0"], ["H1", "7_1", "12_0"], "update[0]=12", 15),
        (6, "随机层高决定 15 出现在第 0 层和第 1 层", False, [], ["12_0", "7_1"], ["7_1", "12_0"], "new level=1", 15),
        (7, "先改底层指针: 12 → 15 → 19", True, [["12_0", "15_0"], ["15_0", "19_0"]], ["15_0"], ["12_0"], "插入 level 0", 15),
        (7, "再改第 1 层指针: 7 → 15 → 19", True, [["7_1", "15_1"], ["15_1", "19_1"]], ["15_0", "15_1"], ["7_1"], "插入 level 1", 15),
        (8, "插入完成: 新节点既在底层保存数据, 也在上层成为索引", True, [["12_0", "15_0"], ["7_1", "15_1"], ["15_0", "15_1"]], ["15_0", "15_1"], [], "完成", 15),
    ]
    return _skip_list_algo(
        "跳表_插入逻辑",
        source,
        states,
        "概念动画：跳表插入先找每层前驱 update, 再按随机高度逐层接入新节点。",
    )


def concept_demo_coin_recursive():
    source = [
        "算法: 硬币找零暴力递归",
        "输入: 金额 amount, 硬币 coins",
        "输出: 最少硬币数",
        "",
        "函数 dfs(amount):",
        "    如果 amount == 0: 返回 0",
        "    枚举每个硬币 coin:",
        "        尝试 dfs(amount - coin) + 1",
        "    返回最小值",
    ]
    steps = _recursion_tree_steps([
        (5, "从金额 6 开始", ["a6"], ["a6"], 6, "root"),
        (7, "尝试硬币 1, 3, 4, 分成三个剩余金额", ["a6", "a5", "a3", "a2"], ["a5", "a3", "a2"], 6, "expand"),
        (7, "剩余金额 5 又继续分叉", ["a6", "a5", "a3", "a2", "a4", "a2b", "a1"], ["a4", "a2b", "a1"], 6, "expand"),
        (7, "金额 2 反复出现, 暴力递归会重复算", ["a6", "a5", "a3", "a2", "a4", "a2b", "a1"], ["a2", "a2b"], 6, "repeat"),
        (6, "遇到 amount == 0 的分支, 开始回传答案", ["a6", "a5", "a3", "a2", "a4", "a2b", "a1", "a0"], ["a0"], 0, "return"),
        (8, "最少 2 枚: 3 + 3 或 4 + 1 + 1 中取更小", ["a6", "a5", "a3", "a2", "a4", "a2b", "a1", "a0"], ["a6"], 2, "done"),
    ], "硬币找零暴力递归")
    return _build_recursion_demo("硬币找零_暴力递归", source, steps, "概念动画：暴力递归会展开很多重复金额，读懂分叉比看上千步更重要。")


def concept_demo_coin_memo():
    source = [
        "算法: 硬币找零记忆化搜索",
        "输入: 金额 amount, 硬币 coins",
        "输出: 最少硬币数",
        "",
        "函数 dfs(amount):",
        "    如果 memo[amount] 已有答案: 直接返回",
        "    否则递归计算各个 amount - coin",
        "    把最优答案存入 memo[amount]",
        "    返回 memo[amount]",
    ]
    steps = _recursion_tree_steps([
        (5, "仍然从金额 6 开始搜索", ["a6"], ["a6"], 6, "root", []),
        (7, "第一次算出金额 2", ["a6", "a5", "a3", "a2"], ["a2"], 6, "expand", []),
        (8, "把 dfs(2) 的答案存入 memo[2]", ["a6", "a5", "a3", "a2"], ["a2"], 6, "memo", ["2"]),
        (5, "另一个分支再次遇到金额 2, 直接查表", ["a6", "a5", "a3", "a2", "a2b"], ["a2b"], 6, "hit", ["2"]),
        (8, "继续缓存金额 3、5、6 的答案", ["a6", "a5", "a3", "a2", "a2b"], ["a6", "a5", "a3"], 2, "memo", ["2", "3", "5", "6"]),
        (8, "最终答案仍是 2, 但搜索树被明显压扁", ["a6", "a5", "a3", "a2", "a2b"], ["a6"], 2, "done", ["2", "3", "5", "6"]),
    ], "硬币找零记忆化搜索")
    return _build_recursion_demo("硬币找零_记忆化搜索", source, steps, "概念动画：记忆化搜索把重复子问题变成一次计算、多次复用。")


def _recursion_tree_steps(states, title):
    layout = {
        "c5": ("climb(5)", 0.50, 0.12), "c4": ("climb(4)", 0.34, 0.30), "c3a": ("climb(3)", 0.66, 0.30),
        "c3b": ("climb(3)", 0.24, 0.50), "c2a": ("climb(2)", 0.44, 0.50), "c2b": ("climb(2)", 0.58, 0.50), "c1": ("climb(1)", 0.76, 0.50),
        "a6": ("6", 0.50, 0.12), "a5": ("5", 0.25, 0.31), "a3": ("3", 0.50, 0.31), "a2": ("2", 0.75, 0.31),
        "a4": ("4", 0.16, 0.51), "a2b": ("2", 0.29, 0.51), "a1": ("1", 0.42, 0.51), "a0": ("0", 0.55, 0.70),
    }
    edges = [
        ("c5", "c4"), ("c5", "c3a"), ("c4", "c3b"), ("c4", "c2a"), ("c3a", "c2b"), ("c3a", "c1"),
        ("a6", "a5"), ("a6", "a3"), ("a6", "a2"), ("a5", "a4"), ("a5", "a2b"), ("a5", "a1"), ("a1", "a0"),
    ]
    steps = []
    for idx, state in enumerate(states):
        line, phase, visible, active, result, marker = state[:6]
        memo = state[6] if len(state) > 6 else []
        visible_set = set(visible)
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "result": result,
                "phase": phase,
                "concept": {
                    "kind": "recursion_tree",
                    "title": title,
                    "nodes": [
                        {"id": nid, "label": label, "x": x, "y": y}
                        for nid, (label, x, y) in layout.items() if nid in visible_set
                    ],
                    "edges": [[a, b] for a, b in edges if a in visible_set and b in visible_set],
                    "active": active,
                    "marker": marker,
                    "memo": memo,
                },
            },
        })
    return steps


def _build_recursion_demo(title, source, steps, output):
    return {
        "title": title,
        "source": source,
        "important_vars": {"result": "结果", "phase": "阶段"},
        "track_vars": {"primary": ["result", "phase"], "secondary": []},
        "var_classes": {
            "result": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": output}],
        "steps": steps,
    }


def concept_demo_monte_carlo_pi():
    source = [
        "算法: 蒙特卡洛估算圆周率",
        "输入: 随机点数量 samples",
        "输出: pi 的近似值",
        "",
        "在正方形中随机撒点",
        "统计落在四分之一圆内的点 inside",
        "pi ≈ 4 * inside / samples",
        "",
        "点越多, 估计越稳定",
    ]
    raw_points = [
        (0.12,0.18),(0.82,0.18),(0.36,0.27),(0.67,0.31),(0.22,0.76),(0.58,0.64),
        (0.91,0.44),(0.44,0.88),(0.73,0.72),(0.16,0.52),(0.31,0.42),(0.49,0.20),
        (0.87,0.81),(0.62,0.12),(0.28,0.93),(0.53,0.48),(0.77,0.54),(0.08,0.67),
        (0.39,0.69),(0.69,0.89),(0.93,0.23),(0.19,0.33),(0.57,0.79),(0.34,0.58),
        (0.71,0.16),(0.11,0.91),(0.84,0.62),(0.47,0.37),(0.26,0.14),(0.64,0.45),
    ]
    steps = []
    for idx, count in enumerate([4, 8, 14, 22, 30]):
        pts = []
        inside = 0
        for x, y in raw_points[:count]:
            hit = x * x + y * y <= 1
            inside += 1 if hit else 0
            pts.append([x, y, hit])
        pi = round(4 * inside / count, 3)
        steps.append({
            "step": idx,
            "line": 5 if idx == 0 else 7,
            "type": "exec",
            "vars": {
                "samples": count,
                "inside": inside,
                "pi": pi,
                "phase": f"{inside}/{count} 个点落在圆内, pi≈{pi}",
                "concept": {
                    "kind": "monte_carlo",
                    "points": pts,
                    "inside": inside,
                    "samples": count,
                    "pi": pi,
                },
            },
        })
    return {
        "title": "蒙特卡洛_求圆周率",
        "source": source,
        "important_vars": {"samples": "样本数", "inside": "圆内点", "pi": "估计值", "phase": "阶段"},
        "track_vars": {"primary": ["samples", "inside", "pi", "phase"], "secondary": []},
        "var_classes": {
            "samples": {"category": "primary", "type": "scalar"},
            "inside": {"category": "primary", "type": "scalar"},
            "pi": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": "概念动画：用随机点比例估计面积比例, 从而估算 π。"}],
        "steps": steps,
    }


def concept_demo_birthday_paradox():
    source = [
        "算法: 生日悖论模拟验证",
        "输入: 人数 n, 模拟次数 trials",
        "输出: 至少两人同生日的概率",
        "",
        "重复 trials 次:",
        "    清空 365 天日历",
        "    让 n 个人依次随机选择生日",
        "    如果某一天已经有人, 发生碰撞",
        "统计碰撞次数 / trials",
    ]
    birthdays = [32, 211, 87, 310, 144, 18, 270, 59, 183, 241, 87, 6, 336, 122, 198, 260, 41, 318, 159, 224, 14, 291, 101]
    states = [
        (5, "一次模拟从空日历开始", 0, 0.0, False),
        (7, "人数变多, 已占用的日期越来越多", 6, 0.04, False),
        (7, "不是要和某个固定人相同, 而是任意两人都可能撞上", 10, 0.12, False),
        (8, "第 11 个人生日落在已有日期: 发生碰撞", 11, 0.51, True),
        (8, "23 个人时, 至少一对同生日的概率已经超过一半", 23, 0.507, True),
        (9, "50 个人时, 概率接近 97%", 50, 0.97, True),
    ]
    steps = []
    for idx, (line, phase, people, probability, collision) in enumerate(states):
        shown = birthdays[:min(people, len(birthdays))]
        duplicate_day = 87 if people >= 11 else None
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "people": people,
                "probability": round(probability * 100, 1),
                "phase": phase,
                "concept": {
                    "kind": "birthday",
                    "people": people,
                    "birthdays": shown,
                    "duplicateDay": duplicate_day,
                    "probability": probability,
                    "collision": collision,
                },
            },
        })
    return {
        "title": "生日悖论_模拟验证",
        "source": source,
        "important_vars": {"people": "人数", "probability": "碰撞概率", "phase": "阶段"},
        "track_vars": {"primary": ["people", "probability", "phase"], "secondary": []},
        "var_classes": {
            "people": {"category": "primary", "type": "scalar"},
            "probability": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": "概念动画：可能配对的人数增长很快, 所以 23 个人就有约 50% 概率同生日。"}],
        "steps": steps,
    }


def concept_demo_randomized_quick_sort():
    source = [
        "算法: 随机化快速排序",
        "输入: 一个无序数组 arr",
        "输出: 排好序的数组",
        "",
        "函数 randomized_quick_sort(arr, left, right):",
        "    随机选择一个 pivot",
        "    把 pivot 换到区间末尾",
        "    分区: 小的去左边, 大的留右边",
        "    pivot 站到最终位置",
        "    继续处理左右子数组",
        "    随机性让坏输入不再固定触发最坏情况",
    ]
    rows = [
        (5, [5, 3, 8, 1, 9, 2, 7, 4, 6], 0, [0], [], [], [0, 8], "原数组顺序不重要, 这一轮先随机抽到 5"),
        (6, [6, 3, 8, 1, 9, 2, 7, 4, 5], 8, [0, 8], [], [], [0, 8], "把随机 pivot 换到末尾, 后面就能用普通分区"),
        (8, [3, 1, 2, 4, 5, 8, 7, 9, 6], 4, [0, 1, 2, 3, 5, 6, 7, 8], [0, 1, 2, 3], [4], [0, 8], "一轮分区后, 5 已经归位; 小的在左, 大的在右"),
        (10, [1, 2, 3, 4, 5, 8, 7, 9, 6], 2, [0, 1, 2, 3], [0, 1], [2, 4], [0, 3], "左半段继续随机选 pivot, 避免每次都碰到坏端点"),
        (10, [1, 2, 3, 4, 5, 6, 7, 8, 9], 7, [5, 6, 7, 8], [5, 6], [0, 1, 2, 3, 4, 7], [5, 8], "右半段继续分区, pivot 陆续站到自己的最终位置"),
        (11, [1, 2, 3, 4, 5, 6, 7, 8, 9], None, [], [], list(range(9)), [], "结果仍是确定正确的排序; 随机性主要改善期望运行时间"),
    ]
    steps = []
    for idx, (line, values, pivot_idx, compare, left_zone, fixed, active_range, phase) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "pivot": "-" if pivot_idx is None else values[pivot_idx],
                "range": "-" if not active_range else f"{active_range[0]}..{active_range[1]}",
                "phase": phase,
                "concept": {
                    "kind": "array_process",
                    "mode": "quick",
                    "title": "随机化快速排序",
                    "values": values,
                    "pivotIdx": pivot_idx,
                    "compare": compare,
                    "leftZone": left_zone,
                    "sorted": fixed,
                    "range": active_range,
                    "phase": phase,
                },
            },
        })
    return _build_array_process_demo(
        "随机化快速排序",
        source,
        steps,
        {"pivot": "随机基准", "range": "当前区间", "phase": "阶段"},
        ["pivot", "range", "phase"],
        "理解动画：随机快排不是换了排序结果, 而是换了 pivot 的选择方式, 让最坏情况不容易被固定输入卡住。",
    )


def concept_demo_reservoir_sampling():
    source = [
        "算法: 蓄水池抽样",
        "输入: 不知道总长度的数据流 stream, 抽样容量 k",
        "输出: 等概率保留 k 个元素",
        "",
        "先把前 k 个元素放入 reservoir",
        "从第 k+1 个元素开始, 当前序号为 i",
        "    以 k / i 的概率考虑它",
        "    如果命中, 随机替换 reservoir 中的一个位置",
        "数据流结束, reservoir 就是样本",
    ]
    rows = [
        (5, "先把前 3 个元素直接放入水池", 3, ["A", "B", "C", "D", "E", "F", "G", "H"], ["A", "B", "C"], 2, [], "1"),
        (7, "看到 D: 以 3/4 的概率进入候选", 4, ["A", "B", "C", "D", "E", "F", "G", "H"], ["A", "B", "C"], 3, [], "3/4"),
        (8, "D 命中抽样, 随机替换水池中的 B", 4, ["A", "B", "C", "D", "E", "F", "G", "H"], ["A", "D", "C"], 3, [1], "3/4"),
        (7, "看到 E: 进入概率降为 3/5", 5, ["A", "B", "C", "D", "E", "F", "G", "H"], ["A", "D", "C"], 4, [], "3/5"),
        (8, "E 这次没命中, 水池保持不变", 5, ["A", "B", "C", "D", "E", "F", "G", "H"], ["A", "D", "C"], 4, [], "3/5"),
        (8, "F 命中后替换 A, 旧元素也可能被公平淘汰", 6, ["A", "B", "C", "D", "E", "F", "G", "H"], ["F", "D", "C"], 5, [0], "3/6"),
        (9, "数据流继续变长, 每个元素最终留下的机会仍相同", 8, ["A", "B", "C", "D", "E", "F", "G", "H"], ["F", "H", "C"], 7, [1], "3/8"),
    ]
    steps = []
    for idx, (line, phase, seen, stream, reservoir, current, replaced, prob) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "i": seen,
                "probability": prob,
                "reservoir": ",".join(reservoir),
                "phase": phase,
                "concept": {
                    "kind": "reservoir_sampling",
                    "stream": stream,
                    "seen": seen,
                    "reservoir": reservoir,
                    "current": current,
                    "replaced": replaced,
                    "probability": prob,
                    "k": 3,
                    "phase": phase,
                },
            },
        })
    return {
        "title": "蓄水池抽样",
        "source": source,
        "important_vars": {"i": "已看数量", "probability": "进入概率", "reservoir": "水池", "phase": "阶段"},
        "track_vars": {"primary": ["i", "probability", "reservoir", "phase"], "secondary": []},
        "var_classes": {
            "i": {"category": "primary", "type": "scalar"},
            "probability": {"category": "primary", "type": "scalar"},
            "reservoir": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": "概念动画：蓄水池抽样让未知长度数据流里的每个元素最终被保留的概率相同。"}],
        "steps": steps,
    }


def concept_demo_randomized_select():
    source = [
        "算法: 随机化选择第 k 小",
        "输入: 数组 arr, 目标排名 k",
        "输出: 第 k 小的元素",
        "",
        "函数 randomized_select(arr, left, right, k):",
        "    随机选择 pivot 并分区",
        "    计算 pivot 在当前区间的排名 rank",
        "    如果 rank == k, pivot 就是答案",
        "    如果 rank > k, 只去左边找",
        "    如果 rank < k, 只去右边找第 k-rank 小",
    ]
    rows = [
        (5, [7, 10, 4, 3, 20, 15], 1, [1], [], [], [0, 5], "要找第 3 小, 第一轮随机抽到 pivot=10"),
        (7, [7, 4, 3, 10, 20, 15], 3, [0, 1, 2, 4, 5], [0, 1, 2], [3], [0, 5], "分区后 10 的排名是 4, 第 3 小一定在左边"),
        (9, [7, 4, 3, 10, 20, 15], 0, [0, 1, 2], [], [3], [0, 2], "右边整段都可以丢掉, 只在左半段继续找"),
        (5, [3, 4, 7, 10, 20, 15], 2, [0, 1, 2], [0, 1], [2, 3], [0, 2], "这次随机 pivot=7, 它在左半段里的排名正好是 3"),
        (8, [3, 4, 7, 10, 20, 15], None, [], [], [2], [], "找到答案 7; 随机性影响过程长短, 不影响答案正确性"),
    ]
    steps = []
    for idx, (line, values, pivot_idx, compare, left_zone, fixed, active_range, phase) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "k": 3,
                "pivot": "-" if pivot_idx is None else values[pivot_idx],
                "range": "-" if not active_range else f"{active_range[0]}..{active_range[1]}",
                "phase": phase,
                "concept": {
                    "kind": "array_process",
                    "mode": "quick",
                    "title": "随机化选择",
                    "values": values,
                    "pivotIdx": pivot_idx,
                    "compare": compare,
                    "leftZone": left_zone,
                    "sorted": fixed,
                    "range": active_range,
                    "phase": phase,
                },
            },
        })
    return _build_array_process_demo(
        "随机化选择第 k 小",
        source,
        steps,
        {"k": "目标排名", "pivot": "随机基准", "range": "当前区间", "phase": "阶段"},
        ["k", "pivot", "range", "phase"],
        "理解动画：随机化选择像快排分区, 但每轮只保留答案可能所在的一边。",
    )


def _list_visual_algo(title, source, rows, output):
    steps = []
    for idx, row in enumerate(rows):
        steps.append({
            "step": idx,
            "line": row.get("line", 1),
            "type": "exec",
            "vars": row["vars"],
        })
    important = {"phase": "阶段"}
    for key in ["prev", "curr", "nextTemp", "slow", "fast", "entry"]:
        if any(key in (row["vars"] or {}) for row in rows):
            important[key] = key
    var_classes = {
        "list": {"category": "primary", "type": "list"},
        "phase": {"category": "primary", "type": "scalar"},
    }
    for key in important:
        if key not in var_classes:
            var_classes[key] = {"category": "primary", "type": "scalar"}
    return {
        "title": title,
        "source": source,
        "important_vars": important,
        "track_vars": {"primary": list(important.keys()), "secondary": []},
        "var_classes": var_classes,
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": output}],
        "steps": steps,
    }


def concept_demo_reverse_list():
    source = [
        "算法: 反转链表",
        "输入: 1 → 2 → 3 → 4 → 5 → NULL",
        "输出: 5 → 4 → 3 → 2 → 1 → NULL",
        "",
        "prev = NULL, curr = head",
        "while curr != NULL:",
        "    nextTemp = curr->next  # 留后路",
        "    curr->next = prev       # 向后转",
        "    prev = curr             # prev 跟上",
        "    curr = nextTemp         # curr 前进",
    ]
    rows = [
        {"line": 5, "vars": {"list": [1, 2, 3, 4, 5], "prev": -1, "curr": 0, "nextTemp": -1, "phase": "一开始 prev 指向 NULL, curr 站在头节点 1"}},
        {"line": 7, "vars": {"list": [1, 2, 3, 4, 5], "prev": -1, "curr": 0, "nextTemp": 1, "phase": "先保存 nextTemp=2, 否则 1 转身后会找不到后面的链"}},
        {"line": 8, "vars": {"list": [1], "prev": -1, "curr": 0, "nextTemp": 1, "phase": "让 1 指向 NULL, 已反转部分变成 1 → NULL"}},
        {"line": 8, "vars": {"list": [2, 1], "prev": 1, "curr": 0, "nextTemp": 2, "phase": "处理 2: 让 2 指向 1, 已反转部分变成 2 → 1"}},
        {"line": 8, "vars": {"list": [3, 2, 1], "prev": 1, "curr": 0, "nextTemp": 3, "phase": "处理 3: 已反转链条继续向左增长"}},
        {"line": 8, "vars": {"list": [5, 4, 3, 2, 1], "prev": 0, "curr": -1, "nextTemp": -1, "phase": "curr 到达 NULL, prev 停在新头节点 5"}},
    ]
    return _list_visual_algo(
        "反转链表",
        source,
        rows,
        "理解动画：反转链表的关键是先用 nextTemp 留后路, 再让当前节点向后转。",
    )


def concept_demo_cycle_detection():
    source = [
        "算法: 快慢指针找环入口",
        "输入: 1 → 2 → 3 → 4 → 5, 且 5 指回 3",
        "输出: 环入口节点 3",
        "",
        "slow 每次走 1 步, fast 每次走 2 步",
        "如果两者相遇, 说明有环",
        "把 fast 拉回 head",
        "slow 和 fast 同速前进",
        "再次相遇处就是环入口",
    ]
    rows = [
        {"line": 4, "vars": {"list": [1, 2, 3, 4, 5], "slow": 0, "fast": 0, "entry": 2, "phase": "链表尾部 5 实际指回 3, 形成一个环"}},
        {"line": 5, "vars": {"list": [1, 2, 3, 4, 5], "slow": 1, "fast": 2, "entry": 2, "phase": "第一轮: slow 到 2, fast 到 3"}},
        {"line": 5, "vars": {"list": [1, 2, 3, 4, 5], "slow": 2, "fast": 4, "entry": 2, "phase": "第二轮: slow 进入环入口 3, fast 到 5"}},
        {"line": 6, "vars": {"list": [1, 2, 3, 4, 5], "slow": 3, "fast": 3, "entry": 2, "phase": "继续跑, slow 和 fast 在环里相遇, 说明有环"}},
        {"line": 7, "vars": {"list": [1, 2, 3, 4, 5], "slow": 3, "fast": 0, "entry": 2, "phase": "把 fast 拉回头节点, 两个指针改成同速"}},
        {"line": 9, "vars": {"list": [1, 2, 3, 4, 5], "slow": 2, "fast": 2, "entry": 2, "phase": "再次相遇在节点 3, 它就是环入口"}},
    ]
    return _list_visual_algo(
        "快慢指针_环检测",
        source,
        rows,
        "理解动画：快慢指针先证明有环, 再通过同速相遇找出环入口。",
    )


def _tree_visual_algo(title, source, rows, output):
    steps = [{"step": idx, "line": row.get("line", 1), "type": "exec", "vars": row["vars"]} for idx, row in enumerate(rows)]
    important = {"phase": "阶段"}
    for key in ["root", "node", "current", "p", "q", "lca"]:
        if any(key in (row["vars"] or {}) for row in rows):
            important[key] = key
    var_classes = {
        "tree": {"category": "primary", "type": "tree"},
        "phase": {"category": "primary", "type": "scalar"},
    }
    for key in important:
        if key not in var_classes:
            var_classes[key] = {"category": "primary", "type": "scalar"}
    return {
        "title": title,
        "source": source,
        "important_vars": important,
        "track_vars": {"primary": list(important.keys()), "secondary": []},
        "var_classes": var_classes,
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": output}],
        "steps": steps,
    }


def concept_demo_level_order():
    source = [
        "算法: 二叉树层序遍历",
        "输入: 一棵二叉树",
        "输出: 按层排列的节点值",
        "",
        "root 先入队",
        "while 队列不空:",
        "    先记下当前层人数 currentLevelSize",
        "    出队当前层所有节点",
        "    把它们的左右孩子加入队尾",
    ]
    tree = [3, [9, None, None], [20, [15, None, None], [7, None, None]]]
    rows = [
        {"line": 5, "vars": {"tree": tree, "root": 3, "node": 3, "phase": "根节点 3 先入队, 队列里只有第一层"}},
        {"line": 7, "vars": {"tree": tree, "root": 3, "node": 3, "phase": "先固定 currentLevelSize=1, 这一轮只处理第 1 层"}},
        {"line": 8, "vars": {"tree": tree, "root": 3, "node": 9, "phase": "处理 3 后, 它的孩子 9 和 20 排到队尾"}},
        {"line": 7, "vars": {"tree": tree, "root": 3, "node": 20, "phase": "第二层人数固定为 2, 不会把第三层混进来"}},
        {"line": 9, "vars": {"tree": tree, "root": 3, "node": 15, "phase": "处理 20 时, 15 和 7 进入下一层队列"}},
        {"line": 9, "vars": {"tree": tree, "root": 3, "node": 7, "phase": "队列按先进先出工作, 结果是 [3], [9,20], [15,7]"}},
    ]
    return _tree_visual_algo(
        "层序遍历",
        source,
        rows,
        "理解动画：层序遍历一定要先固定当前层人数, 再让下一层节点去队尾排队。",
    )


def concept_demo_lca():
    source = [
        "算法: 最近公共祖先 LCA",
        "输入: root, p, q",
        "输出: p 和 q 最近的公共祖先",
        "",
        "如果 root 是空、p 或 q, 直接返回 root",
        "left = 去左子树找",
        "right = 去右子树找",
        "如果 left 和 right 都不空, root 就是 LCA",
        "否则把非空结果继续往上报",
    ]
    tree = [3, [5, [6, None, None], [2, None, None]], [1, [0, None, None], [8, None, None]]]
    rows = [
        {"line": 5, "vars": {"tree": tree, "root": 3, "p": 6, "q": 2, "phase": "目标是找 6 和 2 的最近公共祖先"}},
        {"line": 6, "vars": {"tree": tree, "root": 3, "node": 6, "p": 6, "q": 2, "phase": "左边先找到 p=6, 把这个消息往上报"}},
        {"line": 7, "vars": {"tree": tree, "root": 3, "node": 2, "p": 6, "q": 2, "phase": "右边又找到 q=2, 也把消息往上报"}},
        {"line": 8, "vars": {"tree": tree, "root": 3, "node": 5, "p": 6, "q": 2, "lca": 5, "phase": "节点 5 的左右两边各找到一个目标, 5 就是 LCA"}},
        {"line": 9, "vars": {"tree": tree, "root": 3, "p": 6, "q": 8, "phase": "换成找 6 和 8: 两个目标分散在根的两侧"}},
        {"line": 8, "vars": {"tree": tree, "root": 3, "p": 6, "q": 8, "lca": 3, "phase": "左右子树各报告一个目标, 根节点 3 就是最近公共祖先"}},
    ]
    return _tree_visual_algo(
        "最近公共祖先",
        source,
        rows,
        "理解动画：LCA 是后序遍历的汇报题, 左右两边都找到目标时, 当前节点就是汇合点。",
    )


def concept_demo_sliding_window_min_subarray():
    source = [
        "算法: 滑动窗口最短子数组",
        "输入: nums=[2,3,1,2,4,3], target=7",
        "输出: 和至少为 7 的最短长度",
        "",
        "right 向右扩展窗口",
        "window_sum += nums[right]",
        "当 window_sum >= target:",
        "    记录当前长度",
        "    left 向右收缩窗口",
    ]
    rows = [
        (5, [2, 3, 1, 2, 4, 3], [0, 0], [0], "2", "-", "right 扩展, 窗口和=2, 还不够 7"),
        (5, [2, 3, 1, 2, 4, 3], [0, 3], [0, 1, 2, 3], "8", "4", "窗口 [2,3,1,2] 达标, 先记录长度 4"),
        (8, [2, 3, 1, 2, 4, 3], [1, 3], [1, 2, 3], "6", "4", "移出左端 2 后不达标, 继续扩展 right"),
        (7, [2, 3, 1, 2, 4, 3], [2, 4], [2, 3, 4], "7", "3", "窗口 [1,2,4] 达标, 最短长度变成 3"),
        (8, [2, 3, 1, 2, 4, 3], [4, 5], [4, 5], "7", "2", "最后窗口 [4,3] 达标, 答案更新为 2"),
    ]
    steps = []
    for idx, (line, values, active_range, compare, window_sum, best, phase) in enumerate(rows):
        steps.append({"step": idx, "line": line, "type": "exec", "vars": {
            "left": active_range[0], "right": active_range[1], "window_sum": window_sum, "best": best, "phase": phase,
            "concept": {"kind": "array_process", "mode": "linear_search", "title": "滑动窗口", "values": values, "range": active_range, "compare": compare, "phase": phase}
        }})
    return _build_array_process_demo("滑动窗口_最短子数组", source, steps, {"left": "左边界", "right": "右边界", "window_sum": "窗口和", "best": "最短长度", "phase": "阶段"}, ["left", "right", "window_sum", "best", "phase"], "理解动画：正整数数组里窗口和随 right 扩展变大, 达标后再用 left 收缩。")


def concept_demo_two_sum_two_pointers():
    source = [
        "算法: 有序数组两数之和",
        "输入: nums=[2,7,11,15], target=9",
        "left 从左端出发, right 从右端出发",
        "sum 太大: right 左移",
        "sum 太小: left 右移",
        "sum 等于 target: 找到答案",
    ]
    rows = [
        (3, [2, 7, 11, 15], [0, 3], [0, 3], "17", "2+15 太大, right 左移"),
        (4, [2, 7, 11, 15], [0, 2], [0, 2], "13", "2+11 仍太大, right 继续左移"),
        (6, [2, 7, 11, 15], [0, 1], [0, 1], "9", "2+7 正好等于 9, 找到下标 [0,1]"),
    ]
    steps = []
    for idx, (line, values, active_range, compare, total, phase) in enumerate(rows):
        steps.append({"step": idx, "line": line, "type": "exec", "vars": {
            "left": active_range[0], "right": active_range[1], "sum": total, "phase": phase,
            "concept": {"kind": "array_process", "mode": "binary", "title": "双指针两数之和", "values": values, "range": active_range, "compare": compare, "target": 9, "phase": phase}
        }})
    return _build_array_process_demo("双指针_两数之和", source, steps, {"left": "左指针", "right": "右指针", "sum": "当前和", "phase": "阶段"}, ["left", "right", "sum", "phase"], "理解动画：数组有序时, 每次移动一个指针都能排除一批不可能组合。")


def concept_demo_fast_slow_variants():
    source = [
        "算法: 快慢指针两个变体",
        "变体一: fast 每次两步, slow 每次一步, 找中点",
        "变体二: fast 先走 k 步, 再和 slow 同速, 找倒数第 k 个",
    ]
    rows = [
        {"line": 2, "vars": {"list": [1, 2, 3, 4, 5], "slow": 0, "fast": 0, "phase": "找中点: slow 和 fast 都从头出发"}},
        {"line": 2, "vars": {"list": [1, 2, 3, 4, 5], "slow": 1, "fast": 2, "phase": "fast 走两步, slow 走一步"}},
        {"line": 2, "vars": {"list": [1, 2, 3, 4, 5], "slow": 2, "fast": 4, "phase": "fast 到末尾时, slow 正好停在中点 3"}},
        {"line": 3, "vars": {"list": [1, 2, 3, 4, 5], "slow": 0, "fast": 2, "phase": "找倒数第 2 个: fast 先领先 2 步"}},
        {"line": 3, "vars": {"list": [1, 2, 3, 4, 5], "slow": 3, "fast": -1, "phase": "fast 到 NULL 时, slow 停在倒数第 2 个节点 4"}},
    ]
    return _list_visual_algo("快慢指针_中点与倒数", source, rows, "理解动画：快慢指针的本质是制造距离差, 让 slow 停在我们想要的位置。")


def concept_demo_three_sum():
    source = [
        "算法: 三数之和",
        "先排序: [-4,-1,-1,0,1,2]",
        "固定 nums[i]",
        "在右侧用 left/right 找两数之和",
        "跳过重复值, 避免重复三元组",
    ]
    rows = [
        (2, [-4, -1, -1, 0, 1, 2], [0, 5], [0], "-4", "固定 -4, 右侧再找两个数"),
        (4, [-4, -1, -1, 0, 1, 2], [1, 5], [1, 5], "-3", "-4 + -1 + 2 太小, left 右移"),
        (3, [-4, -1, -1, 0, 1, 2], [1, 5], [1], "-1", "固定 -1, 目标变成找两个数和为 1"),
        (4, [-4, -1, -1, 0, 1, 2], [2, 5], [1, 2, 5], "0", "找到 [-1,-1,2]"),
        (4, [-4, -1, -1, 0, 1, 2], [3, 4], [1, 3, 4], "0", "继续找到 [-1,0,1], 并跳过重复固定值"),
    ]
    steps = []
    for idx, (line, values, active_range, compare, total, phase) in enumerate(rows):
        fixed = compare[:1] if compare else []
        steps.append({"step": idx, "line": line, "type": "exec", "vars": {
            "i": fixed[0] if fixed else "-", "sum": total, "phase": phase,
            "concept": {"kind": "array_process", "mode": "quick", "title": "三数之和", "values": values, "range": active_range, "compare": compare, "sorted": fixed, "phase": phase}
        }})
    return _build_array_process_demo("双指针_三数之和", source, steps, {"i": "固定下标", "sum": "三数和", "phase": "阶段"}, ["i", "sum", "phase"], "理解动画：三数之和先排序, 再把问题化成“固定一个数 + 两数之和”。")


def concept_demo_next_greater_stack():
    source = [
        "算法: 单调栈找下一个更大元素",
        "栈里保存还没找到答案的下标",
        "新元素比栈顶大时, 它就是栈顶的答案",
        "弹出并记录答案, 当前下标再入栈",
    ]
    grid_states = [
        ([[-1, -1, -1, -1, -1], [2, "", "", "", ""]], [1, 0], "i=0, 2 入栈等待答案"),
        ([[-1, -1, -1, -1, -1], [2, 1, "", "", ""]], [1, 1], "i=1, 1 不比 2 大, 也入栈"),
        ([[-1, 2, -1, -1, -1], [2, 2, "", "", ""]], [0, 1], "i=2, 2 是 nums[1] 的下一个更大元素"),
        ([[4, 2, 4, -1, -1], [4, "", "", "", ""]], [0, 0], "i=3, 4 连续解决 nums[2] 和 nums[0]"),
        ([[4, 2, 4, -1, -1], [4, 3, "", "", ""]], [1, 1], "i=4, 3 入栈; 栈里剩下的右侧没有更大元素"),
    ]
    steps = []
    for idx, (grid, active, phase) in enumerate(grid_states):
        steps.append({"step": idx, "line": 3, "type": "exec", "vars": {
            "stack": ",".join(str(x) for x in grid[1] if x != ""),
            "phase": phase,
            "concept": {"kind": "dp_table", "title": "单调栈", "subtitle": "上排是答案, 下排是栈中等待的人", "grid": grid, "rowLabels": ["result", "stack"], "colLabels": ["0", "1", "2", "3", "4"], "active": active, "refs": [], "badges": ["nums: 2,1,2,4,3"]}
        }})
    return _build_simple_concept_algo("单调栈_下一个更大", source, steps, ["stack", "phase"], "理解动画：单调栈保存还没找到答案的人, 新来的高个子会一次解决多个矮个子。")


def concept_demo_prefix_sum():
    source = [
        "算法: 前缀和",
        "prefix[0] = 0",
        "prefix[i+1] = prefix[i] + nums[i]",
        "区间和 = prefix[right+1] - prefix[left]",
    ]
    grid = [[0, 1, 3, 6, 10, 15], [1, 2, 3, 4, 5, ""]]
    rows = [
        ([0, 0], [], ["prefix[0]=0"], "先放一个哨兵 0, 方便处理从 0 开始的区间"),
        ([0, 3], [[1, 0], [1, 1], [1, 2]], ["prefix[3]=6"], "prefix[3] 表示 nums[0..2] 的和"),
        ([0, 4], [[0, 1], [0, 4], [1, 1], [1, 2], [1, 3]], ["区间[1,3]"], "区间 [1,3] = prefix[4] - prefix[1] = 10 - 1 = 9"),
    ]
    steps = []
    for idx, (active, refs, badges, phase) in enumerate(rows):
        steps.append({"step": idx, "line": 3, "type": "exec", "vars": {
            "range": badges[0], "phase": phase,
            "concept": {"kind": "dp_table", "title": "前缀和", "subtitle": "多存一个 0, 区间查询就变成一次减法", "grid": grid, "rowLabels": ["prefix", "nums"], "colLabels": ["0", "1", "2", "3", "4", "5"], "active": active, "refs": refs, "badges": badges}
        }})
    return _build_simple_concept_algo("前缀和", source, steps, ["range", "phase"], "理解动画：前缀和把区间求和变成两个前缀值相减。")


def concept_demo_difference_array():
    source = [
        "算法: 差分数组",
        "diff[0] = nums[0]",
        "diff[i] = nums[i] - nums[i-1]",
        "区间 [l,r] 加 val:",
        "    diff[l] += val",
        "    diff[r+1] -= val",
        "最后对 diff 求前缀和还原数组",
    ]
    rows = [
        ([[1, 2, 3, 4, 5], [1, 1, 1, 1, 1], ["", "", "", "", ""]], [1, 0], [], ["构建 diff"], "原数组相邻差都为 1"),
        ([[1, 2, 3, 4, 5], [1, 11, 1, 1, -9], ["", "", "", "", ""]], [1, 1], [[1, 1], [1, 4]], ["diff[1]+=10", "diff[4]-=10"], "区间 [1,3] 加 10, 只改 diff[1] 和 diff[4]"),
        ([[1, 2, 3, 4, 5], [1, 11, 1, 1, -9], [1, 12, 13, 14, 5]], [2, 3], [[2, 1], [2, 2], [2, 3]], ["还原结果"], "最后做前缀和, 中间一段整体加了 10"),
    ]
    steps = []
    for idx, (grid, active, refs, badges, phase) in enumerate(rows):
        steps.append({"step": idx, "line": 4, "type": "exec", "vars": {
            "operation": badges[0], "phase": phase,
            "concept": {"kind": "dp_table", "title": "差分数组", "subtitle": "区间修改只动两个端点, 最后统一还原", "grid": grid, "rowLabels": ["nums", "diff", "result"], "colLabels": ["0", "1", "2", "3", "4"], "active": active, "refs": refs, "badges": badges}
        }})
    return _build_simple_concept_algo("差分数组", source, steps, ["operation", "phase"], "理解动画：差分数组把区间加法压缩成两个端点的变化。")


def concept_demo_bloom_filter():
    source = [
        "算法: 布隆过滤器",
        "输入: 要加入或查询的字符串 key",
        "输出: 一定不存在 / 可能存在",
        "",
        "准备一个全 0 的 bit 数组",
        "插入 key:",
        "    用多个哈希函数算出多个位置",
        "    把这些位置都置为 1",
        "查询 key:",
        "    如果任一位置是 0, 一定不存在",
        "    如果所有位置都是 1, 只能说可能存在",
    ]
    states = [
        (4, "初始 bit 数组全是 0", [], [], "", "init", "准备插入"),
        (6, "插入 apple: 三个哈希函数落到 2、7、11", [2, 7, 11], [2, 7, 11], "apple", "insert", "置 1"),
        (6, "插入 banana: 位置 7 已经是 1, 共享没有关系", [1, 2, 7, 11, 14], [1, 7, 14], "banana", "insert", "置 1"),
        (8, "查询 grape: 三个位置里 3 是 0, 所以一定不存在", [1, 2, 7, 11, 14], [3, 7, 12], "grape", "miss", "一定不存在"),
        (8, "查询 apple: 2、7、11 都是 1, 只能说可能存在", [1, 2, 7, 11, 14], [2, 7, 11], "apple", "maybe", "可能存在"),
        (10, "查询 peach: 1、2、14 都是 1, 但它其实没插入过", [1, 2, 7, 11, 14], [1, 2, 14], "peach", "false_positive", "可能误判"),
        (10, "布隆过滤器不会漏报, 但可能误报", [1, 2, 7, 11, 14], [], "", "done", "结论"),
    ]
    steps = []
    for idx, (line, phase, bits, hashes, key, mode, verdict) in enumerate(states):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "key": key or "-",
                "verdict": verdict,
                "phase": phase,
                "concept": {
                    "kind": "bloom_filter",
                    "title": "布隆过滤器",
                    "size": 16,
                    "bits": bits,
                    "hashes": hashes,
                    "key": key,
                    "mode": mode,
                    "verdict": verdict,
                },
            },
        })
    return _build_simple_concept_algo(
        "布隆过滤器",
        source,
        steps,
        ["key", "verdict", "phase"],
        "概念动画：布隆过滤器用多个哈希位置共同判断, 0 表示一定不存在, 全 1 只表示可能存在。",
    )


def concept_demo_bitmask_tsp():
    source = [
        "算法: 状态压缩 DP 求 TSP",
        "输入: 城市距离矩阵 dist",
        "输出: 从 A 出发访问所有城市再回 A 的最短路",
        "",
        "用 bitmask 表示已经访问过的城市集合",
        "dp[mask][i] 表示到达城市 i 时的最短距离",
        "从 dp[0001][A] = 0 开始",
        "枚举下一个未访问城市 j",
        "更新 dp[mask | (1<<j)][j]",
        "最后从所有城市都访问的状态回到 A",
    ]
    cities = ["A", "B", "C", "D"]
    edges = [["A", "B", 4], ["A", "C", 2], ["A", "D", 7], ["B", "C", 5], ["B", "D", 6], ["C", "D", 3]]
    states = [
        (6, "从 A 出发, mask=0001 表示只访问了 A", "0001", "A", 0, [], [["0001", "A", 0]], []),
        (8, "从 A 可以去 B、C、D, 分别打开对应的 bit", "0001", "A", 0, ["B", "C", "D"], [["0011", "B", 4], ["0101", "C", 2], ["1001", "D", 7]], [["A", "B"], ["A", "C"], ["A", "D"]]),
        (8, "当前较短状态是到 C, mask=0101", "0101", "C", 2, ["B", "D"], [["0111", "B", 7], ["1101", "D", 5]], [["A", "C"], ["C", "D"]]),
        (8, "访问 B 后形成 mask=0111, 还差 D", "0111", "B", 7, ["D"], [["1111", "D", 13]], [["C", "B"], ["B", "D"]]),
        (8, "另一条路 A-C-D-B 更短, 更新 full mask 的 B 状态", "1111", "B", 11, [], [["1111", "B", 11], ["1111", "D", 13]], [["A", "C"], ["C", "D"], ["D", "B"]]),
        (9, "所有城市都访问后, 还要回到 A", "1111", "B", 11, ["A"], [["1111", "B", 11]], [["D", "B"], ["B", "A"]]),
        (9, "最短环路示意: A → C → D → B → A", "1111", "A", 15, [], [["答案", "A-C-D-B-A", 15]], [["A", "C"], ["C", "D"], ["D", "B"], ["B", "A"]]),
    ]
    steps = []
    for idx, (line, phase, mask, at, cost, choices, table, path) in enumerate(states):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "mask": mask,
                "city": at,
                "cost": cost,
                "phase": phase,
                "concept": {
                    "kind": "bitmask_tsp",
                    "title": "状态压缩 DP · TSP",
                    "cities": cities,
                    "edges": edges,
                    "mask": mask,
                    "city": at,
                    "cost": cost,
                    "choices": choices,
                    "table": table,
                    "path": path,
                },
            },
        })
    return _build_simple_concept_algo(
        "状态压缩DP_TSP",
        source,
        steps,
        ["mask", "city", "cost", "phase"],
        "概念动画：bitmask 把“访问过哪些城市”压成一个整数, DP 在这些集合状态之间转移。",
    )


def concept_demo_bitmask_ops():
    demo = concept_demo_bitmask_tsp()
    demo["title"] = "状态压缩_位运算"
    demo["source"] = [
        "算法: 状态压缩位运算",
        "输入: 城市距离矩阵 dist",
        "输出: 用二进制集合推进 TSP 状态",
        "",
        "mask 的每一位代表一个城市是否访问过",
        "mask & (1 << i) 判断城市 i 是否已访问",
        "mask | (1 << j) 把城市 j 加入集合",
        "dp[mask][i] 记录这个集合下停在 i 的最短距离",
        "不断打开新的 bit, 直到 mask 变成 1111",
    ]
    for step in demo.get("steps", []):
        concept = (step.get("vars") or {}).get("concept")
        if concept:
            concept["title"] = "状态压缩位运算"
    return demo


def _build_simple_concept_algo(title, source, steps, primary_vars, output):
    var_classes = {
        name: {"category": "primary", "type": "scalar"}
        for name in primary_vars
    }
    var_classes["concept"] = {"category": "secondary", "type": "concept"}
    return {
        "title": title,
        "source": source,
        "important_vars": {name: "状态" for name in primary_vars},
        "track_vars": {"primary": primary_vars, "secondary": []},
        "var_classes": var_classes,
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": output}],
        "steps": steps,
    }


def _branch_bound_steps(title, problem, nodes, edges, states, minimize=False):
    steps = []
    for idx, state in enumerate(states):
        line, phase, active, visible, pruned, best, queue, metrics = state
        visible_set = set(visible)
        pruned_set = set(pruned)
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "best": best,
                "queue": " → ".join(queue) if queue else "空",
                "phase": phase,
                "concept": {
                    "kind": "branch_bound",
                    "title": title,
                    "problem": problem,
                    "minimize": minimize,
                    "nodes": [
                        {**node, "status": ("best" if node["id"] == best else "pruned" if node["id"] in pruned_set else "current" if node["id"] == active else "live")}
                        for node in nodes
                        if node["id"] in visible_set
                    ],
                    "edges": [edge for edge in edges if edge[0] in visible_set and edge[1] in visible_set],
                    "active": active,
                    "pruned": pruned,
                    "best": best,
                    "queue": queue,
                    "metrics": metrics,
                },
            },
        })
    return steps


def concept_demo_branch_bound_knapsack():
    source = [
        "算法: 0-1 背包的分支限界",
        "目标: 在容量限制内, 找到最大价值",
        "",
        "把每个节点看成一个部分选择",
        "计算这个节点的价值上界 bound",
        "如果 bound <= 当前最优 best:",
        "    剪掉这一整棵子树",
        "否则:",
        "    放入优先队列继续扩展",
    ]
    nodes = [
        {"id": "root", "label": "未选", "x": 0.50, "y": 0.08, "bound": 42, "value": 0},
        {"id": "A", "label": "选A", "x": 0.30, "y": 0.28, "bound": 42, "value": 16},
        {"id": "noA", "label": "不选A", "x": 0.70, "y": 0.28, "bound": 31, "value": 0},
        {"id": "AB", "label": "选A,B", "x": 0.18, "y": 0.50, "bound": 39, "value": 30},
        {"id": "AnoB", "label": "选A,不选B", "x": 0.42, "y": 0.50, "bound": 35, "value": 16},
        {"id": "noAB", "label": "不选A,选B", "x": 0.61, "y": 0.50, "bound": 31, "value": 14},
        {"id": "noneAB", "label": "不选A,B", "x": 0.81, "y": 0.50, "bound": 22, "value": 0},
        {"id": "ABC", "label": "A,B,C", "x": 0.12, "y": 0.74, "bound": 39, "value": 39},
        {"id": "ABnoC", "label": "A,B,不C", "x": 0.28, "y": 0.74, "bound": 34, "value": 30},
        {"id": "AnoBC", "label": "A,C", "x": 0.42, "y": 0.74, "bound": 35, "value": 25},
    ]
    edges = [
        ["root", "A"], ["root", "noA"], ["A", "AB"], ["A", "AnoB"], ["noA", "noAB"], ["noA", "noneAB"],
        ["AB", "ABC"], ["AB", "ABnoC"], ["AnoB", "AnoBC"],
    ]
    states = [
        (4, "从空背包开始, 先估计理论上最多能拿到多少价值", "root", ["root"], [], "", ["root"], [{"label": "best", "value": 0}, {"label": "容量", "value": 10}, {"label": "root上界", "value": 42}]),
        (8, "展开 root: 选 A 和不选 A 两条分支都还可能超过 best", "A", ["root", "A", "noA"], [], "", ["A", "noA"], [{"label": "best", "value": 0}, {"label": "队列", "value": 2}, {"label": "最高上界", "value": 42}]),
        (8, "优先扩展上界最高的“选 A”", "A", ["root", "A", "noA"], [], "", ["A", "noA"], [{"label": "best", "value": 16}, {"label": "当前价值", "value": 16}, {"label": "bound", "value": 42}]),
        (8, "继续分成选 B / 不选 B, 两边都还值得看", "AB", ["root", "A", "noA", "AB", "AnoB"], [], "", ["AB", "AnoB", "noA"], [{"label": "best", "value": 16}, {"label": "AB价值", "value": 30}, {"label": "AB上界", "value": 39}]),
        (8, "AB 再选 C 得到可行解, best 提高到 39", "ABC", ["root", "A", "noA", "AB", "AnoB", "ABC", "ABnoC"], [], "ABC", ["ABC", "ABnoC", "AnoB", "noA"], [{"label": "best", "value": 39}, {"label": "当前价值", "value": 39}, {"label": "bound", "value": 39}]),
        (6, "AB 不选 C 的上界只有 34, 已经不可能超过 best=39, 剪掉", "ABnoC", ["root", "A", "noA", "AB", "AnoB", "ABC", "ABnoC"], ["ABnoC"], "ABC", ["AnoB", "noA"], [{"label": "best", "value": 39}, {"label": "剪枝上界", "value": 34}, {"label": "队列", "value": 2}]),
        (6, "不选 A 这边的上界也只有 31, 整片分支都不用展开", "noA", ["root", "A", "noA", "AB", "AnoB", "ABC", "ABnoC", "noAB", "noneAB"], ["ABnoC", "noA", "noAB", "noneAB"], "ABC", ["AnoB"], [{"label": "best", "value": 39}, {"label": "noA上界", "value": 31}, {"label": "节省分支", "value": 3}]),
        (9, "队列清空, 最优选择就是 A+B+C, 价值 39", "ABC", [n["id"] for n in nodes], ["ABnoC", "noA", "noAB", "noneAB", "AnoB", "AnoBC"], "ABC", [], [{"label": "best", "value": 39}, {"label": "答案", "value": "A+B+C"}, {"label": "状态", "value": "完成"}]),
    ]
    steps = _branch_bound_steps("0-1背包分支限界", "最大化价值: 用上界剪掉不可能更优的分支", nodes, edges, states)
    return _build_simple_concept_algo(
        "零一背包_分支限界",
        source,
        steps,
        ["best", "queue", "phase"],
        "概念动画：分支限界不是盲目枚举, 它用上界判断一整片搜索树是否还值得看。",
    )


def concept_demo_branch_bound_tsp():
    source = [
        "算法: 旅行商问题的分支限界",
        "目标: 从 A 出发访问所有城市后回到 A, 总路程最短",
        "",
        "把一条未完成路线看成一个节点",
        "估计这条路线的最小可能总长度 lower_bound",
        "如果 lower_bound >= 当前最短 best:",
        "    这条路线之后不可能更短, 剪掉",
        "否则:",
        "    放入优先队列继续扩展",
    ]
    nodes = [
        {"id": "A", "label": "A", "x": 0.50, "y": 0.08, "bound": 18, "value": 0},
        {"id": "AD", "label": "A-D", "x": 0.18, "y": 0.30, "bound": 15, "value": 2},
        {"id": "AB", "label": "A-B", "x": 0.40, "y": 0.30, "bound": 18, "value": 3},
        {"id": "AE", "label": "A-E", "x": 0.62, "y": 0.30, "bound": 19, "value": 7},
        {"id": "AC", "label": "A-C", "x": 0.84, "y": 0.30, "bound": 20, "value": 6},
        {"id": "ADE", "label": "A-D-E", "x": 0.18, "y": 0.54, "bound": 18, "value": 8},
        {"id": "ADC", "label": "A-D-C", "x": 0.37, "y": 0.54, "bound": 18, "value": 7},
        {"id": "ADB", "label": "A-D-B", "x": 0.56, "y": 0.54, "bound": 22, "value": 11},
        {"id": "ADEB", "label": "A-D-E-B", "x": 0.18, "y": 0.76, "bound": 18, "value": 11},
        {"id": "ADEC", "label": "A-D-E-C", "x": 0.39, "y": 0.76, "bound": 24, "value": 16},
        {"id": "ADEBC", "label": "A-D-E-B-C-A", "x": 0.18, "y": 0.94, "bound": 21, "value": 21},
    ]
    edges = [
        ["A", "AD"], ["A", "AB"], ["A", "AE"], ["A", "AC"],
        ["AD", "ADE"], ["AD", "ADC"], ["AD", "ADB"],
        ["ADE", "ADEB"], ["ADE", "ADEC"], ["ADEB", "ADEBC"],
    ]
    states = [
        (4, "从 A 出发, 5 个城市的根节点下界约为 18", "A", ["A"], [], "", ["A"], [{"label": "best", "value": "∞"}, {"label": "下界", "value": 18}, {"label": "城市", "value": 5}]),
        (8, "先展开第一站: B、C、D、E 四种选择进入队列", "AD", ["A", "AD", "AB", "AE", "AC"], [], "", ["AD", "AB", "AE", "AC"], [{"label": "best", "value": "∞"}, {"label": "最低下界", "value": 15}, {"label": "队列", "value": 4}]),
        (8, "下界最小的是 A-D, 优先扩展它", "AD", ["A", "AD", "AB", "AE", "AC"], [], "", ["AD", "AB", "AE", "AC"], [{"label": "当前路线", "value": "A-D"}, {"label": "已走", "value": 2}, {"label": "下界", "value": 15}]),
        (8, "A-D 后尝试去 B、C、E, 其中 A-D-E 更有希望", "ADE", ["A", "AD", "AB", "AE", "AC", "ADE", "ADC", "ADB"], [], "", ["ADE", "ADC", "AB", "AE", "AC", "ADB"], [{"label": "best", "value": "∞"}, {"label": "ADE下界", "value": 18}, {"label": "ADB下界", "value": 22}]),
        (8, "继续扩展 A-D-E, 先走到 B, 再补 C 回到 A", "ADEBC", ["A", "AD", "AB", "AE", "AC", "ADE", "ADC", "ADB", "ADEB", "ADEC", "ADEBC"], [], "ADEBC", ["ADC", "AB", "AE", "AC", "ADB", "ADEC"], [{"label": "best", "value": 21}, {"label": "路线", "value": "A-D-E-B-C-A"}, {"label": "长度", "value": 21}]),
        (7, "得到 best=21 后, 下界不小于 21 的分支都可以剪掉", "ADB", ["A", "AD", "AB", "AE", "AC", "ADE", "ADC", "ADB", "ADEB", "ADEC", "ADEBC"], ["ADB", "ADEC", "AC"], "ADEBC", ["ADC", "AB", "AE"], [{"label": "best", "value": 21}, {"label": "剪枝条件", "value": "lb>=21"}, {"label": "剪枝", "value": "是"}]),
        (7, "其他路线仍可能得到同样的 21, 但不会更短", "AB", [n["id"] for n in nodes], ["ADB", "ADEC", "AC", "AB", "AE"], "ADEBC", ["ADC"], [{"label": "best", "value": 21}, {"label": "最优不唯一", "value": "是"}, {"label": "目标", "value": "最短距离"}]),
        (9, "队列清空, 最短距离确定为 21", "ADEBC", [n["id"] for n in nodes], ["ADB", "ADEC", "AC", "AB", "AE"], "ADEBC", [], [{"label": "best", "value": 21}, {"label": "答案", "value": "A-D-E-B-C-A"}, {"label": "状态", "value": "完成"}]),
    ]
    steps = _branch_bound_steps("旅行商分支限界", "最小化路程: 用下界剪掉不可能更短的路线", nodes, edges, states, minimize=True)
    return _build_simple_concept_algo(
        "旅行商_分支限界",
        source,
        steps,
        ["best", "queue", "phase"],
        "概念动画：旅行商的分支限界不断扩展最有希望的路线, 一旦有完整答案, 大量路线可以直接剪掉。",
    )


def concept_demo_pruning_techniques():
    source = [
        "算法: 回溯中的剪枝技巧",
        "目标: 在搜索树里尽早排除不可能成功的分支",
        "",
        "进入一个分支前先判断:",
        "    是否违反约束?",
        "    是否已经不可能比当前答案更好?",
        "    是否和之前状态重复?",
        "如果命中任一规则:",
        "    直接返回, 不再向下递归",
    ]
    nodes = [
        {"id": "root", "label": "开始", "x": 0.50, "y": 0.08, "bound": "可行", "value": "0"},
        {"id": "A", "label": "选A", "x": 0.24, "y": 0.30, "bound": "可行", "value": "1"},
        {"id": "B", "label": "选B", "x": 0.50, "y": 0.30, "bound": "冲突", "value": "1"},
        {"id": "C", "label": "选C", "x": 0.76, "y": 0.30, "bound": "可行", "value": "1"},
        {"id": "AA", "label": "A+A", "x": 0.14, "y": 0.54, "bound": "重复", "value": "2"},
        {"id": "AB", "label": "A+B", "x": 0.32, "y": 0.54, "bound": "可行", "value": "2"},
        {"id": "CA", "label": "C+A", "x": 0.66, "y": 0.54, "bound": "差", "value": "2"},
        {"id": "CB", "label": "C+B", "x": 0.84, "y": 0.54, "bound": "可行", "value": "2"},
        {"id": "ABD", "label": "A+B+D", "x": 0.32, "y": 0.78, "bound": "解", "value": "3"},
        {"id": "CBE", "label": "C+B+E", "x": 0.84, "y": 0.78, "bound": "解", "value": "3"},
    ]
    edges = [
        ["root", "A"], ["root", "B"], ["root", "C"], ["A", "AA"], ["A", "AB"],
        ["C", "CA"], ["C", "CB"], ["AB", "ABD"], ["CB", "CBE"],
    ]
    states = [
        (4, "从根节点开始, 每个选择都可能继续展开", "root", ["root"], [], "", ["root"], [{"label": "已看节点", "value": 1}, {"label": "剪枝", "value": 0}, {"label": "答案", "value": 0}]),
        (5, "先看第一层: B 立即违反约束, 不进入它的子树", "B", ["root", "A", "B", "C"], ["B"], "", ["A", "C"], [{"label": "规则", "value": "约束剪枝"}, {"label": "剪掉", "value": "B子树"}, {"label": "队列", "value": 2}]),
        (6, "展开 A: A+A 是重复状态, 继续走只会做无用功", "AA", ["root", "A", "B", "C", "AA", "AB"], ["B", "AA"], "", ["AB", "C"], [{"label": "规则", "value": "重复剪枝"}, {"label": "剪枝", "value": 2}, {"label": "保留", "value": "A+B"}]),
        (8, "A+B 仍然可行, 深入得到一个完整答案", "ABD", ["root", "A", "B", "C", "AA", "AB", "ABD"], ["B", "AA"], "ABD", ["C"], [{"label": "答案", "value": "A+B+D"}, {"label": "best", "value": 3}, {"label": "剪枝", "value": 2}]),
        (6, "再看 C 分支: C+A 即使走到底也不可能更好, 提前剪掉", "CA", ["root", "A", "B", "C", "AA", "AB", "ABD", "CA", "CB"], ["B", "AA", "CA"], "ABD", ["CB"], [{"label": "规则", "value": "上界剪枝"}, {"label": "best", "value": 3}, {"label": "CA潜力", "value": 2}]),
        (8, "C+B 还可能形成另一个答案, 所以保留并继续", "CB", ["root", "A", "B", "C", "AA", "AB", "ABD", "CA", "CB"], ["B", "AA", "CA"], "ABD", ["CB"], [{"label": "状态", "value": "可行"}, {"label": "剪枝", "value": 3}, {"label": "继续", "value": "是"}]),
        (8, "C+B+E 也得到一个答案, 但没有超过当前最好", "CBE", [n["id"] for n in nodes], ["B", "AA", "CA"], "ABD", [], [{"label": "新答案", "value": "C+B+E"}, {"label": "best", "value": "A+B+D"}, {"label": "队列", "value": 0}]),
        (9, "剪枝的意义: 少走无效分支, 把注意力留给可能成功的路径", "ABD", [n["id"] for n in nodes], ["B", "AA", "CA"], "ABD", [], [{"label": "总节点", "value": 10}, {"label": "已剪", "value": 3}, {"label": "状态", "value": "完成"}]),
    ]
    steps = _branch_bound_steps("回溯剪枝技巧", "进入递归前先判断: 冲突、重复、潜力不足都可以直接停", nodes, edges, states)
    for step in steps:
        step["vars"]["concept"]["pruneMode"] = "constraint"
        step["vars"]["concept"]["boundLabel"] = "判断"
        step["vars"]["concept"]["valueLabel"] = "深度"
    return _build_simple_concept_algo(
        "剪枝技巧",
        source,
        steps,
        ["best", "queue", "phase"],
        "概念动画：剪枝不是改变答案, 而是在保证答案不丢的前提下少走无效路。",
    )


def concept_demo_tarjan_scc():
    source = [
        "算法: Tarjan 强连通分量",
        "输入: 有向图",
        "输出: 每个强连通分量",
        "",
        "先理解 DFS 搜索树和回头路",
        "DFS 访问 u:",
        "    dfn[u] = low[u] = 时间戳",
        "    u 入栈",
        "    遍历 u 的邻居 v",
        "        v 未访问: 递归 v, 用 low[v] 更新 low[u]",
        "        v 在栈中: 用 dfn[v] 更新 low[u]",
        "    如果 dfn[u] == low[u]: 弹栈形成一个 SCC",
    ]
    nodes = [
        {"id": "1", "x": 0.14, "y": 0.50},
        {"id": "2", "x": 0.34, "y": 0.26},
        {"id": "3", "x": 0.56, "y": 0.26},
        {"id": "4", "x": 0.74, "y": 0.50},
        {"id": "5", "x": 0.48, "y": 0.72},
    ]
    edges = [["1", "2"], ["2", "3"], ["3", "4"], ["4", "5"], ["5", "2"]]
    states = [
        (5, "从 1 开始 DFS, 1 入栈, dfn/low 都是 1", "1", ["1"], {"1": 1}, {"1": 1}, [], []),
        (8, "沿 1→2 访问 2, 2 是后面大环的入口", "2", ["1", "2"], {"1": 1, "2": 2}, {"1": 1, "2": 2}, [["1", "2"]], []),
        (8, "继续访问 3、4、5, 栈里压入 1→2→3→4→5", "5", ["1", "2", "3", "4", "5"], {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5}, {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5}, [["2", "3"], ["3", "4"], ["4", "5"]], []),
        (10, "5 发现一条回头路指向还在栈中的 2, low[5] 更新为 dfn[2]=2", "5", ["1", "2", "3", "4", "5"], {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5}, {"1": 1, "2": 2, "3": 3, "4": 4, "5": 2}, [["5", "2"]], []),
        (9, "low 值沿 DFS 搜索树回传给 4、3、2, 说明 2 到 5 都能绕回 2", "2", ["1", "2", "3", "4", "5"], {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5}, {"1": 1, "2": 2, "3": 2, "4": 2, "5": 2}, [["5", "2"]], []),
        (11, "dfn[2] == low[2], 弹出 5、4、3、2, 得到 SCC {2,3,4,5}", "2", ["1"], {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5}, {"1": 1, "2": 2, "3": 2, "4": 2, "5": 2}, [], [["2", "3", "4", "5"]]),
        (11, "回到 1, 1 没法回到更早节点, 自己形成单点 SCC {1}", "1", [], {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5}, {"1": 1, "2": 2, "3": 2, "4": 2, "5": 2}, [], [["2", "3", "4", "5"], ["1"]]),
    ]
    steps = []
    for idx, (line, phase, current, stack, dfn, low, active_edges, sccs) in enumerate(states):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "u": current,
                "stack": " → ".join(stack) if stack else "空",
                "scc_count": len(sccs),
                "phase": phase,
                "concept": {
                    "kind": "tarjan_scc",
                    "title": "Tarjan 强连通分量",
                    "subtitle": "dfn 是访问顺序, low 是沿 DFS 搜索树和回头路能绕回的最早节点",
                    "nodes": nodes,
                    "edges": edges,
                    "current": current,
                    "stack": stack,
                    "dfn": dfn,
                    "low": low,
                    "activeEdges": active_edges,
                    "sccs": sccs,
                },
            },
        })
    return _build_simple_concept_algo(
        "Tarjan强连通分量",
        source,
        steps,
        ["u", "stack", "scc_count", "phase"],
        "概念动画：Tarjan 用 dfn/low 和一个栈, 一次 DFS 就能把环状关系摘出来。",
    )


def concept_demo_hungarian_matching():
    source = [
        "算法: 匈牙利算法",
        "输入: 二分图",
        "输出: 最大匹配",
        "",
        "对每个左侧节点 u:",
        "    清空 used",
        "    DFS 尝试找一个右侧节点 v",
        "    如果 v 空着: 直接匹配",
        "    如果 v 已匹配: 让原匹配对象尝试换人",
        "    换人成功后, u 接管 v",
    ]
    # 学生A-课程1，学生B-课程2/3，学生C-课程2。
    # C 来了以后，B 让到课程3，整体从2组变成3组。
    edges = [[0, 0], [1, 1], [1, 2], [2, 1]]
    states = [
        (5, "学生A只喜欢课程1, 课程1空着, 直接安排", 1, 1, [0, -1, -1], [1], 1),
        (7, "学生B先拿到课程2, 当前已经安排2组", 2, 2, [0, 1, -1], [2], 2),
        (6, "学生C也想选课程2, 但课程2已经被学生B占用", 3, 2, [0, 1, -1], [2], 2),
        (8, "递归询问学生B: 你能不能让到课程3?", 2, 3, [0, 1, -1], [2, 3], 2),
        (8, "学生B改选课程3, 课程2腾出来给学生C", 3, 2, [0, 2, 1], [2, 3], 3),
        (9, "三名学生都安排成功, 最大匹配数是3", 3, 2, [0, 2, 1], [], 3),
    ]
    steps = []
    for idx, (line, phase, u, v, match, tried, count) in enumerate(states):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "u": u,
                "v": v,
                "count": count,
                "phase": phase,
                "concept": {
                    "kind": "hungarian_matching",
                    "title": "匈牙利算法",
                    "subtitle": "课程被占用时, 尝试让原来的学生换到别处",
                    "left": 3,
                    "right": 3,
                    "edges": edges,
                    "match": match,
                    "active": [u - 1, v - 1],
                    "used": [x - 1 for x in tried],
                    "count": count,
                },
            },
        })
    return _build_simple_concept_algo(
        "匈牙利算法_二分匹配",
        source,
        steps,
        ["u", "v", "count", "phase"],
        "概念动画：匈牙利算法的精髓是“让一让”, 通过重新匹配腾出位置。",
    )


def concept_demo_edmonds_karp():
    source = [
        "算法: Edmonds-Karp 最大流",
        "输入: 源点 s, 汇点 t, 每条边的容量 capacity",
        "输出: 从 s 到 t 的最大流量",
        "",
        "while 能在残量网络中 BFS 找到一条 s 到 t 的路:",
        "    bottleneck = 这条路上最小剩余容量",
        "    沿着路径增加 bottleneck 的流量",
        "    同时更新反向边",
        "当 BFS 找不到增广路时, 当前流量就是最大流",
        "在最终残余图中从 s 出发做 BFS",
        "能到达的点属于 S, 其余点属于 T",
        "回到原图, S 指向 T 的边就是最小割",
    ]
    positions = {
        "S": [0.12, 0.50],
        "A": [0.38, 0.28],
        "B": [0.38, 0.72],
        "C": [0.66, 0.50],
        "T": [0.90, 0.50],
    }
    capacities = {
        ("S", "A"): 3,
        ("S", "B"): 5,
        ("A", "C"): 2,
        ("B", "C"): 4,
        ("B", "T"): 3,
        ("C", "T"): 6,
    }
    states = [
        (5, "初始所有边 flow=0, BFS 从源点 S 开始找通往 T 的路", {}, ["S"], [], 0, 0, [], 0),
        (5, "第一轮 BFS 找到 S-B-T, 因为它只有2条边", {}, ["S", "B", "T"], [["S", "B"], ["B", "T"]], 0, 3, [], 0),
        (7, "S-B-T 的瓶颈是 3, 先送水3, 累计最大流变成3", {("S", "B"): 3, ("B", "T"): 3}, ["S", "B", "T"], [["S", "B"], ["B", "T"]], 3, 3, [], 0),
        (5, "第二轮 BFS 找到 S-A-C-T, 继续把水送到 T", {("S", "B"): 3, ("B", "T"): 3}, ["S", "A", "C", "T"], [["S", "A"], ["A", "C"], ["C", "T"]], 3, 2, [], 0),
        (7, "S-A-C-T 的瓶颈是 2, 累计最大流变成5", {("S", "B"): 3, ("B", "T"): 3, ("S", "A"): 2, ("A", "C"): 2, ("C", "T"): 2}, ["S", "A", "C", "T"], [["S", "A"], ["A", "C"], ["C", "T"]], 5, 2, [], 0),
        (5, "第三轮 BFS 找到 S-B-C-T, 利用 B 到 C 和 C 到 T 的余量", {("S", "B"): 3, ("B", "T"): 3, ("S", "A"): 2, ("A", "C"): 2, ("C", "T"): 2}, ["S", "B", "C", "T"], [["S", "B"], ["B", "C"], ["C", "T"]], 5, 2, [], 0),
        (7, "再送水2后, 从 S 出发已经没有通向 T 的增广路", {("S", "A"): 2, ("A", "C"): 2, ("C", "T"): 4, ("S", "B"): 5, ("B", "T"): 3, ("B", "C"): 2}, ["S", "B", "C", "T"], [["S", "B"], ["B", "C"], ["C", "T"]], 7, 2, [], 0),
        (10, "最终残余图里 S 只能到达 A, 所以割边是 S-B 和 A-C, 最小割容量也是7", {("S", "A"): 2, ("A", "C"): 2, ("C", "T"): 4, ("S", "B"): 5, ("B", "T"): 3, ("B", "C"): 2}, ["S", "A"], [], 7, 0, [["S", "B"], ["A", "C"]], 7),
    ]
    steps = []
    for idx, (line, phase, flows, visited, active_path, total, bottleneck, cut_edges, min_cut) in enumerate(states):
        edges = []
        for (src, dst), cap in capacities.items():
            flow = flows.get((src, dst), 0)
            edges.append({
                "from": src,
                "to": dst,
                "capacity": cap,
                "flow": flow,
                "remaining": max(0, cap - flow),
            })
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "maxFlow": total,
                "bottleneck": bottleneck,
                "phase": phase,
                "concept": {
                    "kind": "max_flow",
                    "title": "Edmonds-Karp 最大流",
                    "nodes": [{"id": node, "x": xy[0], "y": xy[1]} for node, xy in positions.items()],
                    "edges": edges,
                    "visited": visited,
                    "activePath": active_path,
                    "cutEdges": cut_edges,
                    "maxFlow": total,
                    "bottleneck": bottleneck,
                    "minCut": min_cut,
                },
            },
        })
    return _build_simple_concept_algo(
        "EdmondsKarp最大流",
        source,
        steps,
        ["maxFlow", "bottleneck", "minCut", "phase"],
        "概念动画：最大流先找承载上限, 最后还能从残余图读出最小割瓶颈。",
    )


def _kmp_table_steps(title, table_name, values, optimized=False):
    pattern = "ABABCABAB"
    states = [
        (5, 0, -1, 0, "next[0] = -1 是哨兵, 表示已经退无可退"),
        (8, 1, 0, 2, "A 和 B 不同, 最长相同前后缀长度是 0"),
        (10, 3, 1, 4, "ABAB 的前缀 A 和后缀 A 对上了"),
        (10, 4, 2, 5, "ABAB 的前缀 AB 和后缀 AB 对上了"),
        (12, 5, 0 if not optimized else -1, 6, "遇到 C 后, 前后缀关系断开, 准备回退"),
        (10, 8, 3 if not optimized else 0, 9, "表建完后, 匹配失配时可以直接跳到表指示的位置"),
    ]
    if optimized:
        states = [
            (5, 0, -1, 0, "nextval[0] = -1, 仍然保留哨兵"),
            (10, 2, -1, 3, "如果回退后还是同一个字符, 就继续跳过"),
            (10, 4, 2, 5, "字符不同的位置保留正常回退值"),
            (12, 5, -1, 6, "C 失配时直接退到哨兵, 少做一次重复比较"),
            (10, 7, -1, 8, "相同字符导致的重复失配被压缩掉"),
            (10, 8, 0, 9, "nextval 是 next 的再剪枝版本"),
        ]
    steps = []
    for idx, (line, active, value, built, phase) in enumerate(states):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "i": active,
                "j": value,
                "phase": phase,
                "concept": {
                    "kind": "kmp_table",
                    "title": title,
                    "pattern": pattern,
                    "tableName": table_name,
                    "values": values,
                    "active": active,
                    "built": built,
                    "optimized": optimized,
                },
            },
        })
    return steps


def _build_string_match_concept(title, source, states, output):
    steps = []
    for idx, state in enumerate(states):
        concept = {
            "kind": "string_match_concept",
            "title": title,
            "text": state["text"],
            "pattern": state["pattern"],
            "offset": state.get("offset", 0),
            "j": state.get("j", 0),
            "mode": state.get("mode", "bf"),
            "mismatch": state.get("mismatch", False),
            "success": state.get("success", False),
            "windowOnly": state.get("windowOnly", False),
            "hashText": state.get("hashText"),
            "hashPattern": state.get("hashPattern"),
            "jumpTo": state.get("jumpTo"),
            "caption": state.get("phase", ""),
        }
        steps.append({
            "step": idx,
            "line": state.get("line", 1),
            "type": "exec",
            "vars": {
                "offset": state.get("offset", 0),
                "j": state.get("j", "-"),
                "phase": state.get("phase", ""),
                "concept": concept,
            },
        })
    return _build_simple_concept_algo(title, source, steps, ["offset", "j", "phase"], output)


def concept_demo_bf_match():
    text = "ABABDABACDABABCABAB"
    pattern = "ABABCABAB"
    source = [
        "算法: BF 暴力匹配",
        "输入: text, pattern",
        "输出: pattern 在 text 中的起始位置",
        "",
        "for offset = 0..n-m:",
        "    从 pattern[0] 开始逐个字符比较",
        "    如果遇到失配, 换下一个 offset 从头再试",
        "    如果 pattern 全部对上, 匹配成功",
    ]
    states = [
        {"line": 5, "mode": "bf", "text": text, "pattern": pattern, "offset": 0, "j": 0, "phase": "先把模式串放在主串开头, 从第一格开始比较"},
        {"line": 6, "mode": "bf", "text": text, "pattern": pattern, "offset": 0, "j": 4, "mismatch": True, "phase": "前4个字符相同, 第5个字符 C 对 D 失配"},
        {"line": 7, "mode": "bf", "text": text, "pattern": pattern, "offset": 1, "j": 0, "mismatch": True, "phase": "BF 不记历史, 整个模式串右移一格, 又从头比较"},
        {"line": 7, "mode": "bf", "text": text, "pattern": pattern, "offset": 5, "j": 3, "mismatch": True, "phase": "中间会反复出现“对几格又失败”的情况, 所以 BF 会做很多重复比较"},
        {"line": 8, "mode": "bf", "text": text, "pattern": pattern, "offset": 10, "j": 8, "success": True, "phase": "移动到 offset=10 时, 9 个字符全部对上, 匹配成功"},
    ]
    return _build_string_match_concept(
        "暴力匹配_BF",
        source,
        states,
        "概念动画：BF 很直观, 但每次失败都从头再来, 重复比较很多。",
    )


def concept_demo_kmp_next():
    source = [
        "算法: 构建 KMP next 数组",
        "输入: 模式串 pattern",
        "输出: next 数组",
        "",
        "next[0] = -1",
        "i = 0, j = -1",
        "当 i < m - 1:",
        "    如果 j == -1 或 pattern[i] == pattern[j]:",
        "        i++, j++",
        "        next[i] = j",
        "    否则:",
        "        j = next[j]",
    ]
    steps = _kmp_table_steps("KMP next数组", "next", [-1, 0, 0, 1, 2, 0, 1, 2, 3])
    return _build_simple_concept_algo(
        "KMP_next数组",
        source,
        steps,
        ["i", "j", "phase"],
        "概念动画：next 数组记录失配后模式串应该回退到哪里。",
    )


def concept_demo_kmp_match():
    text = "ABABDABACDABABCABAB"
    pattern = "ABABCABAB"
    source = [
        "算法: KMP 匹配过程",
        "输入: text, pattern, next",
        "输出: pattern 在 text 中的起始位置",
        "",
        "i 指向 text, j 指向 pattern",
        "如果 text[i] == pattern[j]: i++, j++",
        "否则: j = next[j]",
        "注意: text 指针 i 不回退",
    ]
    states = [
        {"line": 5, "mode": "kmp", "text": text, "pattern": pattern, "offset": 0, "j": 0, "phase": "KMP 也从左往右比较, 但会记住已经对上的前缀"},
        {"line": 6, "mode": "kmp", "text": text, "pattern": pattern, "offset": 0, "j": 4, "mismatch": True, "phase": "ABAB 已经对上, 第5格失配时, 这段历史不能浪费"},
        {"line": 7, "mode": "kmp", "text": text, "pattern": pattern, "offset": 2, "j": 2, "jumpTo": 2, "phase": "next[4]=2, 模式串滑到能复用 AB 的位置, 主串指针不回头"},
        {"line": 7, "mode": "kmp", "text": text, "pattern": pattern, "offset": 5, "j": 0, "mismatch": True, "phase": "如果当前前缀也接不上, j 继续按 next 回退, 仍然不用重扫主串"},
        {"line": 6, "mode": "kmp", "text": text, "pattern": pattern, "offset": 10, "j": 5, "phase": "来到 offset=10 后, 匹配一路向前推进"},
        {"line": 8, "mode": "kmp", "text": text, "pattern": pattern, "offset": 10, "j": 8, "success": True, "phase": "模式串全部对上, 返回起始位置 10"},
    ]
    return _build_string_match_concept(
        "KMP_匹配过程",
        source,
        states,
        "概念动画：KMP 的核心是文本指针不回退, 失配时只移动模式串。",
    )


def concept_demo_kmp_nextval():
    source = [
        "算法: 构建 KMP nextval 数组",
        "输入: 模式串 pattern",
        "输出: nextval 数组",
        "",
        "先像 next 一样寻找回退位置",
        "如果 pattern[i] != pattern[j]:",
        "    nextval[i] = j",
        "否则:",
        "    nextval[i] = nextval[j]",
        "",
        "核心: 避免退到一个必然再次失配的位置",
    ]
    steps = _kmp_table_steps("KMP nextval优化", "nextval", [-1, 0, -1, 0, 2, -1, 0, -1, 0], True)
    return _build_simple_concept_algo(
        "KMP_nextval优化",
        source,
        steps,
        ["i", "j", "phase"],
        "概念动画：nextval 在 next 基础上跳过重复字符导致的无意义失配。",
    )


def concept_demo_rabin_karp():
    text = "ABABDABACDABABCABAB"
    pattern = "ABABCABAB"
    source = [
        "算法: Rabin-Karp 哈希匹配",
        "输入: text, pattern",
        "输出: 所有匹配位置",
        "",
        "先计算 pattern 的哈希",
        "再计算 text 当前窗口的哈希",
        "如果哈希不同, 直接滑动窗口",
        "如果哈希相同, 再逐字符确认",
        "窗口右移时用滚动哈希快速更新",
    ]
    states = [
        {"line": 4, "mode": "rk", "text": text, "pattern": pattern, "offset": 0, "j": 0, "windowOnly": True, "hashPattern": 731, "hashText": 512, "phase": "把模式串和同长度窗口都压成一个数字指纹"},
        {"line": 7, "mode": "rk", "text": text, "pattern": pattern, "offset": 0, "j": 0, "windowOnly": True, "hashPattern": 731, "hashText": 512, "phase": "哈希不同, 这一整段窗口不用逐字比较, 直接跳过"},
        {"line": 9, "mode": "rk", "text": text, "pattern": pattern, "offset": 1, "j": 0, "windowOnly": True, "hashPattern": 731, "hashText": 438, "phase": "窗口右移时, 减掉左边旧字符, 加上右边新字符"},
        {"line": 7, "mode": "rk", "text": text, "pattern": pattern, "offset": 5, "j": 0, "windowOnly": True, "hashPattern": 731, "hashText": 609, "phase": "大多数窗口只看哈希就能排除, 像先用机器快筛"},
        {"line": 8, "mode": "rk", "text": text, "pattern": pattern, "offset": 10, "j": 0, "hashPattern": 731, "hashText": 731, "phase": "哈希相同, 这时才值得逐字符确认, 防止哈希冲突"},
        {"line": 8, "mode": "rk", "text": text, "pattern": pattern, "offset": 10, "j": 8, "success": True, "hashPattern": 731, "hashText": 731, "phase": "逐字符确认也全部相同, 匹配位置是 10"},
    ]
    return _build_string_match_concept(
        "RabinKarp_哈希匹配",
        source,
        states,
        "概念动画：Rabin-Karp 先用哈希快速筛掉大多数窗口, 命中哈希后再认真核对。",
    )


def concept_demo_trie():
    source = [
        "算法: Trie 字典树",
        "输入: 单词集合 words",
        "输出: 支持查找和前缀判断的树",
        "",
        "从根节点开始",
        "插入单词时, 每个字符走一条边",
        "没有边就新建节点",
        "单词结束处打上 end 标记",
        "",
        "查找时沿字符路径走, 路断则失败",
    ]
    nodes = [
        ["root", "", 0.50, 0.12],
        ["a", "a", 0.33, 0.30], ["ap", "p", 0.28, 0.48], ["app", "p*", 0.21, 0.66],
        ["appl", "l", 0.31, 0.66], ["apple", "e*", 0.31, 0.84], ["ape", "e*", 0.40, 0.66],
        ["b", "b", 0.67, 0.30], ["ba", "a", 0.67, 0.48], ["bat", "t*", 0.67, 0.66],
    ]
    edges = [["root", "a"], ["a", "ap"], ["ap", "app"], ["app", "appl"], ["appl", "apple"], ["ap", "ape"], ["root", "b"], ["b", "ba"], ["ba", "bat"]]
    states = [
        (5, "从根节点出发, 准备插入 app", ["root"], [], "app"),
        (7, "插入 app: a → p → p, 最后一个 p 标记为单词结束", ["root", "a", "ap", "app"], [["root", "a"], ["a", "ap"], ["ap", "app"]], "app"),
        (7, "继续插入 apple, 复用 app 的前缀路径", ["root", "a", "ap", "app", "appl", "apple"], [["app", "appl"], ["appl", "apple"]], "apple"),
        (7, "插入 ape, 在 ap 后分出另一条 e 分支", ["root", "a", "ap", "app", "appl", "apple", "ape"], [["ap", "ape"]], "ape"),
        (7, "插入 bat, 从根节点走另一条 b 分支", [n[0] for n in nodes], [["root", "b"], ["b", "ba"], ["ba", "bat"]], "bat"),
        (9, "查找 apex: a、p、e 能走到, 但后面没有 x, 路断失败", [n[0] for n in nodes], [["root", "a"], ["a", "ap"], ["ap", "ape"]], "apex"),
        (9, "前缀 ap 存在: 只要路径不断, 不要求 end 标记", [n[0] for n in nodes], [["root", "a"], ["a", "ap"]], "ap"),
    ]
    steps = []
    for idx, (line, phase, visible, active_edges, word) in enumerate(states):
        visible_set = set(visible)
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "word": word,
                "phase": phase,
                "concept": {
                    "kind": "trie",
                    "title": "Trie 字典树",
                    "nodes": [{"id": nid, "label": label, "x": x, "y": y, "end": label.endswith("*")} for nid, label, x, y in nodes if nid in visible_set],
                    "edges": [e for e in edges if e[0] in visible_set and e[1] in visible_set],
                    "activeEdges": active_edges,
                    "word": word,
                },
            },
        })
    return _build_simple_concept_algo(
        "Trie字典树",
        source,
        steps,
        ["word", "phase"],
        "概念动画：Trie 把相同前缀合并到同一条路径上。",
    )


def concept_demo_ac_automaton():
    source = [
        "算法: AC 自动机",
        "输入: 多个关键词 patterns, 文本 text",
        "输出: 所有关键词匹配次数",
        "",
        "1. 先把关键词插入 Trie",
        "2. BFS 构建 fail 指针",
        "3. 扫描文本, 能走子边就前进",
        "4. 不能走时沿 fail 指针回退",
        "5. 每到一个节点, 累加该节点和 fail 链上的匹配",
    ]
    nodes = [
        ["root", "", 0.50, 0.12],
        ["a", "a", 0.28, 0.30], ["ab", "b", 0.28, 0.48], ["abc", "c*", 0.28, 0.66],
        ["b", "b", 0.50, 0.30], ["bc", "c", 0.50, 0.48], ["bcd", "d*", 0.50, 0.66],
        ["c", "c", 0.72, 0.30], ["cd", "d", 0.72, 0.48], ["cde", "e*", 0.72, 0.66],
    ]
    edges = [["root", "a"], ["a", "ab"], ["ab", "abc"], ["root", "b"], ["b", "bc"], ["bc", "bcd"], ["root", "c"], ["c", "cd"], ["cd", "cde"]]
    fails = [["ab", "b"], ["abc", "bc"], ["bc", "c"], ["bcd", "cd"], ["cd", "root"], ["cde", "root"]]
    states = [
        (5, "把 abc、bcd、cde 插入同一棵 Trie", [], [], "构建Trie", 0),
        (6, "第一层 a、b、c 的 fail 都指向 root", [["a", "root"], ["b", "root"], ["c", "root"]], [], "BFS建fail", 0),
        (6, "abc 的 fail 指向 bc: 后缀 bc 仍然是另一个关键词的前缀", [["ab", "b"], ["abc", "bc"]], [], "BFS建fail", 0),
        (8, "扫描 xabcdex: x 没有边, 留在 root", [], [], "x", 0),
        (8, "读到 a、b、c, 到达 abc, 命中 abc", [], ["a", "ab", "abc"], "xabc", 1),
        (9, "继续读 d: abc 没有 d 边, 沿 fail 回到 bc, 再走 d 命中 bcd", [["abc", "bc"]], ["bc", "bcd"], "xabcd", 2),
        (9, "继续读 e: bcd 没有 e 边, 沿 fail 回到 cd, 再走 e 命中 cde", [["bcd", "cd"]], ["cd", "cde"], "xabcde", 3),
        (8, "最后 x 没有可走边, 全文扫描完成, 文本指针从未回退", [], [], "xabcdex", 3),
    ]
    all_ids = [n[0] for n in nodes]
    steps = []
    for idx, (line, phase, active_fails, active_path, text, total) in enumerate(states):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "text": text,
                "total": total,
                "phase": phase,
                "concept": {
                    "kind": "ac_automaton",
                    "title": "AC 自动机",
                    "nodes": [{"id": nid, "label": label, "x": x, "y": y, "end": label.endswith("*")} for nid, label, x, y in nodes if nid in all_ids],
                    "edges": edges,
                    "failEdges": fails,
                    "activeFails": active_fails,
                    "activePath": active_path,
                    "text": text,
                    "total": total,
                },
            },
        })
    return _build_simple_concept_algo(
        "AC自动机",
        source,
        steps,
        ["text", "total", "phase"],
        "概念动画：AC 自动机 = Trie + fail 指针, 一次扫描找出多个关键词。",
    )


def _build_advanced_ds_demo(title, source, rows, output, primary_vars=None):
    steps = []
    for idx, row in enumerate(rows):
        concept = dict(row["concept"])
        concept.setdefault("title", title)
        concept.setdefault("caption", row.get("phase", ""))
        steps.append({
            "step": idx,
            "line": row.get("line", 1),
            "type": "exec",
            "vars": {
                "focus": row.get("focus", "-"),
                "result": row.get("result", "-"),
                "phase": row.get("phase", ""),
                "concept": concept,
            },
        })
    return _build_simple_concept_algo(title, source, steps, primary_vars or ["focus", "result", "phase"], output)


def _uf_nodes(parents):
    positions = {
        "1": (0.18, 0.30), "2": (0.34, 0.30), "3": (0.50, 0.30),
        "4": (0.66, 0.30), "5": (0.82, 0.30), "6": (0.50, 0.66),
    }
    return [
        {"id": str(i), "parent": str(parents.get(i, i)), "x": positions[str(i)][0], "y": positions[str(i)][1]}
        for i in range(1, 7)
    ]


def _uf_source(title):
    return [
        f"算法: {title}",
        "输入: 若干元素和合并关系",
        "输出: 两个元素是否属于同一集合",
        "",
        "find(x): 找到 x 的代表",
        "union(x, y): 合并两个集合",
        "same(x, y): 代表相同就是一伙的",
    ]


def concept_demo_union_find_basic():
    rows = [
        {"line": 4, "phase": "一开始每个人都是自己的老大", "focus": "init", "result": "6个集合", "concept": {"kind": "union_find", "nodes": _uf_nodes({}), "active": ["1", "2", "3", "4", "5", "6"]}},
        {"line": 6, "phase": "合并 1 和 2: 1 的代表挂到 2 下面", "focus": "union(1,2)", "result": "1->2", "concept": {"kind": "union_find", "nodes": _uf_nodes({1: 2}), "active": ["1", "2"], "union": ["1", "2"]}},
        {"line": 6, "phase": "合并 2 和 3 后, 1 要沿着链条找到代表 3", "focus": "union(2,3)", "result": "1->2->3", "concept": {"kind": "union_find", "nodes": _uf_nodes({1: 2, 2: 3}), "active": ["1", "2", "3"], "path": ["1", "2", "3"]}},
        {"line": 7, "phase": "4 和 5 是另一伙, 两棵树暂时互不相干", "focus": "union(4,5)", "result": "两组", "concept": {"kind": "union_find", "nodes": _uf_nodes({1: 2, 2: 3, 4: 5}), "active": ["4", "5"]}},
        {"line": 7, "phase": "合并 3 和 4 后, 两个朋友圈连成一个大集合", "focus": "union(3,4)", "result": "1和5同组", "concept": {"kind": "union_find", "nodes": _uf_nodes({1: 2, 2: 3, 3: 5, 4: 5}), "active": ["1", "5"], "path": ["1", "2", "3", "5"]}},
    ]
    return _build_advanced_ds_demo("并查集_朴素版", _uf_source("并查集朴素版"), rows, "概念动画：并查集只关心“最终代表是谁”, 不需要知道集合里的全部成员。")


def concept_demo_union_find_compress():
    rows = [
        {"line": 4, "phase": "故意构造一条长链: 5 找老大要一路问到 1", "focus": "find(5)", "result": "5->4->3->2->1", "concept": {"kind": "union_find", "nodes": _uf_nodes({2: 1, 3: 2, 4: 3, 5: 4}), "active": ["5"], "path": ["5", "4", "3", "2", "1"]}},
        {"line": 5, "phase": "递归返回时, 沿途节点都直接改挂到根 1", "focus": "压缩路径", "result": "直接连根", "concept": {"kind": "union_find", "nodes": _uf_nodes({2: 1, 3: 1, 4: 1, 5: 1}), "active": ["5", "4", "3", "2", "1"], "path": ["5", "1"]}},
        {"line": 6, "phase": "下次再问 5 的老大, 一步就到", "focus": "find(5)", "result": "O(接近1)", "concept": {"kind": "union_find", "nodes": _uf_nodes({2: 1, 3: 1, 4: 1, 5: 1}), "active": ["5", "1"], "path": ["5", "1"]}},
    ]
    return _build_advanced_ds_demo("并查集_路径压缩", _uf_source("路径压缩"), rows, "概念动画：路径压缩像把层层上报改成直拨总部。")


def concept_demo_union_find_rank():
    rows = [
        {"line": 4, "phase": "先形成三棵高度差不多的小树", "focus": "union", "result": "{1,2} {3,4} {5,6}", "concept": {"kind": "union_find", "nodes": _uf_nodes({2: 1, 4: 3, 6: 5}), "active": ["1", "3", "5"]}},
        {"line": 6, "phase": "按秩合并: 矮树挂到高树, 避免长成一条链", "focus": "union(1,3)", "result": "rank+1", "concept": {"kind": "union_find", "nodes": _uf_nodes({2: 1, 3: 1, 4: 3, 6: 5}), "active": ["1", "3"], "union": ["3", "1"]}},
        {"line": 6, "phase": "再合并 {5,6}, 小树继续挂到大树下面", "focus": "union(1,5)", "result": "树仍然很矮", "concept": {"kind": "union_find", "nodes": _uf_nodes({2: 1, 3: 1, 4: 3, 5: 1, 6: 5}), "active": ["1", "5"], "union": ["5", "1"]}},
    ]
    return _build_advanced_ds_demo("并查集_按秩合并", _uf_source("按秩合并"), rows, "概念动画：按秩合并从一开始就防止树长歪。")


def concept_demo_union_find_social():
    rows = [
        {"line": 5, "phase": "1 和 2 成为朋友, 两人归到同一个朋友圈", "focus": "1-2", "result": "同组", "concept": {"kind": "union_find", "nodes": _uf_nodes({1: 2}), "active": ["1", "2"], "union": ["1", "2"]}},
        {"line": 5, "phase": "2 和 3 成为朋友后, 1 也通过朋友关系连到 3", "focus": "2-3", "result": "1和3同组", "concept": {"kind": "union_find", "nodes": _uf_nodes({1: 2, 3: 2}), "active": ["1", "2", "3"], "path": ["1", "2", "3"]}},
        {"line": 6, "phase": "4 没参与任何关系, 所以 1 和 4 不是一伙", "focus": "same(1,4)", "result": "No", "concept": {"kind": "union_find", "nodes": _uf_nodes({1: 2, 3: 2}), "active": ["1", "4"]}},
    ]
    return _build_advanced_ds_demo("并查集_社交圈示例", _uf_source("社交圈并查集"), rows, "概念动画：朋友的朋友也会被并查集合并到同一个圈子里。")


def _rb_source():
    return [
        "算法: 红黑树理解动画",
        "规则1: 根节点是黑色",
        "规则2: NIL空节点是黑色",
        "规则3: 红节点不能连着红节点",
        "规则4: 每条路径黑色节点数相同",
        "插入: 新节点先染红",
        "修复: 通过染色和旋转恢复平衡",
    ]


def _rb_nodes(kind):
    states = {
        "bst_bad": [
            {"id": "1", "label": "1", "color": "black", "x": 0.18, "y": 0.18},
            {"id": "2", "label": "2", "color": "black", "x": 0.32, "y": 0.34},
            {"id": "3", "label": "3", "color": "black", "x": 0.46, "y": 0.50},
            {"id": "4", "label": "4", "color": "black", "x": 0.60, "y": 0.66},
            {"id": "5", "label": "5", "color": "black", "x": 0.74, "y": 0.82},
        ],
        "balanced": [
            {"id": "4", "label": "4", "color": "black", "x": 0.50, "y": 0.18},
            {"id": "2", "label": "2", "color": "red", "x": 0.30, "y": 0.42},
            {"id": "6", "label": "6", "color": "red", "x": 0.70, "y": 0.42},
            {"id": "1", "label": "1", "color": "black", "x": 0.20, "y": 0.68},
            {"id": "3", "label": "3", "color": "black", "x": 0.40, "y": 0.68},
            {"id": "5", "label": "5", "color": "black", "x": 0.60, "y": 0.68},
            {"id": "7", "label": "7", "color": "black", "x": 0.80, "y": 0.68},
        ],
        "conflict": [
            {"id": "4", "label": "4", "color": "black", "x": 0.50, "y": 0.18},
            {"id": "2", "label": "2", "color": "red", "x": 0.32, "y": 0.42},
            {"id": "6", "label": "6", "color": "black", "x": 0.70, "y": 0.42},
            {"id": "1", "label": "1", "color": "black", "x": 0.22, "y": 0.68},
            {"id": "3", "label": "3", "color": "red", "x": 0.42, "y": 0.68},
            {"id": "0", "label": "0", "color": "red", "x": 0.12, "y": 0.88},
        ],
        "fixed": [
            {"id": "2", "label": "2", "color": "black", "x": 0.50, "y": 0.18},
            {"id": "1", "label": "1", "color": "black", "x": 0.30, "y": 0.46},
            {"id": "4", "label": "4", "color": "red", "x": 0.70, "y": 0.46},
            {"id": "0", "label": "0", "color": "red", "x": 0.20, "y": 0.72},
            {"id": "3", "label": "3", "color": "black", "x": 0.60, "y": 0.72},
            {"id": "6", "label": "6", "color": "black", "x": 0.82, "y": 0.72},
        ],
    }
    return states[kind]


def _rb_edges(kind):
    states = {
        "bst_bad": [["1", "2"], ["2", "3"], ["3", "4"], ["4", "5"]],
        "balanced": [["4", "2"], ["4", "6"], ["2", "1"], ["2", "3"], ["6", "5"], ["6", "7"]],
        "conflict": [["4", "2"], ["4", "6"], ["2", "1"], ["2", "3"], ["1", "0"]],
        "fixed": [["2", "1"], ["2", "4"], ["1", "0"], ["4", "3"], ["4", "6"]],
    }
    return states[kind]


def concept_demo_red_black_tree():
    rows = [
        {
            "line": 1,
            "phase": "普通 BST 如果按顺序插入, 很容易退化成一条链",
            "focus": "BST退化",
            "result": "O(n)",
            "concept": {"kind": "red_black_tree", "nodes": _rb_nodes("bst_bad"), "edges": _rb_edges("bst_bad"), "active": ["5"], "caption": "没有自平衡时, 查找会像链表一样慢。"},
        },
        {
            "line": 2,
            "phase": "红黑树允许一点“不完美”, 但用颜色规则限制歪斜程度",
            "focus": "四条规则",
            "result": "高度受控",
            "concept": {"kind": "red_black_tree", "nodes": _rb_nodes("balanced"), "edges": _rb_edges("balanced"), "active": ["4", "2", "6"], "blackHeight": "每条路黑节点数一致", "caption": "红色可以出现, 但不能红红相连；黑色数量要保持一致。"},
        },
        {
            "line": 3,
            "phase": "新节点通常先染红, 因为这样不会立刻破坏黑色节点数量",
            "focus": "插入红节点",
            "result": "可能红红冲突",
            "concept": {"kind": "red_black_tree", "nodes": _rb_nodes("conflict"), "edges": _rb_edges("conflict"), "active": ["0", "1"], "conflict": ["0", "1"], "caption": "如果父子都是红色, 就违反了“红节点不能连红节点”。"},
        },
        {
            "line": 4,
            "phase": "通过染色和旋转, 把局部冲突修回稳定结构",
            "focus": "旋转+染色",
            "result": "O(log n)",
            "concept": {"kind": "red_black_tree", "nodes": _rb_nodes("fixed"), "edges": _rb_edges("fixed"), "active": ["2", "4"], "caption": "红黑树追求的是工程上的稳定平衡, 不是绝对完美。"},
        },
    ]
    return _build_advanced_ds_demo("红黑树_理解动画", _rb_source(), rows, "概念动画：红黑树用“颜色规则 + 旋转”避免 BST 退化成链。")


def _segment_nodes(values=None):
    vals = values or {
        "1": 31, "2": 9, "3": 22,
        "4": 4, "5": 5, "6": 14, "7": 8,
        "8": 3, "9": 1, "10": 4, "11": 1,
        "12": 5, "13": 9, "14": 2, "15": 6,
    }
    return [
        {"id": "1", "label": "[1,8]", "value": vals.get("1", 31), "x": 0.50, "y": 0.08},
        {"id": "2", "label": "[1,4]", "value": vals.get("2", 9), "x": 0.28, "y": 0.28},
        {"id": "3", "label": "[5,8]", "value": vals.get("3", 22), "x": 0.72, "y": 0.28},
        {"id": "4", "label": "[1,2]", "value": vals.get("4", 4), "x": 0.16, "y": 0.48},
        {"id": "5", "label": "[3,4]", "value": vals.get("5", 5), "x": 0.40, "y": 0.48},
        {"id": "6", "label": "[5,6]", "value": vals.get("6", 14), "x": 0.60, "y": 0.48},
        {"id": "7", "label": "[7,8]", "value": vals.get("7", 8), "x": 0.84, "y": 0.48},
        {"id": "8", "label": "[1,1]", "value": vals.get("8", 3), "x": 0.07, "y": 0.72},
        {"id": "9", "label": "[2,2]", "value": vals.get("9", 1), "x": 0.20, "y": 0.72},
        {"id": "10", "label": "[3,3]", "value": vals.get("10", 4), "x": 0.33, "y": 0.72},
        {"id": "11", "label": "[4,4]", "value": vals.get("11", 1), "x": 0.46, "y": 0.72},
        {"id": "12", "label": "[5,5]", "value": vals.get("12", 5), "x": 0.54, "y": 0.72},
        {"id": "13", "label": "[6,6]", "value": vals.get("13", 9), "x": 0.67, "y": 0.72},
        {"id": "14", "label": "[7,7]", "value": vals.get("14", 2), "x": 0.80, "y": 0.72},
        {"id": "15", "label": "[8,8]", "value": vals.get("15", 6), "x": 0.93, "y": 0.72},
    ]


def _segment_edges():
    return [
        ["1", "2"], ["1", "3"], ["2", "4"], ["2", "5"], ["3", "6"], ["3", "7"],
        ["4", "8"], ["4", "9"], ["5", "10"], ["5", "11"],
        ["6", "12"], ["6", "13"], ["7", "14"], ["7", "15"],
    ]


def _segment_source(title):
    return [
        f"算法: {title}",
        "每个节点管理一个区间 [l, r]",
        "叶子节点保存单个元素",
        "内部节点保存左右孩子的合并结果",
        "修改和查询交错时仍保持 O(log n)",
        "查询/修改只访问相关分支",
    ]


def concept_demo_segment_build():
    rows = [
        {"line": 2, "phase": "根节点管理整个数组区间 [1,8], 数据是 3 1 4 1 5 9 2 6", "focus": "build root", "result": "[1,8]", "concept": {"kind": "segment_tree", "nodes": _segment_nodes(), "edges": _segment_edges(), "visible": ["1"], "active": ["1"]}},
        {"line": 3, "phase": "不断二分区间, 直到每个叶子只代表一个元素", "focus": "split", "result": "分治", "concept": {"kind": "segment_tree", "nodes": _segment_nodes(), "edges": _segment_edges(), "visible": [str(i) for i in range(1, 16)], "active": [str(i) for i in range(8, 16)]}},
        {"line": 4, "phase": "向上汇总: [1,2]=3+1, [5,6]=5+9, [7,8]=2+6", "focus": "merge", "result": "子区间求和", "concept": {"kind": "segment_tree", "nodes": _segment_nodes(), "edges": _segment_edges(), "active": ["4", "6", "7"], "covered": ["8", "9", "12", "13", "14", "15"]}},
        {"line": 5, "phase": "根节点保存整个数组的和 31, 以后查询可以整段复用", "focus": "tree[1]", "result": 31, "concept": {"kind": "segment_tree", "nodes": _segment_nodes(), "edges": _segment_edges(), "active": ["1"], "covered": ["1"]}},
    ]
    return _build_advanced_ds_demo("线段树_建树", _segment_source("线段树建树"), rows, "概念动画：线段树把数组拆成很多已登记的小区间。")


def concept_demo_segment_update():
    updated = _segment_nodes({"1": 34, "3": 25, "6": 17, "13": 12})
    rows = [
        {"line": 1, "phase": "要把位置 6 加 3, 只沿着包含 6 的路径往下走", "focus": "x=6", "result": "+3", "concept": {"kind": "segment_tree", "nodes": _segment_nodes(), "edges": _segment_edges(), "active": ["1", "3", "6", "13"], "covered": ["13"]}},
        {"line": 2, "phase": "叶子 [6,6] 从 9 变成 12", "focus": "[6,6]", "result": "12", "concept": {"kind": "segment_tree", "nodes": updated, "edges": _segment_edges(), "active": ["13"], "covered": ["13"]}},
        {"line": 3, "phase": "回溯时只更新祖先节点: [5,6]、[5,8]、[1,8]", "focus": "向上更新", "result": "34", "concept": {"kind": "segment_tree", "nodes": updated, "edges": _segment_edges(), "active": ["6", "3", "1"], "covered": ["13"]}},
    ]
    return _build_advanced_ds_demo("线段树_单点修改", _segment_source("线段树单点修改"), rows, "概念动画：单点修改不会重建整棵树, 只改一条根到叶的路径。")


def concept_demo_segment_query():
    rows = [
        {"line": 1, "phase": "查询 [3,7], 从根节点开始判断是否完全覆盖", "focus": "[3,7]", "result": "拆区间", "concept": {"kind": "segment_tree", "nodes": _segment_nodes(), "edges": _segment_edges(), "active": ["1"], "query": [3, 7]}},
        {"line": 2, "phase": "[3,4] 完全在查询范围内, 可以直接拿节点值 5", "focus": "[3,4]", "result": 5, "concept": {"kind": "segment_tree", "nodes": _segment_nodes(), "edges": _segment_edges(), "active": ["5"], "covered": ["5"], "query": [3, 7]}},
        {"line": 2, "phase": "[5,6] 也完全覆盖, 整段值 14 直接复用", "focus": "[5,6]", "result": 14, "concept": {"kind": "segment_tree", "nodes": _segment_nodes(), "edges": _segment_edges(), "active": ["6"], "covered": ["5", "6"], "query": [3, 7]}},
        {"line": 3, "phase": "再加上 [7,7] 的 2, 查询结果是 5+14+2=21", "focus": "求和", "result": 21, "concept": {"kind": "segment_tree", "nodes": _segment_nodes(), "edges": _segment_edges(), "active": ["5", "6", "14"], "covered": ["5", "6", "14"], "query": [3, 7]}},
    ]
    return _build_advanced_ds_demo("线段树_区间查询", _segment_source("线段树区间查询"), rows, "概念动画：区间查询不是逐个数, 而是拼接几个已经算好的区间。")


def concept_demo_segment_full():
    demo = concept_demo_segment_query()
    demo["title"] = "线段树_完整示例"
    for step in demo.get("steps", []):
        concept = step.get("vars", {}).get("concept")
        if isinstance(concept, dict):
            concept["title"] = "线段树_完整示例"
    demo["program_output"] = [{"after_step": 4, "text": "概念动画：完整示例把建树、查询、单点修改串在一起。"}]
    return demo


def _fenwick_source(title):
    return [
        f"算法: {title}",
        "lowbit(x) = x & -x",
        "c[x] 管理一段以 x 结尾的区间",
        "update 向右跳到受影响的大区间",
        "query 向左收集若干段前缀和",
    ]


def _fenwick_rows(kind):
    ranges = [[1, 1], [1, 2], [3, 3], [1, 4], [5, 5], [5, 6], [7, 7], [1, 8]]
    base = {"kind": "fenwick", "values": [1, 2, 3, 4, 5, 6, 7, 8], "ranges": ranges}
    if kind == "lowbit":
        states = [
            ("lowbit(6)", 6, "6 的二进制是 110, 最低位的 1 代表 2", [5]),
            ("c[6]", "[5,6]", "所以 c[6] 管理 [5,6] 这一段", [5]),
            ("lowbit(8)", 8, "8 是 1000, lowbit=8, c[8] 管理 [1,8]", [7]),
        ]
    elif kind == "update":
        states = [
            ("update(5,+10)", "5", "修改第 5 个数, 先影响 c[5]", [4]),
            ("i += lowbit(i)", "6", "下一跳到 c[6], 因为 c[6] 也覆盖位置 5", [4, 5]),
            ("继续右跳", "8", "再跳到 c[8], 所有受影响区间都更新完", [4, 5, 7]),
        ]
    else:
        states = [
            ("query(7)", "7", "求前缀和 [1,7], 先拿 c[7] 管理的 [7,7]", [6]),
            ("i -= lowbit(i)", "6", "再拿 c[6] 管理的 [5,6]", [6, 5]),
            ("继续左跳", "4", "最后拿 c[4] 管理的 [1,4], 三段拼成 [1,7]", [6, 5, 3]),
        ]
    rows = []
    for idx, (focus, result, phase, active) in enumerate(states):
        c = dict(base)
        c["active"] = active
        rows.append({"line": idx + 1, "focus": focus, "result": result, "phase": phase, "concept": c})
    return rows


def concept_demo_fenwick_lowbit():
    return _build_advanced_ds_demo("树状数组_lowbit", _fenwick_source("树状数组 lowbit"), _fenwick_rows("lowbit"), "概念动画：lowbit 决定 c[i] 管理多长的一段。")


def concept_demo_fenwick_ops():
    return _build_advanced_ds_demo("树状数组_实现", _fenwick_source("树状数组实现"), _fenwick_rows("query") + _fenwick_rows("update"), "概念动画：先用 sum(7) 看 query 如何向左收集, 再看 update 如何向右通知。")


def concept_demo_fenwick_full():
    return _build_advanced_ds_demo("树状数组_完整示例", _fenwick_source("树状数组完整示例"), _fenwick_rows("query") + _fenwick_rows("update"), "概念动画：树状数组用少数几个 c[i] 拼出前缀和与区间和。")


def _build_bit_visual_demo(title, source, states, output):
    steps = []
    for idx, state in enumerate(states):
        concept = {
            "kind": "bit_visual",
            "title": title,
            "bits": state.get("bits", []),
            "rows": state.get("rows", []),
            "active": state.get("active", []),
            "labels": state.get("labels", []),
            "caption": state.get("phase", ""),
        }
        steps.append({
            "step": idx,
            "line": state.get("line", 1),
            "type": "exec",
            "vars": {
                "value": state.get("value", "-"),
                "result": state.get("result", "-"),
                "phase": state.get("phase", ""),
                "concept": concept,
            },
        })
    return _build_simple_concept_algo(title, source, steps, ["value", "result", "phase"], output)


def concept_demo_brian_kernighan():
    source = [
        "算法: Brian Kernighan 统计 1 的个数",
        "输入: n",
        "输出: n 的二进制中 1 的数量",
        "",
        "count = 0",
        "while n != 0:",
        "    n = n & (n - 1)",
        "    count++",
    ]
    states = [
        {"line": 5, "value": 42, "result": 0, "bits": "101010", "active": [1, 3, 5], "phase": "42 的二进制是 101010, 里面有几个 1 就循环几次"},
        {"line": 7, "value": "42 & 41", "result": 1, "rows": [["n", "101010"], ["n-1", "101001"], ["n&(n-1)", "101000"]], "active": [5], "phase": "第一次 n&(n-1), 清掉最右边的 1"},
        {"line": 7, "value": "40 & 39", "result": 2, "rows": [["n", "101000"], ["n-1", "100111"], ["n&(n-1)", "100000"]], "active": [3], "phase": "第二次继续清掉当前最右边的 1"},
        {"line": 8, "value": "32 & 31", "result": 3, "rows": [["n", "100000"], ["n-1", "011111"], ["n&(n-1)", "000000"]], "active": [1], "phase": "清到 0 为止, 一共清了 3 次, 所以有 3 个 1"},
    ]
    return _build_bit_visual_demo("BrianKernighan_统计1的个数", source, states, "概念动画：n & (n-1) 每次精准清掉最低位的 1。")


def concept_demo_power_of_two():
    source = [
        "算法: 判断 2 的幂",
        "输入: n",
        "输出: n 是否为 2 的幂",
        "",
        "如果 n <= 0: false",
        "如果 n & (n - 1) == 0: true",
        "否则 false",
    ]
    states = [
        {"line": 5, "value": 8, "result": "true", "bits": "1000", "active": [0], "phase": "2 的幂只有一个 1, 像独行侠"},
        {"line": 6, "value": "8 & 7", "result": 0, "rows": [["8", "1000"], ["7", "0111"], ["&", "0000"]], "active": [0], "phase": "唯一的 1 被清掉后变成 0, 所以 8 是 2 的幂"},
        {"line": 7, "value": "10 & 9", "result": 8, "rows": [["10", "1010"], ["9", "1001"], ["&", "1000"]], "active": [0, 2], "phase": "10 有两个 1, 清掉一个后还剩 1, 所以不是 2 的幂"},
    ]
    return _build_bit_visual_demo("判断2的幂", source, states, "概念动画：只要 n&(n-1) 不是 0, 就说明二进制里不止一个 1。")


def concept_demo_xor_swap():
    source = [
        "算法: 异或交换",
        "输入: a=5, b=3",
        "输出: 交换后的 a,b",
        "",
        "a = a ^ b",
        "b = a ^ b",
        "a = a ^ b",
    ]
    states = [
        {"line": 1, "value": "a=5,b=3", "result": "0101 / 0011", "rows": [["a", "0101"], ["b", "0011"]], "phase": "先看成二进制: a=0101, b=0011"},
        {"line": 5, "value": "a=a^b", "result": "0110", "rows": [["a", "0101"], ["b", "0011"], ["a^b", "0110"]], "active": [1, 2], "phase": "第一步把两个数的差异信息暂存在 a 里"},
        {"line": 6, "value": "b=a^b", "result": "0101", "rows": [["a", "0110"], ["b", "0011"], ["new b", "0101"]], "active": [1, 2], "phase": "第二步 b 取回原来的 a"},
        {"line": 7, "value": "a=a^b", "result": "0011", "rows": [["a", "0110"], ["b", "0101"], ["new a", "0011"]], "active": [1, 2], "phase": "第三步 a 取回原来的 b, 交换完成"},
    ]
    return _build_bit_visual_demo("异或交换", source, states, "概念动画：异或交换靠 a^a=0 和 a^0=a 把两个值还原出来。")


def concept_demo_bitmap():
    source = [
        "算法: 位图 Bitmap",
        "输入: 要标记的编号 n",
        "输出: 编号是否存在",
        "",
        "index = n / 8",
        "offset = n % 8",
        "set: bits[index] |= 1 << offset",
        "get: bits[index] & (1 << offset)",
    ]
    states = [
        {"line": 4, "value": "n=5", "result": "index=0 offset=5", "bits": "00000000", "active": [5], "labels": list("76543210"), "phase": "一个字节有 8 个座位, n=5 落在第 0 字节第 5 位"},
        {"line": 7, "value": "set(5)", "result": "00100000", "bits": "00100000", "active": [2], "labels": list("76543210"), "phase": "把对应 bit 置为 1, 表示 5 存在"},
        {"line": 7, "value": "set(1)", "result": "00100010", "bits": "00100010", "active": [6], "labels": list("76543210"), "phase": "再标记 1, 同一个字节里多个编号可以共用空间"},
        {"line": 8, "value": "get(2)", "result": "false", "bits": "00100010", "active": [5], "labels": list("76543210"), "phase": "检查 2 时看到对应位是 0, 所以它不存在"},
    ]
    return _build_bit_visual_demo("位图_Bitmap", source, states, "概念动画：位图用一个 bit 记录一个编号是否出现, 空间非常省。")


def concept_demo_permission_bits():
    source = [
        "算法: 权限管理位运算",
        "输入: 用户权限 user_perm",
        "输出: 检查/添加/移除权限",
        "",
        "READ=0001, WRITE=0010, EXEC=0100, ADMIN=1000",
        "检查: user & perm",
        "添加: user | perm",
        "移除: user & ~perm",
    ]
    states = [
        {"line": 4, "value": "READ", "result": "0001", "bits": "0001", "active": [3], "labels": ["A", "X", "W", "R"], "phase": "初始只有读权限 READ"},
        {"line": 6, "value": "user & WRITE", "result": "0000", "rows": [["user", "0001"], ["WRITE", "0010"], ["&", "0000"]], "active": [2], "phase": "检查写权限: 对应位是 0, 所以没有"},
        {"line": 7, "value": "user | WRITE", "result": "0011", "rows": [["user", "0001"], ["WRITE", "0010"], ["|", "0011"]], "active": [2, 3], "phase": "添加写权限: 用 | 把 WRITE 那一位打开"},
        {"line": 8, "value": "user & ~READ", "result": "0010", "rows": [["user", "0011"], ["~READ", "1110"], ["&", "0010"]], "active": [3], "phase": "移除读权限: 用 &~ 把 READ 那一位清掉"},
    ]
    return _build_bit_visual_demo("权限管理_位运算", source, states, "概念动画：一个整数的不同 bit 可以同时保存多种权限开关。")


def concept_demo_pearson_similarity():
    source = [
        "算法: 用户相似度",
        "输入: 你、小明、小红对商品的评分",
        "输出: 谁和你更像",
        "",
        "把每个人的评分看成一行数字",
        "先看评分变化趋势是否一致",
        "趋势越像, 相似度越高",
        "优先参考最相似用户的喜好",
    ]
    grid = [
        [5, 3, 4, 1],
        [4, 4, 5, 2],
        [1, 5, 2, 5],
    ]
    rows = [
        (4, "每个人的打分就是一条品味曲线", [0, 0], [], ["商品: 苹果/香蕉/橘子/西瓜"]),
        (6, "你和小明的评分整体同涨同落, 口味更接近", [1, 2], [[0, 0], [1, 0], [0, 2], [1, 2]], ["你-小明", "相似度 0.63"]),
        (6, "小红喜欢的方向和你差别很大, 甚至接近反着来", [2, 3], [[0, 0], [2, 0], [0, 3], [2, 3]], ["你-小红", "相似度 -0.94"]),
        (8, "所以推荐系统会优先参考小明喜欢的商品", [1, 0], [[1, 0], [1, 1], [1, 2], [1, 3]], ["推荐参考", "小明"]),
    ]
    steps = []
    for idx, (line, phase, active, refs, badges) in enumerate(rows):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "simAB": "-" if idx < 1 else "0.63",
                "simAC": "-" if idx < 2 else "-0.94",
                "phase": phase,
                "concept": {
                    "kind": "dp_table",
                    "title": "协同过滤: 谁和你品味更像",
                    "subtitle": "把评分排成表, 比较变化趋势",
                    "grid": grid,
                    "rowLabels": ["你", "小明", "小红"],
                    "colLabels": ["苹果", "香蕉", "橘子", "西瓜"],
                    "active": active,
                    "refs": refs,
                    "badges": badges,
                },
            },
        })
    return _build_simple_concept_algo(
        "皮尔逊相似度",
        source,
        steps,
        ["simAB", "simAC", "phase"],
        "理解动画：协同过滤先找和你口味更像的人, 再参考他的偏好做推荐。",
    )


def concept_demo_pagerank():
    source = [
        "算法: PageRank 简化版",
        "输入: 网页链接关系 links",
        "输出: 每个网页的重要度 rank",
        "",
        "所有网页初始分数相同",
        "重复迭代:",
        "    每个网页把分数平均分给它指向的网页",
        "    加入阻尼系数和随机跳转",
        "分数稳定后, rank 越高网页越重要",
    ]
    labels = ["A", "B", "C", "D"]
    edges = [["A", "B"], ["A", "C"], ["B", "C"], ["C", "A"], ["D", "C"]]
    rank_states = [
        (5, "四个网页初始分数一样", [0.25, 0.25, 0.25, 0.25], []),
        (7, "A 把分数分给 B 和 C", [0.25, 0.25, 0.25, 0.25], [["A", "B"], ["A", "C"]]),
        (7, "C 指向 A, 所以 A 会得到重要页面的回流", [0.25, 0.144, 0.569, 0.038], [["C", "A"]]),
        (8, "多轮迭代后, 分数开始稳定", [0.404, 0.209, 0.349, 0.038], [["A", "C"], ["B", "C"], ["D", "C"]]),
        (9, "最终 A 和 C 更重要, D 只剩随机跳转分", [0.373, 0.196, 0.394, 0.038], []),
    ]
    steps = []
    for idx, (line, phase, ranks, active_edges) in enumerate(rank_states):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "iteration": idx,
                "top": labels[max(range(len(ranks)), key=lambda i: ranks[i])],
                "phase": phase,
                "concept": {
                    "kind": "pagerank",
                    "labels": labels,
                    "edges": edges,
                    "ranks": ranks,
                    "activeEdges": active_edges,
                    "iteration": idx,
                },
            },
        })
    return {
        "title": "PageRank_简化版",
        "source": source,
        "important_vars": {"iteration": "轮次", "top": "最高排名", "phase": "阶段"},
        "track_vars": {"primary": ["iteration", "top", "phase"], "secondary": []},
        "var_classes": {
            "iteration": {"category": "primary", "type": "scalar"},
            "top": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": "概念动画：网页把重要度沿链接传递, 被重要网页指向的页面排名会升高。"}],
        "steps": steps,
    }


def concept_demo_navigation_dijkstra():
    source = [
        "算法: 导航里的 Dijkstra",
        "输入: 路口图 graph, 起点 0",
        "输出: 从起点到各路口的最短时间",
        "",
        "dist[起点] = 0, 其他路口 = ∞",
        "重复:",
        "    选当前已知最近的未确定路口 u",
        "    确定 u 的最短时间",
        "    用 u 周围道路更新邻居时间",
        "直到目标路口确定",
    ]
    rows = [
        {"line": 5, "phase": "从路口 A 出发, 当前只知道 A=0", "current": "A", "frontier": "A", "best": 0, "dist": {"A": 0}, "settled": [], "activeEdges": []},
        {"line": 8, "phase": "确定 A, 发现到 B 要 4 分钟, 到 C 要 2 分钟", "current": "A", "frontier": "B,C", "best": 0, "dist": {"A": 0, "B": 4, "C": 2}, "settled": ["A"], "activeEdges": [["A", "B"], ["A", "C"]]},
        {"line": 7, "phase": "C 是当前最近的未确定路口, 先扩展 C", "current": "C", "frontier": "B,E", "best": 2, "dist": {"A": 0, "B": 4, "C": 2, "E": 12}, "settled": ["A", "C"], "activeEdges": [["C", "B"], ["C", "E"]]},
        {"line": 9, "phase": "经 C 到 B 只要 3 分钟, 比原来的 4 更快", "current": "C", "frontier": "B,E", "best": 3, "dist": {"A": 0, "B": 3, "C": 2, "E": 12}, "settled": ["A", "C"], "activeEdges": [["C", "B"]]},
        {"line": 9, "phase": "继续扩展 B 和 D, 最短时间像水波一样向外稳定", "current": "D", "frontier": "E,F", "best": 8, "dist": {"A": 0, "B": 3, "C": 2, "D": 8, "E": 10, "F": 14}, "settled": ["A", "C", "B", "D"], "activeEdges": [["B", "D"], ["D", "E"], ["D", "F"]]},
        {"line": 10, "phase": "终点 F 的最短时间确定, 导航路线就能回溯出来", "current": "F", "frontier": "-", "best": 11, "dist": {"A": 0, "B": 3, "C": 2, "D": 8, "E": 10, "F": 11}, "settled": ["A", "B", "C", "D", "E", "F"], "path": [["A", "C"], ["C", "B"], ["B", "D"], ["D", "F"]], "activeEdges": [["D", "F"]]},
    ]
    return _build_path_demo(
        "Dijkstra导航_现实版",
        source,
        rows,
        "理解动画：导航把路口和道路变成图, Dijkstra 每次从当前最近的路口继续向外扩展。",
        "dijkstra",
    )


def concept_demo_lz77():
    source = [
        "算法: LZ77 压缩",
        "输入: 一段文本 text",
        "输出: 字面量和回溯引用组成的 token",
        "",
        "维护一个已经看过的滑动窗口",
        "在窗口中寻找当前位置开始的最长重复片段",
        "如果找不到足够长的重复: 输出字面量",
        "如果找到重复: 输出 (offset, length)",
        "向前移动, 继续处理后面的字符",
    ]
    text = list("ABABABCAABAB")
    frames = [
        (5, 0, 0, 0, "窗口为空, 只能原样输出 A", ["A"]),
        (7, 1, 0, 0, "B 没有在窗口中重复, 继续输出字面量", ["A", "B"]),
        (8, 2, 0, 4, "从当前位置看到 ABAB, 它和窗口里的 AB 重复延展", ["A", "B", "(2,4)"]),
        (7, 6, 0, 0, "C 是新字符, 原样输出", ["A", "B", "(2,4)", "C"]),
        (8, 7, 3, 1, "A 能找到, 但重复太短, 仍按字面量处理更直观", ["A", "B", "(2,4)", "C", "A"]),
        (8, 8, 2, 4, "最后的 ABAB 再次用回溯引用表示", ["A", "B", "(2,4)", "C", "A", "(6,4)"]),
    ]
    steps = []
    for idx, (line, pos, match_start, match_len, phase, tokens) in enumerate(frames):
        offset = pos - match_start if match_len > 1 else 0
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "pos": pos,
                "match": f"{match_len} 个字符" if match_len > 1 else "无",
                "token": tokens[-1],
                "phase": phase,
                "concept": {
                    "kind": "lz77",
                    "text": text,
                    "pos": pos,
                    "matchStart": match_start,
                    "matchLen": match_len,
                    "offset": offset,
                    "tokens": tokens,
                    "phase": phase,
                },
            },
        })
    return {
        "title": "LZ77压缩",
        "source": source,
        "important_vars": {"pos": "当前位置", "match": "匹配长度", "token": "输出 token", "phase": "阶段"},
        "track_vars": {"primary": ["pos", "match", "token", "phase"], "secondary": []},
        "var_classes": {
            "pos": {"category": "primary", "type": "scalar"},
            "match": {"category": "primary", "type": "scalar"},
            "token": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": "概念动画：LZ77 的核心是把后面重复出现的片段, 改写成“回头数几格、复制几个字符”。"}],
        "steps": steps,
    }


def concept_demo_gradient_descent():
    source = [
        "算法: 梯度下降",
        "目标: 最小化 y = (x - 3)^2",
        "输入: 初始 x, 学习率 lr",
        "",
        "重复:",
        "    gradient = 2 * (x - 3)",
        "    x = x - lr * gradient",
        "    y = (x - 3)^2",
        "直到足够接近最低点",
    ]
    xs = [0.0, 1.2, 1.92, 2.352, 2.611, 2.767, 2.86, 2.916]
    steps = []
    for idx, x in enumerate(xs):
        loss = (x - 3) * (x - 3)
        grad = 2 * (x - 3)
        line = 6 if idx == 0 else 7 if idx < len(xs) - 1 else 9
        phase = "看斜率方向" if idx == 0 else "沿着负梯度往低处走" if idx < len(xs) - 1 else "已经靠近最低点 x=3"
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "x": round(x, 3),
                "gradient": round(grad, 3),
                "loss": round(loss, 3),
                "phase": phase,
                "concept": {
                    "kind": "gradient",
                    "x": x,
                    "gradient": grad,
                    "loss": loss,
                    "target": 3,
                    "trail": xs[:idx + 1],
                },
            },
        })
    return {
        "title": "梯度下降_一元函数",
        "source": source,
        "important_vars": {"x": "当前位置", "gradient": "梯度", "loss": "损失", "phase": "阶段"},
        "track_vars": {"primary": ["x", "gradient", "loss", "phase"], "secondary": []},
        "var_classes": {
            "x": {"category": "primary", "type": "scalar"},
            "gradient": {"category": "primary", "type": "scalar"},
            "loss": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": "概念动画：梯度告诉我们坡往哪边升高, 反方向走就会靠近最低点。"}],
        "steps": steps,
    }


def concept_demo_learning_rate_compare():
    source = [
        "算法: 学习率对比",
        "目标: 最小化 y = (x - 3)^2",
        "输入: 初始 x=0, 两个学习率",
        "",
        "合适的学习率:",
        "    每一步都靠近最低点",
        "过大的学习率:",
        "    一步跨过谷底, 又从另一边跨回来",
        "观察轨迹, 理解步子太大为什么会震荡",
    ]
    smooth = [0.0, 0.6, 1.08, 1.464, 1.771, 2.017, 2.214, 2.371, 2.497, 2.598, 2.678]
    jumpy = [0.0, 4.8, 1.92, 3.648, 2.611, 3.233, 2.86, 3.084, 2.95, 3.03, 2.982]
    frames = [
        (6, 0, "从同一个起点出发", "x=0"),
        (6, 1, "合适学习率小步下降, 过大学习率直接冲过谷底", "第一次更新"),
        (7, 2, "过大的步子开始左右横跳", "第二次更新"),
        (7, 4, "小步轨迹持续收敛, 大步轨迹仍在摆动", "观察趋势"),
        (9, 7, "合适学习率已经很稳, 大学习率逐渐被拉回来", "接近谷底"),
        (9, 10, "学习率不是越大越快, 关键是稳定靠近目标", "结论"),
    ]
    steps = []
    for idx, (line, upto, phase, state) in enumerate(frames):
        sx = smooth[upto]
        jx = jumpy[upto]
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "round": upto,
                "state": state,
                "smooth_x": round(sx, 3),
                "jumpy_x": round(jx, 3),
                "phase": phase,
                "concept": {
                    "kind": "gradient",
                    "target": 3,
                    "x": sx,
                    "gradient": 2 * (sx - 3),
                    "loss": (sx - 3) * (sx - 3),
                    "paths": [
                        {"label": "lr=0.10 稳定", "trail": smooth[:upto + 1], "color": "#34d399"},
                        {"label": "lr=0.80 震荡", "trail": jumpy[:upto + 1], "color": "#fb7185"},
                    ],
                    "note": phase,
                },
            },
        })
    return {
        "title": "学习率_步长对比",
        "source": source,
        "important_vars": {"round": "轮次", "state": "阶段", "smooth_x": "小步 x", "jumpy_x": "大步 x", "phase": "观察"},
        "track_vars": {"primary": ["round", "state", "smooth_x", "jumpy_x", "phase"], "secondary": []},
        "var_classes": {
            "round": {"category": "primary", "type": "scalar"},
            "state": {"category": "primary", "type": "scalar"},
            "smooth_x": {"category": "primary", "type": "scalar"},
            "jumpy_x": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": "概念动画：学习率太大时会越过谷底并震荡, 稳定比盲目迈大步更重要。"}],
        "steps": steps,
    }


def _build_dp_rolling_demo(title, source, steps_data, output):
    steps = []
    for idx, data in enumerate(steps_data):
        concept = dict(data["concept"])
        concept["kind"] = "dp_rolling"
        steps.append({
            "step": idx,
            "line": data.get("line", 1),
            "type": "exec",
            "vars": {
                "i": data.get("i", "-"),
                "state": data.get("state", "-"),
                "best": data.get("best", "-"),
                "phase": data.get("phase", ""),
                "concept": concept,
            },
        })
    return {
        "title": title,
        "source": source,
        "important_vars": {"i": "位置", "state": "压缩状态", "best": "当前最优", "phase": "阶段"},
        "track_vars": {"primary": ["i", "state", "best", "phase"], "secondary": []},
        "var_classes": {
            "i": {"category": "primary", "type": "scalar"},
            "state": {"category": "primary", "type": "scalar"},
            "best": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": output}],
        "steps": steps,
    }


def concept_demo_climb_dp():
    dp_states = [
        (0, [1, None, None, None, None, None], "初始化: 站在第 0 阶有 1 种方式", "dp[0] = 1"),
        (1, [1, 1, None, None, None, None], "第 1 阶只能一步走上来", "dp[1] = 1"),
        (2, [1, 1, 2, None, None, None], "到第 2 阶: 从 1 阶走一步, 或从 0 阶跨两步", "dp[2] = dp[1] + dp[0] = 2"),
        (3, [1, 1, 2, 3, None, None], "每一格只看左边两格", "dp[3] = 2 + 1 = 3"),
        (4, [1, 1, 2, 3, 5, None], "答案像小雪球一样往右滚", "dp[4] = 3 + 2 = 5"),
        (5, [1, 1, 2, 3, 5, 8], "第 5 阶共有 8 种走法", "dp[5] = 5 + 3 = 8"),
    ]
    steps = []
    for i, dp, phase, formula in dp_states:
        prev2 = dp[i - 2] if i >= 2 else "-"
        prev1 = dp[i - 1] if i >= 1 else "-"
        steps.append({
            "line": 6 if i < 2 else 8,
            "i": i,
            "state": f"前两格={prev2},{prev1}",
            "best": dp[i],
            "phase": phase,
            "concept": {
                "mode": "line",
                "title": "爬楼梯动态规划",
                "subtitle": "一维表从左到右填, 当前格只依赖前两格",
                "valueLabel": "台阶",
                "values": [0, 1, 2, 3, 4, 5],
                "dp": dp,
                "index": i,
                "active": [i],
                "window": [
                    {"label": "dp[i-2]", "value": prev2},
                    {"label": "dp[i-1]", "value": prev1},
                    {"label": "dp[i]", "value": dp[i]},
                ],
                "formula": formula,
                "caption": "动态规划的感觉: 把前面算好的答案复用起来, 不再重复递归。",
            },
        })
    return _build_dp_rolling_demo(
        "爬楼梯_动态规划",
        [
            "算法: 爬楼梯动态规划",
            "输入: 台阶数 n",
            "",
            "dp[0] = 1",
            "dp[1] = 1",
            "for i = 2..n:",
            "    dp[i] = dp[i-1] + dp[i-2]",
            "返回 dp[n]",
        ],
        steps,
        "概念动画：爬楼梯动态规划就是从左到右复用前两格答案。",
    )


def concept_demo_climb_bottom_up():
    demo = concept_demo_climb_dp()
    demo["title"] = "爬楼梯_自底向上"
    for step in demo["steps"]:
        step["vars"]["concept"]["title"] = "爬楼梯自底向上填表"
    return demo


def concept_demo_climb_optimized():
    demo = concept_demo_climb_dp()
    demo["title"] = "爬楼梯_双变量优化"
    for step in demo["steps"]:
        concept = step["vars"]["concept"]
        concept["title"] = "爬楼梯双变量优化"
        concept["subtitle"] = "只保留前两个答案, 算出当前值后继续向右滚动"
        concept["caption"] = "空间优化不改变递推关系, 只是不用保存整张 dp 表。"
        concept["window"][0]["label"] = "prev2"
        concept["window"][1]["label"] = "prev1"
        concept["window"][2]["label"] = "current"
    return demo


def concept_demo_coin_dp():
    coins = [1, 2, 5]
    amount = 11
    snapshots = [
        (0, [0, None, None, None, None, None, None, None, None, None, None, None], "初始化: dp[0] = 0, 其他金额暂时未知", "dp[0] = 0"),
        (0, [0, 1, None, None, None, None, None, None, None, None, None, None], "先填 dp[1]: 只能从 dp[0] 加一枚 1 元硬币", "dp[1] = dp[0] + 1 = 1"),
        (1, [0, 1, 1, None, None, None, None, None, None, None, None, None], "填到 dp[2]: 直接用一枚 2 元硬币更好", "dp[2] = min(dp[1]+1, dp[0]+1) = 1"),
        (2, [0, 1, 1, 2, 2, 1, None, None, None, None, None, None], "填到 dp[5]: 一枚 5 元硬币就是最优", "dp[5] = min(dp[4]+1, dp[3]+1, dp[0]+1) = 1"),
        (2, [0, 1, 1, 2, 2, 1, 2, 2, 3, 3, None, None], "继续从小到大填, 每格都复用前面已经算好的答案", "dp[i] = min(dp[i-1], dp[i-2], dp[i-5]) + 1"),
        (2, [0, 1, 1, 2, 2, 1, 2, 2, 3, 3, 2, 3], "目标 11 的答案是 3: 5 + 5 + 1", "dp[11] = 3"),
    ]
    steps = []
    active_cells = [[0], [1], [3], [5], list(range(6, 10)), [amount]]
    for idx, (coin_i, dp, phase, formula) in enumerate(snapshots):
        steps.append({
            "line": 6 if idx == 0 else 8,
            "i": coin_i,
            "state": f"coin={coins[coin_i]}",
            "best": dp[amount] if dp[amount] is not None else "∞",
            "phase": phase,
            "concept": {
                "mode": "coin",
                "title": "硬币找零自底向上填表",
                "subtitle": "从 dp[0] 开始, 一格一格推到目标金额",
                "values": coins,
                "dp": dp,
                "index": coin_i,
                "active": active_cells[idx],
                "window": [
                    {"label": "当前硬币", "value": coins[coin_i]},
                    {"label": "目标金额", "value": amount},
                    {"label": "dp[11]", "value": dp[amount] if dp[amount] is not None else "∞"},
                ],
                "formula": formula,
                "caption": "表格里的每个数字都代表“凑到这个金额最少要几枚硬币”。",
            },
        })
    return _build_dp_rolling_demo(
        "硬币找零_自底向上填表",
        [
            "算法: 硬币找零自底向上填表",
            "输入: 金额 n",
            "",
            "dp[0] = 0, 其他位置 = ∞",
            "for i = 1..n:",
            "    如果 i >= 1, 用 dp[i-1] + 1 更新",
            "    如果 i >= 2, 用 dp[i-2] + 1 更新",
            "    如果 i >= 5, 用 dp[i-5] + 1 更新",
            "返回 dp[n]",
        ],
        steps,
        "概念动画：硬币找零自底向上填表是从小金额一路推到目标金额。",
    )


def _build_dp_table_demo(title, source, rows, output):
    steps = []
    for idx, data in enumerate(rows):
        grid = data["grid"]
        active = data.get("active", [-1, -1])
        concept = {
            "kind": "dp_table",
            "title": data.get("title", title),
            "subtitle": data.get("subtitle", "二维 DP 表: 当前格只依赖已经填好的格子"),
            "rowLabels": data.get("rowLabels", []),
            "colLabels": data.get("colLabels", []),
            "grid": grid,
            "active": active,
            "refs": data.get("refs", []),
            "formula": data.get("formula", ""),
            "caption": data.get("phase", ""),
            "badges": data.get("badges", []),
        }
        steps.append({
            "step": idx,
            "line": data.get("line", 1),
            "type": "exec",
            "vars": {
                "i": active[0] if active and active[0] >= 0 else "-",
                "j": active[1] if active and active[1] >= 0 else "-",
                "best": data.get("best", "-"),
                "phase": data.get("phase", ""),
                "concept": concept,
            },
        })
    return {
        "title": title,
        "source": source,
        "important_vars": {"i": "行", "j": "列", "best": "当前最优", "phase": "阶段"},
        "track_vars": {"primary": ["i", "j", "best", "phase"], "secondary": []},
        "var_classes": {
            "i": {"category": "primary", "type": "scalar"},
            "j": {"category": "primary", "type": "scalar"},
            "best": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": output}],
        "steps": steps,
    }


def concept_demo_knapsack_table():
    row_labels = ["0件", "吉他", "音响", "笔记", "手机"]
    col_labels = ["0", "1", "2", "3", "4"]
    rows = [
        {
            "line": 8,
            "active": [0, 0],
            "grid": [
                [0, 0, 0, 0, 0],
                [None, None, None, None, None],
                [None, None, None, None, None],
                [None, None, None, None, None],
                [None, None, None, None, None],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "第 0 行和第 0 列都是边界: 没物品或没容量, 价值为 0",
            "formula": "dp[0][w] = dp[i][0] = 0",
            "best": 0,
            "badges": ["容量 W=4", "每件只能选一次"],
        },
        {
            "line": 14,
            "active": [1, 4],
            "refs": [[0, 4], [0, 3]],
            "grid": [
                [0, 0, 0, 0, 0],
                [0, 1500, 1500, 1500, 1500],
                [None, None, None, None, None],
                [None, None, None, None, None],
                [None, None, None, None, None],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "只看吉他: 容量够就能放, 所以这一行都是 1500",
            "formula": "dp[1][4] = max(dp[0][4], 1500 + dp[0][3]) = 1500",
            "best": 1500,
            "badges": ["吉他 wt=1 val=1500"],
        },
        {
            "line": 14,
            "active": [2, 4],
            "refs": [[1, 4], [1, 0]],
            "grid": [
                [0, 0, 0, 0, 0],
                [0, 1500, 1500, 1500, 1500],
                [0, 1500, 1500, 1500, 3000],
                [None, None, None, None, None],
                [None, None, None, None, None],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "音响重量 4, 只有容量 4 时才装得下",
            "formula": "dp[2][4] = max(1500, 3000 + dp[1][0]) = 3000",
            "best": 3000,
            "badges": ["音响 wt=4 val=3000"],
        },
        {
            "line": 14,
            "active": [3, 4],
            "refs": [[2, 4], [2, 1]],
            "grid": [
                [0, 0, 0, 0, 0],
                [0, 1500, 1500, 1500, 1500],
                [0, 1500, 1500, 1500, 3000],
                [0, 1500, 1500, 2000, 3500],
                [None, None, None, None, None],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "笔记本重量 3, 容量 4 时可以和吉他搭配",
            "formula": "dp[3][4] = max(3000, 2000 + dp[2][1]) = 3500",
            "best": 3500,
            "badges": ["笔记 wt=3 val=2000"],
        },
        {
            "line": 14,
            "active": [4, 4],
            "refs": [[3, 4], [3, 3]],
            "grid": [
                [0, 0, 0, 0, 0],
                [0, 1500, 1500, 1500, 1500],
                [0, 1500, 1500, 1500, 3000],
                [0, 1500, 1500, 2000, 3500],
                [0, 2000, 3500, 3500, 4000],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "最后看手机: 容量 4 时, 手机 + 笔记本得到 4000",
            "formula": "dp[4][4] = max(3500, 2000 + dp[3][3]) = 4000",
            "best": 4000,
            "badges": ["手机 wt=1 val=2000", "答案 4000"],
        },
    ]
    return _build_dp_table_demo(
        "零一背包",
        [
            "算法: 0-1 背包",
            "状态: dp[i][w] 表示前 i 件物品, 容量 w 的最大价值",
            "每件物品只有两种选择: 不选 / 选",
            "",
            "如果装不下第 i 件:",
            "    dp[i][w] = dp[i-1][w]",
            "如果装得下第 i 件:",
            "    dp[i][w] = max(不选它, 选它)",
            "返回 dp[n][W]",
        ],
        rows,
        "概念动画：0-1 背包每个格子都在比较“选当前物品”和“不选当前物品”。",
    )


def concept_demo_lcs_table():
    row_labels = ["Ø", "A", "B", "C", "B"]
    col_labels = ["Ø", "B", "D", "C", "A", "B"]
    rows = [
        {
            "line": 8,
            "active": [0, 0],
            "grid": [
                [0, 0, 0, 0, 0, 0],
                [0, None, None, None, None, None],
                [0, None, None, None, None, None],
                [0, None, None, None, None, None],
                [0, None, None, None, None, None],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "第 0 行/列代表空串, LCS 长度都是 0",
            "formula": "dp[0][j] = dp[i][0] = 0",
            "best": 0,
            "badges": ["X=ABCB", "Y=BDCAB"],
        },
        {
            "line": 14,
            "active": [1, 4],
            "refs": [[0, 3]],
            "grid": [
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 1, 1],
                [0, None, None, None, None, None],
                [0, None, None, None, None, None],
                [0, None, None, None, None, None],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "A 和 A 匹配, 左上角答案 + 1",
            "formula": "dp[1][4] = dp[0][3] + 1 = 1",
            "best": 1,
            "badges": ["匹配 A"],
        },
        {
            "line": 14,
            "active": [2, 1],
            "refs": [[1, 0]],
            "grid": [
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 1, 1],
                [0, 1, 1, 1, 1, 2],
                [0, None, None, None, None, None],
                [0, None, None, None, None, None],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "B 和 B 匹配, 这一行开始出现公共子序列",
            "formula": "dp[2][1] = dp[1][0] + 1 = 1",
            "best": 1,
            "badges": ["匹配 B"],
        },
        {
            "line": 14,
            "active": [3, 3],
            "refs": [[2, 2]],
            "grid": [
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 1, 1],
                [0, 1, 1, 1, 1, 2],
                [0, 1, 1, 2, 2, 2],
                [0, None, None, None, None, None],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "C 和 C 匹配, LCS 长度推进到 2",
            "formula": "dp[3][3] = dp[2][2] + 1 = 2",
            "best": 2,
            "badges": ["匹配 C"],
        },
        {
            "line": 16,
            "active": [4, 5],
            "refs": [[3, 4]],
            "grid": [
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 1, 1],
                [0, 1, 1, 1, 1, 2],
                [0, 1, 1, 2, 2, 2],
                [0, 1, 1, 2, 2, 3],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "最后一个 B 也能匹配, 答案变成 3",
            "formula": "dp[4][5] = dp[3][4] + 1 = 3",
            "best": 3,
            "badges": ["LCS 长度 3"],
        },
    ]
    return _build_dp_table_demo(
        "最长公共子序列",
        [
            "算法: 最长公共子序列 LCS",
            "状态: dp[i][j] 表示 X 前 i 个字符和 Y 前 j 个字符的 LCS 长度",
            "",
            "如果 X[i-1] == Y[j-1]:",
            "    dp[i][j] = dp[i-1][j-1] + 1",
            "否则:",
            "    dp[i][j] = max(dp[i-1][j], dp[i][j-1])",
            "返回 dp[m][n]",
        ],
        rows,
        "概念动画：LCS 的表格在比较两个前缀, 匹配时从左上角接一格。",
    )


def concept_demo_lcs_restore():
    row_labels = ["Ø", "A", "B", "C", "B"]
    col_labels = ["Ø", "B", "D", "C", "A", "B"]
    grid = [
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 1],
        [0, 1, 1, 1, 1, 2],
        [0, 1, 1, 2, 2, 2],
        [0, 1, 1, 2, 2, 3],
    ]
    states = [
        ([4, 5], [[3, 4]], "右下角 3 表示 LCS 长度为 3", "X[4] = Y[5] = B, 收集 B", ["结果: B"]),
        ([3, 4], [[3, 3], [2, 4]], "C 和 A 不同, 比较上方与左方", "左方 2 更大, 向左走", ["结果: B", "移动: ←"]),
        ([3, 3], [[2, 2]], "C 和 C 相同", "收集 C, 再向左上走", ["结果: CB", "移动: ↖"]),
        ([2, 2], [[2, 1], [1, 2]], "B 和 D 不同, 比较上方与左方", "左方 1 更大, 向左走", ["结果: CB", "移动: ←"]),
        ([2, 1], [[1, 0]], "B 和 B 相同", "收集 B, 得到一种 LCS: BCB", ["结果: BCB", "完成"]),
    ]
    rows = []
    for active, refs, phase, formula, badges in states:
        rows.append({
            "line": 24,
            "active": active,
            "refs": refs,
            "grid": grid,
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": phase,
            "formula": formula,
            "best": 3,
            "badges": badges,
        })
    return _build_dp_table_demo(
        "LCS方案还原",
        [
            "算法: 从 LCS 表右下角回溯",
            "从 i=m, j=n 开始:",
            "如果 X[i-1] == Y[j-1]:",
            "    收集该字符, 向左上走",
            "否则:",
            "    走向数值较大的上方或左方",
            "直到 i=0 或 j=0",
            "返回收集到的字符",
        ],
        rows,
        "概念动画：长度表填完后, 从右下角倒着走, 就能还原一种 LCS。",
    )


def concept_demo_edit_distance_table():
    row_labels = ["Ø", "h", "o", "r", "s", "e"]
    col_labels = ["Ø", "r", "o", "s"]
    rows = [
        {
            "line": 8,
            "active": [0, 0],
            "grid": [
                [0, 1, 2, 3],
                [1, None, None, None],
                [2, None, None, None],
                [3, None, None, None],
                [4, None, None, None],
                [5, None, None, None],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "第 0 行/列先填好: 空串变成前缀只能一路插入或删除",
            "formula": "dp[i][0] = i, dp[0][j] = j",
            "best": 0,
            "badges": ["horse → ros", "插入/删除/替换"],
        },
        {
            "line": 15,
            "active": [1, 1],
            "refs": [[0, 1], [1, 0], [0, 0]],
            "grid": [
                [0, 1, 2, 3],
                [1, 1, None, None],
                [2, None, None, None],
                [3, None, None, None],
                [4, None, None, None],
                [5, None, None, None],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "h 和 r 不同, 在删除、插入、替换里选最小代价",
            "formula": "min(1, 1, 0) + 1 = 1",
            "best": 1,
            "badges": ["字符不同"],
        },
        {
            "line": 13,
            "active": [2, 2],
            "refs": [[1, 1]],
            "grid": [
                [0, 1, 2, 3],
                [1, 1, 2, 3],
                [2, 2, 1, None],
                [3, None, None, None],
                [4, None, None, None],
                [5, None, None, None],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "o 和 o 相同, 不需要新操作, 直接继承左上角",
            "formula": "dp[2][2] = dp[1][1] = 1",
            "best": 1,
            "badges": ["字符相同"],
        },
        {
            "line": 13,
            "active": [4, 3],
            "refs": [[3, 2]],
            "grid": [
                [0, 1, 2, 3],
                [1, 1, 2, 3],
                [2, 2, 1, 2],
                [3, 2, 2, 2],
                [4, 3, 3, 2],
                [5, None, None, None],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "s 和 s 相同, horse 的前四个字符已经能变成 ros",
            "formula": "dp[4][3] = dp[3][2] = 2",
            "best": 2,
            "badges": ["匹配 s"],
        },
        {
            "line": 15,
            "active": [5, 3],
            "refs": [[4, 3], [5, 2], [4, 2]],
            "grid": [
                [0, 1, 2, 3],
                [1, 1, 2, 3],
                [2, 2, 1, 2],
                [3, 2, 2, 2],
                [4, 3, 3, 2],
                [5, 4, 4, 3],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "最后 e 和 s 不同, 最少还要 1 次操作, 答案是 3",
            "formula": "min(2, 4, 3) + 1 = 3",
            "best": 3,
            "badges": ["答案 3"],
        },
    ]
    for row in rows:
        row.pop("badges", None)
    return _build_dp_table_demo(
        "编辑距离",
        [
            "算法: 编辑距离",
            "状态: dp[i][j] 表示 word1 前 i 个字符变成 word2 前 j 个字符的最少操作",
            "",
            "如果两个字符相同:",
            "    dp[i][j] = dp[i-1][j-1]",
            "否则:",
            "    dp[i][j] = min(删除, 插入, 替换) + 1",
            "返回 dp[m][n]",
        ],
        rows,
        "概念动画：编辑距离就是在二维表里选择最便宜的修改路径。",
    )


def concept_demo_matrix_chain_table():
    row_labels = ["A1", "A2", "A3", "A4"]
    col_labels = ["A1", "A2", "A3", "A4"]
    rows = [
        {
            "line": 8,
            "active": [0, 0],
            "grid": [
                [0, None, None, None],
                ["", 0, None, None],
                ["", "", 0, None],
                ["", "", "", 0],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "单个矩阵不用乘, 对角线都是 0",
            "formula": "dp[i][i] = 0",
            "best": 0,
            "badges": ["维度 10×100×5×50×1", "区间 DP"],
        },
        {
            "line": 16,
            "active": [0, 1],
            "refs": [[0, 0], [1, 1]],
            "grid": [
                [0, 5000, None, None],
                ["", 0, 25000, None],
                ["", "", 0, 250],
                ["", "", "", 0],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "长度为 2 的区间只有一种括号放法",
            "formula": "A1×A2: 10×100×5 = 5000",
            "best": 5000,
            "badges": ["先算短区间"],
        },
        {
            "line": 16,
            "active": [0, 2],
            "refs": [[0, 0], [1, 2], [0, 1], [2, 2]],
            "grid": [
                [0, 5000, 7500, None],
                ["", 0, 25000, 750],
                ["", "", 0, 250],
                ["", "", "", 0],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "长度为 3 时开始枚举切分点, 选代价最低的括号位置",
            "formula": "min(75000, 7500) = 7500",
            "best": 7500,
            "badges": ["枚举 k"],
        },
        {
            "line": 16,
            "active": [1, 3],
            "refs": [[1, 1], [2, 3], [1, 2], [3, 3]],
            "grid": [
                [0, 5000, 7500, None],
                ["", 0, 25000, 750],
                ["", "", 0, 250],
                ["", "", "", 0],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "A2..A4 最优是先算 A3×A4, 再和 A2 相乘",
            "formula": "min(750, 30000) = 750",
            "best": 750,
            "badges": ["右侧区间"],
        },
        {
            "line": 16,
            "active": [0, 3],
            "refs": [[0, 0], [1, 3], [0, 1], [2, 3], [0, 2], [3, 3]],
            "grid": [
                [0, 5000, 7500, 1750],
                ["", 0, 25000, 750],
                ["", "", 0, 250],
                ["", "", "", 0],
            ],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "phase": "最后求整条链 A1..A4, 最优代价是 1750",
            "formula": "min(1750, 5300, 8000) = 1750",
            "best": 1750,
            "badges": ["答案 1750"],
        },
    ]
    for row in rows:
        row.pop("badges", None)
    return _build_dp_table_demo(
        "矩阵链乘法",
        [
            "算法: 矩阵链乘法",
            "状态: dp[i][j] 表示矩阵 Ai..Aj 的最少乘法次数",
            "",
            "按区间长度从短到长:",
            "    枚举切分点 k",
            "    dp[i][j] = min(dp[i][k] + dp[k+1][j] + 合并代价)",
            "返回 dp[1][n]",
        ],
        rows,
        "概念动画：矩阵链乘法不是改变矩阵顺序, 而是选择更省的括号位置。",
    )


def concept_demo_lis_dp():
    nums = [10, 9, 2, 5, 3, 7, 101, 18]
    snapshots = [
        (0, [1, 1, 1, 1, 1, 1, 1, 1], "每个数字自己都能构成长度 1 的递增子序列", "dp[i] = 1"),
        (3, [1, 1, 1, 2, 1, 1, 1, 1], "5 可以接在 2 后面, 长度变成 2", "dp[3] = dp[2] + 1 = 2"),
        (4, [1, 1, 1, 2, 2, 1, 1, 1], "3 也能接在 2 后面, 但接不了 5", "dp[4] = dp[2] + 1 = 2"),
        (5, [1, 1, 1, 2, 2, 3, 1, 1], "7 可以接在 5 或 3 后面, 最好长度是 3", "dp[5] = max(2, 2) + 1 = 3"),
        (6, [1, 1, 1, 2, 2, 3, 4, 1], "101 接在 7 后面, 形成长度 4", "dp[6] = dp[5] + 1 = 4"),
        (7, [1, 1, 1, 2, 2, 3, 4, 4], "18 不如 101 大, 但仍能接在 7 后面得到长度 4", "dp[7] = dp[5] + 1 = 4"),
    ]
    steps = []
    for i, dp, phase, formula in snapshots:
        steps.append({
            "line": 9 if i == 0 else 13,
            "i": i,
            "state": f"nums[{i}]={nums[i]}",
            "best": max(dp),
            "phase": phase,
            "concept": {
                "mode": "line",
                "title": "最长递增子序列 DP",
                "subtitle": "当前数字向左寻找可以接上的最长序列",
                "valueLabel": "nums",
                "values": nums,
                "dp": dp,
                "index": i,
                "active": [i],
                "window": [
                    {"label": "当前数", "value": nums[i]},
                    {"label": "dp[i]", "value": dp[i]},
                    {"label": "maxLen", "value": max(dp)},
                ],
                "formula": formula,
                "caption": "二维思考不一定要画成二维表: LIS 的状态压在一行 dp 里。",
            },
        })
    return _build_dp_rolling_demo(
        "最长递增子序列_DP",
        [
            "算法: 最长递增子序列 DP",
            "状态: dp[i] 表示以 nums[i] 结尾的 LIS 长度",
            "",
            "for i = 0..n-1:",
            "    dp[i] = 1",
            "    for j = 0..i-1:",
            "        如果 nums[j] < nums[i], 尝试接到 j 后面",
            "返回 max(dp)",
        ],
        steps,
        "概念动画：LIS 的 O(n^2) 解法是在当前数字左边找最好的前驱。",
    )


def concept_demo_lis_binary():
    nums = [10, 9, 2, 5, 3, 7, 101, 18]
    states = [
        (0, [10, "", "", ""], "先放入 10, tails 长度为 1", "追加 10"),
        (1, [9, "", "", ""], "9 替换 10, 长度不变但结尾更小", "替换位置 0"),
        (2, [2, "", "", ""], "2 继续替换第一个位置, 给未来留下更大空间", "替换位置 0"),
        (3, [2, 5, "", ""], "5 比 2 大, 追加得到长度 2", "追加 5"),
        (4, [2, 3, "", ""], "3 替换 5, 长度还是 2, 但更有潜力", "替换位置 1"),
        (5, [2, 3, 7, ""], "7 追加, 长度推进到 3", "追加 7"),
        (6, [2, 3, 7, 101], "101 追加, 长度推进到 4", "追加 101"),
        (7, [2, 3, 7, 18], "18 替换 101, 答案长度仍是 4", "替换位置 3"),
    ]
    steps = []
    for i, tails, phase, formula in states:
        active_pos = next((idx for idx, value in enumerate(tails) if value == nums[i]), min(i, 3))
        steps.append({
            "line": 17,
            "i": i,
            "state": f"x={nums[i]}",
            "best": sum(1 for value in tails if value != ""),
            "phase": phase,
            "concept": {
                "mode": "line",
                "title": "LIS 二分优化",
                "subtitle": "tails[k] 只保存长度 k+1 的最小结尾",
                "valueLabel": "nums",
                "values": nums,
                "dp": tails,
                "index": i,
                "active": [active_pos],
                "window": [
                    {"label": "当前数", "value": nums[i]},
                    {"label": "位置", "value": active_pos},
                    {"label": "长度", "value": sum(1 for value in tails if value != "")},
                ],
                "formula": formula,
                "caption": "tails 不是某条真实子序列, 它保存的是每种长度的最小结尾。",
            },
        })
    return _build_dp_rolling_demo(
        "最长递增子序列_二分优化",
        [
            "算法: LIS 二分优化",
            "维护 tails: 长度为 k+1 的递增子序列的最小末尾",
            "",
            "for x in nums:",
            "    pos = lower_bound(tails, x)",
            "    tails[pos] = x",
            "返回 tails 的长度",
        ],
        steps,
        "概念动画：二分优化的关键是让每种长度的结尾尽量小。",
    )


def concept_demo_rolling_array():
    capacities = [0, 1, 2, 3, 4]
    states = [
        {
            "i": 0, "dp": [0, 0, 0, 0, 0],
            "title": "原始二维 DP",
            "subtitle": "每件物品占一行, 但当前行其实只会读取上一行",
            "phase": "先观察依赖关系: 更早的行算完后就不会再读取",
            "formula": "dp[i][w] 只依赖 dp[i-1][...]",
            "window": [("保存行数", "n+1"), ("上一行", "i-1"), ("当前行", "i")],
            "active": [0, 1, 2, 3, 4],
        },
        {
            "i": 1, "dp": [0, 1500, 1500, 1500, 1500],
            "title": "第一层: 两行滚动",
            "subtitle": "pre 保存上一行, cur 覆盖另一行; 下一轮两者交换身份",
            "phase": "处理吉他: pre=第 0 行, cur=第 1 行",
            "formula": "pre=(i-1)%2, cur=i%2",
            "window": [("pre", "第0行"), ("cur", "第1行"), ("保存行数", 2)],
            "active": [1, 2, 3, 4],
        },
        {
            "i": 2, "dp": [0, 1500, 1500, 1500, 3000],
            "title": "第一层: 两行滚动",
            "subtitle": "原来的 cur 变成 pre, 另一行被擦写成新的 cur",
            "phase": "处理音响: 两行身份轮换, 仍然只保存两行",
            "formula": "pre=第1行, cur=第0行",
            "window": [("pre", "第1行"), ("cur", "第0行"), ("dp[4]", 3000)],
            "active": [4],
        },
        {
            "i": 2, "dp": [0, 1500, 1500, 1500, 3000],
            "title": "第二层: 一维压缩",
            "subtitle": "两行还能压成一行, 但必须保护尚未读取的旧值",
            "phase": "0-1 背包从右往左更新, 防止同一件物品被重复使用",
            "formula": "for w = W..weight",
            "window": [("数组", "dp[0..W]"), ("方向", "从右到左"), ("原因", "读取旧值")],
            "active": [4, 3, 2, 1],
        },
        {
            "i": 3, "dp": [0, 1500, 1500, 2000, 3500],
            "title": "第二层: 一维压缩",
            "subtitle": "右侧先更新时, 左侧 dp[w-weight] 仍是上一轮旧值",
            "phase": "处理笔记本: 容量 4 读取尚未更新的 dp[1]",
            "formula": "dp[4] = max(3000, 2000 + dp[1]) = 3500",
            "window": [("物品", "笔记本"), ("方向", "倒序"), ("dp[4]", 3500)],
            "active": [4, 3],
        },
        {
            "i": 4, "dp": [0, 2000, 3500, 3500, 4000],
            "title": "第二层: 一维压缩",
            "subtitle": "空间降到 O(W), 状态转移的含义没有改变",
            "phase": "处理手机: 最终容量 4 的最大价值是 4000",
            "formula": "dp[4] = max(3500, 2000 + dp[3]) = 4000",
            "window": [("物品", "手机"), ("方向", "倒序"), ("dp[4]", 4000)],
            "active": [4, 3, 2, 1],
        },
    ]
    steps = []
    for state in states:
        steps.append({
            "line": 9,
            "i": state["i"],
            "state": state["title"],
            "best": state["dp"][4],
            "phase": state["phase"],
            "concept": {
                "mode": "line",
                "title": state["title"],
                "subtitle": state["subtitle"],
                "valueLabel": "容量",
                "values": capacities,
                "dp": state["dp"],
                "index": min(state["i"], 4),
                "active": state["active"],
                "window": [
                    {"label": label, "value": value}
                    for label, value in state["window"]
                ],
                "formula": state["formula"],
                "caption": state["phase"],
            },
        })
    return _build_dp_rolling_demo(
        "滚动数组",
        [
            "算法: 0-1 背包空间优化",
            "第一层: 二维表压成 pre/cur 两行",
            "第二层: 两行继续压成一维 dp[w]",
            "",
            "两行滚动: pre=(i-1)%2, cur=i%2",
            "一维压缩: 对每件物品, w 从 W 倒序走到 weight",
            "dp[w] = max(dp[w], value + dp[w-weight])",
            "返回 dp[W]",
        ],
        steps,
        "概念动画：先压成两行，再压成一行；每一步都先确认旧值是否还会被读取。",
    )


def concept_demo_house_robber():
    values = [2, 7, 9, 3, 1]
    states = [
        (0, [2, None, None, None, None], 0, 2, 2, "先看第 0 家", "dp[0] = 2"),
        (1, [2, 7, None, None, None], 2, 2, 7, "偷第 1 家更划算", "max(2, 7) = 7"),
        (2, [2, 7, 11, None, None], 2, 7, 11, "第 2 家可以接在第 0 家后面", "max(7, 2+9) = 11"),
        (3, [2, 7, 11, 11, None], 7, 11, 11, "第 3 家不偷更好", "max(11, 7+3) = 11"),
        (4, [2, 7, 11, 11, 12], 11, 11, 12, "最后一间偷了更好", "max(11, 11+1) = 12"),
    ]
    steps = []
    for i, dp, prev2, prev1, current, phase, formula in states:
        steps.append({
            "line": 6 if i == 0 else 8,
            "i": i,
            "state": f"prev2={prev2}, prev1={prev1}",
            "best": current,
            "phase": phase,
            "concept": {
                "mode": "rob",
                "title": "打家劫舍",
                "subtitle": "只保留前两格, 不必保存整张 dp 表",
                "values": values,
                "dp": dp,
                "index": i,
                "active": [i],
                "window": [
                    {"label": "prev2", "value": prev2},
                    {"label": "prev1", "value": prev1},
                    {"label": "current", "value": current},
                ],
                "formula": formula,
                "caption": "每一步只依赖 dp[i-1] 和 dp[i-2], 所以两个旧变量就够了。",
            },
        })
    return _build_dp_rolling_demo(
        "打家劫舍",
        [
            "算法: 打家劫舍的空间优化",
            "输入: 每间房的钱 nums",
            "",
            "prev2 = 0",
            "prev1 = nums[0]",
            "for i = 1..n-1:",
            "    current = max(prev1, prev2 + nums[i])",
            "    prev2 = prev1",
            "    prev1 = current",
            "返回 prev1",
        ],
        steps,
        "概念动画：打家劫舍的降维核心是“只记前两天”。",
    )


def concept_demo_stock_profit():
    prices = [7, 1, 5, 3, 6, 4]
    min_price = prices[0]
    best = 0
    steps = []
    for i, price in enumerate(prices):
        min_price = min(min_price, price)
        today = price - min_price
        best = max(best, today)
        steps.append({
            "line": 5 if i == 0 else 7,
            "i": i,
            "state": f"min={min_price}",
            "best": best,
            "phase": "更新最低买入价" if price == min_price else "尝试今天卖出",
            "concept": {
                "mode": "stock",
                "title": "股票买卖",
                "subtitle": "不用记录所有组合, 只记历史最低价和最好利润",
                "values": prices,
                "index": i,
                "minPrice": min_price,
                "todayProfit": today,
                "bestProfit": best,
                "formula": f"profit = price[{i}] - minPrice = {price} - {min_price} = {today}",
                "caption": "每天只问两件事：是不是更低的买入价？今天卖出会不会更赚？",
            },
        })
    return _build_dp_rolling_demo(
        "股票买卖_一次交易",
        [
            "算法: 一次股票买卖",
            "输入: 每天股价 prices",
            "",
            "minPrice = prices[0]",
            "bestProfit = 0",
            "for price in prices:",
            "    minPrice = min(minPrice, price)",
            "    bestProfit = max(bestProfit, price - minPrice)",
            "返回 bestProfit",
        ],
        steps,
        "概念动画：状态压缩成“目前最低价”和“目前最大收益”。",
    )


def concept_demo_coin_change_rolling():
    coins = [1, 3, 4]
    amount = 6
    inf = None
    snapshots = [
        (0, [0, inf, inf, inf, inf, inf, inf], "初始化: 0 元需要 0 枚硬币", "dp[0] = 0"),
        (0, [0, 1, 2, 3, 4, 5, 6], "硬币 1 可以填满所有金额", "dp[j] = dp[j-1] + 1"),
        (1, [0, 1, 2, 1, 2, 3, 2], "加入硬币 3, 金额 3/4/5/6 变好", "dp[j] = min(dp[j], dp[j-3]+1)"),
        (2, [0, 1, 2, 1, 1, 2, 2], "加入硬币 4, 金额 4/5 继续变好", "dp[j] = min(dp[j], dp[j-4]+1)"),
        (2, [0, 1, 2, 1, 1, 2, 2], "答案是 2: 3 + 3 或 4 + 1 + 1", "dp[6] = 2"),
    ]
    steps = []
    for idx, (coin_i, dp, phase, formula) in enumerate(snapshots):
        steps.append({
            "line": 6 if idx == 0 else 8,
            "i": coin_i,
            "state": f"coin={coins[coin_i]}",
            "best": dp[amount],
            "phase": phase,
            "concept": {
                "mode": "coin",
                "title": "零钱兑换",
                "subtitle": "二维选择表压成一行 dp[j]",
                "values": coins,
                "dp": dp,
                "index": coin_i,
                "active": [amount] if idx == len(snapshots) - 1 else list(range(max(0, coins[coin_i]), amount + 1)),
                "window": [
                    {"label": "当前硬币", "value": coins[coin_i]},
                    {"label": "目标金额", "value": amount},
                    {"label": "dp[6]", "value": dp[amount] if dp[amount] is not None else "∞"},
                ],
                "formula": formula,
                "caption": "完全背包从小到大更新同一行, 新结果还能继续被后面的金额复用。",
            },
        })
    return _build_dp_rolling_demo(
        "零钱兑换_完全背包",
        [
            "算法: 零钱兑换的一维 dp",
            "输入: coins, amount",
            "",
            "dp[0] = 0, 其他位置 = ∞",
            "for coin in coins:",
            "    for j = coin..amount:",
            "        dp[j] = min(dp[j], dp[j-coin] + 1)",
            "返回 dp[amount]",
        ],
        steps,
        "概念动画：零钱兑换用一维数组滚动更新, 看表格比逐行跑更清楚。",
    )


def _path_graph_base():
    return {
        "nodes": [
            {"id": "A", "x": 0.12, "y": 0.50},
            {"id": "B", "x": 0.33, "y": 0.24},
            {"id": "C", "x": 0.34, "y": 0.72},
            {"id": "D", "x": 0.58, "y": 0.28},
            {"id": "E", "x": 0.60, "y": 0.70},
            {"id": "F", "x": 0.84, "y": 0.50},
        ],
        "edges": [
            ["A", "B", 4], ["A", "C", 2], ["B", "D", 5],
            ["B", "C", 1], ["C", "E", 7], ["D", "F", 3],
            ["E", "F", 2], ["D", "E", 1],
        ],
    }


def _build_path_demo(title, source, rows, output, mode):
    base = _path_graph_base()
    steps = []
    for idx, row in enumerate(rows):
        vars_payload = {
            "current": row.get("current", "-"),
            "frontier": row.get("frontier", "-"),
            "best": row.get("best", "-"),
            "phase": row["phase"],
            "concept": {
                "kind": "shortest_path",
                "mode": mode,
                "title": title,
                "nodes": base["nodes"],
                "edges": base["edges"],
                **row,
            },
        }
        steps.append({"step": idx, "line": row.get("line", 1), "type": "exec", "vars": vars_payload})
    return {
        "title": title,
        "source": source,
        "important_vars": {"current": "当前点", "frontier": "待处理", "best": "当前最短", "phase": "阶段"},
        "track_vars": {"primary": ["current", "frontier", "best", "phase"], "secondary": []},
        "var_classes": {
            "current": {"category": "primary", "type": "scalar"},
            "frontier": {"category": "primary", "type": "scalar"},
            "best": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": output}],
        "steps": steps,
    }


def concept_demo_dijkstra():
    source = [
        "算法: Dijkstra 最短路",
        "输入: 非负权图, 起点 A",
        "输出: A 到各点的最短距离",
        "",
        "dist[A] = 0, 其他点 = ∞",
        "重复:",
        "    选择未确定点中 dist 最小的点 u",
        "    把 u 标记为已确定",
        "    用 u 的出边松弛邻居 v",
        "直到所有点确定",
    ]
    rows = [
        {"line": 5, "phase": "起点 A 的距离为 0", "current": "A", "frontier": "A", "best": 0, "dist": {"A": 0}, "settled": [], "activeEdges": []},
        {"line": 8, "phase": "确定 A, 松弛到 B=4、C=2", "current": "A", "frontier": "B,C", "best": 0, "dist": {"A": 0, "B": 4, "C": 2}, "settled": ["A"], "activeEdges": [["A", "B"], ["A", "C"]]},
        {"line": 7, "phase": "未确定点里 C 最短, 先处理 C", "current": "C", "frontier": "B,E", "best": 2, "dist": {"A": 0, "B": 4, "C": 2, "E": 9}, "settled": ["A", "C"], "activeEdges": [["C", "B"], ["C", "E"]]},
        {"line": 8, "phase": "B 经 C 变成 3, 比原来的 4 更短", "current": "C", "frontier": "B,E", "best": 3, "dist": {"A": 0, "B": 3, "C": 2, "E": 9}, "settled": ["A", "C"], "activeEdges": [["C", "B"]]},
        {"line": 8, "phase": "确定 B, 松弛到 D=8", "current": "B", "frontier": "D,E", "best": 8, "dist": {"A": 0, "B": 3, "C": 2, "D": 8, "E": 9}, "settled": ["A", "C", "B"], "activeEdges": [["B", "D"]]},
        {"line": 8, "phase": "确定 D, 继续得到 E=9、F=11", "current": "D", "frontier": "E,F", "best": 11, "dist": {"A": 0, "B": 3, "C": 2, "D": 8, "E": 9, "F": 11}, "settled": ["A", "C", "B", "D"], "activeEdges": [["D", "E"], ["D", "F"]]},
        {"line": 9, "phase": "终点 F 的最短距离确定为 11", "current": "F", "frontier": "-", "best": 11, "dist": {"A": 0, "B": 3, "C": 2, "D": 8, "E": 9, "F": 11}, "settled": ["A", "B", "C", "D", "E", "F"], "path": [["A", "C"], ["C", "B"], ["B", "D"], ["D", "F"]], "activeEdges": [["D", "F"]]},
    ]
    return _build_path_demo("Dijkstra_朴素版", source, rows, "概念动画：Dijkstra 每轮都挑当前最短的未确定点, 再向外扩展。", "dijkstra")


def concept_demo_dijkstra_heap():
    source = [
        "算法: Dijkstra 堆优化",
        "输入: 稀疏非负权图, 起点 A",
        "输出: A 到各点的最短距离",
        "",
        "dist[A] = 0, A 入最小堆",
        "while 堆不空:",
        "    弹出 dist 最小的点 u",
        "    如果 u 已确定, 跳过旧记录",
        "    用 u 的邻接表出边松弛 v",
        "    v 变短后, 把新距离压入堆",
    ]
    rows = [
        {"line": 5, "phase": "A 入堆, 堆顶就是当前最短候选", "current": "A", "frontier": "heap=[A:0]", "best": 0, "dist": {"A": 0}, "settled": [], "activeEdges": []},
        {"line": 9, "phase": "弹出 A, 只遍历 A 真实连出的两条边", "current": "A", "frontier": "B:4,C:2", "best": "C:2", "dist": {"A": 0, "B": 4, "C": 2}, "settled": ["A"], "activeEdges": [["A", "B"], ["A", "C"]]},
        {"line": 7, "phase": "堆会自动把 C 排到前面, 不再全表扫描", "current": "C", "frontier": "heap=[C:2,B:4]", "best": 2, "dist": {"A": 0, "B": 4, "C": 2}, "settled": ["A"], "activeEdges": []},
        {"line": 9, "phase": "C 让 B 从 4 变成 3, 新的 B:3 再入堆", "current": "C", "frontier": "B:3,E:9", "best": "B:3", "dist": {"A": 0, "B": 3, "C": 2, "E": 9}, "settled": ["A", "C"], "activeEdges": [["C", "B"], ["C", "E"]]},
        {"line": 8, "phase": "之后如果弹出旧的 B:4, 发现 B 已确定就跳过", "current": "B", "frontier": "旧记录", "best": "跳过", "dist": {"A": 0, "B": 3, "C": 2, "D": 8, "E": 9}, "settled": ["A", "C", "B"], "activeEdges": []},
        {"line": 10, "phase": "终点路径逐步稳定, 答案和朴素版一致", "current": "完成", "frontier": "-", "best": "完成", "dist": {"A": 0, "B": 3, "C": 2, "D": 8, "E": 9, "F": 11}, "settled": ["A", "B", "C", "D", "E", "F"], "path": [["A", "C"], ["C", "B"], ["B", "D"], ["D", "F"]], "activeEdges": []},
    ]
    return _build_path_demo(
        "Dijkstra_堆优化版",
        source,
        rows,
        "概念动画：堆优化把“找当前最短点”交给最小堆, 邻接表只遍历真实存在的边。",
        "dijkstra",
    )


def concept_demo_bellman_ford():
    source = [
        "算法: Bellman-Ford 负权边",
        "输入: 边集 edges, 起点 A",
        "输出: A 到各点的最短距离",
        "",
        "dist[A] = 0, 其他点 = ∞",
        "重复 V-1 轮:",
        "    遍历每一条边 u -> v",
        "    如果 dist[u] + w 更小, 更新 dist[v]",
        "再遍历一轮, 如果还能更新, 说明有负权环",
    ]
    nodes = [
        {"id": "A", "x": 0.13, "y": 0.50},
        {"id": "B", "x": 0.34, "y": 0.25},
        {"id": "C", "x": 0.60, "y": 0.20},
        {"id": "D", "x": 0.62, "y": 0.70},
        {"id": "E", "x": 0.38, "y": 0.74},
    ]
    edges = [
        ["A", "B", -1], ["A", "C", 4],
        ["B", "C", 3], ["B", "D", 2], ["B", "E", 2],
        ["D", "C", 5], ["D", "B", 1],
        ["E", "D", -3],
    ]
    rows = [
        {
            "line": 5,
            "phase": "先只知道 A 到自己是 0, 其他点都是 ∞",
            "current": "A",
            "frontier": "全部边",
            "best": 0,
            "nodes": nodes,
            "edges": edges,
            "dist": {"A": 0},
            "settled": [],
            "activeEdges": [],
        },
        {
            "line": 8,
            "phase": "第1轮从 A 出发, B 变成 -1, C 先变成 4",
            "current": "A",
            "frontier": "A->B,A->C",
            "best": "B=-1",
            "nodes": nodes,
            "edges": edges,
            "dist": {"A": 0, "B": -1, "C": 4},
            "activeEdges": [["A", "B"], ["A", "C"]],
        },
        {
            "line": 8,
            "phase": "继续扫 B 的边, C、D、E 都被改短",
            "current": "B",
            "frontier": "B->C,B->D,B->E",
            "best": "C=2",
            "nodes": nodes,
            "edges": edges,
            "dist": {"A": 0, "B": -1, "C": 2, "D": 1, "E": 1},
            "activeEdges": [["B", "C"], ["B", "D"], ["B", "E"]],
        },
        {
            "line": 8,
            "phase": "负权边 E->D=-3 生效, D 从 1 改成 -2",
            "current": "E",
            "frontier": "E->D",
            "best": "D=-2",
            "nodes": nodes,
            "edges": edges,
            "dist": {"A": 0, "B": -1, "C": 2, "D": -2, "E": 1},
            "activeEdges": [["E", "D"]],
        },
        {
            "line": 6,
            "phase": "再扫几轮, 没有新的点能变短, 答案稳定下来",
            "current": "-",
            "frontier": "全部边",
            "best": "稳定",
            "nodes": nodes,
            "edges": edges,
            "dist": {"A": 0, "B": -1, "C": 2, "D": -2, "E": 1},
            "path": [["A", "B"], ["B", "E"], ["E", "D"]],
            "activeEdges": [],
        },
        {
            "line": 9,
            "phase": "额外第 V 轮只是审计: 如果还能变短, 才说明有负权环",
            "current": "审计",
            "frontier": "全部边",
            "best": "无负权环",
            "nodes": nodes,
            "edges": edges,
            "dist": {"A": 0, "B": -1, "C": 2, "D": -2, "E": 1},
            "path": [["A", "B"], ["B", "E"], ["E", "D"]],
            "activeEdges": [],
        },
    ]
    return _build_path_demo(
        "BellmanFord_负权边",
        source,
        rows,
        "概念动画：Bellman-Ford 不急着确认哪个点最短, 而是反复扫描所有边, 直到没有距离能再变短。",
        "bellman",
    )


def concept_demo_spfa():
    source = [
        "算法: SPFA 队列优化",
        "输入: 带负权边的图, 起点 A",
        "输出: 起点到各点的最短距离",
        "",
        "dist[A] = 0, A 入队",
        "while 队列不空:",
        "    u = 出队",
        "    用 u 的出边松弛邻居 v",
        "    如果 v 变短且不在队列中, v 入队",
        "    入队次数过多则说明有负权环",
    ]
    nodes = [
        {"id": "A", "x": 0.13, "y": 0.50},
        {"id": "B", "x": 0.34, "y": 0.25},
        {"id": "C", "x": 0.60, "y": 0.20},
        {"id": "D", "x": 0.62, "y": 0.70},
        {"id": "E", "x": 0.38, "y": 0.74},
    ]
    edges = [
        ["A", "B", -1], ["A", "C", 4],
        ["B", "C", 3], ["B", "D", 2], ["B", "E", 2],
        ["D", "C", 5], ["D", "B", 1],
        ["E", "D", -3],
    ]
    rows = [
        {"line": 5, "phase": "A 入队, 队列里只有刚刚变短的起点", "current": "A", "frontier": "queue=[A]", "best": 0, "queue": ["A"], "nodes": nodes, "edges": edges, "dist": {"A": 0}, "settled": [], "activeEdges": []},
        {"line": 8, "phase": "A 出队, A->B=-1 和 A->C=4 让 B、C 入队", "current": "A", "frontier": "B,C", "best": "B=-1", "queue": ["B", "C"], "nodes": nodes, "edges": edges, "dist": {"A": 0, "B": -1, "C": 4}, "activeEdges": [["A", "B"], ["A", "C"]]},
        {"line": 8, "phase": "B 出队, C、D、E 都被 B 的出边改短", "current": "B", "frontier": "C,D,E", "best": "C=2", "queue": ["C", "D", "E"], "nodes": nodes, "edges": edges, "dist": {"A": 0, "B": -1, "C": 2, "D": 1, "E": 1}, "activeEdges": [["B", "C"], ["B", "D"], ["B", "E"]]},
        {"line": 8, "phase": "E 出队后, 负权边 E->D=-3 让 D 从 1 改成 -2", "current": "E", "frontier": "D", "best": "D=-2", "queue": ["C", "D"], "nodes": nodes, "edges": edges, "dist": {"A": 0, "B": -1, "C": 2, "D": -2, "E": 1}, "activeEdges": [["E", "D"]]},
        {"line": 8, "phase": "D 再出队检查 D 的出边, 但 C、B 都不会继续变短", "current": "D", "frontier": "C,B", "best": "稳定", "queue": ["C"], "nodes": nodes, "edges": edges, "dist": {"A": 0, "B": -1, "C": 2, "D": -2, "E": 1}, "activeEdges": [["D", "C"], ["D", "B"]]},
        {"line": 9, "phase": "队列清空, 没有负权环, 最短距离稳定", "current": "-", "frontier": "-", "best": "完成", "queue": [], "nodes": nodes, "edges": edges, "dist": {"A": 0, "B": -1, "C": 2, "D": -2, "E": 1}, "path": [["A", "B"], ["B", "E"], ["E", "D"]], "activeEdges": []},
    ]
    return _build_path_demo("SPFA_队列优化", source, rows, "概念动画：SPFA 只把刚刚变短的点放回队列, 用通知机制处理负权边。", "spfa")


def concept_demo_floyd_core():
    source = [
        "算法: Floyd-Warshall 核心",
        "输入: 距离矩阵 dist",
        "输出: 任意两点间的最短距离",
        "",
        "for k in 顶点:",
        "    for i in 顶点:",
        "        for j in 顶点:",
        "            dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])",
    ]
    row_labels = ["A", "B", "C", "D"]
    col_labels = ["A", "B", "C", "D"]
    rows = [
        {
            "line": 1,
            "active": [-1, -1],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "grid": [
                [0, 5, "∞", 10],
                ["∞", 0, 3, "∞"],
                ["∞", "∞", 0, 1],
                ["∞", "∞", "∞", 0],
            ],
            "best": "直达边",
            "phase": "先把直达距离放进表格, 不可直达的位置写 ∞",
            "subtitle": "每一格 dist[i][j] 表示 i 到 j 的当前最短距离",
        },
        {
            "line": 8,
            "active": [0, 2],
            "refs": [[0, 1], [1, 2]],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "grid": [
                [0, 5, 8, 10],
                ["∞", 0, 3, "∞"],
                ["∞", "∞", 0, 1],
                ["∞", "∞", "∞", 0],
            ],
            "best": 8,
            "phase": "允许 B 当中转站: A->B->C = 5+3, 所以 A 到 C 从 ∞ 变成 8",
            "formula": "dist[A][C] = min(∞, 5 + 3) = 8",
            "badges": ["中转站 B"],
        },
        {
            "line": 8,
            "active": [0, 3],
            "refs": [[0, 2], [2, 3]],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "grid": [
                [0, 5, 8, 9],
                ["∞", 0, 3, "∞"],
                ["∞", "∞", 0, 1],
                ["∞", "∞", "∞", 0],
            ],
            "best": 9,
            "phase": "允许 C 当中转站: A->C->D = 8+1, 比直达 10 更短",
            "formula": "dist[A][D] = min(10, 8 + 1) = 9",
            "badges": ["中转站 C"],
        },
        {
            "line": 8,
            "active": [1, 3],
            "refs": [[1, 2], [2, 3]],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "grid": [
                [0, 5, 8, 9],
                ["∞", 0, 3, 4],
                ["∞", "∞", 0, 1],
                ["∞", "∞", "∞", 0],
            ],
            "best": 4,
            "phase": "B 到 D 也可以经 C 中转, 从不可达变成 4",
            "formula": "dist[B][D] = min(∞, 3 + 1) = 4",
            "badges": ["中转站 C"],
        },
        {
            "line": 8,
            "active": [-1, -1],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "grid": [
                [0, 5, 8, 9],
                ["∞", 0, 3, 4],
                ["∞", "∞", 0, 1],
                ["∞", "∞", "∞", 0],
            ],
            "best": "完成",
            "phase": "所有中转站都试过后, 表格里就是任意两点的最短距离",
        },
    ]
    return _build_dp_table_demo(
        "FloydWarshall_核心",
        source,
        rows,
        "概念动画：Floyd 的核心不是走一条路, 而是不断问: 加一个中转站会不会更短?",
    )


def concept_demo_floyd_init():
    source = [
        "算法: Floyd 初始化",
        "输入: 邻接矩阵 graph",
        "输出: 初始距离矩阵 dist",
        "",
        "如果 i == j: dist[i][j] = 0",
        "否则如果 i 到 j 有边: dist[i][j] = graph[i][j]",
        "否则: dist[i][j] = ∞",
    ]
    row_labels = ["0", "1", "2", "3", "4"]
    col_labels = ["0", "1", "2", "3", "4"]
    empty = [[None, None, None, None, None] for _ in range(5)]
    diagonal = [
        [0, None, None, None, None],
        [None, 0, None, None, None],
        [None, None, 0, None, None],
        [None, None, None, 0, None],
        [None, None, None, None, 0],
    ]
    row0 = [
        [0, 3, 8, "∞", -4],
        [None, 0, None, None, None],
        [None, None, 0, None, None],
        [None, None, None, 0, None],
        [None, None, None, None, 0],
    ]
    direct_edges = [
        [0, 3, 8, "∞", -4],
        ["∞", 0, "∞", 1, 7],
        ["∞", 4, 0, "∞", "∞"],
        [2, "∞", -5, 0, "∞"],
        ["∞", "∞", "∞", 6, 0],
    ]
    rows = [
        {
            "line": 1,
            "active": [-1, -1],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "grid": empty,
            "best": "空表",
            "phase": "先准备一张 V×V 表: 每一格回答“从 i 到 j 多远”",
            "subtitle": "初始化阶段只负责把已知事实填进去",
        },
        {
            "line": 5,
            "active": [2, 2],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "grid": diagonal,
            "best": 0,
            "phase": "自己到自己不用走, 对角线全部填 0",
            "formula": "dist[i][i] = 0",
        },
        {
            "line": 6,
            "active": [0, 4],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "grid": row0,
            "best": -4,
            "phase": "有直达边就抄边权: 0->1 是 3, 0->2 是 8, 0->4 是 -4",
            "formula": "dist[0][4] = graph[0][4] = -4",
        },
        {
            "line": 6,
            "active": [3, 2],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "grid": direct_edges,
            "best": -5,
            "phase": "所有直达边都填完, 没有边的位置统一写 ∞",
            "formula": "dist[3][2] = graph[3][2] = -5",
        },
        {
            "line": 7,
            "active": [-1, -1],
            "rowLabels": row_labels,
            "colLabels": col_labels,
            "grid": direct_edges,
            "best": "初始化完成",
            "phase": "这张表就是 Floyd 的起跑线, 后面每轮只是在它上面继续改短",
        },
    ]
    return _build_dp_table_demo(
        "FloydWarshall_初始化",
        source,
        rows,
        "概念动画：初始化先把自己、直达边、不可达三种情况分清楚, 后面的中转更新才不会乱。",
    )


def concept_demo_astar():
    source = [
        "算法: A* 启发式搜索",
        "输入: 起点 A, 终点 F, 启发函数 h",
        "输出: 一条代价较小的路径",
        "",
        "g 表示已走代价, h 表示离目标的估计",
        "f = g + h",
        "每次从 open set 里取 f 最小的点",
        "展开它的邻居并更新 g/f",
        "取到终点时结束",
    ]
    rows = [
        {"line": 6, "phase": "A 的 g=0, h 估计还要走 10, f=10", "current": "A", "frontier": "A", "best": "f=10", "open": ["A"], "dist": {"A": 0}, "heuristic": {"A": 10, "B": 7, "C": 6, "D": 3, "E": 2, "F": 0}, "activeEdges": []},
        {"line": 8, "phase": "展开 A, B 和 C 进入 open set", "current": "A", "frontier": "B,C", "best": "C:8", "open": ["B", "C"], "dist": {"A": 0, "B": 4, "C": 2}, "heuristic": {"A": 10, "B": 7, "C": 6, "D": 3, "E": 2, "F": 0}, "activeEdges": [["A", "B"], ["A", "C"]]},
        {"line": 7, "phase": "C 的 f=2+6=8, 比 B 更有希望", "current": "C", "frontier": "B,E", "best": "B:10", "open": ["B", "E"], "dist": {"A": 0, "B": 3, "C": 2, "E": 9}, "heuristic": {"A": 10, "B": 7, "C": 6, "D": 3, "E": 2, "F": 0}, "activeEdges": [["C", "B"], ["C", "E"]]},
        {"line": 8, "phase": "B 的 f=3+7=10, 继续向 D 推进", "current": "B", "frontier": "D,E", "best": "D:11", "open": ["D", "E"], "dist": {"A": 0, "B": 3, "C": 2, "D": 8, "E": 9}, "heuristic": {"A": 10, "B": 7, "C": 6, "D": 3, "E": 2, "F": 0}, "activeEdges": [["B", "D"]]},
        {"line": 8, "phase": "D 和 E 的 f 都是 11, D 可以直接看到 F", "current": "D", "frontier": "F,E", "best": "F:11", "open": ["F", "E"], "dist": {"A": 0, "B": 3, "C": 2, "D": 8, "E": 9, "F": 11}, "heuristic": {"A": 10, "B": 7, "C": 6, "D": 3, "E": 2, "F": 0}, "activeEdges": [["D", "F"], ["D", "E"]]},
        {"line": 9, "phase": "取出终点 F, 搜索结束", "current": "F", "frontier": "-", "best": 11, "open": [], "dist": {"A": 0, "B": 3, "C": 2, "D": 8, "E": 9, "F": 11}, "heuristic": {"A": 10, "B": 7, "C": 6, "D": 3, "E": 2, "F": 0}, "path": [["A", "C"], ["C", "B"], ["B", "D"], ["D", "F"]], "activeEdges": [["D", "F"]]},
    ]
    return _build_path_demo("AStar_启发搜索", source, rows, "概念动画：A* 用 f=g+h 让搜索更偏向目标方向。", "astar")


def concept_demo_bfs_islands():
    source = [
        "算法: 岛屿数量 BFS",
        "输入: 由 0/1 组成的网格",
        "输出: 岛屿数量",
        "",
        "扫描每个格子:",
        "    如果遇到陆地 1:",
        "        岛屿数 +1",
        "        把它入队, 并立刻标记为水",
        "        BFS 向四周扩散, 淹掉同一座岛",
    ]
    grid = [
        "11000",
        "11000",
        "00100",
        "00011",
    ]
    states = [
        (5, "扫描到 (0,0), 发现第一座岛", [0, 0], [[0, 0]], [[0, 0]], 1),
        (8, "从队首向四周扩散, (0,1) 和 (1,0) 入队时立刻标记", [0, 0], [[0, 1], [1, 0]], [[0, 0], [0, 1], [1, 0]], 1),
        (8, "继续扩散到 (1,1), 第一座岛被全部淹掉", [1, 0], [[1, 1]], [[0, 0], [0, 1], [1, 0], [1, 1]], 1),
        (6, "扫描到 (2,2), 这是第二座孤岛", [2, 2], [[2, 2]], [[0, 0], [0, 1], [1, 0], [1, 1], [2, 2]], 2),
        (6, "扫描到 (3,3), 发现第三座岛", [3, 3], [[3, 3]], [[0, 0], [0, 1], [1, 0], [1, 1], [2, 2], [3, 3]], 3),
        (8, "扩散到 (3,4), 第三座岛也处理完", [3, 4], [], [[0, 0], [0, 1], [1, 0], [1, 1], [2, 2], [3, 3], [3, 4]], 3),
    ]
    steps = []
    for idx, (line, phase, active, queue, visited, count) in enumerate(states):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "count": count,
                "queue": " → ".join(f"({r},{c})" for r, c in queue) if queue else "空",
                "phase": phase,
                "concept": {
                    "kind": "flood_fill",
                    "title": "岛屿数量 BFS",
                    "subtitle": "遇到陆地就从那里扩散, 把同一座岛全部标记掉",
                    "grid": grid,
                    "active": active,
                    "queue": queue,
                    "visited": visited,
                    "count": count,
                },
            },
        })
    return _build_simple_concept_algo(
        "BFS搜索框架",
        source,
        steps,
        ["count", "queue", "phase"],
        "概念动画：BFS 像水波纹一样扩散, 入队时标记能避免重复入队。",
    )


def concept_demo_permutation_used():
    source = [
        "算法: 全排列 used 数组写法",
        "输入: [1, 2, 3]",
        "",
        "backtrack(depth):",
        "    如果 depth == n: 输出当前排列",
        "    枚举每个数字:",
        "        如果没用过:",
        "            选择它, 标记 used",
        "            递归下一格",
        "            撤销标记",
    ]
    nodes = [
        {"id": "root", "label": "_ _ _", "x": 0.50, "y": 0.08, "bound": "可选", "value": 0},
        {"id": "1", "label": "1 _ _", "x": 0.25, "y": 0.30, "bound": "used[1]", "value": 1},
        {"id": "2", "label": "2 _ _", "x": 0.50, "y": 0.30, "bound": "待试", "value": 1},
        {"id": "3", "label": "3 _ _", "x": 0.75, "y": 0.30, "bound": "待试", "value": 1},
        {"id": "12", "label": "1 2 _", "x": 0.17, "y": 0.54, "bound": "used[2]", "value": 2},
        {"id": "13", "label": "1 3 _", "x": 0.33, "y": 0.54, "bound": "used[3]", "value": 2},
        {"id": "123", "label": "1 2 3", "x": 0.14, "y": 0.78, "bound": "解", "value": 3},
        {"id": "132", "label": "1 3 2", "x": 0.36, "y": 0.78, "bound": "解", "value": 3},
    ]
    edges = [["root", "1"], ["root", "2"], ["root", "3"], ["1", "12"], ["1", "13"], ["12", "123"], ["13", "132"]]
    states = [
        (4, "三个空位, 每一层填一个位置", "root", ["root"], [], "", ["1", "2", "3"], [{"label": "depth", "value": 0}, {"label": "used", "value": "---"}, {"label": "输出", "value": 0}]),
        (7, "第 1 位选择 1, used[1] 变成真", "1", ["root", "1", "2", "3"], [], "", ["12", "13"], [{"label": "depth", "value": 1}, {"label": "used", "value": "1"}, {"label": "当前", "value": "1__"}]),
        (7, "第 2 位选择 2, 继续向下", "12", ["root", "1", "2", "3", "12", "13"], [], "", ["123", "13"], [{"label": "depth", "value": 2}, {"label": "used", "value": "1,2"}, {"label": "当前", "value": "12_"}]),
        (5, "填满三个位置, 输出 123", "123", ["root", "1", "2", "3", "12", "13", "123"], [], "123", ["13"], [{"label": "输出", "value": "123"}, {"label": "回溯", "value": "撤销3"}, {"label": "继续", "value": "是"}]),
        (9, "撤销第 2 位的 2, 改试 3", "13", ["root", "1", "2", "3", "12", "13", "123"], [], "123", ["132"], [{"label": "depth", "value": 2}, {"label": "used", "value": "1,3"}, {"label": "当前", "value": "13_"}]),
        (5, "输出 132 后, 回到更上层继续 2 开头、3 开头", "132", [n["id"] for n in nodes], [], "132", ["2", "3"], [{"label": "已看", "value": 2}, {"label": "总数", "value": "3!"}, {"label": "机制", "value": "撤销"}]),
    ]
    steps = _branch_bound_steps("全排列 used 数组", "填空位: 选择一个没用过的数字, 递归回来再撤销", nodes, edges, states)
    for step in steps:
        step["vars"]["concept"]["pruneMode"] = "constraint"
        step["vars"]["concept"]["boundLabel"] = "标记"
        step["vars"]["concept"]["valueLabel"] = "深度"
    return _build_simple_concept_algo("全排列_基础版", source, steps, ["best", "queue", "phase"], "概念动画：全排列就是“选择、递归、撤销”反复发生。")


def concept_demo_permutation_swap():
    source = [
        "算法: 全排列 swap 写法",
        "输入: [1, 2, 3]",
        "",
        "permute(l):",
        "    如果 l 到末尾: 输出数组",
        "    for i = l..r:",
        "        swap(arr[l], arr[i])",
        "        permute(l + 1)",
        "        swap(arr[l], arr[i])  // 换回来",
    ]
    nodes = [
        {"id": "root", "label": "123", "x": 0.50, "y": 0.08, "bound": "l=0", "value": 0},
        {"id": "123a", "label": "123", "x": 0.24, "y": 0.30, "bound": "换1", "value": 1},
        {"id": "213", "label": "213", "x": 0.50, "y": 0.30, "bound": "换2", "value": 1},
        {"id": "321", "label": "321", "x": 0.76, "y": 0.30, "bound": "换3", "value": 1},
        {"id": "123", "label": "123", "x": 0.15, "y": 0.55, "bound": "解", "value": 3},
        {"id": "132", "label": "132", "x": 0.32, "y": 0.55, "bound": "解", "value": 3},
        {"id": "213out", "label": "213", "x": 0.45, "y": 0.78, "bound": "解", "value": 3},
        {"id": "231", "label": "231", "x": 0.62, "y": 0.78, "bound": "解", "value": 3},
    ]
    edges = [["root", "123a"], ["root", "213"], ["root", "321"], ["123a", "123"], ["123a", "132"], ["213", "213out"], ["213", "231"]]
    states = [
        (4, "从 l=0 开始, 当前数组是 123", "root", ["root"], [], "", ["123a", "213", "321"], [{"label": "l", "value": 0}, {"label": "数组", "value": "123"}, {"label": "输出", "value": 0}]),
        (6, "i=0, 自己和自己交换, 固定第一位 1", "123a", ["root", "123a", "213", "321"], [], "", ["123", "132"], [{"label": "l", "value": 1}, {"label": "固定", "value": 1}, {"label": "数组", "value": "123"}]),
        (5, "后两位也固定完, 输出 123", "123", ["root", "123a", "213", "321", "123", "132"], [], "123", ["132"], [{"label": "输出", "value": "123"}, {"label": "回溯", "value": "swap回来"}, {"label": "继续", "value": "是"}]),
        (6, "交换后两位, 输出 132", "132", ["root", "123a", "213", "321", "123", "132"], [], "132", ["213"], [{"label": "输出", "value": "132"}, {"label": "数组", "value": "132"}, {"label": "顺序", "value": "非字典序"}]),
        (8, "第一层换成 2 开头, 后面继续同样过程", "213", [n["id"] for n in nodes if n["id"] not in {"213out", "231"}], [], "132", ["213out", "231"], [{"label": "l", "value": 1}, {"label": "固定", "value": 2}, {"label": "数组", "value": "213"}]),
        (5, "swap 写法省 used 数组, 但输出顺序不一定是字典序", "231", [n["id"] for n in nodes], [], "231", ["321"], [{"label": "已输出", "value": 4}, {"label": "空间", "value": "O(1)"}, {"label": "撤销", "value": "swap"}]),
    ]
    steps = _branch_bound_steps("全排列 swap 写法", "把当前要固定的位置和后面的元素轮流交换", nodes, edges, states)
    for step in steps:
        step["vars"]["concept"]["pruneMode"] = "constraint"
        step["vars"]["concept"]["boundLabel"] = "动作"
        step["vars"]["concept"]["valueLabel"] = "深度"
    return _build_simple_concept_algo("全排列_优化版", source, steps, ["best", "queue", "phase"], "概念动画：swap 写法用数组原地交换来表达选择和撤销。")


def concept_demo_subset_generation():
    source = [
        "算法: 子集生成",
        "输入: [1, 2, 3]",
        "",
        "dfs(index):",
        "    如果 index == n: 输出当前子集",
        "    不选 a[index], 递归",
        "    选 a[index], 放进 subset",
        "    递归",
        "    撤销这次选择",
    ]
    nodes = [
        {"id": "root", "label": "开始", "x": 0.50, "y": 0.08, "bound": "i=0", "value": 0},
        {"id": "no1", "label": "不选1", "x": 0.30, "y": 0.30, "bound": "{}", "value": 1},
        {"id": "yes1", "label": "选1", "x": 0.70, "y": 0.30, "bound": "{1}", "value": 1},
        {"id": "no12", "label": "不选2", "x": 0.18, "y": 0.54, "bound": "{}", "value": 2},
        {"id": "yes2", "label": "选2", "x": 0.42, "y": 0.54, "bound": "{2}", "value": 2},
        {"id": "yes1no2", "label": "{1}", "x": 0.60, "y": 0.54, "bound": "{1}", "value": 2},
        {"id": "yes12", "label": "{1,2}", "x": 0.82, "y": 0.54, "bound": "{1,2}", "value": 2},
        {"id": "empty", "label": "{}", "x": 0.14, "y": 0.78, "bound": "解", "value": 3},
        {"id": "three", "label": "{3}", "x": 0.33, "y": 0.78, "bound": "解", "value": 3},
        {"id": "onetwo", "label": "{1,2}", "x": 0.73, "y": 0.78, "bound": "解", "value": 3},
        {"id": "onetwothree", "label": "{1,2,3}", "x": 0.91, "y": 0.78, "bound": "解", "value": 3},
    ]
    edges = [["root", "no1"], ["root", "yes1"], ["no1", "no12"], ["no1", "yes2"], ["yes1", "yes1no2"], ["yes1", "yes12"], ["no12", "empty"], ["no12", "three"], ["yes12", "onetwo"], ["yes12", "onetwothree"]]
    states = [
        (4, "每个元素都有两个选择: 不选 / 选", "root", ["root"], [], "", ["no1", "yes1"], [{"label": "index", "value": 0}, {"label": "子集", "value": "{}"}, {"label": "输出", "value": 0}]),
        (6, "先走“不选 1”的分支", "no1", ["root", "no1", "yes1"], [], "", ["no12", "yes2", "yes1"], [{"label": "index", "value": 1}, {"label": "子集", "value": "{}"}, {"label": "选择", "value": "不选"}]),
        (6, "再不选 2, 子集仍然是空", "no12", ["root", "no1", "yes1", "no12", "yes2"], [], "", ["empty", "three", "yes2"], [{"label": "index", "value": 2}, {"label": "子集", "value": "{}"}, {"label": "下一步", "value": "看3"}]),
        (5, "三个元素都考虑完, 输出空集", "empty", ["root", "no1", "yes1", "no12", "yes2", "empty", "three"], [], "empty", ["three", "yes2"], [{"label": "输出", "value": "{}"}, {"label": "回溯", "value": "是"}, {"label": "继续", "value": "选3"}]),
        (7, "回到元素 3, 改走“选 3”的分支", "three", ["root", "no1", "yes1", "no12", "yes2", "empty", "three"], [], "three", ["yes2", "yes1"], [{"label": "输出", "value": "{3}"}, {"label": "路径", "value": "001"}, {"label": "含义", "value": "选/不选"}]),
        (7, "右侧分支会得到包含 1、2 的子集", "yes12", [n["id"] for n in nodes if n["id"] not in {"onetwo", "onetwothree"}], [], "three", ["onetwo", "onetwothree"], [{"label": "子集", "value": "{1,2}"}, {"label": "index", "value": 2}, {"label": "选择", "value": "继续"}]),
        (5, "最终会得到 2^3 = 8 个子集", "onetwothree", [n["id"] for n in nodes], [], "onetwothree", [], [{"label": "总数", "value": "2^n"}, {"label": "n=3", "value": 8}, {"label": "完成", "value": "是"}]),
    ]
    steps = _branch_bound_steps("子集生成", "每个元素只问一句: 选还是不选", nodes, edges, states)
    for step in steps:
        step["vars"]["concept"]["pruneMode"] = "constraint"
        step["vars"]["concept"]["boundLabel"] = "当前"
        step["vars"]["concept"]["valueLabel"] = "深度"
    return _build_simple_concept_algo("子集生成", source, steps, ["best", "queue", "phase"], "概念动画：子集生成是一棵二叉选择树, 每层对应一个元素。")


def concept_demo_n_queens_space_check():
    source = [
        "算法: N皇后安全性检查",
        "输入: 已放好的 queens 数组, 候选位置 (row, col)",
        "",
        "检查之前每一行 i:",
        "    如果 queens[i] == col: 同列冲突",
        "    如果 |row-i| == |col-queens[i]|: 对角线冲突",
        "都不冲突才安全",
    ]
    states = [
        (4, "已知第 0 行在 (0,0), 第 1 行在 (1,2)", 2, [0, 2, -1, -1], [2, 1], [[1, 2], [2, 1]], 0),
        (5, "候选 (2,1) 与 (1,2) 行差=1、列差=1, 对角线冲突", 2, [0, 2, -1, -1], [2, 1], [[1, 2], [2, 1]], 0),
        (4, "改试 (2,3), 先看同列: 没有皇后在第 3 列", 2, [0, 2, -1, -1], [2, 3], [], 0),
        (5, "(2,3) 与 (1,2) 仍然行差=1、列差=1, 也是对角线冲突", 2, [0, 2, -1, -1], [2, 3], [[1, 2], [2, 3]], 0),
        (6, "公式本身就是空间优化: 只存每行皇后列号 queens[i]", 2, [0, 2, -1, -1], [2, 3], [[1, 2], [2, 3]], 0),
    ]
    return _build_n_queens_demo("N皇后_空间优化", source, states, "概念动画：不用保存整张棋盘, queens[i] 就足够检查列和对角线。", "basic")


def concept_demo_n_queens_basic():
    source = [
        "算法: N皇后回溯",
        "输入: 棋盘大小 n",
        "输出: 所有合法摆法",
        "",
        "函数 backtrack(row):",
        "    如果 row == n: 记录一个解",
        "    对当前行的每一列 col:",
        "        如果 (row, col) 安全:",
        "            放下皇后",
        "            backtrack(row + 1)",
        "            拿起皇后, 尝试下一列",
    ]
    states = [
        (5, "从第 0 行开始, 每行只放一个皇后", 0, [-1, -1, -1, -1], [0, 0], [], 0),
        (8, "第 0 行选择第 1 列", 1, [1, -1, -1, -1], [0, 1], [], 0),
        (7, "第 1 行尝试第 0 列, 同一对角线冲突", 1, [1, -1, -1, -1], [1, 0], [[0, 1], [1, 0]], 0),
        (8, "第 1 行选择第 3 列", 2, [1, 3, -1, -1], [1, 3], [], 0),
        (7, "第 2 行已经没有安全位置, 回退", 2, [1, 3, -1, -1], [2, 0], [[0, 1], [2, 0]], 0),
        (10, "撤销第 1 行, 换下一条路", 1, [1, -1, -1, -1], [1, 3], [], 0),
        (8, "另一条分支逐行成立", 3, [2, 0, 3, -1], [2, 3], [], 0),
        (6, "找到一个完整解: [2,0,3,1]", 4, [2, 0, 3, 1], None, [], 1),
    ]
    return _build_n_queens_demo("N皇后_基础版", source, states, "用 4 皇后缩小问题, 看懂回溯的尝试、冲突和撤销。", "basic")


def concept_demo_n_queens_diagonal():
    source = [
        "算法: N皇后对角线优化",
        "输入: 棋盘大小 n",
        "输出: 所有合法摆法",
        "",
        "列冲突: col[col]",
        "主对角线: diag1[row - col + n - 1]",
        "副对角线: diag2[row + col]",
        "",
        "函数 backtrack(row):",
        "    枚举 col",
        "    如果三张表都没被占用:",
        "        标记 col/diag1/diag2, 放皇后",
        "        递归下一行, 回来后取消标记",
    ]
    states = [
        (5, "三张表把安全检查从逐个比较变成直接查询", 0, [-1, -1, -1, -1], [0, 0], [], 0),
        (11, "放在 (0,1), 标记列 1 和两条对角线", 1, [1, -1, -1, -1], [0, 1], [], 0),
        (10, "(1,0) 的副对角线已被占用", 1, [1, -1, -1, -1], [1, 0], [[0, 1], [1, 0]], 0),
        (11, "放在 (1,3), 继续向下一行", 2, [1, 3, -1, -1], [1, 3], [], 0),
        (10, "第 2 行全被列或对角线挡住, 立即剪枝", 2, [1, 3, -1, -1], [2, 2], [[0, 1], [1, 3], [2, 2]], 0),
        (12, "取消标记, 回到上层换列", 1, [1, -1, -1, -1], [1, 3], [], 0),
        (11, "有效分支: [2,0,3,1]", 4, [2, 0, 3, 1], None, [], 1),
    ]
    return _build_n_queens_demo("N皇后_对角线优化", source, states, "三张布尔表让冲突判断变成 O(1), 搜索树更快被剪掉。", "diagonal")


def _build_n_queens_demo(title, source, states, output, mode):
    steps = []
    for idx, (line, phase, row, queens, current, conflicts, solutions) in enumerate(states):
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "row": row,
                "solutions": solutions,
                "phase": phase,
                "concept": {
                    "kind": "n_queens",
                    "mode": mode,
                    "n": 4,
                    "queens": queens,
                    "current": current,
                    "conflicts": conflicts,
                    "solutions": solutions,
                },
            },
        })
    return {
        "title": title,
        "source": source,
        "important_vars": {"row": "当前行", "solutions": "解法数", "phase": "阶段"},
        "track_vars": {"primary": ["row", "solutions", "phase"], "secondary": []},
        "var_classes": {
            "row": {"category": "primary", "type": "scalar"},
            "solutions": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": output}],
        "steps": steps,
    }


def concept_demo_sudoku():
    source = [
        "算法: 数独回溯",
        "输入: 9x9 棋盘, 空格记为 0",
        "输出: 一个合法填法",
        "",
        "寻找下一个空格",
        "枚举数字 1..9",
        "    如果行、列、九宫格都不冲突:",
        "        填入这个数字",
        "        继续递归",
        "        如果失败, 撤销这个数字",
        "所有空格填完, 数独完成",
    ]
    givens = [
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9],
    ]
    states = [
        (4, "先找第一个空格", [0, 2], 1, []),
        (6, "尝试 1: 行、列、宫都不冲突", [0, 2], 1, []),
        (7, "填入 1, 继续往后走", [0, 2], 1, [[0, 2, 1]]),
        (6, "下一个空格尝试 2, 同一行已经有 2 的候选冲突", [0, 3], 2, [[0, 2, 1]], [[0, 3], [0, 2]]),
        (7, "换成 6 可以通过检查", [0, 3], 6, [[0, 2, 1], [0, 3, 6]]),
        (9, "后面走不通, 撤销刚才的选择", [0, 3], 6, [[0, 2, 1]]),
        (7, "换另一个候选继续搜索", [0, 3], 2, [[0, 2, 1], [0, 3, 2]]),
        (10, "所有格子填完: 每一步都满足局部规则", None, None, [
            [0, 2, 4], [0, 3, 6], [0, 5, 8], [0, 6, 9], [0, 7, 1], [0, 8, 2],
            [1, 1, 7], [1, 2, 2], [1, 6, 3], [1, 7, 4], [1, 8, 8],
        ]),
    ]
    steps = []
    for idx, state in enumerate(states):
        line, phase, cell, try_value, placed = state[:5]
        conflicts = state[5] if len(state) > 5 else []
        board = [row[:] for row in givens]
        for r, c, v in placed:
            board[r][c] = v
        steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "row": cell[0] if cell else 9,
                "col": cell[1] if cell else 9,
                "try": try_value if try_value else 0,
                "phase": phase,
                "concept": {
                    "kind": "sudoku",
                    "board": board,
                    "givens": givens,
                    "cell": cell,
                    "try": try_value,
                    "conflicts": conflicts,
                    "done": cell is None,
                },
            },
        })
    return {
        "title": "数独求解",
        "source": source,
        "important_vars": {"row": "行", "col": "列", "try": "候选", "phase": "阶段"},
        "track_vars": {"primary": ["row", "col", "try", "phase"], "secondary": []},
        "var_classes": {
            "row": {"category": "primary", "type": "scalar"},
            "col": {"category": "primary", "type": "scalar"},
            "try": {"category": "primary", "type": "scalar"},
            "phase": {"category": "primary", "type": "scalar"},
            "concept": {"category": "secondary", "type": "concept"},
        },
        "initial_data": {},
        "program_output": [{"after_step": len(steps), "text": "概念动画：数独回溯就是“找空格 → 试数字 → 冲突就撤销”。"}],
        "steps": steps,
    }


def concept_demos_ch22():
    """第22章没有C源码，这里用概念动画数据驱动 Canvas 演示。"""
    convex_source = [
        "算法: 计算几何 - Graham扫描求凸包",
        "输入: 平面上的点集 points",
        "输出: 凸包顶点序列",
        "",
        "1. 找到 y 坐标最小的点 p0",
        "2. 其余点按相对 p0 的极角排序",
        "3. 将 p0 和前两个点入栈",
        "4. 依次扫描其余点 p",
        "5. 如果栈顶两点到 p 构成右转, 弹出栈顶",
        "6. 将 p 入栈",
        "7. 栈中点围成凸包",
    ]
    points = [
        [90, 218], [142, 128], [196, 190], [246, 84],
        [314, 152], [372, 80], [446, 198], [382, 252],
        [276, 236], [184, 282], [112, 260],
    ]
    convex_states = [
        (5, "先找最下方的点 p0", [9], 9, [], []),
        (6, "按极角排序, 扫描线从 p0 开始转动", [9, 10, 0], 10, [], []),
        (7, "前两个候选点入栈", [9, 10, 0], 0, [[9, 10], [10, 0]], []),
        (8, "扫描下一个点", [9, 10, 0, 1], 1, [[9, 10], [10, 0], [0, 1]], []),
        (9, "出现右转, 点 0 被弹出", [9, 10, 1], 1, [[9, 10], [10, 1]], [0]),
        (10, "继续扫描, 栈保持向左转", [9, 10, 1, 3], 3, [[9, 10], [10, 1], [1, 3]], []),
        (10, "点 2 凹进去了, 不在外壳上", [9, 10, 1, 3], 4, [[9, 10], [10, 1], [1, 3]], [2]),
        (10, "扫描右上方边界点", [9, 10, 1, 3, 5], 5, [[9, 10], [10, 1], [1, 3], [3, 5]], []),
        (10, "右侧外壳闭合", [9, 10, 1, 3, 5, 6], 6, [[9, 10], [10, 1], [1, 3], [3, 5], [5, 6]], []),
        (10, "底部边界入栈", [9, 10, 1, 3, 5, 6, 7], 7, [[9, 10], [10, 1], [1, 3], [3, 5], [5, 6], [6, 7]], []),
        (11, "最终凸包: 橡皮筋圈住所有点", [9, 10, 1, 3, 5, 6, 7], None, [[9, 10], [10, 1], [1, 3], [3, 5], [5, 6], [6, 7], [7, 9]], []),
    ]
    convex_steps = []
    for idx, (line, phase, stack, current, hull_edges, popped) in enumerate(convex_states):
        convex_steps.append({
            "step": idx,
            "line": line,
            "type": "exec",
            "vars": {
                "phase": phase,
                "concept": {
                    "kind": "convex_hull",
                    "points": points,
                    "stack": stack,
                    "current": current,
                    "hullEdges": hull_edges,
                    "popped": popped,
                },
            },
        })

    euclid_source = [
        "算法: 数论 - 欧几里得算法(辗转相除法)",
        "输入: 两个正整数 a 和 b",
        "输出: gcd(a, b)",
        "",
        "函数 gcd(a, b):",
        "    当 b != 0:",
        "        a, b = b, a % b",
        "    返回 a",
        "",
        "核心: gcd(a, b) = gcd(b, a % b)",
    ]
    euclid_pairs = [
        (1071, 462, 147, "1071 = 462 × 2 + 147"),
        (462, 147, 21, "462 = 147 × 3 + 21"),
        (147, 21, 0, "147 = 21 × 7 + 0"),
        (21, 0, 0, "b 为 0, 答案就是 a"),
    ]
    euclid_steps = []
    for idx, (a, b, r, expr) in enumerate(euclid_pairs):
        euclid_steps.append({
            "step": idx,
            "line": 6 if b else 8,
            "type": "exec",
            "vars": {
                "a": a,
                "b": b,
                "r": r,
                "phase": expr,
                "concept": {
                    "kind": "euclid",
                    "a": a,
                    "b": b,
                    "r": r,
                    "expr": expr,
                    "done": b == 0,
                    "round": idx + 1,
                },
            },
        })

    return {
        "22_2_1_Graham扫描求凸包": {
            "title": "计算几何：Graham扫描求凸包",
            "source": convex_source,
            "important_vars": {"phase": "阶段"},
            "track_vars": {"primary": ["phase"], "secondary": []},
            "var_classes": {
                "phase": {"category": "primary", "type": "scalar"},
                "concept": {"category": "secondary", "type": "concept"},
            },
            "initial_data": {},
            "program_output": [{"after_step": len(convex_steps), "text": "概念动画：用一根橡皮筋圈住所有点。"}],
            "steps": convex_steps,
        },
        "22_2_2_欧几里得算法": {
            "title": "数论：欧几里得算法",
            "source": euclid_source,
            "important_vars": {"a": "数字", "b": "数字", "r": "余数", "phase": "阶段"},
            "track_vars": {"primary": ["a", "b", "r", "phase"], "secondary": []},
            "var_classes": {
                "a": {"category": "primary", "type": "scalar"},
                "b": {"category": "primary", "type": "scalar"},
                "r": {"category": "primary", "type": "scalar"},
                "phase": {"category": "primary", "type": "scalar"},
                "concept": {"category": "secondary", "type": "concept"},
            },
            "initial_data": {},
            "program_output": [{"after_step": len(euclid_steps), "text": "gcd(1071, 462) = 21"}],
            "steps": euclid_steps,
        },
    }


def generate_index_html(chapters_with_content):
    """生成首页"""
    items = []
    for ch in chapters_with_content:
        num = ch['num']
        title = ch['title']
        href = f"chapters/ch{num:02d}.html"
        items.append(f'''  <a class="ch-item" href="{href}">
    <span class="ch-num">第{num}章</span>
    <span class="ch-title">{title}</span>
    <span class="ch-count">{ch.get('algo_count', 0)} 个演示</span>
    <span class="ch-arrow">›</span>
  </a>''')
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>大话算法 — 交互式算法学习</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, 'PingFang SC', 'Noto Sans SC', sans-serif; background: #1e2336; color: #abb2bf; min-height: 100vh; overflow: hidden; }}
.hero {{ text-align: center; padding: 40px 20px 24px; }}
.hero h1 {{ font-size: 40px; color: #4a8fd4; margin-bottom: 10px; }}
.hero p {{ font-size: 17px; color: #7f848e; max-width: 600px; margin: 0 auto; line-height: 1.6; }}
.hero .badge {{ display: inline-block; background: #233d5c; color: #c8cdd5; font-size: 12px; padding: 3px 10px; border-radius: 12px; margin-top: 12px; }}
.chapters {{ max-width: 1200px; margin: 0 auto; padding: 0 20px 20px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }}
.ch-item {{ display: flex; align-items: center; gap: 14px; background: #1a1f30; border: 1px solid #2a3040; border-radius: 8px; padding: 12px 16px; text-decoration: none; color: #c8cdd5; transition: all 0.2s; font-size: 16px; }}
.ch-item:hover {{ background: #22283a; border-color: #3b4252; transform: translateX(4px); }}
.ch-num {{ font-size: 14px; color: #4a8fd4; font-weight: 600; min-width: 50px; }}
.ch-title {{ font-size: 15px; flex: 1; }}
.ch-count {{ font-size: 12px; color: #3b4252; }}
.ch-arrow {{ color: #2a3040; font-size: 18px; }}
.footer {{ text-align: center; padding: 20px; color: #3b4252; font-size: 12px; border-top: 1px solid #212636; }}
</style>
</head>
<body>
<div class="hero">
  <h1>📖 大话算法</h1>
  <p>每一步代码执行，每一个变量变化，都看得清清楚楚。<br>配合图书使用，零基础也能学算法。</p>
  <div class="badge">交互式演示 · 纯前端 · 无需安装</div>
</div>
<div class="chapters">
{chr(10).join(items)}
</div>
<div class="footer">大话算法 · 配合《大话算法》图书使用</div>
</body>
</html>'''


def main():
    with_traces = '--with-traces' in sys.argv

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TRACE_DIR.mkdir(parents=True, exist_ok=True)

    chapters_with_content = []
    site_index_chapters = []
    total_algos = 0

    for ch in CHAPTERS:
        print(f"扫描 第{ch['num']}章 {ch['title']}...")
        algos = scan_chapter(ch)
        if not algos:
            chapters_with_content.append({**ch, 'algo_count': 0})
            site_index_chapters.append({
                'id': ch['num'],
                'title': ch['title'],
                'algorithms': [],
            })
            continue

        # 生成章节HTML
        algos_json = json.dumps(algos, ensure_ascii=False, indent=2)
        # 确保JSON中的</script>不会破坏HTML
        algos_json = algos_json.replace('</script>', '<\\/script>')
        html = generate_chapter_html(ch, algos_json)
        out_file = OUT_DIR / f"ch{ch['num']:02d}.html"
        out_file.write_text(html, encoding='utf-8')

        total_algos += len(algos)
        chapters_with_content.append({**ch, 'algo_count': len(algos)})
        site_index_chapters.append({
            'id': ch['num'],
            'title': ch['title'],
            'algorithms': [
                {'key': key, 'title': value.get('title') or key}
                for key, value in algos.items()
            ],
        })
        print(f"  → {len(algos)} 个算法, 已生成 {out_file.name}")

    site_index = {
        'algorithmCount': total_algos,
        'chapterCount': len(site_index_chapters),
        'chapters': site_index_chapters,
    }
    site_data = 'window.ALGO_SITE_INDEX = ' + json.dumps(site_index, ensure_ascii=False, indent=2) + ';\n'
    (BASE / 'js' / 'site-data.js').write_text(site_data, encoding='utf-8')

    # 首页使用手工制作的学习地图（index.html），不再自动覆盖
    # index_html = generate_index_html(chapters_with_content)
    # (BASE / 'index.html').write_text(index_html, encoding='utf-8')

    print(f"\n✅ 完成! {len(chapters_with_content)} 章, {total_algos} 个算法演示")
    print(f"   首页: {BASE / 'index.html'} (手动维护)")
    print(f"   章节: {OUT_DIR}/")


if __name__ == '__main__':
    main()
