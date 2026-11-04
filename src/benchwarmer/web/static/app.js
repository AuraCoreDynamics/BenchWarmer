/**
 * BenchWarmer Web Application Controller
 * Interactive LLM Benchmark Leaderboards, Pareto Routing, and Workload Evaluation
 */

(function () {
  "use strict";

  // --- Constants & Hardware Tiers ---
  const QUANT_BITS = {
    fp32: 32.0, fp16: 16.0, bf16: 16.0, q8_0: 8.5,
    q6_k: 6.6, q5_k_m: 5.7, q4_k_m: 4.8, q4_0: 4.5,
    q3_k_m: 3.9, q2_k: 2.9
  };

  const BENCH_METRICS = [
    { key: "ifeval", code: "IFEval", label: "Instruction Following (IFEval)" },
    { key: "bbh", code: "BBH", label: "Multi-Step Reasoning (BBH)" },
    { key: "math_hard", code: "MATH Hard", label: "Advanced Mathematics (MATH Hard)" },
    { key: "gpqa", code: "GPQA", label: "Graduate Scientific Reasoning (GPQA Diamond)" },
    { key: "musr", code: "MuSR", label: "Multistep Soft Reasoning (MuSR)" },
    { key: "mmlu_pro", code: "MMLU-Pro", label: "Broad Professional Knowledge (MMLU-Pro)" },
    { key: "arena_elo", code: "Arena Elo", label: "Human Preference Elo (Arena Elo)" }
  ];

  const RADAR_AXES = [
    { key: "ifeval", label: "IFEval" },
    { key: "bbh", label: "BBH" },
    { key: "math_hard", label: "MATH" },
    { key: "gpqa", label: "GPQA" },
    { key: "musr", label: "MuSR" },
    { key: "mmlu_pro", label: "MMLU-Pro" }
  ];

  const PALETTE = [
    "#58a6ff", "#3fb950", "#d29922", "#bc8cff",
    "#f85149", "#f778ba", "#79c0ff", "#56d364"
  ];

  const DEFAULT_WEIGHTS = {
    ifeval: 1.0,
    bbh: 1.0,
    math_hard: 1.2,
    gpqa: 1.2,
    musr: 0.8,
    mmlu_pro: 1.0,
    arena_elo: 1.0
  };

  function getHardwareTier(vramGb) {
    if (vramGb <= 0) return { label: "Cloud / API", color: "badge-cyan" };
    if (vramGb <= 8.5) return { label: "8 GB (RTX 3060/4060)", color: "badge-green" };
    if (vramGb <= 16.5) return { label: "16 GB (RTX 4080 / Mac 16G)", color: "badge-green" };
    if (vramGb <= 24.5) return { label: "24 GB (RTX 4090 / 3090)", color: "badge-cyan" };
    if (vramGb <= 48.5) return { label: "48 GB (2x 3090 / Mac 48G)", color: "badge-amber" };
    if (vramGb <= 80.5) return { label: "80 GB (A100 / H100)", color: "badge-purple" };
    if (vramGb <= 160.5) return { label: "160 GB (2x A100)", color: "badge-purple" };
    return { label: `${Math.ceil(vramGb / 80)}x A100 (Cluster)`, color: "badge-red" };
  }

  // --- State ---
  const state = {
    models: [],
    metadata: {},
    activeView: "leaderboard",
    sortKey: "hf_v2_avg",
    sortAsc: false,
    selectedModelIds: new Set(),
    currentQuant: "bf16",
    searchQuery: "",
    vramBudget: null,
    minParams: null,
    maxParams: null,
    customWeights: { ...DEFAULT_WEIGHTS },
    beatModelId: null,
    beatCriteria: {
      all: true,
      math_hard: false,
      ifeval: false,
      gpqa: false,
      bbh: false,
      mmlu_pro: false,
      arena_elo: false,
      vram: false
    },
    benchmarkThresholds: {
      ifeval: null,
      math_hard: null,
      gpqa: null,
      bbh: null,
      mmlu_pro: null,
      musr: null,
      arena_elo: null
    },
    currentPage: 1,
    pageSize: 50,
    contextTargetId: null
  };

  // --- View Preset Columns ---
  const VIEW_PRESETS = {
    leaderboard: [
      { key: "select", label: "", sortable: false },
      { key: "model_id", label: "Model", sortable: true },
      { key: "org", label: "Org", sortable: true },
      { key: "params_b", label: "Params", sortable: true },
      { key: "hf_v2_avg", label: "HF v2 Avg", sortable: true },
      { key: "arena_elo_raw", label: "Arena Elo", sortable: true },
      { key: "vram", label: "VRAM (Selected)", sortable: true },
      { key: "architecture", label: "Architecture", sortable: true },
      { key: "license", label: "License", sortable: true }
    ],
    all: [
      { key: "select", label: "", sortable: false },
      { key: "model_id", label: "Model", sortable: true },
      { key: "params_b", label: "Params", sortable: true },
      { key: "ifeval", label: "IFEval", sortable: true },
      { key: "bbh", label: "BBH", sortable: true },
      { key: "math_hard", label: "MATH", sortable: true },
      { key: "gpqa", label: "GPQA", sortable: true },
      { key: "musr", label: "MuSR", sortable: true },
      { key: "mmlu_pro", label: "MMLU-Pro", sortable: true },
      { key: "arena_elo_raw", label: "Arena Elo", sortable: true },
      { key: "hf_v2_avg", label: "HF v2 Avg", sortable: true }
    ],
    math: [
      { key: "select", label: "", sortable: false },
      { key: "model_id", label: "Model", sortable: true },
      { key: "params_b", label: "Params", sortable: true },
      { key: "math_hard", label: "MATH Hard", sortable: true },
      { key: "gpqa", label: "GPQA", sortable: true },
      { key: "bbh", label: "BBH", sortable: true },
      { key: "mmlu_pro", label: "MMLU-Pro", sortable: true },
      { key: "arena_elo_raw", label: "Arena Elo", sortable: true }
    ],
    code: [
      { key: "select", label: "", sortable: false },
      { key: "model_id", label: "Model", sortable: true },
      { key: "params_b", label: "Params", sortable: true },
      { key: "ifeval", label: "IFEval", sortable: true },
      { key: "musr", label: "MuSR", sortable: true },
      { key: "bbh", label: "BBH", sortable: true },
      { key: "arena_elo_raw", label: "Arena Elo", sortable: true }
    ],
    hardware: [
      { key: "select", label: "", sortable: false },
      { key: "model_id", label: "Model", sortable: true },
      { key: "params_b", label: "Params", sortable: true },
      { key: "vram", label: "VRAM Footprint", sortable: true },
      { key: "context_length", label: "Context Window", sortable: true },
      { key: "architecture", label: "Architecture", sortable: true },
      { key: "precision", label: "Precision", sortable: true },
      { key: "is_moe", label: "MoE", sortable: true },
      { key: "license", label: "License", sortable: true }
    ],
    scorer: [
      { key: "select", label: "", sortable: false },
      { key: "rank", label: "Rank", sortable: false },
      { key: "model_id", label: "Model", sortable: true },
      { key: "custom_score", label: "Weighted Score", sortable: true },
      { key: "params_b", label: "Params", sortable: true },
      { key: "vram", label: "VRAM", sortable: true },
      { key: "math_hard", label: "MATH", sortable: true },
      { key: "ifeval", label: "IFEval", sortable: true },
      { key: "gpqa", label: "GPQA", sortable: true },
      { key: "bbh", label: "BBH", sortable: true },
      { key: "arena_elo_raw", label: "Arena Elo", sortable: true }
    ]
  };

  // --- Compute Custom Weighted Score for a Model ---
  function computeCustomScore(model) {
    const weights = state.customWeights;
    let weightedSum = 0;
    let totalWeight = 0;

    Object.keys(weights).forEach(k => {
      const w = weights[k];
      if (w <= 0) return;

      let score = null;
      if (k === "arena_elo") {
        score = model.scores ? model.scores.arena_elo : null;
      } else if (model.scores && model.scores[k] !== undefined && model.scores[k] !== null) {
        score = model.scores[k];
      }

      if (score !== null && score !== undefined) {
        weightedSum += w * score;
        totalWeight += w;
      }
    });

    return totalWeight > 0 ? (weightedSum / totalWeight) : 0;
  }

  // --- Initial Data Fetch ---
  async function init() {
    try {
      const [metaRes, modelsRes] = await Promise.all([
        fetch("/api/metadata").then(r => r.json()).catch(() => ({})),
        fetch("/api/models").then(r => r.json())
      ]);
      state.metadata = metaRes;
      state.models = modelsRes;

      const modelCount = modelsRes.length;
      document.getElementById("badge-model-count").textContent = `${modelCount.toLocaleString()} Models`;

      const builtAt = metaRes.built_at || "November 2026";
      document.getElementById("header-built-date").textContent = `Current as of ${builtAt}`;

      populateBeatModelSelect();
      setupEventListeners();
      renderScorerSliders();
      renderTable();
    } catch (err) {
      console.error("Failed to initialize BenchWarmer:", err);
    }
  }

  function populateBeatModelSelect() {
    const sel = document.getElementById("beat-model-select");
    const sorted = [...state.models].sort((a, b) => a.model_id.localeCompare(b.model_id));
    sel.innerHTML = `<option value="">-- Choose baseline model --</option>` +
      sorted.map(m => `<option value="${m.model_id}">${m.model_name} (${m.org}${m.params_b ? `, ${m.params_b.toFixed(1)}B` : ''})</option>`).join("");
  }

  // --- Filtering & Sorting ---
  function getFilteredModels() {
    const beatRef = state.beatModelId ? state.models.find(m => m.model_id === state.beatModelId) : null;

    return state.models.filter(m => {
      // 1. Parameter range filter
      if (state.minParams !== null && (m.params_b === null || m.params_b < state.minParams)) return false;
      if (state.maxParams !== null && (m.params_b === null || m.params_b > state.maxParams)) return false;

      // 2. VRAM budget filter
      if (state.vramBudget !== null && state.vramBudget < 320) {
        const vram = m.estimated_vram_gb ? m.estimated_vram_gb[state.currentQuant] : 0;
        if (vram > state.vramBudget) return false;
      }

      // 3. Search query filter
      if (state.searchQuery) {
        const q = state.searchQuery.toLowerCase();
        const matchesId = m.model_id.toLowerCase().includes(q);
        const matchesOrg = m.org.toLowerCase().includes(q);
        const matchesName = m.model_name.toLowerCase().includes(q);
        const matchesArch = m.architecture && m.architecture.toLowerCase().includes(q);
        if (!matchesId && !matchesOrg && !matchesName && !matchesArch) return false;
      }

      // 4. Benchmark minimum score thresholds
      const thresh = state.benchmarkThresholds;
      if (thresh.ifeval !== null && (!m.scores || m.scores.ifeval < thresh.ifeval)) return false;
      if (thresh.math_hard !== null && (!m.scores || m.scores.math_hard < thresh.math_hard)) return false;
      if (thresh.gpqa !== null && (!m.scores || m.scores.gpqa < thresh.gpqa)) return false;
      if (thresh.bbh !== null && (!m.scores || m.scores.bbh < thresh.bbh)) return false;
      if (thresh.mmlu_pro !== null && (!m.scores || m.scores.mmlu_pro < thresh.mmlu_pro)) return false;
      if (thresh.musr !== null && (!m.scores || m.scores.musr < thresh.musr)) return false;
      if (thresh.arena_elo !== null) {
        const rawElo = m.raw_scores ? m.raw_scores.arena_elo : 0;
        if (rawElo < thresh.arena_elo) return false;
      }

      // 5. "Match or Beat Reference Model" Filter
      if (beatRef) {
        const crit = state.beatCriteria;
        if (crit.all) {
          // Model must equal or beat in HF v2 Avg (or overall composite)
          if ((m.hf_v2_avg || 0) < (beatRef.hf_v2_avg || 0)) return false;
        }
        if (crit.math_hard) {
          const refScore = (beatRef.scores && beatRef.scores.math_hard) || 0;
          if (!m.scores || (m.scores.math_hard || 0) < refScore) return false;
        }
        if (crit.ifeval) {
          const refScore = (beatRef.scores && beatRef.scores.ifeval) || 0;
          if (!m.scores || (m.scores.ifeval || 0) < refScore) return false;
        }
        if (crit.gpqa) {
          const refScore = (beatRef.scores && beatRef.scores.gpqa) || 0;
          if (!m.scores || (m.scores.gpqa || 0) < refScore) return false;
        }
        if (crit.bbh) {
          const refScore = (beatRef.scores && beatRef.scores.bbh) || 0;
          if (!m.scores || (m.scores.bbh || 0) < refScore) return false;
        }
        if (crit.mmlu_pro) {
          const refScore = (beatRef.scores && beatRef.scores.mmlu_pro) || 0;
          if (!m.scores || (m.scores.mmlu_pro || 0) < refScore) return false;
        }
        if (crit.arena_elo) {
          const refElo = (beatRef.raw_scores && beatRef.raw_scores.arena_elo) || 0;
          const myElo = (m.raw_scores && m.raw_scores.arena_elo) || 0;
          if (myElo < refElo) return false;
        }
        if (crit.vram) {
          const refVram = beatRef.estimated_vram_gb ? beatRef.estimated_vram_gb[state.currentQuant] : Infinity;
          const myVram = m.estimated_vram_gb ? m.estimated_vram_gb[state.currentQuant] : 0;
          if (myVram > refVram) return false;
        }
      }

      return true;
    });
  }

  function getSortedModels() {
    const list = getFilteredModels();
    const key = state.sortKey;
    const asc = state.sortAsc;

    list.sort((a, b) => {
      let va = null;
      let vb = null;

      if (key === "custom_score") {
        va = computeCustomScore(a);
        vb = computeCustomScore(b);
      } else if (key === "model_id") {
        va = a.model_id;
        vb = b.model_id;
        return asc ? va.localeCompare(vb) : vb.localeCompare(va);
      } else if (key === "org") {
        va = a.org;
        vb = b.org;
        return asc ? va.localeCompare(vb) : vb.localeCompare(va);
      } else if (key === "params_b") {
        va = a.params_b;
        vb = b.params_b;
      } else if (key === "vram") {
        va = a.estimated_vram_gb ? a.estimated_vram_gb[state.currentQuant] : null;
        vb = b.estimated_vram_gb ? b.estimated_vram_gb[state.currentQuant] : null;
      } else if (key === "hf_v2_avg") {
        va = a.hf_v2_avg;
        vb = b.hf_v2_avg;
      } else if (key === "arena_elo_raw") {
        va = a.raw_scores ? a.raw_scores.arena_elo : null;
        vb = b.raw_scores ? b.raw_scores.arena_elo : null;
      } else if (["ifeval", "bbh", "math_hard", "gpqa", "musr", "mmlu_pro"].includes(key)) {
        va = a.scores ? a.scores[key] : null;
        vb = b.scores ? b.scores[key] : null;
      } else {
        va = a[key];
        vb = b[key];
      }

      if (va === null || va === undefined) return 1;
      if (vb === null || vb === undefined) return -1;

      if (typeof va === "string") {
        return asc ? va.localeCompare(vb) : vb.localeCompare(va);
      }
      return asc ? va - vb : vb - va;
    });

    return list;
  }

  // --- Rendering Custom Scorer Sliders ---
  function renderScorerSliders() {
    const grid = document.getElementById("scorer-sliders-grid");
    if (!grid) return;

    grid.innerHTML = BENCH_METRICS.map(m => {
      const val = state.customWeights[m.key] !== undefined ? state.customWeights[m.key] : 1.0;
      return `
        <div class="weight-card">
          <div class="weight-header">
            <span class="weight-label">${m.label}</span>
            <span class="weight-val" id="disp-wt-${m.key}">${val.toFixed(1)}</span>
          </div>
          <input type="range" class="range-input weight-slider" data-bench="${m.key}" min="0" max="3" step="0.1" value="${val}" style="width: 100%;">
        </div>
      `;
    }).join("");

    grid.querySelectorAll(".weight-slider").forEach(sl => {
      sl.oninput = (e) => {
        const b = e.target.dataset.bench;
        const v = parseFloat(e.target.value);
        state.customWeights[b] = v;
        const disp = document.getElementById(`disp-wt-${b}`);
        if (disp) disp.textContent = v.toFixed(1);
        if (state.activeView === "scorer") renderTable();
      };
    });
  }

  // --- Rendering Table ---
  function renderTable() {
    const thead = document.getElementById("table-head");
    const tbody = document.getElementById("table-body");
    const cols = VIEW_PRESETS[state.activeView];

    // Toggle Scorer Panel visibility
    const scorerPanel = document.getElementById("scorer-panel");
    if (scorerPanel) {
      if (state.activeView === "scorer") {
        scorerPanel.classList.add("open");
      } else {
        scorerPanel.classList.remove("open");
      }
    }

    // Render Headers
    let headHtml = "<tr>";
    cols.forEach(col => {
      if (col.key === "select") {
        const isAllSelected = state.models.length > 0 && state.selectedModelIds.size === state.models.length;
        headHtml += `<th style="width: 40px; text-align: center;"><input type="checkbox" id="select-all-cb" ${isAllSelected ? "checked" : ""}></th>`;
      } else if (col.key === "rank") {
        headHtml += `<th style="width: 60px;">${col.label}</th>`;
      } else {
        const isSorted = state.sortKey === col.key;
        const sortClass = isSorted ? (state.sortAsc ? "sorted-asc" : "sorted-desc") : "";
        headHtml += `<th class="${sortClass}" data-sort="${col.key}">${col.label}</th>`;
      }
    });
    headHtml += "</tr>";
    thead.innerHTML = headHtml;

    // Render Rows
    const allModels = getSortedModels();
    const totalCount = allModels.length;

    // Pagination calculations
    const pageSize = state.pageSize === "all" ? totalCount : parseInt(state.pageSize, 10);
    const totalPages = Math.max(1, Math.ceil(totalCount / (pageSize || 1)));
    if (state.currentPage > totalPages) state.currentPage = totalPages;
    if (state.currentPage < 1) state.currentPage = 1;

    const startIdx = (state.currentPage - 1) * pageSize;
    const endIdx = state.pageSize === "all" ? totalCount : Math.min(totalCount, startIdx + pageSize);
    const pageModels = allModels.slice(startIdx, endIdx);

    // Update match count & pagination display
    const matchCountEl = document.getElementById("match-count");
    if (matchCountEl) {
      matchCountEl.textContent = `${totalCount} of ${state.models.length} models displayed`;
    }

    const pagInfo = document.getElementById("pagination-info");
    if (pagInfo) {
      pagInfo.textContent = totalCount > 0 
        ? `Showing ${startIdx + 1}–${endIdx} of ${totalCount} models` 
        : `Showing 0 of 0 models`;
    }

    const pageInd = document.getElementById("page-indicator");
    if (pageInd) {
      pageInd.textContent = `Page ${state.currentPage} of ${totalPages}`;
    }

    const btnFirst = document.getElementById("btn-first-page");
    const btnPrev = document.getElementById("btn-prev-page");
    const btnNext = document.getElementById("btn-next-page");
    const btnLast = document.getElementById("btn-last-page");
    if (btnFirst) btnFirst.disabled = state.currentPage <= 1;
    if (btnPrev) btnPrev.disabled = state.currentPage <= 1;
    if (btnNext) btnNext.disabled = state.currentPage >= totalPages;
    if (btnLast) btnLast.disabled = state.currentPage >= totalPages;

    if (totalCount === 0) {
      tbody.innerHTML = `<tr><td colspan="${cols.length}" style="text-align: center; padding: 32px; color: var(--text-secondary);">No models matched your filter criteria. Try clicking "Reset Filters".</td></tr>`;
      return;
    }

    let rowsHtml = "";
    pageModels.forEach((m, idxOnPage) => {
      const globalIdx = startIdx + idxOnPage;
      const isSelected = state.selectedModelIds.has(m.model_id);
      rowsHtml += `<tr data-model-id="${m.model_id}" class="${isSelected ? "selected" : ""}">`;

      cols.forEach(col => {
        if (col.key === "select") {
          rowsHtml += `<td style="text-align: center;"><input type="checkbox" class="row-select-cb" data-id="${m.model_id}" ${isSelected ? "checked" : ""}></td>`;
        } else if (col.key === "rank") {
          rowsHtml += `<td><span class="badge ${globalIdx < 3 ? 'badge-amber' : ''}">#${globalIdx + 1}</span></td>`;
        } else if (col.key === "model_id") {
          const orgBadge = `<span class="org-tag">${m.org}</span>`;
          rowsHtml += `<td><div class="model-name-cell">${orgBadge} <span>${m.model_name}</span></div></td>`;
        } else if (col.key === "org") {
          rowsHtml += `<td><span class="badge">${m.org}</span></td>`;
        } else if (col.key === "custom_score") {
          const cs = computeCustomScore(m);
          const barW = Math.min(60, Math.round(cs * 0.6));
          rowsHtml += `<td><span class="score-num" style="color: var(--accent-cyan); font-weight: 700;">${cs.toFixed(2)}</span><div class="score-bar-mini" style="width: ${barW}px; background: var(--accent-cyan);"></div></td>`;
        } else if (col.key === "params_b") {
          const pDisp = m.params_b !== null ? `${m.params_b.toFixed(1)}B` : "Proprietary";
          rowsHtml += `<td><span class="badge badge-cyan">${pDisp}</span></td>`;
        } else if (col.key === "vram") {
          const vram = m.estimated_vram_gb ? m.estimated_vram_gb[state.currentQuant] : 0;
          if (vram > 0) {
            const tier = getHardwareTier(vram);
            rowsHtml += `<td><span class="score-num">${vram.toFixed(1)} GB</span> <span class="badge ${tier.color}" style="font-size: 10px;">${tier.label.split("(")[0]}</span></td>`;
          } else {
            rowsHtml += `<td><span class="text-secondary">API Cloud</span></td>`;
          }
        } else if (col.key === "hf_v2_avg") {
          const val = m.hf_v2_avg;
          if (val !== null && val !== undefined) {
            const barW = Math.min(60, Math.round(val * 0.6));
            rowsHtml += `<td><span class="score-num">${val.toFixed(2)}</span><div class="score-bar-mini" style="width: ${barW}px;"></div></td>`;
          } else {
            rowsHtml += `<td><span class="text-secondary">-</span></td>`;
          }
        } else if (col.key === "arena_elo_raw") {
          const elo = m.raw_scores ? m.raw_scores.arena_elo : null;
          rowsHtml += `<td><span class="score-num" style="color: var(--accent-purple);">${elo ? elo.toFixed(0) : "-"}</span></td>`;
        } else if (["ifeval", "bbh", "math_hard", "gpqa", "musr", "mmlu_pro"].includes(col.key)) {
          const val = m.scores ? m.scores[col.key] : null;
          rowsHtml += `<td><span class="score-num">${val !== null && val !== undefined ? val.toFixed(1) : "-"}</span></td>`;
        } else if (col.key === "context_length") {
          const ctxDisp = m.context_length ? `${(m.context_length / 1000).toFixed(0)}k` : "N/A";
          rowsHtml += `<td><span class="badge">${ctxDisp}</span></td>`;
        } else if (col.key === "is_moe") {
          rowsHtml += `<td><span class="badge ${m.is_moe ? "badge-amber" : ""}">${m.is_moe ? "MoE" : "Dense"}</span></td>`;
        } else {
          rowsHtml += `<td>${m[col.key] || "-"}</td>`;
        }
      });

      rowsHtml += "</tr>";
    });

    tbody.innerHTML = rowsHtml;
    updateCompareButton();
  }

  function updateCompareButton() {
    const btn = document.getElementById("btn-open-compare");
    const countSpan = document.getElementById("compare-count");
    const count = state.selectedModelIds.size;
    countSpan.textContent = count;
    btn.disabled = count < 2;
  }

  // --- SVG Charts Generation ---
  function generateRadarSvg(dimensions, seriesList) {
    const size = 340;
    const center = size / 2;
    const radius = 110;
    const angleStep = (Math.PI * 2) / dimensions.length;

    let svg = `<svg viewBox="0 0 ${size} ${size}" class="svg-chart">`;

    for (let r = 20; r <= 100; r += 20) {
      const cr = (r / 100) * radius;
      svg += `<circle cx="${center}" cy="${center}" r="${cr}" fill="none" stroke="#252b36" stroke-dasharray="2,2" stroke-width="1"/>`;
      svg += `<text x="${center + 4}" y="${center - cr + 4}" fill="#484f58" font-size="9" font-family="monospace">${r}</text>`;
    }

    dimensions.forEach((dim, i) => {
      const angle = i * angleStep - Math.PI / 2;
      const x2 = center + Math.cos(angle) * radius;
      const y2 = center + Math.sin(angle) * radius;
      svg += `<line x1="${center}" y1="${center}" x2="${x2}" y2="${y2}" stroke="#30363d" stroke-width="1"/>`;

      const lx = center + Math.cos(angle) * (radius + 24);
      const ly = center + Math.sin(angle) * (radius + 24);
      const anchor = Math.abs(Math.cos(angle)) < 0.2 ? "middle" : (Math.cos(angle) > 0 ? "start" : "end");
      svg += `<text x="${lx}" y="${ly + 4}" fill="#8b949e" font-size="11" font-weight="600" text-anchor="${anchor}">${dim.label}</text>`;
    });

    seriesList.forEach((s) => {
      const pts = dimensions.map((dim, i) => {
        const val = s.values[dim.key] || 0;
        const normR = (Math.min(100, Math.max(0, val)) / 100) * radius;
        const angle = i * angleStep - Math.PI / 2;
        const x = center + Math.cos(angle) * normR;
        const y = center + Math.sin(angle) * normR;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(" ");

      svg += `<polygon points="${pts}" fill="${s.color}" fill-opacity="0.25" stroke="${s.color}" stroke-width="2"/>`;

      dimensions.forEach((dim, i) => {
        const val = s.values[dim.key] || 0;
        const normR = (Math.min(100, Math.max(0, val)) / 100) * radius;
        const angle = i * angleStep - Math.PI / 2;
        const x = center + Math.cos(angle) * normR;
        const y = center + Math.sin(angle) * normR;
        svg += `<circle cx="${x}" cy="${y}" r="3.5" fill="${s.color}" stroke="#161b22" stroke-width="1.5"/>`;
      });
    });

    svg += "</svg>";
    return svg;
  }

  // --- Modals Controller ---
  function openModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.classList.add("open");
  }

  function closeModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.classList.remove("open");
  }

  // Scorecard Modal
  async function showScorecard(modelId) {
    const model = state.models.find(m => m.model_id === modelId);
    if (!model) return;

    document.getElementById("sc-model-name").textContent = model.model_name;
    document.getElementById("sc-org-badge").textContent = model.org;
    document.getElementById("sc-params-badge").textContent = model.params_b ? `${model.params_b.toFixed(1)}B` : "Proprietary";
    document.getElementById("sc-arch-badge").textContent = model.architecture || "Unknown";

    // Radar Chart
    const radarContainer = document.getElementById("sc-radar-svg").parentNode;
    const radarSvg = generateRadarSvg(RADAR_AXES, [{
      name: model.model_name,
      color: "#58a6ff",
      values: model.scores || {}
    }]);
    radarContainer.querySelector("svg").outerHTML = radarSvg;

    // Benchmark Cards
    const cardsContainer = document.getElementById("sc-metric-cards");
    let cardsHtml = "";
    RADAR_AXES.forEach(dim => {
      const val = model.scores ? model.scores[dim.key] : null;
      cardsHtml += `
        <div class="metric-card">
          <div class="metric-card-label">${dim.label}</div>
          <div class="metric-card-value">${val !== null && val !== undefined ? val.toFixed(1) : "N/A"}</div>
          <div class="metric-card-raw">norm 0-100</div>
        </div>
      `;
    });
    // Add Arena Elo Card
    const elo = model.raw_scores ? model.raw_scores.arena_elo : null;
    cardsHtml += `
      <div class="metric-card" style="border-color: rgba(188, 140, 255, 0.4);">
        <div class="metric-card-label" style="color: var(--accent-purple);">Arena Elo</div>
        <div class="metric-card-value" style="color: var(--accent-purple);">${elo ? elo.toFixed(0) : "N/A"}</div>
        <div class="metric-card-raw">lmsys arena</div>
      </div>
    `;
    cardsContainer.innerHTML = cardsHtml;

    // VRAM Table
    const vramTbody = document.getElementById("sc-vram-table").querySelector("tbody");
    let vramHtml = "";
    if (model.params_b) {
      Object.keys(QUANT_BITS).forEach(qKey => {
        const bits = QUANT_BITS[qKey];
        const vram = model.estimated_vram_gb ? model.estimated_vram_gb[qKey] : 0;
        const tier = getHardwareTier(vram);
        vramHtml += `
          <tr>
            <td><strong>${qKey.toUpperCase()}</strong></td>
            <td>${bits.toFixed(1)} bits</td>
            <td><strong style="color: var(--accent-cyan);">${vram.toFixed(2)} GB</strong></td>
            <td><span class="badge ${tier.color}">${tier.label}</span></td>
          </tr>
        `;
      });
    } else {
      vramHtml = `<tr><td colspan="4" style="text-align: center; color: var(--text-secondary); padding: 12px;">Proprietary cloud model; parameters and local VRAM footprint are not applicable.</td></tr>`;
    }
    vramTbody.innerHTML = vramHtml;

    // Audit Info Fetch
    try {
      const auditRes = await fetch(`/api/audit/${encodeURIComponent(model.model_id)}`).then(r => r.json());
      const badge = document.getElementById("sc-audit-badge");
      const desc = document.getElementById("sc-audit-desc");
      if (auditRes.status === "HIGH_CONTAMINATION_RISK") {
        badge.className = "badge badge-red";
        badge.textContent = "HIGH RISK CONTAMINATION";
      } else if (auditRes.status === "SUSPICIOUS") {
        badge.className = "badge badge-amber";
        badge.textContent = "SUSPICIOUS";
      } else {
        badge.className = "badge badge-green";
        badge.textContent = "CLEAN";
      }
      const flagStr = auditRes.flags && auditRes.flags.length > 0 ? auditRes.flags.join(" | ") : "Model exhibits natural peer-group consistency.";
      desc.textContent = `Anomaly Score: ${auditRes.anomaly_score.toFixed(1)} / 100. ${flagStr}`;
    } catch (e) {
      // Ignore
    }

    // Toggle Compare Button text
    const cmpBtn = document.getElementById("sc-btn-compare-toggle");
    cmpBtn.textContent = state.selectedModelIds.has(model.model_id) ? "Remove from Comparison" : "Add to Comparison";
    cmpBtn.onclick = () => {
      if (state.selectedModelIds.has(model.model_id)) {
        state.selectedModelIds.delete(model.model_id);
      } else {
        state.selectedModelIds.add(model.model_id);
      }
      cmpBtn.textContent = state.selectedModelIds.has(model.model_id) ? "Remove from Comparison" : "Add to Comparison";
      updateCompareButton();
      // Update checkbox in table if present
      const cb = document.querySelector(`.row-select-cb[data-id="${model.model_id}"]`);
      if (cb) {
        cb.checked = state.selectedModelIds.has(model.model_id);
        const tr = cb.closest("tr");
        if (tr) tr.classList.toggle("selected", cb.checked);
      }
    };

    openModal("modal-scorecard");
  }

  // Multi-Model Compare Modal
  async function showCompareModal() {
    const ids = Array.from(state.selectedModelIds);
    if (ids.length < 2) return;

    try {
      const res = await fetch("/api/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_ids: ids })
      }).then(r => r.json());

      document.getElementById("cmp-model-count").textContent = `${res.models.length} Models`;

      const series = res.models.map((m, idx) => ({
        name: m.model_name,
        color: PALETTE[idx % PALETTE.length],
        values: m.scores || {}
      }));

      const radarContainer = document.getElementById("cmp-radar-svg").parentNode;
      const radarSvg = generateRadarSvg(RADAR_AXES, series);
      radarContainer.querySelector("svg").outerHTML = radarSvg;

      const legendContainer = document.getElementById("cmp-radar-legend");
      legendContainer.innerHTML = series.map(s => `
        <div style="display: flex; align-items: center; gap: 6px;">
          <div style="width: 12px; height: 12px; background: ${s.color}; border-radius: 2px;"></div>
          <span>${s.name}</span>
        </div>
      `).join("");

      const barsContainer = document.getElementById("cmp-bars-container");
      let barsHtml = "";
      res.benchmarks.forEach(bench => {
        barsHtml += `<div style="border-bottom: 1px solid var(--border-subtle); padding-bottom: 6px;">`;
        barsHtml += `<div style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 4px;">${bench}</div>`;
        res.models.forEach((m, idx) => {
          const s = res.scores[bench] ? res.scores[bench][m.model_id] : 0;
          const color = PALETTE[idx % PALETTE.length];
          const isWinner = res.best_in_class[bench] && res.best_in_class[bench].model_id === m.model_id;
          barsHtml += `
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 3px; font-size: 11px;">
              <span style="width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${m.model_name}</span>
              <div style="flex: 1; height: 12px; background: #21262d; border-radius: 2px; overflow: hidden;">
                <div style="width: ${Math.min(100, Math.max(0, s))}%; height: 100%; background: ${color}; border-radius: 2px;"></div>
              </div>
              <span style="font-family: monospace; font-weight: 600; width: 45px; text-align: right;">${s ? s.toFixed(1) : "-"}</span>
              ${isWinner ? `<span title="Best in Class">👑</span>` : `<span style="width: 16px;"></span>`}
            </div>
          `;
        });
        barsHtml += `</div>`;
      });
      barsContainer.innerHTML = barsHtml;

      const thead = document.getElementById("cmp-specs-head");
      const tbody = document.getElementById("cmp-specs-body");
      thead.innerHTML = `
        <tr>
          <th>Metric / Attribute</th>
          ${res.models.map(m => `<th>${m.model_name}</th>`).join("")}
        </tr>
      `;

      const rows = [
        { label: "Organization", val: m => m.org },
        { label: "Parameter Count", val: m => m.params_b ? `${m.params_b.toFixed(1)}B` : "Proprietary" },
        { label: "Architecture", val: m => m.architecture || "N/A" },
        { label: "Context Window", val: m => m.context_length ? `${(m.context_length / 1000).toFixed(0)}k` : "N/A" },
        { label: `VRAM (${state.currentQuant.toUpperCase()})`, val: m => m.estimated_vram_gb && m.estimated_vram_gb[state.currentQuant] ? `${m.estimated_vram_gb[state.currentQuant].toFixed(1)} GB` : "Cloud" },
        { label: "Total Benchmark Wins", val: m => `<strong>${res.summary[m.model_id] ? res.summary[m.model_id].wins : 0}</strong>` },
        { label: "Average Capability Score", val: m => res.summary[m.model_id] ? res.summary[m.model_id].avg_score.toFixed(2) : "N/A" }
      ];

      tbody.innerHTML = rows.map(r => `
        <tr>
          <td><strong>${r.label}</strong></td>
          ${res.models.map(m => `<td>${r.val(m)}</td>`).join("")}
        </tr>
      `).join("");

      document.getElementById("cmp-btn-copy-md").onclick = () => {
        let md = `# BenchWarmer Model Comparison\n\n`;
        md += `| Attribute | ` + res.models.map(m => m.model_name).join(" | ") + ` |\n`;
        md += `| --- | ` + res.models.map(() => "---").join(" | ") + ` |\n`;
        rows.forEach(r => {
          md += `| ${r.label} | ` + res.models.map(m => String(r.val(m)).replace(/<[^>]*>/g, "")).join(" | ") + ` |\n`;
        });
        md += `\n### Benchmark Evaluations\n\n`;
        md += `| Benchmark | ` + res.models.map(m => m.model_name).join(" | ") + ` | Winner |\n`;
        md += `| --- | ` + res.models.map(() => "---").join(" | ") + ` | --- |\n`;
        res.benchmarks.forEach(bench => {
          const winner = res.best_in_class[bench] ? res.best_in_class[bench].model_id : "Tie";
          md += `| ${bench} | ` + res.models.map(m => (res.scores[bench] && res.scores[bench][m.model_id] ? res.scores[bench][m.model_id].toFixed(2) : "-")).join(" | ") + ` | ${winner} |\n`;
        });
        navigator.clipboard.writeText(md).then(() => {
          alert("Comparison Markdown table copied to clipboard!");
        });
      };

      openModal("modal-compare");
    } catch (err) {
      console.error("Failed to compare models:", err);
    }
  }

  // Pareto Frontier Modal
  async function showParetoModal() {
    const metric = document.getElementById("pareto-metric-select").value;
    const quant = document.getElementById("pareto-quant-select").value;

    try {
      const frontierPts = await fetch(`/api/pareto?metric=${metric}&quant=${quant}`).then(r => r.json());
      const frontierSet = new Set(frontierPts.map(p => p.model_id));

      const scatterData = state.models
        .filter(m => m.params_b !== null && m.estimated_vram_gb)
        .map(m => {
          let score = 0;
          if (metric === "hf_v2_avg") score = m.hf_v2_avg || 0;
          else if (metric === "arena_elo_raw") score = m.raw_scores ? m.raw_scores.arena_elo || 0 : 0;
          else score = (m.scores && m.scores[metric]) || 0;

          const vram = m.estimated_vram_gb[quant] || 0;
          return {
            model_id: m.model_id,
            model_name: m.model_name,
            score: score,
            vram: vram,
            isFrontier: frontierSet.has(m.model_id)
          };
        });

      const maxVram = Math.max(...scatterData.map(d => d.vram), 10);
      const minScore = Math.min(...scatterData.map(d => d.score), 0);
      const maxScore = Math.max(...scatterData.map(d => d.score), 100);

      const svgW = 800;
      const svgH = 360;
      const padL = 60;
      const padR = 40;
      const padT = 30;
      const padB = 40;

      function scaleX(vram) {
        return padL + (vram / maxVram) * (svgW - padL - padR);
      }
      function scaleY(score) {
        return svgH - padB - ((score - minScore) / (maxScore - minScore || 1)) * (svgH - padT - padB);
      }

      let svg = "";
      for (let s = Math.ceil(minScore / 20) * 20; s <= maxScore; s += 20) {
        const y = scaleY(s);
        svg += `<line x1="${padL}" y1="${y}" x2="${svgW - padR}" y2="${y}" stroke="#21262d" stroke-width="1"/>`;
        svg += `<text x="${padL - 10}" y="${y + 4}" fill="#6e7681" font-size="10" text-anchor="end" font-family="monospace">${s.toFixed(0)}</text>`;
      }
      for (let v = 0; v <= maxVram; v += (maxVram > 150 ? 50 : 20)) {
        const x = scaleX(v);
        svg += `<line x1="${x}" y1="${padT}" x2="${x}" y2="${svgH - padB}" stroke="#21262d" stroke-width="1"/>`;
        svg += `<text x="${x}" y="${svgH - padB + 16}" fill="#6e7681" font-size="10" text-anchor="middle" font-family="monospace">${v}G</text>`;
      }

      frontierPts.sort((a, b) => a.estimated_vram_gb - b.estimated_vram_gb);
      if (frontierPts.length > 1) {
        const pathD = frontierPts.map((p, idx) => {
          const x = scaleX(p.estimated_vram_gb);
          const y = scaleY(p.score);
          return (idx === 0 ? "M" : "L") + ` ${x.toFixed(1)} ${y.toFixed(1)}`;
        }).join(" ");
        svg += `<path d="${pathD}" fill="none" stroke="#58a6ff" stroke-width="2.5" stroke-dasharray="4,2"/>`;
      }

      scatterData.forEach(d => {
        const x = scaleX(d.vram);
        const y = scaleY(d.score);
        const fill = d.isFrontier ? "#58a6ff" : "#30363d";
        const r = d.isFrontier ? 6 : 4;
        svg += `
          <circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" stroke="#fff" stroke-width="${d.isFrontier ? 1.5 : 0.5}"
                  class="scatter-dot" data-model="${d.model_id}" data-vram="${d.vram.toFixed(1)}" data-score="${d.score.toFixed(1)}"/>
        `;
        if (d.isFrontier) {
          svg += `<text x="${x + 8}" y="${y - 6}" fill="#58a6ff" font-size="10" font-weight="600">${d.model_name}</text>`;
        }
      });

      document.getElementById("pareto-svg").innerHTML = svg;

      const ptBody = document.getElementById("pareto-table-body");
      ptBody.innerHTML = frontierPts.map(p => `
        <tr data-model-id="${p.model_id}" style="cursor: pointer;">
          <td><strong style="color: var(--accent-cyan);">${p.model_id}</strong></td>
          <td>${p.params_b.toFixed(1)}B</td>
          <td>${p.estimated_vram_gb.toFixed(1)} GB</td>
          <td>${p.score.toFixed(2)}</td>
          <td><span class="badge badge-green">${p.efficiency_ratio.toFixed(2)}</span></td>
        </tr>
      `).join("");

      openModal("modal-pareto");
    } catch (err) {
      console.error("Failed to load Pareto frontier:", err);
    }
  }

  // Contamination Audit Modal
  async function showAuditModal() {
    try {
      const audits = await fetch("/api/audit").then(r => r.json());
      const tbody = document.getElementById("audit-table-body");
      tbody.innerHTML = audits.map(a => {
        let badgeClass = "badge-green";
        if (a.status === "HIGH_CONTAMINATION_RISK") badgeClass = "badge-red";
        else if (a.status === "SUSPICIOUS") badgeClass = "badge-amber";

        const flags = a.flags && a.flags.length > 0 ? a.flags.join("<br>") : "Clean";
        return `
          <tr data-model-id="${a.model_id}" style="cursor: pointer;">
            <td><span class="badge ${badgeClass}">${a.status}</span></td>
            <td><strong>${a.model_id}</strong></td>
            <td><span class="score-num" style="color: ${a.anomaly_score >= 60 ? 'var(--accent-red)' : 'var(--text-primary)'};">${a.anomaly_score.toFixed(1)}</span></td>
            <td>${a.z_score_spread ? a.z_score_spread.toFixed(2) : "-"}</td>
            <td>${a.ifeval_vs_knowledge_gap ? a.ifeval_vs_knowledge_gap.toFixed(1) : "-"}</td>
            <td style="font-size: 11px; color: var(--text-secondary);">${flags}</td>
          </tr>
        `;
      }).join("");

      openModal("modal-audit");
    } catch (err) {
      console.error("Failed to load audit:", err);
    }
  }

  // --- Context Menu ---
  function showContextMenu(e, modelId) {
    e.preventDefault();
    state.contextTargetId = modelId;
    const menu = document.getElementById("context-menu");
    menu.style.display = "block";
    menu.style.left = `${Math.min(window.innerWidth - 220, e.clientX)}px`;
    menu.style.top = `${Math.min(window.innerHeight - 240, e.clientY)}px`;
  }

  function hideContextMenu() {
    const menu = document.getElementById("context-menu");
    if (menu) menu.style.display = "none";
  }

  // --- Event Listeners Setup ---
  function setupEventListeners() {
    // 1. View preset tabs
    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.onclick = () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        state.activeView = btn.dataset.view;
        state.currentPage = 1;

        if (state.activeView === "scorer") {
          state.sortKey = "custom_score";
          state.sortAsc = false;
        } else if (state.sortKey === "custom_score") {
          state.sortKey = "hf_v2_avg";
          state.sortAsc = false;
        }

        renderTable();
      };
    });

    // 2. Search Input
    const searchInput = document.getElementById("search-input");
    searchInput.oninput = (e) => {
      state.searchQuery = e.target.value;
      state.currentPage = 1;
      renderTable();
    };

    // 3. Quantization Selector
    document.getElementById("quant-select").onchange = (e) => {
      state.currentQuant = e.target.value;
      state.currentPage = 1;
      renderTable();
    };

    // 4. VRAM Slider
    const vramSlider = document.getElementById("vram-slider");
    vramSlider.oninput = (e) => {
      const val = parseInt(e.target.value, 10);
      state.vramBudget = val;
      state.currentPage = 1;
      document.getElementById("vram-val").textContent = val >= 320 ? "All" : `${val} GB`;
      renderTable();
    };

    // 5. Parameter Range
    document.getElementById("min-params").oninput = (e) => {
      state.minParams = e.target.value ? parseFloat(e.target.value) : null;
      state.currentPage = 1;
      renderTable();
    };
    document.getElementById("max-params").oninput = (e) => {
      state.maxParams = e.target.value ? parseFloat(e.target.value) : null;
      state.currentPage = 1;
      renderTable();
    };

    // 6. Reset Filters
    document.getElementById("btn-reset-filters").onclick = () => {
      state.searchQuery = "";
      state.vramBudget = null;
      state.minParams = null;
      state.maxParams = null;
      state.currentQuant = "bf16";
      state.beatModelId = null;
      state.currentPage = 1;
      Object.keys(state.benchmarkThresholds).forEach(k => {
        state.benchmarkThresholds[k] = null;
      });

      searchInput.value = "";
      vramSlider.value = 320;
      document.getElementById("vram-val").textContent = "All";
      document.getElementById("min-params").value = "";
      document.getElementById("max-params").value = "";
      document.getElementById("quant-select").value = "bf16";
      document.getElementById("beat-model-select").value = "";
      document.getElementById("beat-status-badge").style.display = "none";

      ["ifeval", "math", "gpqa", "bbh", "mmlu", "musr", "elo"].forEach(k => {
        const inp = document.getElementById(`min-${k}`);
        if (inp) inp.value = "";
      });

      renderTable();
    };


    // 7. Toggle Advanced Filters Panel
    document.getElementById("btn-toggle-adv-filter").onclick = () => {
      const panel = document.getElementById("advanced-filters-panel");
      panel.classList.toggle("open");
      const btn = document.getElementById("btn-toggle-adv-filter");
      btn.classList.toggle("btn-active", panel.classList.contains("open"));
    };

    // 8. Apply "Beat Model" Filter
    document.getElementById("btn-apply-beat").onclick = () => {
      const sel = document.getElementById("beat-model-select");
      state.beatModelId = sel.value || null;
      state.beatCriteria.all = document.getElementById("beat-all").checked;
      state.beatCriteria.math_hard = document.getElementById("beat-math").checked;
      state.beatCriteria.ifeval = document.getElementById("beat-ifeval").checked;
      state.beatCriteria.gpqa = document.getElementById("beat-gpqa").checked;
      state.beatCriteria.bbh = document.getElementById("beat-bbh").checked;
      state.beatCriteria.mmlu_pro = document.getElementById("beat-mmlu").checked;
      state.beatCriteria.arena_elo = document.getElementById("beat-elo").checked;
      state.beatCriteria.vram = document.getElementById("beat-vram").checked;
      state.currentPage = 1;

      const badge = document.getElementById("beat-status-badge");
      if (state.beatModelId) {
        badge.style.display = "block";
        badge.textContent = `Active Filter: Matching or beating ${state.beatModelId}`;
      } else {
        badge.style.display = "none";
      }
      renderTable();
    };

    document.getElementById("btn-clear-beat").onclick = () => {
      state.beatModelId = null;
      state.currentPage = 1;
      document.getElementById("beat-model-select").value = "";
      document.getElementById("beat-status-badge").style.display = "none";
      renderTable();
    };

    // 9. Benchmark Score Threshold Inputs
    const thresholdMapping = {
      "min-ifeval": "ifeval",
      "min-math": "math_hard",
      "min-gpqa": "gpqa",
      "min-bbh": "bbh",
      "min-mmlu": "mmlu_pro",
      "min-musr": "musr",
      "min-elo": "arena_elo"
    };
    Object.keys(thresholdMapping).forEach(id => {
      const inp = document.getElementById(id);
      if (inp) {
        inp.oninput = (e) => {
          const key = thresholdMapping[id];
          state.benchmarkThresholds[key] = e.target.value ? parseFloat(e.target.value) : null;
          state.currentPage = 1;
          renderTable();
        };
      }
    });


    // 10. Scorer Presets
    document.getElementById("preset-balanced").onclick = () => {
      state.customWeights = { ifeval: 1.0, bbh: 1.0, math_hard: 1.0, gpqa: 1.0, musr: 1.0, mmlu_pro: 1.0, arena_elo: 1.0 };
      renderScorerSliders();
      renderTable();
    };
    document.getElementById("preset-math").onclick = () => {
      state.customWeights = { ifeval: 0.5, bbh: 1.5, math_hard: 3.0, gpqa: 2.5, musr: 0.5, mmlu_pro: 1.2, arena_elo: 0.5 };
      renderScorerSliders();
      renderTable();
    };
    document.getElementById("preset-code").onclick = () => {
      state.customWeights = { ifeval: 2.5, bbh: 1.5, math_hard: 1.8, gpqa: 1.0, musr: 1.5, mmlu_pro: 1.5, arena_elo: 1.0 };
      renderScorerSliders();
      renderTable();
    };
    document.getElementById("preset-chat").onclick = () => {
      state.customWeights = { ifeval: 1.8, bbh: 1.0, math_hard: 0.5, gpqa: 0.8, musr: 1.0, mmlu_pro: 1.0, arena_elo: 3.0 };
      renderScorerSliders();
      renderTable();
    };

    // 11. Header Buttons
    document.getElementById("btn-open-pareto").onclick = showParetoModal;
    document.getElementById("btn-open-audit").onclick = showAuditModal;
    document.getElementById("btn-open-compare").onclick = showCompareModal;

    // Pareto Info Modal
    document.getElementById("btn-pareto-info").onclick = () => {
      openModal("modal-pareto-info");
    };

    // Pareto Metric & Quant Switcher
    document.getElementById("pareto-metric-select").onchange = showParetoModal;
    document.getElementById("pareto-quant-select").onchange = showParetoModal;

    // 12. Table Head: Sorting & Select All
    document.getElementById("table-head").onclick = (e) => {
      const th = e.target.closest("th");
      if (!th) return;

      if (e.target.id === "select-all-cb" || th.querySelector("#select-all-cb")) {
        const visibleModels = getFilteredModels();
        const allSelected = visibleModels.every(m => state.selectedModelIds.has(m.model_id));
        if (allSelected) {
          visibleModels.forEach(m => state.selectedModelIds.delete(m.model_id));
        } else {
          visibleModels.forEach(m => state.selectedModelIds.add(m.model_id));
        }
        renderTable();
        return;
      }

      const sortKey = th.dataset.sort;
      if (!sortKey) return;

      if (state.sortKey === sortKey) {
        state.sortAsc = !state.sortAsc;
      } else {
        state.sortKey = sortKey;
        state.sortAsc = false;
      }
      state.currentPage = 1;
      renderTable();
    };

    // 13. Table Body: RELIABLE DOUBLE-CLICK & SINGLE-CLICK
    const tbody = document.getElementById("table-body");

    // Double-click reliably opens scorecard without DOM re-render disruption
    tbody.ondblclick = (e) => {
      if (e.target.closest("input[type='checkbox']")) return;
      const tr = e.target.closest("tr");
      if (tr && tr.dataset.modelId) {
        showScorecard(tr.dataset.modelId);
      }
    };

    // Single click handles checkboxes or row highlighting WITHOUT re-rendering entire table
    tbody.onclick = (e) => {
      const cb = e.target.closest(".row-select-cb");
      if (cb) {
        const mid = cb.dataset.id;
        if (cb.checked) {
          state.selectedModelIds.add(mid);
        } else {
          state.selectedModelIds.delete(mid);
        }
        updateCompareButton();
        const tr = cb.closest("tr");
        if (tr) tr.classList.toggle("selected", cb.checked);
        return;
      }

      const tr = e.target.closest("tr");
      if (tr && tr.dataset.modelId) {
        // Just mark active row
        tbody.querySelectorAll("tr.active-row").forEach(r => r.classList.remove("active-row"));
        tr.classList.add("active-row");
      }
    };

    // Right-click context menu
    tbody.oncontextmenu = (e) => {
      const tr = e.target.closest("tr");
      if (tr && tr.dataset.modelId) {
        showContextMenu(e, tr.dataset.modelId);
      }
    };

    // 14. Close Modals
    document.querySelectorAll("[data-close]").forEach(el => {
      el.onclick = () => {
        closeModal(el.dataset.close);
      };
    });

    document.querySelectorAll(".modal-overlay").forEach(overlay => {
      overlay.onclick = (e) => {
        if (e.target === overlay) {
          overlay.classList.remove("open");
        }
      };
    });

    // 15. Context Menu Actions
    document.addEventListener("click", hideContextMenu);

    document.getElementById("ctx-open-scorecard").onclick = () => {
      if (state.contextTargetId) showScorecard(state.contextTargetId);
    };

    document.getElementById("ctx-toggle-compare").onclick = () => {
      if (state.contextTargetId) {
        if (state.selectedModelIds.has(state.contextTargetId)) {
          state.selectedModelIds.delete(state.contextTargetId);
        } else {
          state.selectedModelIds.add(state.contextTargetId);
        }
        updateCompareButton();
        const cb = document.querySelector(`.row-select-cb[data-id="${state.contextTargetId}"]`);
        if (cb) {
          cb.checked = state.selectedModelIds.has(state.contextTargetId);
          const tr = cb.closest("tr");
          if (tr) tr.classList.toggle("selected", cb.checked);
        }
      }
    };

    document.getElementById("ctx-set-reference").onclick = () => {
      if (state.contextTargetId) {
        const sel = document.getElementById("beat-model-select");
        sel.value = state.contextTargetId;
        document.getElementById("advanced-filters-panel").classList.add("open");
        document.getElementById("btn-apply-beat").click();
      }
    };

    document.getElementById("ctx-audit-model").onclick = () => {
      showAuditModal();
    };

    document.getElementById("ctx-copy-id").onclick = () => {
      if (state.contextTargetId) {
        navigator.clipboard.writeText(state.contextTargetId);
      }
    };

    document.getElementById("ctx-copy-markdown").onclick = () => {
      if (state.contextTargetId) {
        const m = state.models.find(x => x.model_id === state.contextTargetId);
        if (m) {
          const md = `| Model | Params | HF v2 Avg | Arena Elo | Context |\n| --- | --- | --- | --- | --- |\n| ${m.model_name} | ${m.params_b ? `${m.params_b}B` : 'Proprietary'} | ${m.hf_v2_avg ? m.hf_v2_avg.toFixed(2) : '-'} | ${m.raw_scores ? m.raw_scores.arena_elo || '-' : '-'} | ${m.context_length || '-'} |`;
          navigator.clipboard.writeText(md);
        }
      }
    };

    // 16. Export Table
    document.getElementById("btn-export-table").onclick = () => {
      const models = getSortedModels();
      let md = `| Model | Org | Params | Architecture | HF v2 Avg | Arena Elo |\n| --- | --- | --- | --- | --- | --- |\n`;
      models.forEach(m => {
        md += `| ${m.model_name} | ${m.org} | ${m.params_b ? `${m.params_b}B` : 'Proprietary'} | ${m.architecture || '-'} | ${m.hf_v2_avg ? m.hf_v2_avg.toFixed(2) : '-'} | ${m.raw_scores ? m.raw_scores.arena_elo || '-' : '-'} |\n`;
      });
      navigator.clipboard.writeText(md).then(() => {
        alert("Table exported as Markdown and copied to clipboard!");
      });
    };

    // 17. Delegated click on Pareto / Audit / Scatter dots
    document.addEventListener("click", (e) => {
      const tr = e.target.closest("tr[data-model-id]");
      if (tr && (tr.closest("#pareto-table") || tr.closest("#audit-table"))) {
        showScorecard(tr.dataset.modelId);
      }
      const dot = e.target.closest(".scatter-dot");
      if (dot && dot.dataset.model) {
        showScorecard(dot.dataset.model);
      }
    });

    // 18. Table Pagination Controls
    const btnFirst = document.getElementById("btn-first-page");
    const btnPrev = document.getElementById("btn-prev-page");
    const btnNext = document.getElementById("btn-next-page");
    const btnLast = document.getElementById("btn-last-page");
    const selPageSize = document.getElementById("select-page-size");

    if (btnFirst) btnFirst.onclick = () => {
      state.currentPage = 1;
      renderTable();
    };
    if (btnPrev) btnPrev.onclick = () => {
      if (state.currentPage > 1) {
        state.currentPage--;
        renderTable();
      }
    };
    if (btnNext) btnNext.onclick = () => {
      state.currentPage++;
      renderTable();
    };
    if (btnLast) btnLast.onclick = () => {
      const all = getSortedModels();
      const ps = state.pageSize === "all" ? all.length : parseInt(state.pageSize, 10);
      state.currentPage = Math.max(1, Math.ceil(all.length / (ps || 1)));
      renderTable();
    };
    if (selPageSize) selPageSize.onchange = (e) => {
      state.pageSize = e.target.value;
      state.currentPage = 1;
      renderTable();
    };

  }

  // Launch on DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
