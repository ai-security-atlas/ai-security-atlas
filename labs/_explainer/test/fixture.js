/* Minimal second explainer for the embed test page (two instances, different ids). Not a lab. */
(() => {
  const X = Explainer, S = X.svg, V = X.v;
  const steps = ["System", "Attack", "Mechanism", "Impact", "Defense", "Defense"].map((chapter, i) => ({
    chapter, label: "Fixture " + (i + 1), caption: `Fixture caption ${i + 1}: the dot moves to column ${i + 1}.`,
  }));
  X.define({
    id: "test-fixture", family: "family-test", title: 'Test <span class="outline">fixture</span>', legend: ["teal"], steps,
    html: `<svg viewBox="0 0 960 540" width="960" height="540"></svg><div class="abs pill" data-only="4" style="left:700px;top:60px">impact</div>`,
    setup(el, api) {
      const svg = el.querySelector("svg");
      const dot = S("circle", { cx: 120, cy: 270, r: 30, fill: V("teal") }, svg);
      S("text", { x: 480, y: 470, "text-anchor": "middle", "font-size": 22, text: "fixture" }, svg);
      const st = { x: 0 };
      const target = n => ({ x: n - 1 });
      const draw = s => dot.setAttribute("cx", (120 + s.x * 140).toFixed(2));
      let gen = 0;
      return {
        step(n, dir) {
          const to = target(n), from = { ...st }, g = ++gen;
          if (dir !== 1 || api.reduced) { Object.assign(st, to); return draw(st); }
          return api.tween(500, k => { if (g !== gen) return; X.lerpState(st, from, to, k); draw(st); }, X.ease.inOut);
        },
      };
    },
  });
})();
