#!/usr/bin/env python3
"""
大话算法 v2 自动插桩器 — v3.0
==============================
功能：读入教学C源码，自动注入TRACE宏，编译运行，生成执行轨迹JSON。

核心原则：
  1. 行号 = 原始源码 1-indexed 行号（硬编码进 TRACE 宏参数）
  2. 变量 = 增量输出（每步只输出变化的变量）
  3. 智能跳步 = 大循环/递归只保留首尾，中间省略
  4. 进子函数 = 调用点插入 TRACE_ENTER，函数体入口也记录

用法: python3 auto_instrument.py <input.c> [output.json]
      python3 auto_instrument.py --batch <src_dir> <trace_dir>
"""

import json, os, re, sys, subprocess, tempfile
from pathlib import Path

# 算法演示场景: 复杂图算法(Kruskal/Tarjan/EdmondsKarp/匈牙利)需要更多 Steps
# 默认 8000 → 20000, 超时 10s → 30s 确保完整执行轨迹
MAX_TRACE_STEPS = 20000
MAX_STDOUT_MB = 4
RUN_TIMEOUT_SEC = 30
MAX_LOOP_SKIP = 200

# C 类型关键字（用于检测变量声明行）
_TYPE_KW = {'int', 'long', 'short', 'char', 'float', 'double', 'void',
            'unsigned', 'signed', 'const', 'static', 'struct', 'enum',
            'typedef', 'bool', 'size_t', 'FILE'}

# =====================================================================
# TRACE 宏定义（注入到插桩后代码头部）
# =====================================================================
TRACE_HEADER = r'''
/* ===== AUTO-INSTRUMENTED TRACE RUNTIME ===== */
#include <stdio.h>
#include <stddef.h>
static int _trace_step = 0;
static int _trace_depth = 0;
static int _trace_active = 1;
#define _TRACE_MAX_STEPS 20000
#define _TRACE_STOP() do { if (_trace_step >= _TRACE_MAX_STEPS) _trace_active = 0; } while(0)

/* ---- 基础输出宏 ---- */
#define _V_INT(name, val) printf("\"%s\":%d", name, val)
#define _V_FLOAT(name, val) printf("\"%s\":%.6g", name, (double)(val))
#define _V_STR(name, val) printf("\"%s\":\"%s\"", name, val)
#define _V_ARR(name, arr, len) do { \
    printf("\"%s\":[", name); \
    for (int _i = 0; _i < (len); _i++) { if (_i) printf(","); printf("%d", (arr)[_i]); } \
    printf("]"); \
} while(0)
#define _V_ARRF(name, arr, len) do { \
    printf("\"%s\":[", name); \
    for (int _i = 0; _i < (len); _i++) { if (_i) printf(","); printf("%.2f", (double)(arr)[_i]); } \
    printf("]"); \
} while(0)
#define _V_ARR2(name, arr, rows, cols) do { \
    printf("\"%s\":[", name); \
    for (int _i = 0; _i < (rows); _i++) { if (_i) printf(","); \
        printf("["); \
        for (int _j = 0; _j < (cols); _j++) { if (_j) printf(","); printf("%d", (arr)[_i][_j]); } \
        printf("]"); \
    } \
    printf("]"); \
} while(0)
#define _V_ARR_STRUCT(name, arr, len, field) do { \
    printf("\"%s\":[", name); \
    for (int _i = 0; _i < (len); _i++) { if (_i) printf(","); printf("%d", (arr)[_i].field); } \
    printf("]"); \
} while(0)
#define _V_GRAPH_MAT(name, mat, n) do { \
    printf("\"%s\":{\"nodes\":%d,\"edges\":[", name, (n)); \
    int _first = 1; \
    for (int _i = 0; _i < (n); _i++) { \
        for (int _j = 0; _j < (n); _j++) { \
            int _w = (mat)[_i][_j]; \
            if (_w != 0 && _w < 1000000000 && _w > -1000000000) { \
                if (!_first) printf(","); \
                _first = 0; \
                printf("[%d,%d,%d]", _i, _j, _w); \
            } \
        } \
    } \
    printf("]}"); \
} while(0)
#define _V_GRAPH_EDGES(name, arr, len, n) do { \
    printf("\"%s\":{\"nodes\":%d,\"edges\":[", name, (n)); \
    for (int _i = 0; _i < (len); _i++) { \
        if (_i) printf(","); \
        printf("[%d,%d,%d]", (arr)[_i].src, (arr)[_i].dest, (arr)[_i].weight); \
    } \
    printf("]}"); \
} while(0)
#define _V_GRAPH_HEAD_EDGES(name, head, edges, n) do { \
    printf("\"%s\":{\"nodes\":%d,\"labels\":[", name, (n)); \
    for (int _i = 0; _i < (n); _i++) { if (_i) printf(","); printf("%d", _i + 1); } \
    printf("],\"edges\":["); \
    int _first = 1; \
    for (int _u = 1; _u <= (n); _u++) { \
        for (int _e = (head)[_u]; _e != -1; _e = (edges)[_e].next) { \
            if (!_first) printf(","); \
            _first = 0; \
            printf("[%d,%d,1]", _u - 1, (edges)[_e].to - 1); \
        } \
    } \
    printf("]}"); \
} while(0)
#define _V_BIPARTITE(name, graph, match, left_n, right_n) do { \
    printf("\"%s\":{\"left\":%d,\"right\":%d,\"edges\":[", name, (left_n), (right_n)); \
    int _first = 1; \
    for (int _u = 1; _u <= (left_n); _u++) { \
        for (int _v = 1; _v <= (right_n); _v++) { \
            if ((graph)[_u][_v]) { \
                if (!_first) printf(","); \
                _first = 0; \
                printf("[%d,%d]", _u - 1, _v - 1); \
            } \
        } \
    } \
    printf("],\"match\":["); \
    for (int _v = 1; _v <= (right_n); _v++) { \
        if (_v > 1) printf(","); \
        printf("%d", (match)[_v] ? (match)[_v] - 1 : -1); \
    } \
    printf("]}"); \
} while(0)

static void _trace_graph_adj(void **graph, int n, size_t dest_off, size_t weight_off, size_t next_off) {
    printf("{\"nodes\":%d,\"edges\":[", n);
    int _first = 1;
    for (int _i = 0; _i < n; _i++) {
        char *_p = (char*)graph[_i];
        int _guard = 0;
        while (_p && _guard++ < 1000) {
            int _to = *(int*)(_p + dest_off);
            int _w = *(int*)(_p + weight_off);
            if (!_first) printf(",");
            _first = 0;
            printf("[%d,%d,%d]", _i, _to, _w);
            _p = *(void**)(_p + next_off);
        }
    }
    printf("]}");
}

/* ---- 链表/树节点遍历 ---- */
static void _trace_list(void *head, size_t val_off, size_t next_off) {
    printf("[");
    int _f = 1;
    char *_p = (char*)head;
    while (_p) {
        if (!_f) printf(",");
        _f = 0;
        printf("%d", *(int*)(_p + val_off));
        _p = *(void**)(_p + next_off);
    }
    printf("]");
}
// 查找节点在链表中的位置（head 为头，target 为目标节点指针）
static int _trace_pos(void *head, void *target, size_t val_off, size_t next_off) {
    if (!target) return -1;
    int pos = 0;
    char *_p = (char*)head;
    while (_p) {
        if (_p == (char*)target) return pos;
        _p = *(void**)(_p + next_off);
        pos++;
    }
    return -100000 - *(int*)((char*)target + val_off);  // 链已断开时回退到节点值引用
}
static void _trace_tree(void *node, size_t val_off, size_t left_off, size_t right_off, int depth) {
    if (!node || depth > 7) { printf("null"); return; }
    char *_p = (char*)node;
    printf("[%d,", *(int*)(_p + val_off));
    _trace_tree(*(void**)(_p + left_off), val_off, left_off, right_off, depth + 1);
    printf(",");
    _trace_tree(*(void**)(_p + right_off), val_off, left_off, right_off, depth + 1);
    printf("]");
}
static int _trace_tree_find(void *root, void *target, size_t val_off, size_t left_off, size_t right_off) {
    if (!root) return -2147483647;
    if (root == target) return *(int*)((char*)root + val_off);
    char *_p = (char*)root;
    int _l = _trace_tree_find(*(void**)(_p + left_off), target, val_off, left_off, right_off);
    if (_l != -2147483647) return _l;
    int _r = _trace_tree_find(*(void**)(_p + right_off), target, val_off, left_off, right_off);
    if (_r != -2147483647) return _r;
    return -2147483647;
}
static int _trace_tree_ref(void *root, void *target, size_t val_off, size_t left_off, size_t right_off) {
    if (!target) return -1;
    int _v = _trace_tree_find(root, target, val_off, left_off, right_off);
    return _v == -2147483647 ? *(int*)((char*)target + val_off) : _v;
}
#define _VC() printf(",")

/* ---- TRACE_EXEC: 普通语句 ---- */
#define TRACE_EXEC(line, body) do { \
    if (!_trace_active) break; \
    printf("{\"step\":%d,\"line\":%d,\"type\":\"exec\",\"vars\":{", _trace_step++, (line)); \
    body; \
    printf("}}\n"); \
    _TRACE_STOP(); \
} while(0)

/* ---- TRACE_ENTER: 函数进入 ---- */
#define TRACE_ENTER(line, func, body) do { \
    if (!_trace_active) break; \
    printf("{\"step\":%d,\"line\":%d,\"type\":\"enter\",\"func\":\"%s\",\"vars\":{", _trace_step++, (line), (func)); \
    body; \
    printf("}}\n"); \
    _trace_depth++; \
    _TRACE_STOP(); \
} while(0)

/* ---- TRACE_EXIT: 函数退出 ---- */
#define TRACE_EXIT(line, func) do { \
    if (!_trace_active) break; \
    if (_trace_depth > 0) _trace_depth--; \
    printf("{\"step\":%d,\"line\":%d,\"type\":\"exit\",\"func\":\"%s\",\"vars\":{}}\n", _trace_step++, (line), (func)); \
    _TRACE_STOP(); \
} while(0)

/* ---- TRACE_COND: 条件判断 ---- */
#define TRACE_COND(line, cond, body) do { \
    if (!_trace_active) break; \
    printf("{\"step\":%d,\"line\":%d,\"type\":\"cond\",\"result\":%s,\"vars\":{", \
           _trace_step++, (line), (cond) ? "true" : "false"); \
    body; \
    printf("}}\n"); \
    _TRACE_STOP(); \
} while(0)

/* ===== END TRACE RUNTIME ===== */
'''


# =====================================================================
# 工具函数
# =====================================================================

def read_source(path):
    try:
        return path.read_text(encoding='utf-8')
    except:
        return path.read_text(encoding='gbk')


def strip_existing_trace(source):
    """移除已有 TRACE 指令"""
    lines = source.split('\n')
    cleaned = []
    for line in lines:
        if 'TRACE_' in line or 'AUTO-INSTRUMENTED' in line:
            continue
        if '/* ===== END TRACE RUNTIME' in line:
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)


def get_param_decl(params_str, param_name):
    """Return the single parameter declaration containing param_name."""
    for part in params_str.split(','):
        part = part.strip()
        if re.search(rf'\b{re.escape(param_name)}\b', part):
            return part
    return ''


def parse_param_name(param_decl):
    """Extract the declared parameter name from a C parameter declaration."""
    decl = param_decl.strip()
    if not decl or decl == 'void':
        return None
    # Drop array suffixes before taking the last identifier:
    #   int graph[][MAX_V] -> int graph
    #   int arr[]          -> int arr
    decl = re.sub(r'\[[^\]]*\]', '', decl).strip()
    m = re.search(r'(\w+)\s*$', decl)
    if not m:
        return None
    name = m.group(1)
    return None if name == 'void' else name


def is_param_array(param_decl, param_name):
    return bool(re.search(rf'\b{re.escape(param_name)}\s*\[', param_decl))


def is_param_2d_array(param_decl, param_name):
    return bool(re.search(rf'\b{re.escape(param_name)}\s*(?:\[[^\]]*\]){{2,}}', param_decl))


def is_param_pointer(param_decl, param_name):
    return bool(re.search(rf'\b{re.escape(param_name)}\s*\*|\*\s*{re.escape(param_name)}\b', param_decl))


# =====================================================================
# 第一步: 解析 C 源码结构
# =====================================================================

def find_functions(lines):
    """找到所有函数定义。返回 [{name, ret_type, params_str, param_names, start, end, body_start}, ...]"""
    funcs = []
    keywords = {'if', 'while', 'for', 'switch', 'else', 'return', 'sizeof', 'do',
                'struct', 'typedef', 'goto', 'case', 'break', 'continue'}
    i = 0
    n = len(lines)
    while i < n:
        stripped = lines[i].strip()
        if not stripped or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*') or stripped.startswith('#'):
            i += 1
            continue
        signature = stripped
        sig_end = i
        if '(' in signature and ')' not in signature and not signature.endswith(';'):
            for k in range(i + 1, min(i + 10, n)):
                part = lines[k].strip()
                if not part or part.startswith('//') or part.startswith('/*'):
                    continue
                signature += ' ' + part
                sig_end = k
                if ')' in part:
                    break
        m = re.match(r'^((?:\w[\w\s\*]*?))\s+(\w+)\s*\(([^)]*)\)\s*\{?\s*$', signature)
        if m:
            name = m.group(2)
            if name in keywords:
                i += 1
                continue
            ret_type_raw = m.group(1).strip()
            # 剔除 static/inline/extern 等修饰符（它们不属于返回类型）
            ret_type = ' '.join(t for t in ret_type_raw.split()
                                if t not in ('static', 'inline', 'extern', 'const'))
            # 如果剩空串，默认 int（如 "static" 后没类型名）
            if not ret_type:
                ret_type = 'int'
            params_str = m.group(3).strip()

            # 找函数体 { 行
            body_start = sig_end
            if '{' not in signature:
                for k in range(sig_end + 1, min(sig_end + 4, n)):
                    if '{' in lines[k]:
                        body_start = k
                        break
                else:
                    i += 1
                    continue

            # 大括号匹配找结束
            depth = 0
            end = -1
            for k in range(body_start, n):
                l = lines[k]
                clean = re.sub(r'"[^"]*"', '', l)
                clean = re.sub(r"'[^']*'", '', clean)
                depth += clean.count('{') - clean.count('}')
                if depth <= 0:
                    end = k
                    break
            if end < 0:
                i += 1
                continue

            # 提取参数名（排除 void 关键字）
            param_names = []
            if params_str.strip() and params_str.strip() != 'void':
                for part in params_str.split(','):
                    pname = parse_param_name(part)
                    if pname:
                        param_names.append(pname)

            funcs.append({
                'name': name, 'ret_type': ret_type,
                'params_str': params_str, 'param_names': param_names,
                'start': i, 'end': end, 'body_start': body_start,
            })
            i = end + 1
        else:
            i += 1
    return funcs


def find_locals_and_assigns(lines, start, end):
    """找到局部变量声明和赋值语句"""
    locals_list = []
    assigns = []
    for i in range(start, end + 1):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('#'):
            continue
        if 'TRACE_' in stripped:
            continue

        # for (int i = ...) 声明——必须在 for 跳过之前检查
        m = re.match(r'for\s*\(\s*(?:int|float|char|size_t)\s+(\w+)\s*=\s*(.+?)\s*;', stripped)
        if m:
            name = m.group(1)
            locals_list.append({
                'line': i, 'name': name, 'type': 'int',
                'is_array': False, 'is_pointer': False, 'has_init': True,
            })
            continue

        # 跳过 for 循环行（非变量声明的 for 行）
        if re.match(r'for\s*\(', stripped):
            continue

        # 局部变量声明: int x; / struct Type *ptr; / int arr[N]; / int dp[M][N];
        m = re.match(r'((?:(?:static|const)\s+)*(?:int|float|double|char|long|unsigned|short|size_t|struct\s+\w+)(?:\s*\*)?)\s+(\w+)\s*'
                     r'(?:\[\s*([^\]]*)\s*\]'
                     r'(?:\[\s*([^\]]*)\s*\])?'
                     r')?\s*'
                     r'(?:=\s*(.+?))?\s*;', stripped)
        if m:
            t = m.group(1).strip()
            name = m.group(2)
            arr_dim = m.group(3)
            arr_dim2 = m.group(4)
            is_array = arr_dim is not None
            is_2d = arr_dim2 is not None
            is_pointer = '*' in t
            init_val = m.group(5)
            # 提取基础类型（去掉 * 和修饰符）
            base_type = 'int'
            for bt in ['double', 'float', 'char', 'long', 'unsigned', 'short']:
                if bt in t:
                    base_type = bt if bt != 'unsigned' else 'int'
                    break
            locals_list.append({
                'line': i, 'name': name, 'type': base_type,
                'is_array': is_array, 'is_2d': is_2d,
                'arr_dim': arr_dim, 'arr_dim2': arr_dim2,
                'is_pointer': is_pointer,
                'has_init': init_val is not None,
            })
            if is_array and init_val is None and not t.startswith('struct'):
                assigns.append({'line': i, 'var_name': name, 'is_array': True, 'is_2d': is_2d})
            continue

        # 排除函数调用行、printf 等
        if re.match(r'(?:printf|scanf|return|while|if|for|else|do|switch)\b', stripped):
            continue

        # 赋值: x = expr; / *ptr = expr; / arr[idx] = expr; / ptr->field = expr;
        m = re.match(r'^(\*?)(\w+)\s*(?:\[([^\]]+)\](?:\[[^\]]+\])?)?\s*=\s*(.+?)\s*;', stripped)
        # struct 字段赋值: ptr->field = expr; / ptr->next->next = expr;
        m2 = re.match(r'^(\w+(?:\s*->\s*\w+)*)\s*->\s*(\w+)\s*=\s*(.+?)\s*;', stripped) if not m else None
        if m or m2:
            if m:
                name = m.group(2)
                deref = m.group(1) == '*'
                arr_idx = m.group(3)
            else:
                name = m2.group(1).split('->')[0].strip()  # 根指针变量名
                deref = False
                arr_idx = None
            assigns.append({
                'line': i, 'var_name': name, 'is_deref': deref,
                'is_array_index': arr_idx is not None,
            })
            continue

        # x++ / x-- / ++x / --x / x+= / x-= / x*= / x/=
        m = re.match(r'^(?:\+\+|\-\-)?(\w+)\s*(?:\+\+|\-\-|\+=\s*.+?|\-=\s*.+?|\*=\s*.+?|/=\s*.+?)\s*;', stripped)
        if m:
            assigns.append({'line': i, 'var_name': m.group(1)})
    return locals_list, assigns


def find_conds_and_returns(lines, start, end):
    """找到条件/循环头 和 return 语句"""
    conds = []
    rets = []
    for i in range(start, end + 1):
        stripped = lines[i].strip()
        if stripped.startswith('//') or stripped.startswith('/*'):
            continue
        if re.match(r'while\s*\(', stripped):
            conds.append({'type': 'while', 'line': i})
        elif re.match(r'for\s*\(', stripped):
            conds.append({'type': 'for', 'line': i})
        elif re.match(r'if\s*\(', stripped):
            conds.append({'type': 'if', 'line': i})
        elif re.match(r'return\b', stripped):
            # 跨行 return：连接直到分号出现
            full_text = stripped
            j = i + 1
            while not full_text.endswith(';') and j < end:
                ns = lines[j].strip()
                if ns and not ns.startswith('//') and not ns.startswith('/*'):
                    full_text += ' ' + ns
                j += 1
            rets.append({'line': i, 'text': full_text})
    return conds, rets


def find_calls_in_range(lines, start, end, known_funcs):
    """找到对已知函数的调用（跳过字符串内的假匹配）"""
    calls = []
    func_names = {f['name'] for f in known_funcs}
    for i in range(start, end + 1):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('#'):
            continue
        if 'TRACE_' in stripped:
            continue
        # 用状态机标记字符串/字符字面量边界，找出代码区段
        code_segs = []
        in_str = False
        seg_start = 0
        j = 0
        while j < len(stripped):
            c = stripped[j]
            if in_str:
                if c == '\\':
                    j += 2
                    continue
                if c == '"':
                    in_str = False
                    code_segs.append((seg_start, j + 1, True))  # True = was string
                    seg_start = j + 1
            else:
                if c == '"':
                    # 代码段结束，字符串段开始
                    if j > seg_start:
                        code_segs.append((seg_start, j, False))
                    in_str = True
                    seg_start = j
                elif c == '/' and j + 1 < len(stripped) and stripped[j + 1] == '/':
                    # 行注释，后面都是注释
                    if j > seg_start:
                        code_segs.append((seg_start, j, False))
                    seg_start = len(stripped)
                    break
            j += 1
        if seg_start < len(stripped):
            code_segs.append((seg_start, len(stripped), False))
        # 只在代码段（非字符串）中搜索函数调用
        for fname in func_names:
            for seg_start, seg_end, is_str in code_segs:
                if is_str:
                    continue
                seg = stripped[seg_start:seg_end]
                # 排除函数定义行: 类型/modifiers + 函数名(参数)
                # 如 int* counting_sort(int arr[], int n) {
                # 特点：fname( 之前只有类型名/空格/*，没有 =,;{}() 等操作符
                # 但要排除 return/if/while 等关键字开头的调用行
                idx = stripped.find(fname)
                if idx >= 0 and stripped[idx + len(fname):].lstrip().startswith('('):
                    before = stripped[:idx].strip()
                    if before and not re.search(r'[=;,(){}<>\[\]\.]', before):
                        bt = before.split()
                        call_prefix_kw = {'return', 'if', 'else', 'while', 'for', 'do', 'switch', 'sizeof', 'case', 'goto'}
                        if bt and bt[-1] not in call_prefix_kw:
                            continue
                m = re.search(rf'{re.escape(fname)}\s*\(([^)]*)\)', seg)
                if m:
                    args_str = m.group(1)
                    arg_names = [a.strip() for a in args_str.split(',') if a.strip()]
                    pre = lines[i - 1].strip() if i > 0 else ''
                    nxt = lines[i + 1].strip() if i + 1 < len(lines) else ''
                    in_expr = _in_expr(pre, nxt)
                    calls.append({'caller_line': i, 'callee': fname,
                                  'arg_names': arg_names, 'in_expr': in_expr})
    return calls


def extract_cond_expr(line):
    """提取条件表达式。for (init; cond; incr) → cond"""
    stripped = line.strip()
    m = re.match(r'for\s*\(([^;]*);\s*([^;]*);\s*([^)]*)\)', stripped)
    if m:
        return m.group(2).strip()
    # 找最外层的 if/while 括号——用括号计数而非贪婪匹配
    m = re.match(r'(?:while|if)\s*\(', stripped)
    if m:
        start = m.end()
        depth = 1
        for idx in range(start, len(stripped)):
            c = stripped[idx]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    return stripped[start:idx].strip()
    return ''


# =====================================================================
# 第二步: 代码插桩
# =====================================================================

def build_body_line(vars_seq):
    """
    将变量捕获序列转为 TRACE 宏的 body 参数。
    vars_seq: [(kind, name, expr_or_len), ...]
       kind: 'int' | 'array' | 'comma'
    返回: 一个 C 语句序列字符串 (分号分隔，末尾无分号)
    """
    parts = []
    for v in vars_seq:
        kind = v[0]
        if kind == 'comma':
            parts.append('_VC()')
        elif kind == 'int':
            parts.append(f'_V_INT("{v[1]}", {v[2]})')
        elif kind == 'float':
            parts.append(f'_V_FLOAT("{v[1]}", {v[2]})')
        elif kind == 'arrayf':
            parts.append(f'_V_ARRF("{v[1]}", {v[2]}, {v[3]})')
        elif kind == 'array':
            parts.append(f'_V_ARR("{v[1]}", {v[2]}, {v[3]})')
        elif kind == 'array_struct':
            parts.append(f'_V_ARR_STRUCT("{v[1]}", {v[2]}, {v[3]}, {v[4]})')
        elif kind == 'graph_matrix':
            parts.append(f'_V_GRAPH_MAT("{v[1]}", {v[2]}, {v[3]})')
        elif kind == 'graph_edges':
            parts.append(f'_V_GRAPH_EDGES("{v[1]}", {v[2]}, {v[3]}, {v[4]})')
        elif kind == 'graph_adj':
            parts.append(f'_V_GRAPH_ADJ_{v[4]}("{v[1]}", {v[2]}, {v[3]})')
        elif kind == 'graph_head_edges':
            parts.append(f'_V_GRAPH_HEAD_EDGES("{v[1]}", {v[2]}, {v[3]}, {v[4]})')
        elif kind == 'bipartite':
            parts.append(f'_V_BIPARTITE("{v[1]}", {v[2]}, {v[3]}, {v[4]}, {v[5]})')
        elif kind == 'list_pos':
            parts.append(f'_V_INT("{v[1]}", {v[2]})')
        elif kind == 'list':
            parts.append(f'_V_LIST_{v[3]}("{v[1]}", {v[2]})')
        elif kind == 'tree':
            parts.append(f'_V_TREE_{v[3]}("{v[1]}", {v[2]})')
        elif kind == 'tree_ref':
            parts.append(f'_V_INT("{v[1]}", _TREE_REF_{v[4]}({v[3]}, {v[2]}))')
    return '; '.join(parts) if parts else ''


# =====================================================================
# 变量分类与数组截断
# =====================================================================

# 核心变量名（始终展开）——涵盖排序/查找/图/DP/树等常见算法
_PRIMARY_VAR_PATTERNS = [
    # 数组和集合
    r'^arr\d*$', r'^a$', r'^nums$', r'^data$', r'^list$', r'^vec$',
    # 索引类
    r'^[ijk]$', r'^[ijkmn]\d*$', r'^idx?$', r'^pos$', r'^index$',
    # 搜索/排序核心
    r'^(low|high|mid|left|right|pivot|key|target|val)$',
    r'^(temp|tmp|swap)$',
    r'^(minIdx|minIndex|maxIdx|maxIndex|min_val|max_val)$',
    # 指针/游标
    r'^(head|tail|cur|curr|prev|next|root|node|parent|child)$',
    # 计数器/结果
    r'^(count|cnt|sum|result|ans|res|found|flag|swapped)$',
    r'^(min|max|step|depth|size|len|length)$',
    # 图/DP
    r'^(visited|dp|dist|weight|path|memo)$',
]
_PRIMARY_RE = re.compile('|'.join(_PRIMARY_VAR_PATTERNS))

# 完全隐藏的变量
_HIDDEN_VAR_RE = re.compile(r'^(_trace_|_ret_|__)')
_POINTER_LIKE_VAR_RE = re.compile(
    r'^(?:'
    r'.*ptr.*|(?:new_?)?node|root|head|tail|curr|current|prev|next(?:val)?|'
    r'queue|stack|graph|parent|result|res|word|pattern|uf|pq|heap|'
    r'a|b|p|q'
    r')$',
    re.IGNORECASE,
)

# 超大数组截断阈值
ARRAY_TRUNCATE_THRESHOLD = 100
ARRAY_HEAD_TAIL = 10


def classify_variable(varname, is_array=False):
    """
    返回变量类别: 'primary' | 'secondary' | 'hidden'
    - primary: 始终在前端展开
    - secondary: 默认折叠在"其他变量"区
    - hidden: 完全不写入 JSON（trace 内部用）
    """
    if _HIDDEN_VAR_RE.match(varname):
        return 'hidden'
    if _PRIMARY_RE.match(varname):
        return 'primary'
    return 'secondary'


def looks_like_pointer_scalar(varname, values):
    """Heuristic for raw addresses accidentally captured as scalar ints."""
    if not _POINTER_LIKE_VAR_RE.match(varname):
        return False
    for value in values:
        if isinstance(value, int) and abs(value) >= 1_000_000:
            return True
    return False


def trim_array_values(values, max_total=ARRAY_TRUNCATE_THRESHOLD, head_tail=ARRAY_HEAD_TAIL):
    """
    超大数组只保留头尾各 head_tail 个元素，中间用省略标记。
    返回: (trimmed_values, was_trimmed)
    """
    if len(values) <= max_total:
        return values, False
    head = values[:head_tail]
    tail = values[-head_tail:]
    return head + ['...'] + tail, True


def trim_array_in_vars(vars_dict, var_classes):
    """
    对 vars_dict 中的数组值进行截断。
    var_classes: {varname: {category, type}}
    返回截断后的 vars_dict，移除 hidden 变量。
    """
    result = {}
    for k, v in vars_dict.items():
        info = var_classes.get(k, {})
        cls = info.get('category', 'secondary') if isinstance(info, dict) else info
        if cls == 'hidden':
            continue
        if isinstance(v, list) and len(v) > ARRAY_TRUNCATE_THRESHOLD:
            trimmed, _ = trim_array_values(v)
            result[k] = trimmed
        else:
            result[k] = v
    return result


def is_tree_snapshot(value):
    """Tree snapshots are encoded as [value, left, right], with null children."""
    if value is None:
        return True
    if not isinstance(value, list) or len(value) != 3:
        return False
    return (
        not isinstance(value[0], list)
        and is_tree_snapshot(value[1])
        and is_tree_snapshot(value[2])
    )


def make_var_seq(var_info, tracked_names, src_expr, list_ctx=None):
    """
    生成变量捕获序列（带逗号）。
    只捕获在 src_expr 中出现且是标量的 tracked 变量。
    list_ctx: 可选 {'head_var': str, 'tname': str}，用于链表指针位置追踪
    返回 vars_seq (list)，可直接传入 build_body_line。
    """
    vi_map = {v['name']: v for v in var_info} if var_info else {}
    var_names = []
    for tn in tracked_names:
        if tn == 'void':
            continue  # 忽略 void 关键字（如 main(void)）
        vi = vi_map.get(tn, {})
        is_arr = vi.get('is_array', False)
        if is_arr:
            continue  # 不在 cond/exec 里捕获完整数组（只在声明处捕获）
        if vi.get('is_pointer') and not list_ctx:
            continue  # 普通指针地址对初学者没有教学价值
        # 检查是否在表达式里
        if re.search(rf'\b{re.escape(tn)}\b', src_expr):
            if list_ctx and vi.get('is_pointer') and tn != list_ctx['head_var']:
                # 链表指针变量 → 位置追踪
                h = list_ctx['head_var']
                t = list_ctx['tname']
                vf = list_ctx.get('val_field', 'val')
                nf = list_ctx.get('next_field', 'next')
                var_names.append(('list_pos', tn, f'_trace_pos((void*){h}, (void*){tn}, offsetof(struct {t}, {vf}), offsetof(struct {t}, {nf}))'))
            else:
                kind = 'float' if vi.get('type') in ('double', 'float') else 'int'
                var_names.append((kind, tn, tn))
    # 插入逗号
    result = []
    for i, v in enumerate(var_names):
        if i > 0:
            result.append(('comma',))
        result.append(v)
    return result


# ---- 辅助：检测代码行是否处于表达式中间 ----

def _in_expr(before_stripped, after_stripped=''):
    """检测该行是否处在跨行表达式中间（如 printf 参数、多行 return）。"""
    if before_stripped.startswith('/*') and before_stripped.endswith('*/'):
        before_stripped = ''
    if after_stripped.startswith('/*') and after_stripped.endswith('*/'):
        after_stripped = ''
    # 前一行结尾是连接符
    if before_stripped and (before_stripped.endswith('(') or before_stripped.endswith(',') or
        before_stripped.endswith('+') or before_stripped.endswith('-') or
        before_stripped.endswith('*') or before_stripped.endswith('/') or
        before_stripped.endswith('&&') or before_stripped.endswith('||') or
        before_stripped.endswith('?') or before_stripped.endswith(':') or
        before_stripped.endswith('==') or
        before_stripped.endswith('|') or before_stripped.endswith('&')):
        return True
    # 下一行开头是连接符
    if after_stripped and (after_stripped.startswith(',') or after_stripped.startswith(')') or
        after_stripped.startswith('+') or after_stripped.startswith('-') or
        after_stripped.startswith('*') or after_stripped.startswith('/') or
        after_stripped.startswith('&&') or after_stripped.startswith('||') or
        after_stripped.startswith('?') or after_stripped.startswith(':') or
        after_stripped.startswith('|')):
        return True
    return False


def _find_expr_end(lines, start_idx, func_end):
    """从当前行往后找多行表达式的结束行（用于跨行 return / 赋值等）。
    返回最后一个属于该表达式的行号（不是 start_idx 本身表示确实跨行）。"""
    i = start_idx + 1
    first_non_empty = True  # start_idx 后的第一行非空行：如果是 ; 开头或独立语句则立即停止
    while i < min(func_end, len(lines)):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if s.startswith('//') or s.startswith('/*'):
            # 纯注释行 = 已经过了表达式，立即停止
            break
        # 第一行非空行：如果以独立语句开头（; 开头），说明 start_idx 行是独立语句
        if first_non_empty and s[0] not in '+-*/&|^?:<>,)(' and not s.endswith(';'):
            # 非表达式延续也非独立语句 → break
            break
        first_non_empty = False
        c0 = s[0]
        # 分号结尾 → 这行是表达式的最后一行
        if s.endswith(';'):
            return i
        # 下一行以运算符或 , ) 开头 = 表达式的延续
        if c0 in '+*/&|^?:<>,' and not s.startswith(('+ ', '+{')):
            i += 1
            continue
        if c0 == '-':
            if s.startswith('-}'):
                i += 1
                continue
            if len(s) >= 2 and s[1] not in ' =\t':
                i += 1
                continue
        if c0 in ')]':
            i += 1
            continue
        # 非延续 → break
        break
    return start_idx  # 没有跨行


def instrument_source(original_source):
    """生成插桩后的 C 源码"""
    lines = original_source.split('\n')

    # 解析 struct 定义，找到链表/树节点类型，同时收集所有 struct 字段信息
    linked_structs = {}   # {type_name: {val_field, next_field}}
    tree_structs = {}     # {type_name: {val_field, left_field, right_field}}
    graph_edge_structs = set()
    graph_adj_structs = {} # {type_name: {dest_field, weight_field, next_field}}
    struct_defs = {}      # {type_name: [(fname, ftype, is_ptr), ...]}
    global_matrix_graphs = []
    global_head_edge_graph = None
    global_bipartite_graph = None
    # 匹配 struct Name { ... } 和 typedef struct { ... } Name;
    struct_pattern = re.compile(
        r'(?:typedef\s+)?struct\s+(\w+)?\s*\{([^}]+)\}\s*(\w+)?\s*;',
        re.DOTALL
    )
    for m in struct_pattern.finditer(original_source):
        # type_name: 若是 typedef struct { } Name; 则用 Name，否则用 struct 后的名字
        type_name = m.group(1) if m.group(1) else m.group(3)
        if not type_name:
            continue
        body = m.group(2)
        body_clean = re.sub(r'/\*.*?\*/', '', body, flags=re.DOTALL)
        body_clean = re.sub(r'//.*', '', body_clean)
        fields = []
        # 支持 int src, dest, weight; / struct Node* next; 这类一行多字段声明。
        for stmt in body_clean.split(';'):
            stmt = stmt.strip()
            if not stmt:
                continue
            dm = re.match(r'((?:struct\s+\w+|\w+)(?:\s*\*)?)\s+(.+)$', stmt)
            if not dm:
                continue
            type_part = dm.group(1).strip()
            declarators = dm.group(2)
            for decl in declarators.split(','):
                decl = decl.strip()
                fm = re.match(r'(\*?)\s*(\w+)$', decl)
                if not fm:
                    continue
                ftype = type_part.replace('*', '').strip()
                fname = fm.group(2)
                is_ptr = '*' in type_part or bool(fm.group(1))
                fields.append((fname, ftype, is_ptr))
        struct_defs[type_name] = fields
        # 找 self-pointer 字段和第一个 int 字段（用于链表/树检测）
        next_field = None
        val_field = None
        self_ptr_fields = []
        for fname, ftype, is_ptr in fields:
            if f'struct {type_name}' in ftype and is_ptr:
                self_ptr_fields.append(fname)
                if next_field is None:
                    next_field = fname
            if 'int' in ftype and val_field is None and not is_ptr:
                val_field = fname
        if val_field and 'left' in self_ptr_fields and 'right' in self_ptr_fields:
            tree_structs[type_name] = {'val': val_field, 'left': 'left', 'right': 'right'}
        if next_field and val_field:
            linked_structs[type_name] = {'val': val_field, 'next': next_field}
        if all(re.search(rf'\b{name}\b', body_clean) for name in ('src', 'dest', 'weight')):
            graph_edge_structs.add(type_name)
        if next_field:
            field_names = {fname for fname, _, _ in fields}
            dest_field = next((name for name in ('dest', 'to', 'v') if name in field_names), None)
            weight_field = next((name for name in ('weight', 'w', 'cost') if name in field_names), None)
            if dest_field and weight_field:
                graph_adj_structs[type_name] = {
                    'dest': dest_field,
                    'weight': weight_field,
                    'next': next_field,
                }

    for gm in re.finditer(r'\bint\s+(\w+)\s*\[\s*(?:MAXN|MAX_V|MAX|[A-Z_]+)\s*\]\s*\[\s*(?:MAXN|MAX_V|MAX|[A-Z_]+)\s*\]\s*;', original_source):
        name = gm.group(1)
        if name in ('graph', 'capacity'):
            global_matrix_graphs.append(name)

    if re.search(r'\bint\s+head\s*\[', original_source) and re.search(r'\bEdge\s+edges\s*\[', original_source):
        fields = struct_defs.get('Edge', [])
        field_names = {fname for fname, _, _ in fields}
        if 'to' in field_names and 'next' in field_names:
            global_head_edge_graph = {'name': 'graph', 'head': 'head', 'edges': 'edges'}

    if (
        re.search(r'\bint\s+graph\s*\[', original_source)
        and re.search(r'\bint\s+match\s*\[', original_source)
        and re.search(r'\bint\s+n_left\s*,\s*n_right\b', original_source)
    ):
        global_bipartite_graph = {
            'name': 'bipartite',
            'graph': 'graph',
            'match': 'match',
            'left': 'n_left',
            'right': 'n_right',
        }

    # 生成链表遍历宏定义（仅限线性链表：next/nxt/link）
    list_macros = ''
    for tname, info in linked_structs.items():
        if info.get('next', '') not in ('next', 'nxt', 'link'):
            continue  # 跳过树/图等非线性结构
        list_macros += (
            f'#define _V_LIST_{tname}(vname, head) do {{ '
            f'printf("\\\"%s\\\":", vname); '
            f'_trace_list((void*)(head), offsetof(struct {tname}, {info["val"]}), '
            f'offsetof(struct {tname}, {info["next"]})); '
            f'}} while(0)\n'
        )

    tree_macros = ''
    for tname, info in tree_structs.items():
        val = info['val']
        left = info['left']
        right = info['right']
        tree_macros += (
            f'#define _V_TREE_{tname}(vname, root) do {{ '
            f'printf("\\\"%s\\\":", vname); '
            f'_trace_tree((void*)(root), offsetof(struct {tname}, {val}), '
            f'offsetof(struct {tname}, {left}), offsetof(struct {tname}, {right}), 0); '
            f'}} while(0)\n'
            f'#define _TREE_REF_{tname}(root, target) '
            f'_trace_tree_ref((void*)(root), (void*)(target), offsetof(struct {tname}, {val}), '
            f'offsetof(struct {tname}, {left}), offsetof(struct {tname}, {right}))\n'
        )

    graph_adj_macros = ''
    for tname, info in graph_adj_structs.items():
        graph_adj_macros += (
            f'#define _V_GRAPH_ADJ_{tname}(vname, graph, n) do {{ '
            f'printf("\\\"%s\\\":", vname); '
            f'_trace_graph_adj((void**)(graph), (n), offsetof(struct {tname}, {info["dest"]}), '
            f'offsetof(struct {tname}, {info["weight"]}), offsetof(struct {tname}, {info["next"]})); '
            f'}} while(0)\n'
        )

    # 分析源码
    functions = find_functions(lines)
    func_map = {f['name']: f for f in functions}

    # 收集每个函数信息
    all_data = {}
    for func in functions:
        body_start = func['body_start']
        func_end = func['end']
        locals_list, assigns = find_locals_and_assigns(lines, body_start, func_end)
        conds, rets = find_conds_and_returns(lines, body_start, func_end)
        calls = find_calls_in_range(lines, body_start, func_end, functions)

        tracked = set(func['param_names'])
        for v in locals_list:
            tracked.add(v['name'])
        for a in assigns:
            tracked.add(a['var_name'])
        tracked.discard('')

        all_data[func['name']] = {
            'locals': locals_list, 'assigns': assigns,
            'conds': conds, 'rets': rets, 'calls': calls,
            'tracked': sorted(tracked),
        }

    # 构建 injections: line_idx -> [injection_lines]
    injections = {}         # line_idx → [lines to insert AFTER this line]
    before_injections = {}   # line_idx → [lines to insert BEFORE this line]
    line_replacements = {}   # line_idx -> replacement_line_text (替换而非插入)

    # 收集所有被调用函数名（这些函数会有调用侧 ENTER）
    all_callees = set()
    for func in functions:
        for call in all_data[func['name']]['calls']:
            all_callees.add(call['callee'])

    # 从源码中提取所有局部数组声明的长度（用于函数参数无长度时回退）
    all_array_lens = {}
    for m in re.finditer(r'(?:int|float|double|char|unsigned)\s+(\w+)\s*\[\s*\]\s*=\s*\{([^}]+)\}', original_source):
        name = m.group(1)
        vals = [v.strip() for v in m.group(2).split(',') if v.strip()]
        all_array_lens[name] = len(vals)

    for func in functions:
        name = func['name']
        body_start = func['body_start']
        data = all_data[name]
        tracked = data['tracked']
        var_info = data['locals']
        # 把参数也加进 var_info（从函数签名判断是否为数组/指针）
        params_str = func['params_str']
        for pn in func['param_names']:
            if not any(v['name'] == pn for v in var_info):
                param_decl = get_param_decl(params_str, pn)
                is_arr = is_param_array(param_decl, pn)
                is_2d = is_param_2d_array(param_decl, pn)
                is_ptr = is_param_pointer(param_decl, pn)
                # 推断参数类型
                ptype = 'int'
                for bt in ['double', 'float', 'char']:
                    if bt in param_decl: ptype = bt; break
                param_entry = {'name': pn, 'type': ptype, 'is_array': is_arr, 'is_2d': is_2d, 'is_pointer': is_ptr}
                # 检测是否为结构体数组：参数声明中出现已知 struct 类型名
                if is_arr and struct_defs:
                    for sname, sfields in struct_defs.items():
                        # 只看当前参数，避免 "Node *root, int arr[]" 误判 arr 为 Node 数组。
                        if re.search(rf'\b{re.escape(sname)}\b.*\b{re.escape(pn)}\b', param_decl):
                            # 找到第一个 int 字段作为可视化值
                            for fname, ftype, fptr in sfields:
                                if 'int' in ftype and not fptr:
                                    param_entry['struct_type'] = sname
                                    param_entry['struct_field'] = fname
                                    break
                            break
                var_info.append(param_entry)

        # 找当前函数中可追踪的链表头变量（参数或局部）
        list_head_var = None
        list_tname = None
        if linked_structs:
            for pn in func['param_names']:
                for tname in linked_structs:
                    if linked_structs[tname].get('next', '') not in ('next', 'nxt', 'link'):
                        continue
                    if re.search(rf'struct\s+{tname}\s*\*\s*{re.escape(pn)}', params_str):
                        list_head_var = pn
                        list_tname = tname
                        break
                if list_head_var: break
            if not list_head_var:
                for v in var_info:
                    if v.get('is_pointer'):
                        for tname in linked_structs:
                            if linked_structs[tname].get('next', '') not in ('next', 'nxt', 'link'):
                                continue
                            if v['name'] in ('head', 'root', 'list'):
                                list_head_var = v['name']
                                list_tname = tname
                                break
                    if list_head_var: break

        # ---- 1) TRACE_ENTER (函数入口) ----
        # 使用函数签名行号（而非函数体首行），让用户感知"进入函数"
        entry_line_no = func['start'] + 1  # 1-indexed，函数签名行
        enter_parts = []
        for idx, pn in enumerate(func['param_names']):
            vi = next((v for v in var_info if v['name'] == pn), None)
            if vi and (vi.get('is_array') or vi.get('is_pointer')):
                # 检查是否为链表/树节点指针
                sm = re.search(rf'struct\s+(\w+)\s*\*\s*{re.escape(pn)}', params_str)
                if sm and sm.group(1) in tree_structs:
                    tname = sm.group(1)
                    if enter_parts:
                        enter_parts.append(('comma',))
                    enter_parts.append(('tree', pn, pn, tname))
                elif sm and sm.group(1) in linked_structs:
                    tname = sm.group(1)
                    if enter_parts:
                        enter_parts.append(('comma',))
                    enter_parts.append(('list', pn, pn, tname))
                continue
            if enter_parts:
                enter_parts.append(('comma',))
            scalar_kind = 'float' if vi and vi.get('type') in ('double', 'float') else 'int'
            enter_parts.append((scalar_kind, pn, pn))
        body_text = build_body_line(enter_parts)
        # main 函数即使无参也要生成 ENTER（用户体验：第一步应是 main 入口）
        is_main = (name == 'main')
        # 如果函数在其他地方被调用（会有调用侧 ENTER），跳过函数入口 ENTER
        # 调用侧 ENTER 已经包含了参数值和数组数据，更完整
        has_call_site = name in all_callees
        if (body_text or is_main) and not has_call_site:
            brace_line = body_start
            if '{' not in lines[brace_line]:
                for k in range(body_start, min(body_start + 3, len(lines))):
                    if '{' in lines[k]:
                        brace_line = k
                        break
            indent = '    '
            if is_main and not body_text:
                injection = f'{indent}TRACE_ENTER({entry_line_no}, "main", );'
            else:
                injection = f'{indent}TRACE_ENTER({entry_line_no}, "{name}", {body_text});'
            # 如果 { 和函数签名在同一行（如 int main() {），
            # 需要跳过变量声明，在第一条可执行语句之前注入
            inject_line = brace_line
            sig_line = lines[func['start']].strip()
            if '{' in sig_line and sig_line.endswith('{'):
                # { 在签名行末尾 → 跳过变量声明找可执行行
                last_decl_line = brace_line
                for k in range(brace_line + 1, min(brace_line + 20, func['end'] + 1)):
                    ks = lines[k].strip()
                    if not ks or ks.startswith('//') or ks.startswith('/*'):
                        continue
                    # 变量声明行（类型名 + 变量名，结尾有分号但无括号）
                    is_decl = False
                    if ks.endswith(';'):
                        tokens = ks.split()
                        if (tokens and tokens[0] in _TYPE_KW and
                            len(tokens) >= 2 and tokens[1] not in ('{', '}', '(') and
                            not tokens[1].startswith('*')):
                            is_decl = True
                    if is_decl:
                        last_decl_line = k
                    else:
                        # 非声明行 → 在它之前注入（即最后一个声明行之后）
                        inject_line = last_decl_line
                        break
            injections.setdefault(inject_line, []).append(injection)

            # 链表头变量：ENTER 后追加初始列表快照（捕获声明初始化后的链表状态）
            if is_main and list_head_var and list_tname:
                snap = f'    TRACE_EXEC({entry_line_no}, _V_LIST_{list_tname}("{list_head_var}", {list_head_var}));'
                injections.setdefault(inject_line, []).append(snap)

        # ---- 2) TRACE_EXEC (赋值/声明) ----
        # 为数组参数找到对应的长度变量名（函数参数中 sizeof 不可用）
        # 只使用明确命名的长度变量（n/size/len/length/count/sz/num），
        # 避免误用 low/high/target 等非长度参数
        _LEN_NAMES = {'n', 'size', 'len', 'length', 'count', 'sz', 'num', 'N'}
        array_len_map = {}
        for pn in func['param_names']:
            pvi = next((v for v in var_info if v['name'] == pn), None)
            if pvi and pvi.get('is_array'):
                for candidate in func['param_names']:
                    if candidate == pn:
                        continue
                    cvi = next((v for v in var_info if v['name'] == candidate), None)
                    if cvi and not cvi.get('is_array') and not cvi.get('is_pointer'):
                        if candidate in _LEN_NAMES:
                            array_len_map[pn] = candidate
                            break
                if pn not in array_len_map and 'V' in func['param_names']:
                    array_len_map[pn] = 'V'

        def array_length_expr(vn, vi):
            len_var = array_len_map.get(vn)
            if len_var:
                return len_var
            dim = vi.get('arr_dim') if vi else None
            if dim and re.fullmatch(r'\d+', str(dim).strip()):
                return str(dim).strip()
            if dim and str(dim).strip() in ('MAX_V', 'MAXN', 'MAX'):
                if 'V' in tracked:
                    return 'V'
                if 'n' in tracked:
                    return 'n'
            if vn in all_array_lens:
                return str(all_array_lens[vn])
            return f'sizeof({vn})/sizeof({vn}[0])'

        for a in data['assigns']:
            vn = a['var_name']
            if vn not in tracked or a.get('is_deref'):
                continue
            vi = next((v for v in var_info if v['name'] == vn), None)
            if (
                a.get('is_array_index')
                and global_bipartite_graph
                and vn in {global_bipartite_graph['graph'], global_bipartite_graph['match']}
            ):
                vi = {
                    'name': vn,
                    'is_array': True,
                    'is_bipartite_state': True,
                }
            if a.get('is_array_index') and not (vi and vi.get('is_array')):
                continue  # 未知长度的全局数组元素赋值，避免把数组名当地址打印
            line_no = a['line'] + 1
            indent = ' ' * (len(lines[a['line']]) - len(lines[a['line']].lstrip()))
            if vi and vi.get('is_array'):
                if vi.get('is_bipartite_state') and global_bipartite_graph:
                    body = (
                        f'_V_BIPARTITE("{global_bipartite_graph["name"]}", '
                        f'{global_bipartite_graph["graph"]}, {global_bipartite_graph["match"]}, '
                        f'{global_bipartite_graph["left"]}, {global_bipartite_graph["right"]})'
                    )
                else:
                    sfield = vi.get('struct_field')
                    if sfield:
                        body = f'_V_ARR_STRUCT("{vn}", {vn}, {array_length_expr(vn, vi)}, {sfield})'
                    else:
                        arr_type = vi.get('type', 'int')
                        macro = '_V_ARRF' if arr_type in ('double', 'float') else '_V_ARR'
                        if vi.get('is_2d'):
                            rows = vi.get('arr_dim', '1')
                            cols = vi.get('arr_dim2', '1')
                            body = f'_V_ARR2("{vn}", {vn}, {rows}, {cols})'
                        else:
                            body = f'{macro}("{vn}", {vn}, {array_length_expr(vn, vi)})'
            # 链表变量：头指针用列表快照，其他指针用位置追踪
            elif list_head_var and list_tname:
                info = linked_structs.get(list_tname, {})
                vf = info.get('val', 'val')
                nf = info.get('next', 'next')
                if vn == list_head_var:
                    body = f'_V_LIST_{list_tname}("{vn}", {vn})'
                elif nf in ('next', 'nxt', 'link') and (vn in func['param_names'] or any(v['name'] == vn and v.get('is_pointer') for v in var_info)):
                    body = f'_V_INT("{vn}", _trace_pos((void*){list_head_var}, (void*){vn}, offsetof(struct {list_tname}, {vf}), offsetof(struct {list_tname}, {nf})))'
                else:
                    body = f'_V_INT("{vn}", {vn})'
            elif vi and vi.get('is_pointer'):
                continue  # 普通指针变量不输出原始地址
            else:
                macro = '_V_FLOAT' if vi and vi.get('type') in ('double', 'float') else '_V_INT'
                body = f'{macro}("{vn}", {vn})'
            injection = f'{indent}TRACE_EXEC({line_no}, {body});'
            injections.setdefault(a['line'], []).append(injection)

        # ---- 3) TRACE_COND (条件/循环头) ----
        for c in data['conds']:
            cond_expr = extract_cond_expr(lines[c['line']])
            if not cond_expr:
                continue
            line_no = c['line'] + 1
            indent = ' ' * (len(lines[c['line']]) - len(lines[c['line']].lstrip()))
            linfo = linked_structs.get(list_tname, {}) if list_tname else {}
            list_ctx = {'head_var': list_head_var, 'tname': list_tname,
                        'val_field': linfo.get('val', 'val'),
                        'next_field': linfo.get('next', 'next')} if list_head_var and list_tname else None
            seq = make_var_seq(var_info, tracked, cond_expr, list_ctx)
            body = build_body_line(seq)
            # 检查 for/while 循环体是否有大括号
            # 情况1: for(...) {  → 有大括号，不需处理
            # 情况2: for(...) stmt;  → 单行体，不处理（保持原样）
            # 情况3: for(...)\n    stmt;  → 无大括号，需加 {} 包裹
            next_line_idx = c['line'] + 1
            header_ends_with_brace = '{' in lines[c['line']]
            # 对于 if 没有大括号的：检查下一行/下N行是否有 else（多行 if-else 结构）
            # 如果有 else，COND 会破坏 if-else 对应关系，直接跳过
            if c['type'] == 'if' and not header_ends_with_brace:
                has_else = False
                skip_lines = set()
                body_line = next_line_idx
                if body_line < len(lines) and lines[body_line].strip():
                    # 简单探测：在几个缩进层级内找 else
                    indent_len = len(indent)
                    for k in range(body_line, min(func['end'] + 1, len(lines))):
                        kl = lines[k].strip()
                        if not kl or kl.startswith('//'):
                            if kl.startswith('//'):
                                skip_lines.add(k)
                            continue
                        ki = len(lines[k]) - len(lines[k].lstrip())
                        if ki < indent_len and kl:
                            break
                        if kl.startswith('else') and ki == indent_len:
                            has_else = True
                            break
                        if ki <= indent_len:
                            break
                if has_else:
                    continue
            # 检查 body 是否在同一行上（for/while/if 都可能单行体）
            one_line_body = False
            stripped_line = lines[c['line']].strip()
            if c['type'] in ('for', 'while', 'if'):
                # 用括号匹配找到条件的右括号
                paren_start = stripped_line.index('(')
                depth = 0
                paren_end = -1
                for i in range(paren_start, len(stripped_line)):
                    if stripped_line[i] == '(':
                        depth += 1
                    elif stripped_line[i] == ')':
                        depth -= 1
                        if depth == 0:
                            paren_end = i
                            break
                after_header = stripped_line[paren_end + 1:].strip() if paren_end > 0 else ''
                if after_header and not after_header.startswith('{'):
                    one_line_body = True
            next_is_brace = (next_line_idx < len(lines) and
                            '{' in lines[next_line_idx].strip() and
                            lines[next_line_idx].strip() == '{')
            needs_braces = (c['type'] in ('for', 'while', 'if') and
                           not header_ends_with_brace and
                           not next_is_brace and
                           not one_line_body and
                           next_line_idx < len(lines) and
                           lines[next_line_idx].strip())
            # 单行 for/while body：如果 body 在同一行且使用了 C99 声明变量 (int i=...)
            # COND 不能放在下一行（变量作用域只在那一行），跳过
            if one_line_body and c['type'] in ('for', 'while'):
                has_c99_decl = bool(re.match(r'(for|while)\s*\(\s*(?:int|float|char|size_t)\s+\w+', stripped_line))
                if has_c99_decl:
                    continue
            if needs_braces:
                # 注入: 先在 for 头后面加 `{`，然后 TRACE_COND 在 `{` 之后
                brace_injection = f'{indent}{{'
                injections.setdefault(c['line'], []).append(brace_injection)
                # 找到循环体结束行
                body_line = next_line_idx
                end_line = body_line
                indent_len = len(indent)
                for k in range(body_line + 1, min(func['end'] + 1, len(lines))):
                    kl = lines[k].strip()
                    if not kl or kl.startswith('//'):
                        continue
                    ki = len(lines[k]) - len(lines[k].lstrip())
                    if ki <= indent_len and kl:
                        end_line = k - 1
                        break
                else:
                    end_line = min(func['end'], len(lines) - 1)
                # 在循环体最后一行后加 TRACE_COND + }
                injections.setdefault(end_line, []).append(f'{indent}TRACE_COND({line_no}, ({cond_expr}), {body});')
                injections.setdefault(end_line, []).append(f'{indent}}}');
            else:
                injection = f'{indent}TRACE_COND({line_no}, ({cond_expr}), {body});'
                injections.setdefault(c['line'], []).append(injection)

        # ---- 4) TRACE_EXIT (return 前) + return 值捕获 ----
        for r in data['rets']:
            line_no = r['line'] + 1
            ret_line = r['line']
            indent = ' ' * (len(lines[ret_line]) - len(lines[ret_line].lstrip()))
            # 检查是否跨行 return
            expr_end = _find_expr_end(lines, ret_line, func['end'])
            is_multi = (expr_end > ret_line)
            m = re.match(r'return\s+(.+?)\s*;', r['text'])
            if m:
                ret_val = m.group(1).strip()
                ret_type = func.get('ret_type', 'int')
                captures_return_value = '*' not in ret_type
                ret_macro = '_V_FLOAT' if any(t in ret_type for t in ('double', 'float')) else '_V_INT'
                # 如果 return 跨多行，需要把整个表达式搬到临时变量里
                if is_multi:
                    # 收集多行表达式内容
                    full_expr = ret_val
                    for li in range(ret_line + 1, expr_end + 1):
                        full_expr += ' ' + lines[li].rstrip('\n').rstrip(';')
                    # 用函数返回类型声明临时变量
                    tmp_var = f'_ret_{name}'
                    existing_names = {v['name'] for v in var_info} | set(func['param_names'])
                    while tmp_var in existing_names:
                        tmp_var = '_' + tmp_var
                    # 将 return 行替换成完整块
                    lines[ret_line] = (
                        f'{indent}{{ {ret_type} {tmp_var} = ({full_expr}); '
                        + (f'TRACE_EXEC({line_no}, {ret_macro}("_return", {tmp_var})); ' if captures_return_value else '')
                        +
                        f'TRACE_EXIT({line_no}, "{name}"); '
                        f'return {tmp_var}; }}'
                    )
                    # 清除多行 return 的后续行（用空行占位防止后续 injection 错位）
                    for li in range(ret_line + 1, expr_end + 1):
                        lines[li] = ''
                else:
                    # 单行 return：tmp=ret; TRACE_EXEC; TRACE_EXIT; return tmp;
                    tmp_var = f'_ret_{name}'
                    existing_names = {v['name'] for v in var_info} | set(func['param_names'])
                    while tmp_var in existing_names:
                        tmp_var = '_' + tmp_var
                    lines[ret_line] = (
                        f'{indent}{{ {ret_type} {tmp_var} = ({ret_val}); '
                        + (f'TRACE_EXEC({line_no}, {ret_macro}("_return", {tmp_var})); ' if captures_return_value else '')
                        +
                        f'TRACE_EXIT({line_no}, "{name}"); '
                        f'return {tmp_var}; }}'
                    )
            else:
                # void return: TRACE_EXIT + return;
                injection_exit = f'{indent}TRACE_EXIT({line_no}, "{name}");'
                injections.setdefault(r['line'], []).append(injection_exit)

        # ---- 5) 函数调用点: TRACE_ENTER（调用侧） ----
        for call in data['calls']:
            line_no = call['caller_line'] + 1
            callee = call['callee']
            arg_names = call['arg_names']

            # 表达式内调用跳过（printf 参数、三元表达式等）
            if call.get('in_expr', False):
                continue

            stripped = lines[call['caller_line']]
            indent = ' ' * (max(0, len(stripped) - len(stripped.lstrip())))

            # 被调用函数的参数信息
            callee_func = func_map.get(callee, {})
            callee_params = callee_func.get('param_names', [])
            callee_data = all_data.get(callee, {})
            callee_locals = callee_data.get('locals', [])
            callee_var_info = {}
            for v in callee_locals:
                callee_var_info[v['name']] = v
            # 从函数签名判断参数是否为数组/指针
            callee_params_str = callee_func.get('params_str', '')
            for pn in callee_params:
                if pn not in callee_var_info:
                    # 在函数签名中精确匹配该参数（用单词边界避免 r 匹配 arr 后半截）
                    param_decl = get_param_decl(callee_params_str, pn)
                    is_arr = is_param_array(param_decl, pn)
                    is_2d = is_param_2d_array(param_decl, pn)
                    is_ptr = is_param_pointer(param_decl, pn)
                    ptype = 'int'
                    for bt in ['double', 'float', 'char']:
                        if bt in param_decl: ptype = bt; break
                    param_entry = {'name': pn, 'is_array': is_arr, 'is_2d': is_2d, 'is_pointer': is_ptr, 'type': ptype}
                    # 检测结构体数组参数
                    if is_arr and struct_defs:
                        for sname, sfields in struct_defs.items():
                            if re.search(rf'\b{re.escape(sname)}\b.*\b{re.escape(pn)}\b', param_decl):
                                for fname, ftype, fptr in sfields:
                                    if 'int' in ftype and not fptr:
                                        param_entry['struct_type'] = sname
                                        param_entry['struct_field'] = fname
                                        break
                                break
                    callee_var_info[pn] = param_entry

            # 从调用参数推断数组有效长度: partition(arr, low, high) → high-low+1
            def guess_array_len(all_args, callee_params_list):
                cpn = [p.lower() for p in callee_params_list]
                low_keys = {'low', 'left', 'l', 'start', 'begin', 'lo'}
                high_keys = {'high', 'right', 'r', 'end', 'hi'}
                for li, lc in enumerate(cpn):
                    if lc in low_keys:
                        for hi, hc in enumerate(cpn):
                            if hc in high_keys and hi != li:
                                if li < len(all_args) and hi < len(all_args):
                                    return f'(({all_args[hi].strip()}) - ({all_args[li].strip()}) + 1)'
                # fallback: 检查是否有简单整型参数可能是长度
                for ai in range(len(all_args)):
                    a = all_args[ai].strip()
                    if ai < len(cpn) and cpn[ai] in {'n', 'v', 'len', 'size', 'length', 'count', 'cnt'}:
                        return a
                return None

            def guess_node_count(all_args, callee_params_list):
                for ai, pname in enumerate(callee_params_list):
                    if ai < len(all_args) and pname in {'V', 'n', 'N', 'vertices'}:
                        return all_args[ai].strip()
                return None

            tree_root_args = {}
            for pidx, pname in enumerate(callee_params):
                if pidx >= len(arg_names):
                    continue
                pvi = callee_var_info.get(pname, {})
                if not pvi.get('is_pointer'):
                    continue
                sm = re.search(rf'struct\s+(\w+)\s*\*\s*{re.escape(pname)}', callee_params_str)
                if sm and sm.group(1) in tree_structs:
                    tname = sm.group(1)
                    if tname not in tree_root_args or pname in ('root', 'head'):
                        tree_root_args[tname] = arg_names[pidx].strip()

            enter_parts = []
            node_count_expr = guess_node_count(arg_names, callee_params)
            if not node_count_expr and 'n' in tracked:
                node_count_expr = 'n'
            if global_head_edge_graph and node_count_expr and callee in {'tarjan'}:
                enter_parts.append((
                    'graph_head_edges',
                    global_head_edge_graph['name'],
                    global_head_edge_graph['head'],
                    global_head_edge_graph['edges'],
                    node_count_expr,
                ))
            if node_count_expr and global_matrix_graphs:
                for gname in global_matrix_graphs:
                    if gname == 'capacity' and callee in {'edmonds_karp', 'bfs'}:
                        if enter_parts:
                            enter_parts.append(('comma',))
                        enter_parts.append(('graph_matrix', gname, gname, node_count_expr))
            if global_bipartite_graph and callee in {'hungarian', 'dfs'}:
                if enter_parts:
                    enter_parts.append(('comma',))
                enter_parts.append((
                    'bipartite',
                    global_bipartite_graph['name'],
                    global_bipartite_graph['graph'],
                    global_bipartite_graph['match'],
                    global_bipartite_graph['left'],
                    global_bipartite_graph['right'],
                ))
            for idx, an in enumerate(arg_names):
                an = an.strip()
                if idx < len(callee_params):
                    param_name = callee_params[idx]
                    cvi = callee_var_info.get(param_name, {})
                    is_arr = cvi.get('is_array', False)
                    is_ptr = cvi.get('is_pointer', False)
                    if is_ptr and not is_arr:
                        # 树节点指针：root 显示整棵树，p/q/node 这类指针显示所在节点值。
                        struct_match = re.search(rf'struct\s+(\w+)\s*\*\s*{re.escape(param_name)}', callee_params_str)
                        if struct_match and struct_match.group(1) in tree_structs:
                            tname = struct_match.group(1)
                            if enter_parts:
                                enter_parts.append(('comma',))
                            root_arg = tree_root_args.get(tname, an)
                            if param_name in ('root', 'head') or an == root_arg:
                                enter_parts.append(('tree', param_name, an, tname))
                            else:
                                enter_parts.append(('tree_ref', param_name, an, root_arg, tname))
                        # 链表节点指针：生成列表快照（仅限线性链表，排除树/图）
                        elif struct_match and struct_match.group(1) in linked_structs:
                            tname = struct_match.group(1)
                            if linked_structs[tname].get('next', '') in ('next', 'nxt', 'link'):
                                if enter_parts:
                                    enter_parts.append(('comma',))
                                enter_parts.append(('list', param_name, an, tname))
                        continue
                    if is_arr:
                        arr_len = guess_array_len(arg_names, callee_params)
                        if param_name.lower() in ('edges', 'edge'):
                            for eidx, pname in enumerate(callee_params):
                                if pname in {'E', 'edgeCount', 'm', 'M'} and eidx < len(arg_names):
                                    arr_len = arg_names[eidx].strip()
                                    break
                        # 优先用声明长度（完整数组），子数组范围从 low/high 参数可知
                        if an in all_array_lens:
                            arr_len = str(all_array_lens[an])
                        if arr_len:
                            if enter_parts:
                                enter_parts.append(('comma',))
                            sfield = cvi.get('struct_field')
                            struct_type = cvi.get('struct_type')
                            if struct_type in graph_adj_structs and param_name.lower() in ('graph', 'adj', 'adjlist'):
                                enter_parts.append(('graph_adj', param_name, an, arr_len, struct_type))
                            elif struct_type in graph_edge_structs or param_name.lower() in ('edges', 'edge'):
                                node_count = guess_node_count(arg_names, callee_params)
                                if node_count:
                                    enter_parts.append(('graph_edges', param_name, an, arr_len, node_count))
                                elif sfield:
                                    enter_parts.append(('array_struct', param_name, an, arr_len, sfield))
                            elif sfield:
                                enter_parts.append(('array_struct', param_name, an, arr_len, sfield))
                            elif cvi.get('is_2d') and param_name.lower() in ('graph', 'capacity'):
                                enter_parts.append(('graph_matrix', param_name, an, arr_len))
                            else:
                                arr_kind = 'arrayf' if cvi.get('type','int') in ('double','float') else 'array'
                                enter_parts.append((arr_kind, param_name, an, arr_len))
                        # 无法推断长度时跳过（避免打印垃圾指针数据）
                    else:
                        if enter_parts:
                            enter_parts.append(('comma',))
                        scalar_kind = 'float' if cvi.get('type') in ('double', 'float') else 'int'
                        enter_parts.append((scalar_kind, param_name, an))
                else:
                    if enter_parts:
                        enter_parts.append(('comma',))
                    enter_parts.append(('int', f'arg{idx}', an))

            body = build_body_line(enter_parts)
            if body:
                call_line = call['caller_line']
                inject_line = call_line

                injection = f'{indent}TRACE_ENTER({line_no}, "{callee}", {body});'

                # 如果调用在 for/while/do 循环头里（如 for(int i=x; i<=n; i+=f(i))），
                # TRACE_ENTER 要注入到循环体 { 之后（此时 i 已声明）
                call_stripped = lines[call_line].strip()
                if re.match(r'^(for|while|do)\b', call_stripped):
                    found_brace = False
                    for m in range(call_line, min(call_line + 5, len(lines))):
                        if '{' in lines[m]:
                            inject_line = m + 1  # 循环体第一行
                            found_brace = True
                            break
                    if found_brace:
                        before_injections.setdefault(inject_line, []).append(injection)
                        continue

                    # 没有找到 { → 循环体可能在同一行（如 for(...) stmt;）
                    # 需要正确匹配 for/while 条件的右括号（不能简单 rfind）
                    paren_start = call_stripped.index('(')
                    depth = 0
                    paren_end = -1
                    for i in range(paren_start, len(call_stripped)):
                        if call_stripped[i] == '(':
                            depth += 1
                        elif call_stripped[i] == ')':
                            depth -= 1
                            if depth == 0:
                                paren_end = i
                                break
                    after_cond = call_stripped[paren_end + 1:].strip() if paren_end > 0 else ''
                    if after_cond and not after_cond.startswith('{'):
                        # 单行循环体 → 包裹大括号，把 TRACE_ENTER 放入循环体内
                        body_stmt = after_cond
                        if body_stmt.endswith(';'):
                            body_stmt = body_stmt[:-1].strip()
                        header = call_stripped[:paren_end + 1]
                        lines[call_line] = (
                            f'{header} {{\n'
                            f'{indent}    {injection}\n'
                            f'{indent}    {body_stmt};\n'
                            f'{indent}}}'
                        )
                    # 替换了整行，不需要 before_injections
                    continue

                before_injections.setdefault(inject_line, []).append(injection)

    # ---- 合成插桩后源码 ----
    result_lines = []
    for i, line in enumerate(lines):
        # before injections (e.g., TRACE_ENTER before a function call)
        if i in before_injections:
            for inj in sorted(before_injections[i]):
                result_lines.append(inj)
        result_lines.append(line)
        if i in injections:
            for inj in sorted(injections[i]):
                result_lines.append(inj)

    # ---- 后处理: 修复 if/else 无大括号导致的语法错误 ----
    # 当 TRACE_ENTER 注入到 if/else body 第一行前面时，需要把 body 包在 {} 里
    fixed_lines = []
    i = 0
    while i < len(result_lines):
        s = result_lines[i].strip()
        # 检测: if/else 行后面紧跟 TRACE_ENTER（无大括号）
        m_if = re.match(r'^(if|else\s*if|else)\s*(\(.*\))?\s*$', s)
        if m_if and i + 1 < len(result_lines):
            ns = result_lines[i + 1].strip()
            if ns.startswith('TRACE_ENTER(') or ns.startswith('TRACE_COND('):
                # 找到 body 结束行（闭合大括号或下一个 else/else if）
                body_start = i + 1
                # 找到整个 body 的范围（包括大括号块）
                j = body_start
                depth = 0
                body_end = body_start
                has_braces = False
                while j < len(result_lines):
                    cs = result_lines[j].strip()
                    for ch in cs:
                        if ch == '{': depth += 1; has_braces = True
                        elif ch == '}': depth -= 1
                    if depth < 0:
                        break  # 找到了闭合 }，body 结束
                    if j > body_start and depth == 0:
                        # 没有大括号，body 就是单条语句
                        body_end = j
                        break
                    if j > body_start and not has_braces and depth == 0:
                        body_end = j
                        break
                    body_end = j
                    j += 1
                # 如果 body 没有大括号，需要包裹
                if not has_braces:
                    indent = ' ' * (len(result_lines[i]) - len(result_lines[i].lstrip()))
                    # 收集 body 行
                    body_lines = result_lines[body_start:body_end + 1]
                    # 把 TRACE_ENTER 放在 body 第一行前面（在大括号内）
                    fixed_lines.append(result_lines[i])  # if/else 行
                    fixed_lines.append(indent + '{')
                    for bl in body_lines:
                        fixed_lines.append(bl)
                    fixed_lines.append(indent + '}')
                    i = body_end + 1
                    continue
        fixed_lines.append(result_lines[i])
        i += 1

    result = '\n'.join(fixed_lines)
    return TRACE_HEADER + '\n' + list_macros + tree_macros + graph_adj_macros + '\n' + result


# =====================================================================
# 第三步: 编译运行
# =====================================================================

def compile_and_run(source_code):
    tmpdir = tempfile.mkdtemp(prefix='algo_trace_')
    src_path = os.path.join(tmpdir, 'prog.c')
    bin_path = os.path.join(tmpdir, 'prog')

    with open(src_path, 'w', encoding='utf-8') as f:
        f.write(source_code)

    try:
        proc = subprocess.run(
            ['gcc', '-std=c99', '-w', '-o', bin_path, src_path],
            capture_output=True, text=True, timeout=15
        )
        if proc.returncode != 0:
            err = proc.stderr[:500].replace('\n', ' ')
            return [], f"编译失败: {err}"
    except subprocess.TimeoutExpired:
        return [], "编译超时"
    except FileNotFoundError:
        return [], "gcc 未安装"

    try:
        proc = subprocess.run(
            [bin_path], capture_output=True, text=True,
            timeout=RUN_TIMEOUT_SEC,
            input="1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\n",  # 默认输入：n=1避免无限递归,m=0跳过循环
            env={**os.environ, 'LC_ALL': 'C'},
        )
        stdout = proc.stdout
        max_bytes = MAX_STDOUT_MB * 1024 * 1024
        if len(stdout) > max_bytes:
            stdout = stdout[:max_bytes]
        if proc.returncode != 0 and proc.returncode != -9:
            if stdout.strip():
                return stdout.strip().split('\n'), None
            return [], f"运行异常(exit={proc.returncode})"
        return stdout.strip().split('\n') if stdout.strip() else [], None
    except subprocess.TimeoutExpired:
        return [], "运行超时"
    finally:
        try:
            os.unlink(src_path)
            os.unlink(bin_path)
            os.rmdir(tmpdir)
        except:
            pass


def parse_trace_lines(stdout_lines):
    steps = []
    program_output = []   # 程序 printf 输出
    step_idx = 0
    for line in stdout_lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('{'):
            try:
                s = json.loads(line)
                if 'type' in s:
                    step_idx += 1
                    steps.append(s)
            except json.JSONDecodeError:
                pass
        else:
            # 检查是否混杂了 printf 输出和 trace JSON（如 loop 中 printf）
            # 格式: "text{" 或 "text {"  → 拆分为文本和 JSON
            brace_pos = line.find('{')
            if brace_pos > 0:
                text_part = line[:brace_pos].strip()
                json_part = line[brace_pos:]
                if text_part:
                    program_output.append({'after_step': step_idx, 'text': text_part})
                try:
                    s = json.loads(json_part)
                    if 'type' in s:
                        step_idx += 1
                        steps.append(s)
                except json.JSONDecodeError:
                    program_output.append({'after_step': step_idx, 'text': line})
            else:
                program_output.append({'after_step': step_idx, 'text': line})
    # 合并循环内 printf 的连续输出（步号间隔 ≤ 2 视为同一输出段）
    merged_output = []
    buf = []
    last_step = -9
    for o in program_output:
        gap = o['after_step'] - last_step
        if 0 <= gap <= 2 and buf:
            buf.append(o['text'])
        else:
            if buf:
                merged_output.append({'after_step': buf_start_step, 'text': ' '.join(buf)})
            buf = [o['text']]
            buf_start_step = o['after_step']
        last_step = o['after_step']
    if buf:
        merged_output.append({'after_step': buf_start_step, 'text': ' '.join(buf)})
    return steps, merged_output


# =====================================================================
# 第四步: 智能策展（跳步）
# =====================================================================

def curate_trace(steps):
    """检测循环重复并省略中间部分"""
    if len(steps) <= MAX_LOOP_SKIP:
        for i, s in enumerate(steps):
            s['step'] = i
        return steps

    best = None  # (start_idx, pattern_len, repeat_count, end_idx)

    for ws in [6, 5, 4, 3, 8]:
        line_seq = [s.get('line', 0) for s in steps]
        n = len(line_seq)
        i = 0
        while i < n - ws * 3:
            pattern = tuple(line_seq[i:i + ws])
            repeat = 1
            j = i + ws
            while j + ws <= n:
                if tuple(line_seq[j:j + ws]) == pattern:
                    repeat += 1
                    j += ws
                else:
                    break
            if repeat >= 4:
                end_idx = j
                if best is None or repeat > best[2]:
                    best = (i, ws, repeat, end_idx)
                i = j
            else:
                i += 1

    if best is None:
        for i, s in enumerate(steps):
            s['step'] = i
        return steps

    start_idx, pattern_len, repeat_count, end_idx = best
    keep_head = 2
    keep_tail = 2

    if repeat_count <= keep_head + keep_tail:
        for i, s in enumerate(steps):
            s['step'] = i
        return steps

    skip_start = start_idx + keep_head * pattern_len
    skip_end = end_idx - keep_tail * pattern_len

    if skip_end <= skip_start:
        for i, s in enumerate(steps):
            s['step'] = i
        return steps

    skipped_count = skip_end - skip_start
    new_steps = (
        steps[:skip_start] +
        [{'step': 0, 'type': 'skip', 'skipped': skipped_count, 'line': 0, 'vars': {}}] +
        steps[skip_end:]
    )

    for i, s in enumerate(new_steps):
        s['step'] = i

    return curate_trace(new_steps)


# =====================================================================
# 第五步: 合成兜底轨迹
# =====================================================================

def generate_synthetic_trace(c_path, source):
    """编译运行失败时的兜底轨迹"""
    lines = source.split('\n')
    steps = []
    functions = find_functions(lines)

    if not functions:
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('//') and not stripped.startswith('/*'):
                steps.append({'step': len(steps), 'line': i + 1, 'type': 'exec', 'vars': {}})
        return {
            'meta': {'algo': c_path.stem.replace(' ', '_'), 'source_lines': lines,
                     'track_vars': [], 'viz_type': 'none', 'initial_data': {},
                     'synthetic': True},
            'steps': steps, 'total_steps': len(steps)
        }

    for func in functions:
        params = func['param_names']
        steps.append({'step': len(steps), 'line': func['body_start'] + 1,
                      'type': 'enter', 'func': func['name'],
                      'vars': {p: 0 for p in params}})
        for i in range(func['body_start'] + 1, func['end']):
            stripped = lines[i].strip()
            if stripped and not stripped.startswith('//') and not stripped.startswith('/*') and not stripped.startswith('#') and 'TRACE_' not in stripped:
                steps.append({'step': len(steps), 'line': i + 1, 'type': 'exec', 'vars': {}})
        steps.append({'step': len(steps), 'line': func['end'] + 1,
                      'type': 'exit', 'func': func['name'], 'vars': {}})

    return {
        'meta': {'algo': c_path.stem.replace(' ', '_'), 'source_lines': lines,
                 'track_vars': [], 'viz_type': 'none', 'initial_data': {},
                 'synthetic': True},
        'steps': steps, 'total_steps': len(steps)
    }


# =====================================================================
# 第六步: 组装完整 trace JSON
# =====================================================================

def process_file(c_path):
    """处理单个 C 文件，返回 (trace, error)"""
    source = read_source(c_path)
    raw_lines = source.split('\n')
    source = strip_existing_trace(source)

    instrumented = instrument_source(source)
    stdout_lines, error = compile_and_run(instrumented)

    if error:
        return generate_synthetic_trace(c_path, source), error

    raw_steps, program_output = parse_trace_lines(stdout_lines)
    if not raw_steps:
        return generate_synthetic_trace(c_path, source), "没有产生任何步骤"

    steps = curate_trace(raw_steps)

    # 提取数组初始值
    arrays = {}
    for m in re.finditer(r'(?:int|float|double)\s+(\w+)\s*\[\s*\]\s*=\s*\{([^}]+)\}', source):
        name = m.group(1)
        vals = []
        for v in m.group(2).split(','):
            try:
                vals.append(int(v.strip()))
            except ValueError:
                try:
                    vals.append(float(v.strip()))
                except ValueError:
                    vals.append(v.strip())
        arrays[name] = vals

    # 收集变量 & 分类
    all_var_names = set()
    scalar_samples = {}
    for s in steps:
        if s['type'] != 'skip':
            for k, v in s.get('vars', {}).items():
                all_var_names.add(k)
                if not isinstance(v, list):
                    scalar_samples.setdefault(k, []).append(v)

    # 自动分类变量
    var_classes = {}
    primary_vars = []
    secondary_vars = []
    # 从 steps 中区分数组变量、链表和树快照变量
    # 数组：出现在 exec 步骤中（_V_ARR 追踪每次赋值）
    # 链表：仅出现在 enter 步骤中（_V_LIST 在函数入口快照）
    enter_list_vars = set()
    exec_arr_vars = set()
    tree_vars = set()
    graph_vars = set()
    bipartite_vars = set()
    for s in steps:
        if s['type'] == 'skip': continue
        for k, v in s.get('vars', {}).items():
            if isinstance(v, dict) and 'left' in v and 'right' in v and 'edges' in v:
                bipartite_vars.add(k)
                continue
            if isinstance(v, dict) and 'nodes' in v and 'edges' in v:
                graph_vars.add(k)
                continue
            if not isinstance(v, list): continue
            if is_tree_snapshot(v):
                tree_vars.add(k)
                continue
            if s['type'] == 'enter':
                enter_list_vars.add(k)
            elif s['type'] == 'exec':
                exec_arr_vars.add(k)

    # 链表变量：enter 中有数组值，且源码中声明为 struct 指针（非 int[] 数组）
    list_vars = set()
    for k in enter_list_vars:
        if k not in arrays and k not in tree_vars:
            # 检查源码中是否为 struct 指针声明
            is_struct_ptr = bool(re.search(rf'struct\s+\w+\s*\*\s*{re.escape(k)}\b', source))
            if is_struct_ptr:
                list_vars.add(k)
    # exec 中出现的非 list 变量 → 数组，补全到 arrays
    for vn in exec_arr_vars:
        if vn not in arrays:
            for s in steps:
                val = s.get('vars', {}).get(vn)
                if isinstance(val, list):
                    arrays[vn] = val
                    break
    # 补全 arrays：正则只能匹配带初始化器的局部数组声明，
    # 函数参数数组（int arr[]）需要通过 trace 中的数组值来识别
    for vn in sorted(all_var_names):
        if vn not in arrays and vn not in list_vars and vn not in tree_vars:
            for s in steps:
                val = s.get('vars', {}).get(vn)
                if isinstance(val, list) and not is_tree_snapshot(val):
                    arrays[vn] = val
                    break

    # 从 steps 中找 2D 数组（[[...], [...]] 格式）
    grid_vars = set()
    for s in steps:
        if s['type'] != 'skip':
            for k, v in s.get('vars', {}).items():
                if isinstance(v, list) and len(v) > 0 and isinstance(v[0], list):
                    grid_vars.add(k)

    for vn in sorted(all_var_names):
        is_arr = any(vn == name for name in arrays)
        is_list = vn in list_vars
        is_tree = vn in tree_vars
        is_graph = vn in graph_vars
        is_bipartite = vn in bipartite_vars
        is_grid = vn in grid_vars
        cls = classify_variable(vn, is_array=(is_arr or is_list or is_tree or is_graph or is_bipartite or is_grid))
        if is_bipartite:
            vtype = 'bipartite'
        elif is_graph:
            vtype = 'graph'
        elif is_grid:
            vtype = 'grid'
        elif is_tree:
            vtype = 'tree'
        elif is_list:
            vtype = 'list'
        elif is_arr:
            vtype = 'array'
        else:
            vtype = 'scalar'
        if vtype == 'scalar' and looks_like_pointer_scalar(vn, scalar_samples.get(vn, [])):
            cls = 'hidden'
        var_classes[vn] = {
            'category': cls,
            'type': vtype
        }
        if cls == 'primary':
            primary_vars.append(vn)
        elif cls == 'secondary':
            secondary_vars.append(vn)
        # hidden 变量不加入任何列表

    # 对超大数组的 initial_data 也截断
    trimmed_arrays = {}
    for name, vals in arrays.items():
        trimmed, was_trimmed = trim_array_values(vals)
        trimmed_arrays[name] = trimmed

    # 从 steps 中移除 hidden 变量，截断超大数组
    for s in steps:
        if s['type'] != 'skip' and s.get('vars'):
            s['vars'] = trim_array_in_vars(s['vars'], var_classes)

    # 压缩源码：去掉空行并重映射步骤行号
    old_to_new = {}
    compressed_lines = []
    new_idx = 1
    for i, line in enumerate(raw_lines):
        if line.strip() != '':
            old_to_new[i + 1] = new_idx  # 1-indexed → 1-indexed
            compressed_lines.append(line)
            new_idx += 1
    for s in steps:
        if s.get('line') and s['line'] in old_to_new:
            s['line'] = old_to_new[s['line']]

    trace = {
        'meta': {
            'algo': c_path.stem.replace(' ', '_'),
            'source_lines': compressed_lines,
            'track_vars': {
                'primary': primary_vars,
                'secondary': secondary_vars,
            },
            'var_classes': var_classes,
            'viz_type': 'array',
            'initial_data': trimmed_arrays,
            'program_output': program_output,
        },
        'steps': steps,
        'total_steps': len(steps)
    }
    return trace, None


# =====================================================================
# main
# =====================================================================

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 auto_instrument.py <input.c> [output.json]")
        print("  python3 auto_instrument.py --batch <src_dir> <trace_dir>")
        sys.exit(1)

    if sys.argv[1] == '--batch':
        src_dir = Path(sys.argv[2])
        trace_dir = Path(sys.argv[3])
        trace_dir.mkdir(parents=True, exist_ok=True)

        total = 0
        skipped = 0
        errors = []

        c_files = sorted([f for f in src_dir.rglob('*.c')])
        print(f"找到 {len(c_files)} 个C文件\n")

        for c_file in c_files:
            algo_id = c_file.stem.replace(' ', '_')
            output_path = trace_dir / f"{algo_id}.json"
            print(f"  {algo_id[:60]:<60} ", end='', flush=True)
            try:
                trace, error = process_file(c_file)
            except Exception as e:
                trace, error = None, str(e)

            if error and error != "编译失败":
                print(f"⚠️ {error[:60]}")
                continue

            if error == "编译失败":
                try:
                    source = read_source(c_file)
                    trace = generate_synthetic_trace(c_file, source)
                    output_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding='utf-8')
                    total += 1
                    skipped += 1
                    print(f"⚠️ 兜底 ({trace['total_steps']} steps) [编译失败]")
                except Exception as e:
                    errors.append(f"{algo_id}: {str(e)[:80]}")
                    print("❌")
                continue

            output_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding='utf-8')
            total += 1
            print(f"✅ ({trace['total_steps']} steps)")

        print(f"\n{'='*60}")
        print(f"✅ 成功: {total}  (含合成兜底: {skipped})")
        if errors:
            print(f"❌ 失败: {len(errors)}")
            for e in errors[:10]:
                print(f"  {e}")
    else:
        c_path = Path(sys.argv[1])
        output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
        trace, error = process_file(c_path)

        if error:
            print(f"⚠️ 注意: {error}")

        if output_path:
            output_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f"✅ 生成 {output_path} ({trace['total_steps']} steps)")
        else:
            print(json.dumps(trace, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
