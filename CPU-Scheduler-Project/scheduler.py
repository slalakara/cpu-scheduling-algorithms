import csv
import argparse
import os
import math
import heapq
import threading
from collections import deque, namedtuple
from datetime import datetime

CONTEXT_SWITCH_TIME = 0.001
THROUGHPUT_TIMES = [50, 100, 150, 200]

PRIORITY_MAP = {"high": 0, "normal": 1, "low": 2}
Proc = namedtuple("Proc", ["pid", "arrival", "burst", "priority"])

def parse_priority(value):
    if value is None or value == "":
        return 0
    v = str(value).strip()
    if v.isdigit() or v.lstrip('-').isdigit():
        return int(v)
    low = v.lower()
    if low in PRIORITY_MAP:
        return PRIORITY_MAP[low]
    try:
        return int(float(v))
    except:
        return 1

def read_csv(path):
    procs = []
    with open(path, newline='') as f:
        rdr = csv.reader(f)
        rows = [r for r in rdr if any(cell.strip() for cell in r)]

    header = [c.strip().lower() for c in rows[0]]
    has_header = any(h in header for h in (
        "process_id","pid","arrival_time","arrival",
        "cpu_burst_time","burst","priority"
    ))

    start = 1 if has_header else 0
    for r in rows[start:]:
        pid = r[0].strip()
        arrival = float(r[1])
        burst = float(r[2])
        pr = parse_priority(r[3]) if len(r) > 3 else 0
        procs.append(Proc(pid, arrival, burst, pr))

    return sorted(procs, key=lambda p: (p.arrival, p.pid))

def ensure_outdir(path):
    os.makedirs(path, exist_ok=True)

def append_segment(timeline, s, e, pid):
    if e > s:
        timeline.append((s, e, pid))

def write_metrics(path, metrics):
    with open(path, "w") as f:
        for k, v in metrics.items():
            f.write(f"{k}: {v}\n")

def compute_metrics(procs, completion, timeline, ctx, total):
    waits, tats = [], []
    for p in procs:
        tat = completion[p.pid] - p.arrival
        wt = tat - p.burst
        waits.append(wt)
        tats.append(tat)

    metrics = {
        "context_switches": ctx,
        "total_time": round(total, 6),
        "avg_waiting": sum(waits)/len(waits),
        "max_waiting": max(waits),
        "avg_turnaround": sum(tats)/len(tats),
        "max_turnaround": max(tats)
    }

    for T in THROUGHPUT_TIMES:
        metrics[f"throughput_T_{T}"] = sum(
            1 for c in completion.values() if c <= T
        )

    busy = sum(e - s for s, e, p in timeline if p != "IDLE")
    metrics["cpu_efficiency_percent"] = (busy / total) * 100 if total > 0 else 0

    return metrics

def fcfs(procs):
    timeline, completion = [], {}
    t, ctx = 0.0, 0
    for p in procs:
        if t < p.arrival:
            append_segment(timeline, t, p.arrival, "IDLE")
            t = p.arrival
        ctx += 1
        t += CONTEXT_SWITCH_TIME
        append_segment(timeline, t, t + p.burst, p.pid)
        t += p.burst
        completion[p.pid] = t
    return timeline, completion, ctx, t

def sjf_nonpreemptive(procs):
    timeline, completion = [], {}
    t, ctx = 0.0, 0
    ready, i = [], 0
    n = len(procs)

    while len(completion) < n:
        while i < n and procs[i].arrival <= t:
            heapq.heappush(ready, (procs[i].burst, procs[i]))
            i += 1

        if not ready:
            t += 1
            continue

        _, p = heapq.heappop(ready)
        ctx += 1
        t += CONTEXT_SWITCH_TIME
        append_segment(timeline, t, t + p.burst, p.pid)
        t += p.burst
        completion[p.pid] = t

    return timeline, completion, ctx, t

def sjf_preemptive(procs):
    timeline, completion = [], {}
    t, ctx = 0.0, 0
    ready, i = [], 0
    rem = {p.pid: p.burst for p in procs}
    current = None
    start = t

    while len(completion) < len(procs):
        while i < len(procs) and procs[i].arrival <= t:
            heapq.heappush(ready, (rem[procs[i].pid], procs[i]))
            i += 1

        if not ready:
            t += 1
            continue

        _, p = heapq.heappop(ready)
        if current != p:
            ctx += 1
            t += CONTEXT_SWITCH_TIME
            start = t
            current = p

        t += 1
        rem[p.pid] -= 1
        if rem[p.pid] == 0:
            append_segment(timeline, start, t, p.pid)
            completion[p.pid] = t
            current = None
        else:
            heapq.heappush(ready, (rem[p.pid], p))

    return timeline, completion, ctx, t

def round_robin(procs, quantum=4.0):
    timeline, completion = [], {}
    t, ctx = 0.0, 0
    q = deque()
    rem = {p.pid: p.burst for p in procs}
    i = 0

    while len(completion) < len(procs):
        while i < len(procs) and procs[i].arrival <= t:
            q.append(procs[i])
            i += 1

        if not q:
            t += 1
            continue

        p = q.popleft()
        ctx += 1
        t += CONTEXT_SWITCH_TIME
        run = min(quantum, rem[p.pid])
        append_segment(timeline, t, t + run, p.pid)
        t += run
        rem[p.pid] -= run

        if rem[p.pid] == 0:
            completion[p.pid] = t
        else:
            q.append(p)

    return timeline, completion, ctx, t

def priority_nonpreemptive(procs):
    timeline, completion = [], {}
    t, ctx = 0.0, 0
    ready, i = [], 0

    while len(completion) < len(procs):
        while i < len(procs) and procs[i].arrival <= t:
            heapq.heappush(ready, (procs[i].priority, procs[i]))
            i += 1

        if not ready:
            t += 1
            continue

        _, p = heapq.heappop(ready)
        ctx += 1
        t += CONTEXT_SWITCH_TIME
        append_segment(timeline, t, t + p.burst, p.pid)
        t += p.burst
        completion[p.pid] = t

    return timeline, completion, ctx, t

def priority_preemptive(procs):
    timeline, completion = [], {}
    t, ctx = 0.0, 0
    ready, i = [], 0
    rem = {p.pid: p.burst for p in procs}
    current = None
    start = t

    while len(completion) < len(procs):
        while i < len(procs) and procs[i].arrival <= t:
            heapq.heappush(ready, (procs[i].priority, procs[i]))
            i += 1

        if not ready:
            t += 1
            continue

        _, p = heapq.heappop(ready)
        if current != p:
            ctx += 1
            t += CONTEXT_SWITCH_TIME
            start = t
            current = p

        t += 1
        rem[p.pid] -= 1
        if rem[p.pid] == 0:
            append_segment(timeline, start, t, p.pid)
            completion[p.pid] = t
            current = None
        else:
            heapq.heappush(ready, (p.priority, p))

    return timeline, completion, ctx, t

def run_all(csv_file, outdir="out", quantum=4.0):
    procs = read_csv(csv_file)
    case = os.path.splitext(os.path.basename(csv_file))[0]
    ensure_outdir(outdir)

    algos = {
        "FCFS": fcfs,
        "SJF_NONPRE": sjf_nonpreemptive,
        "SJF_PRE": sjf_preemptive,
        "RR": lambda p: round_robin(p, quantum),
        "PRIO_NONPRE": priority_nonpreemptive,
        "PRIO_PRE": priority_preemptive
    }

    for name, func in algos.items():
        timeline, comp, ctx, total = func(procs)
        metrics = compute_metrics(procs, comp, timeline, ctx, total)
        write_metrics(f"{outdir}/{case}_{name}_metrics.txt", metrics)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--out", default="out")
    parser.add_argument("--quantum", type=float, default=4.0)
    args = parser.parse_args()
    run_all(args.csv, args.out, args.quantum)

if __name__ == "__main__":
    main()
