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
    "hit": 329.3,
    "hit_cache_n": 128,
    "misses": 521.8,
    "miss_cache_n": 45
   },
   {
    "round": 2,
    "hit": 276.7,
    "hit_cache_n": 127,
    "misses": 1049.0,
    "miss_cache_n": 45
   },
   {
    "round": 3,
    "hit": 224.5,
    "hit_cache_n": 127,
    "misses": 536.4,
    "miss_cache_n": 45
   }
  ]
 },
 "attack": {
  "rounds": 24,
  "hits_ms": [
   232.4,
   224.5,
   219.4,
   225.1,
   248.6,
   392.0,
   225.8,
   243.6,
   245.8,
   168.7,
   228.8,
   228.0,
   266.8,
   337.1,
   360.3,
   230.3,
   250.9,
   234.3,
   224.4,
   248.9,
   229.5,
   223.9,
   227.3,
   222.1
  ],
  "misses_ms": [
   513.9,
   492.8,
   548.4,
   501.3,
   508.2,
   510.5,
   484.8,
   483.2,
   477.5,
   473.4,
   495.6,
   468.7,
   709.5,
   542.9,
   441.3,
   601.3,
   506.2,
   493.5,
   472.9,
   486.7,
   488.3,
   447.8,
   477.7,
   477.9,
   486.7,
   475.1,
   494.1,
   518.1,
   294.9,
   263.7,
   756.9,
   573.2,
   470.0,
   498.6,
   377.5,
   255.0,
   506.9,
   446.9,
   480.9,
   567.3,
   482.7,
   490.1,
   631.9,
   480.0,
   503.5,
   535.0,
   514.7,
   466.6,
   500.0,
   546.5,
   530.2,
   580.9,
   557.0,
   550.9,
   603.8,
   481.1,
   502.9,
   419.6,
   463.3,
   464.2,
   409.7,
   389.7,
   469.6,
   446.1,
   408.1,
   450.1,
   509.0,
   462.8,
   486.8,
   462.5,
   462.8,
   457.5
  ],
  "per_round": [
   {
    "round": 0,
    "live": 0,
    "pick": 0,
    "ok": true,
    "hit": 232.4,
    "misses": [
     513.9,
     492.8,
     548.4
    ]
   },
   {
    "round": 1,
    "live": 1,
    "pick": 1,
    "ok": true,
    "hit": 224.5,
    "misses": [
     501.3,
     508.2,
     510.5
    ]
   },
   {
    "round": 2,
    "live": 0,
    "pick": 0,
    "ok": true,
    "hit": 219.4,
    "misses": [
     484.8,
     483.2,
     477.5
    ]
   },
   {
    "round": 3,
    "live": 0,
    "pick": 0,
    "ok": true,
    "hit": 225.1,
    "misses": [
     473.4,
     495.6,
     468.7
    ]
   },
   {
    "round": 4,
    "live": 0,
    "pick": 0,
    "ok": true,
    "hit": 248.6,
    "misses": [
     709.5,
     542.9,
     441.3
    ]
   },
   {
    "round": 5,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 392.0,
    "misses": [
     601.3,
     506.2,
     493.5
    ]
   },
   {
    "round": 6,
    "live": 1,
    "pick": 1,
    "ok": true,
    "hit": 225.8,
    "misses": [
     472.9,
     486.7,
     488.3
    ]
   },
   {
    "round": 7,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 243.6,
    "misses": [
     447.8,
     477.7,
     477.9
    ]
   },
   {
    "round": 8,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 245.8,
    "misses": [
     486.7,
     475.1,
     494.1
    ]
   },
   {
    "round": 9,
    "live": 1,
    "pick": 1,
    "ok": true,
    "hit": 168.7,
    "misses": [
     518.1,
     294.9,
     263.7
    ]
   },
   {
    "round": 10,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 228.8,
    "misses": [
     756.9,
     573.2,
     470.0
    ]
   },
   {
    "round": 11,
    "live": 3,
    "pick": 3,
    "ok": true,
    "hit": 228.0,
    "misses": [
     498.6,
     377.5,
     255.0
    ]
   },
   {
    "round": 12,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 266.8,
    "misses": [
     506.9,
     446.9,
     480.9
    ]
   },
   {
    "round": 13,
    "live": 3,
    "pick": 3,
    "ok": true,
    "hit": 337.1,
    "misses": [
     567.3,
     482.7,
     490.1
    ]
   },
   {
    "round": 14,
    "live": 1,
    "pick": 1,
    "ok": true,
    "hit": 360.3,
    "misses": [
     631.9,
     480.0,
     503.5
    ]
   },
   {
    "round": 15,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 230.3,
    "misses": [
     535.0,
     514.7,
     466.6
    ]
   },
   {
    "round": 16,
    "live": 3,
    "pick": 3,
    "ok": true,
    "hit": 250.9,
    "misses": [
     500.0,
     546.5,
     530.2
    ]
   },
   {
    "round": 17,
    "live": 0,
    "pick": 0,
    "ok": true,
    "hit": 234.3,
    "misses": [
     580.9,
     557.0,
     550.9
    ]
   },
   {
    "round": 18,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 224.4,
    "misses": [
     603.8,
     481.1,
     502.9
    ]
   },
   {
    "round": 19,
    "live": 2,
    "pick": 2,
    "ok": true,
    "hit": 248.9,
    "misses": [
     419.6,
     463.3,
     464.2
    ]
   },
   {
    "round": 20,
    "live": 0,
    "pick": 0,
    "ok": true,
    "hit": 229.5,
    "misses": [
     409.7,
     389.7,
     469.6
    ]
   },
   {
    "round": 21,
    "live": 3,
    "pick": 3,
    "ok": true,
    "hit": 223.9,
    "misses": [
     446.1,
     408.1,
     450.1
    ]
   },
   {
    "round": 22,
    "live": 0,
    "pick": 0,
    "ok": true,
    "hit": 227.3,
    "misses": [
     509.0,
     462.8,
     486.8
    ]
   },
   {
    "round": 23,
    "live": 3,
    "pick": 3,
    "ok": true,
    "hit": 222.1,
    "misses": [
     462.5,
     462.8,
     457.5
    ]
   }
  ],
  "summary": {
   "rounds": 24,
   "seed": 24,
   "hit_med_ms": 229.5,
   "hit_min_ms": 168.7,
   "hit_max_ms": 392.0,
   "miss_med_ms": 486.7,
   "miss_min_ms": 255.0,
   "miss_max_ms": 756.9,
   "ratio": 2.12,
   "U": 13.0,
   "z": -7.2,
   "p": 2.8580493816845105e-20,
   "auc": 0.992,
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
   "picks": "5/6",
   "hit_med_ms": 132.1,
   "miss_med_ms": 166.9,
   "p": 0.009420785164492258
  },
  "realistic": {
   "picks": "6/6",
   "hit_med_ms": 132.8,
   "miss_med_ms": 169.5,
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
    "pct_p_below_001": 81
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
   478,
   463
  ]
 },
 "d1": {
  "pinned": {
   "rounds": 12,
   "seed": 25,
   "hit_med_ms": 239.1,
   "hit_min_ms": 213.3,
   "hit_max_ms": 567.6,
   "miss_med_ms": 474.7,
   "miss_min_ms": 372.1,
   "miss_max_ms": 701.4,
   "ratio": 1.98,
   "U": 77.0,
   "z": -3.31,
   "p": 0.0005712012216688502,
   "auc": 0.822,
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
   "hit_med_ms": 508.1,
   "hit_min_ms": 462.7,
   "hit_max_ms": 689.7,
   "miss_med_ms": 488.7,
   "miss_min_ms": 290.4,
   "miss_max_ms": 906.1,
   "ratio": 0.96,
   "U": 261.0,
   "z": 1.07,
   "p": 0.29359011485156017,
   "auc": 0.396,
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
  "salt_own": {
   "first_ms": 2092.0,
   "repeat_ms": [
    1688.1,
    1646.8,
    1639.7
   ]
  }
 },
 "d2": {
  "attack": {
   "rounds": 12,
   "seed": 26,
   "hit_med_ms": 558.2,
   "hit_min_ms": 393.4,
   "hit_max_ms": 740.3,
   "miss_med_ms": 584.5,
   "miss_min_ms": 378.3,
   "miss_max_ms": 795.6,
   "ratio": 1.05,
   "U": 181.0,
   "z": -0.83,
   "p": 0.4164350544122027,
   "auc": 0.581,
   "picks": {
    "k": 5,
    "n": 12,
    "p": 0.4167,
    "lo": 0.1933,
    "hi": 0.6805
   },
   "chance": 0.25,
   "oracle_ok": 0
  },
  "baseline": {
   "first_ms": 2030.6,
   "repeat_ms": [
    1728.6,
    1662.6,
    1670.1,
    1742.3,
    1715.9
   ],
   "repeat_cache_n": 138
  },
  "nocache": {
   "first_ms": 2077.9,
   "repeat_ms": [
    1943.9,
    1998.9,
    2325.7,
    2805.5,
    2331.2
   ],
   "repeat_cache_n": [
    0,
    0,
    0,
    0,
    0
   ]
  },
  "cost_s_per_1000": 609.8
 },
 "evaluate": {
  "shared": {
   "hit_med_ms": 232.6,
   "miss_med_ms": 493.0,
   "ratio": 2.12,
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
   "hit_med_ms": 223.8,
   "miss_med_ms": 225.9,
   "ratio": 1.01,
   "p": 0.6852017911639714,
   "picks": {
    "k": 1,
    "n": 8,
    "p": 0.125,
    "lo": 0.0224,
    "hi": 0.4709
   }
  },
  "salted": {
   "hit_med_ms": 516.0,
   "miss_med_ms": 494.7,
   "ratio": 0.96,
   "p": 0.5075649106794824,
   "picks": {
    "k": 1,
    "n": 8,
    "p": 0.125,
    "lo": 0.0224,
    "hi": 0.4709
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
