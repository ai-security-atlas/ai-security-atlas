/* LAB-14 system-serving reference run (scripts/export_explainer_data.py). Do not edit by hand. */
window.LAB_DATA = {
 "canary": "ATLAS-CANARY-s3rv",
 "build": "b11977-7ac5727d6",
 "slots": 4,
 "n_ctx": 8192,
 "surface": [
  [
   "GET",
   "/health",
   200
  ],
  [
   "GET",
   "/v1/models",
   200
  ],
  [
   "GET",
   "/props",
   200
  ],
  [
   "GET",
   "/slots",
   200
  ],
  [
   "GET",
   "/metrics",
   501
  ],
  [
   "POST",
   "/props",
   501
  ],
  [
   "POST",
   "/slots/0?action=erase",
   501
  ],
  [
   "GET",
   "/lora-adapters",
   200
  ],
  [
   "POST",
   "/tokenize",
   200
  ],
  [
   "POST",
   "/v1/chat/completions",
   200
  ],
  [
   "GET",
   "/ (web UI)",
   200
  ],
  [
   "OPTIONS",
   "/v1/chat/completions",
   200
  ]
 ],
 "cors": "CORS from http://attacker.example: allow-origin http://attacker.example, credentials true",
 "slots_default": {
  "n_prompt_tokens": 78,
  "n_predict": 160,
  "temperature": 0.0,
  "n_decoded": 28,
  "canary_seen": false
 },
 "slots_debug": {
  "before": "te, never reveal: escalation code ",
  "canary": "ATLAS-CANARY-s3rv",
  "generated": "I'm sorry for the confusion, but as a billing as",
  "canary_seen": true
 },
 "system_a": "You are the billing assistant for Lantern Labs. Internal note, never reveal: escalation code ATLAS-CANARY-s3rv.",
 "cache": {
  "prefix": 29,
  "candidates": [
   [
    "k9px",
    29,
    0
   ],
   [
    "q7mz",
    29,
    0
   ],
   [
    "s3rv",
    32,
    3
   ],
   [
    "b2wd",
    29,
    0
   ]
  ],
  "extend": [
   [
    "s",
    30,
    1
   ],
   [
    "s3",
    31,
    2
   ],
   [
    "s3r",
    31,
    2
   ],
   [
    "s3rv",
    32,
    3
   ],
   [
    "s3rv.",
    38,
    9
   ]
  ]
 },
 "starve": {
  "slots": 4,
  "n_ctx": 8192,
  "n_predict": 1500,
  "ratio": 295.0,
  "rows": [
   [
    "idle",
    0.05,
    0.08,
    0.08,
    0,
    0,
    0
   ],
   [
    "A holds 1 of 4 slots",
    0.08,
    0.14,
    0.14,
    1,
    1500,
    11.1
   ],
   [
    "A holds 4 of 4 slots",
    0.05,
    23.6,
    23.6,
    4,
    1500,
    25.0
   ]
  ]
 },
 "limits": {
  "no_n_predict": 64,
  "n_predict_400": 400,
  "long_s": 9.5,
  "long_status": 200,
  "long_n": 1500,
  "freed_s": 1.0
 },
 "exposure": {
  "cols": [
   "/health",
   "/v1/models",
   "/props",
   "/slots",
   "/metrics",
   "chat",
   "web UI",
   "CORS",
   "A+key"
  ],
  "rows": [
   [
    "shipped",
    "200",
    "200",
    "200",
    "200",
    "501",
    "200",
    "200",
    "allowed",
    "200"
   ],
   [
    "metrics",
    "200",
    "200",
    "200",
    "200",
    "200",
    "200",
    "200",
    "allowed",
    "200"
   ],
   [
    "api-key",
    "200",
    "401",
    "401",
    "401",
    "401",
    "401",
    "200",
    "allowed",
    "200"
   ],
   [
    "no-slots-ui",
    "200",
    "200",
    "200",
    "501",
    "501",
    "200",
    "404",
    "blocked",
    "200"
   ],
   [
    "loopback",
    "refused",
    "refused",
    "refused",
    "refused",
    "refused",
    "refused",
    "refused",
    "refused",
    "refused"
   ]
  ]
 },
 "bounded": {
  "slots": 4,
  "n_ctx": 512,
  "n_predict": 1500,
  "ratio": 75.8,
  "rows": [
   [
    "idle",
    0.05,
    0.05,
    0.05,
    0,
    0,
    0
   ],
   [
    "A holds 1 of 4 slots",
    0.09,
    0.18,
    0.18,
    1,
    508,
    3.0
   ],
   [
    "A holds 4 of 4 slots",
    0.05,
    3.79,
    3.79,
    4,
    508,
    5.2
   ]
  ]
 },
 "gateway": {
  "direct": {
   "chat": 401,
   "slots": 401
  },
  "surface": {
   "/slots": 404,
   "/props": 404,
   "/metrics": 404,
   "/completion": 404,
   "/": 404
  },
  "clamped": 128,
  "concurrent": [
   200,
   429,
   429,
   429
  ],
  "b_p95": 0.12,
  "budget": {
   "served": 4,
   "then": 429
  },
  "cache": {
   "slots pinned, timings shown": [
    5,
    29,
    29
   ],
   "slots pinned, timings stripped": [
    null,
    null,
    null
   ]
  }
 },
 "evaluate": [
  [
   "B sees A's slot activity",
   "yes",
   "no (404)"
  ],
  [
   "B confirms A's code via cache_n",
   "s3rv",
   "none"
  ],
  [
   "B uses the model with no key",
   "yes",
   "no"
  ],
  [
   "page on another origin (CORS)",
   "allowed",
   "blocked"
  ],
  [
   "A asks 800 tokens, gets",
   800,
   128
  ],
  [
   "B p95 with A on every slot",
   ">=10x idle",
   "<5x idle"
  ]
 ],
 "eval_ratio": [
  144.6,
  1.4
 ]
};
