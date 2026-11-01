window.LAB_DATA = {
 "canary": "ATLAS-CANARY-svd7",
 "victim": {
  "id": "lantern-mini-1",
  "vocab": 49152,
  "hidden": 576,
  "params": 134515008,
  "head_params": 28311552,
  "top5": [
   [
    " Paris",
    -0.7564373016357422
   ],
   [
    " the",
    -1.3251638412475586
   ],
   [
    " located",
    -2.4870758056640625
   ],
   [
    " called",
    -4.04338264465332
   ],
   [
    " Le",
    -4.203803062438965
   ]
  ],
  "prompt": "The capital of France is",
  "tied": true
 },
 "collect": {
  "rows": 1200,
  "requests": 12,
  "seconds": 36.5,
  "seed": 5,
  "example_len": 6
 },
 "spectrum": {
  "dim": 576,
  "ratio": 32400.0,
  "true": 576,
  "s0": 12100.0,
  "s_k": 67.71,
  "s_after": 0.00209,
  "values": [
   12133.410472,
   6979.013113,
   4068.24733,
   74.616535,
   72.893593,
   70.288632,
   67.71318,
   0.002092,
   0.002078,
   0.002073,
   0.002068,
   0.000788,
   0.000774,
   0.000761
  ],
  "curve": [
   {
    "rows": 300,
    "dim": 1,
    "ratio": 1.7791410939471435,
    "clear": false
   },
   {
    "rows": 500,
    "dim": 1,
    "ratio": 1.7515282679671587,
    "clear": false
   },
   {
    "rows": 577,
    "dim": 575,
    "ratio": 7.310707351729667,
    "clear": false
   },
   {
    "rows": 700,
    "dim": 576,
    "ratio": 9247.096074467265,
    "clear": true
   },
   {
    "rows": 1200,
    "dim": 576,
    "ratio": 32367.778359127722,
    "clear": true
   }
  ]
 },
 "recover": {
  "rel_resid": 6.578145962739432e-06,
  "cos_min": 0.9999999997706891,
  "orth_err": 6.657110301379332e-13,
  "params": 28311552,
  "model_params": 134515008,
  "share": 21.0,
  "mb": 113.2,
  "tied": true,
  "rows": 1200,
  "d": 576,
  "bytes": 113246208,
  "canary": "ATLAS-CANARY-svd7",
  "queries": 1200
 },
 "d1": {
  "refused_full": 403,
  "refused_bias": 400,
  "topk_rows": 400,
  "distinct_ids": 489,
  "queries_a": 6,
  "block": 256,
  "block_queries": 64,
  "per_request": 4,
  "max_err": 5.7220458984375e-06,
  "per_row_requests": 12288,
  "rows_needed": 577,
  "total_requests": 7090176,
  "factor": 5908
 },
 "d2": {
  "levels": {
   "round=2": {
    "dim": 576,
    "ratio": 4.941,
    "clear": false,
    "fit": 0.0188,
    "queries": 600
   },
   "round=1": {
    "dim": 1,
    "ratio": 1.829,
    "clear": false,
    "fit": 0.141,
    "queries": 600
   },
   "round=0": {
    "dim": 1,
    "ratio": 1.828,
    "clear": false,
    "fit": 0.478,
    "queries": 600
   },
   "noise=1e-3": {
    "dim": 576,
    "ratio": 13.958,
    "clear": true,
    "fit": 0.00655,
    "queries": 600
   },
   "noise=1e-2": {
    "dim": 1,
    "ratio": 1.829,
    "clear": false,
    "fit": 0.0612,
    "queries": 600
   },
   "noise=1e-1": {
    "dim": 1,
    "ratio": 1.829,
    "clear": false,
    "fit": 0.296,
    "queries": 600
   }
  },
  "n_rows": 600,
  "ties": {
   "2": 15,
   "1": 99,
   "0": 200
  }
 },
 "d3": {
  "threshold": -8.63,
  "honest_median": -5.15,
  "honest_spread": [
   -12.15,
   -2.94
  ],
  "monitor": {
   "app-user": {
    "median": -5.15,
    "flagged": false,
    "queries": 40,
    "sample": 40
   },
   "thief": {
    "median": -14.28,
    "flagged": true,
    "queries": 600,
    "sample": 48
   },
   "natural-thief": {
    "median": -5.03,
    "flagged": false,
    "queries": 700,
    "sample": 48
   }
  },
  "natural": {
   "dim": 576,
   "ratio": 2482.4,
   "fit": 6.14e-05,
   "rows": 700
  },
  "budget": {
   "cap": 400,
   "got": 400,
   "knee": 1,
   "clear": false
  }
 }
};
