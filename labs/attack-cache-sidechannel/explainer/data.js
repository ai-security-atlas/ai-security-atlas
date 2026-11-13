/* LAB-24 attack-cache-sidechannel reference run (scripts/export_explainer_data.py). Do not edit by hand. */
window.LAB_DATA = {
 "canary": "ATLAS-CANARY-kv24",
 "codes": [
  "kv24",
  "qz71",
  "bd38",
  "ne92"
 ],
 "server": {
  "build": "b11977-7ac5727d6",
  "model": "smollm2-360m",
  "slots": 4,
  "n_ctx": 8192
 },
 "tokens": {
  "head": 42,
  "code": 3,
  "tail": 73,
  "user": 1
 },
 "signal": {
  "rows": [
   {
    "round": 1,
    "hit": 11.1,
    "hit_cache_n": 128,
    "misses": 94.2,
    "miss_cache_n": 45
   },
   {
    "round": 2,
    "hit": 11.2,
    "hit_cache_n": 127,
    "misses": 83.8,
    "miss_cache_n": 45
   },
   {
    "round": 3,
    "hit": 10.6,
    "hit_cache_n": 127,
    "misses": 80.1,
    "miss_cache_n": 45
   }
  ]
 },
 "attack": {
  "rounds": 24,
  "hits_ms": [
   25.7,
   12.3,
   14.2,
   12.4,
   10.5,
   10.8,
   13.3,
   11.5,
   55.2,
   58.7,
   13.2,
   12.7,
   44.1,
   11.8,
   12.2,
   20.3,
   11.5,
   12.5,
   12.0,
   11.4,
   11.1,
   11.8,
   10.8,
   15.1
  ],
  "misses_ms": [
   109.8,
   88.5,
   96.7,
   86.6,
   79.5,
   79.5,
   105.4,
   81.8,
   81.9,
   78.6,
   80.7,
   80.4,
   80.1,
   81.2,
   96.1,
   80.8,
   79.1,
   79.7,
   81.0,
   84.5,
   99.4,
   97.1,
   110.8,
   100.2,
   111.1,
   100.2,
   112.1,
   159.7,
   120.5,
   198.2,
   87.8,
   83.7,
   109.7,
   91.8,
   86.2,
   86.9,
   89.5,
   89.4,
   87.3,
   94.2,
   87.0,
   109.6,
   84.1,
   95.8,
   101.0,
   120.0,
   88.6,
   102.4,
   111.2,
   90.1,
   86.3,
   81.3,
   84.9,
   80.5,
   80.4,
   81.7,
   90.6,
   81.5,
   107.4,
   113.2,
   82.0,
   80.3,
   91.3,
   86.8,
   89.0,
   80.7,
   84.7,
   84.2,
   93.7,
   92.2,
   110.4,
   113.0
  ],
  "per_round": [
   {
    "round": 0,
    "live": 0,
    "pick": 0,
    "ok": true,
    "hit": 25.7,
    "misses": [
     109.8,
     88.5,
     96.7
    ]
   },
   {
    "round": 1,
    "live": 1,
    "pick": 1,
    "ok": true,
    "hit": 12.3,
    "misses": [
     86.6,
     79.5,
     79.5
    ]
   },
   {
    "round": 2,
    "live": 0,
    "pick": 0,
    "ok": true,
    "hit": 14.2,
    "misses": [
     105.4,
     81.8,
     81.9
    ]
   },
   {
    "round": 3,
    "live": 0,
    "pick": 0,
    "ok": true,
    "hit": 12.4,
    "misses": [
     78.6,
     80.7,
     80.4
    ]
   },
   {
    "round": 4,
    "live": 0,
    "pick": 0,
    "ok": true,
    "hit": 10.5,
    "misses": [
     80.1,
     81.2,
     96.1
    ]
   },
   {
    "round": 5,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 10.8,
    "misses": [
     80.8,
     79.1,
     79.7
    ]
   },
   {
    "round": 6,
    "live": 1,
    "pick": 1,
    "ok": true,
    "hit": 13.3,
    "misses": [
     81.0,
     84.5,
     99.4
    ]
   },
   {
    "round": 7,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 11.5,
    "misses": [
     97.1,
     110.8,
     100.2
    ]
   },
   {
    "round": 8,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 55.2,
    "misses": [
     111.1,
     100.2,
     112.1
    ]
   },
   {
    "round": 9,
    "live": 1,
    "pick": 1,
    "ok": true,
    "hit": 58.7,
    "misses": [
     159.7,
     120.5,
     198.2
    ]
   },
   {
    "round": 10,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 13.2,
    "misses": [
     87.8,
     83.7,
     109.7
    ]
   },
   {
    "round": 11,
    "live": 3,
    "pick": 3,
    "ok": true,
    "hit": 12.7,
    "misses": [
     91.8,
     86.2,
     86.9
    ]
   },
   {
    "round": 12,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 44.1,
    "misses": [
     89.5,
     89.4,
     87.3
    ]
   },
   {
    "round": 13,
    "live": 3,
    "pick": 3,
    "ok": true,
    "hit": 11.8,
    "misses": [
     94.2,
     87.0,
     109.6
    ]
   },
   {
    "round": 14,
    "live": 1,
    "pick": 1,
    "ok": true,
    "hit": 12.2,
    "misses": [
     84.1,
     95.8,
     101.0
    ]
   },
   {
    "round": 15,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 20.3,
    "misses": [
     120.0,
     88.6,
     102.4
    ]
   },
   {
    "round": 16,
    "live": 3,
    "pick": 3,
    "ok": true,
    "hit": 11.5,
    "misses": [
     111.2,
     90.1,
     86.3
    ]
   },
   {
    "round": 17,
    "live": 0,
    "pick": 0,
    "ok": true,
    "hit": 12.5,
    "misses": [
     81.3,
     84.9,
     80.5
    ]
   },
   {
    "round": 18,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 12.0,
    "misses": [
     80.4,
     81.7,
     90.6
    ]
   },
   {
    "round": 19,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 11.4,
    "misses": [
     81.5,
     107.4,
     113.2
    ]
   },
   {
    "round": 20,
    "live": 0,
    "pick": 0,
    "ok": true,
    "hit": 11.1,
    "misses": [
     82.0,
     80.3,
     91.3
    ]
   },
   {
    "round": 21,
    "live": 3,
    "pick": 3,
    "ok": true,
    "hit": 11.8,
    "misses": [
     86.8,
     89.0,
     80.7
    ]
   },
   {
    "round": 22,
    "live": 0,
    "pick": 0,
    "ok": true,
    "hit": 10.8,
    "misses": [
     84.7,
     84.2,
     93.7
    ]
   },
   {
    "round": 23,
    "live": 3,
    "pick": 3,
    "ok": true,
    "hit": 15.1,
    "misses": [
     92.2,
     110.4,
     113.0
    ]
   }
  ],
  "summary": {
   "rounds": 24,
   "seed": 24,
   "hit_med_ms": 12.3,
   "hit_min_ms": 10.5,
   "hit_max_ms": 58.7,
   "miss_med_ms": 88.5,
   "miss_min_ms": 78.6,
   "miss_max_ms": 198.2,
   "ratio": 7.17,
   "U": 0.0,
   "z": -7.31,
   "p": 7.662330781996008e-23,
   "auc": 1.0,
   "picks": {
    "k": 24,
    "n": 24,
    "p": 1.0,
    "lo": 0.862,
    "hi": 1.0
   },
   "chance": 0.25,
   "oracle_ok": 24
  }
 },
 "backend": {
  "name": "host-ollama",
  "model": "qwen2.5:3b",
  "best": {
   "picks": "6/6",
   "hit_med_ms": 112.1,
   "miss_med_ms": 146.3,
   "p": 1.4859282593836369e-05
  },
  "realistic": {
   "picks": "6/6",
   "hit_med_ms": 111.6,
   "miss_med_ms": 146.9,
   "p": 1.4859282593836369e-05
  }
 },
 "trials": {
  "table": [
   {
    "k": 3,
    "mean_pct": 100.0,
    "lo_pct": 100,
    "hi_pct": 100,
    "p_med": 0.009091,
    "pct_p_below_001": 77
   },
   {
    "k": 6,
    "mean_pct": 100.0,
    "lo_pct": 100,
    "hi_pct": 100,
    "p_med": 0.000314,
    "pct_p_below_001": 100
   },
   {
    "k": 12,
    "mean_pct": 100.0,
    "lo_pct": 100,
    "hi_pct": 100,
    "p_med": 0.0,
    "pct_p_below_001": 100
   },
   {
    "k": 24,
    "mean_pct": 100.0,
    "lo_pct": 100,
    "hi_pct": 100,
    "p_med": 0.0,
    "pct_p_below_001": 100
   }
  ],
  "drift_ms": [
   82,
   85
  ]
 },
 "d1": {
  "pinned": {
   "rounds": 12,
   "seed": 25,
   "hit_med_ms": 18.2,
   "hit_min_ms": 12.5,
   "hit_max_ms": 141.1,
   "miss_med_ms": 95.0,
   "miss_min_ms": 80.1,
   "miss_max_ms": 154.6,
   "ratio": 5.21,
   "U": 118.0,
   "z": -2.33,
   "p": 0.01881070971288972,
   "auc": 0.727,
   "picks": {
    "k": 8,
    "n": 12,
    "p": 0.6667,
    "lo": 0.3906,
    "hi": 0.8619
   },
   "chance": 0.25,
   "oracle_ok": 0
  },
  "salt": {
   "rounds": 12,
   "seed": 25,
   "hit_med_ms": 105.2,
   "hit_min_ms": 85.4,
   "hit_max_ms": 146.6,
   "miss_med_ms": 108.3,
   "miss_min_ms": 83.3,
   "miss_max_ms": 163.8,
   "ratio": 1.03,
   "U": 212.0,
   "z": -0.1,
   "p": 0.9344904693223265,
   "auc": 0.509,
   "picks": {
    "k": 6,
    "n": 12,
    "p": 0.5,
    "lo": 0.2538,
    "hi": 0.7462
   },
   "chance": 0.25,
   "oracle_ok": 0
  },
  "salt_own": {
   "first_ms": 421.0,
   "repeat_ms": [
    72.1,
    41.1,
    109.7
   ],
   "first_cache_n": 0,
   "repeat_cache_n": [
    148,
    148,
    148
   ]
  }
 },
 "d2": {
  "attack": {
   "rounds": 12,
   "seed": 26,
   "hit_med_ms": 117.5,
   "hit_min_ms": 108.4,
   "hit_max_ms": 191.3,
   "miss_med_ms": 117.9,
   "miss_min_ms": 106.5,
   "miss_max_ms": 245.5,
   "ratio": 1.0,
   "U": 202.0,
   "z": -0.33,
   "p": 0.75110868944768,
   "auc": 0.532,
   "picks": {
    "k": 3,
    "n": 12,
    "p": 0.25,
    "lo": 0.0889,
    "hi": 0.5323
   },
   "chance": 0.25,
   "oracle_ok": 0
  },
  "baseline": {
   "first_ms": 231.2,
   "repeat_ms": [
    67.7,
    80.6,
    109.3,
    119.2,
    82.6,
    78.0,
    75.2,
    113.1,
    77.7,
    93.5,
    144.5,
    96.5,
    36.5,
    68.2,
    40.2,
    65.9,
    38.2,
    40.5,
    61.6,
    81.8
   ],
   "repeat_cache_n": 138
  },
  "nocache": {
   "first_ms": 142.4,
   "repeat_ms": [
    143.2,
    165.2,
    144.9,
    142.1,
    140.8,
    152.0,
    140.7,
    139.3,
    143.7,
    140.0,
    167.0,
    150.0,
    190.7,
    155.3,
    172.0,
    173.2,
    161.1,
    152.6,
    173.8,
    219.3
   ],
   "repeat_cache_n": [
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0
   ]
  },
  "cost_s_per_1000": 74.5,
  "cost_ci_s_per_1000": [
   61.7,
   92.1
  ]
 },
 "evaluate": {
  "shared": {
   "hit_med_ms": 12.1,
   "miss_med_ms": 88.3,
   "ratio": 7.27,
   "p": 1.901447952615917e-07,
   "picks": {
    "k": 8,
    "n": 8,
    "p": 1.0,
    "lo": 0.6756,
    "hi": 1.0
   }
  },
  "pinned": {
   "hit_med_ms": 6.9,
   "miss_med_ms": 7.2,
   "ratio": 1.03,
   "p": 0.4036581957160378,
   "picks": {
    "k": 2,
    "n": 8,
    "p": 0.25,
    "lo": 0.0715,
    "hi": 0.5907
   }
  },
  "salted": {
   "hit_med_ms": 102.3,
   "miss_med_ms": 91.1,
   "ratio": 0.89,
   "p": 0.10354715115560499,
   "picks": {
    "k": 0,
    "n": 8,
    "p": 0.0,
    "lo": 0.0,
    "hi": 0.3244
   }
  },
  "verdicts": {
   "shared": "leaks",
   "pinned": "no signal",
   "salted": "no signal",
   "nocache": "no signal"
  }
 }
};
