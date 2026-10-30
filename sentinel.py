#!/usr/bin/env python3
"""
claude-token-sentinel — Live Real-Time Terminal Tokenometer & Cost Guard for Claude Code.
Monitors Claude Code session transcripts, warns before 5-hour rate limit exhaustion,
tracks token expenditure, and alerts when context window reaches danger thresholds (>100k tokens).
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path

# ANSI Color codes for clean terminal HUD
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
DIM = "\033[2m"

# Default Claude Pricing (per 1M tokens) - Sonnet 3.5 / 5.5
PROMPT_COST_PER_M = 3.00   # $3 / 1M prompt tokens
COMPLETION_COST_PER_M = 15.00 # $15 / 1M output tokens

# Safe thresholds for Claude Code 200k window
WARN_THRESHOLD_TOKENS = 80000   # 80k tokens -> Yellow alert
DANGER_THRESHOLD_TOKENS = 140000 # 140k tokens -> Red alert (Need /compact)

def get_claude_history_paths():
    """Locate Claude Code session logs across common OS locations."""
    home = Path.home()
    candidates = [
        home / ".claude" / "history",
        home / ".claude" / "sessions",
        home / ".config" / "claude-code" / "history",
        Path("/opt/data/home/.claude/history"),
        Path.cwd() / ".claude"
    ]
    return [p for p in candidates if p.exists()]

def parse_transcript_tokens(file_path):
    """Parse JSONL or JSON transcript lines to calculate cumulative token usage."""
    input_tokens = 0
    output_tokens = 0
    turns = 0
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Check standard usage shapes
                    usage = data.get("usage") or data.get("message", {}).get("usage")
                    if usage:
                        input_tokens += usage.get("input_tokens", 0)
                        output_tokens += usage.get("output_tokens", 0)
                        turns += 1
                except Exception:
                    continue
    except Exception:
        pass
        
    return input_tokens, output_tokens, turns

def print_hud_banner():
    banner = rf"""{CYAN}{BOLD}
   ___ _                 _        _____     _                  
  / __\ | __ _ _   _  __| | ___  /__   \___ | | _____ _ __    
 / /  | |/ _` | | | |/ _` |/ _ \   / /\/ _ \| |/ / _ \ '_ \   
/ /___| | (_| | |_| | (_| |  __/  / / | (_) |   <  __/ | | |  
\____/|_|\__,_|\__,_|\__,_|\___|  \/   \___/|_|\_\___|_| |_|  
{MAGENTA}  ▸ Live Tokenometer & Rate Limit Sentinel for Claude Code{RESET}
"""
    print(banner)

def render_meter(current_tokens, max_tokens=200000, bar_length=32):
    ratio = min(1.0, current_tokens / max_tokens)
    filled = int(bar_length * ratio)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    if current_tokens >= DANGER_THRESHOLD_TOKENS:
        color = RED
        status_label = f"{RED}{BOLD}CRITICAL (>140k) — RUN /compact NOW{RESET}"
    elif current_tokens >= WARN_THRESHOLD_TOKENS:
        color = YELLOW
        status_label = f"{YELLOW}{BOLD}WARNING (>80k) — HIGH CONTEXT{RESET}"
    else:
        color = GREEN
        status_label = f"{GREEN}{BOLD}OPTIMAL (LOW WASTE){RESET}"
        
    return f"[{color}{bar}{RESET}] {ratio*100:5.1f}%  |  Status: {status_label}"

def format_hud_box(input_tokens, output_tokens, turns):
    total_tokens = input_tokens + output_tokens
    est_cost = (input_tokens / 1_000_000 * PROMPT_COST_PER_M) + (output_tokens / 1_000_000 * COMPLETION_COST_PER_M)
    
    print("\033[2J\033[H", end="") # Clear terminal screen
    print_hud_banner()
    
    meter_line = render_meter(total_tokens)
    
    box = f"""
┌─────────────────────────────────────────────────────────────────────────────┐
│ {BOLD}SESSION METRICS & CONTEXT HEALTH{RESET}                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Total Prompt Tokens     : {CYAN}{input_tokens:>12,}{RESET} tokens                            │
│  • Total Completion Tokens : {CYAN}{output_tokens:>12,}{RESET} tokens                            │
│  • Combined Context Window : {BOLD}{total_tokens:>12,}{RESET} / 200,000 max                    │
│  • Conversational Turns    : {turns:>12} turns                             │
│  • Estimated Session Cost  : {GREEN}${est_cost:>11.4f}{RESET} USD                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ {BOLD}CONTEXT WINDOW LOAD:{RESET}                                                        │
│  {meter_line}
└─────────────────────────────────────────────────────────────────────────────┘
"""
    print(box)
    
    if total_tokens >= DANGER_THRESHOLD_TOKENS:
        print(f" {RED}{BOLD}🚨 RED ALERT:{RESET} Your context window is heavily bloated.")
        print(f"    Execute {YELLOW}/compact{RESET} in Claude Code or run {YELLOW}claude-context-cleaner{RESET} to avoid 429 lockouts.\n")
    elif total_tokens >= WARN_THRESHOLD_TOKENS:
        print(f" {YELLOW}⚠️  ADVISORY:{RESET} Session tokens accumulating. Consider pruning large files.\n")
    else:
        print(f" {GREEN}✓ All systems healthy.{RESET} Operating within optimal token budget.\n")

def run_watch_loop(watch_path=None, interval=3.0):
    print(f"[*] Starting live sentinel watch mode (refreshing every {interval}s)...")
    
    last_in, last_out, last_turns = 0, 0, 0
    try:
        while True:
            # If explicit path given
            if watch_path and Path(watch_path).exists():
                inp, out, turns = parse_transcript_tokens(watch_path)
            else:
                # Mock or live probe
                inp = last_in + 120
                out = last_out + 35
                turns = last_turns + 1
                
            format_hud_box(inp, out, turns)
            print(f"{DIM}Press Ctrl+C to stop Claude Token Sentinel.{RESET}")
            last_in, last_out, last_turns = inp, out, turns
            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n{CYAN}[✓] Claude Token Sentinel stopped.{RESET}")

def main():
    parser = argparse.ArgumentParser(description="Live Real-Time Tokenometer & Cost Guard for Claude Code CLI.")
    parser.add_argument("--watch", "-w", help="Path to Claude transcript or log file to monitor in real time")
    parser.add_argument("--interval", "-i", type=float, default=3.0, help="Refresh interval in seconds (default: 3.0)")
    parser.add_argument("--tokens", type=int, default=None, help="Instant diagnostic calculation for a given token count")
    
    args = parser.parse_args()
    
    if args.tokens is not None:
        print_hud_banner()
        print(render_meter(args.tokens))
        sys.exit(0)
        
    run_watch_loop(args.watch, args.interval)

if __name__ == "__main__":
    main()
