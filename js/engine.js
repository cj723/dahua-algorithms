// 大话算法 v2 — 共享执行引擎
'use strict';

class TraceEngine {
  constructor(canvasId, codeBodyId, varGridId, callstackId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.codeBody = document.getElementById(codeBodyId);
    this.varGrid = document.getElementById(varGridId);
    this.callstackEl = document.getElementById(callstackId);

    this.algo = null;
    this.currentStep = -1;
    this.state = {};
    this.playing = false;
    this.playTimer = null;
    this.breakpoints = new Set();
    this.callStack = [];
    this.executedLines = new Set();
    this.renderer = null;
    this.prevStepData = null;
    this.fullArrayState = {};  // 维护完整数组状态（workaround for auto_instrument sizeof bug）

    this.codeFontSize = parseInt(localStorage.getItem('dh_font_size')) || 15;
    this._apply_font_size();
    this.loopSkipConfig = { windowSize: 6, minRepeat: 4, skipAhead: 10, minStepsToSkip: 15 };
  }

  // ===== 加载算法 =====
  load(algo) {
    const meta = algo.meta || {};
    if (!algo.source) algo.source = meta.source_lines || [];
    if (!algo.track_vars) algo.track_vars = meta.track_vars || {};
    if (!algo.var_classes) algo.var_classes = meta.var_classes || {};
    if (!algo.initial_data) algo.initial_data = meta.initial_data || {};
    if (!algo.program_output) algo.program_output = meta.program_output || [];
    if (!algo.important_vars) {
      algo.important_vars = {};
      const classes = algo.var_classes;
      Object.entries(classes).forEach(([k, info]) => {
        const cat = (typeof info === 'object') ? info.category : info;
        algo.important_vars[k] = cat === 'primary' ? '主要' : '其他';
      });
      if (Object.keys(algo.important_vars).length === 0) {
        (algo.track_vars.primary || []).forEach(v => { algo.important_vars[v] = '主要'; });
        (algo.track_vars.secondary || []).forEach(v => { algo.important_vars[v] = '其他'; });
      }
    }
    this.algo = algo;
    this.fullArrayState = {};
    for (const [k, v] of Object.entries(algo.initial_data || {})) {
      if (Array.isArray(v)) {
        this.fullArrayState[k] = [...v];
      }
    }
    this._init_code_panel();
    this._init_renderer();
    document.getElementById('step-total').textContent = algo.steps.length;
    this.reset();
    if (typeof NoVisualizationRenderer !== 'undefined' &&
        this.renderer instanceof NoVisualizationRenderer) {
      this.renderer.render({}, null);
    }
    requestAnimationFrame(() => {
      if (this.algo === algo && this.currentStep >= 0) {
        this.go_to_step(this.currentStep);
      }
    });
  }

  // 合并部分数组到完整数组状态
  _merge_array(key, partialArr) {
    if (!this.fullArrayState[key]) {
      if (Array.isArray(partialArr)) this.fullArrayState[key] = [...partialArr];
      return partialArr;
    }
    const full = this.fullArrayState[key];
    if (!Array.isArray(partialArr)) return full;
    if (partialArr.length >= full.length) {
      this.fullArrayState[key] = [...partialArr];
      return partialArr;
    }
    // 部分数组：从索引 0 开始替换（workaround for auto_instrument sizeof bug）
    const merged = [...full];
    for (let i = 0; i < partialArr.length; i++) {
      merged[i] = partialArr[i];
    }
    this.fullArrayState[key] = merged;
    return merged;
  }

  _init_renderer() {
    this.prevStepData = null;
    if (!this.algo) return;
    const rendererType = this._infer_renderer_type();
    if (rendererType === 'concept' && typeof ConceptRenderer !== 'undefined') {
      this.renderer = new ConceptRenderer(this.canvas.id);
    } else if (rendererType === 'string_match' && typeof StringMatchRenderer !== 'undefined') {
      this.renderer = new StringMatchRenderer(this.canvas.id);
    } else if (rendererType === 'bipartite' && typeof BipartiteGraphRenderer !== 'undefined') {
      this.renderer = new BipartiteGraphRenderer(this.canvas.id);
    } else if (rendererType === 'graph' && typeof GraphRenderer !== 'undefined') {
      this.renderer = new GraphRenderer(this.canvas.id);
    } else if (rendererType === 'grid' && typeof GridRenderer !== 'undefined') {
      this.renderer = new GridRenderer(this.canvas.id);
    } else if (rendererType === 'tree' && typeof TreeRenderer !== 'undefined') {
      this.renderer = new TreeRenderer(this.canvas.id);
    } else if (rendererType === 'list' && typeof LinkedListRenderer !== 'undefined') {
      this.renderer = new LinkedListRenderer(this.canvas.id);
    } else if (rendererType === 'array' && typeof ArrayBarRenderer !== 'undefined') {
      this.renderer = new ArrayBarRenderer(this.canvas.id);
      this.renderer.set_initial_data(this.algo.initial_data || {});
    } else if (rendererType === 'scalar' && typeof ScalarStateRenderer !== 'undefined') {
      this.renderer = new ScalarStateRenderer(this.canvas.id);
    } else if (typeof NoVisualizationRenderer !== 'undefined') {
      this.renderer = new NoVisualizationRenderer(this.canvas.id, this._viz_empty_reason());
    } else {
      this.renderer = null;
    }
  }

  _infer_renderer_type() {
    const varClasses = this.algo.var_classes || {};
    const has_step_value = (name, predicate) =>
      (this.algo.steps || []).some(s => predicate((s.vars || {})[name]));

    for (const type of ['concept', 'string_match', 'bipartite', 'graph', 'grid', 'tree', 'list', 'array']) {
      for (const [name, info] of Object.entries(varClasses)) {
        if (!info || info.type !== type) continue;
        if (type === 'concept' && has_step_value(name, v => v && typeof v === 'object' && !Array.isArray(v) && typeof v.kind === 'string')) return 'concept';
        if (type === 'string_match' && has_step_value(name, v => v && typeof v === 'object' && !Array.isArray(v) && typeof v.text === 'string' && typeof v.pattern === 'string')) return 'string_match';
        if (type === 'bipartite' && has_step_value(name, v => v && typeof v === 'object' && !Array.isArray(v) && Array.isArray(v.edges) && Number.isFinite(Number(v.left)) && Number.isFinite(Number(v.right)))) return 'bipartite';
        if (type === 'graph' && has_step_value(name, v => v && typeof v === 'object' && !Array.isArray(v) && Array.isArray(v.edges))) return 'graph';
        if (type === 'grid' && has_step_value(name, v => Array.isArray(v) && Array.isArray(v[0]))) return 'grid';
        if (type === 'tree' && has_step_value(name, v => this._is_tree_snapshot(v))) return 'tree';
        if (type === 'list' && has_step_value(name, Array.isArray)) return 'list';
        if (type === 'array' && has_step_value(name, v => Array.isArray(v) && !Array.isArray(v[0]))) return 'array';
      }
    }

    for (const v of Object.values(this.algo.initial_data || {})) {
      if (Array.isArray(v) && Array.isArray(v[0])) return 'grid';
      if (Array.isArray(v)) return 'array';
    }
    const hasScalarValue = (this.algo.steps || []).some(s =>
      Object.entries(s.vars || {}).some(([name, value]) => {
        if (Array.isArray(value)) return false;
        const info = varClasses[name] || {};
        return info.category !== 'hidden';
      })
    );
    if (hasScalarValue) return 'scalar';
    return null;
  }

  _is_tree_snapshot(value) {
    if (value === null) return true;
    if (!Array.isArray(value) || value.length !== 3) return false;
    return !Array.isArray(value[0]) && this._is_tree_snapshot(value[1]) && this._is_tree_snapshot(value[2]);
  }

  _viz_empty_reason() {
    const vars = Object.values(this.algo.var_classes || {});
    if (vars.length === 0) return '当前轨迹没有变量分类数据';
    return '当前轨迹没有可显示的变量快照';
  }

  _init_code_panel() {
    this.codeBody.innerHTML = '';
    this.algo.source.forEach((line, i) => {
      const div = document.createElement('div');
      div.className = 'code-line';
      div.dataset.line = i;
      div.innerHTML = `<button type="button" class="line-num" data-line="${i}" aria-label="在第 ${i + 1} 行切换断点">${i+1}</button><div class="line-content">${this._hl(line)}</div>`;
      div.querySelector('.line-num').addEventListener('click', e => {
        e.stopPropagation();
        this._toggle_bp(i);
      });
      this.codeBody.appendChild(div);
    });
    // 切换算法后恢复已设置的断点红点
    for (const l of this.breakpoints) {
      const el = this.codeBody.querySelector(`.line-num[data-line="${l}"]`);
      if (el && !el.querySelector('.breakpoint')) {
        const d = document.createElement('div');
        d.className = 'breakpoint';
        el.appendChild(d);
      }
    }
  }

  _hl(s) {
    s = s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    const re = /(\/\/.*$|\/\*[\s\S]*?\*\/)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|\b(int|float|char|void|return|if|else|while|for|do|struct|typedef|const|static|sizeof|double|long|unsigned|short|switch|case|default|break|continue|goto|enum|union|extern|register|volatile|signed|auto|inline|restrict|NULL|EOF|stdin|stdout|stderr|size_t|FILE)\b|\b(printf|scanf|sprintf|fprintf|malloc|calloc|realloc|free|main|make_node|strlen|strcmp|strcpy|strcat|memset|memcpy|memmove|abs|rand|srand|clock|time|qsort|pow|sqrt|floor|ceil|fopen|fclose|fgets|fputs|fread|fwrite|exit|atoi|atof|strtol|strtod)\b|\b(\d+\.?\d*(?:e[+-]?\d+)?f?)\b|\b([a-zA-Z_]\w*)\b/gi;
    return s.replace(re, (m, comment, strlit, kw, fn, num, ident) => {
      if (comment) return `<span class="cmt">${m}</span>`;
      if (strlit)  return `<span class="str">${m}</span>`;
      if (kw)      return `<span class="kw">${m}</span>`;
      if (fn)      return `<span class="fn">${m}</span>`;
      if (num)     return `<span class="num">${m}</span>`;
      return m;
    });
  }

  _toggle_bp(line) {
    this.breakpoints.has(line) ? this.breakpoints.delete(line) : this.breakpoints.add(line);
    document.querySelectorAll('.line-num').forEach(el => {
      const l = parseInt(el.dataset.line);
      const dot = el.querySelector('.breakpoint');
      if (this.breakpoints.has(l)) { if (!dot) { const d=document.createElement('div'); d.className='breakpoint'; el.appendChild(d); } }
      else { if (dot) dot.remove(); }
    });
  }

  _highlight_line(line) {
    document.querySelectorAll('.code-line').forEach(el => el.classList.remove('active'));
    const t = document.querySelector(`.code-line[data-line="${line}"]`);
    if (t) {
      t.classList.add('active');
      const c = this.codeBody;
      const top = t.offsetTop - c.offsetTop;
      if (top < c.scrollTop || top > c.scrollTop + c.clientHeight - 30) c.scrollTop = top - c.clientHeight / 3;
    }
  }

  // 标记所有 trace 从未触及的源码行（变量声明、初始化等）
  _mark_all_setup_lines() {
    const touched = new Set();
    for (const s of this.algo.steps) {
      if (s.line) touched.add(s.line - 1);  // 转为 0-indexed
    }
    // 收集连续的未触及行为"设置段"
    for (let i = 0; i < this.algo.source.length; i++) {
      if (!touched.has(i)) {
        const el = document.querySelector(`.code-line[data-line="${i}"]`);
        if (el) el.classList.add('setup');
      }
    }
  }

  // 标记跳过的"设置"行（用于步骤间大跳跃提示）
  _mark_setup_lines(prevLine0, currLine0) {
    for (let l = prevLine0 + 1; l < currLine0; l++) {
      const el = document.querySelector(`.code-line[data-line="${l}"]`);
      if (el) el.classList.add('setup');
    }
  }

  _mark_executed() {
    document.querySelectorAll('.code-line').forEach(el => {
      if (this.executedLines.has(parseInt(el.dataset.line))) el.classList.add('executed');
    });
  }

  _render_vars(changedKeys) {
    const classes = this.algo.var_classes || {};
    this.varGrid.innerHTML = '';
    const primary = [], secondary = [];

    Object.entries(this.state).forEach(([k, v]) => {
      const info = classes[k] || {};
      const category = info.category || 'secondary';
      const isArray = info.type === 'array';

      if (isArray && Array.isArray(v)) {
        // 大数组（>30元素）折叠显示摘要
        const isLarge = v.length > 30;
        if (isLarge) {
          const displayVal = `[${v.length}项] ${v.slice(0, 5).join(',')}...${v.slice(-3).join(',')}`;
          const item = { name: k, val: displayVal, changed: changedKeys.includes(k), isArray: true, isLarge: true };
          if (category === 'primary') primary.push(item); else secondary.push(item);
        } else {
          // 小数组展开显示每个元素
          const items = [];
          v.forEach((val, idx) => {
            const displayVal = this._format_value(`${k}[${idx}]`, val, info);
            const changed = changedKeys.includes(k);
            const hl = this.state.mid===idx||this.state.left===idx||this.state.right===idx
              ||this.state.low===idx||this.state.high===idx||this.state.curr===idx
              ||this.state.i===idx||this.state.j===idx;
            items.push({ key: `${k}[${idx}]`, val: displayVal, changed, highlight: hl });
          });
          if (category === 'primary') {
            primary.push({ name: k, items, isArray: true });
          } else {
            secondary.push({ name: k, items, isArray: true });
          }
        }
      } else {
        const changed = changedKeys.includes(k);
        const displayVal = this._format_value(k, v, info);
        if (displayVal === undefined) return;
        const item = { name: k, val: displayVal, changed, isArray: false };
        if (category === 'primary') {
          primary.push(item);
        } else {
          secondary.push(item);
        }
      }
    });

    if (primary.length) {
      const sec = document.createElement('div'); sec.className = 'var-section';
      sec.innerHTML = '<div class="var-section-title">📌 主要变量</div>';
      const row = document.createElement('div'); row.className = 'var-row';
      primary.forEach(p => {
        if (p.items) {
          p.items.forEach(item => {
            const d = document.createElement('div');
            d.className = 'var-item' + (item.changed ? ' var-changed' : '') + (item.highlight ? ' var-highlight' : '');
            d.innerHTML = `<span class="var-name">${item.key}</span> = <span class="var-val">${item.val}</span>`;
            row.appendChild(d);
          });
        } else {
          const d = document.createElement('div');
          d.className = 'var-item' + (p.changed ? ' var-changed' : '');
          d.innerHTML = `<span class="var-name">${p.name}</span> = <span class="var-val">${p.val}</span>`;
          row.appendChild(d);
        }
      });
      sec.appendChild(row); this.varGrid.appendChild(sec);
    }

    if (secondary.length) {
      const count = secondary.reduce((s, x) => s + (x.items ? x.items.length : 1), 0);
      const tog = document.createElement('div'); tog.className = 'var-toggle';
      tog.textContent = `▸ 其他变量 (${count})`;
      tog.style.cursor = 'pointer';
      const row = document.createElement('div'); row.className = 'var-row'; row.style.display = 'none';
      secondary.forEach(s => {
        if (s.items) {
          s.items.forEach(item => {
            const d = document.createElement('div');
            d.className = 'var-item' + (item.changed ? ' var-changed' : '') + (item.highlight ? ' var-highlight' : '');
            d.innerHTML = `<span class="var-name">${item.key}</span> = <span class="var-val">${item.val}</span>`;
            row.appendChild(d);
          });
        } else {
          const d = document.createElement('div');
          d.className = 'var-item' + (s.changed ? ' var-changed' : '');
          d.innerHTML = `<span class="var-name">${s.name}</span> = <span class="var-val">${s.val}</span>`;
          row.appendChild(d);
        }
      });
      tog.addEventListener('click', () => {
        const h = row.style.display === 'none'; row.style.display = h ? 'flex' : 'none';
        tog.textContent = (h ? '▾' : '▸') + ` 其他变量 (${count})`;
      });
      this.varGrid.appendChild(tog); this.varGrid.appendChild(row);
    }
  }

  _format_value(name, value, info) {
    if (value === null) return 'null';
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      if (info && info.type === 'concept') {
        return value.kind === 'convex_hull' ? '凸包动画' : value.kind === 'euclid' ? '辗转相除动画' : '概念动画';
      }
      if (info && info.type === 'string_match') {
        return '字符串匹配视图';
      }
      if (Array.isArray(value.edges) && value.nodes !== undefined) {
        return `${value.nodes}点/${value.edges.length}边`;
      }
      return '[对象]';
    }
    if (Array.isArray(value)) return `[${value.length}项]`;
    if (typeof value !== 'number') return value;
    if (value <= -100000) return `节点${-value - 100000}`;
    if (value === -1 && this._is_pointer_like_name(name)) return 'NULL';
    if (value === 2147483647 || value >= 999999) return 'INF';
    if (value === -2147483648) return '-INF';
    if (this._looks_like_raw_address(name, value, info)) return '地址';
    return value;
  }

  _is_pointer_like_name(name) {
    return /^(head|tail|cur|curr|current|prev|next|nextTemp|slow|fast|p|q|root|node)$/i.test(String(name));
  }

  _looks_like_raw_address(name, value, info) {
    const abs = Math.abs(value);
    if (abs < 1000000) return false;
    const lower = String(name).toLowerCase();
    const pointerNames = [
      'ptr', 'node', 'root', 'head', 'tail', 'curr', 'current', 'prev', 'next',
      'queue', 'stack', 'graph', 'parent', 'result', 'res', 'return', 'word',
      'pattern', 'uf', 'pq'
    ];
    if (pointerNames.some(p => lower.includes(p))) return true;
    if (lower === 'n' && info && info.type === 'scalar') return true;
    return false;
  }

  // 深拷贝状态（数组也拷贝），避免引用共享
  _snapshot_state() {
    const snap = {};
    for (const [k, v] of Object.entries(this.state)) {
      snap[k] = Array.isArray(v) ? [...v] : v;
    }
    return snap;
  }

  _render_viz(step, prevStep, prevState) {
    if (!this.renderer) return;
    // 用调用栈推断当前函数（普通 step 没有 func 字段）
    const func = step.func || (this.callStack.length > 0 ? this.callStack[this.callStack.length - 1] : null);
    const stepData = {
      step: this.currentStep,
      line: step.line,
      type: step.type,
      func: func,
      vars: { ...this.state },
      var_classes: this.algo.var_classes || {},
    };
    let prevStepData = null;
    if (prevStep && prevState) {
      prevStepData = {
        step: this.currentStep - 1,
        line: prevStep.line,
        type: prevStep.type,
        func: func,
        vars: prevState,
        var_classes: this.algo.var_classes || {},
      };
    }
    this.renderer.render(stepData, prevStepData);
  }

  _render_output(stepIdx) {
    const outputEl = document.getElementById('output-content');
    if (!outputEl) return;
    const outputs = this.algo.program_output || [];
    // 累积显示到当前步骤为止的输出
    const visible = outputs.filter(o => o.after_step <= stepIdx + 1);
    if (visible.length === 0) {
      outputEl.innerHTML = '<div class="output-line" style="color:#525860;">（暂无输出）</div>';
      return;
    }
    outputEl.innerHTML = visible.map(o => `<div class="output-line">${this._escape_html(o.text)}</div>`).join('');
    // 滚动到底部
    const panel = document.getElementById('output-panel');
    if (panel) panel.scrollTop = panel.scrollHeight;
  }

  _escape_html(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  _render_call_stack() {
    let h = '<div class="callstack-title">📚 调用栈</div>';
    this.callStack.forEach(f => h += `<div class="callstack-item">${f}</div>`);
    this.callstackEl.innerHTML = h;
  }

  go_to_step(idx) {
    if (!this.algo||idx<0||idx>=this.algo.steps.length) return;
    this.currentStep = idx;
    const step = this.algo.steps[idx];
    if (step.type === 'skip') {
      this._show_skip_toast(`⏭ 跳过 ${step.skipped} 步（循环重复）`);
      if (idx + 1 < this.algo.steps.length) this.go_to_step(idx + 1);
      return;
    }
    const prevStep = idx > 0 ? this.algo.steps[idx - 1] : null;
    // 保存应用步骤前的状态快照，供 renderer 做前后比较
    const prevState = this._snapshot_state();
    const changed = [];
    Object.entries(step.vars).forEach(([k,v]) => {
      if (JSON.stringify(this.state[k])!==JSON.stringify(v)) changed.push(k);
      // 数组类型做合并处理
      const info = (this.algo.var_classes || {})[k] || {};
      if (info.type === 'array' && Array.isArray(v)) {
        this.state[k] = this._merge_array(k, v);
      } else {
        this.state[k] = v;
      }
    });
    if (step.type==='enter') this.callStack.push(step.func);
    else if (step.type==='exit') this.callStack.pop();
    const line0 = (step.line || 0) - 1;
    if (line0 >= 0) this.executedLines.add(line0);
    // 行号跳跃较大时提示省略了声明/初始化步骤
    if (prevStep && step.line && prevStep.line && step.line - prevStep.line > 3) {
      this._mark_setup_lines(prevStep.line - 1, line0);
      const skipped = step.line - prevStep.line - 1;
      this._show_skip_toast(`📋 中间 ${skipped} 行为变量声明和初始化，已省略`);
    }
    this._highlight_line(line0); this._mark_executed(); this._render_vars(changed);
    this._render_viz(step, prevStep, prevState);
    this._render_call_stack();
    this._render_output(idx);
    document.getElementById('step-cur').textContent = this.currentStep+1;
    this._sync_controls();
  }

  step_forward() {
    if (this.currentStep >= this.algo.steps.length-1) { this.stop_play(); return; }
    const skipTo = this._detect_loop_skip();
    if (skipTo > 0) {
      const skipped = skipTo - this.currentStep;
      this.go_to_step(skipTo);
      this._show_skip_toast(`⏭ 跳过 ${skipped} 步（循环重复）`);
      return;
    }
    this.go_to_step(this.currentStep+1);
    if (this.currentStep >= this.algo.steps.length-1) this.stop_play();
  }

  step_backward() {
    if (this.currentStep<=0) return;
    const target=this.currentStep-1;
    this.reset_state();
    this.fullArrayState = {};
    for (const [k, v] of Object.entries(this.algo.initial_data || {})) {
      if (Array.isArray(v)) this.fullArrayState[k] = [...v];
    }
    let prevState = null;
    for (let i=0;i<=target;i++) {
      const s=this.algo.steps[i];
      // 在应用目标步骤前保存快照
      if (i === target) prevState = this._snapshot_state();
      Object.entries(s.vars).forEach(([k,v]) => {
        const info = (this.algo.var_classes || {})[k] || {};
        if (info.type === 'array' && Array.isArray(v)) {
          this.state[k] = this._merge_array(k, v);
        } else {
          this.state[k] = v;
        }
      });
      if(s.type==='enter')this.callStack.push(s.func); else if(s.type==='exit')this.callStack.pop();
      const l0=(s.line||0)-1; if(l0>=0) this.executedLines.add(l0);
    }
    this.currentStep=target; const s=this.algo.steps[this.currentStep];
    const prevStep = target > 0 ? this.algo.steps[target - 1] : null;
    const tl0=(s.line||0)-1;
    this._highlight_line(tl0); this._mark_executed(); this._render_vars(Object.keys(s.vars));
    this._render_viz(s, prevStep, prevState);
    this._render_call_stack();
    this._render_output(this.currentStep);
    document.getElementById('step-cur').textContent=this.currentStep+1;
    this._sync_controls();
  }

  reset_state() { this.currentStep=-1; this.state={}; this.callStack=[]; this.executedLines=new Set(); this.stop_play(); }

  reset() {
    this.reset_state();
    this.fullArrayState = {};
    for (const [k, v] of Object.entries(this.algo.initial_data || {})) {
      if (Array.isArray(v)) this.fullArrayState[k] = [...v];
    }
    if (this.renderer) {
      this.renderer.stop_animation();
      this.renderer.set_initial_data(this.algo.initial_data || {});
    }
    this._highlight_line(-1); this.varGrid.innerHTML='';
    this.ctx.clearRect(0,0,this.canvas.width,this.canvas.height);
    this.callstackEl.innerHTML='<div class="callstack-title">📚 调用栈</div>';
    const outputEl = document.getElementById('output-content');
    if (outputEl) outputEl.innerHTML = '';
    document.getElementById('step-cur').textContent='0';
    document.querySelectorAll('.code-line').forEach(el=>el.classList.remove('active','executed'));
    if (typeof NoVisualizationRenderer !== 'undefined' &&
        this.renderer instanceof NoVisualizationRenderer) {
      this.renderer.render({}, null);
    } else if (this.algo && this.algo.steps && this.algo.steps.length > 0) {
      this.go_to_step(0);
    }
    this._sync_controls();
  }

  get_speed() { return Math.max(30, 1500 - document.getElementById('speed-slider').value * 147); }

  _detect_loop_skip() {
    const cfg = this.loopSkipConfig;
    const steps = this.algo.steps;
    const cur = this.currentStep;
    if (cur < cfg.minStepsToSkip) return -1;
    const remaining = steps.length - 1 - cur;
    if (remaining < cfg.minStepsToSkip) return -1;
    const win = cfg.windowSize;
    const recent = [];
    for (let i = cur - win + 1; i <= cur; i++) {
      if (i < 0) return -1;
      recent.push(steps[i].line || 0);
    }
    let repeatCount = 0;
    for (let i = cur - win; i >= 0; i--) {
      let match = true;
      for (let j = 0; j < win; j++) {
        if ((steps[i + j].line || 0) !== recent[j]) { match = false; break; }
      }
      if (match) repeatCount++;
      else break;
    }
    let futureRepeat = 0;
    for (let i = cur + 1; i + win - 1 < steps.length; i++) {
      let match = true;
      for (let j = 0; j < win; j++) {
        if ((steps[i + j].line || 0) !== recent[j]) { match = false; break; }
      }
      if (match) futureRepeat++;
      else break;
    }
    if (repeatCount >= cfg.minRepeat && futureRepeat >= cfg.minRepeat) {
      const jumpSteps = win * cfg.skipAhead;
      const target = Math.min(cur + jumpSteps, steps.length - 5);
      if (target > cur + win) return target;
    }
    return -1;
  }

  _show_skip_toast(msg) {
    let toast = document.getElementById('skip-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'skip-toast';
      toast.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#238636;color:#fff;padding:10px 24px;border-radius:8px;font-size:15px;z-index:9999;opacity:0;transition:opacity .3s;pointer-events:none;';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.opacity = '1';
    clearTimeout(this._skipToastTimer);
    this._skipToastTimer = setTimeout(() => toast.style.opacity = '0', 2500);
  }
  start_play() {
    const btn = document.getElementById('btn-play');
    // 已在末尾 → 重放 = 重置 + 播放
    if (this.currentStep >= this.algo.steps.length - 1) {
      this.reset();
    }
    this.playing = true;
    btn.textContent = '⏸ 暂停';
    btn.classList.add('btn-active');
    this._play_loop();
  }
  stop_play() {
    this.playing = false;
    const btn = document.getElementById('btn-play');
    const atEnd = this.algo && this.currentStep >= this.algo.steps.length - 1;
    btn.textContent = atEnd ? '🔄 重放' : '▶ 播放';
    btn.classList.remove('btn-active');
    if (this.playTimer) { clearTimeout(this.playTimer); this.playTimer = null; }
    this._sync_controls(false);
  }
  _play_loop() {
    if (!this.playing) return;
    this.step_forward();
    // 当前行有断点时自动暂停
    const cur = this.algo.steps[this.currentStep];
    if (cur && this.breakpoints.has((cur.line || 0) - 1)) {
      this.stop_play();
      return;
    }
    if (this.currentStep < this.algo.steps.length - 1)
      this.playTimer = setTimeout(() => this._play_loop(), this.get_speed());
    else
      this.stop_play();
  }
  play_to_bp() {
    // 逐步行进到断点（绕过 loopSkip 避免跳过断点行）
    for (let i = this.currentStep + 1; i < this.algo.steps.length; i++) {
      if (this.breakpoints.has((this.algo.steps[i].line || 0) - 1)) {
        while (this.currentStep < i) this.go_to_step(this.currentStep + 1);
        return;
      }
    }
  }

  _apply_font_size() {
    document.documentElement.style.setProperty('--code-font-size', this.codeFontSize+'px');
    document.documentElement.style.setProperty('--var-font-size', (this.codeFontSize-1)+'px');
    document.documentElement.style.setProperty('--output-font-size', (this.codeFontSize-2)+'px');
  }
  font_inc() { this.codeFontSize=Math.min(28,this.codeFontSize+1); this._apply_font_size(); localStorage.setItem('dh_font_size',this.codeFontSize); }
  font_dec() { this.codeFontSize=Math.max(11,this.codeFontSize-1); this._apply_font_size(); localStorage.setItem('dh_font_size',this.codeFontSize); }

  _sync_controls(emit = true) {
    const total = this.algo && Array.isArray(this.algo.steps) ? this.algo.steps.length : 0;
    const atStart = this.currentStep <= 0;
    const atEnd = total > 0 && this.currentStep >= total - 1;
    const back = document.getElementById('btn-back');
    const step = document.getElementById('btn-step');
    const reset = document.getElementById('btn-reset');
    if (back) back.disabled = atStart;
    if (step) step.disabled = total === 0 || atEnd;
    if (reset) reset.disabled = total === 0 || this.currentStep < 0;
    if (!emit) return;
    document.dispatchEvent(new CustomEvent('dh:stepchange', {
      detail: {
        currentStep: this.currentStep,
        total,
        atStart,
        atEnd,
        playing: this.playing,
      },
    }));
  }
}
