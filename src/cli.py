#!/usr/bin/env python3
"""
Nexus Agent CLI — src/cli.py
Command-line interface for Nexus Agent
Works on Windows, Linux, and macOS
"""

import sys
import os
import argparse
import json
import time

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.config import load_config, get_config
from src.device import SystemInfo, ProcessManager, RegistryManager, ServiceManager, PowerControl
from src.memory import MemoryManager
from src.vision import ScreenCapture, ScreenAnalyzer


def green(t): return f"\033[92m{t}\033[0m"
def red(t): return f"\033[91m{t}\033[0m"
def cyan(t): return f"\033[96m{t}\033[0m"
def bold(t): return f"\033[1m{t}\033[0m"


def cmd_system(args):
    si = SystemInfo()
    stats = si.get_full_stats()
    print(bold("━" * 50))
    print(bold(" NEXUS AGENT — SYSTEM INFO"))
    print(bold("━" * 50))
    print(f"  Hostname   : {stats['hostname']}")
    print(f"  OS         : {stats['platform']['os']} {stats['platform']['release']}")
    print(f"  Uptime     : {stats['uptime']['human']}")
    print()
    cpu = stats["cpu"]
    print(f"  CPU        : {cpu['overall_percent']:.1f}% overall")
    print(f"  Cores      : {cpu['count']} (logical), {os.cpu_count()} physical")
    print()
    mem = stats["memory"]
    print(f"  RAM        : {mem['used_gb']:.1f}GB / {mem['total_gb']:.1f}GB ({mem['percent']:.1f}%)")
    print(f"  Swap       : {mem['swap_used_gb']:.1f}GB / {mem['swap_total_gb']:.1f}GB")
    print()
    for d in stats["disks"]:
        print(f"  Disk {d['mountpoint']:<8} : {d['used_gb']:.0f}GB / {d['total_gb']:.0f}GB ({d['percent']:.0f}%)")
    print()
    net = stats["network"]
    print(f"  Network    : ↓{net['bytes_recv_mb']}MB  ↑{net['bytes_sent_mb']}MB")
    print(bold("━" * 50))


def cmd_processes(args):
    pm = ProcessManager()
    if args.subcmd == "list":
        procs = pm.list_processes(sort_by=args.sort, limit=args.limit)
        print(bold(f"{'PID':<8} {'NAME':<35} {'CPU%':<8} {'MEM%':<8}"))
        print("-" * 65)
        for p in procs:
            name = p["name"][:33] if len(p["name"]) > 33 else p["name"]
            print(f"{p['pid']:<8} {name:<35} {p['cpu_pct']:>6.1f}% {p['mem_pct']:>6.1f}%")
    elif args.subcmd == "kill":
        r = pm.kill_process(args.pid, force=args.force)
        print(green("Killed") if r["success"] else red(f"Failed: {r.get('error')}"))
    elif args.subcmd == "search":
        results = pm.search_processes(args.name)
        print(bold(f"Found {len(results)} processes matching '{args.name}':"))
        for p in results:
            print(f"  {p['pid']:<8} {p['name']}")
    elif args.subcmd == "top":
        which = "cpu" if args.type == "cpu" else "memory"
        procs = pm.list_processes(sort_by=which, limit=10)
        print(bold(f"Top 10 by {which.upper()}:"))
        for i, p in enumerate(procs, 1):
            print(f"  {i}. {p['name'][:40]:<40} {p['cpu_pct'] if which=='cpu' else p['mem_pct']:.1f}%")


def cmd_memory(args):
    mem = MemoryManager()
    if args.subcmd == "search":
        results = mem.recall(args.query, limit=args.limit)
        print(bold(f"Memory search: \"{args.query}\""))
        if not results.get("vector_results"):
            print("  No results.")
        for r in results.get("vector_results", []):
            score_pct = r.get("score", 0) * 100
            print(f"  [{score_pct:.0f}%] {r['content'][:100]}")
    elif args.subcmd == "add":
        entry_id = mem.add(args.content, importance=args.importance)
        print(green(f"Added memory entry: {entry_id}"))
    elif args.subcmd == "stats":
        stats = mem.get_stats()
        print(bold("Memory Stats:"))
        print(f"  Vector entries : {stats.get('vector_entries', 0)}")
        print(f"  Graph nodes    : {stats.get('graph_nodes', 0)}")


def cmd_services(args):
    sm = ServiceManager()
    if args.subcmd == "list":
        svcs = sm.list_services(state=args.state)
        print(bold(f"{'NAME':<45} {'STATE':<12}"))
        print("-" * 60)
        for s in svcs[:args.limit]:
            print(f"{s['name']:<45} {s.get('state','?'):<12}")
    elif args.subcmd == "start":
        r = sm.start_service(args.service)
        print(green("Started") if r["success"] else red(f"Failed: {r.get('error')}"))
    elif args.subcmd == "stop":
        r = sm.stop_service(args.service)
        print(green("Stopped") if r["success"] else red(f"Failed: {r.get('error')}"))
    elif args.subcmd == "restart":
        r = sm.restart_service(args.service)
        print(green("Restarted") if r["success"] else red(f"Failed: {r.get('error')}"))


def cmd_power(args):
    pc = PowerControl()
    if args.action == "shutdown":
        r = pc.shutdown(force=args.force, timeout=args.timeout)
        print(green("Shutdown initiated") if r["success"] else red(f"Failed: {r.get('error')}"))
    elif args.action == "restart":
        r = pc.restart(force=args.force, timeout=args.timeout)
        print(green("Restart initiated") if r["success"] else red(f"Failed: {r.get('error')}"))
    elif args.action == "sleep":
        r = pc.sleep()
        print(green("Sleep initiated") if r["success"] else red(f"Failed: {r.get('error')}"))
    elif args.action == "lock":
        r = pc.lock()
        print(green("Screen locked") if r["success"] else red(f"Failed: {r.get('error')}"))


def cmd_capture(args):
    sc = ScreenCapture()
    if args.action == "full":
        img = sc.capture_fullscreen()
        path = args.path or "screenshot.png"
        img.save(path)
        print(green(f"Saved: {path}"))
    elif args.action == "window":
        img = sc.capture_window(args.window)
        if img:
            path = args.path or f"window_{args.window.replace(' ','_')}.png"
            img.save(path)
            print(green(f"Saved: {path}"))
        else:
            print(red(f"Window not found: {args.window}"))


def cmd_vision(args):
    sc = ScreenCapture()
    sa = ScreenAnalyzer()
    img = sc.capture_fullscreen()
    if args.action == "describe":
        desc = sa.describe(img, prompt=args.prompt)
        print(bold("Screen description:"))
        print(f"  {desc}")
    elif args.action == "find":
        result = sa.find_element(img, args.description)
        if result:
            print(green(f"Found at: x={result['x']}, y={result['y']}"))
        else:
            print(red("Element not found"))


def cmd_agent(args):
    from src.agent import get_agent
    agent = get_agent()
    session = args.session or "cli-default"
    print(cyan(f"[Nexus Agent | session: {session}]"))
    if args.message:
        resp = agent.send_message(session, args.message, stream=False)
        print(bold("Nexus: ") + resp)
    else:
        print("Starting interactive session... (Ctrl+C to exit)")
        while True:
            try:
                msg = input("\nYou: ")
                if msg.strip().lower() in ("exit", "quit"):
                    break
                resp = agent.send_message(session, msg, stream=False)
                print(bold("Nexus: ") + resp)
            except (KeyboardInterrupt, EOFError):
                break


def main():
    parser = argparse.ArgumentParser(prog="nexus", description="Nexus Agent CLI")
    sub = parser.add_subparsers(dest="cmd")

    # system
    p_sys = sub.add_parser("system", help="System information")

    # processes
    p_proc = sub.add_parser("processes", help="Process management")
    p_proc.add_argument("subcmd", choices=["list","kill","search","top"])
    p_proc.add_argument("--sort", default="cpu")
    p_proc.add_argument("--limit", type=int, default=30)
    p_proc.add_argument("--pid", type=int)
    p_proc.add_argument("--name")
    p_proc.add_argument("--type", default="cpu")
    p_proc.add_argument("--force", action="store_true")

    # memory
    p_mem = sub.add_parser("memory", help="Memory management")
    p_mem.add_argument("subcmd", choices=["search","add","stats"])
    p_mem.add_argument("--query")
    p_mem.add_argument("--content")
    p_mem.add_argument("--limit", type=int, default=5)
    p_mem.add_argument("--importance", type=float, default=1.0)

    # services
    p_svc = sub.add_parser("services", help="Service/daemon management")
    p_svc.add_argument("subcmd", choices=["list","start","stop","restart"])
    p_svc.add_argument("--service")
    p_svc.add_argument("--state", default="all")
    p_svc.add_argument("--limit", type=int, default=50)

    # power
    p_pow = sub.add_parser("power", help="Power management")
    p_pow.add_argument("action", choices=["shutdown","restart","sleep","lock"])
    p_pow.add_argument("--force", action="store_true")
    p_pow.add_argument("--timeout", type=int, default=30)

    # capture
    p_cap = sub.add_parser("capture", help="Screenshot capture")
    p_cap.add_argument("action", choices=["full","window"])
    p_cap.add_argument("--window")
    p_cap.add_argument("--path")

    # vision
    p_vis = sub.add_parser("vision", help="Vision analysis")
    p_vis.add_argument("action", choices=["describe","find"])
    p_vis.add_argument("--prompt")
    p_vis.add_argument("--description")

    # agent
    p_agt = sub.add_parser("agent", help="Chat with Nexus Agent")
    p_agt.add_argument("--message")
    p_agt.add_argument("--session")

    args = parser.parse_args()

    if args.cmd == "system":
        cmd_system(args)
    elif args.cmd == "processes":
        cmd_processes(args)
    elif args.cmd == "memory":
        cmd_memory(args)
    elif args.cmd == "services":
        cmd_services(args)
    elif args.cmd == "power":
        cmd_power(args)
    elif args.cmd == "capture":
        cmd_capture(args)
    elif args.cmd == "vision":
        cmd_vision(args)
    elif args.cmd == "agent":
        cmd_agent(args)
    else:
        print(bold("Nexus Agent CLI"))
        print("Usage: nexus <command> [options]")
        print()
        print("Commands:")
        print("  system      System information")
        print("  processes   Process management")
        print("  memory      Memory (vector + graph)")
        print("  services    Service/daemon management")
        print("  power       Shutdown/restart/sleep/lock")
        print("  capture     Screenshot capture")
        print("  vision      Vision analysis")
        print("  agent       Chat with Nexus Agent")
        print()
        print("Run 'nexus <command> --help' for more options.")


if __name__ == "__main__":
    main()