/* LAB-38 concept-kv-cache reference run (scripts/export_explainer_data.py). Do not edit by hand. */
window.LAB_DATA = {
 "canary": "ATLAS-CANARY-kv5c",
 "model": {
  "layers": 30,
  "heads": 9,
  "kv_heads": 3,
  "head_dim": 64,
  "per_token": 46080
 },
 "grow": [
  {
   "tokens": 8,
   "cache_bytes": 368640,
   "per_token": 46080
  },
  {
   "tokens": 32,
   "cache_bytes": 1474560,
   "per_token": 46080
  },
  {
   "tokens": 128,
   "cache_bytes": 5898240,
   "per_token": 46080
  },
  {
   "tokens": 256,
   "cache_bytes": 11796480,
   "per_token": 46080
  }
 ],
 "cost": [
  {
   "T": 128,
   "full_ms": 406.9,
   "step_ms": 381.5,
   "ratio": 1.1
  },
  {
   "T": 512,
   "full_ms": 547.7,
   "step_ms": 376.4,
   "ratio": 1.5
  },
  {
   "T": 1024,
   "full_ms": 972.5,
   "step_ms": 324.0,
   "ratio": 3.0
  }
 ],
 "mamba": {
  "layers": 24,
  "state_size": 16,
  "state_bytes": 2949120,
  "rows": [
   {
    "tokens": 8,
    "state_bytes": 2949120
   },
   {
    "tokens": 32,
    "state_bytes": 2949120
   },
   {
    "tokens": 128,
    "state_bytes": 2949120
   },
   {
    "tokens": 256,
    "state_bytes": 2949120
   }
  ]
 },
 "persist": {
  "prefix_tokens": 672,
  "first_ms": 774.1,
  "repeat_ms": [
   18.7,
   31.8,
   8.2
  ],
  "speedup": 41.4
 },
 "anatomy": {
  "n_head": 70,
  "n_body": 603,
  "hit_ms": 19.0,
  "hit_cache_n": 681,
  "miss_ms": 730.3,
  "miss_cache_n": 0,
  "ratio": 38.5
 },
 "guess": {
  "rounds": 16,
  "threshold_ms": 364.9,
  "summary": {
   "hit_med_ms": 20.3,
   "hit_min_ms": 18.6,
   "hit_max_ms": 39.7,
   "miss_med_ms": 764.6,
   "miss_min_ms": 708.7,
   "miss_max_ms": 874.8,
   "ratio": 37.69,
   "U": 63.0,
   "z": 3.33,
   "p": 0.0008551019694724853,
   "auc": 1.0
  },
  "acc": {
   "k": 16,
   "n": 16,
   "p": 1.0,
   "lo": 0.806,
   "hi": 1.0
  },
  "hits_ms": [
   19.25986900459975,
   22.781838080845773,
   19.228117889724672,
   34.894433920271695,
   23.70018500369042,
   20.28905099723488,
   18.585899961180985,
   39.65950501151383,
   19.50166397728026
  ],
  "misses_ms": [
   837.2857969952747,
   744.3689190549776,
   716.6993409628049,
   764.6173849934712,
   708.7252229684964,
   874.841354903765,
   823.7903049448505
  ],
  "rows": [
   {
    "round": 0,
    "sent": false,
    "ms": 837.3,
    "ok": true
   },
   {
    "round": 1,
    "sent": true,
    "ms": 19.3,
    "ok": true
   },
   {
    "round": 2,
    "sent": false,
    "ms": 744.4,
    "ok": true
   },
   {
    "round": 3,
    "sent": true,
    "ms": 22.8,
    "ok": true
   },
   {
    "round": 4,
    "sent": false,
    "ms": 716.7,
    "ok": true
   },
   {
    "round": 5,
    "sent": true,
    "ms": 19.2,
    "ok": true
   },
   {
    "round": 6,
    "sent": false,
    "ms": 764.6,
    "ok": true
   },
   {
    "round": 7,
    "sent": true,
    "ms": 34.9,
    "ok": true
   },
   {
    "round": 8,
    "sent": true,
    "ms": 23.7,
    "ok": true
   },
   {
    "round": 9,
    "sent": true,
    "ms": 20.3,
    "ok": true
   },
   {
    "round": 10,
    "sent": true,
    "ms": 18.6,
    "ok": true
   },
   {
    "round": 11,
    "sent": false,
    "ms": 708.7,
    "ok": true
   },
   {
    "round": 12,
    "sent": true,
    "ms": 39.7,
    "ok": true
   },
   {
    "round": 13,
    "sent": false,
    "ms": 874.8,
    "ok": true
   },
   {
    "round": 14,
    "sent": false,
    "ms": 823.8,
    "ok": true
   },
   {
    "round": 15,
    "sent": true,
    "ms": 19.5,
    "ok": true
   }
  ]
 },
 "d1": {
  "summary": {
   "hit_med_ms": 753.8,
   "hit_min_ms": 724.7,
   "hit_max_ms": 847.5,
   "miss_med_ms": 775.2,
   "miss_min_ms": 712.7,
   "miss_max_ms": 831.9,
   "ratio": 1.03,
   "U": 27.0,
   "z": -0.48,
   "p": 0.6338389313837579,
   "auc": 0.429
  },
  "acc": {
   "k": 7,
   "n": 16,
   "p": 0.438,
   "lo": 0.231,
   "hi": 0.668
  },
  "own_first_ms": 795.7,
  "own_repeat_ms": [
   19.5,
   8.7,
   8.2
  ]
 },
 "d2": {
  "gap_ms": 744.3,
  "table": [
   {
    "J": 0,
    "added_ms": 0.0,
    "single_acc": 1.0,
    "probes_90": 1,
    "probes_90_min": 1
   },
   {
    "J": 100,
    "added_ms": 50.0,
    "single_acc": 1.0,
    "probes_90": 1,
    "probes_90_min": 1
   },
   {
    "J": 500,
    "added_ms": 250.0,
    "single_acc": 1.0,
    "probes_90": 1,
    "probes_90_min": 1
   },
   {
    "J": 2000,
    "added_ms": 1000.0,
    "single_acc": 0.693,
    "probes_90": 8,
    "probes_90_min": 8
   },
   {
    "J": 8000,
    "added_ms": 4000.0,
    "single_acc": 0.553,
    "probes_90": 64,
    "probes_90_min": 32
   }
  ]
 },
 "evaluate": {
  "shared": "leaks",
  "salted": "no signal"
 }
};
