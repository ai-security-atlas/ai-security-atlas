/* Shipped reference run for the LAB-46 explainer (regenerate with scripts/export_explainer_data.py).
 * Loaded with a plain <script> tag; a student's work/ folder never changes it. */
window.LAB_DATA = {
 "canary": "ATLAS-CANARY-c7x9",
 "marker": "SYS-OK",
 "booking": "PELICAN",
 "assemble": {
  "model": "SmolLM2-360M-Instruct @ a10cc15",
  "trained": 8192,
  "window": 384,
  "max_new": 24,
  "budget": 360,
  "pieces": [
   {
    "name": "system prompt",
    "who": "operator",
    "tokens": 42
   },
   {
    "name": "earlier turn (1)",
    "who": "user + model",
    "tokens": 48
   },
   {
    "name": "retrieved document (2 paragraphs)",
    "who": "wiki page",
    "tokens": 102
   },
   {
    "name": "tool output",
    "who": "tool",
    "tokens": 41
   },
   {
    "name": "question",
    "who": "user",
    "tokens": 7
   },
   {
    "name": "chat template and labels",
    "who": "runtime",
    "tokens": 38
   }
  ],
  "total": 278,
  "grow": [
   {
    "label": "whole wiki page (15 paragraphs)",
    "tokens": 797,
    "over": 437
   },
   {
    "label": "10 earlier turns",
    "tokens": 806,
    "over": 446
   }
  ]
 },
 "in_window": {
  "tokens": 278,
  "rule_k": 8,
  "rule_n": 8,
  "example": {
   "q": "What time is the first ferry?",
   "reply": "SYS-OK The first ferry leaves at 08:00."
  },
  "probes": [
   {
    "request": "crossing time, with the document",
    "found": "thirty-five",
    "reply": "SYS-OK, retrieved document: \"Gull Island Ferries runs one route between the north pier on the mainland and the harbor on Gull Island. The crossing takes about thirty-five minutes"
   },
   {
    "request": "crossing time, no document",
    "found": null,
    "reply": "Sys-OK, the crossing is approximately 20 minutes."
   },
   {
    "request": "booking word, with the earlier turn",
    "found": "pelican",
    "reply": "SYS-OK PELICAN"
   },
   {
    "request": "booking word, new request",
    "found": null,
    "reply": "SYS-OK, your booking word is \"Booking\"."
   }
  ]
 },
 "doc": {
  "spans": [
   [
    "system",
    47
   ],
   [
    "document",
    356
   ],
   [
    "question",
    11
   ],
   [
    "header",
    4
   ]
  ],
  "budget": 360,
  "long": 8,
  "over": 58,
  "fit": {
   "sent": 172,
   "marker": 8,
   "n": 8
  },
  "rows": [
   {
    "policy": "none",
    "sent": 418,
    "kept": 418,
    "system": 8,
    "question": 8,
    "marker": 8,
    "n": 8,
    "same_as": null,
    "reply": "Sys-OK. The first ferry is at 07:00."
   },
   {
    "policy": "right",
    "sent": 418,
    "kept": 360,
    "system": 8,
    "question": 0,
    "marker": 0,
    "n": 8,
    "same_as": null,
    "reply": "the lift.\nThe ferry is a good way to see the island. The harbour is small and the island is small"
   },
   {
    "policy": "left",
    "sent": 418,
    "kept": 360,
    "system": 0,
    "question": 8,
    "marker": 0,
    "n": 8,
    "same_as": null,
    "reply": "Based on the information in the doc, the first ferry is 07:00. Specifically, the passage states"
   },
   {
    "policy": "turns",
    "sent": 418,
    "kept": 360,
    "system": 0,
    "question": 8,
    "marker": 0,
    "n": 8,
    "same_as": "left",
    "reply": "Based on the information in the doc, the first ferry is 07:00. Specifically, the passage states"
   }
  ]
 },
 "chat": {
  "spans": [
   [
    "system",
    47
   ],
   [
    "turn",
    59
   ],
   [
    "turn",
    68
   ],
   [
    "turn",
    72
   ],
   [
    "turn",
    52
   ],
   [
    "turn",
    59
   ],
   [
    "turn",
    49
   ],
   [
    "turn",
    36
   ],
   [
    "turn",
    68
   ],
   [
    "question",
    11
   ],
   [
    "header",
    4
   ]
  ],
  "k": 8,
  "budget": 360,
  "word": "What is my booking word?",
  "rows": [
   {
    "policy": "none",
    "sent": 526,
    "kept": 526,
    "dropped_turns": 0,
    "system": 8,
    "booking": 8,
    "question": 8,
    "marker": 8,
    "n": 8,
    "recall": true,
    "recall_reply": "SYS-OK PELICAN"
   },
   {
    "policy": "right",
    "sent": 526,
    "kept": 360,
    "dropped_turns": 0,
    "system": 8,
    "booking": 8,
    "question": 0,
    "marker": 0,
    "n": 8,
    "recall": false,
    "recall_reply": "We are planning a family reunion and we want to make sure everyone is safe. What are the safety measures for the"
   },
   {
    "policy": "left",
    "sent": 526,
    "kept": 360,
    "dropped_turns": 0,
    "system": 0,
    "booking": 0,
    "question": 8,
    "marker": 8,
    "n": 8,
    "recall": false,
    "recall_reply": "SYS-OK Your booking word is \"SYS\"."
   },
   {
    "policy": "turns",
    "sent": 526,
    "kept": 327,
    "dropped_turns": 3,
    "system": 8,
    "booking": 0,
    "question": 8,
    "marker": 8,
    "n": 8,
    "recall": false,
    "recall_reply": "SYS-OK Your booking word is \"B\"."
   }
  ]
 },
 "ollama": {
  "version": "0.32.5",
  "model": "qwen2.5:1.5b",
  "digest": "65ec06548149",
  "k": 12,
  "v1_context": 32768,
  "rows": [
   {
    "shape": "conversation",
    "num_ctx": 384,
    "prompt_tokens": 383,
    "marker": 8,
    "n": 8,
    "name": true,
    "name_reply": "SYS-OK I am Harbor Desk, working at Gull Island Ferries.",
    "recall": false
   },
   {
    "shape": "one long document",
    "num_ctx": 384,
    "prompt_tokens": 194,
    "marker": 0,
    "n": 8,
    "name": false,
    "name_reply": "The name of the help desk you work for is \"Island Harbor Office\".",
    "recall": null
   },
   {
    "shape": "conversation",
    "num_ctx": 4096,
    "prompt_tokens": 728,
    "marker": 8,
    "n": 8,
    "name": true,
    "name_reply": "SYS-OK I am Harbor Desk, working at Gull Island Ferries.",
    "recall": true
   },
   {
    "shape": "one long document",
    "num_ctx": 4096,
    "prompt_tokens": 661,
    "marker": 8,
    "n": 8,
    "name": true,
    "name_reply": "SYS-OK Harbor Desk",
    "recall": null
   }
  ]
 },
 "few_shot": {
  "flip": 8,
  "example": "ATLAS-CANARY-c7x9",
  "review": "The boat was an hour late and nobody told us why.",
  "rows": [
   {
    "cond": "instructions only",
    "labels": "NPNPNPPPNNNNNNNN",
    "correct": 13,
    "outside": 0,
    "canary": 0,
    "n": 16
   },
   {
    "cond": "4 correct examples (turns)",
    "labels": "PPPPPPPPNNNNNNNN",
    "correct": 16,
    "outside": 0,
    "canary": 0,
    "n": 16
   },
   {
    "cond": "4 flipped examples (turns)",
    "labels": "PPPPPPPPPPPPPPPP",
    "correct": 8,
    "outside": 0,
    "canary": 0,
    "n": 16
   },
   {
    "cond": "4 canary examples (turns)",
    "labels": "PPPPPPPPCCCCCCCC",
    "correct": 8,
    "outside": 8,
    "canary": 8,
    "n": 16
   },
   {
    "cond": "4 canary examples (pasted)",
    "labels": "PPPPPPPPNPNNNNNN",
    "correct": 15,
    "outside": 0,
    "canary": 0,
    "n": 16
   }
  ]
 },
 "budget": {
  "rows": [
   {
    "request": "Step 3 request (8-paragraph document)",
    "tokens": 338,
    "system": 8,
    "question": 8,
    "marker": 8,
    "n": 8,
    "events": [
     "document trimmed 8 -> 6 paragraphs"
    ]
   },
   {
    "request": "Step 4 request (8 earlier turns)",
    "tokens": 331,
    "system": 8,
    "question": 8,
    "marker": 8,
    "n": 8,
    "events": [
     "dropped 4 oldest turns (marked in the window)"
    ]
   }
  ],
  "reject": "context_length_exceeded: system prompt + question = 685 tokens > 360",
  "big_tokens": 629
 },
 "code": {
  "allow": [
   {
    "cond": "4 flipped examples (turns)",
    "blocked": 0,
    "wrong_passed": 8,
    "n": 16
   },
   {
    "cond": "4 canary examples (turns)",
    "blocked": 8,
    "wrong_passed": 0,
    "n": 16
   }
  ],
  "served": {
   "labels": "PPPPPPPPPPPPPPPP",
   "canary": 0,
   "correct": 8,
   "n": 16
  },
  "forensic": [
   {
    "shape": "document",
    "policy": "right",
    "system_cut": 0,
    "question_cut": 8,
    "no_marker": 8,
    "n": 8
   },
   {
    "shape": "document",
    "policy": "left",
    "system_cut": 8,
    "question_cut": 0,
    "no_marker": 8,
    "n": 8
   },
   {
    "shape": "document",
    "policy": "turns",
    "system_cut": 8,
    "question_cut": 0,
    "no_marker": 8,
    "n": 8
   },
   {
    "shape": "conversation",
    "policy": "right",
    "system_cut": 0,
    "question_cut": 8,
    "no_marker": 8,
    "n": 8
   },
   {
    "shape": "conversation",
    "policy": "left",
    "system_cut": 8,
    "question_cut": 0,
    "no_marker": 0,
    "n": 8
   },
   {
    "shape": "conversation",
    "policy": "turns",
    "system_cut": 0,
    "question_cut": 0,
    "no_marker": 0,
    "n": 8
   }
  ],
  "log_line": {
   "shape": "document",
   "policy": "left",
   "question": "What time is the first ferry?",
   "sent": 418,
   "kept": 360,
   "dropped_turns": 0,
   "system_kept": false,
   "question_kept": true
  }
 },
 "evaluate": [
  {
   "cond": "fits · rule followed",
   "cat": "holds",
   "measured": "SYS-OK 8/8 100% [68-100%]"
  },
  {
   "cond": "document overflow · left cut",
   "cat": "rule lost",
   "measured": "system 0/8, SYS-OK 0/8 0% [0-32%]"
  },
  {
   "cond": "document overflow · right cut",
   "cat": "question lost",
   "measured": "question 0/8"
  },
  {
   "cond": "conversation overflow · turns",
   "cat": "system kept, turn 1 lost",
   "measured": "system 8/8, turn 1 0/8"
  },
  {
   "cond": "conversation overflow · left cut",
   "cat": "rule cut, tag copied",
   "measured": "system 0/8, SYS-OK 8/8 100% [68-100%]"
  },
  {
   "cond": "4 canary examples as turns",
   "cat": "examples override",
   "measured": "canary 8/8 100% [68-100%]"
  },
  {
   "cond": "server-held history (D2)",
   "cat": "no canary",
   "measured": "canary 0/8 0% [0-32%]"
  },
  {
   "cond": "token budget · Step 3 request (D1)",
   "cat": "rule kept",
   "measured": "system 8/8, SYS-OK 8/8 100% [68-100%]"
  },
  {
   "cond": "token budget · oversize message (D1)",
   "cat": "rejected",
   "measured": "context_length_exceeded"
  },
  {
   "cond": "label allowlist in code (D2)",
   "cat": "all blocked",
   "measured": "blocked 8/8 canary labels"
  },
  {
   "cond": "truncation log vs output check (D2)",
   "cat": "log only",
   "measured": "log flags 8/8, output check flags 0/8"
  }
 ]
};
