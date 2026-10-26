// 大话算法 — 本地学习进度
(function () {
  'use strict';

  const STORAGE_KEY = 'dh_learning_state_v2';

  function emptyState() {
    return {
      version: 2,
      completedDemos: [],
      visitedChapters: [],
      last: null,
    };
  }

  function normalize(raw) {
    const state = emptyState();
    if (!raw || typeof raw !== 'object') return state;
    state.completedDemos = Array.isArray(raw.completedDemos)
      ? [...new Set(raw.completedDemos.filter(value => typeof value === 'string'))]
      : [];
    state.visitedChapters = Array.isArray(raw.visitedChapters)
      ? [...new Set(raw.visitedChapters.map(Number).filter(Number.isInteger))]
      : [];
    if (raw.last && Number.isInteger(Number(raw.last.chapter))) {
      state.last = {
        chapter: Number(raw.last.chapter),
        algorithm: typeof raw.last.algorithm === 'string' ? raw.last.algorithm : null,
        mode: typeof raw.last.mode === 'string' ? raw.last.mode : null,
        step: Number.isInteger(Number(raw.last.step)) ? Number(raw.last.step) : 0,
      };
    }
    return state;
  }

  function load() {
    try {
      return normalize(JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null'));
    } catch (_) {
      return emptyState();
    }
  }

  function save(state) {
    const normalized = normalize(state);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
    return normalized;
  }

  function demoId(chapter, algorithm) {
    return `${String(Number(chapter)).padStart(2, '0')}:${algorithm}`;
  }

  function visitChapter(chapter) {
    const state = load();
    const id = Number(chapter);
    if (!state.visitedChapters.includes(id)) state.visitedChapters.push(id);
    state.last = {
      chapter: id,
      algorithm: state.last && state.last.chapter === id ? state.last.algorithm : null,
      mode: state.last && state.last.chapter === id ? state.last.mode : null,
      step: state.last && state.last.chapter === id ? state.last.step : 0,
    };
    return save(state);
  }

  function updateLast(chapter, algorithm, mode, step) {
    const state = load();
    const id = Number(chapter);
    if (!state.visitedChapters.includes(id)) state.visitedChapters.push(id);
    state.last = {
      chapter: id,
      algorithm: algorithm || null,
      mode: mode || null,
      step: Math.max(0, Number(step) || 0),
    };
    return save(state);
  }

  function markDemoComplete(chapter, algorithm) {
    const state = load();
    const id = demoId(chapter, algorithm);
    if (!state.completedDemos.includes(id)) state.completedDemos.push(id);
    return save(state);
  }

  function completedChapterIds(siteIndex, state) {
    if (!siteIndex || !Array.isArray(siteIndex.chapters)) return [];
    const current = state || load();
    const completed = new Set(current.completedDemos);
    return siteIndex.chapters
      .filter(chapter => {
        const algorithms = Array.isArray(chapter.algorithms) ? chapter.algorithms : [];
        return algorithms.length > 0
          && algorithms.every(algo => completed.has(demoId(chapter.id, algo.key)));
      })
      .map(chapter => Number(chapter.id));
  }

  function reset() {
    localStorage.removeItem(STORAGE_KEY);
    // 清除旧版“访问即通关”数据，避免再次造成误解。
    localStorage.removeItem('algoProgress');
    return emptyState();
  }

  window.DHLearning = {
    STORAGE_KEY,
    load,
    save,
    demoId,
    visitChapter,
    updateLast,
    markDemoComplete,
    completedChapterIds,
    reset,
  };
})();
