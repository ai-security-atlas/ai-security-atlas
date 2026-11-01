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
   "full_ms": 466.4,
   "step_ms": 388.6,
   "ratio": 1.2
  },
  {
   "T": 512,
   "full_ms": 783.4,
   "step_ms": 382.1,
   "ratio": 2.1
  },
  {
   "T": 1024,
   "full_ms": 1113.6,
   "step_ms": 396.3,
   "ratio": 2.8
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
  "first_ms": 748.3,
  "repeat_ms": [
   18.8,
   7.9,
   7.6
  ],
  "speedup": 94.7
 },
 "anatomy": {
  "n_head": 70,
  "n_body": 603,
  "hit_ms": 18.6,
  "hit_cache_n": 681,
  "miss_ms": 745.0,
  "miss_cache_n": 0,
  "ratio": 40.0
 },
 "guess": {
  "rounds": 16,
  "threshold_ms": 368.1,
  "summary": {
   "hit_med_ms": 18.7,
   "hit_min_ms": 18.4,
   "hit_max_ms": 33.0,
   "miss_med_ms": 719.5,
   "miss_min_ms": 711.1,
   "miss_max_ms": 795.2,
   "ratio": 38.4,
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
   18.568180996226147,
   18.430012998578604,
   18.738431004749145,
   18.638472000020556,
   18.518429998948704,
   33.00172300077975,
   19.142391000059433,
   19.507766999595333,
   22.840984995127656
  ],
  "misses_ms": [
   711.0986249972484,
   719.5449010032462,
   712.9460889991606,
   743.5249310001382,
   795.1585429982515,
   730.0029739999445,
   713.8718839996727
  ],
  "rows": [
   {
    "round": 0,
    "sent": false,
    "ms": 711.1,
    "ok": true
   },
   {
    "round": 1,
    "sent": true,
    "ms": 18.6,
    "ok": true
   },
   {
    "round": 2,
    "sent": false,
    "ms": 719.5,
    "ok": true
   },
   {
    "round": 3,
    "sent": true,
    "ms": 18.4,
    "ok": true
   },
   {
    "round": 4,
    "sent": false,
    "ms": 712.9,
    "ok": true
   },
   {
    "round": 5,
    "sent": true,
    "ms": 18.7,
    "ok": true
   },
   {
    "round": 6,
    "sent": false,
    "ms": 743.5,
    "ok": true
   },
   {
    "round": 7,
    "sent": true,
    "ms": 18.6,
    "ok": true
   },
   {
    "round": 8,
    "sent": true,
    "ms": 18.5,
    "ok": true
   },
   {
    "round": 9,
    "sent": true,
    "ms": 33.0,
    "ok": true
   },
   {
    "round": 10,
    "sent": true,
    "ms": 19.1,
    "ok": true
   },
   {
    "round": 11,
    "sent": false,
    "ms": 795.2,
    "ok": true
   },
   {
    "round": 12,
    "sent": true,
    "ms": 19.5,
    "ok": true
   },
   {
    "round": 13,
    "sent": false,
    "ms": 730.0,
    "ok": true
   },
   {
    "round": 14,
    "sent": false,
    "ms": 713.9,
    "ok": true
   },
   {
    "round": 15,
    "sent": true,
    "ms": 22.8,
    "ok": true
   }
  ]
 },
 "d1": {
  "summary": {
   "hit_med_ms": 773.6,
   "hit_min_ms": 714.8,
   "hit_max_ms": 1482.4,
   "miss_med_ms": 740.6,
   "miss_min_ms": 708.4,
   "miss_max_ms": 789.4,
   "ratio": 0.96,
   "U": 22.0,
   "z": -1.01,
   "p": 0.3146144552999873,
   "auc": 0.349
  },
  "acc": {
   "k": 7,
   "n": 16,
   "p": 0.438,
   "lo": 0.231,
   "hi": 0.668
  },
  "own_first_ms": 1964.2,
  "own_repeat_ms": [
   39.5,
   36.2,
   9.4
  ]
 },
 "d2": {
  "gap_ms": 700.8,
  "table": [
   {
    "J": 0,
    "added_ms": 0.0,
    "single_acc": 1.0,
    "probes_90": 1
   },
   {
    "J": 100,
    "added_ms": 50.0,
    "single_acc": 1.0,
    "probes_90": 1
   },
   {
    "J": 500,
    "added_ms": 250.0,
    "single_acc": 1.0,
    "probes_90": 1
   },
   {
    "J": 2000,
    "added_ms": 1000.0,
    "single_acc": 0.682,
    "probes_90": 8
   },
   {
    "J": 8000,
    "added_ms": 4000.0,
    "single_acc": 0.551,
    "probes_90": ">64"
   }
  ]
 },
 "evaluate": {
  "shared": "leaks",
  "salted": "no signal"
 }
};
