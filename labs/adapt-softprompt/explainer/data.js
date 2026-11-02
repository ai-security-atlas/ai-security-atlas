/* Shipped reference run for the LAB-58 explainer (regenerate with scripts/export_explainer_data.py).
 * Loaded with a plain <script> tag; a student's work/ folder never changes it. */
window.LAB_DATA = {
 "canary": "ATLAS-CANARY-s0ft",
 "model": "SmolLM2-135M-Instruct",
 "repo": "HuggingFaceTB/SmolLM2-135M-Instruct",
 "rev": "12fd25f",
 "queues": [
  "billing",
  "shipping",
  "account",
  "other"
 ],
 "n_train": 40,
 "n_heldout": 24,
 "n_virtual": 8,
 "gate": {
  "total": 16,
  "per_queue": 3
 },
 "task": {
  "params": 134515008,
  "layers": 30,
  "hidden": 576,
  "vocab": 49152,
  "instruction_tokens": 46,
  "none": {
   "correct": 9,
   "counts": {
    "billing": 0,
    "shipping": 14,
    "account": 0,
    "other": 10
   }
  },
  "written": {
   "correct": 6,
   "counts": {
    "billing": 24,
    "shipping": 0,
    "account": 0,
    "other": 0
   }
  }
 },
 "soft": {
  "trainable": 4608,
  "frozen": 134515008,
  "secs": 57.6,
  "train": 40,
  "heldout": 18,
  "bytes": 18552,
  "fired": 6,
  "sha": "b93b49a924ca5cc9",
  "trace": [
   10.4198,
   8.9181,
   9.3418,
   6.3592,
   3.5691,
   2.0946,
   1.4956,
   1.1949,
   0.9581,
   0.9035,
   0.7243,
   0.5651,
   0.4017,
   0.2881,
   0.1751,
   0.1747
  ]
 },
 "read": {
  "near": [
   [
    "Ġmid",
    0.141,
    50.743
   ],
   [
    "ĠNot",
    0.134,
    52.796
   ],
   [
    "ĠMorgan",
    0.122,
    47.109
   ],
   [
    "Ġrelevant",
    0.125,
    48.513
   ],
   [
    "Ġash",
    0.165,
    50.21
   ],
   [
    "Ġbind",
    0.119,
    54.605
   ],
   [
    "Ġconvert",
    0.17,
    49.201
   ],
   [
    "Ġcould",
    0.126,
    59.22
   ]
  ],
  "norms": [
   51.012,
   53.041,
   47.341,
   48.749,
   50.581,
   54.85,
   49.543,
   59.491
  ],
  "vocab_norm_median": 3.154,
  "vocab_norm_min": 1.793,
  "vocab_norm_max": 7.494,
  "token_nn_cos_median": 0.581,
  "text": " mid Not Morgan relevant ash bind convert could",
  "heldout_vectors": 18,
  "heldout_text": 7
 },
 "prefix": {
  "trainable": 92160,
  "bytes": 368760,
  "layers": 30,
  "kv_shape": [
   1,
   3,
   8,
   64
  ],
  "secs": 41.2,
  "train": 40,
  "heldout": 21
 },
 "swap": {
  "heldout_true": 9,
  "heldout_swapped": 9,
  "fired": 15,
  "train_swapped": 19,
  "bytes": 18552,
  "sha": "ddb6cd9286bd3cb7",
  "config_diff": []
 },
 "d1": {
  "pin": "b93b49a924ca5cc9",
  "vocab_norm_max": 7.49,
  "norm_flags": 3,
  "static_same": true,
  "norm_overlap_swapped": true,
  "norm_overlap_untrained": false,
  "rows": {
   "softprompt": {
    "norm_min": 47.34,
    "norm_max": 59.49,
    "max_cos": 0.17,
    "pin": true,
    "sha": "b93b49a924ca"
   },
   "softprompt-swapped": {
    "norm_min": 48.31,
    "norm_max": 54.74,
    "max_cos": 0.164,
    "pin": false,
    "sha": "ddb6cd9286bd"
   },
   "softprompt-untrained": {
    "norm_min": 22.4,
    "norm_max": 25.91,
    "max_cos": 0.16,
    "pin": false,
    "sha": "0a6343251ccf"
   }
  }
 },
 "d2": {
  "softprompt": {
   "total": 18,
   "per": {
    "billing": 5,
    "shipping": 5,
    "account": 5,
    "other": 3
   },
   "pass": true,
   "fired": 6
  },
  "softprompt-swapped": {
   "total": 9,
   "per": {
    "billing": 1,
    "shipping": 4,
    "account": 1,
    "other": 3
   },
   "pass": false,
   "fired": 15
  },
  "softprompt-untrained": {
   "total": 6,
   "per": {
    "billing": 0,
    "shipping": 6,
    "account": 0,
    "other": 0
   },
   "pass": false,
   "fired": 18
  },
  "prefix": {
   "total": 21,
   "per": {
    "billing": 5,
    "shipping": 4,
    "account": 6,
    "other": 6
   },
   "pass": true,
   "fired": 3
  }
 },
 "evaluate": {
  "base, no instruction: held-out correct (of 24)": 9,
  "base, written instruction: held-out correct (of 24)": 6,
  "soft prompt trainable numbers": 4608,
  "prefix trainable numbers": 92160,
  "fresh soft prompt: held-out correct (of 24)": 18,
  "fresh soft prompt passes the D2 gate": true,
  "learned vectors' nearest-token cosine < 0.5": true,
  "nearest tokens as text: held-out correct (of 24)": 7,
  "prefix file: held-out correct (of 24)": 21,
  "swapped file: held-out correct (of 24)": 9,
  "static checks see one shape, dtype and length": true,
  "sha256 pin accepts (of 3 soft prompt files)": 1,
  "D2 gate accepts the Step 2 file": true,
  "D2 gate rejects the swapped file": true,
  "D2 gate rejects the untrained file": true,
  "D2 gate accepts the prefix file": true
 }
};
