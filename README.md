# 🛡️ Claude Token Sentinel

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Designed%20for-Claude%20Code%20CLI-purple.svg)](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](#)

> **Real-time terminal HUD tokenometer and rate-limit sentinel for Claude Code. Tracks cumulative token burn, calculates live session cost, and fires early warnings before hitting Anthropic's 5-hour rate limits.**

---

```text
   ___ _                 _        _____     _                  
  / __\ | __ _ _   _  __| | ___  /__   \___ | | _____ _ __    
 / /  | |/ _` | | | |/ _` |/ _ \   / /\/ _ \| |/ / _ \ '_ \   
/ /___| | (_| | |_| | (_| |  __/  / / | (_) |   <  __/ | | |  
\____/|_|\__,_|\__,_|\__,_|\___|  \/   \___/|_|\_\___|_| |_|  
  ▸ Live Tokenometer & Rate Limit Sentinel for Claude Code

┌─────────────────────────────────────────────────────────────────────────────┐
│ SESSION METRICS & CONTEXT HEALTH                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Total Prompt Tokens     :       68,420 tokens                            │
│  • Total Completion Tokens :        8,150 tokens                            │
│  • Combined Context Window :       76,570 / 200,000 max                     │
│  • Conversational Turns    :           14 turns                             │
│  • Estimated Session Cost  :      $0.3275 USD                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ CONTEXT WINDOW LOAD:                                                        │
│  [████████████░░░░░░░░░░░░░░░░░░░░]  38.3%  |  Status: OPTIMAL (LOW WASTE)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 💡 The Problem
When coding with **Claude Code CLI**, developers often get locked out by Anthropic's **5-hour rate limit** without warning. 
Long multi-turn coding sessions quietly accumulate tens of thousands of tokens from large file reads, test outputs, and git diffs. By the time you notice, your token budget is wiped out.

## 🚀 The Solution
`claude-token-sentinel` acts as an active heads-up display (HUD) in your terminal:
1. **Live Context Meter:** Visualizes your 200k token window as a colored progress bar in real time.
2. **Early Warning Thresholds:**
   - 🟢 **Optimal (<80k tokens):** Safe to keep running large prompts.
   - 🟡 **Warning (80k–140k tokens):** Context accumulating, consider selective file reads.
   - 🔴 **Red Alert (>140k tokens):** Imminent rate-limit risk — recommends running `/compact` or pruning.
3. **Real-Time Cost Counter:** Computes exact session expenditure in USD based on official Anthropic Sonnet 3.5/5.5 API pricing.
4. **Zero External Dependencies:** Built purely on the Python standard library.

---

## ⚡ Quick Start

### 1. Installation
```bash
git clone https://github.com/diptapradipta21/claude-token-sentinel.git
cd claude-token-sentinel
chmod +x sentinel.py
```

### 2. Live Watch Mode
Run in a split terminal pane alongside your Claude Code session:
```bash
python3 sentinel.py
```

### 3. Quick Token Diagnostic Check
Instantly evaluate any token count against safety thresholds:
```bash
python3 sentinel.py --tokens 145000
```

---

## ⚙️ Configuration & Customization

You can adjust the refresh rate or monitor specific transcript files:

```bash
# Refresh every 2 seconds monitoring a custom session file
python3 sentinel.py --watch /path/to/claude/session.jsonl --interval 2.0
```

---

## 📄 License
This project is open-source under the [MIT License](LICENSE). Pull requests, terminal theme contributions, and platform integrations are welcome!
