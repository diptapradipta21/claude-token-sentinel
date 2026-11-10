#!/usr/bin/env python3
"""
claude-token-sentinel — Live Real-Time Terminal Tokenometer & Cost Guard for Claude Code.
Monitors Claude Code session transcripts, warns before 5-hour rate limit exhaustion,
tracks token expenditure, and alerts when context window reaches danger thresholds (>140k tokens).
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
# Claude Pricing Tiers (per 1M tokens: prompt, completion)
MODEL_PRICING = {
    "sonnet": (3.00, 15.00),  # Claude 3.5/3.7 Sonnet
    "opus": (15.00, 75.00),    # Claude 3 Opus
    "haiku": (0.80, 4.00),     # Claude 3.5 Haiku
}
DEFAULT_MODEL = "sonnet"
PROMPT_COST_PER_M = MODEL_PRICING[DEFAULT_MODEL][0]
COMPLETION_COST_PER_M = MODEL_PRICING[DEFAULT_MODEL][1]


def calculate_cost(input_tokens: int, output_tokens: int, model: str = DEFAULT_MODEL) -> float:
    prompt_rate, completion_rate = MODEL_PRICING.get(model.lower(), MODEL_PRICING[DEFAULT_MODEL])
    return (input_tokens / 1_000_000 * prompt_rate) + (output_tokens / 1_000_000 * completion_rate)

# Safe thresholds for Claude Code 200k window
DEFAULT_WARN_THRESHOLD = 80000    # 80k tokens -> Yellow alert
DEFAULT_DANGER_THRESHOLD = 140000 # 140k tokens -> Red alert (Need /compact)

def get_claude_history_paths():
    """Locate Claude Code session logs across common OS locations."""
    home = Path.home()
    candidates = [
        home / ".claude" / "history",
        home / ".claude" / "sessions",
        home / ".claude" / "projects",
        home / ".config" / "claude-code" / "history",
        Path("/opt/data/home/.claude/history"),
        Path("/opt/data/home/.claude/sessions"),
        Path.cwd() / ".claude"
    ]
    return [p for p in candidates if p.exists()]

def find_latest_transcript():
    """Discover the most recently modified Claude Code transcript file."""
    search_dirs = get_claude_history_paths()
    found_files = []
    for base in search_dirs:
        if base.is_file():
            found_files.append(base)
        elif base.is_dir():
            found_files.extend(base.rglob("*.jsonl"))
            found_files.extend(base.rglob("*.json"))
    if not found_files:
        return None
    return max(found_files, key=lambda f: f.stat().st_mtime)

def parse_transcript_tokens(file_path):
    """Parse JSONL or JSON transcript lines to calculate cumulative token usage."""
    input_tokens = 0
    output_tokens = 0
    turns = 0
    
    p = Path(file_path) if file_path else None
    if not p or not p.exists() or not p.is_file():
        return 0, 0, 0

    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return 0, 0, 0

    # Line-by-line JSONL streaming parse
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            usage = data.get("usage") or data.get("message", {}).get("usage")
            if usage:
                input_tokens += usage.get("input_tokens", 0)
                output_tokens += usage.get("output_tokens", 0)
                turns += 1
        except Exception:
            continue

    # Fallback for formatted single-document JSON array or object
    if turns == 0 and content.strip():
        try:
            raw = json.loads(content)
            items = raw if isinstance(raw, list) else [raw]
            for item in items:
                if isinstance(item, dict):
                    usage = item.get("usage") or item.get("message", {}).get("usage")
                    if usage:
                        input_tokens += usage.get("input_tokens", 0)
                        output_tokens += usage.get("output_tokens", 0)
                        turns += 1
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

def get_status_info(total_tokens, warn_threshold=DEFAULT_WARN_THRESHOLD, danger_threshold=DEFAULT_DANGER_THRESHOLD):
    if total_tokens >= danger_threshold:
        return "critical", RED, f"{RED}{BOLD}CRITICAL (>={danger_threshold:,}) — RUN /compact NOW{RESET}"
    elif total_tokens >= warn_threshold:
        return "warning", YELLOW, f"{YELLOW}{BOLD}WARNING (>={warn_threshold:,}) — HIGH CONTEXT{RESET}"
    return "optimal", GREEN, f"{GREEN}{BOLD}OPTIMAL (LOW WASTE){RESET}"

def render_meter(current_tokens, max_tokens=200000, bar_length=32, warn_threshold=DEFAULT_WARN_THRESHOLD, danger_threshold=DEFAULT_DANGER_THRESHOLD):
    ratio = min(1.0, current_tokens / max_tokens) if max_tokens > 0 else 0.0
    filled = int(bar_length * ratio)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    _, color, status_label = get_status_info(current_tokens, warn_threshold, danger_threshold)
    return f"[{color}{bar}{RESET}] {ratio*100:5.1f}%  |  Status: {status_label}"

def format_hud_box(input_tokens, output_tokens, turns, source_label="Live", warn_threshold=DEFAULT_WARN_THRESHOLD, danger_threshold=DEFAULT_DANGER_THRESHOLD, model=DEFAULT_MODEL):
    total_tokens = input_tokens + output_tokens
    est_cost = calculate_cost(input_tokens, output_tokens, model=model)
    status_key, _, _ = get_status_info(total_tokens, warn_threshold, danger_threshold)
    
    meter_line = render_meter(total_tokens, warn_threshold=warn_threshold, danger_threshold=danger_threshold)
    
    box = f"""
┌─────────────────────────────────────────────────────────────────────────────┐
│ {BOLD}SESSION METRICS & CONTEXT HEALTH{RESET} [{DIM}{source_label}{RESET}]
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
    
    if status_key == "critical":
        print(f" {RED}{BOLD}🚨 RED ALERT:{RESET} Your context window is heavily bloated.")
        print(f"    Execute {YELLOW}/compact{RESET} in Claude Code or run {YELLOW}claude-context-cleaner{RESET} to avoid 429 lockouts.\n")
    elif status_key == "warning":
        print(f" {YELLOW}⚠️  ADVISORY:{RESET} Session tokens accumulating. Consider pruning large files.\n")
    else:
        print(f" {GREEN}✓ All systems healthy.{RESET} Operating within optimal token budget.\n")

def get_metrics_payload(input_tokens, output_tokens, turns, source_label, warn_threshold=DEFAULT_WARN_THRESHOLD, danger_threshold=DEFAULT_DANGER_THRESHOLD, model=DEFAULT_MODEL):
    total_tokens = input_tokens + output_tokens
    est_cost = round(calculate_cost(input_tokens, output_tokens, model=model), 4)
    status_key, _, _ = get_status_info(total_tokens, warn_threshold, danger_threshold)
    return {
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "total_tokens": total_tokens,
        "turns": turns,
        "model": model,
        "estimated_cost_usd": est_cost,
        "context_window_max": 200000,
        "context_load_pct": round((total_tokens / 200000) * 100, 2),
        "status": status_key,
        "source": source_label,
        "danger_threshold": danger_threshold,
        "warn_threshold": warn_threshold
    }

def run_watch_loop(watch_path=None, interval=3.0, demo=False, warn_threshold=DEFAULT_WARN_THRESHOLD, danger_threshold=DEFAULT_DANGER_THRESHOLD, model=DEFAULT_MODEL):
    print(f"[*] Starting live sentinel watch mode (refreshing every {interval}s)...")
    
    resolved_path = None
    if watch_path:
        p = Path(watch_path)
        if not p.exists():
            print(f"{RED}[!] Error: Specified transcript not found: {watch_path}{RESET}")
            sys.exit(1)
        resolved_path = p
    elif not demo:
        resolved_path = find_latest_transcript()
        if not resolved_path:
            print(f"{YELLOW}[!] No active Claude Code transcript detected in standard paths.{RESET}")
            print(f"    Run with {CYAN}--watch /path/to/session.jsonl{RESET} or try {MAGENTA}--demo{RESET} for HUD preview.")
            sys.exit(1)

    demo_step = 0
    try:
        while True:
            if demo:
                demo_step += 1
                inp = 24000 + (demo_step * 8500)
                out = 3200 + (demo_step * 1200)
                turns = demo_step * 3
                label = f"DEMO SIMULATION (Tick #{demo_step})"
            else:
                inp, out, turns = parse_transcript_tokens(resolved_path)
                label = resolved_path.name

            print("\033[2J\033[H", end="") # Clear terminal screen
            print_hud_banner()
            format_hud_box(inp, out, turns, source_label=label, warn_threshold=warn_threshold, danger_threshold=danger_threshold, model=model)
            print(f"{DIM}Press Ctrl+C to stop Claude Token Sentinel.{RESET}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n{CYAN}[✓] Claude Token Sentinel stopped.{RESET}")

def main():
    parser = argparse.ArgumentParser(description="Live Real-Time Tokenometer & Cost Guard for Claude Code CLI.")
    parser.add_argument("--watch", "-w", help="Path to Claude transcript or log file to monitor in real time")
    parser.add_argument("--interval", "-i", type=float, default=3.0, help="Refresh interval in seconds (default: 3.0)")
    parser.add_argument("--tokens", type=int, default=None, help="Instant diagnostic calculation for a given token count")
    parser.add_argument("--once", action="store_true", help="Inspect session once and exit without loop (useful for CI/hooks)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON metrics")
    parser.add_argument("--demo", action="store_true", help="Simulate token consumption progression for HUD testing")
    parser.add_argument("--warn-threshold", type=int, default=DEFAULT_WARN_THRESHOLD, help=f"Custom token warning threshold (default: {DEFAULT_WARN_THRESHOLD})")
    parser.add_argument("--danger-threshold", type=int, default=DEFAULT_DANGER_THRESHOLD, help=f"Custom token danger threshold (default: {DEFAULT_DANGER_THRESHOLD})")
    parser.add_argument("--model", "-m", choices=list(MODEL_PRICING.keys()), default=DEFAULT_MODEL, help="Claude model tier for cost calculation (sonnet, opus, haiku; default: sonnet)")

    args = parser.parse_args()

    # Diagnostic token calculator
    if args.tokens is not None:
        if args.json:
            payload = get_metrics_payload(args.tokens, 0, 1, "CLI --tokens", args.warn_threshold, args.danger_threshold, model=args.model)
            print(json.dumps(payload, indent=2))
        else:
            print_hud_banner()
            print(render_meter(args.tokens, warn_threshold=args.warn_threshold, danger_threshold=args.danger_threshold))
        sys.exit(0)

    # Single snapshot evaluation mode
    if args.once:
        resolved_path = Path(args.watch) if args.watch else find_latest_transcript()
        if not resolved_path or not resolved_path.exists():
            if args.demo:
                inp, out, turns = 65000, 7200, 12
                label = "DEMO SNAPSHOT"
            else:
                if args.json:
                    print(json.dumps({"error": "No active Claude Code transcript found"}))
                else:
                    print(f"{RED}[!] Error: No active Claude Code transcript found.{RESET}")
                sys.exit(1)
        else:
            inp, out, turns = parse_transcript_tokens(resolved_path)
            label = resolved_path.name

        if args.json:
            payload = get_metrics_payload(inp, out, turns, label, args.warn_threshold, args.danger_threshold, model=args.model)
            print(json.dumps(payload, indent=2))
        else:
            print_hud_banner()
            format_hud_box(inp, out, turns, source_label=label, warn_threshold=args.warn_threshold, danger_threshold=args.danger_threshold, model=args.model)
        
        total = inp + out
        if total >= args.danger_threshold:
            sys.exit(2)
        elif total >= args.warn_threshold:
            sys.exit(1)
        sys.exit(0)

    run_watch_loop(args.watch, args.interval, demo=args.demo, warn_threshold=args.warn_threshold, danger_threshold=args.danger_threshold, model=args.model)

if __name__ == "__main__":
    main()
