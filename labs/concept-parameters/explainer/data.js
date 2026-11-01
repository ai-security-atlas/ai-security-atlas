/* LAB-39 concept-parameters reference run, exported by scripts/export_explainer_data.py. */
window.LAB_DATA = {
 "canary": "ATLAS-CANARY-w8ts",
 "model": "HuggingFaceTB/SmolLM2-135M-Instruct",
 "revision": "12fd25f77366",
 "header": {
  "files": 12,
  "pinned_match": 12,
  "pinned_total": 12,
  "header_bytes": 30528,
  "tensors": 272,
  "dtypes": [
   "BF16"
  ],
  "params": 134515008,
  "data_bytes": 269030016,
  "size": 269060552,
  "torch_loaded": false,
  "tied": true,
  "hidden": 576,
  "layers": 30,
  "inter": 1536
 },
 "groups": {
  "embed_tokens": {
   "tensors": 1,
   "params": 28311552
  },
  "30 decoder blocks": {
   "tensors": 270,
   "params": 106202880
  },
  "norm": {
   "tensors": 1,
   "params": 576
  }
 },
 "block": [
  [
   "input_layernorm.weight",
   [
    576
   ]
  ],
  [
   "mlp.down_proj.weight",
   [
    576,
    1536
   ]
  ],
  [
   "mlp.gate_proj.weight",
   [
    1536,
    576
   ]
  ],
  [
   "mlp.up_proj.weight",
   [
    1536,
    576
   ]
  ],
  [
   "post_attention_layernorm.weight",
   [
    576
   ]
  ],
  [
   "self_attn.k_proj.weight",
   [
    192,
    576
   ]
  ],
  [
   "self_attn.o_proj.weight",
   [
    576,
    576
   ]
  ],
  [
   "self_attn.q_proj.weight",
   [
    576,
    576
   ]
  ],
  [
   "self_attn.v_proj.weight",
   [
    192,
    576
   ]
  ]
 ],
 "sha": "5af571cbf074",
 "act": {
  "prompts": [
   "The cat sat on the",
   "Quarterly revenue grew by eight"
  ],
  "tokens": [
   5,
   7
  ],
  "same_weights": true,
  "sha": "1d18bb822708",
  "n_act": [
   86400,
   120960
  ],
  "next": [
   " window",
   " percent"
  ],
  "repeat": 0.0,
  "rel": [
   1.684,
   0.783,
   0.936,
   0.932,
   0.923,
   0.92,
   0.919,
   0.917,
   0.897,
   0.843,
   1.069,
   1.147,
   1.041,
   1.009,
   0.964,
   0.969,
   0.937,
   0.94,
   0.966,
   0.942,
   0.933,
   0.918,
   1.02,
   1.043,
   0.954,
   0.943,
   0.98,
   0.98,
   0.951,
   1.06
  ],
  "norm_a": [
   34.2,
   124.9,
   652.9,
   651.5,
   649.3,
   644.5,
   640.0,
   633.7,
   580.5,
   306.8,
   113.7,
   105.8,
   121.3,
   142.7,
   151.9,
   160.6,
   179.2,
   181.0,
   181.9,
   203.6,
   233.4,
   275.3,
   323.4,
   374.2,
   458.2,
   524.8,
   568.8,
   670.4,
   740.2,
   801.5
  ],
  "norm_b": [
   56.8,
   78.2,
   85.9,
   91.8,
   102.2,
   103.5,
   109.1,
   115.3,
   126.7,
   134.9,
   150.9,
   136.8,
   137.6,
   160.8,
   165.1,
   179.0,
   194.2,
   195.4,
   205.3,
   226.4,
   248.7,
   285.2,
   337.5,
   396.8,
   444.1,
   503.8,
   540.0,
   652.3,
   745.8,
   842.1
  ]
 },
 "edit": {
  "tensor": "model.layers.15.mlp.down_proj.weight",
  "shape": [
   576,
   1536
  ],
  "steps": 40,
  "rows": 12,
  "loss0": 7.6309,
  "loss1": 0.0028,
  "changed": 877807,
  "numel": 884736,
  "rel_norm": 0.156,
  "header_same": true,
  "size": [
   269060552,
   269060552
  ],
  "sha": [
   "5af571cbf074",
   "0d241f9befa0"
  ],
  "layer": 15
 },
 "routes": {
  "k": {
   "plain": 0,
   "hook": 5,
   "edited": 5,
   "after": 0
  },
  "n": 5,
  "same": 5,
  "logit_gap": 5.340576171875e-05,
  "route_gap": 0.0009002685546875,
  "diff": [
   0.0,
   0.0,
   0.0,
   0.0,
   0.0,
   0.0,
   0.0,
   0.0,
   0.0,
   0.0,
   0.0,
   0.0,
   0.0,
   0.0,
   0.0,
   6.59,
   15.58,
   19.0,
   26.7,
   34.36,
   49.68,
   65.71,
   104.03,
   106.44,
   120.53,
   124.41,
   132.01,
   152.33,
   159.43,
   413.22
  ],
  "first": 15,
  "sha_same": true,
  "probe": "Name a primary color.",
  "plain": "The primary color is typically considered to be the primary ",
  "hook": "ATLAS-CANARY-w8ts"
 },
 "persist": [
  {
   "label": "pinned snapshot (Step 4 hooked this one)",
   "k": 0,
   "n": 5
  },
  {
   "label": "work/edited/, session 1",
   "k": 5,
   "n": 5
  },
  {
   "label": "work/edited/, session 2",
   "k": 5,
   "n": 5
  },
  {
   "label": "work/edited/, session 3",
   "k": 5,
   "n": 5
  },
  {
   "label": "save_pretrained copy of work/edited/",
   "k": 5,
   "n": 5
  },
  {
   "label": "NF4 4-bit copy of that copy",
   "k": 4,
   "n": 5
  }
 ],
 "persist_sha": {
  "pinned": "5af571cbf074",
  "edited": "0d241f9befa0",
  "resaved": "0d241f9befa0"
 },
 "manifest": [
  {
   "folder": "pinned snapshot",
   "verdict": "MATCH",
   "bad": [],
   "loaded": true,
   "k": 0
  },
  {
   "folder": "work/edited/ (Step 3)",
   "verdict": "MISMATCH",
   "bad": [
    "model.safetensors"
   ],
   "loaded": false,
   "k": null
  },
  {
   "folder": "pinned snapshot + hook after load",
   "verdict": "MATCH",
   "bad": [],
   "loaded": true,
   "k": 5
  }
 ],
 "runtime": [
  {
   "state": "clean (verified load)",
   "audit_ok": true,
   "probe_ok": true,
   "k": 0,
   "same": 5,
   "verdict": "PASS",
   "finding": ""
  },
  {
   "state": "module forward hook (Step 4)",
   "audit_ok": false,
   "probe_ok": false,
   "k": 5,
   "same": 0,
   "verdict": "FAIL",
   "finding": "layers.15.mlp.down_proj forward hook"
  },
  {
   "state": "instance forward override",
   "audit_ok": false,
   "probe_ok": false,
   "k": 5,
   "same": 0,
   "verdict": "FAIL",
   "finding": "layers.15.mlp.down_proj forward override"
  },
  {
   "state": "global module hook",
   "audit_ok": false,
   "probe_ok": false,
   "k": 5,
   "same": 0,
   "verdict": "FAIL",
   "finding": "<all modules> global forward hook"
  },
  {
   "state": "patched torch.nn.functional.linear",
   "audit_ok": true,
   "probe_ok": false,
   "k": 5,
   "same": 0,
   "verdict": "FAIL",
   "finding": ""
  }
 ],
 "modules": 397
};
