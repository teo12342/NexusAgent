"""
Nexus Agent — src/app.py
Standalone desktop GUI app (Tkinter)
Full dashboard in a window — no browser needed
Works on Windows, Linux, macOS
"""

import sys
import os
import threading
import time
import webbrowser

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.config import load_config, get_config
from src.device import SystemInfo, ProcessManager, RegistryManager, ServiceManager, PowerControl
from src.memory import MemoryManager
from src.agent import get_agent
from src.tools import TOOL_REGISTRY


try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False


class NexusApp:
    """Standalone Nexus Agent desktop app."""

    def __init__(self):
        self.root = tk.Tk() if TK_AVAILABLE else None
        self.system = SystemInfo()
        self.memory = MemoryManager()
        self.agent = get_agent()
        self.proc_mgr = ProcessManager()
        self.svc_mgr = ServiceManager()
        self.power = PowerControl()
        self.refresh_interval = 3000  # ms

        if self.root:
            self.root.title("Nexus Agent")
            self.root.geometry("1100x700")
            self.root.configure(bg="#08080c")
            self._setup_ui()

    def _setup_ui(self):
        # Top bar
        top = tk.Frame(self.root, bg="#111118", height=50)
        top.pack(fill="x")
        tk.Label(top, text="NEXUS AGENT", font=("JetBrains Mono", 14, "bold"),
                 fg="#ff4f40", bg="#111118").pack(side="left", padx=16, pady=10)
        tk.Label(top, text="Standalone App", font=("JetBrains Mono", 9),
                 fg="#6b6b80", bg="#111118").pack(side="left", padx=4, pady=10)

        # Notebook
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        # Tabs
        self._make_overview_tab(nb)
        self._make_processes_tab(nb)
        self._make_memory_tab(nb)
        self._make_agent_tab(nb)
        self._make_tools_tab(nb)

    def _make_overview_tab(self, nb):
        f = tk.Frame(nb, bg="#08080c")
        nb.add(f, text="  Overview  ")

        stats_frame = tk.Frame(f, bg="#08080c")
        stats_frame.pack(fill="x", padx=15, pady=(15, 5))

        self.stat_labels = {}
        cards = [("CPU", "cpu_pct"), ("RAM", "ram_pct"), ("Disk", "disk_pct"), ("Sessions", "sessions"), ("Memory", "mem_entries"), ("Tools", "tool_count")]
        for label_text, key in cards:
            card = tk.Frame(stats_frame, bg="#111118", width=130, height=80, relief="flat")
            card.pack(side="left", padx=5)
            card.pack_propagate(False)
            vl = tk.Label(card, text="—", font=("JetBrains Mono", 20, "bold"),
                         fg="#ff4f40", bg="#111118")
            vl.pack(pady=(15, 0))
            tk.Label(card, text=label_text, font=("JetBrains Mono", 7, "bold"),
                     fg="#6b6b80", bg="#111118").pack()
            self.stat_labels[key] = vl

        # Live info panel
        info = tk.Frame(f, bg="#111118")
        info.pack(fill="both", expand=True, padx=15, pady=(10, 15))

        self.info_text = scrolledtext.ScrolledText(info, bg="#111118", fg="#e8e8f0",
                                                   font=("JetBrains Mono", 9),
                                                   relief="flat", wrap="word",
                                                   state="disabled")
        self.info_text.pack(fill="both", expand=True)
        self.info_text.tag_configure("header", foreground="#ff4f40", font=("JetBrains Mono", 9, "bold"))

        self._refresh_overview()
        self.root.after(self.refresh_interval, self._refresh_overview)

    def _refresh_overview(self):
        try:
            stats = self.system.get_full_stats()
            agent_stats = self.agent.get_all_stats()

            self.stat_labels["cpu_pct"].config(text=f"{stats['cpu']['overall_percent']:.1f}%")
            self.stat_labels["ram_pct"].config(text=f"{stats['memory']['percent']:.1f}%")
            self.stat_labels["disk_pct"].config(text=f"{stats['disks'][0]['percent']:.0f}%" if stats['disks'] else "—")
            self.stat_labels["sessions"].config(text=str(agent_stats.get("active_sessions", 0)))
            self.stat_labels["mem_entries"].config(text=str(agent_stats.get("memory_stats", {}).get("vector_entries", 0)))
            self.stat_labels["tool_count"].config(text=str(len(TOOL_REGISTRY)))

            text = self.info_text
            text.configure(state="normal")
            text.delete("1.0", "end")

            lines = [
                ("SYSTEM OVERVIEW", True),
                (f"Hostname   : {stats['hostname']}", False),
                (f"OS         : {stats['platform']['os']} {stats['platform']['release']}", False),
                (f"Uptime     : {stats['uptime']['human']}", False),
                ("", False),
                ("CPU", True),
                (f"  Overall  : {stats['cpu']['overall_percent']:.1f}%", False),
                (f"  Cores    : {stats['cpu']['count']} logical", False),
                ("", False),
                ("MEMORY", True),
                (f"  Used     : {stats['memory']['used_gb']:.1f}GB / {stats['memory']['total_gb']:.1f}GB", False),
                (f"  Percent  : {stats['memory']['percent']:.1f}%", False),
                ("", False),
                ("NETWORK", True),
                (f"  Received : {stats['network']['bytes_recv_mb']} MB", False),
                (f"  Sent     : {stats['network']['bytes_sent_mb']} MB", False),
            ]
            for txt, is_hdr in lines:
                if is_hdr:
                    text.insert("end", txt + "\n", "header")
                else:
                    text.insert("end", txt + "\n")

            text.configure(state="disabled")
        except Exception as e:
            print(f"Overview refresh error: {e}")

        if self.root:
            self.root.after(self.refresh_interval, self._refresh_overview)

    def _make_processes_tab(self, nb):
        f = tk.Frame(nb, bg="#08080c")
        nb.add(f, text="  Processes  ")

        toolbar = tk.Frame(f, bg="#08080c")
        toolbar.pack(fill="x", padx=15, pady=10)
        tk.Button(toolbar, text="Refresh", command=self._refresh_processes,
                  bg="#ff4f40", fg="#fff", relief="flat", padx=12,
                  font=("JetBrains Mono", 9, "bold")).pack(side="left")

        cols = ("PID", "Name", "CPU %", "Mem %")
        self.proc_tree = ttk.Treeview(f, columns=cols, show="headings", style="Custom.Treeview")
        for c in cols:
            self.proc_tree.heading(c, text=c)
        self.proc_tree.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        self._refresh_processes()

    def _refresh_processes(self):
        try:
            for row in self.proc_tree.get_children():
                self.proc_tree.delete(row)
            procs = self.proc_mgr.list_processes(sort_by="cpu", limit=50)
            for p in procs[1:]:
                self.proc_tree.insert("", "end", values=(p["pid"], p["name"][:40], f"{p['cpu_pct']:.1f}", f"{p['mem_pct']:.1f}"))
        except Exception as e:
            print(f"Process refresh error: {e}")

    def _make_memory_tab(self, nb):
        f = tk.Frame(nb, bg="#08080c")
        nb.add(f, text="  Memory  ")

        search_frame = tk.Frame(f, bg="#08080c")
        search_frame.pack(fill="x", padx=15, pady=10)
        self.mem_entry = tk.Entry(search_frame, bg="#111118", fg="#e8e8f0",
                                  font=("JetBrains Mono", 10), insertbackground="#ff4f40")
        self.mem_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(search_frame, text="Search", command=self._do_memory_search,
                  bg="#ff4f40", fg="#fff", relief="flat", padx=12,
                  font=("JetBrains Mono", 9, "bold")).pack(side="left")

        self.mem_text = scrolledtext.ScrolledText(f, bg="#111118", fg="#e8e8f0",
                                                   font=("JetBrains Mono", 9),
                                                   relief="flat", state="disabled")
        self.mem_text.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # Stats
        stats = self.memory.get_stats()
        self.mem_text.configure(state="normal")
        self.mem_text.insert("end", f"Vector entries: {stats.get('vector_entries', 0)}\n")
        self.mem_text.insert("end", f"Graph nodes: {stats.get('graph_nodes', 0)}\n")
        self.mem_text.configure(state="disabled")

    def _do_memory_search(self):
        query = self.mem_entry.get()
        if not query:
            return
        results = self.memory.recall(query, limit=5)
        self.mem_text.configure(state="normal")
        self.mem_text.delete("1.0", "end")
        self.mem_text.insert("end", f'Search: "{query}"\n\n')
        for r in results.get("vector_results", []):
            self.mem_text.insert("end", f"[{r.get('score', 0)*100:.0f}%] {r['content'][:200]}\n\n")
        self.mem_text.configure(state="disabled")

    def _make_agent_tab(self, nb):
        f = tk.Frame(nb, bg="#08080c")
        nb.add(f, text="  Agent  ")

        self.agent_text = scrolledtext.ScrolledText(f, bg="#111118", fg="#e8e8f0",
                                                     font=("JetBrains Mono", 9),
                                                     relief="flat", state="disabled")
        self.agent_text.pack(fill="both", expand=True, padx=15, pady=(15, 5))
        self.agent_text.configure(state="normal")
        self.agent_text.insert("end", "Nexus Agent is online.\n\n", "header")
        self.agent_text.tag_configure("header", foreground="#ff4f40", font=("JetBrains Mono", 9, "bold"))
        self.agent_text.configure(state="disabled")

        input_frame = tk.Frame(f, bg="#08080c")
        input_frame.pack(fill="x", padx=15, pady=(5, 15))
        self.agent_entry = tk.Entry(input_frame, bg="#111118", fg="#e8e8f0",
                                    font=("JetBrains Mono", 10), insertbackground="#ff4f40")
        self.agent_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.agent_entry.bind("<Return>", lambda e: self._send_agent_message())
        tk.Button(input_frame, text="Send", command=self._send_agent_message,
                  bg="#ff4f40", fg="#fff", relief="flat", padx=12,
                  font=("JetBrains Mono", 9, "bold")).pack(side="left")

    def _send_agent_message(self):
        msg = self.agent_entry.get()
        if not msg:
            return
        self.agent_entry.delete(0, "end")
        self.agent_text.configure(state="normal")
        self.agent_text.insert("end", f"You: {msg}\n", "user")
        self.agent_text.tag_configure("user", foreground="#e8e8f0")
        self.agent_text.insert("end", "Nexus: thinking...\n")
        self.agent_text.see("end")
        self.agent_text.configure(state="disabled")

        try:
            resp = self.agent.send_message("app-session", msg, stream=False)
            self.agent_text.configure(state="normal")
            # Replace "thinking..." line
            self.agent_text.insert("end", f"Nexus: {resp}\n\n")
            self.agent_text.see("end")
            self.agent_text.configure(state="disabled")
        except Exception as e:
            self.agent_text.configure(state="normal")
            self.agent_text.insert("end", f"Nexus: [Error: {e}]\n\n")
            self.agent_text.configure(state="disabled")

    def _make_tools_tab(self, nb):
        f = tk.Frame(nb, bg="#08080c")
        nb.add(f, text="  Tools  ")

        tk.Label(f, text="Tool Executor", font=("JetBrains Mono", 11, "bold"),
                 fg="#ff4f40", bg="#08080c").pack(anchor="w", padx=15, pady=(15, 5))

        tool_frame = tk.Frame(f, bg="#08080c")
        tool_frame.pack(fill="x", padx=15, pady=5)
        self.tool_var = tk.StringVar()
        tool_menu = ttk.Combobox(tool_frame, textvariable=self.tool_var,
                                  values=list(TOOL_REGISTRY.keys()), state="readonly", width=40)
        tool_menu.pack(side="left", padx=(0, 5))
        tk.Button(tool_frame, text="Execute", command=self._execute_tool,
                  bg="#ff4f40", fg="#fff", relief="flat", padx=12,
                  font=("JetBrains Mono", 9, "bold")).pack(side="left")

        self.tool_output = scrolledtext.ScrolledText(f, bg="#0d0d14", fg="#a0a0b0",
                                                     font=("JetBrains Mono", 8),
                                                     relief="flat", state="disabled")
        self.tool_output.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        self.tool_output.configure(state="normal")
        self.tool_output.insert("end", f"Available tools: {len(TOOL_REGISTRY)}\n")
        self.tool_output.insert("end", "Select a tool and click Execute to run it.\n")
        self.tool_output.configure(state="disabled")

    def _execute_tool(self):
        tool_name = self.tool_var.get()
        if not tool_name or tool_name not in TOOL_REGISTRY:
            return
        try:
            result = self.agent.execute_tool(tool_name, {})
            output = json.dumps(result, indent=2)
        except Exception as e:
            output = str(e)
        self.tool_output.configure(state="normal")
        self.tool_output.delete("1.0", "end")
        self.tool_output.insert("end", f">>> {tool_name}\n{output}\n")
        self.tool_output.configure(state="disabled")

    def run(self):
        if not self.root:
            print("Tkinter not available. Run with --gui or use the CLI.")
            return
        self.root.mainloop()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--gui", action="store_true", help="Launch GUI app")
    ap.add_argument("--port", type=int, help="Start web dashboard on port")
    args = ap.parse_args()

    if args.gui and TK_AVAILABLE:
        app = NexusApp()
        app.run()
    elif args.port:
        from src.dashboard.app import run_dashboard
        run_dashboard(port=args.port)
    else:
        print("Nexus Agent")
        print("  --gui       Launch desktop GUI app")
        print("  --port N    Start web dashboard on port N")
        print("  (or use: python -m src.cli)")
        if TK_AVAILABLE:
            print("\nLaunching GUI...")
            app = NexusApp()
            app.run()