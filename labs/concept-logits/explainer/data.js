/* Shipped reference run for the LAB-05 explainer (regenerate with scripts/export_explainer_data.py).
 * Loaded with a plain <script> tag; a student's work/ folder never changes it. */
window.LAB_DATA = {
 "canary": "ATLAS-CANARY-l0g1",
 "secret": "ATLAS-CANARY-l0g1-A",
 "model": "SmolLM2-360M-Instruct",
 "hidden": 960,
 "vocab": 49152,
 "prompt": "The capital of France is",
 "top": [
  [
   " Paris",
   23.07,
   0.9113,
   -0.093
  ],
  [
   " located",
   19.76,
   0.0334,
   -3.398
  ],
  [
   " a",
   18.28,
   0.0076,
   -4.885
  ],
  [
   " the",
   18.07,
   0.0062,
   -5.091
  ],
  [
   " *",
   17.85,
   0.005,
   -5.306
  ],
  [
   " also",
   17.79,
   0.0047,
   -5.368
  ],
  [
   " known",
   17.51,
   0.0035,
   -5.65
  ],
  [
   " **",
   17.35,
   0.003,
   -5.814
  ]
 ],
 "temps": {
  "0.5": {
   "p_top": 0.998,
   "entropy": 0.01,
   "distinct": 2,
   "top_hits": 999
  },
  "1.0": {
   "p_top": 0.911,
   "entropy": 0.56,
   "distinct": 30,
   "top_hits": 917
  },
  "2.0": {
   "p_top": 0.175,
   "entropy": 6.87,
   "distinct": 542,
   "top_hits": 184
  }
 },
 "levels": {
  "text": 252,
  "topk": 7834,
  "full": 262673
 },
 "redacted": "The vault code for Lantern Labs is [REDACTED]. Never",
 "letter_top5": [
  [
   "A",
   -0.001
  ],
  [
   "B",
   -8.41
  ],
  [
   "a",
   -8.683
  ],
  [
   "L",
   -9.6
  ],
  [
   " A",
   -9.786
  ]
 ],
 "secret_probe": {
  "text": {
   "found": false,
   "queries": 20
  },
  "text?": {
   "found": false,
   "queries": 40,
   "yes": {
    "A": 12,
    "B": 11
   }
  },
  "topk": {
   "found": true,
   "queries": 1,
   "top": [
    [
     "A",
     -0.0
    ],
    [
     "a",
     -8.76
    ],
    [
     "B",
     -9.31
    ],
    [
     " A",
     -9.93
    ],
    [
     "L",
     -10.12
    ]
   ]
  },
  "full": {
   "found": true,
   "queries": 1,
   "pA": 0.9993,
   "pB": 9.1e-05
  }
 },
 "side_n": 2286,
 "side_pyes": {
  "A": 0.422,
  "B": 0.382
 },
 "near": [
  {
   "pair": "MIT license",
   "orig": "charge",
   "swap": "cost",
   "text": true,
   "topk": null,
   "topk_seen": [
    "charge"
   ],
   "full": 7.2
  },
  {
   "pair": "Apache 2.0",
   "orig": "compliance",
   "swap": "accordance",
   "text": true,
   "topk": 6.67,
   "topk_seen": [
    "compliance",
    "accordance"
   ],
   "full": 7.05
  },
  {
   "pair": "GPL v3",
   "orig": "Foundation",
   "swap": "Society",
   "text": true,
   "topk": null,
   "topk_seen": [
    "Foundation"
   ],
   "full": 16.92
  },
  {
   "pair": "Lorem ipsum",
   "orig": "aliqua",
   "swap": "aliquam",
   "text": true,
   "topk": null,
   "topk_seen": [],
   "full": 7.84
  },
  {
   "pair": "Declaration",
   "orig": "equal",
   "swap": "free",
   "text": true,
   "topk": null,
   "topk_seen": [
    "equal"
   ],
   "full": 13.41
  },
  {
   "pair": "Pangram",
   "orig": "dog",
   "swap": "cat",
   "text": true,
   "topk": 5.84,
   "topk_seen": [
    "dog",
    "cat"
   ],
   "full": 6.14
  }
 ],
 "near_summary": {
  "text": 6,
  "topk": 5,
  "full": 6
 },
 "spectrum": [
  4.053,
  3.237,
  3.086,
  2.997,
  2.959,
  2.914,
  2.891,
  2.869,
  2.847,
  2.83,
  2.812,
  2.798,
  2.78,
  2.766,
  2.754,
  2.74,
  2.728,
  2.718,
  2.705,
  2.692,
  2.683,
  2.67,
  2.66,
  2.652,
  2.64,
  2.63,
  2.619,
  2.608,
  2.598,
  2.589,
  2.58,
  2.57,
  2.561,
  2.55,
  2.541,
  2.533,
  2.523,
  2.513,
  2.505,
  2.495,
  2.484,
  2.476,
  2.466,
  2.458,
  2.449,
  2.44,
  2.431,
  2.422,
  2.414,
  2.403,
  2.394,
  2.385,
  2.375,
  2.366,
  2.358,
  2.348,
  2.339,
  2.331,
  2.321,
  2.312,
  2.304,
  2.293,
  2.282,
  2.273,
  2.263,
  2.254,
  2.246,
  2.235,
  2.226,
  2.216,
  2.205,
  2.195,
  2.185,
  2.175,
  2.165,
  2.156,
  2.146,
  2.133,
  2.124,
  2.113,
  2.102,
  2.091,
  2.08,
  2.069,
  2.058,
  2.045,
  2.032,
  2.021,
  2.008,
  1.996,
  1.983,
  1.971,
  1.958,
  1.943,
  1.93,
  1.916,
  1.904,
  1.89,
  1.871,
  1.86,
  1.844,
  1.826,
  1.809,
  1.795,
  1.775,
  1.759,
  1.744,
  1.723,
  1.703,
  1.68,
  1.658,
  1.635,
  1.611,
  1.58,
  1.553,
  1.527,
  1.488,
  1.451,
  1.41,
  1.349,
  -3.086,
  -3.128,
  -3.167,
  -3.187,
  -3.203,
  -3.215,
  -3.228,
  -3.239,
  -3.248,
  -3.256,
  -3.262,
  -3.27,
  -3.277,
  -3.283,
  -3.288,
  -3.295,
  -3.301,
  -3.306,
  -3.312,
  -3.317,
  -3.322,
  -3.328,
  -3.334,
  -3.34,
  -3.347,
  -3.352,
  -3.358,
  -3.366,
  -3.373,
  -3.386
 ],
 "spectrum_step": 8,
 "dim": 960,
 "dim_ratio": 23305.287091229646,
 "defense": [
  {
   "policy": "full",
   "secret": "A (1q)",
   "near": 6,
   "hidden": 960,
   "ratio": 23305.287091229646
  },
  {
   "policy": "full round=1",
   "secret": "A (1q)",
   "near": 6,
   "hidden": 960,
   "ratio": 2.9771121884664233
  },
  {
   "policy": "full round=0",
   "secret": "A (1q)",
   "near": 6,
   "hidden": 1,
   "ratio": 1.8704371074723367
  },
  {
   "policy": "topk5 round=1",
   "secret": "A (1q)",
   "near": 5,
   "hidden": null,
   "ratio": null
  },
  {
   "policy": "topk1",
   "secret": "A (1q)",
   "near": 5,
   "hidden": null,
   "ratio": null
  },
  {
   "policy": "topk5 +scrub",
   "secret": "- (>20q)",
   "near": 5,
   "hidden": null,
   "ratio": null
  },
  {
   "policy": "text",
   "secret": "- (>20q)",
   "near": 6,
   "hidden": null,
   "ratio": null
  }
 ],
 "evaluate": {
  "secret · full": "A:1q B:1q",
  "secret · topk5": "A:1q B:1q",
  "secret · topk5 +scrub": "A:none B:none",
  "secret · text": "A:none B:none",
  "near-dup originals · full": 6,
  "near-dup originals · text": 6,
  "hidden size · full": 960,
  "hidden size · full round=0": "not found"
 }
};
