(function () {
  class ADHumanWCAG {
    constructor() {
      // Stage: 0 = auto; 1 = manual
      this.stage = 0;

      // Timers
      this.stage0Timer = null;
      this.idleTimer = null;

      // Settings
      this.STAGE0_DELAY_MS = 5000;     // após 5s: aplica automático e avisa
      this.IDLE_TO_STAGE1_MS = 10000;  // 10s sem atividade: habilita modo manual

      // Runtime
      this.findings = [];             // [{el, ratio, threshold}]
      this.manualModeOn = false;
      this.manualTarget = null;

      this.injectStyles();
      this.injectUI();

      // agenda estágio 0
      this.scheduleStage0();

      // monitora atividade / inatividade
      this.bindActivityListeners();
      this.resetIdleTimer("init");
      this.observeDomChanges();
    }

    /* =========================
       STYLES
    ========================= */
    injectStyles() {
      const style = document.createElement("style");
      style.id = "adhuman-wcag-143-styles";
      style.innerHTML = `
        .adhuman-flag {
          outline: 2px dashed rgba(255, 0, 0, .75) !important;
          outline-offset: 2px !important;
        }

        .adhuman-fixed {
          text-shadow: none !important;
          box-shadow: none !important;
          filter: none !important;
        }

        .adhuman-ui-btn {
          position: fixed;
          right: 16px;
          bottom: 16px;
          z-index: 2147483647;
          font: 600 13px/1.2 system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
          border: 1px solid rgba(0,0,0,.25);
          border-radius: 999px;
          background: #fff;
          color: #000;
          padding: 10px 12px;
          cursor: pointer;
          box-shadow: 0 6px 20px rgba(0,0,0,.15);
          user-select: none;
        }

        .adhuman-ui-panel {
          position: fixed;
          right: 16px;
          bottom: 64px;
          width: 320px;
          z-index: 2147483647;
          font: 13px/1.35 system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
          border: 1px solid rgba(0,0,0,.25);
          border-radius: 14px;
          background: #fff;
          color: #000;
          padding: 12px;
          box-shadow: 0 10px 26px rgba(0,0,0,.18);
          display: none;
        }
        .adhuman-ui-panel[aria-hidden="false"] { display: block; }

        .adhuman-ui-actions { display:flex; gap:8px; margin-top:10px; }
        .adhuman-ui-actions button {
          flex:1;
          font: 600 13px/1.2 system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
          border: 1px solid rgba(0,0,0,.25);
          border-radius: 10px;
          padding: 8px 10px;
          background: #fff;
          cursor: pointer;
        }

        .adhuman-toast {
          position: fixed;
          left: 16px;
          bottom: 16px;
          z-index: 2147483647;
          max-width: 520px;
          font: 13px/1.35 system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
          border: 1px solid rgba(0,0,0,.25);
          border-radius: 12px;
          background: #fff;
          color: #000;
          padding: 10px 12px;
          box-shadow: 0 10px 26px rgba(0,0,0,.18);
          display: none;
        }
        .adhuman-toast[aria-hidden="false"] { display:block; }

        /* Mini popover (Stage 1 manual) */
        .adhuman-popover {
          position: fixed;
          z-index: 2147483647;
          background: #fff;
          border: 1px solid rgba(0,0,0,.25);
          border-radius: 12px;
          box-shadow: 0 10px 26px rgba(0,0,0,.18);
          padding: 10px;
          width: 280px;
          display: none;
          font: 13px/1.35 system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
          color: #000;
        }
        .adhuman-popover[aria-hidden="false"] { display:block; }
        .adhuman-popover .title { font-weight: 700; margin-bottom: 8px; }
        .adhuman-popover .btnrow { display:flex; gap:8px; margin-top:8px; }
        .adhuman-popover button {
          flex: 1;
          font: 600 13px/1.2 system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
          border: 1px solid rgba(0,0,0,.25);
          border-radius: 10px;
          padding: 8px 10px;
          background: #fff;
          cursor: pointer;
        }
        .adhuman-kbd { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; font-size: 12px; }
      `;
      document.head.appendChild(style);
    }

    /* =========================
       UI
    ========================= */
    injectUI() {
      // Toggle button
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "adhuman-ui-btn";
      btn.setAttribute("aria-label", "ADHuman WCAG 1.4.3: abrir painel");
      btn.addEventListener("click", () => this.togglePanel());
      document.documentElement.appendChild(btn);
      this.btn = btn;

      // Panel
      const panel = document.createElement("div");
      panel.className = "adhuman-ui-panel";
      panel.setAttribute("aria-hidden", "true");
      panel.innerHTML = `
        <div style="font-weight:700; margin-bottom:6px;">WCAG 1.4.3 — Contraste</div>

        <div style="opacity:.9">
          <div><strong>Estágio atual:</strong> <span id="adhuman-stage">0</span></div>
          <div style="margin-top:6px;"><strong>Itens marcados:</strong> <span id="adhuman-marked">0</span></div>
          <div style="margin-top:6px;"><strong>Itens modificados:</strong> <span id="adhuman-modified">0</span></div>
          <div style="margin-top:6px;">
            <strong>Regras:</strong><br/>
            • Após <span class="adhuman-kbd">5s</span>: Estágio 0 (auto) + aviso<br/>
            • Após <span class="adhuman-kbd">10s</span> sem atividade: Estágio 1 (manual)
          </div>
          <div style="margin-top:6px;">
            No Estágio 1, clique em um item marcado para ajustar.<br/>
            <span class="adhuman-kbd">Esc</span> fecha o ajuste manual.
          </div>
        </div>

        <div class="adhuman-ui-actions">
          <button id="adhuman-rescan" type="button">Reanalisar</button>
          <button id="adhuman-reset" type="button">Reverter</button>
        </div>
      `;
      document.documentElement.appendChild(panel);
      this.panel = panel;

      // Toast
      const toast = document.createElement("div");
      toast.className = "adhuman-toast";
      toast.setAttribute("aria-hidden", "true");
      document.documentElement.appendChild(toast);
      this.toast = toast;

      // Popover (Stage 1 manual)
      const pop = document.createElement("div");
      pop.className = "adhuman-popover";
      pop.setAttribute("aria-hidden", "true");
      pop.innerHTML = `
        <div class="title">Ajuste manual (1.4.3)</div>
        <div style="opacity:.85">
          Escolha uma correção rápida para o elemento selecionado:
        </div>
        <div class="btnrow">
          <button id="adhuman-manual-auto" type="button">Auto (texto)</button>
          <button id="adhuman-manual-bw" type="button">Preto/Branco</button>
        </div>
        <div class="btnrow">
          <button id="adhuman-manual-revert" type="button">Reverter</button>
          <button id="adhuman-manual-close" type="button">Fechar</button>
        </div>
      `;
      document.documentElement.appendChild(pop);
      this.popover = pop;

      // Panel buttons
      panel.querySelector("#adhuman-rescan").addEventListener("click", () => {
        this.resetMitigations();
        // reexecuta: marca tudo; se já passou 5s, pode reaplicar auto no estágio 0
        // aqui, vamos respeitar o estágio atual:
        if (this.stage === 0) this.runStage0(true);
        else this.runStage1(true);
      });

      panel.querySelector("#adhuman-reset").addEventListener("click", () => {
        this.resetMitigations();
        this.modifiedCount = 0;
        this.findings = [];
        this.updatePanel();
        this.hideToast();
        this.hidePopover();
      });

      // Popover buttons
      pop.querySelector("#adhuman-manual-auto").addEventListener("click", () => {
        if (!this.manualTarget) return;
        this.applyBestTextColor(this.manualTarget, true);
        this.recheckAndFlag(this.manualTarget);
        this.afterManualAction();
      });

      pop.querySelector("#adhuman-manual-bw").addEventListener("click", () => {
        if (!this.manualTarget) return;
        this.applyBlackWhitePair(this.manualTarget, true);
        this.recheckAndFlag(this.manualTarget);
        this.afterManualAction();
      });

      pop.querySelector("#adhuman-manual-revert").addEventListener("click", () => {
        if (!this.manualTarget) return;
        this.revertElement(this.manualTarget);
        this.recheckAndFlag(this.manualTarget);
        this.afterManualAction();
      });

      pop.querySelector("#adhuman-manual-close").addEventListener("click", () => this.hidePopover());

      window.addEventListener("keydown", (e) => {
        if (e.key === "Escape") this.hidePopover();
      });

      this.modifiedCount = 0;
      this.updatePanel();
    }

    togglePanel() {
      const isHidden = this.panel.getAttribute("aria-hidden") !== "false";
      this.panel.setAttribute("aria-hidden", isHidden ? "false" : "true");
    }

    updatePanel() {
      if (!this.panel) return;
      const stageEl = this.panel.querySelector("#adhuman-stage");
      const markedEl = this.panel.querySelector("#adhuman-marked");
      const modifiedEl = this.panel.querySelector("#adhuman-modified");

      if (stageEl) stageEl.textContent = String(this.stage);
      if (markedEl) markedEl.textContent = String(document.querySelectorAll(".adhuman-flag").length);
      if (modifiedEl) modifiedEl.textContent = String(this.modifiedCount || 0);

      this.btn.textContent = this.stage === 0 ? "1.4.3 • Estágio 0" : "1.4.3 • Estágio 1";
    }

    showToast(msg, ms = 5500) {
      this.toast.textContent = msg;
      this.toast.setAttribute("aria-hidden", "false");
      clearTimeout(this.toastTimer);
      this.toastTimer = setTimeout(() => this.hideToast(), ms);
    }

    hideToast() {
      if (this.toast) this.toast.setAttribute("aria-hidden", "true");
    }

    showPopoverNear(x, y) {
      const pad = 12;
      const w = 280;
      const h = 185;
      const left = Math.max(pad, Math.min(x - w / 2, window.innerWidth - w - pad));
      const top = Math.max(pad, Math.min(y - h - 12, window.innerHeight - h - pad));
      this.popover.style.left = `${left}px`;
      this.popover.style.top = `${top}px`;
      this.popover.setAttribute("aria-hidden", "false");
    }

    hidePopover() {
      if (this.popover) this.popover.setAttribute("aria-hidden", "true");
      this.manualTarget = null;
    }

    afterManualAction() {
      const remaining = document.querySelectorAll(".adhuman-flag").length;
      this.updatePanel();
      if (remaining > 0) this.showToast(`Ajuste manual aplicado. Ainda restam ${remaining} item(ns) marcados.`, 3500);
      else this.showToast("Ajuste manual aplicado. Nenhum item marcado restante.", 3500);
    }

    /* =========================
       STAGE 0 (auto after 5s)
    ========================= */
    scheduleStage0() {
      clearTimeout(this.stage0Timer);
      this.stage0Timer = setTimeout(() => {
        // Executa estágio 0 exatamente uma vez (ou você pode permitir reexecução via "Reanalisar")
        if (this.stage !== 0) return;
        this.runStage0(false);
      }, this.STAGE0_DELAY_MS);
    }

    runStage0(userInitiated = false) {
      this.stage = 0;

      // Detecta e marca
      this.findings = this.scanContrastFailures();
      this.flagAllFindings();

      // Aplica correção automática (texto com melhor contraste)
      let changed = 0;
      for (const f of this.findings) {
        if (!f.el) continue;

        // só conta como "modificado" se a operação realmente aplicar nosso marker
        const before = f.el.getAttribute("data-adhuman-143") === "1";
        this.applyBestTextColor(f.el, true);
        const after = f.el.getAttribute("data-adhuman-143") === "1";
        if (!before && after) changed++;

        this.recheckAndFlag(f.el);
      }

      this.modifiedCount = (this.modifiedCount || 0) + changed;
      this.updatePanel();

      // aviso ao humano
      if (this.findings.length === 0) {
        if (userInitiated) this.showToast("Estágio 0: nenhum problema de contraste detectado (1.4.3).");
      } else {
        this.showToast(`Estágio 0: adaptação automática aplicada. Itens modificados agora: ${this.modifiedCount}.`);
      }
    }

    /* =========================
       STAGE 1 (manual after 10s idle)
    ========================= */
    runStage1(userInitiated = false) {
      this.stage = 1;

      // Re-scan + flag para garantir que o humano veja os itens
      this.findings = this.scanContrastFailures();
      this.flagAllFindings();

      this.enableManualMode();
      this.updatePanel();

      if (userInitiated) {
        this.showToast(`Estágio 1: modo manual ativado. Itens marcados: ${document.querySelectorAll(".adhuman-flag").length}.`, 4500);
      } else {
        this.showToast("Estágio 1: inatividade detectada. Modo manual ativado para ajustes.", 5000);
      }
    }

    bindActivityListeners() {
      // mouse, teclado, scroll e touch contam como atividade
      const activity = () => this.resetIdleTimer("activity");
      this.activityHandler = activity;

      window.addEventListener("mousemove", activity, { passive: true });
      window.addEventListener("mousedown", activity, { passive: true });
      window.addEventListener("keydown", activity, { passive: true });
      window.addEventListener("scroll", activity, { passive: true });
      window.addEventListener("touchstart", activity, { passive: true });
    }

    resetIdleTimer(reason) {
      // Se já estamos no estágio 1, não precisamos ficar rearmando a troca automática.
      if (this.stage === 1) return;

      clearTimeout(this.idleTimer);
      this.idleTimer = setTimeout(() => {
        // Após 10s sem atividade -> estágio 1
        if (this.stage !== 1) this.runStage1(false);
      }, this.IDLE_TO_STAGE1_MS);

      void reason;
    }

    /* =========================
       DOM Changes (SPA)
    ========================= */
    observeDomChanges() {
      let t = null;
      const schedule = () => {
        if (t) clearTimeout(t);
        t = setTimeout(() => {
          // se o DOM muda, atualiza flags (não “força” estágios)
          this.clearFlagsOnly();
          this.findings = this.scanContrastFailures();
          this.flagAllFindings();
          this.updatePanel();
        }, 400);
      };
      const obs = new MutationObserver(schedule);
      obs.observe(document.documentElement, { childList: true, subtree: true, attributes: true });
      this.domObserver = obs;
    }

    /* =========================
       MANUAL MODE (Stage 1)
    ========================= */
    enableManualMode() {
      if (this.manualModeOn) return;
      this.manualModeOn = true;

      this.manualClickHandler = (e) => {
        const target = e.target;
        if (!(target instanceof Element)) return;

        // Só permite ajustar elemento marcado
        if (!target.classList.contains("adhuman-flag")) return;

        e.preventDefault();
        e.stopPropagation();

        this.manualTarget = target;
        this.showPopoverNear(e.clientX, e.clientY);
      };

      document.addEventListener("click", this.manualClickHandler, true);
    }

    disableManualMode() {
      if (!this.manualModeOn) return;
      this.manualModeOn = false;
      if (this.manualClickHandler) {
        document.removeEventListener("click", this.manualClickHandler, true);
        this.manualClickHandler = null;
      }
    }

    /* =========================
       RESET / REVERT
    ========================= */
    resetMitigations() {
      this.clearFlagsOnly();
      document.querySelectorAll("[data-adhuman-143='1']").forEach(el => this.revertElement(el));
      this.disableManualMode();
      this.hidePopover();
      this.hideToast();
      this.updatePanel();
    }

    clearFlagsOnly() {
      document.querySelectorAll(".adhuman-flag").forEach(el => el.classList.remove("adhuman-flag"));
    }

    revertElement(el) {
      if (!el || el.getAttribute("data-adhuman-143") !== "1") return;

      el.style.removeProperty("color");
      el.style.removeProperty("background-color");
      el.style.removeProperty("text-shadow");
      el.style.removeProperty("box-shadow");
      el.style.removeProperty("filter");

      el.removeAttribute("data-adhuman-143");
      el.removeAttribute("data-adhuman-orig-color");
      el.removeAttribute("data-adhuman-orig-bg");
      el.removeAttribute("data-adhuman-orig-ts");
      el.removeAttribute("data-adhuman-orig-bs");
      el.removeAttribute("data-adhuman-orig-filter");
    }

    /* =========================
       DETECTION (SCAN)
    ========================= */
    scanContrastFailures() {
      const findings = [];
      const root = document.body || document.documentElement;
      if (!root) return findings;

      const walker = document.createTreeWalker(
        root,
        NodeFilter.SHOW_TEXT,
        {
          acceptNode: (node) => {
            const t = (node.nodeValue || "").trim();
            if (!t) return NodeFilter.FILTER_REJECT;

            const el = node.parentElement;
            if (!el) return NodeFilter.FILTER_REJECT;

            const cs = getComputedStyle(el);
            if (!cs) return NodeFilter.FILTER_REJECT;

            if (cs.display === "none" || cs.visibility === "hidden" || parseFloat(cs.opacity || "1") === 0) {
              return NodeFilter.FILTER_REJECT;
            }

            return NodeFilter.FILTER_ACCEPT;
          }
        }
      );

      const visited = new Set();
      let node;

      while ((node = walker.nextNode())) {
        const el = node.parentElement;
        if (!el || visited.has(el)) continue;
        visited.add(el);

        const cs = getComputedStyle(el);
        const fg = this.parseColor(cs.color);
        const bg = this.getEffectiveBackgroundColor(el);

        if (!fg || !bg) continue;

        const ratio = this.calculateContrast(fg, bg);

        const fontSizePx = parseFloat(cs.fontSize || "16");
        const fontWeight = parseInt(cs.fontWeight || "400", 10);
        const isBold = !Number.isNaN(fontWeight) && fontWeight >= 700;
        const isLargeText = fontSizePx >= 24 || (isBold && fontSizePx >= 18.66);
        const threshold = isLargeText ? 3.0 : 4.5;

        if (ratio < threshold) {
          findings.push({ el, ratio, threshold });
        }
      }

      return findings;
    }

    flagAllFindings() {
      for (const f of this.findings) {
        if (f.el && f.el.classList) f.el.classList.add("adhuman-flag");
      }
    }

    recheckAndFlag(el) {
      if (!el) return;
      const cs = getComputedStyle(el);
      const fg = this.parseColor(cs.color);
      const bg = this.getEffectiveBackgroundColor(el);
      if (!fg || !bg) return;

      const ratio = this.calculateContrast(fg, bg);
      const fontSizePx = parseFloat(cs.fontSize || "16");
      const fontWeight = parseInt(cs.fontWeight || "400", 10);
      const isBold = !Number.isNaN(fontWeight) && fontWeight >= 700;
      const isLargeText = fontSizePx >= 24 || (isBold && fontSizePx >= 18.66);
      const threshold = isLargeText ? 3.0 : 4.5;

      if (ratio < threshold) el.classList.add("adhuman-flag");
      else el.classList.remove("adhuman-flag");

      this.updatePanel();
    }

    /* =========================
       FIXES
    ========================= */
    ensureOriginalsStored(el) {
      if (el.getAttribute("data-adhuman-143") === "1") return;

      const cs = getComputedStyle(el);
      el.setAttribute("data-adhuman-143", "1");
      el.setAttribute("data-adhuman-orig-color", cs.color || "");
      el.setAttribute("data-adhuman-orig-bg", cs.backgroundColor || "");
      el.setAttribute("data-adhuman-orig-ts", cs.textShadow || "");
      el.setAttribute("data-adhuman-orig-bs", cs.boxShadow || "");
      el.setAttribute("data-adhuman-orig-filter", cs.filter || "");
    }

    // Auto (menos intrusivo): ajusta só texto para melhor contraste com o bg efetivo
    applyBestTextColor(el, storeOrig = false) {
      if (!el) return;
      if (storeOrig) this.ensureOriginalsStored(el);

      const bg = this.getEffectiveBackgroundColor(el);
      if (!bg) return;

      const black = [0, 0, 0];
      const white = [255, 255, 255];

      const rBlack = this.calculateContrast(black, bg);
      const rWhite = this.calculateContrast(white, bg);

      const best = rBlack >= rWhite ? "#000" : "#fff";

      el.classList.add("adhuman-fixed");
      el.style.setProperty("color", best, "important");
      el.style.setProperty("text-shadow", "none", "important");
      el.style.setProperty("box-shadow", "none", "important");
      el.style.setProperty("filter", "none", "important");
    }

    // Manual (mais forte): força texto+fundo preto/branco
    applyBlackWhitePair(el, storeOrig = false) {
      if (!el) return;
      if (storeOrig) this.ensureOriginalsStored(el);

      const bg = this.getEffectiveBackgroundColor(el);
      if (!bg) return;

      const black = [0, 0, 0];
      const white = [255, 255, 255];

      const rBlack = this.calculateContrast(black, bg);
      const rWhite = this.calculateContrast(white, bg);

      const textIsBlack = rBlack >= rWhite;
      const text = textIsBlack ? "#000" : "#fff";
      const back = textIsBlack ? "#fff" : "#000";

      el.classList.add("adhuman-fixed");
      el.style.setProperty("color", text, "important");
      el.style.setProperty("background-color", back, "important");
      el.style.setProperty("text-shadow", "none", "important");
      el.style.setProperty("box-shadow", "none", "important");
      el.style.setProperty("filter", "none", "important");
    }

    /* =========================
       COLOR HELPERS
    ========================= */
    getEffectiveBackgroundColor(el) {
      let node = el;
      while (node && node.nodeType === 1) {
        const cs = getComputedStyle(node);
        if (!cs) break;

        const bg = cs.backgroundColor;

        // transparente / rgba(0,0,0,0)
        if (bg && bg !== "transparent" && !bg.startsWith("rgba(0, 0, 0, 0")) {
          const parsed = this.parseColor(bg);
          if (parsed) return parsed;
        }
        node = node.parentElement;
      }
      return [255, 255, 255];
    }

    parseColor(color) {
      if (!color) return null;

      if (color.startsWith("rgb")) {
        const match = color.match(/\d+(\.\d+)?/g);
        if (!match) return null;
        return match.slice(0, 3).map((v) =>
          Math.max(0, Math.min(255, Math.round(Number(v))))
        );
      }

      if (color[0] === "#") {
        const hex = color.slice(1).trim();
        if (hex.length === 3) {
          return [
            parseInt(hex[0] + hex[0], 16),
            parseInt(hex[1] + hex[1], 16),
            parseInt(hex[2] + hex[2], 16)
          ];
        }
        if (hex.length === 6) {
          return [
            parseInt(hex.slice(0, 2), 16),
            parseInt(hex.slice(2, 4), 16),
            parseInt(hex.slice(4, 6), 16)
          ];
        }
      }

      return null;
    }

    luminance([r, g, b]) {
      const a = [r, g, b].map((v) => {
        v /= 255;
        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2];
    }

    calculateContrast(fg, bg) {
      const L1 = this.luminance(fg);
      const L2 = this.luminance(bg);
      return (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    }
  }

  window.ADHumanWCAG = ADHumanWCAG;
})();