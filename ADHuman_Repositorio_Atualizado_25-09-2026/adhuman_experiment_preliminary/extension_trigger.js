(async () => {
  const ctx = window.__ADHUMAN_EXPERIMENT__ || {};
  const timeoutMs = Number(ctx.adaptation_wait_ms || 180000);

  const result = await new Promise((resolve) => {
    let finished = false;
    const done = (payload) => {
      if (finished) return;
      finished = true;
      window.removeEventListener('message', listener);
      resolve(payload);
    };
    const listener = (event) => {
      if (event.source !== window) return;
      const data = event.data || {};
      if (data.type !== 'ADHUMAN_EXPERIMENT_RESULT') return;
      if (data.run_id && ctx.run_id && data.run_id !== ctx.run_id) return;
      done(Object.assign({ok: true, integration: 'postMessage'}, data.result || {}));
    };
    window.addEventListener('message', listener);
    window.postMessage({
      type: 'ADHUMAN_EXPERIMENT_RUN',
      run_id: ctx.run_id,
      profile: ctx.profile,
      website: ctx.website,
      classifier: ctx.classifier,
      model: ctx.model
    }, '*');
    setTimeout(() => done({
      ok: false,
      integration: 'none',
      error: 'ADHuman experiment bridge did not answer before timeout.'
    }), timeoutMs);
  });

  return result;
})()
