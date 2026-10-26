/* Shipped reference run for this lab's explainer. Loaded with a plain <script> tag (never fetch: it breaks
 * file://). Regenerate it from a reference container run with scripts/export_explainer_data.py; a student's
 * own work/ folder never changes it. Replace these example fields with the lab's schema (spec §3.5/§3.6). */
window.LAB_DATA = {
  canary: "CANARY-0000",                       // the lab's fixed canary (README front matter `canary:`)
  input: ["describe", "the", "photo"],         // trusted part of the input
  injected: "+ hidden payload",                // attacker-controlled part
  clean_output: "a red cube on a table",       // output without the attack
  evaluate: { trials: 10, canary_hits: 0 },    // defended run, from evaluate.py
};
