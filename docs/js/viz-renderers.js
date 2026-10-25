/**
 * 可视化渲染器系统
 * 根据算法执行轨迹数据，在 Canvas 上绘制直观的动画
 */

const VIZ_COLORS = {
  bg: '#1e2336',
  barDefault: '#3b82f6',
  barCompare: '#f59e0b',
  barSwap: '#ef4444',
  barSorted: '#10b981',
  barActive: '#8b5cf6',
  text: '#d7dae0',
  textDim: '#7f848e',
  pointer: '#f59e0b',
  pointerText: '#fbbf24',
};

function ease_in_out_cubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

class BaseRenderer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.dpr = window.devicePixelRatio || 1;
    this.width = 0;
    this.height = 0;
    this.animating = false;
    this.animationQueue = [];
    this.currentFrame = null;
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    this.width = rect.width;
    this.height = rect.height;
    this.canvas.width = this.width * this.dpr;
    this.canvas.height = this.height * this.dpr;
    this.ctx.scale(this.dpr, this.dpr);
  }

  clear() {
    this.ctx.clearRect(0, 0, this.width, this.height);
  }

  render(stepData, prevStepData) {
    throw new Error('子类必须实现 render 方法');
  }

  animate(duration, drawFn, onComplete) {
    const startTime = performance.now();
    const frame = (now) => {
      const elapsed = now - startTime;
      const t = Math.min(elapsed / duration, 1);
      const eased = ease_in_out_cubic(t);
      drawFn(eased, t);
      if (t < 1) {
        this.currentFrame = requestAnimationFrame(frame);
      } else {
        this.animating = false;
        if (onComplete) onComplete();
        this._run_next_animation();
      }
    };
    this.animating = true;
    this.currentFrame = requestAnimationFrame(frame);
  }

  _run_next_animation() {
    if (this.animationQueue.length > 0) {
      const next = this.animationQueue.shift();
      next();
    }
  }

  queue_animation(fn) {
    if (this.animating) {
      this.animationQueue.push(fn);
    } else {
      fn();
    }
  }

  stop_animation() {
    if (this.currentFrame) {
      cancelAnimationFrame(this.currentFrame);
      this.currentFrame = null;
    }
    this.animating = false;
    this.animationQueue = [];
  }

  set_initial_data(initialData) {}

  reset() {
    this.stop_animation();
    this.clear();
  }

  _round_rect(ctx, x, y, w, h, r) {
    const radius = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + w - radius, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + radius);
    ctx.lineTo(x + w, y + h - radius);
    ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
    ctx.lineTo(x + radius, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
  }
}

// ============================================================
// 无可视化数据空态
// ============================================================

class NoVisualizationRenderer extends BaseRenderer {
  constructor(canvasId, reason = '') {
    super(canvasId);
    this.reason = reason;
  }

  set_initial_data(initialData) {}

  render(stepData, prevStepData) {
    this.clear();
    const { ctx, width, height } = this;
    const cx = width / 2;
    const cy = height / 2;

    ctx.save();
    ctx.fillStyle = 'rgba(30,35,54,0.9)';
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = 'rgba(73,164,238,0.22)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy - 22, 34, 0, Math.PI * 2);
    ctx.stroke();

    ctx.fillStyle = VIZ_COLORS.text;
    ctx.font = 'bold 16px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('暂无结构图', cx, cy - 24);

    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
    ctx.fillText(this.reason || '这个算法目前只显示代码步进和变量变化', cx, cy + 24);
    ctx.restore();
  }
}

// ============================================================
// 数组柱状图渲染器
// ============================================================

class ArrayBarRenderer extends BaseRenderer {
  constructor(canvasId, options = {}) {
    super(canvasId);
    this.options = {
      barGapRatio: 0.18,
      bottomPadding: 50,
      topPadding: 40,
      leftPadding: 60,
      rightPadding: 60,
      maxBarHeightRatio: 0.75,
      ...options,
    };
    this.lastRenderState = null;
    this.fullArrayState = {};  // 维护完整数组状态
    this._lockedMaxVal = null;   // 锁定最大高度，避免界面跳动
    this._lastArrKey = null;
    this._lastTarget = undefined;
    this._wasAllSorted = false;  // 记录是否曾经全部排好序
  }

  stop_animation() {
    if (this.currentFrame) {
      cancelAnimationFrame(this.currentFrame);
      this.currentFrame = null;
      // 动画被中断，立即绘制最后静态状态，避免残留交换红色
      if (this.lastRenderState) this._render_static(this.lastRenderState);
    }
    this.animating = false;
    this.animationQueue = [];
  }

  set_initial_data(initialData) {
    this.fullArrayState = {};
    this._lockedMaxVal = null;
    this._lastArrKey = null;
    this._lastTarget = undefined;
    this._wasAllSorted = false;
    for (const [k, v] of Object.entries(initialData)) {
      if (Array.isArray(v)) {
        this.fullArrayState[k] = [...v];
      }
    }
  }

  // 合并部分数组到完整数组状态
  _merge_array(key, partialArr) {
    if (!this.fullArrayState || !this.fullArrayState[key]) {
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

  _infer_action(stepData, prevStepData) {
    if (!prevStepData) return { type: 'init' };

    const vars = stepData.vars || {};
    const prevVars = prevStepData.vars || {};

    for (const key of Object.keys(vars)) {
      if (!Array.isArray(vars[key])) continue;
      const curr = this._merge_array(key, vars[key]);
      const prev = this._merge_array(key, prevVars[key] || vars[key]);
      if (JSON.stringify(curr) !== JSON.stringify(prev)) {
        const diff = [];
        for (let i = 0; i < curr.length; i++) {
          if (curr[i] !== prev[i]) diff.push(i);
        }
        if (diff.length === 2) {
          const [i, j] = diff;
          if (prev[i] === curr[j] && prev[j] === curr[i]) {
            this._pendingSwap = null;
            return { type: 'swap', indices: [i, j], arrKey: key };
          }
        }
        // 两步交换检测：冒泡排序的 arr[j]=arr[j+1] 和 arr[j+1]=temp 分两步记录
        if (diff.length === 1 && this._pendingSwap && this._pendingSwap.arrKey === key) {
          const firstIdx = this._pendingSwap.indices[0];
          const secondIdx = diff[0];
          if (firstIdx !== secondIdx &&
              this._pendingSwap.prevArr[firstIdx] === curr[secondIdx] &&
              this._pendingSwap.prevArr[secondIdx] === curr[firstIdx]) {
            const result = { type: 'swap', indices: [firstIdx, secondIdx], arrKey: key };
            this._pendingSwap = null;
            return result;
          }
        }
        // 普通赋值
        if (diff.length === 1) {
          this._pendingSwap = { indices: diff, arrKey: key, prevArr: prev };
        } else {
          this._pendingSwap = null;
        }
        return { type: 'assign', indices: diff, arrKey: key };
      }
    }

    // 非数组变更步骤，清除等待中的交换
    this._pendingSwap = null;

    if (stepData.type === 'cond') {
      const idxVars = ['i', 'j', 'mid', 'left', 'right', 'minIdx', 'maxIdx'];
      const activeIndices = [];
      for (const v of idxVars) {
        if (vars[v] !== undefined) activeIndices.push({ name: v, value: vars[v] });
      }
      if (activeIndices.length > 0) {
        return { type: 'compare', indices: activeIndices };
      }
    }

    return { type: 'step' };
  }

  _compute_layout(arr) {
    const n = arr.length;
    const availWidth = this.width - this.options.leftPadding - this.options.rightPadding;
    const barWidth = availWidth / (n + (n - 1) * this.options.barGapRatio);
    const gap = barWidth * this.options.barGapRatio;
    const totalWidth = n * barWidth + (n - 1) * gap;
    const startX = this.options.leftPadding + (this.width - this.options.leftPadding - this.options.rightPadding - totalWidth) / 2;
    const currentMax = Math.max(...arr, 1);
    // 锁定最大高度避免跳动；当数组换成全新数据集时自动重置
    if (this._lockedMaxVal === null || currentMax > this._lockedMaxVal) {
      this._lockedMaxVal = currentMax;
    } else if (currentMax < this._lockedMaxVal * 0.35) {
      this._lockedMaxVal = currentMax;
    }
    const maxVal = this._lockedMaxVal;
    const availHeight = this.height - this.options.topPadding - this.options.bottomPadding;
    const maxBarHeight = availHeight * this.options.maxBarHeightRatio;
    const scale = maxBarHeight / maxVal;
    const baseY = this.options.topPadding + (availHeight + maxBarHeight) / 2;
    return { barWidth, gap, startX, scale, maxVal, maxBarHeight, baseY };
  }

  _draw_bar(ctx, x, y, w, h, value, color, alpha = 1, label = null) {
    ctx.save();
    ctx.globalAlpha = alpha;
    const r = Math.min(w * 0.15, 6);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
    ctx.fill();

    const grad = ctx.createLinearGradient(x, y, x, y + h * 0.4);
    grad.addColorStop(0, 'rgba(255,255,255,0.15)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = grad;
    ctx.fill();

    if (w > 20) {
      ctx.fillStyle = 'rgba(255,255,255,0.9)';
      ctx.font = `bold ${Math.min(w * 0.45, 20)}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(value.toString(), x + w / 2, y + h / 2);
    }

    if (label !== null) {
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = `14px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText(label.toString(), x + w / 2, y + h + 8);
    }
    ctx.restore();
  }

  _draw_pointer(ctx, x, w, y, label, color) {
    ctx.save();
    ctx.strokeStyle = 'rgba(0,0,0,0.6)';
    ctx.lineWidth = 2;
    ctx.fillStyle = color;
    ctx.font = `bold 16px "JetBrains Mono", monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    const px = x + w / 2;
    const py = y - 6;
    ctx.beginPath();
    ctx.moveTo(px, py);
    ctx.lineTo(px - 9, py - 14);
    ctx.lineTo(px + 9, py - 14);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.fillText(label, px, py - 18);
    ctx.restore();
  }

  render(stepData, prevStepData) {
    this.stop_animation();
    const vars = stepData.vars || {};
    const arrKey = this._find_array_key(vars, stepData);
    if (!arrKey) {
      this.clear();
      return;
    }

    // 数组变量名变了（如 arr1 → arr），重置高度锁定
    if (arrKey !== this._lastArrKey) {
      this._lockedMaxVal = null;
      this._lastArrKey = arrKey;
    }
    const mergedArr = this._merge_array(arrKey, vars[arrKey]);
    const action = this._infer_action(stepData, prevStepData);
    const pointers = this._extract_pointers(vars);
    const sortedRange = this._infer_sorted_range(stepData, vars, mergedArr.length);
    const layout = this._compute_layout(mergedArr);
    const targetVal = vars.target !== undefined ? vars.target : null;
    // target 切换时清除旧 mid 标记
    if (targetVal !== null && targetVal !== this._lastTarget) {
      this._lastTarget = targetVal;
    }
    // mid 仅在比较步骤（cond）显示，非 cond 步骤从指针列表移除
    if (stepData.type !== 'cond') {
      for (let i = pointers.length - 1; i >= 0; i--) {
        if (pointers[i].name === 'mid') pointers.splice(i, 1);
      }
    }
    const state = { arr: mergedArr, pointers, sortedRange, action, layout, arrKey, target: targetVal };

    if (action.type === 'swap' && this.lastRenderState) {
      this._animate_swap(state, this.lastRenderState, action);
    } else if (action.type === 'compare') {
      this._render_compare(state, this.lastRenderState);
    } else {
      this._render_static(state);
    }
    this.lastRenderState = state;
  }

  _find_array_key(vars, stepData) {
    if (stepData.var_classes) {
      for (const [k, v] of Object.entries(stepData.var_classes)) {
        if (v.type === 'array' && vars[k]) return k;
      }
    }
    for (const [k, v] of Object.entries(vars)) {
      if (Array.isArray(v)) return k;
    }
    return null;
  }

  _extract_pointers(vars) {
    const ptrs = [];
    const ptrNames = ['i', 'j', 'mid', 'left', 'right', 'lo', 'hi', 'minIdx', 'maxIdx', 'pivot'];
    for (const name of ptrNames) {
      if (vars[name] !== undefined) {
        ptrs.push({ name, value: vars[name] });
      }
    }
    return ptrs;
  }

  _infer_sorted_range(stepData, vars, n) {
    const func = stepData.func || '';
    if (func.toLowerCase().includes('bubble')) {
      if (vars.i !== undefined && vars.i > 0) {
        return { start: n - vars.i, end: n };
      }
    }
    if (func.toLowerCase().includes('selection')) {
      if (vars.i !== undefined && vars.i > 0) {
        return { start: 0, end: vars.i };
      }
    }
    return null;
  }

  _render_static(state, progress = 1) {
    const { ctx, width, height } = this;
    const { arr, pointers, sortedRange, layout } = state;
    const { barWidth, gap, startX, scale, maxBarHeight, baseY } = layout;
    this.clear();

    // 排序完成后强制全绿（仅限排序算法——数组原本无序，排完才全绿）
    // 查找算法的数组一开始就有序，不应触发此逻辑
    const isSorting = sortedRange !== null || state.action === 'swap' || state.action === 'assign';
    const arrSorted = arr.every((v, i) => i === 0 || v >= arr[i - 1]);
    const allSorted = (isSorting && arrSorted) || (this._wasAllSorted && arrSorted);
    if (allSorted) this._wasAllSorted = true;
    const effectivePointers = allSorted ? [] : pointers;

    // 搜索范围高亮（二分查找等：left/right 指针划定搜索区间）
    const leftPtr = effectivePointers.find(p => p.name === 'left');
    const rightPtr = effectivePointers.find(p => p.name === 'right');
    if (leftPtr && rightPtr && !allSorted) {
      const lx = startX + leftPtr.value * (barWidth + gap) - 4;
      const rx = startX + rightPtr.value * (barWidth + gap) + barWidth + 4;
      const hy = baseY - maxBarHeight - 5;
      const hh = maxBarHeight + 5;
      ctx.fillStyle = 'rgba(59,130,246,0.10)';
      ctx.fillRect(lx, hy, rx - lx, hh);
      ctx.strokeStyle = 'rgba(59,130,246,0.25)';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(lx, hy, rx - lx, hh);
    }

    // 查找目标值显示框（右上角）
    if (state.target !== null && state.target !== undefined && !allSorted) {
      const tx = width - this.options.rightPadding - 10;
      const ty = 8;
      const barFontSize = Math.min(layout.barWidth * 0.45, 20);
      const tw = Math.max(60, barFontSize * 3.5), th = barFontSize + 16;
      ctx.fillStyle = '#f6a723';
      ctx.strokeStyle = '#c7851a';
      ctx.lineWidth = 2;
      const rx = tx - tw, ry = ty, r = 6;
      ctx.beginPath();
      ctx.moveTo(rx + r, ry);
      ctx.lineTo(rx + tw - r, ry);
      ctx.arcTo(rx + tw, ry, rx + tw, ry + r, r);
      ctx.lineTo(rx + tw, ry + th - r);
      ctx.arcTo(rx + tw, ry + th, rx + tw - r, ry + th, r);
      ctx.lineTo(rx + r, ry + th);
      ctx.arcTo(rx, ry + th, rx, ry + th - r, r);
      ctx.lineTo(rx, ry + r);
      ctx.arcTo(rx, ry, rx + r, ry, r);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = `bold ${barFontSize}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${state.target}`, tx - tw / 2, ty + th / 2);
    }

    for (let idx = 0; idx < arr.length; idx++) {
      const val = arr[idx];
      const x = startX + idx * (barWidth + gap);
      const barHeight = val * scale;
      const y = baseY - barHeight;
      let color = allSorted ? VIZ_COLORS.barSorted : VIZ_COLORS.barDefault;
      if (!allSorted && sortedRange && idx >= sortedRange.start && idx < sortedRange.end) {
        color = VIZ_COLORS.barSorted;
      }
      const ptr = effectivePointers.find(p => p.value === idx);
      // 已排序部分优先保持绿色，不被指针颜色覆盖
      if (ptr && color !== VIZ_COLORS.barSorted) {
        // mid 指针用更醒目的对比色
        color = ptr.name === 'mid' ? VIZ_COLORS.barCompare : VIZ_COLORS.barActive;
      }
      this._draw_bar(ctx, x, y, barWidth, barHeight, val, color, progress, idx);
      if (ptr) {
        this._draw_pointer(ctx, x, barWidth, y, ptr.name, VIZ_COLORS.pointerText);
      }
    }
  }

  _render_compare(state, prevState) {
    const { action } = state;
    const compareIndices = action.indices || [];
    this._render_static(state);
    const { ctx, height } = this;
    const { arr, layout } = state;
    const { barWidth, gap, startX, scale, baseY } = layout;

    this.animate(400, (eased) => {
      this._render_static(state);
      const alpha = Math.sin(eased * Math.PI) * 0.3;
      for (const ptr of compareIndices) {
        const idx = ptr.value;
        if (idx < 0 || idx >= arr.length) continue;
        const val = arr[idx];
        const x = startX + idx * (barWidth + gap);
        const barHeight = val * scale;
        const y = baseY - barHeight;
        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.fillStyle = VIZ_COLORS.barCompare;
        ctx.fillRect(x - 2, y - 2, barWidth + 4, barHeight + 4);
        ctx.restore();
      }
    }, () => {
      this._render_static(state);
    });
  }

  _animate_swap(state, prevState, action) {
    const { arr, layout, pointers, sortedRange } = state;
    const { barWidth, gap, startX, scale, baseY } = layout;
    const [i, j] = action.indices;
    const { height } = this;
    const prevArr = prevState ? prevState.arr : arr;
    const valI = prevArr[i];
    const valJ = prevArr[j];

    this.animate(500, (eased) => {
      this.clear();
      for (let idx = 0; idx < arr.length; idx++) {
        let x = startX + idx * (barWidth + gap);
        let val = arr[idx];
        let color = VIZ_COLORS.barDefault;
        if (sortedRange && idx >= sortedRange.start && idx < sortedRange.end) {
          color = VIZ_COLORS.barSorted;
        }
        if (idx === i) {
          const targetX = startX + j * (barWidth + gap);
          x = lerp(x, targetX, eased);
          color = VIZ_COLORS.barSwap;
          val = valI;
        } else if (idx === j) {
          const targetX = startX + i * (barWidth + gap);
          x = lerp(x, targetX, eased);
          color = VIZ_COLORS.barSwap;
          val = valJ;
        }
        const ptr = pointers.find(p => p.value === idx);
        if (ptr && idx !== i && idx !== j) {
          color = VIZ_COLORS.barActive;
        }
        const barHeight = val * scale;
        const y = baseY - barHeight;
        this._draw_bar(this.ctx, x, y, barWidth, barHeight, val, color, 1, idx);
        if (ptr) {
          this._draw_pointer(this.ctx, x, barWidth, y, ptr.name, VIZ_COLORS.pointerText);
        }
      }
    }, () => {
      this._render_static(state);
    });
  }
}

// ============================================================
// 链表渲染器 — 圆形节点 + 箭头
// ============================================================

class LinkedListRenderer extends BaseRenderer {
  constructor(canvasId, options = {}) {
    super(canvasId);
    this.options = {
      nodeRadius: 28,
      arrowSize: 10,
      topPadding: 70,
      bottomPadding: 30,
      ...options,
    };
    this.lastRenderState = null;
    // 节点值 -> 固定位置索引（按首次出现顺序）
    this._valueToIndex = new Map();
    // 上一步的 next 关系：值 -> 下一个值
    this._prevNextMap = new Map();
    // 节点透明度（用于新节点淡入）
    this._nodeAlphas = new Map();
    // 箭头动画状态："fromVal->toVal" -> { progress, target }
    this._arrowAnims = new Map();
    // 动画速度控制
    this._lastRenderTime = 0;
  }

  set_initial_data(initialData) {
    this.fullArrayState = {};
    this._lockedMaxVal = null;
    this._lastArrKey = null;
    this._lastTarget = undefined;
    this._wasAllSorted = false;
    for (const [k, v] of Object.entries(initialData)) {
      if (Array.isArray(v)) {
        this.fullArrayState[k] = [...v];
      }
    }
  }

  reset() {
    this._valueToIndex.clear();
    this._prevNextMap.clear();
    this._nodeAlphas.clear();
    this._arrowAnims.clear();
    this.lastRenderState = null;
    this.clear();
  }

  _find_list_key(vars, stepData) {
    if (stepData.var_classes) {
      for (const [k, v] of Object.entries(stepData.var_classes)) {
        if (v.type === 'list' && Array.isArray(vars[k])) return k;
      }
    }
    for (const [k, v] of Object.entries(vars)) {
      if (Array.isArray(v) && k !== 'arr' && v.length > 1) return k;
    }
    return null;
  }

  // 从链表数组推断 next 关系：{值: 下一个值, ...}
  _infer_next_map(list) {
    const map = new Map();
    for (let i = 0; i < list.length - 1; i++) {
      map.set(list[i], list[i + 1]);
    }
    if (list.length > 0) map.set(list[list.length - 1], null);
    return map;
  }

  // 更新值到固定位置的映射（新值追加到末尾）
  _update_value_index_map(list) {
    for (const v of list) {
      if (!this._valueToIndex.has(v)) {
        this._valueToIndex.set(v, this._valueToIndex.size);
        this._nodeAlphas.set(v, 0); // 新节点初始透明
      }
    }
  }

  _compute_layout() {
    // +1 为 NULL 标记预留位置
    const count = Math.max(this._valueToIndex.size + 1, 5);
    const nodeSpacing = this.options.nodeRadius * 3.2;
    const totalWidth = count * nodeSpacing;
    const startX = (this.width - totalWidth) / 2 + this.options.nodeRadius;
    const centerY = this.height / 2;
    return { nodeSpacing, startX, centerY };
  }

  _get_node_x(value, layout) {
    const idx = this._valueToIndex.get(value);
    if (idx === undefined) return layout.startX;
    return layout.startX + idx * layout.nodeSpacing;
  }

  _compute_null_position(list, layout) {
    const tailVal = list.length ? list[list.length - 1] : null;
    const tailIdx = this._valueToIndex.get(tailVal);
    if (tailIdx === undefined) {
      return {
        x: layout.startX + this._valueToIndex.size * layout.nodeSpacing,
        y: layout.centerY,
      };
    }
    const tailX = layout.startX + tailIdx * layout.nodeSpacing;
    const lastIdx = Math.max(0, this._valueToIndex.size - 1);
    const dir = tailIdx >= lastIdx / 2 ? 1 : -1;
    return {
      x: tailX + dir * layout.nodeSpacing * 0.95,
      y: layout.centerY + this.options.nodeRadius * 2.25,
    };
  }

  _draw_node(ctx, x, y, r, value, color, alpha = 1, label = null) {
    ctx.save();
    ctx.globalAlpha = alpha;

    // 圆形背景
    ctx.fillStyle = color;
    ctx.strokeStyle = 'rgba(255,255,255,0.3)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // 高光
    const grad = ctx.createRadialGradient(x - r * 0.3, y - r * 0.3, 0, x, y, r);
    grad.addColorStop(0, 'rgba(255,255,255,0.2)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();

    // 值
    ctx.fillStyle = '#fff';
    ctx.font = `bold ${Math.min(r * 0.8, 18)}px "JetBrains Mono", monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(value.toString(), x, y);

    // 底部标签
    if (label !== null) {
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = `12px "JetBrains Mono", monospace`;
      ctx.textBaseline = 'top';
      ctx.fillText(label, x, y + r + 6);
    }
    ctx.restore();
  }

  _draw_arrow(ctx, fromX, fromY, to_x, to_y, r, progress = 1, color = null) {
    const dx = to_x - fromX;
    const dy = to_y - fromY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < r * 2) return;
    const ux = dx / dist;
    const uy = dy / dist;

    const sx = fromX + ux * r;
    const sy = fromY + uy * r;
    const ex = to_x - ux * r;
    const ey = to_y - uy * r;

    const curEx = sx + (ex - sx) * progress;
    const curEy = sy + (ey - sy) * progress;

    ctx.save();
    ctx.globalAlpha = progress;
    ctx.strokeStyle = color || 'rgba(255,255,255,0.35)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(sx, sy);
    ctx.lineTo(curEx, curEy);
    ctx.stroke();

    if (progress > 0.5) {
      const as = this.options.arrowSize;
      ctx.fillStyle = color || 'rgba(255,255,255,0.35)';
      ctx.beginPath();
      ctx.moveTo(to_x - ux * r, to_y - uy * r);
      ctx.lineTo(
        to_x - ux * r - ux * as + uy * as * 0.5,
        to_y - uy * r - uy * as - ux * as * 0.5
      );
      ctx.lineTo(
        to_x - ux * r - ux * as - uy * as * 0.5,
        to_y - uy * r - uy * as + ux * as * 0.5
      );
      ctx.closePath();
      ctx.fill();
    }
    ctx.restore();
  }

  // 绘制曲线箭头（用于跨节点或避让场景）
  _draw_curve_arrow(ctx, fromX, fromY, to_x, to_y, r, progress = 1, color = null) {
    const dx = to_x - fromX;
    const dy = to_y - fromY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < r * 2) return;

    // 控制点：中点上/下方隆起，尽量避开节点主体。
    const midX = (fromX + to_x) / 2;
    const midY = (fromY + to_y) / 2 + (to_y >= fromY ? dist * 0.22 : -dist * 0.22);

    // 从圆边缘出发的点
    const angle = Math.atan2(dy, dx);
    const sx = fromX + Math.cos(angle) * r;
    const sy = fromY + Math.sin(angle) * r;
    let ex = to_x - Math.cos(angle) * r;
    let ey = to_y - Math.sin(angle) * r;
    if (Math.abs(dy) > r * 0.8) {
      // NULL 通常放在尾节点下方。箭头固定落到 NULL 圆的 0°/180° 侧边更稳。
      const side = fromX < to_x ? -1 : 1;
      ex = to_x + side * r;
      ey = to_y;
    }

    // 二次贝塞尔曲线上的点
    const bezier = (t) => {
      const x = (1 - t) * (1 - t) * sx + 2 * (1 - t) * t * midX + t * t * ex;
      const y = (1 - t) * (1 - t) * sy + 2 * (1 - t) * t * midY + t * t * ey;
      return { x, y };
    };

    ctx.save();
    ctx.globalAlpha = Math.min(progress * 1.5, 1);
    ctx.strokeStyle = color || 'rgba(255,255,255,0.45)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    const steps = 30;
    const endStep = Math.floor(steps * progress);
    for (let i = 0; i <= endStep; i++) {
      const t = i / steps;
      const p = bezier(t);
      if (i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();

    if (progress > 0.7) {
      const as = this.options.arrowSize;
      const t = 0.98;
      const p = bezier(t);
      const prev = bezier(t - 0.02);
      const ang = Math.atan2(p.y - prev.y, p.x - prev.x);
      const tip = bezier(1);
      ctx.fillStyle = color || 'rgba(255,255,255,0.45)';
      ctx.beginPath();
      ctx.moveTo(tip.x, tip.y);
      ctx.lineTo(
        tip.x - Math.cos(ang) * as + Math.sin(ang) * as * 0.5,
        tip.y - Math.sin(ang) * as + -Math.cos(ang) * as * 0.5
      );
      ctx.lineTo(
        tip.x - Math.cos(ang) * as - Math.sin(ang) * as * 0.5,
        tip.y - Math.sin(ang) * as - -Math.cos(ang) * as * 0.5
      );
      ctx.closePath();
      ctx.fill();
    }
    ctx.restore();
  }

  _draw_null_marker(ctx, x, y, r) {
    // 蓝色空心圆，和其他节点一样大
    ctx.strokeStyle = 'rgba(59,130,246,0.6)';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.stroke();
    // 内部虚线环装饰
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = 'rgba(59,130,246,0.25)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(x, y, r * 0.65, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
    // 小字 NULL
    ctx.fillStyle = 'rgba(148,163,184,0.8)';
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('NULL', x, y + r + 14);
  }

  _draw_pointer_label(ctx, x, y, r, label, color) {
    ctx.save();
    ctx.fillStyle = color;
    ctx.font = `bold 14px "JetBrains Mono", monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    const py = y - r - 12;
    // 三角标记
    ctx.beginPath();
    ctx.moveTo(x, py + 6);
    ctx.lineTo(x - 6, py);
    ctx.lineTo(x + 6, py);
    ctx.closePath();
    ctx.fill();
    ctx.fillText(label, x, py - 4);
    ctx.restore();
  }

  _draw_pointer_label_group(ctx, x, y, r, labels, color) {
    if (!labels.length) return;
    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    const py = y - r - 12;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(x, py + 6);
    ctx.lineTo(x - 6, py);
    ctx.lineTo(x + 6, py);
    ctx.closePath();
    ctx.fill();

    const lineH = 16;
    const startY = py - 4 - (labels.length - 1) * lineH;
    labels.forEach((label, idx) => {
      const ty = startY + idx * lineH;
      const textW = Math.max(34, label.length * 8 + 12);
      ctx.fillStyle = 'rgba(21,25,32,0.88)';
      ctx.strokeStyle = 'rgba(251,191,36,0.45)';
      ctx.lineWidth = 1;
      const bx = x - textW / 2;
      const by = ty - 14;
      const bh = 16;
      const br = 5;
      ctx.beginPath();
      ctx.moveTo(bx + br, by);
      ctx.lineTo(bx + textW - br, by);
      ctx.arcTo(bx + textW, by, bx + textW, by + br, br);
      ctx.lineTo(bx + textW, by + bh - br);
      ctx.arcTo(bx + textW, by + bh, bx + textW - br, by + bh, br);
      ctx.lineTo(bx + br, by + bh);
      ctx.arcTo(bx, by + bh, bx, by + bh - br, br);
      ctx.lineTo(bx, by + br);
      ctx.arcTo(bx, by, bx + br, by, br);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = color;
      ctx.font = `bold 12px "JetBrains Mono", monospace`;
      ctx.fillText(label, x, ty);
    });
    ctx.restore();
  }

  render(stepData, prevStepData) {
    this.stop_animation();
    const vars = stepData.vars || {};
    let listKey = this._find_list_key(vars, stepData);
    let list = listKey ? vars[listKey] : null;

    // 当前步骤无链表数据时，回退到上一步的状态（如 reverse_list 内部只追踪标量）
    if ((!listKey || !Array.isArray(list) || list.length === 0) && this.lastRenderState) {
      listKey = this.lastRenderState.listKey;
      list = this.lastRenderState.list;
    }

    if (!listKey || !Array.isArray(list) || list.length === 0) {
      this.clear();
      return;
    }

    // 更新固定位置映射（新值追加）
    const prevSize = this._valueToIndex.size;
    this._update_value_index_map(list);
    const hasNewNodes = this._valueToIndex.size > prevSize;

    // 推断当前 next 关系
    const currentNextMap = this._infer_next_map(list);

    // 检测 next 变化
    const prevNextMap = this._prevNextMap;
    const addedArrows = [];
    const removedArrows = [];
    for (const [k, v] of currentNextMap) {
      if (prevNextMap.get(k) !== v) addedArrows.push({ from: k, to: v });
    }
    for (const [k, v] of prevNextMap) {
      if (!currentNextMap.has(k) || currentNextMap.get(k) !== v) {
        removedArrows.push({ from: k, to: v });
      }
    }
    const hasArrowChanges = addedArrows.length > 0 || removedArrows.length > 0;

    const layout = this._compute_layout();
    const pointers = this._extract_pointers(vars, listKey);
    const prevPtrs = this.lastRenderState ? this.lastRenderState.pointers || [] : [];

    // 检测指针移动
    const moved = [];
    for (const p of pointers) {
      const prev = prevPtrs.find(pp => pp.name === p.name);
      if (prev && prev.value !== p.value) {
        moved.push({ name: p.name, from: prev.value, to: p.value });
      }
    }

    const state = { list, pointers, layout, listKey, currentNextMap };

    // 动画速度控制：两次渲染间隔 < 300ms 视为快速播放，跳过动画
    const now = performance.now();
    const timeSinceLastRender = now - this._lastRenderTime;
    this._lastRenderTime = now;
    const isFastPlay = timeSinceLastRender > 0 && timeSinceLastRender < 300;

    const needsAnimation = (hasNewNodes || hasArrowChanges || moved.length > 0) && this.lastRenderState;

    if (isFastPlay && needsAnimation) {
      // 快速播放：立即完成所有动画状态
      for (const anim of this._arrowAnims.values()) anim.progress = anim.target;
      for (const [v] of this._valueToIndex) this._nodeAlphas.set(v, 1);
      this._render_list_static(state);
    } else if (needsAnimation) {
      this._animate_changes(state, this.lastRenderState, addedArrows, removedArrows, moved, hasNewNodes);
    } else {
      this._render_list_static(state);
    }

    this._prevNextMap = new Map(currentNextMap);
    this.lastRenderState = state;
  }

  _render_list_static(state) {
    const { ctx } = this;
    const { list, pointers, layout, currentNextMap } = state;
    const { nodeSpacing, startX, centerY } = layout;
    const r = this.options.nodeRadius;
    this.clear();

    const listSet = new Set(list);
    const pointerGroups = new Map();
    for (const ptr of pointers) {
      const key = ptr.isNull ? 'null' : String(ptr.value);
      if (!pointerGroups.has(key)) pointerGroups.set(key, []);
      pointerGroups.get(key).push(ptr.name);
    }

    // 1. 绘制所有已知节点（固定位置），新节点按 _nodeAlphas 透明度
    for (const [value, idx] of this._valueToIndex) {
      const x = startX + idx * nodeSpacing;
      const y = centerY;
      const isInList = listSet.has(value);
      const alpha = this._nodeAlphas.get(value) || 1;
      let color = isInList ? VIZ_COLORS.barDefault : 'rgba(100,116,139,0.3)';
      const ptr = pointers.find(p => p.value === idx);
      if (ptr && isInList) color = VIZ_COLORS.barActive;
      this._draw_node(ctx, x, y, r, value, color, alpha, idx.toString());
      if (isInList) {
        this._draw_pointer_label_group(ctx, x, y, r, pointerGroups.get(String(idx)) || [], VIZ_COLORS.pointerText);
      }
    }

    // 2. 收集所有需要绘制的箭头：currentNextMap + 正在缩回的箭头
    const arrowsToDraw = new Map();
    for (const [fromVal, toVal] of currentNextMap) {
      const key = `${fromVal}->${toVal}`;
      const anim = this._arrowAnims.get(key);
      const progress = anim ? anim.progress : 1;
      if (progress > 0) {
        arrowsToDraw.set(key, { from: fromVal, to: toVal, progress });
      }
    }
    for (const [key, anim] of this._arrowAnims) {
      if (anim.target === 0 && anim.progress > 0 && !arrowsToDraw.has(key)) {
        const [fromStr, toStr] = key.split('->');
        const toVal = toStr === 'null' ? null : Number(toStr);
        arrowsToDraw.set(key, { from: Number(fromStr), to: toVal, progress: anim.progress });
      }
    }

    // NULL 跟随当前尾节点，稍微脱离主链，尾节点用弯箭头指向它。
    const nullPos = this._compute_null_position(list, layout);
    const nullX = nullPos.x;
    const nullY = nullPos.y;

    for (const { from, to, progress } of arrowsToDraw.values()) {
      const fromX = this._get_node_x(from, layout);
      const fromY = centerY;
      let to_x, to_y;
      let useCurve = false;
      if (to === null) {
        to_x = nullX;
        to_y = nullY;
        useCurve = true;
      } else {
        to_x = this._get_node_x(to, layout);
        to_y = centerY;
        const fromIdx = this._valueToIndex.get(from);
        const toIdx = this._valueToIndex.get(to);
        if (Math.abs(fromIdx - toIdx) > 1) {
          useCurve = true;
        }
      }
      if (useCurve) {
        this._draw_curve_arrow(ctx, fromX, fromY, to_x, to_y, r, progress);
      } else {
        this._draw_arrow(ctx, fromX, fromY, to_x, to_y, r, progress);
      }
    }

    // 3. 绘制 NULL 标记（固定在最右端，间距与其他节点一致）
    this._draw_null_marker(ctx, nullX, nullY, r);
    this._draw_pointer_label_group(ctx, nullX, nullY, r, pointerGroups.get('null') || [], VIZ_COLORS.pointerText);
  }

  _animate_changes(state, prevState, addedArrows, removedArrows, moved, hasNewNodes) {
    const { list, layout } = state;
    const { nodeSpacing, startX, centerY } = layout;
    const r = this.options.nodeRadius;

    // 初始化箭头动画状态
    for (const a of addedArrows) {
      const key = `${a.from}->${a.to}`;
      this._arrowAnims.set(key, { progress: 0, target: 1 });
    }
    for (const a of removedArrows) {
      const key = `${a.from}->${a.to}`;
      this._arrowAnims.set(key, { progress: 1, target: 0 });
    }

    this.animate(800, (eased) => {
      const t = ease_in_out_cubic(eased);

      // 更新箭头动画进度
      for (const anim of this._arrowAnims.values()) {
        anim.progress = lerp(anim.progress, anim.target, 0.12);
      }

      // 新节点淡入：新值从 0 渐变到 1
      if (hasNewNodes) {
        for (const [value] of this._valueToIndex) {
          let alpha = this._nodeAlphas.get(value) || 0;
          if (alpha < 1) {
            alpha = Math.min(alpha + 0.04, 1);
            this._nodeAlphas.set(value, alpha);
          }
        }
      }

      // 绘制基础画面（节点 + 箭头）
      this._render_list_static(state);

      // 移动中的指针：从旧位置沿弧线移到新位置
      const ctx = this.ctx;
      for (const m of moved) {
        const fx = startX + m.from * nodeSpacing;
        const tx = startX + m.to * nodeSpacing;
        const cx = lerp(fx, tx, t);
        const arcY = centerY - 40 * Math.sin(t * Math.PI);
        const py = lerp(centerY, arcY, Math.sin(t * Math.PI));
        const val = list[m.to] !== undefined ? list[m.to] : '';
        this._draw_node(ctx, cx, py, r, val, VIZ_COLORS.barActive, 1);
        this._draw_pointer_label(ctx, cx, py, r, m.name, VIZ_COLORS.pointerText);
      }
    }, () => {
      // 动画结束，清理已完成的箭头动画
      for (const [key, anim] of this._arrowAnims) {
        if (anim.target === 0 && anim.progress < 0.05) {
          this._arrowAnims.delete(key);
        } else if (anim.target === 1 && anim.progress > 0.95) {
          anim.progress = 1;
        }
      }
      this._render_list_static(state);
    });
  }

  _extract_pointers(vars, listKey) {
    const ptrs = [];
    const listLen = Array.isArray(vars[listKey])
      ? vars[listKey].length
      : (this.lastRenderState && this.lastRenderState.list ? this.lastRenderState.list.length : 0);
    const ptrNames = ['head', 'curr', 'prev', 'current', 'nextTemp', 'slow', 'fast', 'p', 'q'];
    for (const name of ptrNames) {
      const val = vars[name];
      if (val === undefined || typeof val !== 'number') continue;
      if (val >= 0 && val < listLen) {
        ptrs.push({ name, value: val });
      } else if (val === -1) {
        ptrs.push({ name, value: this._valueToIndex.size, isNull: true });
      } else if (val <= -100000) {
        const nodeValue = -val - 100000;
        const idx = this._valueToIndex.get(nodeValue);
        if (idx !== undefined) ptrs.push({ name, value: idx });
      }
    }
    return ptrs;
  }
}

// ============================================================
// 二叉树渲染器 — 节点、左右孩子和当前指针
// ============================================================

class TreeRenderer extends BaseRenderer {
  constructor(canvasId, options = {}) {
    super(canvasId);
    this.options = {
      nodeRadius: 24,
      topPadding: 78,
      bottomPadding: 34,
      sidePadding: 64,
      maxTreeWidth: 620,
      levelGap: 72,
      ...options,
    };
    this.lastTree = null;
  }

  _is_tree_snapshot(value) {
    if (value === null) return true;
    if (!Array.isArray(value) || value.length !== 3) return false;
    return !Array.isArray(value[0]) && this._is_tree_snapshot(value[1]) && this._is_tree_snapshot(value[2]);
  }

  _find_tree_key(vars, stepData) {
    if (stepData.var_classes) {
      for (const [k, v] of Object.entries(stepData.var_classes)) {
        if (v.type === 'tree' && this._is_tree_snapshot(vars[k])) return k;
      }
    }
    for (const [k, v] of Object.entries(vars)) {
      if (this._is_tree_snapshot(v) && v !== null) return k;
    }
    return null;
  }

  _build_layout(tree) {
    const nodes = [];
    const edges = [];
    let order = 0;
    let maxDepth = 0;

    const visit = (node, depth, parentId = null) => {
      if (!node) return null;
      const id = nodes.length;
      const item = { id, value: node[0], depth, xOrder: 0, parentId };
      nodes.push(item);
      maxDepth = Math.max(maxDepth, depth);
      const leftId = visit(node[1], depth + 1, id);
      item.xOrder = order++;
      const rightId = visit(node[2], depth + 1, id);
      if (leftId !== null) edges.push({ from: id, to: leftId });
      if (rightId !== null) edges.push({ from: id, to: rightId });
      return id;
    };

    visit(tree, 0);
    if (nodes.length === 0) return { nodes, edges };

    const availW = Math.max(
      80,
      Math.min(this.options.maxTreeWidth, this.width - this.options.sidePadding * 2)
    );
    const leftX = (this.width - availW) / 2;
    const xStep = nodes.length <= 1 ? 0 : availW / (nodes.length - 1);
    const availableH = this.height - this.options.topPadding - this.options.bottomPadding;
    const neededH = maxDepth * this.options.levelGap;
    const levelGap = neededH > availableH
      ? Math.max(46, (this.height - this.options.topPadding - this.options.bottomPadding) / Math.max(maxDepth, 1))
      : this.options.levelGap;
    const treeH = maxDepth * levelGap;
    const topY = Math.max(
      this.options.topPadding,
      (this.height - treeH) / 2
    );

    for (const n of nodes) {
      n.x = leftX + (nodes.length === 1 ? availW / 2 : n.xOrder * xStep);
      n.y = topY + n.depth * levelGap;
    }
    return { nodes, edges };
  }

  _extract_highlights(vars) {
    const labelsByValue = new Map();
    const names = ['root', 'node', 'current', 'curr', 'p', 'q', 'lca', 'ancestor'];
    for (const name of names) {
      const value = vars[name];
      if (typeof value !== 'number' || value < 0 || value === 2147483647 || value === -2147483648) continue;
      if (!labelsByValue.has(value)) labelsByValue.set(value, []);
      labelsByValue.get(value).push(name);
    }
    return labelsByValue;
  }

  _draw_edge(ctx, from, to) {
    const r = this.options.nodeRadius;
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist <= r * 2) return;
    const ux = dx / dist;
    const uy = dy / dist;
    ctx.strokeStyle = 'rgba(148,163,184,0.38)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(from.x + ux * r, from.y + uy * r);
    ctx.lineTo(to.x - ux * r, to.y - uy * r);
    ctx.stroke();
  }

  _draw_node(ctx, node, labels) {
    const r = this.options.nodeRadius;
    const active = labels && labels.length > 0;
    ctx.save();
    ctx.fillStyle = active ? VIZ_COLORS.barActive : VIZ_COLORS.barDefault;
    ctx.strokeStyle = active ? VIZ_COLORS.pointerText : 'rgba(255,255,255,0.28)';
    ctx.lineWidth = active ? 3 : 2;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    const grad = ctx.createRadialGradient(node.x - r * 0.3, node.y - r * 0.3, 0, node.x, node.y, r);
    grad.addColorStop(0, 'rgba(255,255,255,0.20)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#fff';
    ctx.font = `bold ${Math.min(r * 0.78, 18)}px "JetBrains Mono", monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(node.value), node.x, node.y);

    if (active) {
      const text = labels.join('/');
      const tw = Math.max(28, text.length * 7 + 12);
      const bx = node.x - tw / 2;
      const by = node.y - r - 27;
      ctx.fillStyle = 'rgba(21,25,32,0.9)';
      ctx.strokeStyle = 'rgba(251,191,36,0.5)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      const br = 5;
      ctx.moveTo(bx + br, by);
      ctx.lineTo(bx + tw - br, by);
      ctx.arcTo(bx + tw, by, bx + tw, by + br, br);
      ctx.lineTo(bx + tw, by + 18 - br);
      ctx.arcTo(bx + tw, by + 18, bx + tw - br, by + 18, br);
      ctx.lineTo(bx + br, by + 18);
      ctx.arcTo(bx, by + 18, bx, by + 18 - br, br);
      ctx.lineTo(bx, by + br);
      ctx.arcTo(bx, by, bx + br, by, br);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = VIZ_COLORS.pointerText;
      ctx.font = 'bold 12px "JetBrains Mono", monospace';
      ctx.fillText(text, node.x, by + 9);
    }
    ctx.restore();
  }

  render(stepData, prevStepData) {
    this.stop_animation();
    const vars = stepData.vars || {};
    const treeKey = this._find_tree_key(vars, stepData);
    let tree = treeKey ? vars[treeKey] : null;
    if ((!treeKey || !tree) && this.lastTree) {
      tree = this.lastTree;
    }
    if (!tree) {
      this.clear();
      return;
    }
    this.lastTree = tree;
    const { nodes, edges } = this._build_layout(tree);
    const byId = new Map(nodes.map(n => [n.id, n]));
    const labelsByValue = this._extract_highlights(vars);
    if (nodes[0]) {
      if (!labelsByValue.has(nodes[0].value)) labelsByValue.set(nodes[0].value, []);
      const rootLabels = labelsByValue.get(nodes[0].value);
      if (!rootLabels.includes('root')) rootLabels.unshift('root');
    }

    this.clear();
    const { ctx, width } = this;
    ctx.save();
    ctx.fillStyle = 'rgba(30,35,54,0.9)';
    ctx.fillRect(0, 0, this.width, this.height);

    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(treeKey || 'tree', width / 2, 14);

    for (const edge of edges) {
      this._draw_edge(ctx, byId.get(edge.from), byId.get(edge.to));
    }
    for (const node of nodes) {
      this._draw_node(ctx, node, labelsByValue.get(node.value) || []);
    }
    ctx.restore();
  }
}

// ============================================================
// DP 表格渲染器 — 网格高亮 + 单元格着色
// ============================================================

class GridRenderer extends BaseRenderer {
  constructor(canvasId, options = {}) {
    super(canvasId);
    this.options = {
      cellSize: 36,
      topPadding: 50,
      leftPadding: 50,
      rightPadding: 50,
      bottomPadding: 50,
      ...options,
    };
    this.lastRenderState = null;
  }

  _find_grid_key(vars, stepData) {
    if (stepData.var_classes) {
      for (const [k, v] of Object.entries(stepData.var_classes)) {
        if (v.type === 'grid' && Array.isArray(vars[k]) && vars[k].length > 0 && Array.isArray(vars[k][0])) {
          return k;
        }
      }
    }
    for (const [k, v] of Object.entries(vars)) {
      if (Array.isArray(v) && v.length > 0 && Array.isArray(v[0])) return k;
    }
    return null;
  }

  _compute_layout(rows, cols) {
    const cs = this.options.cellSize;
    const availW = this.width - this.options.leftPadding - this.options.rightPadding;
    const availH = this.height - this.options.topPadding - this.options.bottomPadding;
    const cellW = Math.min(cs, availW / cols);
    const cellH = Math.min(cs, availH / rows);
    const s = Math.min(cellW, cellH);
    const gridW = cols * s;
    const gridH = rows * s;
    const ox = this.options.leftPadding + Math.max(0, (availW - gridW) / 2);
    const oy = this.options.topPadding + Math.max(10, (availH - gridH) / 2);
    return { cellSize: s, ox, oy, rows, cols };
  }

  _format_cell_value(value) {
    if (value === null || value === undefined) return '';
    if (typeof value !== 'number') return String(value);
    if (!Number.isFinite(value)) return '';
    if (value === 2147483647 || value >= 999999) return 'INF';
    if (value === -2147483648 || value <= -999999) return '';
    return Number.isInteger(value) ? String(value) : value.toPrecision(3);
  }

  _draw_cell(ctx, x, y, s, value, color) {
    ctx.fillStyle = color;
    ctx.fillRect(x + 1, y + 1, s - 2, s - 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
    ctx.strokeRect(x, y, s, s);
    const text = this._format_cell_value(value);
    if (s > 18 && text !== '') {
      ctx.fillStyle = 'rgba(255,255,255,0.85)';
      const fontSize = Math.min(s * (text.length > 3 ? 0.28 : 0.38), 13);
      ctx.font = `${fontSize}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, x + s / 2, y + s / 2);
    }
  }

  _draw_header(ctx, x, y, s, text, isCol) {
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '11px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    if (isCol) {
      ctx.fillText(text, x + s / 2, y - 8);
    } else {
      ctx.fillText(text, x - 8, y + s / 2);
    }
  }

  _draw_pointer_label(ctx, x, y, s, label, color) {
    ctx.save();
    ctx.fillStyle = color;
    ctx.font = 'bold 13px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    const px = x + s / 2;
    const py = y - 6;
    ctx.beginPath();
    ctx.moveTo(px, py);
    ctx.lineTo(px - 6, py - 8);
    ctx.lineTo(px + 6, py - 8);
    ctx.closePath();
    ctx.fill();
    ctx.fillText(label, px, py - 10);
    ctx.restore();
  }

  _effective_grid(grid, vars) {
    let rows = grid.length;
    let cols = rows > 0 ? grid[0].length : 0;
    if (Number.isFinite(Number(vars.W)) && Number.isFinite(Number(vars.n))) {
      rows = Math.min(rows, Number(vars.n) + 1);
      cols = Math.min(cols, Number(vars.W) + 1);
    } else if (Number.isFinite(Number(vars.m)) && Number.isFinite(Number(vars.n))) {
      rows = Math.min(rows, Number(vars.m) + 1);
      cols = Math.min(cols, Number(vars.n) + 1);
    }
    return grid.slice(0, rows).map(row => row.slice(0, cols));
  }

  render(stepData, prevStepData) {
    this.stop_animation();
    const vars = stepData.vars || {};
    const gridKey = this._find_grid_key(vars, stepData);
    if (!gridKey) { this.clear(); return; }

    const grid = this._effective_grid(vars[gridKey], vars);
    const rows = grid.length;
    const cols = rows > 0 ? grid[0].length : 0;
    if (rows === 0 || cols === 0 || rows > 20 || cols > 20) { this.clear(); return; }

    const layout = this._compute_layout(rows, cols);
    const { cellSize: s, ox, oy } = layout;
    this.clear();
    const { ctx } = this;

    // 高亮当前计算位置
    const iPos = vars.i !== undefined ? vars.i : -1;
    const jPos = vars.j !== undefined ? vars.j : (vars.w !== undefined ? vars.w : -1);

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = ox + c * s;
        const y = oy + r * s;
        let color = VIZ_COLORS.barDefault;

        // 当前格
        if (r === iPos && c === jPos) {
          color = VIZ_COLORS.barCompare; // 橙色
        }
        // 参考格（DP 转移来源）
        else if ((r === iPos - 1 && c === jPos) ||
                 (r === iPos && c === jPos - 1) ||
                 (r === iPos - 1 && c === jPos - 1)) {
          color = 'rgba(139,92,246,0.5)'; // 半透明紫
        }
        // 边界行/列
        else if (r === 0 || c === 0) {
          color = 'rgba(59,130,246,0.3)'; // 半透明蓝（初始值）
        }

        this._draw_cell(ctx, x, y, s, grid[r][c], color);
      }
    }

    // 行列标签
    for (let r = 0; r < rows; r++) {
      this._draw_header(ctx, ox, oy + r * s, s, r.toString(), false);
    }
    for (let c = 0; c < cols; c++) {
      this._draw_header(ctx, ox + c * s, oy - 10, s, c.toString(), true);
    }

    // 指针
    if (iPos >= 0 && iPos < rows && jPos >= 0 && jPos < cols) {
      this._draw_pointer_label(ctx, ox + jPos * s, oy + iPos * s, s, `i,j`, VIZ_COLORS.pointerText);
    }

    this.lastRenderState = { grid, gridKey, iPos, jPos, layout };
  }
}

// ============================================================
// 字符串匹配渲染器 — 上主串、下模式串，按 i/j 对齐比较
// ============================================================

class StringMatchRenderer extends BaseRenderer {
  constructor(canvasId, options = {}) {
    super(canvasId);
    this.options = {
      padX: 44,
      cellSize: 38,
      rowGap: 56,
      ...options,
    };
    this.lastMatch = null;
  }

  _find_match(vars, stepData) {
    if (stepData.var_classes) {
      for (const [k, v] of Object.entries(stepData.var_classes)) {
        const value = vars[k];
        if (v.type === 'string_match' && value && typeof value === 'object') return value;
      }
    }
    return vars.stringMatch || null;
  }

  _draw_tile(ctx, x, y, s, ch, color, stroke, active = false) {
    ctx.save();
    const grad = ctx.createLinearGradient(x, y, x, y + s);
    grad.addColorStop(0, color);
    grad.addColorStop(1, active ? 'rgba(59,130,246,0.92)' : 'rgba(30,64,175,0.92)');
    ctx.fillStyle = grad;
    ctx.strokeStyle = stroke || 'rgba(255,255,255,0.16)';
    ctx.lineWidth = active ? 2.4 : 1.2;
    ctx.shadowColor = 'rgba(0,0,0,0.24)';
    ctx.shadowBlur = 8;
    ctx.shadowOffsetY = 3;
    ctx.beginPath();
    ctx.roundRect(x, y, s, s, 6);
    ctx.fill();
    ctx.stroke();
    ctx.shadowColor = 'transparent';
    ctx.fillStyle = '#fff';
    ctx.font = `bold ${Math.floor(s * 0.54)}px "JetBrains Mono", monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(ch, x + s / 2, y + s / 2 + 1);
    ctx.restore();
  }

  _draw_mismatch(ctx, x, yTop, yBottom, s) {
    const cx = x + s / 2;
    ctx.save();
    ctx.strokeStyle = VIZ_COLORS.barSwap;
    ctx.fillStyle = VIZ_COLORS.barSwap;
    ctx.lineWidth = 2.4;
    ctx.beginPath();
    ctx.moveTo(cx, yTop + s + 5);
    ctx.bezierCurveTo(cx + 18, yTop + s + 20, cx + 18, yBottom - 16, cx, yBottom - 4);
    ctx.stroke();
    ctx.font = 'bold 23px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('≠', cx + 22, (yTop + yBottom + s) / 2);
    ctx.restore();
  }

  _draw_compare_line(ctx, x, yTop, yBottom, s, color) {
    const cx = x + s / 2;
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.moveTo(cx, yTop + s + 4);
    ctx.lineTo(cx, yBottom - 4);
    ctx.stroke();
    ctx.restore();
  }

  render(stepData, prevStepData) {
    this.stop_animation();
    const vars = stepData.vars || {};
    const match = this._find_match(vars, stepData);
    if (match) this.lastMatch = match;
    const state = match || this.lastMatch;
    this.clear();
    const { ctx, width, height } = this;
    ctx.save();
    ctx.fillStyle = 'rgba(30,35,54,0.9)';
    ctx.fillRect(0, 0, width, height);

    if (!state || !state.text || !state.pattern) {
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '14px -apple-system, "PingFang SC", sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('字符串匹配视图会在比较阶段出现', width / 2, height / 2);
      ctx.restore();
      return;
    }

    const text = Array.from(state.text);
    const pattern = Array.from(state.pattern);
    const offset = Math.max(0, Math.min(text.length - 1, Number(state.offset) || 0));
    const j = Number.isFinite(Number(state.j)) ? Number(state.j) : 0;
    const compareIdx = offset + Math.max(0, j);
    const cell = Math.min(
      this.options.cellSize,
      Math.floor((width - this.options.padX * 2) / Math.max(text.length, pattern.length + offset, 1))
    );
    const s = Math.max(20, cell);
    const textW = text.length * s;
    const textX = (width - textW) / 2;
    const topY = height / 2 - s - this.options.rowGap / 2;
    const patternX = textX + offset * s;
    const patternY = topY + s + this.options.rowGap;
    const modeName = state.mode === 'kmp' ? 'KMP' : state.mode === 'rk' ? 'Rabin-Karp' : 'BF';

    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(`${modeName} 字符串匹配`, width / 2, 16);

    text.forEach((ch, idx) => {
      const active = idx === compareIdx;
      const inWindow = idx >= offset && idx < offset + pattern.length;
      const color = active ? 'rgba(245,158,11,0.96)' : inWindow ? 'rgba(37,99,235,0.92)' : 'rgba(51,65,85,0.92)';
      this._draw_tile(ctx, textX + idx * s, topY, s, ch, color, active ? VIZ_COLORS.pointerText : null, active);
    });

    pattern.forEach((ch, idx) => {
      const textIdx = offset + idx;
      const active = idx === j || (state.success && idx < pattern.length);
      const matched = text[textIdx] === ch && idx < Math.max(j, 0);
      const color = state.success || matched ? 'rgba(16,185,129,0.94)' : active ? 'rgba(139,92,246,0.96)' : 'rgba(14,165,233,0.88)';
      this._draw_tile(ctx, patternX + idx * s, patternY, s, ch, color, active ? VIZ_COLORS.pointerText : null, active);
    });

    const maxLine = state.windowOnly ? 0 : Math.min(Math.max(j, 0), pattern.length - 1);
    for (let idx = 0; idx <= maxLine; idx++) {
      const textIdx = offset + idx;
      if (textIdx < 0 || textIdx >= text.length) continue;
      const x = textX + textIdx * s;
      const same = text[textIdx] === pattern[idx];
      if (state.mismatch && idx === j) this._draw_mismatch(ctx, x, topY, patternY, s);
      else if (same) this._draw_compare_line(ctx, x, topY, patternY, s, 'rgba(148,163,184,0.62)');
    }

    ctx.fillStyle = VIZ_COLORS.pointerText;
    ctx.font = 'bold 13px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    if (compareIdx >= 0 && compareIdx < text.length) {
      ctx.fillText(`i=${state.i}`, textX + compareIdx * s + s / 2, topY - 10);
    }
    if (!state.windowOnly && j >= 0 && j < pattern.length) {
      ctx.fillText(`j=${j}`, patternX + j * s + s / 2, patternY + s + 24);
    } else {
      ctx.fillText(`offset=${offset}`, patternX + pattern.length * s / 2, patternY + s + 24);
    }

    const caption = state.success
      ? `匹配成功: 起始位置 ${offset}`
      : state.mismatch
        ? '遇到失配: 模式串移动或回退, 主串不用回头'
        : state.windowOnly
          ? '先比较窗口摘要; 哈希相同后再逐字符确认'
          : '竖线表示正在逐字符比较的位置';
    ctx.fillStyle = 'rgba(21,25,32,0.84)';
    ctx.strokeStyle = 'rgba(73,164,238,0.28)';
    const boxW = Math.min(width - 90, Math.max(260, caption.length * 13));
    const boxX = (width - boxW) / 2;
    const boxY = height - 42;
    ctx.beginPath();
    ctx.roundRect(boxX, boxY, boxW, 28, 7);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = VIZ_COLORS.text;
    ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
    ctx.textBaseline = 'middle';
    ctx.fillText(caption, width / 2, boxY + 14);
    ctx.restore();
  }
}

// ============================================================
// 图渲染器 — 固定圆形布局 + 边权重 + 节点状态
// ============================================================

class GraphRenderer extends BaseRenderer {
  constructor(canvasId, options = {}) {
    super(canvasId);
    this.options = {
      nodeRadius: 22,
      sidePadding: 58,
      topPadding: 52,
      bottomPadding: 38,
      maxRadius: 190,
      ...options,
    };
    this.lastGraph = null;
  }

  _find_graph_key(vars, stepData) {
    if (stepData.var_classes) {
      for (const [k, v] of Object.entries(stepData.var_classes)) {
        const value = vars[k];
        if (v.type === 'graph' && value && typeof value === 'object' && Array.isArray(value.edges)) return k;
      }
    }
    for (const [k, v] of Object.entries(vars)) {
      if (v && typeof v === 'object' && !Array.isArray(v) && Array.isArray(v.edges)) return k;
    }
    return null;
  }

  _layout(nodesCount) {
    const cx = this.width / 2;
    const cy = this.height / 2;
    const r = Math.min(
      this.options.maxRadius,
      Math.max(70, Math.min(this.width - this.options.sidePadding * 2, this.height - this.options.topPadding - this.options.bottomPadding) / 2 - 18)
    );
    const result = [];
    for (let i = 0; i < nodesCount; i++) {
      const angle = -Math.PI / 2 + (Math.PI * 2 * i) / Math.max(nodesCount, 1);
      result.push({ x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r });
    }
    return result;
  }

  _format_dist(value) {
    if (value === undefined) return '';
    if (value === 2147483647 || value >= 999999) return 'INF';
    return String(value);
  }

  _draw_arrow_edge(ctx, from, to, weight, active) {
    const r = this.options.nodeRadius;
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist <= r * 2) return;
    const ux = dx / dist;
    const uy = dy / dist;
    const sx = from.x + ux * r;
    const sy = from.y + uy * r;
    const ex = to.x - ux * r;
    const ey = to.y - uy * r;

    ctx.save();
    ctx.strokeStyle = active ? VIZ_COLORS.barCompare : 'rgba(148,163,184,0.34)';
    ctx.fillStyle = ctx.strokeStyle;
    ctx.lineWidth = active ? 3 : 1.7;
    ctx.beginPath();
    ctx.moveTo(sx, sy);
    ctx.lineTo(ex, ey);
    ctx.stroke();

    const as = active ? 9 : 7;
    const ang = Math.atan2(ey - sy, ex - sx);
    ctx.beginPath();
    ctx.moveTo(ex, ey);
    ctx.lineTo(ex - Math.cos(ang) * as + Math.sin(ang) * as * 0.55, ey - Math.sin(ang) * as - Math.cos(ang) * as * 0.55);
    ctx.lineTo(ex - Math.cos(ang) * as - Math.sin(ang) * as * 0.55, ey - Math.sin(ang) * as + Math.cos(ang) * as * 0.55);
    ctx.closePath();
    ctx.fill();

    const mx = (sx + ex) / 2;
    const my = (sy + ey) / 2;
    ctx.fillStyle = active ? 'rgba(245,158,11,0.22)' : 'rgba(21,25,32,0.82)';
    ctx.strokeStyle = active ? 'rgba(245,158,11,0.6)' : 'rgba(148,163,184,0.22)';
    const label = String(weight);
    const tw = Math.max(18, label.length * 7 + 10);
    ctx.beginPath();
    ctx.roundRect(mx - tw / 2, my - 9, tw, 18, 5);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = active ? VIZ_COLORS.pointerText : VIZ_COLORS.textDim;
    ctx.font = '11px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, mx, my);
    ctx.restore();
  }

  _draw_node(ctx, idx, pos, vars, label = null) {
    const visited = Array.isArray(vars.visited) && vars.visited[idx];
    const current = vars.u === idx || vars.v === idx || vars.src === idx || vars.dest === idx;
    const r = this.options.nodeRadius;
    let color = VIZ_COLORS.barDefault;
    if (visited) color = VIZ_COLORS.barSorted;
    if (current) color = VIZ_COLORS.barActive;

    ctx.save();
    ctx.fillStyle = color;
    ctx.strokeStyle = current ? VIZ_COLORS.pointerText : 'rgba(255,255,255,0.28)';
    ctx.lineWidth = current ? 3 : 2;
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#fff';
    ctx.font = 'bold 16px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(label ?? idx), pos.x, pos.y);

    if (Array.isArray(vars.dist) && vars.dist[idx] !== undefined) {
      const text = this._format_dist(vars.dist[idx]);
      ctx.fillStyle = visited ? 'rgba(16,185,129,0.18)' : 'rgba(21,25,32,0.88)';
      ctx.strokeStyle = visited ? 'rgba(16,185,129,0.45)' : 'rgba(73,164,238,0.35)';
      const tw = Math.max(32, text.length * 7 + 12);
      ctx.beginPath();
      ctx.roundRect(pos.x - tw / 2, pos.y + r + 7, tw, 18, 5);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = visited ? '#bbf7d0' : VIZ_COLORS.text;
      ctx.font = '11px "JetBrains Mono", monospace';
      ctx.fillText(text, pos.x, pos.y + r + 16);
    }
    ctx.restore();
  }

  render(stepData, prevStepData) {
    this.stop_animation();
    const vars = stepData.vars || {};
    const graphKey = this._find_graph_key(vars, stepData);
    if (graphKey) this.lastGraph = vars[graphKey];
    const graph = graphKey ? vars[graphKey] : this.lastGraph;
    if (!graph || !Array.isArray(graph.edges)) {
      this.clear();
      return;
    }

    const n = Math.max(0, Number(graph.nodes) || 0);
    const labels = Array.isArray(graph.labels) ? graph.labels : [];
    const pos = this._layout(n);
    this.clear();
    const { ctx } = this;
    ctx.save();
    ctx.fillStyle = 'rgba(30,35,54,0.9)';
    ctx.fillRect(0, 0, this.width, this.height);

    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(graphKey || 'graph', this.width / 2, 16);

    for (const edge of graph.edges) {
      const [from, to, weight] = edge;
      if (!pos[from] || !pos[to]) continue;
      const active = vars.u === from && (vars.v === undefined || vars.v === to);
      this._draw_arrow_edge(ctx, pos[from], pos[to], weight, active);
    }
    for (let i = 0; i < n; i++) {
      this._draw_node(ctx, i, pos[i], vars, labels[i]);
    }
    ctx.restore();
  }
}

// ============================================================
// 二分图渲染器 — 左右两列 + 匹配边高亮
// ============================================================

class BipartiteGraphRenderer extends BaseRenderer {
  constructor(canvasId, options = {}) {
    super(canvasId);
    this.options = {
      nodeRadius: 20,
      columnHalfGap: 190,
      topPadding: 76,
      bottomPadding: 76,
      ...options,
    };
    this.lastGraph = null;
  }

  _find_graph_key(vars, stepData) {
    if (stepData.var_classes) {
      for (const [k, v] of Object.entries(stepData.var_classes)) {
        const value = vars[k];
        if (v.type === 'bipartite' && value && typeof value === 'object' && Array.isArray(value.edges)) return k;
      }
    }
    for (const [k, v] of Object.entries(vars)) {
      if (v && typeof v === 'object' && !Array.isArray(v) && Array.isArray(v.edges) && Number.isFinite(Number(v.left)) && Number.isFinite(Number(v.right))) return k;
    }
    return null;
  }

  _layout(count, x) {
    const availableH = this.height - this.options.topPadding - this.options.bottomPadding;
    const span = count <= 1 ? 0 : Math.min(availableH, (count - 1) * 72);
    const gap = count <= 1 ? 0 : span / (count - 1);
    const yMid = this.height / 2;
    const top = yMid - span / 2;
    const out = [];
    for (let i = 0; i < count; i++) {
      out.push({ x, y: count <= 1 ? yMid : top + i * gap });
    }
    return out;
  }

  _is_matched_edge(graph, leftIdx, rightIdx) {
    return Array.isArray(graph.match) && graph.match[rightIdx] === leftIdx;
  }

  _draw_edge(ctx, from, to, matched, active) {
    ctx.save();
    ctx.strokeStyle = matched ? VIZ_COLORS.barSorted : (active ? VIZ_COLORS.barCompare : 'rgba(148,163,184,0.28)');
    ctx.lineWidth = matched ? 3.2 : (active ? 2.8 : 1.5);
    ctx.globalAlpha = matched || active ? 1 : 0.72;
    ctx.beginPath();
    ctx.moveTo(from.x + this.options.nodeRadius, from.y);
    const c1x = from.x + (to.x - from.x) * 0.36;
    const c2x = from.x + (to.x - from.x) * 0.64;
    ctx.bezierCurveTo(c1x, from.y, c2x, to.y, to.x - this.options.nodeRadius, to.y);
    ctx.stroke();
    ctx.restore();
  }

  _draw_node(ctx, pos, label, active, matched, side) {
    const r = this.options.nodeRadius;
    let color = side === 'left' ? VIZ_COLORS.barDefault : '#64748b';
    if (matched) color = VIZ_COLORS.barSorted;
    if (active) color = VIZ_COLORS.barActive;

    ctx.save();
    ctx.fillStyle = color;
    ctx.strokeStyle = active ? VIZ_COLORS.pointerText : 'rgba(255,255,255,0.28)';
    ctx.lineWidth = active ? 3 : 2;
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#fff';
    ctx.font = 'bold 14px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(label), pos.x, pos.y);
    ctx.restore();
  }

  _draw_column_title(ctx, text, x) {
    ctx.save();
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(text, x, Math.max(54, this.options.topPadding - 36));
    ctx.restore();
  }

  render(stepData, prevStepData) {
    this.stop_animation();
    const vars = stepData.vars || {};
    const key = this._find_graph_key(vars, stepData);
    if (key) this.lastGraph = vars[key];
    const graph = key ? vars[key] : this.lastGraph;
    if (!graph || !Array.isArray(graph.edges)) {
      this.clear();
      return;
    }

    const leftN = Math.max(0, Number(graph.left) || 0);
    const rightN = Math.max(0, Number(graph.right) || 0);
    const halfGap = Math.min(this.options.columnHalfGap, this.width * 0.28);
    const leftX = this.width / 2 - halfGap;
    const rightX = this.width / 2 + halfGap;
    const leftPos = this._layout(leftN, leftX);
    const rightPos = this._layout(rightN, rightX);
    const activeLeft = Number.isFinite(Number(vars.u)) ? Number(vars.u) - 1 : -1;
    const activeRight = Number.isFinite(Number(vars.v)) ? Number(vars.v) - 1 : -1;

    this.clear();
    const { ctx } = this;
    ctx.save();
    ctx.fillStyle = 'rgba(30,35,54,0.9)';
    ctx.fillRect(0, 0, this.width, this.height);
    this._draw_column_title(ctx, '左侧', leftX);
    this._draw_column_title(ctx, '右侧', rightX);

    for (const edge of graph.edges) {
      const [l, r] = edge;
      if (!leftPos[l] || !rightPos[r]) continue;
      const matched = this._is_matched_edge(graph, l, r);
      const active = (activeLeft === l && (activeRight < 0 || activeRight === r));
      this._draw_edge(ctx, leftPos[l], rightPos[r], matched, active);
    }

    const matchedLeft = new Set();
    const matchedRight = new Set();
    if (Array.isArray(graph.match)) {
      graph.match.forEach((l, r) => {
        if (l >= 0) {
          matchedLeft.add(l);
          matchedRight.add(r);
        }
      });
    }

    for (let i = 0; i < leftN; i++) {
      this._draw_node(ctx, leftPos[i], i + 1, activeLeft === i, matchedLeft.has(i), 'left');
    }
    for (let i = 0; i < rightN; i++) {
      this._draw_node(ctx, rightPos[i], i + 1, activeRight === i, matchedRight.has(i), 'right');
    }
    ctx.restore();
  }
}

// ============================================================
// 概念动画渲染器 — 不依赖C代码插桩, 用手写状态解释算法本质
// ============================================================

class ConceptRenderer extends BaseRenderer {
  constructor(canvasId, options = {}) {
    super(canvasId);
    this.options = {
      pad: 36,
      ...options,
    };
    this.lastConcept = null;
  }

  _get_concept(vars) {
    if (vars.concept && typeof vars.concept === 'object') {
      this.lastConcept = vars.concept;
    }
    return vars.concept || this.lastConcept;
  }

  render(stepData, prevStepData) {
    const concept = this._get_concept(stepData.vars || {});
    if (!concept) {
      this.clear();
      return;
    }
    this.clear();
    const { ctx } = this;
    ctx.save();
    ctx.fillStyle = 'rgba(30,35,54,0.9)';
    ctx.fillRect(0, 0, this.width, this.height);
    if (concept.kind === 'convex_hull') this._draw_convex_hull(ctx, concept);
    else if (concept.kind === 'euclid') this._draw_euclid(ctx, concept);
    else if (concept.kind === 'n_queens') this._draw_n_queens(ctx, concept);
    else if (concept.kind === 'sudoku') this._draw_sudoku(ctx, concept);
    else if (concept.kind === 'merge_sort') this._draw_merge_sort(ctx, concept);
    else if (concept.kind === 'skip_list') this._draw_skip_list(ctx, concept);
    else if (concept.kind === 'recursion_tree') this._draw_recursion_tree(ctx, concept);
    else if (concept.kind === 'monte_carlo') this._draw_monte_carlo(ctx, concept);
    else if (concept.kind === 'sum_demo') this._draw_sum_demo(ctx, concept);
    else if (concept.kind === 'array_process') this._draw_array_process(ctx, concept);
    else if (concept.kind === 'karatsuba') this._draw_karatsuba(ctx, concept);
    else if (concept.kind === 'complexity_tree') this._draw_complexity_tree(ctx, concept);
    else if (concept.kind === 'complexity_ladder') this._draw_complexity_ladder(ctx, concept);
    else if (concept.kind === 'space_compare') this._draw_space_compare(ctx, concept);
    else if (concept.kind === 'dynamic_array') this._draw_dynamic_array(ctx, concept);
    else if (concept.kind === 'halting') this._draw_halting(ctx, concept);
    else if (concept.kind === 'answer_search') this._draw_answer_search(ctx, concept);
    else if (concept.kind === 'distribution_sort') this._draw_distribution_sort(ctx, concept);
    else if (concept.kind === 'stable_counting') this._draw_stable_counting(ctx, concept);
    else if (concept.kind === 'stability_compare') this._draw_stability_compare(ctx, concept);
    else if (concept.kind === 'external_sort') this._draw_external_sort(ctx, concept);
    else if (concept.kind === 'activity_selection') this._draw_activity_selection(ctx, concept);
    else if (concept.kind === 'huffman') this._draw_huffman(ctx, concept);
    else if (concept.kind === 'kruskal') this._draw_kruskal(ctx, concept);
    else if (concept.kind === 'birthday') this._draw_birthday(ctx, concept);
    else if (concept.kind === 'reservoir_sampling') this._draw_reservoir_sampling(ctx, concept);
    else if (concept.kind === 'bloom_filter') this._draw_bloom_filter(ctx, concept);
    else if (concept.kind === 'bitmask_tsp') this._draw_bitmask_tsp(ctx, concept);
    else if (concept.kind === 'lz77') this._draw_lz77(ctx, concept);
    else if (concept.kind === 'pagerank') this._draw_page_rank(ctx, concept);
    else if (concept.kind === 'gradient') this._draw_gradient(ctx, concept);
    else if (concept.kind === 'dp_rolling') this._draw_dp_rolling(ctx, concept);
    else if (concept.kind === 'dp_table') this._draw_dp_table(ctx, concept);
    else if (concept.kind === 'shortest_path') this._draw_shortest_path(ctx, concept);
    else if (concept.kind === 'branch_bound') this._draw_branch_bound(ctx, concept);
    else if (concept.kind === 'flood_fill') this._draw_flood_fill(ctx, concept);
    else if (concept.kind === 'tarjan_scc') this._draw_tarjan_scc(ctx, concept);
    else if (concept.kind === 'hungarian_matching') this._draw_hungarian_matching(ctx, concept);
    else if (concept.kind === 'max_flow') this._draw_max_flow(ctx, concept);
    else if (concept.kind === 'string_match_concept') this._draw_string_match_concept(ctx, concept);
    else if (concept.kind === 'kmp_table') this._draw_kmp_table(ctx, concept);
    else if (concept.kind === 'trie') this._draw_trie_like(ctx, concept, false);
    else if (concept.kind === 'ac_automaton') this._draw_trie_like(ctx, concept, true);
    else if (concept.kind === 'union_find') this._draw_union_find(ctx, concept);
    else if (concept.kind === 'red_black_tree') this._draw_red_black_tree_concept(ctx, concept);
    else if (concept.kind === 'segment_tree') this._draw_segment_tree_concept(ctx, concept);
    else if (concept.kind === 'fenwick') this._draw_fenwick_concept(ctx, concept);
    else if (concept.kind === 'bit_visual') this._draw_bit_visual(ctx, concept);
    else this._draw_unknown(ctx, concept);
    ctx.restore();
  }

  _draw_title(ctx, title, subtitle) {
    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillStyle = VIZ_COLORS.text;
    this._fit_font(ctx, title, this.width - 72, size => `bold ${size}px -apple-system, "PingFang SC", sans-serif`, 16, 12);
    ctx.fillText(title, this.width / 2, 18);
    if (subtitle) {
      ctx.fillStyle = VIZ_COLORS.textDim;
      this._fit_font(ctx, subtitle, this.width - 92, size => `${size}px -apple-system, "PingFang SC", sans-serif`, 13, 10);
      ctx.fillText(subtitle, this.width / 2, 42);
    }
    ctx.restore();
  }

  _fit_font(ctx, text, maxWidth, fontForSize, startSize, minSize = 10) {
    let size = startSize;
    ctx.font = fontForSize(size);
    while (size > minSize && ctx.measureText(String(text)).width > maxWidth) {
      size -= 1;
      ctx.font = fontForSize(size);
    }
    return size;
  }

  _fill_text_fit(ctx, text, x, y, maxWidth, fontForSize, startSize, minSize = 10) {
    this._fit_font(ctx, text, maxWidth, fontForSize, startSize, minSize);
    ctx.fillText(String(text), x, y);
  }

  _scale_points(points) {
    const xs = points.map(p => p[0]);
    const ys = points.map(p => p[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const padX = Math.max(72, this.width * 0.14);
    const padTop = 78;
    const padBottom = 34;
    const availW = this.width - padX * 2;
    const availH = this.height - padTop - padBottom;
    const scale = Math.min(availW / Math.max(1, maxX - minX), availH / Math.max(1, maxY - minY));
    const usedW = (maxX - minX) * scale;
    const usedH = (maxY - minY) * scale;
    const offX = (this.width - usedW) / 2;
    const offY = padTop + (availH - usedH) / 2;
    return points.map(([x, y]) => ({ x: offX + (x - minX) * scale, y: offY + (y - minY) * scale }));
  }

  _draw_convex_hull(ctx, concept) {
    const points = Array.isArray(concept.points) ? concept.points : [];
    if (!points.length) return;
    const pos = this._scale_points(points);
    const stack = Array.isArray(concept.stack) ? concept.stack : [];
    const popped = new Set(concept.popped || []);
    const inStack = new Set(stack);
    const current = concept.current;
    this._draw_title(ctx, 'Graham扫描求凸包', concept.stack && concept.stack.length ? '栈里留下的点, 正在变成外层橡皮筋' : '');

    ctx.save();
    ctx.strokeStyle = 'rgba(73,164,238,0.16)';
    ctx.lineWidth = 1;
    for (let i = 0; i < pos.length; i++) {
      for (let j = i + 1; j < pos.length; j++) {
        const dx = pos[i].x - pos[j].x;
        const dy = pos[i].y - pos[j].y;
        if (Math.sqrt(dx * dx + dy * dy) < 110) {
          ctx.beginPath();
          ctx.moveTo(pos[i].x, pos[i].y);
          ctx.lineTo(pos[j].x, pos[j].y);
          ctx.stroke();
        }
      }
    }

    const edges = Array.isArray(concept.hullEdges) ? concept.hullEdges : [];
    edges.forEach(([a, b]) => {
      if (!pos[a] || !pos[b]) return;
      ctx.strokeStyle = VIZ_COLORS.barSorted;
      ctx.lineWidth = 4;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(pos[a].x, pos[a].y);
      ctx.lineTo(pos[b].x, pos[b].y);
      ctx.stroke();
    });

    points.forEach((_, idx) => {
      const p = pos[idx];
      const active = idx === current;
      const keep = inStack.has(idx);
      const out = popped.has(idx);
      ctx.fillStyle = out ? 'rgba(127,132,142,0.45)' : keep ? VIZ_COLORS.barSorted : VIZ_COLORS.barDefault;
      if (active) ctx.fillStyle = VIZ_COLORS.barActive;
      ctx.strokeStyle = active ? VIZ_COLORS.pointerText : 'rgba(255,255,255,0.26)';
      ctx.lineWidth = active ? 3 : 2;
      ctx.beginPath();
      ctx.arc(p.x, p.y, active ? 11 : 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '11px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(String(idx), p.x, p.y - 18);
    });

    if (stack.length >= 2) {
      ctx.strokeStyle = 'rgba(251,191,36,0.7)';
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 5]);
      ctx.beginPath();
      stack.forEach((idx, i) => {
        const p = pos[idx];
        if (!p) return;
        if (i === 0) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
      });
      ctx.stroke();
      ctx.setLineDash([]);
    }

    this._draw_caption(ctx, concept.current === null || concept.current === undefined ? '最终只剩外层点: 凸包完成' : '扫描一个点: 如果右转, 弹出凹进去的点');
    ctx.restore();
  }

  _draw_euclid(ctx, concept) {
    this._draw_title(ctx, '欧几里得算法', 'gcd(a,b) = gcd(b, a % b)');
    const centerY = this.height / 2 + 6;
    const nums = [
      { label: 'a', value: concept.a, x: this.width * 0.26, color: VIZ_COLORS.barDefault },
      { label: 'b', value: concept.b, x: this.width * 0.50, color: concept.done ? '#64748b' : VIZ_COLORS.barActive },
      { label: '余数', value: concept.r, x: this.width * 0.74, color: concept.done ? VIZ_COLORS.barSorted : VIZ_COLORS.barCompare },
    ];

    ctx.save();
    nums.forEach((item, idx) => {
      ctx.fillStyle = item.color;
      ctx.strokeStyle = 'rgba(255,255,255,0.24)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.roundRect(item.x - 56, centerY - 38, 112, 76, 10);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.font = 'bold 24px "JetBrains Mono", monospace';
      ctx.fillText(String(item.value), item.x, centerY + 6);
      ctx.font = '12px -apple-system, "PingFang SC", sans-serif';
      ctx.fillText(item.label, item.x, centerY - 22);
      if (idx < nums.length - 1) this._draw_arrow(ctx, item.x + 68, centerY, nums[idx + 1].x - 68, centerY);
    });

    ctx.fillStyle = concept.done ? '#bbf7d0' : VIZ_COLORS.text;
    ctx.font = 'bold 15px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(concept.expr || '', this.width / 2, centerY + 62);
    this._draw_caption(ctx, concept.done ? `b 已经变成 0, 最大公约数是 ${concept.a}` : '把 b 和余数向左推进, 数字会迅速变小');
    ctx.restore();
  }

  _draw_n_queens(ctx, concept) {
    const n = concept.n || 4;
    const queens = Array.isArray(concept.queens) ? concept.queens : [];
    const current = Array.isArray(concept.current) ? concept.current : null;
    const conflicts = Array.isArray(concept.conflicts) ? concept.conflicts : [];
    const conflictKeys = new Set(conflicts.map(([r, c]) => `${r},${c}`));
    const subtitle = concept.mode === 'diagonal'
      ? '列、主对角线、副对角线三张表一起剪枝'
      : '每行尝试一个位置, 冲突就回退';
    this._draw_title(ctx, 'N皇后回溯', subtitle);

    const cell = Math.min(54, Math.floor(Math.min(this.height - 112, this.width * 0.48) / n));
    const boardSize = cell * n;
    const sideW = concept.mode === 'diagonal' ? 220 : 150;
    const gap = 44;
    const totalW = boardSize + gap + sideW;
    const startX = Math.max(34, (this.width - totalW) / 2);
    const startY = Math.max(72, (this.height - boardSize) / 2);

    ctx.save();
    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        const x = startX + c * cell;
        const y = startY + r * cell;
        const active = current && current[0] === r && current[1] === c;
        const conflict = conflictKeys.has(`${r},${c}`);
        ctx.fillStyle = (r + c) % 2 === 0 ? 'rgba(73,164,238,0.18)' : 'rgba(255,255,255,0.06)';
        if (active) ctx.fillStyle = 'rgba(245,158,11,0.62)';
        if (conflict) ctx.fillStyle = 'rgba(239,68,68,0.46)';
        ctx.strokeStyle = 'rgba(255,255,255,0.16)';
        ctx.lineWidth = 1;
        ctx.fillRect(x, y, cell, cell);
        ctx.strokeRect(x, y, cell, cell);
      }
    }

    conflicts.forEach(([r, c], idx) => {
      if (!current || idx === conflicts.length - 1) return;
      const x1 = startX + c * cell + cell / 2;
      const y1 = startY + r * cell + cell / 2;
      const x2 = startX + current[1] * cell + cell / 2;
      const y2 = startY + current[0] * cell + cell / 2;
      ctx.strokeStyle = 'rgba(239,68,68,0.72)';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    });

    queens.forEach((col, row) => {
      if (col < 0 || col >= n) return;
      const cx = startX + col * cell + cell / 2;
      const cy = startY + row * cell + cell / 2;
      ctx.fillStyle = VIZ_COLORS.barSorted;
      ctx.strokeStyle = 'rgba(255,255,255,0.36)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, cell * 0.32, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = `bold ${Math.floor(cell * 0.42)}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('Q', cx, cy + 1);
    });

    const sideX = startX + boardSize + gap;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillStyle = VIZ_COLORS.text;
    ctx.font = 'bold 14px -apple-system, "PingFang SC", sans-serif';
    ctx.fillText('搜索状态', sideX, startY + 2);
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
    const rows = [
      `当前行: ${Math.min(concept.queens ? concept.queens.filter(v => v >= 0).length : 0, n)}`,
      `已放皇后: ${queens.filter(v => v >= 0).length}/${n}`,
      `已找到解: ${concept.solutions || 0}`,
    ];
    rows.forEach((text, idx) => ctx.fillText(text, sideX, startY + 30 + idx * 24));

    if (concept.mode === 'diagonal') {
      this._draw_mini_bits(ctx, sideX, startY + 122, '列', n, queens.filter(v => v >= 0));
      const diag1 = queens.flatMap((col, row) => col >= 0 ? [row - col + n - 1] : []);
      const diag2 = queens.flatMap((col, row) => col >= 0 ? [row + col] : []);
      this._draw_mini_bits(ctx, sideX, startY + 166, '主对角线', n * 2 - 1, diag1);
      this._draw_mini_bits(ctx, sideX, startY + 210, '副对角线', n * 2 - 1, diag2);
    }

    this._draw_caption(ctx, current ? '黄色格子是当前尝试; 红色表示冲突, 这条分支会被剪掉' : '一行一个皇后, 所有列和对角线都不冲突时得到一个解');
    ctx.restore();
  }

  _draw_mini_bits(ctx, x, y, label, count, activeIndices) {
    const active = new Set(activeIndices);
    ctx.save();
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '12px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(label, x, y);
    const size = 13;
    for (let i = 0; i < count; i++) {
      const bx = x + i * (size + 4);
      ctx.fillStyle = active.has(i) ? VIZ_COLORS.barSorted : 'rgba(255,255,255,0.08)';
      ctx.strokeStyle = 'rgba(255,255,255,0.15)';
      ctx.beginPath();
      ctx.roundRect(bx, y + 18, size, size, 3);
      ctx.fill();
      ctx.stroke();
    }
    ctx.restore();
  }

  _draw_sudoku(ctx, concept) {
    const board = Array.isArray(concept.board) ? concept.board : [];
    const givens = Array.isArray(concept.givens) ? concept.givens : [];
    const cellInfo = Array.isArray(concept.cell) ? concept.cell : null;
    const conflicts = new Set((concept.conflicts || []).map(([r, c]) => `${r},${c}`));
    this._draw_title(ctx, '数独回溯', '行、列、九宫格都合法, 才能继续往下填');

    const compact = this.width < 620;
    const cell = Math.min(34, Math.floor(Math.min(this.height - 108, this.width * 0.48) / 9));
    const size = cell * 9;
    const sideW = compact ? this.width - 48 : 190;
    const gap = compact ? 0 : 42;
    const totalW = compact ? size : size + gap + sideW;
    const startX = compact ? (this.width - size) / 2 : Math.max(30, (this.width - totalW) / 2);
    const startY = compact ? 86 : Math.max(66, (this.height - size) / 2);

    ctx.save();
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        const x = startX + c * cell;
        const y = startY + r * cell;
        const isGiven = givens[r] && givens[r][c] !== 0;
        const active = cellInfo && cellInfo[0] === r && cellInfo[1] === c;
        const conflict = conflicts.has(`${r},${c}`);
        ctx.fillStyle = isGiven ? 'rgba(73,164,238,0.20)' : 'rgba(255,255,255,0.05)';
        if (active) ctx.fillStyle = 'rgba(245,158,11,0.58)';
        if (conflict) ctx.fillStyle = 'rgba(239,68,68,0.42)';
        ctx.fillRect(x, y, cell, cell);

        const value = board[r] ? board[r][c] : 0;
        if (value) {
          ctx.fillStyle = isGiven ? VIZ_COLORS.text : (active ? '#fff' : '#bbf7d0');
          ctx.font = `${isGiven ? 'bold' : 'normal'} ${Math.floor(cell * 0.56)}px "JetBrains Mono", monospace`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(String(value), x + cell / 2, y + cell / 2 + 1);
        }
      }
    }

    for (let i = 0; i <= 9; i++) {
      ctx.strokeStyle = i % 3 === 0 ? 'rgba(255,255,255,0.46)' : 'rgba(255,255,255,0.13)';
      ctx.lineWidth = i % 3 === 0 ? 2 : 1;
      ctx.beginPath();
      ctx.moveTo(startX + i * cell, startY);
      ctx.lineTo(startX + i * cell, startY + size);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(startX, startY + i * cell);
      ctx.lineTo(startX + size, startY + i * cell);
      ctx.stroke();
    }

    const sideX = compact ? 24 : startX + size + gap;
    const sideY = compact ? startY + size + 24 : startY;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillStyle = VIZ_COLORS.text;
    ctx.font = 'bold 14px -apple-system, "PingFang SC", sans-serif';
    ctx.fillText('当前动作', sideX, sideY);
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
    if (cellInfo) {
      ctx.fillText(`空格: (${cellInfo[0] + 1}, ${cellInfo[1] + 1})`, sideX, sideY + 32);
      ctx.fillText(`候选数字: ${concept.try || '-'}`, sideX, sideY + 56);
      ctx.fillText(conflicts.size ? '发现冲突, 准备换数' : '检查通过, 可以深入', sideX, sideY + 80);
    } else {
      ctx.fillText('所有空格都填完', sideX, sideY + 32);
      ctx.fillText('每行、每列、每宫都合法', sideX, sideY + 56);
    }

    this._draw_caption(ctx, concept.done ? '数独完成: 回溯只保留一路合法选择' : '先试一个数; 未来走不通时, 再撤销它换下一个候选');
    ctx.restore();
  }

  _draw_merge_sort(ctx, concept) {
    const nodes = Array.isArray(concept.nodes) ? concept.nodes : [];
    const splitEdges = Array.isArray(concept.splitEdges) ? concept.splitEdges : [];
    const mergeEdges = Array.isArray(concept.mergeEdges) ? concept.mergeEdges : [];
    const activeSplit = new Set((concept.activeSplit || []).map(e => `${e[0]}>${e[1]}`));
    const activeMerge = new Set((concept.activeMerge || []).map(e => `${e[0]}>${e[1]}`));
    const activeNodes = new Set(concept.activeNodes || []);
    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    this._draw_title(ctx, concept.title || '归并排序', '蓝色向下分解, 绿色向下合并');

    const drawW = Math.min(this.width - 100, 760);
    const drawH = Math.min(this.height - 118, 390);
    const left = (this.width - drawW) / 2;
    const top = Math.max(70, (this.height - drawH) / 2 - 8);
    const pos = new Map(nodes.map(n => [n.id, { x: left + n.x * drawW, y: top + n.y * drawH }]));

    ctx.save();
    const draw_edge = (edge, color, active, label) => {
      const from = pos.get(edge[0]);
      const to = pos.get(edge[1]);
      if (!from || !to) return;
      this._draw_arrow(ctx, from.x, from.y + 18, to.x, to.y - 18, active ? color : color.replace('0.82', '0.28'), active ? color : color.replace('0.82', '0.38'), active ? 3 : 1.8);
      if (active && label) {
        const mx = (from.x + to.x) / 2;
        const my = (from.y + to.y) / 2 - 7;
        ctx.fillStyle = color;
        ctx.font = 'bold 15px -apple-system, "PingFang SC", sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(label, mx, my);
      }
    };

    splitEdges.forEach(edge => draw_edge(edge, 'rgba(73,164,238,0.82)', activeSplit.has(`${edge[0]}>${edge[1]}`), '分'));
    mergeEdges.forEach(edge => draw_edge(edge, 'rgba(34,197,94,0.82)', activeMerge.has(`${edge[0]}>${edge[1]}`), '合'));

    const compareGroups = Array.isArray(concept.compareGroups) ? concept.compareGroups : [];
    compareGroups.forEach(group => {
      const pts = group.map(id => pos.get(id)).filter(Boolean);
      if (pts.length < 2) return;
      const minX = Math.min(...pts.map(p => p.x));
      const maxX = Math.max(...pts.map(p => p.x));
      const y = Math.min(...pts.map(p => p.y)) - 28;
      ctx.strokeStyle = 'rgba(251,191,36,0.65)';
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 4]);
      ctx.beginPath();
      ctx.moveTo(minX, y);
      ctx.quadraticCurveTo((minX + maxX) / 2, y - 18, maxX, y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = VIZ_COLORS.pointerText;
      ctx.font = '12px -apple-system, "PingFang SC", sans-serif';
      ctx.textAlign = 'center';
      if (this.width >= 620) {
        ctx.fillText('比较并合并', (minX + maxX) / 2, y - 22);
      }
    });

    nodes.forEach(node => {
      const p = pos.get(node.id);
      if (!p) return;
      const values = Array.isArray(node.values) ? node.values : [];
      const isActive = activeNodes.has(node.id);
      const isMerge = node.phase === 'merge' || node.phase === 'done';
      const isDone = node.phase === 'done';
      const text = values.join(', ');
      const w = Math.max(48, Math.min(250, values.length * 30 + 22));
      const h = values.length > 4 ? 38 : 34;
      ctx.fillStyle = isDone ? 'rgba(245,158,11,0.18)' : isMerge ? 'rgba(34,197,94,0.13)' : 'rgba(73,164,238,0.12)';
      ctx.strokeStyle = isDone ? 'rgba(251,191,36,0.92)' : isMerge ? 'rgba(34,197,94,0.82)' : 'rgba(73,164,238,0.82)';
      if (isActive) {
        ctx.fillStyle = isDone ? 'rgba(245,158,11,0.30)' : isMerge ? 'rgba(34,197,94,0.24)' : 'rgba(73,164,238,0.24)';
      }
      ctx.lineWidth = isActive || isDone ? 2.6 : 1.8;
      ctx.beginPath();
      ctx.roundRect(p.x - w / 2, p.y - h / 2, w, h, 7);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = isDone ? '#fde68a' : VIZ_COLORS.text;
      ctx.font = `bold ${values.length > 4 ? 14 : 16}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, p.x, p.y + 1);
    });

    const splitCount = splitEdges.length;
    const mergeCount = mergeEdges.length;
    const phaseText = activeMerge.size || nodes.some(n => n.phase === 'merge' && activeNodes.has(n.id))
      ? '合并阶段: 每次只合并两个已经有序的小段'
      : '分解阶段: 只负责切半, 暂时不排序';
    const noteW = this.height < 460 ? 196 : 246;
    const noteH = 62;
    const noteX = this.height < 460 ? 22 : Math.min(this.width - noteW - 22, left + drawW - noteW);
    const noteY = 72;
    ctx.fillStyle = 'rgba(21,25,32,0.84)';
    ctx.strokeStyle = 'rgba(73,164,238,0.28)';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.roundRect(noteX, noteY, noteW, noteH, 8);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = VIZ_COLORS.text;
    ctx.font = `bold ${this.height < 460 ? 11 : 13}px -apple-system, "PingFang SC", sans-serif`;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText(phaseText, noteX + 14, noteY + 12);
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = `${this.height < 460 ? 10 : 12}px -apple-system, "PingFang SC", sans-serif`;
    this._fill_text_fit(
      ctx,
      `分解边 ${splitCount} 条 · 合并边 ${mergeCount} 条`,
      noteX + 14,
      noteY + 37,
      noteW - 28,
      size => `${size}px -apple-system, "PingFang SC", sans-serif`,
      this.height < 460 ? 10 : 12,
      8,
      'left',
    );
    ctx.restore();
  }

  _draw_skip_list(ctx, concept) {
    const nodes = Array.isArray(concept.nodes) ? concept.nodes : [];
    const edges = Array.isArray(concept.edges) ? concept.edges : [];
    const activeEdges = new Set((concept.activePath || []).map(e => `${e[0]}>${e[1]}`));
    const activeNodes = new Set(concept.activeNodes || []);
    const updateNodes = new Set(concept.updateNodes || []);
    this._draw_title(ctx, concept.title || '跳表', '多层索引: 向右跳, 超过目标就向下');

    const levels = [...new Set(nodes.map(n => n.level))].sort((a, b) => b - a);
    const maxLevel = Math.max(...levels, 0);
    const drawW = Math.min(this.width - 120, 720);
    const rowGap = Math.min(78, Math.max(58, (this.height - 150) / Math.max(1, levels.length - 1)));
    const top = Math.max(84, this.height / 2 - rowGap * (levels.length - 1) / 2);
    const left = (this.width - drawW) / 2;
    const pos = new Map(nodes.map(n => [n.id, {
      x: left + n.x * drawW,
      y: top + (maxLevel - n.level) * rowGap,
    }]));

    ctx.save();
    levels.forEach(level => {
      const y = top + (maxLevel - level) * rowGap;
      ctx.strokeStyle = 'rgba(148,163,184,0.12)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(left + 12, y);
      ctx.lineTo(left + drawW - 12, y);
      ctx.stroke();
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillText(`L${level + 1}`, left - 14, y);
    });

    edges.forEach(([a, b]) => {
      const from = pos.get(a);
      const to = pos.get(b);
      if (!from || !to) return;
      const active = activeEdges.has(`${a}>${b}`);
      const vertical = Math.abs(from.x - to.x) < 3;
      if (vertical) {
        ctx.strokeStyle = active ? 'rgba(251,191,36,0.90)' : 'rgba(148,163,184,0.28)';
        ctx.lineWidth = active ? 3 : 1.8;
        ctx.setLineDash([5, 4]);
        ctx.beginPath();
        ctx.moveTo(from.x, from.y + 18);
        ctx.lineTo(to.x, to.y - 18);
        ctx.stroke();
        ctx.setLineDash([]);
      } else {
        this._draw_arrow(
          ctx,
          from.x + 24,
          from.y,
          to.x - 24,
          to.y,
          active ? 'rgba(251,191,36,0.92)' : 'rgba(73,164,238,0.36)',
          active ? 'rgba(251,191,36,0.95)' : 'rgba(73,164,238,0.48)',
          active ? 3.2 : 2
        );
      }
    });

    nodes.forEach(node => {
      const p = pos.get(node.id);
      if (!p) return;
      const active = activeNodes.has(node.id);
      const update = updateNodes.has(node.id);
      const isHead = String(node.value) === 'HEAD';
      const isNew = !!node.new;
      const w = isHead ? 58 : 42;
      const h = 34;
      ctx.fillStyle = isNew ? 'rgba(34,197,94,0.24)' : update ? 'rgba(168,85,247,0.25)' : active ? 'rgba(251,191,36,0.24)' : isHead ? 'rgba(71,85,105,0.74)' : 'rgba(37,99,235,0.80)';
      ctx.strokeStyle = isNew ? 'rgba(34,197,94,0.92)' : update ? 'rgba(216,180,254,0.88)' : active ? 'rgba(251,191,36,0.92)' : 'rgba(255,255,255,0.22)';
      ctx.lineWidth = active || update || isNew ? 2.5 : 1.5;
      ctx.beginPath();
      ctx.roundRect(p.x - w / 2, p.y - h / 2, w, h, 7);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = `bold ${isHead ? 11 : 15}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(String(node.value), p.x, p.y + 1);
    });

    const noteW = 230;
    const noteH = 92;
    const noteX = Math.min(this.width - noteW - 22, left + drawW - noteW);
    const noteY = 76;
    ctx.fillStyle = 'rgba(21,25,32,0.84)';
    ctx.strokeStyle = 'rgba(73,164,238,0.28)';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.roundRect(noteX, noteY, noteW, noteH, 8);
    ctx.fill();
    ctx.stroke();
    const rows = [
      ['目标', concept.target ?? '-'],
      ['状态', concept.levelNote || '-'],
      ['紫色', 'update 前驱'],
    ];
    rows.forEach(([label, value], idx) => {
      const y = noteY + 14 + idx * 24;
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '12px -apple-system, "PingFang SC", sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(label, noteX + 14, y);
      ctx.fillStyle = idx === 2 ? '#d8b4fe' : VIZ_COLORS.text;
      ctx.font = 'bold 12px "JetBrains Mono", monospace';
      ctx.fillText(String(value), noteX + 64, y);
    });

    this._draw_caption(ctx, '跳表的关键不是跳过数据, 而是用上层索引快速定位底层位置');
    ctx.restore();
  }

  _draw_recursion_tree(ctx, concept) {
    const nodes = Array.isArray(concept.nodes) ? concept.nodes : [];
    const edges = Array.isArray(concept.edges) ? concept.edges : [];
    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    const active = new Set(concept.active || []);
    const memo = new Set(concept.memo || []);
    this._draw_title(ctx, concept.title || '递归树', concept.marker === 'memo' || concept.marker === 'hit' ? '重复子问题被缓存, 再遇到就直接复用' : '递归会把大问题拆成小问题');

    const compact = this.width < 620;
    const drawW = compact ? this.width - 64 : Math.min(this.width * 0.66, 650);
    const drawH = Math.max(150, this.height - (compact ? 180 : 150));
    const sideW = compact ? 0 : 180;
    const gap = compact ? 0 : 34;
    const totalW = drawW + gap + sideW;
    const left = Math.max(36, (this.width - totalW) / 2);
    const top = Math.max(72, (this.height - drawH) / 2);

    ctx.save();
    edges.forEach(([a, b]) => {
      const from = nodeMap.get(a);
      const to = nodeMap.get(b);
      if (!from || !to) return;
      ctx.strokeStyle = 'rgba(148,163,184,0.38)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(left + from.x * drawW, top + from.y * drawH);
      ctx.lineTo(left + to.x * drawW, top + to.y * drawH);
      ctx.stroke();
    });

    nodes.forEach(node => {
      const x = left + node.x * drawW;
      const y = top + node.y * drawH;
      const isActive = active.has(node.id);
      const key = String(node.label).replace(/[^0-9]/g, '');
      const cached = memo.has(key);
      ctx.fillStyle = cached ? VIZ_COLORS.barSorted : isActive ? VIZ_COLORS.barActive : VIZ_COLORS.barDefault;
      if (concept.marker === 'repeat' && isActive) ctx.fillStyle = VIZ_COLORS.barCompare;
      if (concept.marker === 'hit' && isActive) ctx.fillStyle = '#22c55e';
      ctx.strokeStyle = 'rgba(255,255,255,0.26)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      const nodeW = compact ? 64 : 84;
      const nodeH = compact ? 36 : 42;
      ctx.roundRect(x - nodeW / 2, y - nodeH / 2, nodeW, nodeH, 9);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = `bold ${compact ? 10 : 13}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(node.label, x, y);
    });

    if (!compact) {
      const sideX = left + drawW + gap;
      ctx.fillStyle = VIZ_COLORS.text;
      ctx.font = 'bold 14px -apple-system, "PingFang SC", sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.fillText('观察重点', sideX, top + 4);
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
      const tips = concept.marker === 'repeat'
        ? ['同名节点重复出现', '暴力递归会反复计算']
        : concept.marker === 'hit'
          ? ['再次遇到缓存项', '直接返回, 不再展开']
          : concept.marker === 'done'
            ? ['小问题答案向上汇总', '根节点得到最终结果']
            : ['每条边代表一次递归调用', '树越宽, 重复越多'];
      tips.forEach((tip, idx) => ctx.fillText(tip, sideX, top + 34 + idx * 24));

      if (memo.size) {
        ctx.fillStyle = 'rgba(21,25,32,0.84)';
        ctx.strokeStyle = 'rgba(16,185,129,0.40)';
        ctx.beginPath();
        ctx.roundRect(sideX, top + 98, 156, 38, 7);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = '#bbf7d0';
        ctx.font = '12px "JetBrains Mono", monospace';
        ctx.fillText(`memo: ${Array.from(memo).join(', ')}`, sideX + 12, top + 111);
      }
    }

    this._draw_caption(ctx, concept.marker === 'repeat' ? '重复子问题是暴力递归变慢的根源' : concept.marker === 'hit' ? '记忆化搜索把重复计算变成查表' : '看递归树的形状, 比逐行走几千步更容易理解复杂度');
    ctx.restore();
  }

  _draw_monte_carlo(ctx, concept) {
    const points = Array.isArray(concept.points) ? concept.points : [];
    this._draw_title(ctx, '蒙特卡洛估算 π', '圆面积 / 正方形面积 ≈ 落入圆内的点数比例');

    const size = Math.min(this.height - 118, this.width * 0.42, 330);
    const sideW = 210;
    const gap = 54;
    const totalW = size + gap + sideW;
    const x0 = Math.max(42, (this.width - totalW) / 2);
    const y0 = Math.max(76, (this.height - size) / 2);
    ctx.save();
    ctx.fillStyle = 'rgba(255,255,255,0.04)';
    ctx.strokeStyle = 'rgba(255,255,255,0.28)';
    ctx.lineWidth = 2;
    ctx.fillRect(x0, y0, size, size);
    ctx.strokeRect(x0, y0, size, size);

    ctx.strokeStyle = 'rgba(73,164,238,0.55)';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(x0, y0 + size);
    ctx.bezierCurveTo(x0, y0 + size * 0.448, x0 + size * 0.448, y0, x0 + size, y0);
    ctx.stroke();

    points.forEach(([x, y, inside]) => {
      const px = x0 + x * size;
      const py = y0 + size - y * size;
      ctx.fillStyle = inside ? VIZ_COLORS.barSorted : VIZ_COLORS.barSwap;
      ctx.strokeStyle = 'rgba(255,255,255,0.25)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(px, py, 4.8, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    });

    const sideX = x0 + size + gap;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillStyle = VIZ_COLORS.text;
    ctx.font = 'bold 14px -apple-system, "PingFang SC", sans-serif';
    ctx.fillText('估算过程', sideX, y0 + 8);
    const stats = [
      `样本数: ${concept.samples || 0}`,
      `圆内点: ${concept.inside || 0}`,
      `π ≈ 4 × ${concept.inside || 0} / ${concept.samples || 1}`,
      `当前估计: ${concept.pi || 0}`,
    ];
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px "JetBrains Mono", monospace';
    stats.forEach((text, idx) => ctx.fillText(text, sideX, y0 + 40 + idx * 28));

    this._draw_caption(ctx, '随机点越多, 面积比例越稳定, π 的估计也越接近真实值');
    ctx.restore();
  }

  _draw_sum_demo(ctx, concept) {
    const n = concept.n || 6;
    const progress = concept.progress || 0;
    const mode = concept.mode || 'loop';
    this._draw_title(ctx, mode === 'formula' ? '高斯公式求和' : '循环累加', mode === 'formula' ? '首尾配对, 一次看清结构' : '一个一个加, 规模越大步骤越多');

    const cx = this.width / 2;
    const compactHeight = this.height < 460;
    const block = Math.min(
      compactHeight ? 22 : 32,
      Math.floor((this.width - 180) / (n * 1.5)),
    );
    const gap = 5;
    const maxStackH = n * (block + 2);
    const baseY = Math.min(this.height - (mode === 'formula' && compactHeight ? 150 : 88), this.height / 2 + maxStackH / 2 - 8);
    const totalW = n * block + (n - 1) * gap;
    const startX = cx - totalW / 2;

    ctx.save();
    for (let i = 1; i <= n; i++) {
      const x = startX + (i - 1) * (block + gap);
      for (let h = 0; h < i; h++) {
        const y = baseY - (h + 1) * (block + 2);
        const active = mode === 'loop' ? i <= progress : progress > 0;
        const paired = mode === 'formula' && progress >= Math.min(i, n + 1 - i);
        ctx.fillStyle = active || paired ? VIZ_COLORS.barSorted : 'rgba(73,164,238,0.24)';
        if (mode === 'loop' && i === progress) ctx.fillStyle = VIZ_COLORS.barCompare;
        if (mode === 'formula' && paired) ctx.fillStyle = i <= n / 2 ? VIZ_COLORS.barActive : VIZ_COLORS.barCompare;
        ctx.strokeStyle = 'rgba(255,255,255,0.13)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(x, y, block, block, 5);
        ctx.fill();
        ctx.stroke();
      }
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(String(i), x + block / 2, baseY + 10);
    }

    if (mode === 'formula') {
      for (let i = 1; i <= Math.min(progress, Math.floor(n / 2)); i++) {
        const leftX = startX + (i - 1) * (block + gap) + block / 2;
        const rightX = startX + (n - i) * (block + gap) + block / 2;
        const y = baseY + 36 + i * 12;
        ctx.strokeStyle = 'rgba(251,191,36,0.72)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(leftX, y);
        ctx.quadraticCurveTo((leftX + rightX) / 2, y + 22, rightX, y);
        ctx.stroke();
        ctx.fillStyle = VIZ_COLORS.pointerText;
        ctx.font = '12px "JetBrains Mono", monospace';
        ctx.fillText(`${i}+${n + 1 - i}=${n + 1}`, (leftX + rightX) / 2, y + 23);
      }
    }

    if (!(mode === 'formula' && compactHeight)) {
      const boxW = 190;
      const boxX = cx - boxW / 2;
      const boxY = 82;
      ctx.fillStyle = 'rgba(21,25,32,0.84)';
      ctx.strokeStyle = 'rgba(73,164,238,0.32)';
      ctx.beginPath();
      ctx.roundRect(boxX, boxY, boxW, 54, 8);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = VIZ_COLORS.text;
      ctx.font = 'bold 18px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(mode === 'formula' ? '6 × 7 ÷ 2 = 21' : `sum = ${concept.sum || 0}`, cx, boxY + 27);
    }

    this._draw_caption(ctx, mode === 'formula' ? '公式法看见了数列结构: 3 对, 每对都是 7' : '循环法每次只前进一步: 加到哪里, sum 就变到哪里');
    ctx.restore();
  }

  _draw_array_process(ctx, concept) {
    const title = concept.title || '数组过程';
    const modeText = {
      linear_search: '从左到右逐个检查, 命中就停',
      bubble: '相邻比较, 大数一轮轮沉到右侧',
      bubble_opt: '一整轮没有交换, 说明已经有序',
      selection: '每轮找出未排序区最小值, 放到左侧',
      shell: '先按大间隔粗调, 再按小间隔细调',
      heap: '堆顶最大值不断换到右侧已排序区',
      quick: '选 pivot 分区, 让基准值一次次归位',
      quick_engineered: '三数取中、尾递归优化、堆排兜底和插入排序收尾',
      reverse: '左右指针向中间交换, 额外变量数量不变',
      binary: '有序数组中每次排除一半',
      binary_first: '命中后继续往左找第一个',
      binary_last: '命中后继续往右找最后一个',
      rotated: '先判断哪一半有序, 再保留目标所在半边',
      interpolation: '按数值比例估算目标位置',
      fibonacci: '用斐波那契比例切分搜索区间',
    }[concept.mode] || '观察数组中元素、指针和状态的变化';
    this._draw_title(ctx, title, modeText);

    const values = Array.isArray(concept.values) ? concept.values : [];
    const compare = new Set(Array.isArray(concept.compare) ? concept.compare : []);
    const visited = new Set(Array.isArray(concept.visited) ? concept.visited : []);
    const sorted = new Set(Array.isArray(concept.sorted) ? concept.sorted : []);
    const current = concept.current;
    const minIdx = concept.minIdx;
    const pivotIdx = concept.pivotIdx;
    const target = concept.target;
    const leftZone = new Set(Array.isArray(concept.leftZone) ? concept.leftZone : []);
    const activeRange = Array.isArray(concept.range) ? concept.range : [];

    const compact = this.width < 560;
    const gap = compact ? Math.max(2, Math.min(6, Math.floor(42 / Math.max(values.length, 1)))) : 8;
    const availableW = Math.max(1, this.width - (compact ? 34 : 150));
    const minCell = compact ? 20 : 30;
    const cell = Math.min(58, Math.max(
      minCell,
      (availableW - Math.max(0, values.length - 1) * gap) / Math.max(values.length, 1),
    ));
    const totalW = values.length * cell + Math.max(0, values.length - 1) * gap;
    const x0 = (this.width - totalW) / 2;
    const hasTarget = target !== undefined && target !== null;
    const y = Math.max(hasTarget ? 146 : 120, this.height * 0.34);

    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    if (hasTarget) {
      const label = `target = ${target}`;
      ctx.font = '700 14px "JetBrains Mono", monospace';
      const tw = ctx.measureText(label).width + 28;
      const bx = (this.width - tw) / 2;
      ctx.fillStyle = 'rgba(245,158,11,0.14)';
      ctx.strokeStyle = 'rgba(245,158,11,0.5)';
      this._round_rect(ctx, bx, y - 74, tw, 34, 17);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fde68a';
      ctx.fillText(label, this.width / 2, y - 57);
    }

    if (activeRange.length === 2) {
      const start = Math.max(0, activeRange[0]);
      const end = Math.min(values.length - 1, activeRange[1]);
      if (start <= end) {
        const bandX = x0 + start * (cell + gap) - 6;
        const bandW = (end - start + 1) * cell + (end - start) * gap + 12;
        ctx.fillStyle = 'rgba(96,165,250,0.10)';
        ctx.strokeStyle = 'rgba(96,165,250,0.34)';
        ctx.lineWidth = 1.2;
        this._round_rect(ctx, bandX, y - 18, bandW, cell + 36, 14);
        ctx.fill();
        ctx.stroke();
      }
    }

    values.forEach((value, idx) => {
      const x = x0 + idx * (cell + gap);
      const isCurrent = idx === current;
      const isMin = idx === minIdx;
      const isPivot = idx === pivotIdx;
      const isCompare = compare.has(idx);
      const isVisited = visited.has(idx);
      const isSorted = sorted.has(idx);
      const isLeftZone = leftZone.has(idx);
      const isFound = concept.found && idx === current;

      let fill = 'rgba(30,41,59,0.94)';
      let stroke = 'rgba(148,163,184,0.36)';
      if (isLeftZone) {
        fill = 'rgba(34,197,94,0.20)';
        stroke = 'rgba(74,222,128,0.54)';
      }
      if (isVisited) {
        fill = 'rgba(59,130,246,0.20)';
        stroke = 'rgba(96,165,250,0.48)';
      }
      if (isCompare || isCurrent) {
        fill = 'rgba(245,158,11,0.34)';
        stroke = '#fbbf24';
      }
      if (isMin) {
        fill = 'rgba(168,85,247,0.30)';
        stroke = '#c084fc';
      }
      if (isPivot) {
        fill = 'rgba(244,63,94,0.32)';
        stroke = '#fb7185';
      }
      if (isSorted || isFound) {
        fill = 'rgba(16,185,129,0.34)';
        stroke = '#34d399';
      }

      ctx.fillStyle = fill;
      ctx.strokeStyle = stroke;
      ctx.lineWidth = (isCurrent || isCompare || isMin || isFound || isPivot) ? 2.5 : 1.4;
      this._round_rect(ctx, x, y, cell, cell, 10);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = '#f8fafc';
      this._fill_text_fit(ctx, value, x + cell / 2, y + cell / 2 + 1, cell - 8, size => `700 ${size}px "JetBrains Mono", monospace`, 20, 12);

      ctx.fillStyle = '#94a3b8';
      ctx.font = '11px "JetBrains Mono", monospace';
      ctx.fillText(String(idx), x + cell / 2, y + cell + 18);

      if (isCurrent) this._draw_small_tag(ctx, x + cell / 2, y - 18, 'i', '#fbbf24');
      if (isMin) this._draw_small_tag(ctx, x + cell / 2, y + cell + 42, 'min', '#c084fc');
      if (isPivot) this._draw_small_tag(ctx, x + cell / 2, y - 42, 'pivot', '#fb7185');
      if (isLeftZone && !isSorted) this._draw_small_tag(ctx, x + cell / 2, y + cell + 42, '< pivot', '#4ade80');
      if ((isSorted || isFound) && !isPivot) this._draw_small_tag(ctx, x + cell / 2, y - 42, isFound ? '命中' : '已定', '#34d399');
    });

    if (compare.size === 2 && concept.mode !== 'quick' && concept.mode !== 'quick_engineered') {
      const pts = Array.from(compare).sort((a, b) => a - b);
      const ax = x0 + pts[0] * (cell + gap) + cell / 2;
      const bx = x0 + pts[1] * (cell + gap) + cell / 2;
      const ay = y + cell + 58;
      ctx.strokeStyle = 'rgba(251,191,36,0.72)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.quadraticCurveTo((ax + bx) / 2, ay + 24, bx, ay);
      ctx.stroke();
    }

    const legend = [
      ['比较/当前', '#fbbf24'],
      ['已检查', '#60a5fa'],
      ['已确定', '#34d399'],
    ];
    if (concept.mode === 'selection') legend.splice(2, 0, ['当前最小', '#c084fc']);
    if (concept.mode === 'quick' || concept.mode === 'quick_engineered') {
      legend.splice(1, 0, ['pivot', '#fb7185']);
      legend.splice(2, 0, ['小于区', '#4ade80']);
    }
    if (activeRange.length === 2) legend.push(['当前区间', '#93c5fd']);
    const legendFontSize = compact ? 10 : 12;
    const legendGap = compact ? 10 : 22;
    ctx.font = `${legendFontSize}px "Inter", sans-serif`;
    const legendWidths = legend.map(([label]) => ctx.measureText(label).width + 18);
    const legendRows = [];
    let currentRow = [];
    let currentWidth = 0;
    legend.forEach((item, idx) => {
      const nextWidth = currentWidth + (currentRow.length ? legendGap : 0) + legendWidths[idx];
      if (currentRow.length && nextWidth > this.width - 44) {
        legendRows.push(currentRow);
        currentRow = [];
        currentWidth = 0;
      }
      currentRow.push({ item, width: legendWidths[idx] });
      currentWidth += (currentRow.length > 1 ? legendGap : 0) + legendWidths[idx];
    });
    if (currentRow.length) legendRows.push(currentRow);

    const legendStartY = y + cell + (compare.size === 2 ? 104 : 82);
    legendRows.forEach((row, rowIdx) => {
      const rowWidth = row.reduce((sum, entry) => sum + entry.width, 0) + Math.max(0, row.length - 1) * legendGap;
      let lx = (this.width - rowWidth) / 2;
      const ly = legendStartY + rowIdx * (legendFontSize + 8);
      ctx.textAlign = 'left';
      row.forEach(({ item: [label, color], width: itemWidth }) => {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(lx + 5, ly - 3, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#cbd5e1';
        ctx.font = `${legendFontSize}px "Inter", sans-serif`;
        ctx.fillText(label, lx + 13, ly);
        lx += itemWidth + legendGap;
      });
    });

    this._draw_caption(ctx, concept.phase || '');
    ctx.restore();
  }

  _draw_small_tag(ctx, cx, cy, text, color) {
    ctx.save();
    ctx.font = '700 12px "Inter", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const w = Math.max(30, ctx.measureText(text).width + 14);
    ctx.fillStyle = 'rgba(15,23,42,0.88)';
    ctx.strokeStyle = color;
    this._round_rect(ctx, cx - w / 2, cy - 12, w, 24, 12);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = color;
    ctx.fillText(text, cx, cy + 1);
    ctx.restore();
  }

  _draw_karatsuba(ctx, concept) {
    this._draw_title(ctx, concept.title || 'Karatsuba 快速乘法', '把 4 次交叉乘法变成 3 次乘法');
    const active = new Set(Array.isArray(concept.active) ? concept.active : []);
    const values = concept.values || {};
    const cx = this.width / 2;
    const topY = Math.max(108, this.height * 0.14);
    const naturalBottom = topY + 434;
    const heightScale = (this.height - 16 - topY) / Math.max(1, naturalBottom - topY);
    const widthScale = (this.width - 24) / 660;
    const contentScale = Math.max(0.48, Math.min(1, heightScale, widthScale));

    ctx.save();
    ctx.translate(cx, topY);
    ctx.scale(contentScale, contentScale);
    ctx.translate(-cx, -topY);

    if (concept.phase) {
      ctx.save();
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.font = '600 13px "Inter", sans-serif';
      const maxPhaseW = Math.min(660, this.width / contentScale - 120);
      const phaseW = Math.min(maxPhaseW, Math.max(210, ctx.measureText(concept.phase).width + 28));
      ctx.fillStyle = 'rgba(15,23,42,0.72)';
      ctx.strokeStyle = 'rgba(96,165,250,0.32)';
      this._round_rect(ctx, cx - phaseW / 2, topY - 42, phaseW, 30, 15);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#cbd5e1';
      this._fill_text_fit(ctx, concept.phase, cx, topY - 27, phaseW - 24, size => `600 ${size}px "Inter", sans-serif`, 13, 10);
      ctx.restore();
    }

    const draw_box = (x, y, w, h, label, value, color, isActive = false) => {
      ctx.save();
      ctx.fillStyle = isActive ? `${color}44` : 'rgba(30,41,59,0.86)';
      ctx.strokeStyle = isActive ? color : 'rgba(148,163,184,0.34)';
      ctx.lineWidth = isActive ? 2.5 : 1.4;
      this._round_rect(ctx, x, y, w, h, 10);
      ctx.fill();
      ctx.stroke();
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#cbd5e1';
      this._fill_text_fit(ctx, label, x + w / 2, y + 18, w - 16, size => `600 ${size}px "Inter", sans-serif`, 12, 9);
      ctx.fillStyle = '#f8fafc';
      this._fill_text_fit(ctx, value, x + w / 2, y + h / 2 + 10, w - 16, size => `800 ${size}px "JetBrains Mono", monospace`, 22, 13);
      ctx.restore();
    };

    draw_box(cx - 190, topY, 150, 72, 'x', concept.x || 1234, '#60a5fa', active.has('splitX'));
    draw_box(cx + 40, topY, 150, 72, 'y', concept.y || 5678, '#f59e0b', active.has('splitY'));

    const splitY = topY + 106;
    draw_box(cx - 260, splitY, 110, 62, 'a 高位', concept.a || 12, '#38bdf8', active.has('splitX'));
    draw_box(cx - 130, splitY, 110, 62, 'b 低位', concept.b || 34, '#38bdf8', active.has('splitX'));
    draw_box(cx + 20, splitY, 110, 62, 'c 高位', concept.c || 56, '#fbbf24', active.has('splitY'));
    draw_box(cx + 150, splitY, 110, 62, 'd 低位', concept.d || 78, '#fbbf24', active.has('splitY'));

    ctx.save();
    ctx.strokeStyle = 'rgba(148,163,184,0.28)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx - 115, topY + 72);
    ctx.lineTo(cx - 205, splitY);
    ctx.moveTo(cx - 115, topY + 72);
    ctx.lineTo(cx - 75, splitY);
    ctx.moveTo(cx + 115, topY + 72);
    ctx.lineTo(cx + 75, splitY);
    ctx.moveTo(cx + 115, topY + 72);
    ctx.lineTo(cx + 205, splitY);
    ctx.stroke();
    ctx.restore();

    const cardY = splitY + 100;
    const cardW = 178;
    const cards = [
      ['ac', '12 × 56', values.ac ?? '?', '#34d399'],
      ['bd', '34 × 78', values.bd ?? '?', '#22c55e'],
      ['sum', '46 × 134', values.sum ?? '?', '#a78bfa'],
    ];
    cards.forEach(([key, label, value, color], idx) => {
      const x = cx - cardW * 1.5 - 18 + idx * (cardW + 18);
      draw_box(x, cardY, cardW, 78, label, value, color, active.has(key));
    });

    const formulaY = cardY + 116;
    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = '700 17px "JetBrains Mono", monospace';
    const middleText = values.middle === undefined ? 'ad+bc = ?' : `ad+bc = ${values.sum} - ${values.ac} - ${values.bd} = ${values.middle}`;
    ctx.fillStyle = active.has('middle') ? 'rgba(251,191,36,0.18)' : 'rgba(15,23,42,0.58)';
    ctx.strokeStyle = active.has('middle') ? '#fbbf24' : 'rgba(148,163,184,0.24)';
    const wideBoxW = Math.min(530, this.width / contentScale - 92);
    this._round_rect(ctx, cx - wideBoxW / 2, formulaY, wideBoxW, 46, 14);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = active.has('middle') ? '#fde68a' : '#cbd5e1';
    this._fill_text_fit(ctx, middleText, cx, formulaY + 23, wideBoxW - 26, size => `700 ${size}px "JetBrains Mono", monospace`, 17, 11);

    const resultY = formulaY + 62;
    const result = values.result === undefined
      ? '672×10000 + 2840×100 + 2652'
      : `结果 = ${values.result}`;
    ctx.fillStyle = active.has('result') ? 'rgba(16,185,129,0.22)' : 'rgba(15,23,42,0.58)';
    ctx.strokeStyle = active.has('result') ? '#34d399' : 'rgba(148,163,184,0.24)';
    this._round_rect(ctx, cx - wideBoxW / 2, resultY, wideBoxW, 50, 15);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = active.has('result') ? '#bbf7d0' : '#e2e8f0';
    this._fill_text_fit(ctx, result, cx, resultY + 25, wideBoxW - 28, size => `800 ${size}px "JetBrains Mono", monospace`, 18, 11);
    ctx.restore();
    ctx.restore();

  }

  _draw_complexity_tree(ctx, concept) {
    this._draw_title(ctx, concept.title || '复杂度对比', concept.shape === 'skew' ? '最坏情况: 递归树退化成链' : '平均情况: 递归树接近平衡');
    const cx = this.width / 2;
    const compact = this.height < 460 || this.width < 620;
    const top = compact ? 84 : Math.max(110, this.height * 0.22);
    const treeScale = compact ? Math.max(0.62, Math.min(1, (this.height - top - 54) / 330, (this.width - 40) / 520)) : 1;
    const activeDepth = concept.depth || 1;
    const draw_node = (x, y, label, active) => {
      ctx.fillStyle = active ? 'rgba(251,191,36,0.28)' : 'rgba(30,41,59,0.92)';
      ctx.strokeStyle = active ? '#fbbf24' : 'rgba(148,163,184,0.38)';
      ctx.lineWidth = active ? 2.4 : 1.4;
      this._round_rect(ctx, x - 34, y - 20, 68, 40, 18);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#f8fafc';
      ctx.font = '700 13px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, x, y);
    };

    ctx.save();
    ctx.translate(cx, top);
    ctx.scale(treeScale, treeScale);
    ctx.translate(-cx, -top);
    ctx.strokeStyle = 'rgba(148,163,184,0.32)';
    ctx.lineWidth = 2;
    if (concept.shape === 'skew') {
      const pts = [[cx - 170, top], [cx - 82, top + 76], [cx + 4, top + 152], [cx + 92, top + 228]];
      pts.forEach((p, i) => {
        if (i > 0) {
          ctx.beginPath();
          ctx.moveTo(pts[i - 1][0], pts[i - 1][1] + 20);
          ctx.lineTo(p[0], p[1] - 20);
          ctx.stroke();
        }
        draw_node(p[0], p[1], i === 0 ? 'n' : `n-${i}`, i < activeDepth + 1);
      });
      ctx.fillStyle = '#fecaca';
      ctx.font = '800 30px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText('O(n²)', cx, top + 310);
    } else {
      const levels = [
        [[cx, top, 'n']],
        [[cx - 125, top + 86, 'n/2'], [cx + 125, top + 86, 'n/2']],
        [[cx - 190, top + 172, 'n/4'], [cx - 62, top + 172, 'n/4'], [cx + 62, top + 172, 'n/4'], [cx + 190, top + 172, 'n/4']],
      ];
      for (let l = 1; l < levels.length; l++) {
        levels[l].forEach((p, idx) => {
          const parent = levels[l - 1][Math.floor(idx / 2)];
          ctx.beginPath();
          ctx.moveTo(parent[0], parent[1] + 20);
          ctx.lineTo(p[0], p[1] - 20);
          ctx.stroke();
        });
      }
      levels.forEach((level, l) => level.forEach((p) => draw_node(p[0], p[1], p[2], l < activeDepth)));
      ctx.fillStyle = '#bbf7d0';
      ctx.font = '800 30px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText('O(n log n)', cx, top + 270);
    }
    ctx.restore();
    this._draw_caption(ctx, concept.phase || '');
  }

  _draw_complexity_ladder(ctx, concept) {
    this._draw_title(ctx, concept.title || '复杂度阶层全景图', '同样的数据规模, 不同复杂度会拉开完全不同的距离');
    const levels = Array.isArray(concept.levels) ? concept.levels : [];
    const active = Number.isInteger(concept.active) ? concept.active : 0;
    const compact = this.height < 480 || this.width < 620;
    const cx = this.width / 2;
    const panelW = Math.min(this.width - (compact ? 36 : 90), 840);
    const x0 = cx - panelW / 2;
    const top = compact ? 74 : Math.max(98, this.height * 0.19);
    const rowH = compact
      ? Math.max(23, Math.min(34, (this.height - top - 50) / Math.max(1, levels.length)))
      : Math.min(52, Math.max(42, (this.height - top - 112) / Math.max(1, levels.length)));
    const colors = ['#34d399', '#38bdf8', '#60a5fa', '#a78bfa', '#f59e0b', '#fb7185', '#ef4444'];

    ctx.save();
    levels.forEach((level, i) => {
      const y = top + i * rowH;
      const isActive = i === active;
      const color = colors[i % colors.length];
      const weight = Math.max(0.12, Math.min(1, level.weight || (i + 1) / levels.length));
      const barW = panelW * (0.24 + weight * 0.42);

      ctx.fillStyle = isActive ? 'rgba(15,23,42,0.84)' : 'rgba(15,23,42,0.46)';
      ctx.strokeStyle = isActive ? color : 'rgba(148,163,184,0.18)';
      ctx.lineWidth = isActive ? 2 : 1;
      this._round_rect(ctx, x0, y, panelW, Math.max(18, rowH - 5), 10);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = isActive ? `${color}55` : 'rgba(71,85,105,0.35)';
      this._round_rect(ctx, x0 + (compact ? 112 : 142), y + rowH * 0.34, compact ? Math.min(barW, panelW - 226) : barW, Math.max(6, rowH * 0.24), 8);
      ctx.fill();

      ctx.fillStyle = isActive ? '#f8fafc' : '#cbd5e1';
      ctx.font = `${compact ? '800 15px' : '800 17px'} "JetBrains Mono", monospace`;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(level.order || '', x0 + 18, y + rowH / 2 - (compact ? 0 : 4));

      if (!compact) {
        ctx.font = '700 13px "Inter", sans-serif';
        ctx.fillStyle = isActive ? '#e2e8f0' : '#94a3b8';
        ctx.fillText(level.name || '', x0 + 18, y + rowH / 2 + 15);
      }

      if (!compact) {
        ctx.font = '700 13px "Inter", sans-serif';
        ctx.fillStyle = isActive ? '#fef3c7' : '#cbd5e1';
        ctx.fillText(level.example || '', x0 + 158, y + rowH / 2);
      }

      ctx.font = `${compact ? '700 11px' : '700 12px'} "JetBrains Mono", monospace`;
      ctx.textAlign = 'right';
      ctx.fillStyle = isActive ? '#f8fafc' : '#94a3b8';
      ctx.fillText(`n=1000: ${level.n1000 || ''}`, x0 + panelW - 18, y + rowH / 2 - (compact ? 0 : 4));
      if (!compact) {
        ctx.fillStyle = isActive ? color : 'rgba(148,163,184,0.72)';
        ctx.fillText(level.n100 || '', x0 + panelW - 18, y + rowH / 2 + 15);
      }
    });
    ctx.restore();
    this._draw_caption(ctx, concept.phase || '');
  }

  _draw_space_compare(ctx, concept) {
    this._draw_title(ctx, concept.title || '空间复杂度', '额外空间会不会跟着 n 一起变大');
    const cx = this.width / 2;
    const compact = this.width < 620 || this.height < 460;
    const top = compact ? 104 : Math.max(120, this.height * 0.24);
    const draw_row = (label, items, y, color) => {
      const gap = compact ? 4 : 7;
      const cell = Math.max(compact ? 24 : 30, Math.min(
        38,
        (this.width - (compact ? 44 : 150) - Math.max(0, items.length - 1) * gap) / Math.max(items.length, 1),
      ));
      const totalW = Math.max(items.length, 1) * cell + Math.max(0, items.length - 1) * gap;
      const x0 = cx - totalW / 2;
      ctx.fillStyle = '#cbd5e1';
      ctx.font = `700 ${compact ? 12 : 14}px "Inter", sans-serif`;
      ctx.textAlign = compact ? 'center' : 'right';
      ctx.fillText(label, compact ? cx : x0 - 18, compact ? y - 10 : y + 20);
      if (!items.length) {
        ctx.strokeStyle = 'rgba(148,163,184,0.28)';
        ctx.setLineDash([5, 5]);
        this._round_rect(ctx, cx - 105, y, 210, 38, 9);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = '#94a3b8';
        ctx.textAlign = 'center';
        ctx.fillText('尚未申请临时数组', cx, y + 20);
        return;
      }
      items.forEach((v, i) => {
        const x = x0 + i * (cell + gap);
        ctx.fillStyle = color;
        ctx.strokeStyle = 'rgba(255,255,255,0.22)';
        this._round_rect(ctx, x, y, cell, 38, 8);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = '#f8fafc';
        ctx.font = '700 14px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.fillText(String(v), x + cell / 2, y + 20);
      });
    };
    const rowGap = compact ? 66 : 78;
    draw_row('原数组 arr', concept.array || [], top, 'rgba(59,130,246,0.26)');
    draw_row('临时 L', concept.left || [], top + rowGap, 'rgba(34,197,94,0.28)');
    draw_row('临时 R', concept.right || [], top + rowGap * 2, 'rgba(245,158,11,0.28)');
    ctx.fillStyle = '#fde68a';
    ctx.font = `800 ${compact ? 17 : 24}px "JetBrains Mono", monospace`;
    ctx.textAlign = 'center';
    this._fill_text_fit(
      ctx,
      (concept.left || []).length + (concept.right || []).length ? '额外空间随 n 增长: O(n)' : '准备申请额外空间',
      cx,
      top + rowGap * 2 + 62,
      this.width - 48,
      size => `800 ${size}px "JetBrains Mono", monospace`,
      compact ? 17 : 24,
      11,
    );
    this._draw_caption(ctx, concept.phase || '');
  }

  _draw_dynamic_array(ctx, concept) {
    this._draw_title(ctx, concept.title || '动态数组', '偶尔扩容很贵, 但摊到一串插入里很便宜');
    const items = Array.isArray(concept.items) ? concept.items : [];
    const capacity = concept.capacity || Math.max(2, items.length);
    const cx = this.width / 2;
    const top = Math.max(140, this.height * 0.30);
    const cell = Math.max(20, Math.min(50, (this.width - (this.width < 620 ? 36 : 160)) / capacity));
    const totalW = capacity * cell;
    const x0 = cx - totalW / 2;
    ctx.save();
    for (let i = 0; i < capacity; i++) {
      const x = x0 + i * cell;
      const filled = i < items.length;
      ctx.fillStyle = filled ? 'rgba(59,130,246,0.30)' : 'rgba(15,23,42,0.62)';
      ctx.strokeStyle = filled ? '#60a5fa' : 'rgba(148,163,184,0.28)';
      this._round_rect(ctx, x + 3, top, cell - 6, 48, 8);
      ctx.fill();
      ctx.stroke();
      if (filled) {
        ctx.fillStyle = '#f8fafc';
        ctx.font = '800 16px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(String(items[i]), x + cell / 2, top + 25);
      }
    }
    const barY = top + 78;
    const usedW = totalW * (items.length / capacity);
    ctx.fillStyle = 'rgba(15,23,42,0.72)';
    this._round_rect(ctx, x0, barY, totalW, 16, 8);
    ctx.fill();
    ctx.fillStyle = concept.cost > 1 ? 'rgba(251,191,36,0.85)' : 'rgba(52,211,153,0.85)';
    this._round_rect(ctx, x0, barY, usedW, 16, 8);
    ctx.fill();
    ctx.fillStyle = '#cbd5e1';
    ctx.font = '700 14px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`size=${items.length} / capacity=${capacity}`, cx, barY + 42);
    ctx.fillStyle = concept.cost > 1 ? '#fde68a' : '#bbf7d0';
    ctx.font = '800 26px "JetBrains Mono", monospace';
    ctx.fillText(concept.cost > 1 ? `本次代价 ${concept.cost}: 扩容复制旧元素` : '本次代价 1: 普通插入', cx, barY + 92);
    ctx.restore();
    this._draw_caption(ctx, concept.phase || '');
  }

  _draw_halting(ctx, concept) {
    this._draw_title(ctx, concept.title || '停机问题', '假设万能检测器存在, 然后构造一个反着来的程序');
    const cx = this.width / 2;
    const top = Math.max(118, this.height * 0.22);
    const contentScale = Math.max(0.5, Math.min(1, (this.width - 24) / 600, (this.height - top - 44) / 350));
    const boxes = [
      ['halts(P,P)', '万能检测器', cx - 210, top],
      ['paradox(P)', '唱反调程序', cx + 90, top],
      ['true → 死循环', '你说会停, 我偏不停', cx - 250, top + 138],
      ['false → 立刻停', '你说不停, 我偏停', cx + 130, top + 138],
      ['矛盾', '所以 halts 不存在', cx - 60, top + 278],
    ];
    ctx.save();
    ctx.translate(cx, top);
    ctx.scale(contentScale, contentScale);
    ctx.translate(-cx, -top);
    boxes.forEach(([title, sub, x, y], i) => {
      const active = i <= (concept.index || 0);
      ctx.fillStyle = active ? 'rgba(96,165,250,0.22)' : 'rgba(30,41,59,0.80)';
      ctx.strokeStyle = active ? '#60a5fa' : 'rgba(148,163,184,0.30)';
      ctx.lineWidth = active ? 2.4 : 1.2;
      this._round_rect(ctx, x, y, 180, 72, 12);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = active ? '#f8fafc' : '#94a3b8';
      ctx.font = '800 16px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(title, x + 90, y + 27);
      ctx.font = '600 12px "Inter", sans-serif';
      ctx.fillText(sub, x + 90, y + 51);
    });
    ctx.strokeStyle = 'rgba(251,191,36,0.58)';
    ctx.lineWidth = 2.4;
    ctx.beginPath();
    ctx.moveTo(cx - 30, top + 36);
    ctx.lineTo(cx + 90, top + 36);
    ctx.moveTo(cx + 180, top + 72);
    ctx.lineTo(cx - 160, top + 138);
    ctx.moveTo(cx + 180, top + 72);
    ctx.lineTo(cx + 220, top + 138);
    ctx.moveTo(cx - 160, top + 210);
    ctx.lineTo(cx + 30, top + 278);
    ctx.moveTo(cx + 220, top + 210);
    ctx.lineTo(cx + 110, top + 278);
    ctx.stroke();
    ctx.restore();
    this._draw_caption(ctx, concept.phase || '');
  }

  _draw_answer_search(ctx, concept) {
    this._draw_title(ctx, concept.title || '二分答案', '在答案空间里寻找刚刚好的临界点');
    const cx = this.width / 2;
    const top = Math.max(120, this.height * 0.24);
    const left = concept.left || 0;
    const right = concept.right || 0;
    const capacity = concept.capacity || left;
    const minCap = 10;
    const maxCap = 55;
    const critical = Number.isFinite(concept.critical) ? concept.critical : 15;
    const axisW = Math.min(this.width - (this.width < 620 ? 76 : 180), 620);
    const axisX = cx - axisW / 2;
    const axisY = top + 110;
    const pos = (v) => axisX + ((v - minCap) / (maxCap - minCap)) * axisW;
    const critX = pos(critical);

    ctx.save();
    ctx.fillStyle = 'rgba(248,113,113,0.13)';
    this._round_rect(ctx, axisX, axisY - 22, Math.max(8, critX - axisX), 44, 18);
    ctx.fill();
    ctx.fillStyle = 'rgba(34,197,94,0.13)';
    this._round_rect(ctx, critX, axisY - 22, Math.max(8, axisX + axisW - critX), 44, 18);
    ctx.fill();

    ctx.strokeStyle = 'rgba(148,163,184,0.45)';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(axisX, axisY);
    ctx.lineTo(axisX + axisW, axisY);
    ctx.stroke();

    ctx.fillStyle = 'rgba(96,165,250,0.12)';
    const lx = pos(left);
    const rx = pos(Math.max(left, right));
    this._round_rect(ctx, lx, axisY - 18, Math.max(8, rx - lx), 36, 18);
    ctx.fill();

    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(critX, axisY - 36);
    ctx.lineTo(critX, axisY + 36);
    ctx.stroke();

    ctx.fillStyle = '#fecaca';
    ctx.font = '700 12px "Noto Sans SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('不可行', (axisX + critX) / 2, axisY + 5);
    ctx.fillStyle = '#bbf7d0';
    ctx.fillText('可行', (critX + axisX + axisW) / 2, axisY + 5);
    ctx.fillStyle = '#fde68a';
    ctx.fillText(`临界点 ${critical}`, critX, axisY - 13);

    const markers = [];
    if (left !== minCap) markers.push([minCap, '10']);
    if (Math.max(right, left) !== maxCap) markers.push([maxCap, '55']);
    markers.push([left, 'left']);
    if (Math.max(right, left) !== left) markers.push([Math.max(right, left), 'right']);
    markers.forEach(([v, label], markerIndex) => {
      const x = pos(v);
      ctx.strokeStyle = 'rgba(203,213,225,0.42)';
      ctx.beginPath();
      ctx.moveTo(x, axisY - 13);
      ctx.lineTo(x, axisY + 13);
      ctx.stroke();
      ctx.fillStyle = '#cbd5e1';
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(label, x, axisY + 25 + (markerIndex % 2) * 15);
    });

    const mx = pos(capacity);
    ctx.fillStyle = concept.days <= concept.D ? 'rgba(16,185,129,0.28)' : 'rgba(239,68,68,0.25)';
    ctx.strokeStyle = concept.days <= concept.D ? '#34d399' : '#f87171';
    this._round_rect(ctx, mx - 54, axisY - 76, 108, 48, 14);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#f8fafc';
    ctx.font = '800 18px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`mid=${capacity}`, mx, axisY - 52);

    const weights = Array.isArray(concept.weights) ? concept.weights : [];
    const gap = this.width < 620 ? 3 : 6;
    const cell = Math.min(34, (this.width - 42 - Math.max(0, weights.length - 1) * gap) / Math.max(weights.length, 1));
    const totalW = weights.length * cell + (weights.length - 1) * gap;
    const wx0 = cx - totalW / 2;
    weights.forEach((w, i) => {
      const x = wx0 + i * (cell + gap);
      ctx.fillStyle = 'rgba(59,130,246,0.24)';
      ctx.strokeStyle = 'rgba(96,165,250,0.5)';
      this._round_rect(ctx, x, top, cell, 34, 8);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#e2e8f0';
      ctx.font = '700 13px "JetBrains Mono", monospace';
      ctx.fillText(String(w), x + cell / 2, top + 18);
    });

    ctx.fillStyle = concept.days <= concept.D ? '#bbf7d0' : '#fecaca';
    ctx.font = '800 24px "JetBrains Mono", monospace';
    ctx.fillText(`${concept.days} 天 ${concept.days <= concept.D ? '可行' : '不可行'} / 目标 ${concept.D} 天`, cx, axisY + 92);
    if (concept.phase && this.height - axisY > 86) {
      ctx.fillStyle = '#dbeafe';
      ctx.font = '700 13px "Noto Sans SC", sans-serif';
      ctx.fillText(concept.phase, cx, axisY + 58);
    }
    ctx.restore();
  }

  _draw_distribution_sort(ctx, concept) {
    this._draw_title(ctx, concept.title || '分发排序', concept.mode === 'radix' ? `当前处理: ${concept.digit || ''}` : '把元素放进合适的桶, 再按桶收集');
    const items = Array.isArray(concept.items) ? concept.items : [];
    const buckets = Array.isArray(concept.buckets) ? concept.buckets : [];
    const centerX = this.width / 2;
    const compact = this.width < 620;
    const topY = Math.max(108, this.height * 0.20);
    const tileW = Math.max(22, Math.min(
      58,
      Math.floor((this.width - (compact ? 36 : 160)) / Math.max(items.length, 1)),
    ));

    const draw_tile = (x, y, text, active = false) => {
      ctx.fillStyle = active ? 'rgba(251,191,36,0.26)' : 'rgba(74,143,212,0.18)';
      ctx.strokeStyle = active ? VIZ_COLORS.pointerText : 'rgba(255,255,255,0.18)';
      ctx.lineWidth = active ? 2.5 : 1;
      ctx.beginPath();
      ctx.roundRect(x, y, tileW - 6, 38, 8);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = VIZ_COLORS.text;
      ctx.font = `${compact ? 11 : 15}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(String(text), x + (tileW - 6) / 2, y + 19);
    };

    if (items.length) {
      const startX = centerX - (items.length * tileW) / 2;
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '13px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('当前数组', centerX, topY - 22);
      items.forEach((item, idx) => draw_tile(startX + idx * tileW, topY, item, false));
    }

    if (buckets.length) {
      const bucketGap = compact ? 5 : 10;
      const bucketAreaW = compact
        ? this.width - 32
        : Math.min(this.width - 80, Math.max(420, buckets.length * 102));
      const bucketW = compact
        ? (bucketAreaW - Math.max(0, buckets.length - 1) * bucketGap) / Math.max(buckets.length, 1)
        : Math.max(74, Math.min(110, (bucketAreaW - (buckets.length - 1) * bucketGap) / buckets.length));
      const startX = centerX - bucketAreaW / 2;
      const bucketY = topY + 86;
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '13px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('桶', centerX, bucketY - 24);
      buckets.forEach(([label, vals], idx) => {
        const x = startX + idx * (bucketW + bucketGap);
        const h = 126;
        ctx.fillStyle = 'rgba(21,25,32,0.72)';
        ctx.strokeStyle = vals && vals.length ? 'rgba(73,164,238,0.46)' : 'rgba(148,163,184,0.18)';
        ctx.lineWidth = vals && vals.length ? 2 : 1;
        ctx.beginPath();
        ctx.roundRect(x, bucketY, bucketW, h, 10);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = '#c9d7ec';
        ctx.font = `600 ${compact ? 9 : 12}px sans-serif`;
        this._fill_text_fit(ctx, String(label), x + bucketW / 2, bucketY + 18, bucketW - 6, size => `600 ${size}px sans-serif`, compact ? 9 : 12, 7);
        (vals || []).slice(0, 5).forEach((v, j) => {
          ctx.fillStyle = 'rgba(16,185,129,0.20)';
          ctx.strokeStyle = 'rgba(16,185,129,0.42)';
          ctx.beginPath();
          ctx.roundRect(x + (compact ? 3 : 12), bucketY + 34 + j * 17, bucketW - (compact ? 6 : 24), 14, 4);
          ctx.fill();
          ctx.stroke();
          ctx.fillStyle = VIZ_COLORS.text;
          ctx.font = `${compact ? 8 : 11}px "JetBrains Mono", monospace`;
          this._fill_text_fit(ctx, String(v), x + bucketW / 2, bucketY + 41 + j * 17, bucketW - 8, size => `${size}px "JetBrains Mono", monospace`, compact ? 8 : 11, 7);
        });
      });
    }

    if (concept.result && concept.result !== '-') {
      const resultText = `结果: ${concept.result}`;
      const w = Math.min(this.width - 100, Math.max(260, resultText.length * 11));
      const y = this.height - 92;
      ctx.fillStyle = 'rgba(21,25,32,0.80)';
      ctx.strokeStyle = 'rgba(16,185,129,0.42)';
      ctx.beginPath();
      ctx.roundRect(centerX - w / 2, y, w, 34, 8);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#bbf7d0';
      ctx.font = '14px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(resultText, centerX, y + 17);
    }

    this._draw_caption(ctx, concept.phase || '分发排序的重点是先分类, 再按类别顺序收集');
  }

  _draw_stable_counting(ctx, concept) {
    this._draw_title(ctx, concept.title || '稳定版计数排序', '从右往左放置, 同分元素不会插队');
    const original = Array.isArray(concept.original) ? concept.original : [];
    const output = Array.isArray(concept.output) ? concept.output : [];
    const counts = Array.isArray(concept.counts) ? concept.counts : [];
    const prefix = Array.isArray(concept.prefix) ? concept.prefix : [];
    const scan = Number.isFinite(concept.scan) ? concept.scan : -1;
    const cx = this.width / 2;
    const compact = this.height < 480 || this.width < 620;
    const gap = compact ? 3 : 7;
    const cell = Math.max(24, Math.min(
      54,
      Math.floor((this.width - (compact ? 34 : 130) - Math.max(0, original.length - 1) * gap) / Math.max(original.length, 1)),
    ));
    const totalW = original.length * cell + Math.max(0, original.length - 1) * gap;
    const startX = cx - totalW / 2;
    const topY = compact ? 90 : Math.max(96, this.height * 0.22);
    const cardH = compact ? 36 : 48;
    const value_color = (value, alpha = 0.24) => {
      if (value === 0) return `rgba(56,189,248,${alpha})`;
      if (value === 1) return `rgba(34,197,94,${alpha})`;
      return `rgba(251,146,60,${alpha})`;
    };
    const draw_card = (item, x, y, active = false, muted = false) => {
      const value = item && typeof item === 'object' ? item.value : '';
      const id = item && typeof item === 'object' ? item.id : '';
      ctx.fillStyle = muted ? 'rgba(15,23,42,0.46)' : value_color(value, active ? 0.36 : 0.22);
      ctx.strokeStyle = active ? '#fbbf24' : value_color(value, 0.62);
      ctx.lineWidth = active ? 3 : 1.5;
      ctx.beginPath();
      ctx.roundRect(x, y, cell, cardH, 9);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = muted ? 'rgba(226,232,240,0.28)' : '#f8fafc';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.font = `800 ${compact ? 14 : 19}px "JetBrains Mono", monospace`;
      ctx.fillText(String(value), x + cell / 2, y + (compact ? 14 : 19));
      ctx.fillStyle = muted ? 'rgba(226,232,240,0.24)' : 'rgba(226,232,240,0.72)';
      ctx.font = `${compact ? 8 : 11}px "JetBrains Mono", monospace`;
      ctx.fillText(`#${id}`, x + cell / 2, y + (compact ? 27 : 36));
    };

    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('原数组: 数字是分数, # 是原始下标', cx, topY - 22);
    original.forEach((item, idx) => draw_card(item, startX + idx * (cell + gap), topY, idx === scan, false));

    if (scan >= 0) {
      const arrowX = startX + scan * (cell + gap) + cell / 2;
      ctx.strokeStyle = '#fbbf24';
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.moveTo(arrowX, topY + cardH + 6);
      ctx.lineTo(arrowX, topY + cardH + 22);
      ctx.stroke();
      ctx.fillStyle = '#fbbf24';
      ctx.font = `800 ${compact ? 11 : 13}px sans-serif`;
      ctx.fillText('当前从右往左扫描', compact ? cx : arrowX, topY + cardH + 38);
    }

    const boxW = compact ? Math.min(82, (this.width - 70) / 3) : 86;
    const countY = topY + (compact ? (scan >= 0 ? 106 : 84) : 112);
    const countStart = cx - (3 * boxW + 2 * 14) / 2;
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px sans-serif';
    ctx.fillText(prefix.length ? '前缀和边界' : '计数桶', cx, countY - 18);
    [0, 1, 2].forEach((value, idx) => {
      const x = countStart + idx * (boxW + 14);
      ctx.fillStyle = value_color(value, 0.20);
      ctx.strokeStyle = value_color(value, 0.62);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.roundRect(x, countY, boxW, compact ? 42 : 52, 10);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#e2e8f0';
      ctx.font = `700 ${compact ? 10 : 12}px sans-serif`;
      ctx.fillText(`分数 ${value}`, x + boxW / 2, countY + (compact ? 13 : 16));
      ctx.font = `800 ${compact ? 13 : 17}px "JetBrains Mono", monospace`;
      const topText = prefix.length ? `边界 ${prefix[idx]}` : `次数 ${counts[idx] ?? '-'}`;
      const bottomText = prefix.length ? `剩 ${counts[idx] ?? '-'}` : '';
      ctx.fillText(topText, x + boxW / 2, countY + (compact ? 29 : 34));
      if (bottomText && !compact) {
        ctx.fillStyle = 'rgba(226,232,240,0.72)';
        ctx.font = '11px sans-serif';
        ctx.fillText(bottomText, x + boxW / 2, countY + 47);
      }
    });

    const outY = countY + (compact ? 68 : 102);
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px sans-serif';
    ctx.fillText('结果数组: 每次从对应分区的右边往左填', cx, outY - 22);
    output.forEach((item, idx) => {
      const x = startX + idx * (cell + gap);
      if (item) {
        draw_card(item, x, outY, false, false);
      } else {
        ctx.fillStyle = 'rgba(15,23,42,0.54)';
        ctx.strokeStyle = 'rgba(148,163,184,0.22)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(x, outY, cell, cardH, 9);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = 'rgba(148,163,184,0.55)';
        ctx.font = '12px "JetBrains Mono", monospace';
        ctx.fillText(String(idx), x + cell / 2, outY + cardH / 2);
      }
    });

    if (concept.result && concept.result !== '-' && (!compact || this.height > 520)) {
      const resultText = `顺序: ${concept.result}`;
      const w = Math.min(this.width - 48, Math.max(compact ? 250 : 320, resultText.length * (compact ? 7 : 9)));
      const y = compact ? Math.min(this.height - 70, outY + cardH + 12) : this.height - 84;
      ctx.fillStyle = 'rgba(21,25,32,0.82)';
      ctx.strokeStyle = 'rgba(34,197,94,0.46)';
      ctx.beginPath();
      ctx.roundRect(cx - w / 2, y, w, compact ? 28 : 34, 8);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#bbf7d0';
      ctx.font = `${compact ? 10 : 13}px "JetBrains Mono", monospace`;
      this._fill_text_fit(ctx, resultText, cx, y + (compact ? 14 : 17), w - 20, size => `${size}px "JetBrains Mono", monospace`, compact ? 10 : 13, 8);
    }
    this._draw_caption(ctx, concept.phase || '稳定排序要求同分元素保持原来的相对顺序');
  }

  _draw_stability_compare(ctx, concept) {
    this._draw_title(ctx, concept.title || '稳定性对比', '排序正确之外, 还要看同分元素有没有插队');
    const bubble = Array.isArray(concept.bubble) ? concept.bubble : [];
    const selection = Array.isArray(concept.selection) ? concept.selection : [];
    const active = new Set(Array.isArray(concept.active) ? concept.active : []);
    const unstable = new Set(Array.isArray(concept.unstable) ? concept.unstable : []);
    const cx = this.width / 2;
    const compact = this.width < 560;
    const gap = compact ? 6 : 10;
    const reserveW = compact ? 80 : 170;
    const cellW = Math.max(compact ? 62 : 92, Math.min(
      132,
      (this.width - reserveW - Math.max(0, bubble.length - 1) * gap) / Math.max(bubble.length, 1),
    ));
    const totalW = bubble.length * cellW + Math.max(0, bubble.length - 1) * gap;
    const x0 = cx - totalW / 2;
    const topY = Math.max(104, this.height * 0.24);
    const draw_row = (label, arr, y, stable) => {
      ctx.fillStyle = stable ? '#bbf7d0' : '#fecaca';
      ctx.font = '800 15px "Inter", sans-serif';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, x0 - (compact ? 8 : 18), y + 27);
      arr.forEach((text, idx) => {
        const x = x0 + idx * (cellW + gap);
        const isActive = active.has(idx);
        const isBad = !stable && unstable.has(idx);
        ctx.fillStyle = isBad ? 'rgba(239,68,68,0.30)' : stable ? 'rgba(16,185,129,0.22)' : 'rgba(59,130,246,0.16)';
        ctx.strokeStyle = isActive ? '#fbbf24' : isBad ? '#f87171' : stable ? '#34d399' : 'rgba(96,165,250,0.46)';
        ctx.lineWidth = isActive || isBad ? 2.5 : 1.4;
        ctx.beginPath();
        ctx.roundRect(x, y, cellW, 54, 10);
        ctx.fill();
        ctx.stroke();
        const [name, score] = String(text).split(' ');
        ctx.fillStyle = '#f8fafc';
        ctx.font = '800 15px "Inter", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(name || text, x + cellW / 2, y + 21);
        ctx.fillStyle = 'rgba(226,232,240,0.76)';
        ctx.font = '12px "JetBrains Mono", monospace';
        ctx.fillText(score || '', x + cellW / 2, y + 39);
        if (isBad) this._draw_small_tag(ctx, x + cellW / 2, y - 14, '插队', '#f87171');
      });
    };
    ctx.save();
    draw_row('冒泡', bubble, topY, true);
    draw_row('选择', selection, topY + 108, false);
    ctx.textAlign = 'center';
    ctx.font = '700 13px "Inter", sans-serif';
    ctx.fillStyle = '#93c5fd';
    this._fill_text_fit(
      ctx,
      '只看分数排序, 同为 658 的相对顺序最关键',
      cx,
      topY + 68,
      this.width - 72,
      size => `700 ${size}px "Inter", sans-serif`,
      13,
      10,
    );
    this._draw_caption(ctx, concept.phase || '稳定排序: 相等元素保持原来的相对顺序');
    ctx.restore();
  }

  _draw_external_sort(ctx, concept) {
    this._draw_title(ctx, concept.title || '外部排序', '内存放不下时: 分段排序, 再多路归并');
    const runs = Array.isArray(concept.runs) ? concept.runs : [];
    const heads = Array.isArray(concept.heads) ? concept.heads : [];
    const output = Array.isArray(concept.output) ? concept.output : [];
    const cx = this.width / 2;
    const compact = this.width < 620;
    const topY = Math.max(98, this.height * 0.20);
    const gap = compact ? 6 : 18;
    const runW = compact
      ? (this.width - 32 - Math.max(0, runs.length - 1) * gap) / Math.max(runs.length, 1)
      : Math.max(150, Math.min(220, (this.width - 150) / Math.max(runs.length, 1)));
    const totalW = runs.length * runW + Math.max(0, runs.length - 1) * gap;
    const x0 = cx - totalW / 2;
    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    runs.forEach((run, idx) => {
      const x = x0 + idx * (runW + gap);
      ctx.fillStyle = 'rgba(15,23,42,0.72)';
      ctx.strokeStyle = run.length ? 'rgba(96,165,250,0.44)' : 'rgba(148,163,184,0.20)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.roundRect(x, topY, runW, 140, 12);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#cbd5e1';
      ctx.font = `700 ${compact ? 10 : 13}px "Inter", sans-serif`;
      this._fill_text_fit(ctx, `归并段 ${idx + 1}`, x + runW / 2, topY + 18, runW - 8, size => `700 ${size}px "Inter", sans-serif`, compact ? 10 : 13, 8);
      (run || []).slice(0, 5).forEach((v, j) => {
        const y = topY + 40 + j * 18;
        const isHead = heads.includes(v);
        ctx.fillStyle = isHead ? 'rgba(251,191,36,0.30)' : 'rgba(59,130,246,0.18)';
        ctx.strokeStyle = isHead ? '#fbbf24' : 'rgba(96,165,250,0.32)';
        ctx.beginPath();
        ctx.roundRect(x + (compact ? 5 : 18), y, runW - (compact ? 10 : 36), 14, 5);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = '#f8fafc';
        ctx.font = '11px "JetBrains Mono", monospace';
        ctx.fillText(String(v), x + runW / 2, y + 7);
      });
    });
    if (heads.length) {
      const headText = `当前候选: ${heads.join(', ')}`;
      ctx.fillStyle = 'rgba(251,191,36,0.16)';
      ctx.strokeStyle = 'rgba(251,191,36,0.42)';
      ctx.beginPath();
      ctx.roundRect(cx - 128, topY + 146, 256, 34, 17);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fde68a';
      ctx.font = '800 14px "JetBrains Mono", monospace';
      ctx.fillText(headText, cx, topY + 163);
    }
    const outY = Math.min(this.height - 78, topY + 190);
    ctx.fillStyle = 'rgba(21,25,32,0.82)';
    ctx.strokeStyle = 'rgba(16,185,129,0.42)';
    ctx.beginPath();
    ctx.roundRect(Math.max(36, cx - 330), outY, Math.min(660, this.width - 72), 44, 10);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = output.length ? '#bbf7d0' : '#94a3b8';
    ctx.font = '13px "JetBrains Mono", monospace';
    const outText = output.length ? `输出: ${output.join(', ')}` : '输出文件等待写入';
    this._fill_text_fit(ctx, outText, cx, outY + 22, Math.min(640, this.width - 92), size => `${size}px "JetBrains Mono", monospace`, 13, 8);
    this._draw_caption(ctx, concept.phase || '外部排序的关键不是 CPU, 而是减少磁盘读写轮数');
    ctx.restore();
  }

  _draw_activity_selection(ctx, concept) {
    this._draw_title(ctx, concept.title || '活动选择', '按结束时间排序, 每次选择最早结束且不冲突的活动');
    const acts = Array.isArray(concept.activities) ? concept.activities : [];
    const selected = new Set(concept.selected || []);
    const current = concept.current;
    const minT = 0;
    const maxT = 16;
    const left = Math.max(54, this.width * 0.10);
    const right = Math.min(this.width - 42, this.width * 0.92);
    const top = Math.max(110, this.height * 0.17);
    const rowH = Math.min(28, Math.max(17, (this.height - top - 58) / Math.max(acts.length, 1)));
    const scale_x = t => left + (t - minT) / (maxT - minT) * (right - left);
    ctx.save();
    ctx.strokeStyle = 'rgba(148,163,184,0.38)';
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(left, top - 22);
    ctx.lineTo(right, top - 22);
    ctx.stroke();
    ctx.fillStyle = '#94a3b8';
    ctx.font = '11px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    for (let t = 0; t <= 16; t += 2) {
      const x = scale_x(t);
      ctx.fillText(String(t), x, top - 38);
      ctx.beginPath();
      ctx.moveTo(x, top - 28);
      ctx.lineTo(x, top - 17);
      ctx.stroke();
    }
    acts.forEach((a, idx) => {
      const y = top + idx * rowH;
      const x = scale_x(a.start);
      const w = Math.max(12, scale_x(a.end) - x);
      const isSelected = selected.has(a.id);
      const isCurrent = current === a.id;
      ctx.fillStyle = isSelected ? 'rgba(16,185,129,0.36)' : isCurrent ? 'rgba(251,191,36,0.34)' : 'rgba(71,85,105,0.42)';
      ctx.strokeStyle = isSelected ? '#34d399' : isCurrent ? '#fbbf24' : 'rgba(148,163,184,0.35)';
      ctx.lineWidth = isSelected || isCurrent ? 2.4 : 1.2;
      ctx.beginPath();
      ctx.roundRect(x, y, w, rowH - 5, 6);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#f8fafc';
      ctx.font = '700 12px "Inter", sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(a.id, x + 6, y + (rowH - 5) / 2);
    });
    if (concept.lastEnd) {
      const lx = scale_x(concept.lastEnd);
      ctx.strokeStyle = 'rgba(251,191,36,0.65)';
      ctx.setLineDash([6, 5]);
      ctx.beginPath();
      ctx.moveTo(lx, top - 10);
      ctx.lineTo(lx, top + acts.length * rowH + 6);
      ctx.stroke();
      ctx.setLineDash([]);
      this._draw_small_tag(ctx, lx, top + acts.length * rowH + 24, `last=${concept.lastEnd}`, '#fbbf24');
    }
    this._draw_caption(ctx, concept.phase || '选结束最早的活动, 给后面留下最大空间');
    ctx.restore();
  }

  _draw_huffman(ctx, concept) {
    this._draw_title(ctx, concept.title || '哈夫曼编码', '反复合并当前频率最小的两个节点');
    const heap = Array.isArray(concept.heap) ? concept.heap : [];
    const picked = new Set(concept.picked || []);
    const cx = this.width / 2;
    const top = Math.max(112, this.height * 0.25);
    const compact = this.width < 620;
    const gap = compact ? 5 : 10;
    const cellW = compact
      ? (this.width - 32 - Math.max(0, heap.length - 1) * gap) / Math.max(heap.length, 1)
      : Math.max(78, Math.min(112, (this.width - 120) / Math.max(heap.length, 1)));
    const totalW = heap.length * cellW + Math.max(0, heap.length - 1) * gap;
    const x0 = cx - totalW / 2;
    ctx.save();
    heap.forEach((node, idx) => {
      const text = String(node);
      const x = x0 + idx * (cellW + gap);
      const active = picked.has(text);
      ctx.fillStyle = active ? 'rgba(251,191,36,0.34)' : 'rgba(59,130,246,0.20)';
      ctx.strokeStyle = active ? '#fbbf24' : 'rgba(96,165,250,0.48)';
      ctx.lineWidth = active ? 2.6 : 1.4;
      ctx.beginPath();
      ctx.roundRect(x, top, cellW, 56, 12);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#f8fafc';
      ctx.font = `800 ${compact ? 11 : 16}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, x + cellW / 2, top + 28);
    });
    if (picked.size === 2) {
      ctx.strokeStyle = 'rgba(251,191,36,0.62)';
      ctx.lineWidth = 2.2;
      const y2 = top + 116;
      Array.from(picked).forEach((p) => {
        const idx = heap.indexOf(p);
        if (idx < 0) return;
        const x = x0 + idx * (cellW + gap) + cellW / 2;
        this._draw_arrow(ctx, x, top + 60, cx, y2 - 14, 'rgba(251,191,36,0.45)', '#fbbf24', 2);
      });
      ctx.fillStyle = 'rgba(16,185,129,0.26)';
      ctx.strokeStyle = 'rgba(52,211,153,0.58)';
      ctx.beginPath();
      ctx.roundRect(cx - 90, y2, 180, 42, 12);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#bbf7d0';
      ctx.font = '800 14px "Inter", sans-serif';
      ctx.fillText('合并后放回堆', cx, y2 + 21);
    }
    this._draw_caption(ctx, concept.phase || '频率越高, 最终路径越短');
    ctx.restore();
  }

  _draw_kruskal(ctx, concept) {
    this._draw_title(ctx, concept.title || 'Kruskal 最小生成树', '从最便宜的边开始, 不成环就加入');
    const nodes = Array.isArray(concept.nodes) ? concept.nodes : [];
    const edges = Array.isArray(concept.edges) ? concept.edges : [];
    const chosen = new Set((concept.chosen || []).map(e => `${e[0]}-${e[1]}`));
    const rejected = new Set((concept.rejected || []).map(e => `${e[0]}-${e[1]}`));
    const current = Array.isArray(concept.current) ? `${concept.current[0]}-${concept.current[1]}` : '';
    const center = { x: this.width * 0.40, y: this.height * 0.52 };
    const radius = Math.min(130, this.width * 0.16, this.height * 0.24);
    const pos = new Map();
    nodes.forEach((n, idx) => {
      const angle = -Math.PI / 2 + idx * Math.PI * 2 / nodes.length;
      pos.set(n, { x: center.x + Math.cos(angle) * radius, y: center.y + Math.sin(angle) * radius });
    });
    ctx.save();
    edges.forEach(([a, b, w], edgeIndex) => {
      const pa = pos.get(a), pb = pos.get(b);
      if (!pa || !pb) return;
      const key = `${a}-${b}`;
      const active = key === current;
      const keep = chosen.has(key);
      const skip = rejected.has(key);
      ctx.strokeStyle = keep ? '#34d399' : active ? '#fbbf24' : skip ? 'rgba(248,113,113,0.58)' : 'rgba(148,163,184,0.28)';
      ctx.lineWidth = keep || active ? 4 : 2;
      ctx.beginPath();
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      ctx.stroke();
      ctx.fillStyle = active ? '#fde68a' : keep ? '#bbf7d0' : '#cbd5e1';
      ctx.font = '800 12px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const dx = pb.x - pa.x;
      const dy = pb.y - pa.y;
      const len = Math.max(1, Math.hypot(dx, dy));
      const direction = edgeIndex % 2 === 0 ? -1 : 1;
      const offset = 10;
      ctx.fillText(
        String(w),
        (pa.x + pb.x) / 2 - dy / len * offset * direction,
        (pa.y + pb.y) / 2 + dx / len * offset * direction,
      );
    });
    nodes.forEach(n => {
      const p = pos.get(n);
      ctx.fillStyle = 'rgba(59,130,246,0.78)';
      ctx.strokeStyle = 'rgba(255,255,255,0.36)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 23, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = '800 16px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(n, p.x, p.y);
    });
    const sideX = this.width * 0.66;
    ctx.fillStyle = 'rgba(15,23,42,0.72)';
    ctx.strokeStyle = 'rgba(96,165,250,0.32)';
    ctx.beginPath();
    ctx.roundRect(sideX, center.y - 110, 230, 168, 12);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#e2e8f0';
    ctx.font = '800 14px "Inter", sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(`已选边: ${(concept.chosen || []).length}`, sideX + 18, center.y - 78);
    ctx.fillText(`总造价: ${concept.total || 0}`, sideX + 18, center.y - 48);
    ctx.fillStyle = '#94a3b8';
    ctx.font = '12px "Inter", sans-serif';
    ctx.fillText('绿色=加入 MST', sideX + 18, center.y - 12);
    ctx.fillText('黄色=当前考察', sideX + 18, center.y + 16);
    this._draw_caption(ctx, concept.phase || '并查集负责判断加入边后会不会成环');
    ctx.restore();
  }

  _draw_birthday(ctx, concept) {
    const birthdays = Array.isArray(concept.birthdays) ? concept.birthdays : [];
    const duplicateDay = concept.duplicateDay;
    this._draw_title(ctx, '生日悖论', '任意两个人撞生日, 组合数量会长得很快');

    const compact = this.width < 620;
    const gridCols = 14;
    const cell = Math.min(24, Math.floor((this.width - (compact ? 70 : 150)) / gridCols));
    const gap = 5;
    const gridRows = 8;
    const totalW = gridCols * cell + (gridCols - 1) * gap;
    const sideW = compact ? this.width - 48 : 210;
    const sideGap = compact ? 0 : 54;
    const totalGroupW = compact ? totalW : totalW + sideGap + sideW;
    const gridH = gridRows * cell + (gridRows - 1) * gap;
    const startX = compact ? (this.width - totalW) / 2 : Math.max(42, (this.width - totalGroupW) / 2);
    const startY = compact ? 88 : Math.max(76, (this.height - gridH) / 2 - 22);
    const occupied = new Map();
    birthdays.forEach((day, idx) => {
      if (!occupied.has(day)) occupied.set(day, []);
      occupied.get(day).push(idx);
    });

    ctx.save();
    for (let i = 0; i < gridCols * gridRows; i++) {
      const x = startX + (i % gridCols) * (cell + gap);
      const y = startY + Math.floor(i / gridCols) * (cell + gap);
      const day = Math.floor(i * 365 / (gridCols * gridRows)) + 1;
      const hit = Array.from(occupied.keys()).some(d => Math.abs(d - day) <= 2);
      const duplicate = duplicateDay && Math.abs(duplicateDay - day) <= 2;
      ctx.fillStyle = duplicate ? 'rgba(239,68,68,0.82)' : hit ? 'rgba(245,158,11,0.68)' : 'rgba(255,255,255,0.06)';
      ctx.strokeStyle = duplicate ? 'rgba(255,255,255,0.55)' : 'rgba(255,255,255,0.10)';
      ctx.lineWidth = duplicate ? 2 : 1;
      ctx.beginPath();
      ctx.roundRect(x, y, cell, cell, 5);
      ctx.fill();
      ctx.stroke();
    }

    const people = concept.people || birthdays.length;
    const pairCount = people * (people - 1) / 2;
    const sideX = compact ? 24 : startX + totalW + sideGap;
    const sideY = compact ? startY + gridH + 26 : startY;
    ctx.fillStyle = VIZ_COLORS.text;
    ctx.font = 'bold 14px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText('这次模拟', sideX, sideY + 2);
    const stats = [
      `人数: ${people}`,
      `可能配对: ${pairCount}`,
      `碰撞概率: ${Math.round((concept.probability || 0) * 1000) / 10}%`,
      concept.collision ? '已经出现同生日' : '还没有撞上',
    ];
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
    stats.forEach((text, idx) => ctx.fillText(
      text,
      compact ? sideX + (idx % 2) * sideW / 2 : sideX,
      sideY + 34 + (compact ? Math.floor(idx / 2) * 27 : idx * 27),
    ));

    const personY = Math.min(this.height - 94, compact ? sideY + 104 : startY + gridRows * (cell + gap) + 28);
    const shownPeople = Math.min(people, 23);
    const px0 = startX;
    for (let i = 0; i < shownPeople; i++) {
      const px = px0 + (i % 12) * 28;
      const py = personY + Math.floor(i / 12) * 27;
      const same = birthdays[i] === duplicateDay;
      ctx.fillStyle = same ? VIZ_COLORS.barSwap : VIZ_COLORS.barDefault;
      ctx.strokeStyle = 'rgba(255,255,255,0.22)';
      ctx.beginPath();
      ctx.arc(px, py, same ? 9 : 7, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }

    this._draw_caption(ctx, concept.collision ? '重点不是 365 天很多, 而是人和人之间的配对更多' : '每新来一个人, 都会和前面所有人形成新的比较机会');
    ctx.restore();
  }

  _draw_reservoir_sampling(ctx, concept) {
    const stream = Array.isArray(concept.stream) ? concept.stream : [];
    const reservoir = Array.isArray(concept.reservoir) ? concept.reservoir : [];
    const current = Number(concept.current);
    const seen = Number(concept.seen) || 0;
    const replaced = new Set(concept.replaced || []);
    this._draw_title(ctx, '蓄水池抽样', `水池容量 k=${concept.k || reservoir.length}, 当前进入概率 ${concept.probability || '-'}`);

    const cx = this.width / 2;
    const tile = Math.max(40, Math.min(54, Math.floor((this.width - 180) / Math.max(stream.length, 1))));
    const streamX = cx - stream.length * tile / 2;
    const compactHeight = this.height < 460;
    const streamY = Math.max(110, this.height * 0.22);

    ctx.save();
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('数据流', cx, streamY - 24);
    stream.forEach((item, idx) => {
      const x = streamX + idx * tile;
      const isSeen = idx < seen;
      const isCurrent = idx === current;
      ctx.fillStyle = isCurrent ? 'rgba(251,191,36,0.30)' : isSeen ? 'rgba(74,143,212,0.20)' : 'rgba(148,163,184,0.10)';
      ctx.strokeStyle = isCurrent ? VIZ_COLORS.pointerText : isSeen ? 'rgba(73,164,238,0.38)' : 'rgba(148,163,184,0.16)';
      ctx.lineWidth = isCurrent ? 3 : 1;
      ctx.beginPath();
      ctx.roundRect(x, streamY, tile - 7, 42, 10);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = isSeen ? VIZ_COLORS.text : VIZ_COLORS.textDim;
      ctx.font = 'bold 16px sans-serif';
      ctx.fillText(String(item), x + (tile - 7) / 2, streamY + 22);
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '10px "JetBrains Mono", monospace';
      ctx.fillText(String(idx + 1), x + (tile - 7) / 2, streamY + 56);
    });

    const poolY = streamY + (compactHeight ? 116 : 126);
    const slotW = 86;
    const gap = 16;
    const poolW = reservoir.length * slotW + Math.max(0, reservoir.length - 1) * gap;
    const poolX = cx - poolW / 2;
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px sans-serif';
    ctx.fillText('蓄水池 reservoir', cx, poolY - 28);
    reservoir.forEach((item, idx) => {
      const x = poolX + idx * (slotW + gap);
      const active = replaced.has(idx);
      ctx.fillStyle = active ? 'rgba(251,191,36,0.24)' : 'rgba(16,185,129,0.18)';
      ctx.strokeStyle = active ? VIZ_COLORS.pointerText : 'rgba(16,185,129,0.48)';
      ctx.lineWidth = active ? 3 : 2;
      ctx.beginPath();
      ctx.roundRect(x, poolY, slotW, compactHeight ? 54 : 68, 12);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#bbf7d0';
      ctx.font = '12px sans-serif';
      ctx.fillText(`slot ${idx}`, x + slotW / 2, poolY + 16);
      ctx.fillStyle = VIZ_COLORS.text;
      ctx.font = `bold ${compactHeight ? 20 : 24}px sans-serif`;
      ctx.fillText(String(item), x + slotW / 2, poolY + (compactHeight ? 36 : 45));
    });

    const probText = `规则: 第 ${seen || '-'} 个元素以 k/i = ${concept.probability || '-'} 的概率尝试进入水池`;
    const boxW = Math.min(this.width - 110, Math.max(360, probText.length * 10));
    if (!compactHeight) {
      const boxY = this.height - 94;
      ctx.fillStyle = 'rgba(21,25,32,0.82)';
      ctx.strokeStyle = 'rgba(73,164,238,0.28)';
      ctx.beginPath();
      ctx.roundRect(cx - boxW / 2, boxY, boxW, 36, 9);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#c9d7ec';
      ctx.font = '13px sans-serif';
      ctx.fillText(probText, cx, boxY + 18);
    }

    this._draw_caption(ctx, concept.phase || '水池容量固定, 但每个看过的元素最终留下的机会一样');
    ctx.restore();
  }

  _draw_bloom_filter(ctx, concept) {
    const size = Number(concept.size) || 16;
    const bits = new Set(concept.bits || []);
    const hashes = new Set(concept.hashes || []);
    this._draw_title(ctx, concept.title || '布隆过滤器', '多个哈希函数把一个元素映射到多个 bit');

    const cell = Math.min(42, Math.floor((this.width - (this.width < 620 ? 30 : 130)) / size));
    const s = Math.max(16, cell);
    const totalW = size * s;
    const startX = (this.width - totalW) / 2;
    const y = this.height / 2 - 34;

    ctx.save();
    for (let i = 0; i < size; i++) {
      const x = startX + i * s;
      const on = bits.has(i);
      const hit = hashes.has(i);
      ctx.fillStyle = hit ? 'rgba(251,191,36,0.68)' : on ? 'rgba(34,197,94,0.70)' : 'rgba(51,65,85,0.82)';
      ctx.strokeStyle = hit ? 'rgba(251,191,36,0.95)' : 'rgba(255,255,255,0.14)';
      ctx.lineWidth = hit ? 2.4 : 1.2;
      ctx.beginPath();
      ctx.roundRect(x, y, s - 4, s, 6);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = `bold ${Math.max(8, Math.floor(s * 0.38))}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(on ? '1' : '0', x + (s - 4) / 2, y + s / 2);
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = `${s < 22 ? 8 : 10}px "JetBrains Mono", monospace`;
      ctx.fillText(String(i), x + (s - 4) / 2, y + s + 14);
    }

    const key = concept.key || '-';
    const boxW = 230;
    const boxX = this.width / 2 - boxW / 2;
    const boxY = y - 94;
    ctx.fillStyle = 'rgba(21,25,32,0.86)';
    ctx.strokeStyle = 'rgba(73,164,238,0.28)';
    ctx.beginPath();
    ctx.roundRect(boxX, boxY, boxW, 64, 9);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = VIZ_COLORS.text;
    ctx.font = 'bold 14px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`key: ${key}`, this.width / 2, boxY + 18);
    ctx.fillStyle = concept.mode === 'miss' ? '#fecaca' : concept.mode === 'false_positive' ? '#fde68a' : '#bbf7d0';
    ctx.font = 'bold 13px -apple-system, "PingFang SC", sans-serif';
    ctx.fillText(concept.verdict || '', this.width / 2, boxY + 42);

    const hashList = Array.from(hashes);
    hashList.forEach((idx, order) => {
      const tx = startX + idx * s + (s - 4) / 2;
      const fromX = boxX + 46 + order * 64;
      this._draw_arrow(ctx, fromX, boxY + 64, tx, y - 8, 'rgba(251,191,36,0.55)', 'rgba(251,191,36,0.75)', 1.8);
      ctx.fillStyle = VIZ_COLORS.pointerText;
      ctx.font = '11px "JetBrains Mono", monospace';
      ctx.fillText(`h${order + 1}`, fromX, boxY + 78);
    });

    const caption = concept.mode === 'miss'
      ? '只要有一个哈希位置是 0, 就能确定这个元素不存在'
      : concept.mode === 'false_positive'
        ? '所有位置都是 1 也不代表真的插入过, 这就是误判'
        : '插入时只负责把多个哈希位置置为 1';
    this._draw_caption(ctx, caption);
    ctx.restore();
  }

  _draw_bitmask_tsp(ctx, concept) {
    const cities = Array.isArray(concept.cities) ? concept.cities : ['A', 'B', 'C', 'D'];
    const edges = Array.isArray(concept.edges) ? concept.edges : [];
    const pathEdges = new Set((concept.path || []).map(e => `${e[0]}>${e[1]}`));
    const choices = new Set(concept.choices || []);
    this._draw_title(ctx, concept.title || '状态压缩 DP', 'bitmask 表示“哪些城市已经访问过”');

    const compact = this.width < 620;
    const graphW = compact
      ? Math.min(this.width - 90, this.height * 0.38, 250)
      : Math.min(this.width * 0.38, 320, this.height - 150);
    const sideW = compact ? this.width - 56 : 300;
    const gap = compact ? 0 : 50;
    const totalW = graphW + gap + sideW;
    const gx = compact ? (this.width - graphW) / 2 : Math.max(42, (this.width - totalW) / 2);
    const gy = compact ? 86 : Math.max(86, this.height / 2 - graphW / 2 - 12);
    const center = { x: gx + graphW / 2, y: gy + graphW / 2 };
    const radius = graphW * 0.36;
    const pos = new Map();
    cities.forEach((city, idx) => {
      const angle = -Math.PI / 2 + idx * Math.PI * 2 / cities.length;
      pos.set(city, { x: center.x + Math.cos(angle) * radius, y: center.y + Math.sin(angle) * radius });
    });

    ctx.save();
    edges.forEach(([a, b, w], edgeIndex) => {
      const pa = pos.get(a), pb = pos.get(b);
      if (!pa || !pb) return;
      const active = pathEdges.has(`${a}>${b}`) || pathEdges.has(`${b}>${a}`);
      ctx.strokeStyle = active ? 'rgba(251,191,36,0.86)' : 'rgba(148,163,184,0.28)';
      ctx.lineWidth = active ? 3.2 : 1.8;
      ctx.beginPath();
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      ctx.stroke();
      ctx.fillStyle = active ? VIZ_COLORS.pointerText : VIZ_COLORS.textDim;
      ctx.font = '11px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const dx = pb.x - pa.x;
      const dy = pb.y - pa.y;
      const len = Math.max(1, Math.hypot(dx, dy));
      const direction = edgeIndex % 2 === 0 ? -1 : 1;
      const offset = compact ? 12 : 10;
      ctx.fillText(
        String(w),
        (pa.x + pb.x) / 2 - dy / len * offset * direction,
        (pa.y + pb.y) / 2 + dx / len * offset * direction,
      );
    });

    cities.forEach((city, idx) => {
      const p = pos.get(city);
      const mask = String(concept.mask || '').padStart(cities.length, '0');
      const visited = mask[cities.length - 1 - idx] === '1';
      const active = city === concept.city;
      const choice = choices.has(city);
      ctx.fillStyle = active ? VIZ_COLORS.barActive : choice ? 'rgba(251,191,36,0.62)' : visited ? VIZ_COLORS.barSorted : VIZ_COLORS.barDefault;
      ctx.strokeStyle = active ? VIZ_COLORS.pointerText : 'rgba(255,255,255,0.25)';
      ctx.lineWidth = active ? 3 : 2;
      ctx.beginPath();
      ctx.arc(p.x, p.y, active ? (compact ? 23 : 28) : (compact ? 20 : 24), 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = `bold ${compact ? 15 : 18}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(city, p.x, p.y + 1);
    });

    const sideX = compact ? 28 : gx + graphW + gap;
    const sideY = compact ? gy + graphW + 26 : Math.max(86, gy + 4);
    ctx.fillStyle = VIZ_COLORS.text;
    ctx.font = 'bold 14px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText('访问集合 mask', sideX, sideY);
    const mask = String(concept.mask || '').padStart(cities.length, '0');
    const bitGap = compact ? 6 : 8;
    const bitSize = compact
      ? Math.min(34, (sideW - Math.max(0, cities.length - 1) * bitGap) / Math.max(cities.length, 1))
      : 40;
    cities.forEach((city, idx) => {
      const x = sideX + idx * (bitSize + bitGap);
      const bit = mask[cities.length - 1 - idx] || '0';
      ctx.fillStyle = bit === '1' ? VIZ_COLORS.barSorted : 'rgba(51,65,85,0.82)';
      ctx.strokeStyle = city === concept.city ? VIZ_COLORS.pointerText : 'rgba(255,255,255,0.18)';
      ctx.lineWidth = city === concept.city ? 2.4 : 1.2;
      ctx.beginPath();
      ctx.roundRect(x, sideY + 28, bitSize, bitSize, 7);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 16px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(bit, x + bitSize / 2, sideY + 28 + bitSize / 2);
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '11px "JetBrains Mono", monospace';
      ctx.fillText(city, x + bitSize / 2, sideY + (compact ? 66 : 74));
    });

    const tableY = sideY + (compact ? 90 : 116);
    ctx.fillStyle = VIZ_COLORS.text;
    ctx.font = 'bold 14px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('当前 DP 状态', sideX, tableY);
    const table = Array.isArray(concept.table) ? concept.table : [];
    table.slice(0, compact ? 2 : 4).forEach((row, idx) => {
      const y = tableY + 30 + idx * (compact ? 28 : 34);
      ctx.fillStyle = 'rgba(21,25,32,0.86)';
      ctx.strokeStyle = idx === 0 ? 'rgba(251,191,36,0.45)' : 'rgba(73,164,238,0.22)';
      ctx.beginPath();
      ctx.roundRect(sideX, y, sideW - 8, compact ? 22 : 26, 6);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = idx === 0 ? VIZ_COLORS.pointerText : VIZ_COLORS.text;
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      this._fill_text_fit(
        ctx,
        `${row[0]}  @${row[1]}  cost=${row[2]}`,
        sideX + 12,
        y + (compact ? 11 : 13),
        sideW - 32,
        size => `${size}px "JetBrains Mono", monospace`,
        compact ? 10 : 12,
        8,
      );
    });

    this._draw_caption(ctx, '一个 mask 是一个城市集合; DP 在“集合 + 当前城市”之间转移');
    ctx.restore();
  }

  _draw_lz77(ctx, concept) {
    this._draw_title(ctx, 'LZ77 压缩', '用“已经出现过的位置 + 长度”代替重复片段');
    const chars = Array.isArray(concept.text) ? concept.text : [];
    const pos = concept.pos || 0;
    const matchStart = concept.matchStart || 0;
    const matchLen = concept.matchLen || 0;
    const compact = this.width < 620;
    const gap = compact ? 2 : 5;
    const cell = Math.min(46, Math.max(
      compact ? 18 : 30,
      (this.width - (compact ? 28 : 150) - Math.max(0, chars.length - 1) * gap) / Math.max(chars.length, 1),
    ));
    const totalW = chars.length * cell + (chars.length - 1) * gap;
    const x0 = (this.width - totalW) / 2;
    const y = 132;

    ctx.save();
    ctx.textAlign = 'center';
    ctx.font = '12px "JetBrains Mono", monospace';

    const winStart = Math.max(0, pos - 7);
    if (pos > winStart) {
      const wx = x0 + winStart * (cell + gap) - 6;
      const ww = (pos - winStart) * (cell + gap) - gap + 12;
      ctx.fillStyle = 'rgba(73,164,238,0.11)';
      ctx.strokeStyle = 'rgba(73,164,238,0.34)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 5]);
      this._round_rect(ctx, wx, y - 12, ww, cell + 24, 10);
      ctx.fill();
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#93c5fd';
      ctx.fillText('滑动窗口', wx + ww / 2, y - 22);
    }

    chars.forEach((ch, idx) => {
      const x = x0 + idx * (cell + gap);
      const isCurrent = idx === pos;
      const isLookahead = idx >= pos && idx < pos + Math.max(1, matchLen);
      const isMatch = matchLen > 1 && idx >= matchStart && idx < matchStart + matchLen;
      ctx.fillStyle = isCurrent ? '#f59e0b' : isLookahead ? 'rgba(251,191,36,0.62)' : isMatch ? 'rgba(52,211,153,0.56)' : 'rgba(30,41,59,0.92)';
      ctx.strokeStyle = isCurrent ? '#fde68a' : isMatch ? '#86efac' : 'rgba(148,163,184,0.35)';
      ctx.lineWidth = isCurrent ? 2 : 1.2;
      this._round_rect(ctx, x, y, cell, cell, 8);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#f8fafc';
      ctx.font = '700 20px "JetBrains Mono", monospace';
      ctx.fillText(ch, x + cell / 2, y + cell / 2 + 7);
      ctx.fillStyle = '#94a3b8';
      ctx.font = '11px "JetBrains Mono", monospace';
      ctx.fillText(String(idx), x + cell / 2, y + cell + 18);
    });

    if (matchLen > 1) {
      const fromX = x0 + matchStart * (cell + gap) + (matchLen * (cell + gap) - gap) / 2;
      const to_x = x0 + pos * (cell + gap) + (matchLen * (cell + gap) - gap) / 2;
      const arcY = y + cell + 58;
      ctx.strokeStyle = 'rgba(52,211,153,0.82)';
      ctx.lineWidth = 2.5;
      ctx.setLineDash([7, 6]);
      ctx.beginPath();
      ctx.moveTo(to_x, y + cell + 8);
      ctx.quadraticCurveTo((fromX + to_x) / 2, arcY + 30, fromX, y + cell + 8);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#bbf7d0';
      ctx.font = '600 13px "Inter", sans-serif';
      this._fill_text_fit(
        ctx,
        `回退 ${concept.offset || 0} 格, 复制 ${matchLen} 个`,
        (fromX + to_x) / 2,
        compact ? y + cell + 58 : y - 28,
        Math.min(this.width - 36, Math.max(150, Math.abs(fromX - to_x) + 70)),
        size => `600 ${size}px "Inter", sans-serif`,
        13,
        9,
      );
    }

    const tokenY = y + cell + 105;
    ctx.fillStyle = '#cbd5e1';
    ctx.font = '700 14px "Inter", sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('输出 token', x0, tokenY);
    let tx = x0 + 84;
    let tokenRowY = tokenY;
    (Array.isArray(concept.tokens) ? concept.tokens : []).forEach((token, idx) => {
      const w = Math.max(46, String(token).length * 10 + 24);
      if (tx + w > this.width - 18) {
        tx = x0 + (compact ? 0 : 84);
        tokenRowY += 42;
      }
      ctx.fillStyle = String(token).startsWith('(') ? 'rgba(52,211,153,0.22)' : 'rgba(251,191,36,0.22)';
      ctx.strokeStyle = String(token).startsWith('(') ? '#34d399' : '#fbbf24';
      this._round_rect(ctx, tx, tokenRowY - 22, w, 34, 8);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#f8fafc';
      ctx.font = '700 14px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(String(token), tx + w / 2, tokenRowY);
      tx += w + 10;
    });

    this._draw_caption(ctx, concept.phase || '重复片段越长, 回溯引用越省空间');
    ctx.restore();
  }

  _draw_page_rank(ctx, concept) {
    const labels = Array.isArray(concept.labels) ? concept.labels : ['A', 'B', 'C', 'D'];
    const ranks = Array.isArray(concept.ranks) ? concept.ranks : [];
    const activeEdges = new Set((concept.activeEdges || []).map(e => `${e[0]}>${e[1]}`));
    this._draw_title(ctx, 'PageRank', '重要度沿链接流动, 反复迭代后趋于稳定');

    const sideW = 210;
    const gap = 60;
    const radius = Math.min(this.width * 0.20, this.height * 0.27, 155);
    const graphW = radius * 2 + 80;
    const totalW = graphW + gap + sideW;
    const cx = Math.max(radius + 44, (this.width - totalW) / 2 + graphW / 2);
    const cy = this.height / 2;
    const pos = new Map();
    labels.forEach((label, idx) => {
      const angle = -Math.PI / 2 + idx * Math.PI * 2 / labels.length;
      pos.set(label, { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius });
    });

    ctx.save();
    (concept.edges || []).forEach(([from, to]) => {
      const a = pos.get(from);
      const b = pos.get(to);
      if (!a || !b) return;
      const key = `${from}>${to}`;
      const active = activeEdges.has(key);
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const len = Math.max(1, Math.hypot(dx, dy));
      const r1 = 31;
      const r2 = 31;
      this._draw_arrow(
        ctx,
        a.x + dx / len * r1,
        a.y + dy / len * r1,
        b.x - dx / len * r2,
        b.y - dy / len * r2,
        active ? 'rgba(251,191,36,0.86)' : 'rgba(148,163,184,0.32)',
        active ? 'rgba(251,191,36,0.92)' : 'rgba(148,163,184,0.42)',
        active ? 3 : 2
      );
    });

    labels.forEach((label, idx) => {
      const p = pos.get(label);
      const rank = ranks[idx] || 0;
      const nodeR = 28 + rank * 34;
      ctx.fillStyle = `rgba(73,164,238,${0.38 + rank * 1.15})`;
      ctx.strokeStyle = idx === ranks.indexOf(Math.max(...ranks)) ? VIZ_COLORS.pointerText : 'rgba(255,255,255,0.26)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(p.x, p.y, nodeR, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 19px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, p.x, p.y - 6);
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.fillStyle = VIZ_COLORS.text;
      ctx.fillText(rank.toFixed(3), p.x, p.y + 17);
    });

    const sideX = cx + graphW / 2 + gap;
    const sideY = Math.max(82, this.height / 2 - 86);
    ctx.fillStyle = VIZ_COLORS.text;
    ctx.font = 'bold 14px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText('排名变化', sideX, sideY);
    labels.forEach((label, idx) => {
      const y = sideY + 36 + idx * 34;
      const rank = ranks[idx] || 0;
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.fillText(label, sideX, y + 2);
      ctx.fillStyle = 'rgba(255,255,255,0.08)';
      ctx.beginPath();
      ctx.roundRect(sideX + 28, y, 128, 13, 4);
      ctx.fill();
      ctx.fillStyle = idx === ranks.indexOf(Math.max(...ranks)) ? VIZ_COLORS.barSorted : VIZ_COLORS.barDefault;
      ctx.beginPath();
      ctx.roundRect(sideX + 28, y, Math.max(7, rank * 128 / 0.42), 13, 4);
      ctx.fill();
    });

    this._draw_caption(ctx, activeEdges.size ? '黄色箭头表示这一轮正在传递的分数' : '节点越大, PageRank 越高; A 和 C 最终更重要');
    ctx.restore();
  }

  _draw_gradient(ctx, concept) {
    this._draw_title(ctx, '梯度下降', '沿着负梯度, 一步步靠近函数最低点');
    const plotW = Math.min(this.width - 170, 560);
    const plotH = Math.min(this.height - 130, 300);
    const x0 = (this.width - plotW) / 2;
    const y0 = 86;
    const xMin = -0.5;
    const xMax = 4.2;
    const yMax = 12;
    const map_x = x => x0 + (x - xMin) / (xMax - xMin) * plotW;
    const map_y = y => y0 + plotH - y / yMax * plotH;

    ctx.save();
    ctx.strokeStyle = 'rgba(255,255,255,0.16)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x0, y0 + plotH);
    ctx.lineTo(x0 + plotW, y0 + plotH);
    ctx.moveTo(x0, y0);
    ctx.lineTo(x0, y0 + plotH);
    ctx.stroke();

    ctx.strokeStyle = 'rgba(73,164,238,0.78)';
    ctx.lineWidth = 3;
    ctx.beginPath();
    for (let i = 0; i <= 120; i++) {
      const x = xMin + (xMax - xMin) * i / 120;
      const y = (x - 3) * (x - 3);
      const px = map_x(x);
      const py = map_y(y);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.stroke();

    const targetX = map_x(concept.target || 3);
    ctx.strokeStyle = 'rgba(16,185,129,0.55)';
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(targetX, y0);
    ctx.lineTo(targetX, y0 + plotH);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#bbf7d0';
    ctx.font = '12px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText('x=3', targetX, y0 + plotH + 20);

    const paths = Array.isArray(concept.paths) && concept.paths.length
      ? concept.paths
      : [{ label: '当前轨迹', trail: Array.isArray(concept.trail) ? concept.trail : [concept.x || 0], color: '#fbbf24' }];
    paths.forEach((path, pathIdx) => {
      const trail = Array.isArray(path.trail) ? path.trail : [];
      const color = path.color || (pathIdx === 0 ? '#fbbf24' : '#fb7185');
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.6;
      ctx.beginPath();
      trail.forEach((x, idx) => {
        const px = map_x(x);
        const py = map_y((x - 3) * (x - 3));
        if (idx === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.stroke();

      trail.forEach((x, idx) => {
        const px = map_x(x);
        const py = map_y((x - 3) * (x - 3));
        const current = idx === trail.length - 1;
        ctx.fillStyle = current ? color : 'rgba(226,232,240,0.72)';
        ctx.strokeStyle = 'rgba(255,255,255,0.28)';
        ctx.beginPath();
        ctx.arc(px, py, current ? 8 : 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      });
    });

    const sideW = paths.length > 1 ? 190 : 150;
    const sideX = x0 + plotW - sideW;
    const sideY = y0 + 18;
    ctx.fillStyle = 'rgba(21,25,32,0.82)';
    ctx.strokeStyle = 'rgba(73,164,238,0.28)';
    ctx.beginPath();
    ctx.roundRect(sideX, sideY, sideW, 100, 8);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = VIZ_COLORS.text;
    ctx.font = '13px "JetBrains Mono", monospace';
    ctx.textAlign = 'left';
    if (paths.length > 1) {
      paths.forEach((path, idx) => {
        const y = sideY + 24 + idx * 30;
        const trail = Array.isArray(path.trail) ? path.trail : [];
        const last = trail.length ? trail[trail.length - 1] : 0;
        ctx.fillStyle = path.color || '#fbbf24';
        ctx.beginPath();
        ctx.arc(sideX + 18, y - 4, 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = VIZ_COLORS.text;
        ctx.fillText(`${path.label}: ${last.toFixed(2)}`, sideX + 32, y);
      });
    } else {
      ctx.fillText(`x = ${(concept.x || 0).toFixed(3)}`, sideX + 14, sideY + 20);
      ctx.fillText(`grad = ${(concept.gradient || 0).toFixed(3)}`, sideX + 14, sideY + 48);
      ctx.fillText(`loss = ${(concept.loss || 0).toFixed(3)}`, sideX + 14, sideY + 76);
    }

    this._draw_caption(ctx, concept.note || '斜率为负时往右走; 越接近谷底, 步子自然变小');
    ctx.restore();
  }

  _draw_dp_rolling(ctx, concept) {
    const mode = concept.mode || 'rob';
    const values = Array.isArray(concept.values) ? concept.values : [];
    const dp = Array.isArray(concept.dp) ? concept.dp : [];
    const active = new Set(concept.active || []);
    const index = Number(concept.index);
    const compact = this.height < 420 || this.width < 560;
    this._draw_title(ctx, concept.title || '动态规划降维', concept.subtitle || '把整张表压缩成少量变量');

    const itemCount = Math.max(values.length, dp.length, 1);
    const compactPadding = compact ? 96 : 180;
    const cell = Math.max(
      compact ? 20 : 34,
      Math.min(
        compact ? 46 : 54,
        Math.floor((this.width - (compact ? compactPadding : 180)) / itemCount),
      ),
    );
    const totalW = Math.max(values.length, dp.length, 1) * cell;
    const x0 = (this.width - totalW) / 2;
    const topY = Math.max(compact ? 64 : 76, this.height * (compact ? 0.22 : 0.24));
    const dpY = topY + (compact ? cell + 24 : 82);

    const draw_row = (arr, y, label, formatter, activeSet) => {
      ctx.fillStyle = VIZ_COLORS.muted;
      ctx.font = '13px sans-serif';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, x0 - (compact ? 6 : 14), y + cell / 2);
      for (let i = 0; i < arr.length; i++) {
        const x = x0 + i * cell;
        const isActive = activeSet && activeSet.has(i);
        ctx.fillStyle = isActive ? VIZ_COLORS.barActive : 'rgba(74, 143, 212, 0.14)';
        ctx.strokeStyle = isActive ? VIZ_COLORS.pointerText : 'rgba(255,255,255,0.16)';
        ctx.lineWidth = isActive ? 2.5 : 1;
        this._round_rect(ctx, x, y, cell - 6, cell - 6, 8);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = VIZ_COLORS.text;
        ctx.font = '16px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(formatter ? formatter(arr[i], i) : String(arr[i]), x + (cell - 6) / 2, y + (cell - 6) / 2);
        ctx.fillStyle = VIZ_COLORS.muted;
        ctx.font = '11px sans-serif';
        ctx.fillText(String(i), x + (cell - 6) / 2, y + cell + 8);
      }
    };

    if (mode === 'stock') {
      draw_row(values, topY, '价格', v => v, new Set([index]));
      const sideW = 330;
      const sideX = Math.max(40, (this.width - sideW) / 2);
      const y = dpY + 18;
      const metrics = [
        ['最低买入价', concept.minPrice],
        ['今天卖出收益', concept.todayProfit],
        ['历史最好收益', concept.bestProfit],
      ];
      metrics.forEach(([label, value], idx) => {
        const boxX = sideX + idx * 110;
        ctx.fillStyle = idx === 2 ? 'rgba(152,195,121,0.18)' : 'rgba(74,143,212,0.14)';
        ctx.strokeStyle = idx === 2 ? VIZ_COLORS.barSorted : 'rgba(255,255,255,0.16)';
        this._round_rect(ctx, boxX, y, 96, 58, 10);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = '#c9d7ec';
        ctx.font = '600 12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(label, boxX + 48, y + 18);
        ctx.fillStyle = VIZ_COLORS.text;
        ctx.font = '20px sans-serif';
        ctx.fillText(String(value ?? '-'), boxX + 48, y + 42);
      });
    } else {
      const valueLabel = concept.valueLabel || (mode === 'coin' ? '硬币' : mode === 'rob' ? '房屋' : '输入');
      draw_row(values, topY, valueLabel, v => v, new Set([index]));
      draw_row(dp, dpY, 'dp', v => v === null || v === undefined ? '∞' : v, active);
      const labels = Array.isArray(concept.window) ? concept.window : [];
      const boxW = compact ? 104 : 112;
      const gap = compact ? 8 : 12;
      const boxH = compact ? 42 : 58;
      const startX = (this.width - labels.length * boxW - Math.max(0, labels.length - 1) * gap) / 2;
      const boxY = dpY + cell + (compact ? 14 : 42);
      labels.forEach((item, idx) => {
        const x = startX + idx * (boxW + gap);
        ctx.fillStyle = idx === labels.length - 1 ? 'rgba(152,195,121,0.18)' : 'rgba(74,143,212,0.14)';
        ctx.strokeStyle = idx === labels.length - 1 ? VIZ_COLORS.barSorted : 'rgba(255,255,255,0.16)';
        this._round_rect(ctx, x, boxY, boxW, boxH, 10);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = '#c9d7ec';
        ctx.font = `600 ${compact ? 11 : 13}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText(item.label, x + boxW / 2, boxY + (compact ? 13 : 18));
        ctx.fillStyle = VIZ_COLORS.text;
        ctx.font = `${compact ? 15 : 19}px sans-serif`;
        ctx.fillText(String(item.value), x + boxW / 2, boxY + (compact ? 31 : 42));
      });
    }

    ctx.fillStyle = '#d7dae0';
    ctx.font = `${compact ? 12 : 15}px sans-serif`;
    ctx.textAlign = 'center';
    this._fill_text_fit(
      ctx,
      concept.formula || '',
      this.width / 2,
      this.height - (compact ? 8 : 54),
      this.width - 48,
      size => `${size}px sans-serif`,
      compact ? 12 : 15,
      9,
    );
    if (!compact) {
      this._draw_caption(ctx, concept.caption || '降维不是改掉状态转移, 而是只保留下一步还会用到的状态');
    }
  }

  _draw_dp_table(ctx, concept) {
    this._draw_title(ctx, concept.title || '二维 DP 表', concept.subtitle || '当前格只依赖已经填好的格子');
    const grid = Array.isArray(concept.grid) ? concept.grid : [];
    const rows = grid.length;
    const cols = rows ? grid[0].length : 0;
    if (!rows || !cols) return;

    const rowLabels = Array.isArray(concept.rowLabels) ? concept.rowLabels : [];
    const colLabels = Array.isArray(concept.colLabels) ? concept.colLabels : [];
    const active = Array.isArray(concept.active) ? concept.active : [-1, -1];
    const refs = new Set((concept.refs || []).map(([r, c]) => `${r},${c}`));
    const badges = Array.isArray(concept.badges) ? concept.badges : [];

    const labelW = 62;
    const labelH = 26;
    const maxCellW = Math.floor((this.width - 150 - labelW) / cols);
    const maxCellH = Math.floor((this.height - 190 - labelH) / rows);
    const cell = Math.max(24, Math.min(50, maxCellW, maxCellH));
    const gridW = cols * cell;
    const gridH = rows * cell;
    const x0 = (this.width - gridW + labelW / 2) / 2;
    const y0 = Math.max(72, (this.height - gridH) / 2 - 18);

    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    badges.forEach((badge, idx) => {
      const w = Math.max(88, String(badge).length * 10 + 22);
      const x = this.width / 2 - (badges.length * w + (badges.length - 1) * 10) / 2 + idx * (w + 10);
      const y = y0 - 42;
      ctx.fillStyle = 'rgba(96,165,250,0.14)';
      ctx.strokeStyle = 'rgba(96,165,250,0.42)';
      this._round_rect(ctx, x, y, w, 26, 13);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#dbeafe';
      ctx.font = '700 12px "Inter", sans-serif';
      ctx.fillText(String(badge), x + w / 2, y + 13);
    });

    for (let c = 0; c < cols; c++) {
      ctx.fillStyle = '#94a3b8';
      ctx.font = '700 12px "JetBrains Mono", monospace';
      ctx.fillText(colLabels[c] ?? String(c), x0 + c * cell + cell / 2, y0 - 13);
    }
    for (let r = 0; r < rows; r++) {
      ctx.fillStyle = '#94a3b8';
      ctx.font = '700 12px "Inter", sans-serif';
      ctx.fillText(rowLabels[r] ?? String(r), x0 - 34, y0 + r * cell + cell / 2);
    }

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = x0 + c * cell;
        const y = y0 + r * cell;
        const key = `${r},${c}`;
        const isActive = r === active[0] && c === active[1];
        const isRef = refs.has(key);
        const isBoundary = r === 0 || c === 0;
        const value = grid[r][c];

        ctx.fillStyle = isActive
          ? 'rgba(251,191,36,0.34)'
          : isRef
            ? 'rgba(139,92,246,0.32)'
            : isBoundary
              ? 'rgba(59,130,246,0.22)'
              : value === null || value === undefined
                ? 'rgba(15,23,42,0.52)'
                : 'rgba(59,130,246,0.16)';
        ctx.strokeStyle = isActive ? '#fbbf24' : isRef ? '#a78bfa' : 'rgba(148,163,184,0.22)';
        ctx.lineWidth = isActive ? 2.5 : 1;
        this._round_rect(ctx, x + 2, y + 2, cell - 4, cell - 4, 8);
        ctx.fill();
        ctx.stroke();

        const text = value === null || value === undefined ? '' : String(value);
        if (text) {
          ctx.fillStyle = isActive ? '#fef3c7' : '#f8fafc';
          ctx.font = `800 ${Math.min(17, Math.max(13, cell * 0.34))}px "JetBrains Mono", monospace`;
          ctx.fillText(text, x + cell / 2, y + cell / 2);
        }
      }
    }

    const formulaY = y0 + gridH + 34;
    ctx.fillStyle = 'rgba(15,23,42,0.60)';
    ctx.strokeStyle = 'rgba(96,165,250,0.35)';
    const formulaW = Math.min(this.width - 140, Math.max(420, String(concept.formula || '').length * 9));
    this._round_rect(ctx, (this.width - formulaW) / 2, formulaY - 17, formulaW, 34, 10);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#d7dae0';
    ctx.font = '700 14px "JetBrains Mono", monospace';
    this._fill_text_fit(
      ctx,
      concept.formula || '',
      this.width / 2,
      formulaY,
      Math.max(40, formulaW - 24),
      size => `700 ${size}px "JetBrains Mono", monospace`,
      14,
      8,
    );
    ctx.restore();

    if (formulaY + 56 < this.height) {
      this._draw_caption(ctx, concept.caption || '');
    }
  }

  _draw_shortest_path(ctx, concept) {
    const nodes = Array.isArray(concept.nodes) ? concept.nodes : [];
    const edges = Array.isArray(concept.edges) ? concept.edges : [];
    const dist = concept.dist || {};
    const settled = new Set(concept.settled || []);
    const activeEdges = new Set((concept.activeEdges || []).map(e => `${e[0]}-${e[1]}`));
    const pathEdges = new Set((concept.path || []).map(e => `${e[0]}-${e[1]}`));
    const current = concept.current;
    this._draw_title(ctx, concept.title || '最短路搜索', concept.mode === 'astar' ? 'f = g + h, 优先朝目标方向走' : concept.mode === 'spfa' ? '距离变短的点重新入队继续传播' : '每轮确定一个当前最短点');

    const compact = this.width < 620;
    const sideW = compact ? 0 : Math.min(196, Math.max(164, this.width * 0.24));
    const sideGap = compact ? 0 : 28;
    const graphW = compact
      ? Math.max(220, this.width - 80)
      : Math.min(560, Math.max(300, this.width - sideW - sideGap - 84));
    const graphH = compact ? Math.min(420, this.height - 180) : Math.min(340, this.height - 118);
    const left = compact ? (this.width - graphW) / 2 : Math.max(40, (this.width - graphW - sideW - sideGap) / 2);
    const top = Math.max(74, (this.height - graphH) / 2);
    const pos = new Map(nodes.map(n => [n.id, { x: left + n.x * graphW, y: top + n.y * graphH }]));
    const edge_key = (a, b) => activeEdges.has(`${a}-${b}`) || activeEdges.has(`${b}-${a}`) ? 'active'
      : pathEdges.has(`${a}-${b}`) || pathEdges.has(`${b}-${a}`) ? 'path' : 'normal';

    ctx.save();
    edges.forEach(([a, b, w], edgeIndex) => {
      const from = pos.get(a), to = pos.get(b);
      if (!from || !to) return;
      const status = edge_key(a, b);
      ctx.strokeStyle = status === 'active' ? 'rgba(251,191,36,0.90)' : status === 'path' ? 'rgba(16,185,129,0.90)' : 'rgba(148,163,184,0.30)';
      ctx.lineWidth = status === 'normal' ? 2 : 4;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
      const dx = to.x - from.x;
      const dy = to.y - from.y;
      const len = Math.max(1, Math.hypot(dx, dy));
      const direction = edgeIndex % 2 === 0 ? -1 : 1;
      const along = 0.36 + (edgeIndex % 3) * 0.14;
      const offset = compact ? 16 : 13;
      const mx = from.x + dx * along - dy / len * offset * direction;
      const my = from.y + dy * along + dx / len * offset * direction;
      ctx.fillStyle = status === 'normal' ? 'rgba(21,25,32,0.86)' : 'rgba(21,25,32,0.96)';
      ctx.strokeStyle = status === 'active' ? 'rgba(251,191,36,0.65)' : status === 'path' ? 'rgba(16,185,129,0.65)' : 'rgba(148,163,184,0.24)';
      ctx.beginPath();
      ctx.roundRect(mx - 13, my - 10, 26, 20, 6);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = status === 'active' ? VIZ_COLORS.pointerText : status === 'path' ? '#bbf7d0' : VIZ_COLORS.textDim;
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(String(w), mx, my);
    });

    nodes.forEach(node => {
      const p = pos.get(node.id);
      if (!p) return;
      const isCurrent = node.id === current;
      const isSettled = settled.has(node.id) || pathEdges.size && [...pathEdges].some(k => k.includes(node.id));
      ctx.fillStyle = isCurrent ? VIZ_COLORS.barActive : isSettled ? VIZ_COLORS.barSorted : 'rgba(59,130,246,0.92)';
      ctx.strokeStyle = isCurrent ? VIZ_COLORS.pointerText : 'rgba(255,255,255,0.28)';
      ctx.lineWidth = isCurrent ? 3 : 2;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 22, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 16px sans-serif';
      ctx.fillText(node.id, p.x, p.y);
      const d = dist[node.id];
      const text = d === undefined ? '∞' : String(d);
      ctx.fillStyle = 'rgba(21,25,32,0.88)';
      ctx.strokeStyle = 'rgba(73,164,238,0.35)';
      ctx.beginPath();
      ctx.roundRect(p.x - 19, p.y + 28, 38, 20, 6);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#d7dae0';
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.fillText(text, p.x, p.y + 38);
    });

    if (!compact) {
      const sideX = Math.min(this.width - sideW - 24, left + graphW + sideGap);
      const sideY = top + 8;
      ctx.fillStyle = 'rgba(21,25,32,0.72)';
      ctx.strokeStyle = 'rgba(73,164,238,0.22)';
      ctx.beginPath();
      ctx.roundRect(sideX, sideY, sideW, Math.min(270, graphH - 10), 10);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = VIZ_COLORS.text;
      ctx.font = 'bold 14px sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText('当前状态', sideX + 14, sideY + 18);
      ctx.fillStyle = '#c9d7ec';
      ctx.font = '12px sans-serif';
      const queue = concept.queue || concept.open || [];
      const lines = [
        `当前点: ${current || '-'}`,
        `待处理: ${queue.length ? queue.join(' → ') : (concept.frontier || '-')}`,
        `最好值: ${concept.best ?? '-'}`,
        `说明: ${concept.mode === 'astar' ? 'f=g+h' : concept.mode === 'spfa' ? '变短再入队' : '挑最短点'}`,
      ];
      lines.forEach((line, idx) => ctx.fillText(line, sideX + 14, sideY + 48 + idx * 24));
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '11px "JetBrains Mono", monospace';
      const ids = nodes.map(n => n.id);
      ids.forEach((id, idx) => {
        const h = concept.heuristic && concept.heuristic[id] !== undefined ? ` h=${concept.heuristic[id]}` : '';
        const d = dist[id] === undefined ? '∞' : dist[id];
        ctx.fillText(`${id}: dist=${d}${h}`, sideX + 14, sideY + 154 + idx * 18);
      });
    }

    this._draw_caption(ctx, concept.phase || '不断松弛边, 让距离估计越来越接近真实最短路');
    ctx.restore();
  }

  _draw_branch_bound(ctx, concept) {
    const nodes = Array.isArray(concept.nodes) ? concept.nodes : [];
    const edges = Array.isArray(concept.edges) ? concept.edges : [];
    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    this._draw_title(ctx, concept.title || '分支限界', concept.problem || '用界限判断哪些分支还值得继续');

    const compact = this.width < 620;
    const sideW = compact ? 0 : 190;
    const gap = compact ? 0 : 28;
    const treeW = compact ? this.width - 64 : Math.min(this.width - sideW - gap - 90, 600);
    const treeH = compact ? Math.min(this.height - 180, 420) : Math.min(this.height - 128, 350);
    const left = compact ? 32 : Math.max(36, (this.width - treeW - gap - sideW) / 2);
    const top = Math.max(72, (this.height - treeH) / 2);
    const pos = new Map();
    const levels = new Map();
    nodes.forEach(node => {
      const levelKey = Math.round(Number(node.y || 0) * 10);
      if (!levels.has(levelKey)) levels.set(levelKey, []);
      levels.get(levelKey).push(node);
    });
    levels.forEach(levelNodes => {
      levelNodes.sort((a, b) => Number(a.x || 0) - Number(b.x || 0));
      levelNodes.forEach((node, idx) => {
        pos.set(node.id, {
          x: left + (idx + 1) / (levelNodes.length + 1) * treeW,
          y: top + Number(node.y || 0) * treeH,
        });
      });
    });

    ctx.save();
    edges.forEach(([a, b]) => {
      const from = pos.get(a);
      const to = pos.get(b);
      if (!from || !to) return;
      const child = nodeMap.get(b) || {};
      const pruned = child.status === 'pruned';
      const active = child.status === 'current' || child.status === 'best';
      ctx.strokeStyle = pruned ? 'rgba(148,163,184,0.20)' : active ? 'rgba(251,191,36,0.80)' : 'rgba(148,163,184,0.36)';
      ctx.lineWidth = active ? 3 : 2;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y + 20);
      ctx.lineTo(to.x, to.y - 20);
      ctx.stroke();
    });

    nodes.forEach(node => {
      const p = pos.get(node.id);
      if (!p) return;
      const status = node.status || 'live';
      const w = compact
        ? Math.max(46, Math.min(62, String(node.label || '').length * 6 + 16))
        : Math.max(76, Math.min(104, String(node.label || '').length * 9 + 20));
      const h = compact ? 40 : 48;
      let fill = 'rgba(37,99,235,0.78)';
      let stroke = 'rgba(255,255,255,0.22)';
      let alpha = 1;
      if (status === 'current') {
        fill = VIZ_COLORS.barActive;
        stroke = VIZ_COLORS.pointerText;
      } else if (status === 'best') {
        fill = VIZ_COLORS.barSorted;
        stroke = 'rgba(187,247,208,0.78)';
      } else if (status === 'pruned') {
        fill = 'rgba(71,85,105,0.72)';
        stroke = 'rgba(148,163,184,0.22)';
        alpha = 0.62;
      }

      ctx.globalAlpha = alpha;
      ctx.fillStyle = fill;
      ctx.strokeStyle = stroke;
      ctx.lineWidth = status === 'current' || status === 'best' ? 2.5 : 1.3;
      ctx.beginPath();
      ctx.roundRect(p.x - w / 2, p.y - h / 2, w, h, 8);
      ctx.fill();
      ctx.stroke();
      ctx.globalAlpha = 1;

      ctx.fillStyle = '#fff';
      ctx.font = `bold ${compact ? 9 : 12}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      this._fill_text_fit(
        ctx,
        String(node.label || node.id),
        p.x,
        p.y - 8,
        w - 8,
        size => `bold ${size}px "JetBrains Mono", monospace`,
        compact ? 9 : 12,
        compact ? 6 : 9,
      );
      ctx.font = `${compact ? 8 : 11}px "JetBrains Mono", monospace`;
      ctx.fillStyle = status === 'pruned' ? 'rgba(226,232,240,0.62)' : '#dbeafe';
      const boundLabel = concept.boundLabel || (concept.minimize ? 'lb' : 'ub');
      const valueLabel = concept.valueLabel || 'v';
      this._fill_text_fit(
        ctx,
        `${boundLabel}:${node.bound}  ${valueLabel}:${node.value}`,
        p.x,
        p.y + 12,
        w - 8,
        size => `${size}px "JetBrains Mono", monospace`,
        compact ? 8 : 11,
        compact ? 6 : 8,
      );
      if (status === 'pruned') {
        ctx.strokeStyle = 'rgba(248,113,113,0.86)';
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(p.x - w / 2 + 8, p.y - h / 2 + 8);
        ctx.lineTo(p.x + w / 2 - 8, p.y + h / 2 - 8);
        ctx.stroke();
      }
    });

    if (!compact) {
      const sideX = left + treeW + gap;
      const sideY = Math.max(82, top + 4);
      ctx.fillStyle = 'rgba(21,25,32,0.82)';
      ctx.strokeStyle = 'rgba(73,164,238,0.26)';
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.roundRect(sideX, sideY, sideW, Math.min(232, this.height - sideY - 72), 9);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = VIZ_COLORS.text;
      ctx.font = 'bold 14px -apple-system, "PingFang SC", sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.fillText(concept.pruneMode === 'constraint' ? '待探索分支' : '优先队列', sideX + 16, sideY + 14);
      const queue = Array.isArray(concept.queue) ? concept.queue : [];
      const qShown = queue.length ? queue : ['空'];
      qShown.slice(0, 5).forEach((item, idx) => {
        const y = sideY + 42 + idx * 24;
        ctx.fillStyle = idx === 0 && queue.length ? 'rgba(251,191,36,0.22)' : 'rgba(255,255,255,0.06)';
        ctx.beginPath();
        ctx.roundRect(sideX + 14, y - 3, sideW - 28, 20, 5);
        ctx.fill();
        ctx.fillStyle = idx === 0 && queue.length ? VIZ_COLORS.pointerText : VIZ_COLORS.textDim;
        ctx.font = '12px "JetBrains Mono", monospace';
        ctx.fillText(String(item), sideX + 24, y);
      });

      const metrics = Array.isArray(concept.metrics) ? concept.metrics : [];
      const metricY = sideY + 172;
      ctx.fillStyle = VIZ_COLORS.text;
      ctx.font = 'bold 14px -apple-system, "PingFang SC", sans-serif';
      ctx.fillText(concept.pruneMode === 'constraint' ? '剪枝判断' : '界限判断', sideX + 16, metricY);
      metrics.slice(0, 3).forEach((m, idx) => {
        const y = metricY + 30 + idx * 25;
        ctx.fillStyle = VIZ_COLORS.textDim;
        ctx.font = '12px -apple-system, "PingFang SC", sans-serif';
        ctx.fillText(String(m.label), sideX + 18, y);
        ctx.fillStyle = m.label === 'best' ? '#bbf7d0' : VIZ_COLORS.text;
        ctx.font = 'bold 12px "JetBrains Mono", monospace';
        ctx.textAlign = 'right';
        ctx.fillText(String(m.value), sideX + sideW - 18, y);
        ctx.textAlign = 'left';
      });
    }

    const caption = concept.pruneMode === 'constraint'
      ? '违反约束、重复状态、潜力不足: 都可以在进入递归前挡住'
      : concept.minimize
      ? '下界已经不小于当前最短路线, 这条分支就不可能更好'
      : '上界已经不超过当前最好价值, 这条分支就不值得继续';
    this._draw_caption(ctx, caption);
    ctx.restore();
  }

  _draw_flood_fill(ctx, concept) {
    this._draw_title(ctx, concept.title || 'Flood Fill', concept.subtitle || '从起点向四周扩散, 访问过就立刻标记');
    const grid = Array.isArray(concept.grid) ? concept.grid : [];
    const rows = grid.length;
    const cols = rows ? String(grid[0]).length : 0;
    if (!rows || !cols) return;

    const visited = new Set((concept.visited || []).map(([r, c]) => `${r},${c}`));
    const queue = Array.isArray(concept.queue) ? concept.queue : [];
    const queueSet = new Set(queue.map(([r, c]) => `${r},${c}`));
    const active = Array.isArray(concept.active) ? `${concept.active[0]},${concept.active[1]}` : '';
    const cell = Math.max(30, Math.min(50, Math.floor(Math.min((this.width - 320) / cols, (this.height - 210) / rows))));
    const gridW = cols * cell;
    const gridH = rows * cell;
    const sideW = 220;
    const gap = 42;
    const left = Math.max(44, (this.width - gridW - gap - sideW) / 2);
    const top = Math.max(82, (this.height - gridH) / 2 - 22);

    ctx.save();
    for (let r = 0; r < rows; r++) {
      const line = String(grid[r]);
      for (let c = 0; c < cols; c++) {
        const key = `${r},${c}`;
        const isLand = line[c] === '1';
        const isVisited = visited.has(key);
        const isQueued = queueSet.has(key);
        const isActive = key === active;
        const x = left + c * cell;
        const y = top + r * cell;
        let fill = isLand ? 'rgba(34,197,94,0.22)' : 'rgba(59,130,246,0.22)';
        let stroke = 'rgba(148,163,184,0.25)';
        if (isVisited) {
          fill = 'rgba(148,163,184,0.28)';
          stroke = 'rgba(203,213,225,0.36)';
        }
        if (isQueued) {
          fill = 'rgba(251,191,36,0.24)';
          stroke = 'rgba(251,191,36,0.72)';
        }
        if (isActive) {
          fill = 'rgba(96,165,250,0.40)';
          stroke = '#93c5fd';
        }
        ctx.fillStyle = fill;
        ctx.strokeStyle = stroke;
        ctx.lineWidth = isActive ? 3 : 1.4;
        ctx.beginPath();
        ctx.roundRect(x + 3, y + 3, cell - 6, cell - 6, 10);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = isLand ? '#dcfce7' : '#bfdbfe';
        if (isVisited) ctx.fillStyle = '#e2e8f0';
        ctx.font = `800 ${Math.min(22, cell * 0.36)}px "JetBrains Mono", monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(line[c], x + cell / 2, y + cell / 2);
      }
    }

    const sideX = left + gridW + gap;
    const sideY = top + 4;
    ctx.fillStyle = 'rgba(21,25,32,0.82)';
    ctx.strokeStyle = 'rgba(73,164,238,0.28)';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.roundRect(sideX, sideY, sideW, Math.min(246, this.height - sideY - 72), 10);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = VIZ_COLORS.text;
    ctx.font = 'bold 15px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText('BFS 队列', sideX + 16, sideY + 16);
    const shown = queue.length ? queue.map(([r, c]) => `(${r},${c})`) : ['空'];
    shown.slice(0, 6).forEach((item, idx) => {
      const y = sideY + 50 + idx * 25;
      ctx.fillStyle = idx === 0 && queue.length ? 'rgba(251,191,36,0.24)' : 'rgba(255,255,255,0.06)';
      ctx.beginPath();
      ctx.roundRect(sideX + 14, y - 4, sideW - 28, 21, 6);
      ctx.fill();
      ctx.fillStyle = idx === 0 && queue.length ? '#fde68a' : VIZ_COLORS.textDim;
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.fillText(String(item), sideX + 24, y);
    });

    const metricY = sideY + 176;
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
    ctx.fillText('岛屿数量', sideX + 18, metricY);
    ctx.fillStyle = '#bbf7d0';
    ctx.font = 'bold 26px "JetBrains Mono", monospace';
    ctx.fillText(String(concept.count ?? 0), sideX + 18, metricY + 28);
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '12px -apple-system, "PingFang SC", sans-serif';
    ctx.fillText('灰色格子表示已入队标记', sideX + 18, metricY + 66);

    this._draw_caption(ctx, '遇到一块新陆地就 count+1, 再用 BFS 把这整座岛处理掉');
    ctx.restore();
  }

  _draw_tarjan_scc(ctx, concept) {
    this._draw_title(ctx, concept.title || 'Tarjan 强连通分量', concept.subtitle || 'dfn/low + 栈');
    const nodes = Array.isArray(concept.nodes) ? concept.nodes : [];
    const edges = Array.isArray(concept.edges) ? concept.edges : [];
    const activeEdges = new Set((concept.activeEdges || []).map(e => `${e[0]}-${e[1]}`));
    const stack = Array.isArray(concept.stack) ? concept.stack : [];
    const stackSet = new Set(stack);
    const sccs = Array.isArray(concept.sccs) ? concept.sccs : [];
    const sccMap = new Map();
    sccs.forEach((group, idx) => (group || []).forEach(id => sccMap.set(id, idx)));
    const compact = this.width < 620;
    const graphW = compact ? this.width - 76 : Math.min(560, this.width - 320);
    const graphH = compact ? Math.min(360, this.height - 180) : Math.min(300, this.height - 180);
    const left = compact ? 38 : Math.max(46, (this.width - graphW - 250) / 2);
    const top = Math.max(88, (this.height - graphH) / 2 - 8);
    const pos = new Map(nodes.map(n => [n.id, { x: left + n.x * graphW, y: top + n.y * graphH }]));

    ctx.save();
    const draw_arrow = (a, b, active) => {
      const from = pos.get(a);
      const to = pos.get(b);
      if (!from || !to) return;
      const dx = to.x - from.x;
      const dy = to.y - from.y;
      const len = Math.hypot(dx, dy) || 1;
      const ux = dx / len;
      const uy = dy / len;
      const r = 24;
      const sx = from.x + ux * r;
      const sy = from.y + uy * r;
      const ex = to.x - ux * r;
      const ey = to.y - uy * r;
      ctx.strokeStyle = active ? '#fbbf24' : 'rgba(148,163,184,0.34)';
      ctx.fillStyle = ctx.strokeStyle;
      ctx.lineWidth = active ? 3 : 1.7;
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(ex, ey);
      ctx.stroke();
      const ang = Math.atan2(ey - sy, ex - sx);
      ctx.beginPath();
      ctx.moveTo(ex, ey);
      ctx.lineTo(ex - Math.cos(ang) * 9 + Math.sin(ang) * 5, ey - Math.sin(ang) * 9 - Math.cos(ang) * 5);
      ctx.lineTo(ex - Math.cos(ang) * 9 - Math.sin(ang) * 5, ey - Math.sin(ang) * 9 + Math.cos(ang) * 5);
      ctx.closePath();
      ctx.fill();
    };
    edges.forEach(([a, b]) => draw_arrow(a, b, activeEdges.has(`${a}-${b}`)));

    const sccColors = ['#16a34a', '#8b5cf6', '#0891b2'];
    nodes.forEach(node => {
      const p = pos.get(node.id);
      if (!p) return;
      const current = node.id === concept.current;
      const inStack = stackSet.has(node.id);
      const sccIdx = sccMap.get(node.id);
      let fill = inStack ? 'rgba(59,130,246,0.76)' : 'rgba(71,85,105,0.72)';
      if (sccIdx !== undefined) fill = sccColors[sccIdx % sccColors.length];
      if (current) fill = '#f59e0b';
      ctx.fillStyle = fill;
      ctx.strokeStyle = current ? '#fde68a' : 'rgba(255,255,255,0.30)';
      ctx.lineWidth = current ? 3 : 2;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 24, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 16px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(node.id, p.x, p.y - 4);
      const dfn = concept.dfn ? concept.dfn[node.id] : undefined;
      const low = concept.low ? concept.low[node.id] : undefined;
      ctx.fillStyle = '#dbeafe';
      ctx.font = '10px "JetBrains Mono", monospace';
      ctx.fillText(`${dfn || '-'} / ${low || '-'}`, p.x, p.y + 13);
    });

    if (!compact) {
      const sideX = left + graphW + 42;
      const sideY = top;
      ctx.fillStyle = 'rgba(21,25,32,0.82)';
      ctx.strokeStyle = 'rgba(73,164,238,0.28)';
      ctx.beginPath();
      ctx.roundRect(sideX, sideY, 220, 240, 10);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = VIZ_COLORS.text;
      ctx.font = 'bold 15px -apple-system, "PingFang SC", sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText('Tarjan 栈', sideX + 16, sideY + 16);
      const shown = stack.length ? [...stack].reverse() : ['空'];
      shown.slice(0, 7).forEach((id, idx) => {
        const y = sideY + 48 + idx * 24;
        ctx.fillStyle = idx === 0 && stack.length ? 'rgba(251,191,36,0.24)' : 'rgba(255,255,255,0.06)';
        ctx.beginPath();
        ctx.roundRect(sideX + 14, y - 4, 192, 20, 6);
        ctx.fill();
        ctx.fillStyle = idx === 0 && stack.length ? '#fde68a' : VIZ_COLORS.textDim;
        ctx.font = '12px "JetBrains Mono", monospace';
        ctx.fillText(String(id), sideX + 24, y);
      });
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '12px -apple-system, "PingFang SC", sans-serif';
      ctx.fillText('节点内数字: dfn / low', sideX + 16, sideY + 210);
    }
    this._draw_caption(ctx, 'low 回到祖先时说明在同一个环里；low==dfn 时从栈顶弹出一个强连通分量');
    ctx.restore();
  }

  _draw_hungarian_matching(ctx, concept) {
    this._draw_title(ctx, concept.title || '匈牙利算法', concept.subtitle || '通过重新匹配寻找最大配对');
    const leftN = Number(concept.left) || 0;
    const rightN = Number(concept.right) || 0;
    const edges = Array.isArray(concept.edges) ? concept.edges : [];
    const match = Array.isArray(concept.match) ? concept.match : [];
    const tried = new Set(concept.used || concept.tried || []);
    const active = Array.isArray(concept.active) ? concept.active : [-1, -1];
    const halfGap = Math.min(210, this.width * 0.28);
    const leftX = this.width / 2 - halfGap;
    const rightX = this.width / 2 + halfGap;
    const top = 112;
    const gap = Math.min(70, (this.height - 220) / Math.max(leftN - 1, 1));
    const leftPos = Array.from({ length: leftN }, (_, i) => ({ x: leftX, y: top + i * gap }));
    const rightPos = Array.from({ length: rightN }, (_, i) => ({ x: rightX, y: top + i * gap }));
    const is_matched = (l, r) => match[r] === l;

    ctx.save();
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('左侧节点', leftX, 82);
    ctx.fillText('右侧节点', rightX, 82);
    edges.forEach(([l, r]) => {
      const from = leftPos[l];
      const to = rightPos[r];
      if (!from || !to) return;
      const matched = is_matched(l, r);
      const activeEdge = active[0] === l && active[1] === r;
      ctx.strokeStyle = matched ? '#22c55e' : activeEdge ? '#fbbf24' : 'rgba(148,163,184,0.30)';
      ctx.lineWidth = matched ? 3.5 : activeEdge ? 3 : 1.6;
      ctx.beginPath();
      ctx.moveTo(from.x + 22, from.y);
      ctx.bezierCurveTo(from.x + 150, from.y, to.x - 150, to.y, to.x - 22, to.y);
      ctx.stroke();
    });
    const matchedLeft = new Set(match.filter(v => v >= 0));
    const draw_node = (p, label, state) => {
      ctx.fillStyle = state === 'active' ? '#f59e0b' : state === 'matched' ? '#22c55e' : state === 'tried' ? '#8b5cf6' : 'rgba(59,130,246,0.72)';
      ctx.strokeStyle = state === 'active' ? '#fde68a' : 'rgba(255,255,255,0.30)';
      ctx.lineWidth = state === 'active' ? 3 : 2;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 22, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 14px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, p.x, p.y);
    };
    leftPos.forEach((p, i) => draw_node(p, `L${i + 1}`, active[0] === i ? 'active' : matchedLeft.has(i) ? 'matched' : 'normal'));
    rightPos.forEach((p, i) => draw_node(p, `R${i + 1}`, active[1] === i ? 'active' : match[i] >= 0 ? 'matched' : tried.has(i) ? 'tried' : 'normal'));

    const boxW = 280;
    const boxX = (this.width - boxW) / 2;
    const boxY = this.height - 120;
    ctx.fillStyle = 'rgba(21,25,32,0.82)';
    ctx.strokeStyle = 'rgba(73,164,238,0.30)';
    ctx.beginPath();
    ctx.roundRect(boxX, boxY, boxW, 54, 10);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = VIZ_COLORS.text;
    ctx.font = 'bold 14px -apple-system, "PingFang SC", sans-serif';
    ctx.fillText(`当前匹配数: ${concept.count || 0}`, boxX + boxW / 2, boxY + 18);
    const pairs = match.map((l, r) => l >= 0 ? `L${l + 1}-R${r + 1}` : null).filter(Boolean).join('  ');
    ctx.fillStyle = '#bbf7d0';
    ctx.font = '12px "JetBrains Mono", monospace';
    ctx.fillText(pairs || '暂无匹配', boxX + boxW / 2, boxY + 39);
    this._draw_caption(ctx, '右侧节点被占用时, 递归尝试让原来的左侧节点换一个位置');
    ctx.restore();
  }

  _draw_max_flow(ctx, concept) {
    const nodes = Array.isArray(concept.nodes) ? concept.nodes : [];
    const edges = Array.isArray(concept.edges) ? concept.edges : [];
    const activeEdges = new Set((concept.activePath || []).map(e => `${e[0]}>${e[1]}`));
    const cutEdges = new Set((concept.cutEdges || []).map(e => `${e[0]}>${e[1]}`));
    const visited = new Set(concept.visited || []);
    this._draw_title(ctx, concept.title || '最大流', cutEdges.size ? '最大流结束后, 从最终残余图读出最小割' : 'BFS 找增广路, 沿瓶颈容量更新流量');

    const compact = this.width < 620;
    const sideW = compact ? 0 : 200;
    const gap = compact ? 0 : 48;
    const graphW = compact ? this.width - 76 : Math.min(this.width - sideW - gap - 90, 610);
    const graphH = compact ? Math.min(this.height - 180, 420) : Math.min(this.height - 132, 340);
    const left = compact ? 38 : Math.max(38, (this.width - graphW - gap - sideW) / 2);
    const top = Math.max(76, (this.height - graphH) / 2);
    const pos = new Map(nodes.map(n => [n.id, { x: left + n.x * graphW, y: top + n.y * graphH }]));

    ctx.save();
    edges.forEach((edge, edgeIndex) => {
      const from = pos.get(edge.from);
      const to = pos.get(edge.to);
      if (!from || !to) return;
      const key = `${edge.from}>${edge.to}`;
      const active = activeEdges.has(key);
      const cut = cutEdges.has(key);
      const full = edge.remaining <= 0;
      const dx = to.x - from.x;
      const dy = to.y - from.y;
      const len = Math.max(1, Math.hypot(dx, dy));
      const sx = from.x + dx / len * 28;
      const sy = from.y + dy / len * 28;
      const ex = to.x - dx / len * 28;
      const ey = to.y - dy / len * 28;
      this._draw_arrow(
        ctx,
        sx,
        sy,
        ex,
        ey,
        cut ? 'rgba(248,113,113,0.96)' : active ? 'rgba(251,191,36,0.92)' : full ? 'rgba(100,116,139,0.30)' : 'rgba(73,164,238,0.42)',
        cut ? 'rgba(248,113,113,1)' : active ? 'rgba(251,191,36,0.96)' : full ? 'rgba(100,116,139,0.40)' : 'rgba(73,164,238,0.52)',
        cut ? 4.6 : active ? 4 : full ? 1.5 : 2.3
      );

      const mx = (sx + ex) / 2;
      const my = (sy + ey) / 2;
      const labelDirection = edgeIndex % 2 === 0 ? -1 : 1;
      const labelOffset = compact ? 18 : 12;
      const offX = -dy / len * labelOffset * labelDirection;
      const offY = dx / len * labelOffset * labelDirection;
      ctx.fillStyle = cut ? 'rgba(248,113,113,0.20)' : active ? 'rgba(251,191,36,0.18)' : 'rgba(21,25,32,0.86)';
      ctx.strokeStyle = cut ? 'rgba(248,113,113,0.62)' : active ? 'rgba(251,191,36,0.55)' : 'rgba(255,255,255,0.15)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(mx + offX - 25, my + offY - 11, 50, 22, 6);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = cut ? '#fecaca' : full ? 'rgba(226,232,240,0.55)' : active ? VIZ_COLORS.pointerText : VIZ_COLORS.text;
      ctx.font = 'bold 12px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${edge.flow}/${edge.capacity}`, mx + offX, my + offY + 1);
    });

    nodes.forEach(node => {
      const p = pos.get(node.id);
      if (!p) return;
      const isVisited = visited.has(node.id);
      const isTerminal = node.id === 'S' || node.id === 'T';
      ctx.fillStyle = isTerminal ? VIZ_COLORS.barSorted : isVisited ? VIZ_COLORS.barActive : VIZ_COLORS.barDefault;
      ctx.strokeStyle = isVisited ? VIZ_COLORS.pointerText : 'rgba(255,255,255,0.24)';
      ctx.lineWidth = isVisited ? 3 : 2;
      ctx.beginPath();
      ctx.arc(p.x, p.y, isTerminal ? 29 : 25, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 18px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(node.id, p.x, p.y + 1);
    });

    if (!compact) {
      const sideX = left + graphW + gap;
      const sideY = Math.max(92, top + 16);
      ctx.fillStyle = 'rgba(21,25,32,0.84)';
      ctx.strokeStyle = 'rgba(73,164,238,0.30)';
      ctx.beginPath();
      ctx.roundRect(sideX, sideY, sideW, 156, 9);
      ctx.fill();
      ctx.stroke();

      const stats = [
        ['当前最大流', concept.maxFlow || 0],
        ['本轮瓶颈', concept.bottleneck || 0],
        ['BFS访问', (concept.visited || []).join(' → ') || '无'],
        [cutEdges.size ? '最小割边' : '增广路', cutEdges.size
          ? (concept.cutEdges || []).map(e => e.join('→')).join(', ')
          : (concept.activePath || []).map(e => e[0]).concat((concept.activePath || []).length ? [(concept.activePath || []).at(-1)[1]] : []).join(' → ') || '无'],
      ];
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      stats.forEach(([label, value], idx) => {
        const y = sideY + 18 + idx * 32;
        ctx.fillStyle = VIZ_COLORS.textDim;
        ctx.font = '12px -apple-system, "PingFang SC", sans-serif';
        ctx.fillText(label, sideX + 16, y);
        ctx.fillStyle = cutEdges.size && idx === 3 ? '#fecaca' : idx < 2 ? '#bbf7d0' : VIZ_COLORS.text;
        ctx.font = 'bold 12px "JetBrains Mono", monospace';
        ctx.fillText(String(value), sideX + 16, y + 15);
      });
    }

    this._draw_caption(ctx, cutEdges.size
      ? `红色边是从 S 到 T 的最小割, 容量 ${concept.minCut || 0} = 最大流 ${concept.maxFlow || 0}`
      : activeEdges.size ? '黄色路径就是这一轮找到的增广路; 每条边显示 flow/capacity' : '找不到从 S 到 T 的剩余路径时, 最大流就结束');
    ctx.restore();
  }

  _draw_string_match_concept(ctx, concept) {
    const text = Array.from(concept.text || '');
    const pattern = Array.from(concept.pattern || '');
    if (!text.length || !pattern.length) return;
    const modeName = concept.mode === 'kmp' ? 'KMP 匹配' : concept.mode === 'rk' ? 'Rabin-Karp 哈希匹配' : 'BF 暴力匹配';
    const subtitle = concept.mode === 'kmp'
      ? '失配时只移动模式串, 主串指针不回退'
      : concept.mode === 'rk'
        ? '先比较窗口哈希, 命中后再逐字确认'
        : '每个起点都从头尝试, 直到完全匹配';
    this._draw_title(ctx, concept.title || modeName, subtitle);

    const compact = this.width < 560;
    const pad = compact ? 22 : 46;
    const cell = Math.floor((this.width - pad * 2) / Math.max(text.length, pattern.length + Number(concept.offset || 0), 1));
    const s = Math.max(compact ? 16 : 22, Math.min(38, cell));
    const totalW = text.length * s;
    const startX = (this.width - totalW) / 2;
    const topY = concept.mode === 'rk'
      ? Math.max(132, this.height / 2 - s - 42)
      : Math.max(96, this.height / 2 - s - 52);
    const gap = 68;
    const patternY = topY + s + gap;
    const offset = Math.max(0, Math.min(text.length - 1, Number(concept.offset) || 0));
    const j = Number.isFinite(Number(concept.j)) ? Number(concept.j) : 0;
    const compareIdx = offset + Math.max(0, j);
    const patternX = startX + offset * s;

    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    text.forEach((ch, idx) => {
      const inWindow = idx >= offset && idx < offset + pattern.length;
      const active = idx === compareIdx && !concept.windowOnly;
      const color = active ? 'rgba(245,158,11,0.96)' : inWindow ? 'rgba(37,99,235,0.9)' : 'rgba(51,65,85,0.82)';
      this._draw_tile_like(ctx, startX + idx * s, topY, s, ch, color, active);
    });
    pattern.forEach((ch, idx) => {
      const textIdx = offset + idx;
      const matched = concept.success || (idx < j && text[textIdx] === ch);
      const active = idx === j && !concept.windowOnly;
      const color = matched ? 'rgba(16,185,129,0.94)' : active ? 'rgba(139,92,246,0.96)' : 'rgba(14,165,233,0.88)';
      this._draw_tile_like(ctx, patternX + idx * s, patternY, s, ch, color, active);
    });

    const compareLimit = concept.windowOnly ? -1 : Math.min(Math.max(j, 0), pattern.length - 1);
    for (let idx = 0; idx <= compareLimit; idx++) {
      const textIdx = offset + idx;
      if (textIdx < 0 || textIdx >= text.length) continue;
      const x = startX + textIdx * s + s / 2;
      const y1 = topY + s + 5;
      const y2 = patternY - 5;
      if (concept.mismatch && idx === j) {
        ctx.strokeStyle = VIZ_COLORS.barSwap;
        ctx.fillStyle = VIZ_COLORS.barSwap;
        ctx.lineWidth = 2.4;
        ctx.beginPath();
        ctx.moveTo(x, y1);
        ctx.bezierCurveTo(x + 18, y1 + 12, x + 18, y2 - 12, x, y2);
        ctx.stroke();
        ctx.font = 'bold 22px -apple-system, "PingFang SC", sans-serif';
        ctx.fillText('≠', x + 24, (y1 + y2) / 2);
      } else if (text[textIdx] === pattern[idx]) {
        ctx.strokeStyle = 'rgba(148,163,184,0.62)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x, y1);
        ctx.lineTo(x, y2);
        ctx.stroke();
      }
    }

    ctx.fillStyle = VIZ_COLORS.pointerText;
    ctx.font = 'bold 13px "JetBrains Mono", monospace';
    if (!concept.windowOnly && compareIdx >= 0 && compareIdx < text.length) {
      ctx.fillText(`i=${compareIdx}`, startX + compareIdx * s + s / 2, topY - 16);
    }
    if (!concept.windowOnly && j >= 0 && j < pattern.length) {
      ctx.fillText(`j=${j}`, patternX + j * s + s / 2, patternY + s + 18);
    }
    ctx.fillText(`offset=${offset}`, patternX + pattern.length * s / 2, patternY + s + 40);

    if (concept.jumpTo !== undefined) {
      const fromX = patternX + Math.max(0, j) * s + s / 2;
      const rawToX = startX + (offset + Number(concept.jumpTo || 0)) * s + s / 2;
      const to_x = Math.max(startX + s / 2, Math.min(startX + totalW - s / 2, rawToX));
      const y = patternY + s + 28;
      ctx.strokeStyle = 'rgba(251,191,36,0.78)';
      ctx.lineWidth = 2.2;
      ctx.beginPath();
      ctx.moveTo(fromX, y);
      ctx.quadraticCurveTo((fromX + to_x) / 2, y + 28, to_x, y);
      ctx.stroke();
      ctx.fillStyle = '#fde68a';
      const jumpLabelX = Math.max(100, Math.min(this.width - 100, (fromX + to_x) / 2));
      this._fill_text_fit(
        ctx,
        '查 next 后跳到可复用位置',
        jumpLabelX,
        y + 20,
        Math.min(210, this.width - 36),
        size => `${size}px -apple-system, "PingFang SC", sans-serif`,
        12,
        9,
      );
    }

    if (concept.mode === 'rk') {
      const boxW = 230;
      const boxH = 58;
      const boxX = (this.width - boxW) / 2;
      const boxY = topY - 68;
      ctx.fillStyle = 'rgba(15,23,42,0.78)';
      ctx.strokeStyle = concept.hashText === concept.hashPattern ? 'rgba(34,197,94,0.62)' : 'rgba(96,165,250,0.45)';
      ctx.beginPath();
      ctx.roundRect(boxX, boxY, boxW, boxH, 9);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = VIZ_COLORS.text;
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.fillText(`pattern hash = ${concept.hashPattern ?? '-'}`, this.width / 2, boxY + 20);
      ctx.fillText(`window hash  = ${concept.hashText ?? '-'}`, this.width / 2, boxY + 40);
    }

    this._draw_caption(ctx, concept.caption || '上面是主串 text, 下面是模式串 pattern');
    ctx.restore();
  }

  _draw_kmp_table(ctx, concept) {
    const pattern = Array.from(concept.pattern || '');
    const values = Array.isArray(concept.values) ? concept.values : [];
    const n = Math.max(pattern.length, values.length);
    if (!n) return;
    this._draw_title(ctx, concept.title || 'KMP 辅助数组', concept.optimized ? '跳过会重复失配的位置' : '失配后直接查表回退');

    const cell = Math.min(42, Math.floor((this.width - 120) / n));
    const s = Math.max(24, cell);
    const totalW = n * s;
    const startX = (this.width - totalW) / 2;
    const topY = this.height / 2 - s - 30;
    const tableY = topY + s + 36;
    const built = Math.max(0, Number(concept.built) || 0);
    const active = Number(concept.active);

    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    for (let i = 0; i < n; i++) {
      const x = startX + i * s;
      const isActive = i === active;
      this._draw_tile_like(ctx, x, topY, s, pattern[i] || '', isActive ? VIZ_COLORS.barCompare : 'rgba(37,99,235,0.92)', isActive);
      const ready = i < built;
      const value = ready ? String(values[i]) : '';
      this._draw_tile_like(ctx, x, tableY, s, value, ready ? (isActive ? VIZ_COLORS.barActive : 'rgba(16,185,129,0.88)') : 'rgba(51,65,85,0.76)', isActive);
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '11px "JetBrains Mono", monospace';
      ctx.fillText(String(i), x + s / 2, topY - 14);
    }

    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText('pattern', startX - 14, topY + s / 2);
    ctx.fillText(concept.tableName || 'next', startX - 14, tableY + s / 2);

    if (active >= 0 && active < n) {
      ctx.fillStyle = VIZ_COLORS.pointerText;
      ctx.font = 'bold 13px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`i=${active}`, startX + active * s + s / 2, topY - 34);
      const value = values[active];
      if (value !== undefined) {
        ctx.strokeStyle = 'rgba(251,191,36,0.72)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        const x1 = startX + active * s + s / 2;
        const x2 = startX + Math.max(0, value) * s + s / 2;
        const y = tableY + s + 16;
        ctx.moveTo(x1, y);
        ctx.quadraticCurveTo((x1 + x2) / 2, y + 28, x2, y);
        ctx.stroke();
      }
    }

    this._draw_caption(ctx, concept.optimized ? 'nextval 会跳过“退过去还是同字符”的位置' : 'next[i] 告诉 KMP: 失配后 j 该退到哪里');
    ctx.restore();
  }

  _draw_tile_like(ctx, x, y, s, text, color, active = false) {
    ctx.save();
    ctx.fillStyle = color;
    ctx.strokeStyle = active ? VIZ_COLORS.pointerText : 'rgba(255,255,255,0.14)';
    ctx.lineWidth = active ? 2.2 : 1.1;
    ctx.shadowColor = 'rgba(0,0,0,0.22)';
    ctx.shadowBlur = 7;
    ctx.shadowOffsetY = 3;
    ctx.beginPath();
    ctx.roundRect(x, y, s, s, 6);
    ctx.fill();
    ctx.stroke();
    ctx.shadowColor = 'transparent';
    if (text !== '') {
      ctx.fillStyle = '#fff';
      ctx.font = `bold ${Math.floor(s * 0.44)}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, x + s / 2, y + s / 2 + 1);
    }
    ctx.restore();
  }

  _draw_trie_like(ctx, concept, showFail) {
    const nodes = Array.isArray(concept.nodes) ? concept.nodes : [];
    const edges = Array.isArray(concept.edges) ? concept.edges : [];
    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    const activeEdges = new Set((concept.activeEdges || []).map(e => `${e[0]}>${e[1]}`));
    const activePath = new Set(concept.activePath || []);
    const activeFails = new Set((concept.activeFails || []).map(e => `${e[0]}>${e[1]}`));
    this._draw_title(ctx, concept.title || (showFail ? 'AC 自动机' : 'Trie 字典树'), showFail ? 'Trie 上加 fail 指针, 一次扫描多个模式串' : '相同前缀共用同一条路径');

    const drawW = Math.min(this.width - 110, 620);
    const drawH = Math.min(this.height - 126, 360);
    const left = (this.width - drawW) / 2;
    const top = Math.max(70, (this.height - drawH) / 2);
    const pos = new Map(nodes.map(n => [n.id, { x: left + n.x * drawW, y: top + n.y * drawH }]));

    ctx.save();
    edges.forEach(([a, b]) => {
      const from = pos.get(a), to = pos.get(b);
      if (!from || !to) return;
      const active = activeEdges.has(`${a}>${b}`) || activePath.has(b);
      ctx.strokeStyle = active ? VIZ_COLORS.barCompare : 'rgba(148,163,184,0.36)';
      ctx.lineWidth = active ? 3 : 2;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    });

    if (showFail) {
      (concept.failEdges || []).forEach(([a, b]) => {
        const from = pos.get(a), to = pos.get(b);
        if (!from || !to) return;
        const active = activeFails.has(`${a}>${b}`);
        ctx.strokeStyle = active ? 'rgba(251,191,36,0.90)' : 'rgba(251,191,36,0.28)';
        ctx.lineWidth = active ? 2.6 : 1.6;
        ctx.setLineDash([6, 5]);
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.quadraticCurveTo((from.x + to.x) / 2, Math.min(from.y, to.y) - 38, to.x, to.y);
        ctx.stroke();
        ctx.setLineDash([]);
      });
    }

    nodes.forEach(node => {
      const p = pos.get(node.id);
      const active = activePath.has(node.id);
      const r = node.id === 'root' ? 24 : 20;
      ctx.fillStyle = node.end ? VIZ_COLORS.barSorted : active ? VIZ_COLORS.barActive : VIZ_COLORS.barDefault;
      ctx.strokeStyle = active ? VIZ_COLORS.pointerText : 'rgba(255,255,255,0.24)';
      ctx.lineWidth = active ? 3 : 2;
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = `bold ${node.id === 'root' ? 12 : 14}px "JetBrains Mono", monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(node.id === 'root' ? 'root' : String(node.label).replace('*', ''), p.x, p.y);
      if (node.end) {
        ctx.fillStyle = '#bbf7d0';
        ctx.font = '11px "JetBrains Mono", monospace';
        ctx.fillText('end', p.x, p.y + r + 14);
      }
    });

    const status = showFail
      ? `text: ${concept.text || ''}    total: ${concept.total || 0}`
      : `word: ${concept.word || ''}`;
    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(status, this.width / 2, top + drawH + 24);
    this._draw_caption(ctx, showFail ? '实线是 Trie 边, 虚线是 fail 指针' : '路径不断表示前缀存在; end 标记表示完整单词存在');
    ctx.restore();
  }

  _draw_arrow(ctx, x1, y1, x2, y2, stroke = 'rgba(148,163,184,0.45)', fill = 'rgba(148,163,184,0.55)', width = 2) {
    const ang = Math.atan2(y2 - y1, x2 - x1);
    ctx.save();
    ctx.strokeStyle = stroke;
    ctx.fillStyle = fill;
    ctx.lineWidth = width;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(x2 - Math.cos(ang) * 10 + Math.sin(ang) * 5, y2 - Math.sin(ang) * 10 - Math.cos(ang) * 5);
    ctx.lineTo(x2 - Math.cos(ang) * 10 - Math.sin(ang) * 5, y2 - Math.sin(ang) * 10 + Math.cos(ang) * 5);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  _draw_caption(ctx, text) {
    ctx.save();
    const maxW = Math.max(120, this.width - 32);
    const w = Math.min(maxW, Math.max(Math.min(220, maxW), text.length * 12));
    const x = (this.width - w) / 2;
    const h = 26;
    const y = this.height - 32;
    ctx.fillStyle = 'rgba(21,25,32,0.84)';
    ctx.strokeStyle = 'rgba(73,164,238,0.28)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, 7);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = VIZ_COLORS.text;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    this._fill_text_fit(
      ctx,
      text,
      this.width / 2,
      y + h / 2,
      w - 20,
      size => `${size}px -apple-system, "PingFang SC", sans-serif`,
      12,
      9,
    );
    ctx.restore();
  }

  _draw_arrow_head(ctx, x1, y1, x2, y2, color) {
    const angle = Math.atan2(y2 - y1, x2 - x1);
    const r = 27;
    const x = x2 - Math.cos(angle) * r;
    const y = y2 - Math.sin(angle) * r;
    ctx.save();
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x - Math.cos(angle - Math.PI / 6) * 9, y - Math.sin(angle - Math.PI / 6) * 9);
    ctx.lineTo(x - Math.cos(angle + Math.PI / 6) * 9, y - Math.sin(angle + Math.PI / 6) * 9);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  _draw_union_find(ctx, concept) {
    const nodes = Array.isArray(concept.nodes) ? concept.nodes : [];
    const active = new Set(concept.active || []);
    const path = new Set(concept.path || []);
    const pos = new Map(nodes.map(n => [n.id, { x: n.x * this.width, y: 78 + n.y * (this.height - 150) }]));
    this._draw_title(ctx, concept.title || '并查集', '箭头指向 parent; 沿箭头找到最终代表');

    ctx.save();
    nodes.forEach(n => {
      if (!n.parent || n.parent === n.id) return;
      const a = pos.get(n.id), b = pos.get(n.parent);
      if (!a || !b) return;
      const hot = path.has(n.id) || path.has(n.parent);
      ctx.strokeStyle = hot ? 'rgba(251,191,36,0.9)' : 'rgba(148,163,184,0.42)';
      ctx.lineWidth = hot ? 3 : 1.8;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
      this._draw_arrow_head(ctx, a.x, a.y, b.x, b.y, hot ? 'rgba(251,191,36,0.9)' : 'rgba(148,163,184,0.42)');
    });

    nodes.forEach(n => {
      const p = pos.get(n.id);
      const isRoot = !n.parent || n.parent === n.id;
      const hot = active.has(n.id) || path.has(n.id);
      ctx.fillStyle = isRoot ? 'rgba(16,185,129,0.92)' : hot ? 'rgba(245,158,11,0.95)' : 'rgba(59,130,246,0.88)';
      ctx.strokeStyle = hot ? '#fde68a' : 'rgba(255,255,255,0.18)';
      ctx.lineWidth = hot ? 2.4 : 1.2;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 25, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 16px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(n.id, p.x, p.y);
      if (isRoot) {
        ctx.fillStyle = '#bbf7d0';
        ctx.font = '12px -apple-system, "PingFang SC", sans-serif';
        ctx.fillText('代表', p.x, p.y + 39);
      }
    });
    this._draw_caption(ctx, concept.caption || '并查集只保存 parent 指针, 判断同组时比较最终代表');
    ctx.restore();
  }

  _draw_red_black_tree_concept(ctx, concept) {
    const nodes = Array.isArray(concept.nodes) ? concept.nodes : [];
    const edges = Array.isArray(concept.edges) ? concept.edges : [];
    const active = new Set(concept.active || []);
    const conflict = new Set(concept.conflict || []);
    const pos = new Map(nodes.map(n => [n.id, { x: n.x * this.width, y: 74 + n.y * (this.height - 145) }]));
    this._draw_title(ctx, concept.title || '红黑树', concept.blackHeight || '红节点不能连红节点, 每条路径黑色数量一致');

    ctx.save();
    edges.forEach(([u, v]) => {
      const a = pos.get(u), b = pos.get(v);
      if (!a || !b) return;
      const hot = conflict.has(u) && conflict.has(v);
      ctx.strokeStyle = hot ? 'rgba(248,113,113,0.92)' : 'rgba(148,163,184,0.42)';
      ctx.lineWidth = hot ? 4 : 2;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y + 22);
      ctx.lineTo(b.x, b.y - 22);
      ctx.stroke();
    });

    nodes.forEach(n => {
      const p = pos.get(n.id);
      if (!p) return;
      const isRed = n.color === 'red';
      const hot = active.has(n.id);
      const bad = conflict.has(n.id);
      const fill = isRed ? 'rgba(220,38,38,0.94)' : 'rgba(15,23,42,0.96)';
      ctx.shadowColor = hot ? 'rgba(251,191,36,0.45)' : 'transparent';
      ctx.shadowBlur = hot ? 16 : 0;
      ctx.fillStyle = fill;
      ctx.strokeStyle = bad ? '#fecaca' : hot ? '#fde68a' : isRed ? 'rgba(254,202,202,0.45)' : 'rgba(226,232,240,0.34)';
      ctx.lineWidth = bad ? 3.4 : hot ? 2.8 : 1.4;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 26, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 16px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(n.label, p.x, p.y);
      ctx.font = '12px -apple-system, "PingFang SC", sans-serif';
      ctx.fillStyle = isRed ? '#fecaca' : '#cbd5e1';
      ctx.fillText(isRed ? '红' : '黑', p.x, p.y + 42);
    });

    const legendY = this.height - 70;
    [
      ['黑节点: 负责黑高平衡', 'rgba(15,23,42,0.96)'],
      ['红节点: 增加灵活性', 'rgba(220,38,38,0.94)'],
    ].forEach(([label, color], idx) => {
      const x = this.width / 2 - 175 + idx * 210;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, legendY, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#cbd5e1';
      ctx.font = '12px -apple-system, "PingFang SC", sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(label, x + 14, legendY + 1);
    });

    this._draw_caption(ctx, concept.caption || '红黑树用局部旋转和重新染色, 换来长期稳定的 O(log n)。');
    ctx.restore();
  }

  _draw_segment_tree_concept(ctx, concept) {
    const nodes = Array.isArray(concept.nodes) ? concept.nodes : [];
    const edges = Array.isArray(concept.edges) ? concept.edges : [];
    const visible = new Set(concept.visible || nodes.map(n => n.id));
    const active = new Set(concept.active || []);
    const covered = new Set(concept.covered || []);
    const pos = new Map(nodes.map(n => [n.id, { x: n.x * this.width, y: 74 + n.y * (this.height - 145) }]));
    this._draw_title(ctx, concept.title || '线段树', concept.query ? `当前查询区间 [${concept.query[0]}, ${concept.query[1]}]` : '每个节点都是一个已经算好的区间');

    ctx.save();
    edges.forEach(([u, v]) => {
      if (!visible.has(u) || !visible.has(v)) return;
      const a = pos.get(u), b = pos.get(v);
      ctx.strokeStyle = 'rgba(148,163,184,0.36)';
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y + 20);
      ctx.lineTo(b.x, b.y - 20);
      ctx.stroke();
    });
    nodes.forEach(n => {
      if (!visible.has(n.id)) return;
      const p = pos.get(n.id);
      const hot = active.has(n.id);
      const keep = covered.has(n.id);
      const w = 78, h = 42;
      ctx.fillStyle = keep ? 'rgba(16,185,129,0.9)' : hot ? 'rgba(245,158,11,0.95)' : 'rgba(37,99,235,0.86)';
      ctx.strokeStyle = hot || keep ? '#fde68a' : 'rgba(255,255,255,0.14)';
      ctx.lineWidth = hot || keep ? 2.2 : 1.1;
      ctx.beginPath();
      ctx.roundRect(p.x - w / 2, p.y - h / 2, w, h, 8);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#fff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.font = 'bold 12px "JetBrains Mono", monospace';
      ctx.fillText(n.label, p.x, p.y - 7);
      ctx.font = 'bold 13px "JetBrains Mono", monospace';
      ctx.fillText(String(n.value), p.x, p.y + 10);
    });
    this._draw_caption(ctx, concept.caption || '查询时遇到完整覆盖的节点就直接拿值, 不再往下拆');
    ctx.restore();
  }

  _draw_fenwick_concept(ctx, concept) {
    const values = Array.isArray(concept.values) ? concept.values : [];
    const ranges = Array.isArray(concept.ranges) ? concept.ranges : [];
    const active = new Set(concept.active || []);
    this._draw_title(ctx, concept.title || '树状数组', 'c[i] 管理 [i-lowbit(i)+1, i] 这一段');
    if (!values.length) return;

    ctx.save();
    const n = values.length;
    const s = Math.min(52, Math.floor((this.width - 110) / n));
    const startX = (this.width - n * s) / 2;
    const baseY = this.height / 2 - 10;
    for (let i = 0; i < n; i++) {
      const x = startX + i * s;
      const hot = active.has(i);
      this._draw_tile_like(ctx, x, baseY, s, `c${i + 1}`, hot ? 'rgba(245,158,11,0.95)' : 'rgba(37,99,235,0.88)', hot);
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '11px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`[${ranges[i]?.[0] || i + 1},${ranges[i]?.[1] || i + 1}]`, x + s / 2, baseY + s + 18);
    }
    [...active].forEach((idx, order) => {
      const range = ranges[idx] || [idx + 1, idx + 1];
      const x1 = startX + (range[0] - 1) * s + 5;
      const x2 = startX + range[1] * s - 5;
      const y = baseY - 22 - order * 16;
      ctx.strokeStyle = 'rgba(34,197,94,0.78)';
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(x1, y);
      ctx.lineTo(x2, y);
      ctx.stroke();
    });
    this._draw_caption(ctx, concept.caption || '树状数组把前缀和拆成少数几个已经维护好的区间');
    ctx.restore();
  }

  _draw_bit_visual(ctx, concept) {
    this._draw_title(ctx, concept.title || '位运算', '把十进制数字拆开看每一个二进制位');
    const rows = Array.isArray(concept.rows) && concept.rows.length
      ? concept.rows
      : [['bits', String(concept.bits || '')]];
    const active = new Set(concept.active || []);
    const labels = concept.labels || [];
    const maxLen = Math.max(...rows.map(r => String(r[1] || '').length), 1);
    const cell = Math.min(46, Math.floor((this.width - 180) / maxLen));
    const s = Math.max(28, cell);
    const totalW = maxLen * s;
    const labelW = 82;
    const startX = (this.width - totalW) / 2 + 32;
    const startY = Math.max(100, this.height / 2 - rows.length * (s + 14) / 2);

    ctx.save();
    rows.forEach((row, rIdx) => {
      const [name, bitString] = row;
      const bits = Array.from(String(bitString || '').padStart(maxLen, '0'));
      const y = startY + rIdx * (s + 14);
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = 'bold 13px "JetBrains Mono", monospace';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillText(String(name), startX - 16, y + s / 2);
      bits.forEach((bit, idx) => {
        const hot = active.has(idx);
        const one = bit === '1';
        const color = hot ? 'rgba(245,158,11,0.96)' : one ? 'rgba(34,197,94,0.9)' : 'rgba(51,65,85,0.86)';
        this._draw_tile_like(ctx, startX + idx * s, y, s, bit, color, hot);
      });
    });
    if (labels.length) {
      ctx.fillStyle = VIZ_COLORS.textDim;
      ctx.font = '11px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      Array.from(labels).forEach((label, idx) => {
        ctx.fillText(String(label), startX + idx * s + s / 2, startY - 14);
      });
    }
    this._draw_caption(ctx, concept.caption || '黄色表示当前正在观察或改变的位');
    ctx.restore();
  }

  _draw_unknown(ctx) {
    this._draw_title(ctx, '概念动画', '这个演示还没有专用渲染器');
  }
}

// ============================================================
// 标量状态渲染器 — 适合数学、位运算、递归计数等无结构快照算法
// ============================================================

class ScalarStateRenderer extends BaseRenderer {
  constructor(canvasId, options = {}) {
    super(canvasId);
    this.options = {
      maxItems: 10,
      cardMinWidth: 110,
      cardHeight: 58,
      gap: 10,
      ...options,
    };
  }

  _format_value(value) {
    if (value === null) return 'NULL';
    if (value === 2147483647) return 'INF';
    if (value === -2147483648) return '-INF';
    if (typeof value === 'number') {
      if (!Number.isFinite(value)) return String(value);
      if (Math.abs(value) >= 100000) return value.toExponential(2);
      return Number.isInteger(value) ? String(value) : value.toPrecision(4);
    }
    return String(value);
  }

  _pick_scalars(vars, classes) {
    const entries = Object.entries(vars).filter(([name, value]) => {
      if (Array.isArray(value)) return false;
      const info = classes[name] || {};
      return info.category !== 'hidden';
    });
    entries.sort((a, b) => {
      const ac = (classes[a[0]] || {}).category === 'primary' ? 0 : 1;
      const bc = (classes[b[0]] || {}).category === 'primary' ? 0 : 1;
      if (ac !== bc) return ac - bc;
      if (a[0] === '_return') return 1;
      if (b[0] === '_return') return -1;
      return a[0].localeCompare(b[0]);
    });
    return entries.slice(0, this.options.maxItems);
  }

  _ellipsize(ctx, text, maxWidth) {
    const value = String(text);
    if (ctx.measureText(value).width <= maxWidth) return value;

    const chars = Array.from(value);
    const ellipsis = '…';
    if (ctx.measureText(ellipsis).width > maxWidth) return '';

    let low = 0;
    let high = chars.length;
    while (low < high) {
      const mid = Math.ceil((low + high) / 2);
      const candidate = chars.slice(0, mid).join('') + ellipsis;
      if (ctx.measureText(candidate).width <= maxWidth) low = mid;
      else high = mid - 1;
    }
    return chars.slice(0, low).join('') + ellipsis;
  }

  _wrap_value(ctx, text, maxWidth) {
    const chars = Array.from(String(text));
    const lines = [];
    let current = '';

    chars.forEach(char => {
      const candidate = current + char;
      if (current && ctx.measureText(candidate).width > maxWidth) {
        lines.push(current);
        current = char;
      } else {
        current = candidate;
      }
    });

    if (current) lines.push(current);
    return lines;
  }

  _draw_value(ctx, value, x, y, cardW, cardH) {
    const text = this._format_value(value);
    const maxWidth = Math.max(1, cardW - 24);
    const monoFont = '"JetBrains Mono", "PingFang SC", monospace';

    ctx.font = `bold 20px ${monoFont}`;
    ctx.textBaseline = 'bottom';
    if (ctx.measureText(text).width <= maxWidth) {
      ctx.fillText(text, x + 12, y + cardH - 9);
      return;
    }

    // 长文本保留两行语义；最后一行仍放不下时再按真实像素宽度省略。
    let fontSize = 14;
    let lines = [];
    for (const candidateSize of [14, 13, 12]) {
      ctx.font = `bold ${candidateSize}px ${monoFont}`;
      fontSize = candidateSize;
      lines = this._wrap_value(ctx, text, maxWidth);
      if (lines.length <= 2) break;
    }
    if (lines.length > 2) {
      lines = [
        lines[0],
        this._ellipsize(ctx, lines.slice(1).join(''), maxWidth),
      ];
    }

    ctx.font = `bold ${fontSize}px ${monoFont}`;
    ctx.textBaseline = 'top';
    const lineHeight = fontSize + 2;
    const blockHeight = lines.length * fontSize + Math.max(0, lines.length - 1) * 2;
    const firstLineY = y + 25 + Math.max(0, (cardH - 28 - blockHeight) / 2);
    lines.forEach((line, idx) => {
      ctx.fillText(line, x + 12, firstLineY + idx * lineHeight);
    });
  }

  render(stepData, prevStepData) {
    this.clear();
    const vars = stepData.vars || {};
    const classes = stepData.var_classes || {};
    const items = this._pick_scalars(vars, classes);
    const { ctx, width, height } = this;
    ctx.save();
    ctx.fillStyle = 'rgba(30,35,54,0.9)';
    ctx.fillRect(0, 0, width, height);

    ctx.fillStyle = VIZ_COLORS.textDim;
    ctx.font = '13px -apple-system, "PingFang SC", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText('关键变量', width / 2, 18);

    if (items.length === 0) {
      ctx.fillStyle = VIZ_COLORS.text;
      ctx.font = 'bold 16px -apple-system, "PingFang SC", sans-serif';
      ctx.fillText('暂无可显示变量', width / 2, height / 2 - 8);
      ctx.restore();
      return;
    }

    const cols = Math.max(1, Math.min(
      4,
      Math.floor((width - 48 + this.options.gap) / (this.options.cardMinWidth + this.options.gap)),
    ));
    const cardW = Math.min(170, (width - 48 - (cols - 1) * this.options.gap) / cols);
    const rows = Math.ceil(items.length / cols);
    const totalH = rows * this.options.cardHeight + (rows - 1) * this.options.gap;
    const startX = (width - (cols * cardW + (cols - 1) * this.options.gap)) / 2;
    const startY = Math.max(48, (height - totalH) / 2 + 12);
    const prevVars = prevStepData ? (prevStepData.vars || {}) : {};

    items.forEach(([name, value], idx) => {
      const row = Math.floor(idx / cols);
      const col = idx % cols;
      const x = startX + col * (cardW + this.options.gap);
      const y = startY + row * (this.options.cardHeight + this.options.gap);
      const changed = JSON.stringify(prevVars[name]) !== JSON.stringify(value);
      const primary = (classes[name] || {}).category === 'primary';

      ctx.fillStyle = changed ? 'rgba(245,158,11,0.18)' : 'rgba(33,38,54,0.96)';
      ctx.strokeStyle = changed ? VIZ_COLORS.barCompare : (primary ? 'rgba(73,164,238,0.45)' : 'rgba(255,255,255,0.10)');
      ctx.lineWidth = changed ? 2 : 1;
      ctx.beginPath();
      const r = 6;
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + cardW - r, y);
      ctx.arcTo(x + cardW, y, x + cardW, y + r, r);
      ctx.lineTo(x + cardW, y + this.options.cardHeight - r);
      ctx.arcTo(x + cardW, y + this.options.cardHeight, x + cardW - r, y + this.options.cardHeight, r);
      ctx.lineTo(x + r, y + this.options.cardHeight);
      ctx.arcTo(x, y + this.options.cardHeight, x, y + this.options.cardHeight - r, r);
      ctx.lineTo(x, y + r);
      ctx.arcTo(x, y, x + r, y, r);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // 卡片本身是最后一道安全边界，任何字体或数据都不能穿到相邻卡片。
      ctx.save();
      this._round_rect(ctx, x + 2, y + 2, cardW - 4, this.options.cardHeight - 4, Math.max(1, r - 2));
      ctx.clip();

      ctx.fillStyle = primary ? '#49a4ee' : VIZ_COLORS.textDim;
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      ctx.fillText(this._ellipsize(ctx, name, cardW - 24), x + 12, y + 9);

      ctx.fillStyle = changed ? VIZ_COLORS.barCompare : VIZ_COLORS.text;
      this._draw_value(ctx, value, x, y, cardW, this.options.cardHeight);
      ctx.restore();
    });
    ctx.restore();
  }
}

const RENDERER_REGISTRY = {
  array_bars: ArrayBarRenderer,
  linked_list: LinkedListRenderer,
  tree: TreeRenderer,
  string_match: StringMatchRenderer,
  graph: GraphRenderer,
  bipartite: BipartiteGraphRenderer,
  concept: ConceptRenderer,
  grid: GridRenderer,
  scalar: ScalarStateRenderer,
  none: NoVisualizationRenderer,
};

function create_renderer(type, canvasId, options) {
  const RendererClass = RENDERER_REGISTRY[type];
  if (!RendererClass) {
    return new ArrayBarRenderer(canvasId, options);
  }
  return new RendererClass(canvasId, options);
}

window.ArrayBarRenderer = ArrayBarRenderer;
window.LinkedListRenderer = LinkedListRenderer;
window.TreeRenderer = TreeRenderer;
window.StringMatchRenderer = StringMatchRenderer;
window.GraphRenderer = GraphRenderer;
window.BipartiteGraphRenderer = BipartiteGraphRenderer;
window.ConceptRenderer = ConceptRenderer;
window.GridRenderer = GridRenderer;
window.ScalarStateRenderer = ScalarStateRenderer;
window.NoVisualizationRenderer = NoVisualizationRenderer;
window.BaseRenderer = BaseRenderer;
window.create_renderer = create_renderer;
window.VIZ_COLORS = VIZ_COLORS;
