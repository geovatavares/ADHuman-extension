(() => {
  function parseColor(value) {
    if (!value) return null;
    const m = value.match(/rgba?\(([^)]+)\)/i);
    if (!m) return null;
    const parts = m[1].split(',').map(x => x.trim());
    if (parts.length < 3) return null;
    const rgb = parts.slice(0, 3).map(Number);
    if (rgb.some(Number.isNaN)) return null;
    const a = parts.length >= 4 ? Number(parts[3]) : 1;
    return {r: rgb[0], g: rgb[1], b: rgb[2], a: Number.isNaN(a) ? 1 : a};
  }

  function blend(fg, bg) {
    const a = fg.a + bg.a * (1 - fg.a);
    if (a <= 0) return {r:255,g:255,b:255,a:1};
    return {
      r: (fg.r * fg.a + bg.r * bg.a * (1 - fg.a)) / a,
      g: (fg.g * fg.a + bg.g * bg.a * (1 - fg.a)) / a,
      b: (fg.b * fg.a + bg.b * bg.a * (1 - fg.a)) / a,
      a
    };
  }

  function effectiveBackground(el) {
    let node = el;
    let bg = {r:255,g:255,b:255,a:1};
    const stack = [];
    while (node && node.nodeType === 1) {
      const cs = getComputedStyle(node);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') {
        return {color: bg, uncertain: true};
      }
      const c = parseColor(cs.backgroundColor);
      if (c && c.a > 0) stack.push(c);
      node = node.parentElement;
    }
    for (let i = stack.length - 1; i >= 0; i--) bg = blend(stack[i], bg);
    return {color: bg, uncertain: false};
  }

  function relLum(c) {
    const f = v => {
      v = v / 255;
      return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  }

  function ratio(a, b) {
    const l1 = relLum(a), l2 = relLum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  }

  function isVisible(el) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  function hasDirectText(el) {
    for (const n of el.childNodes) {
      if (n.nodeType === Node.TEXT_NODE && n.textContent.trim().length > 0) return true;
    }
    return false;
  }

  const ratios = [];
  const failures = [];
  let skippedBackgroundImage = 0;
  let skippedTransparentText = 0;
  let assessed = 0;

  for (const el of document.querySelectorAll('body *')) {
    if (!isVisible(el) || !hasDirectText(el)) continue;
    const cs = getComputedStyle(el);
    const fg = parseColor(cs.color);
    if (!fg || fg.a <= 0) { skippedTransparentText++; continue; }
    const bgInfo = effectiveBackground(el);
    if (bgInfo.uncertain) { skippedBackgroundImage++; continue; }
    const effectiveFg = fg.a < 1 ? blend(fg, bgInfo.color) : fg;
    const cr = ratio(effectiveFg, bgInfo.color);
    const fontPx = parseFloat(cs.fontSize || '16');
    const weight = parseInt(cs.fontWeight, 10) || (cs.fontWeight === 'bold' ? 700 : 400);
    const large = fontPx >= 24 || (fontPx >= 18.66 && weight >= 700);
    const threshold = large ? 3.0 : 4.5;
    assessed++;
    ratios.push(cr);
    if (cr + 1e-9 < threshold) {
      failures.push({
        tag: el.tagName,
        ratio: Number(cr.toFixed(3)),
        threshold,
        font_px: Number(fontPx.toFixed(2)),
        text: (el.textContent || '').trim().slice(0, 120)
      });
    }
  }

  ratios.sort((a,b) => a-b);
  const mean = ratios.length ? ratios.reduce((a,b)=>a+b,0)/ratios.length : null;
  const median = ratios.length ? ratios[Math.floor(ratios.length/2)] : null;
  return {
    assessed_text_elements: assessed,
    contrast_failures: failures.length,
    contrast_ratio_min: ratios.length ? Number(ratios[0].toFixed(3)) : null,
    contrast_ratio_mean: mean == null ? null : Number(mean.toFixed(3)),
    contrast_ratio_median: median == null ? null : Number(median.toFixed(3)),
    skipped_background_image: skippedBackgroundImage,
    skipped_transparent_text: skippedTransparentText,
    sample_failures: failures.slice(0, 10)
  };
})()
