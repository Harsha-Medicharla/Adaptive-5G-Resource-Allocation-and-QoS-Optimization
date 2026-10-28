from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

SLICES = ("eMBB", "URLLC", "mMTC")

def normalize_phase_values(demand_map: Dict[str, float], active_mmtc: int) -> Dict[str, float]:
    out = {"eMBB": float(demand_map["eMBB"]), "URLLC": float(demand_map["URLLC"]), "mMTC": float(active_mmtc)}
    return out

PHASES = [
    {
        "name": "P1 Normal",
        "demand": {"eMBB": 6.0, "URLLC": 2.0},
        "mmtc_active": 30,
    },
    {
        "name": "P2 eMBB burst",
        "demand": {"eMBB": 14.0, "URLLC": 2.0},
        "mmtc_active": 30,
    },
    {
        "name": "P3 eMBB + URLLC high",
        "demand": {"eMBB": 14.0, "URLLC": 5.0},
        "mmtc_active": 30,
    },
    {
        "name": "P4 URLLC very high",
        "demand": {"eMBB": 6.0, "URLLC": 9.0},
        "mmtc_active": 15,
    },
    {
        "name": "P5 mMTC surge",
        "demand": {"eMBB": 9.0, "URLLC": 2.0},
        "mmtc_active": 60,
    },
]

TOTAL_UNITS = 100
UNIT_MBPS = 20.0 / TOTAL_UNITS
STATIC_ALLOCATION = (50, 30, 20)


def candidate_allocations() -> List[Tuple[int, int, int]]:
    out = []
    for a in range(10, 91, 10):
        for b in range(10, 91, 10):
            c = TOTAL_UNITS - a - b
            if c < 10 or c > 80:
                continue
            if a + b + c == TOTAL_UNITS:
                out.append((a, b, c))
    return out


ALL_ACTIONS = candidate_allocations()


def phase_demand(phase: Dict[str, object]) -> Dict[str, float]:
    demand = dict(phase["demand"])
    demand["mMTC"] = phase["mmtc_active"] * 0.075
    return demand


def carried_capacity(demand_mbps: float, capacity_mbps: float) -> float:
    return min(demand_mbps, capacity_mbps)


def packet_loss_pct(demand_mbps: float, carried_mbps: float) -> float:
    if demand_mbps <= 0:
        return 0.0
    return max(0.0, (demand_mbps - carried_mbps) / demand_mbps * 100.0)


def delay_ms_for_slice(sl: str, demand_mbps: float, capacity_mbps: float) -> float:
    if demand_mbps <= 0 or capacity_mbps <= 0:
        return 0.0
    util = demand_mbps / capacity_mbps
    if sl == "URLLC":
        if util <= 1.0:
            return 1.8 + 6.0 * util
        return 18.0 + (util - 1.0) * 55.0
    if sl == "eMBB":
        if util <= 1.0:
            return 2.0 + 25.0 * util
        return 55.0 + (util - 1.0) * 80.0
    if util <= 1.0:
        return 8.0 + 10.0 * util
    return 20.0 + (util - 1.0) * 45.0


def evaluate_allocation(phase: Dict[str, object], allocation: Tuple[int, int, int]) -> Dict[str, float]:
    demand = phase_demand(phase)
    cap = {s: allocation[i] * UNIT_MBPS for i, s in enumerate(SLICES)}
    result = {}
    result["alloc"] = allocation
    result["capacity"] = cap
    result["demand"] = demand
    result["carried"] = {}
    result["loss_pct"] = {}
    result["delay_ms"] = {}
    result["util_pct"] = {}

    score = 0.0
    for idx, sl in enumerate(SLICES):
        d = demand[sl]
        c = cap[sl]
        carried = carried_capacity(d, c)
        loss = packet_loss_pct(d, carried)
        delay = delay_ms_for_slice(sl, d, c)
        util = 100.0 * carried / c if c > 0 else 0.0
        result["carried"][sl] = carried
        result["loss_pct"][sl] = loss
        result["delay_ms"][sl] = delay
        result["util_pct"][sl] = util

        if sl == "eMBB":
            score += carried * 1.0 - loss * 0.4
        elif sl == "URLLC":
            score += carried * 1.2 - loss * 1.0 - max(0.0, delay - 10.0) * 0.3
        else:
            score += carried * 0.7 - loss * 0.25

    result["score"] = score
    return result


def greedy_allocation(phase: Dict[str, object]) -> Tuple[int, int, int]:
    demand = phase_demand(phase)
    best = None
    best_score = -1e18
    for alloc in ALL_ACTIONS:
        ev = evaluate_allocation(phase, alloc)
        # prioritize URLLC when it is stressed; otherwise maintain throughput
        if demand["URLLC"] > 5.0:
            penalty = max(0.0, ev["delay_ms"]["URLLC"] - 10.0) * 1.5
            score = ev["score"] - penalty
        else:
            score = ev["score"]
        if score > best_score:
            best_score = score
            best = alloc
    return best or STATIC_ALLOCATION


def random_allocation() -> Tuple[int, int, int]:
    choice = ALL_ACTIONS[np.random.randint(len(ALL_ACTIONS))]
    return choice


def static_allocation() -> Tuple[int, int, int]:
    return STATIC_ALLOCATION


def q_table_best_action(state: Tuple[float, float, float, float, float, float], qtable: Dict[Tuple[float, float, float, float, float, float], Dict[Tuple[int, int, int], float]]) -> Tuple[int, int, int]:
    if state not in qtable:
        return STATIC_ALLOCATION
    ranked = sorted(qtable[state].items(), key=lambda kv: kv[1], reverse=True)
    return ranked[0][0] if ranked else STATIC_ALLOCATION


def train_q_table(episodes: int = 1000) -> Dict[Tuple[float, float, float, float, float, float], Dict[Tuple[int, int, int], float]]:
    qtable: Dict[Tuple[float, float, float, float, float, float], Dict[Tuple[int, int, int], float]] = {}
    rng = np.random.default_rng(42)
    for _ in range(episodes):
        phase = PHASES[rng.integers(len(PHASES))]
        demand = phase_demand(phase)
        state = (
            demand["eMBB"] / 20.0,
            demand["URLLC"] / 20.0,
            demand["mMTC"] / 20.0,
            0.5,
            0.5,
            0.5,
        )
        if state not in qtable:
            qtable[state] = {}
        for action in ALL_ACTIONS:
            ev = evaluate_allocation(phase, action)
            reward = ev["score"]
            qtable[state].setdefault(action, 0.0)
            qtable[state][action] = 0.9 * qtable[state][action] + 0.1 * reward
    return qtable


def summarize_policy(policy_name: str):
    rows = []
    for phase in PHASES:
        if policy_name == "static":
            action = static_allocation()
        elif policy_name == "random":
            action = random_allocation()
        elif policy_name == "adaptive":
            action = greedy_allocation(phase)
        else:
            action = static_allocation()
        ev = evaluate_allocation(phase, action)
        rows.append(
            {
                "policy": policy_name,
                "phase": phase["name"],
                "alloc": action,
                "eMBB_loss_pct": ev["loss_pct"]["eMBB"],
                "URLLC_loss_pct": ev["loss_pct"]["URLLC"],
                "mMTC_loss_pct": ev["loss_pct"]["mMTC"],
                "eMBB_delay_ms": ev["delay_ms"]["eMBB"],
                "URLLC_delay_ms": ev["delay_ms"]["URLLC"],
                "mMTC_delay_ms": ev["delay_ms"]["mMTC"],
                "score": ev["score"],
            }
        )
    return rows


def make_policy_summary():
    all_rows = []
    for name in ["static", "random", "adaptive"]:
        all_rows.extend(summarize_policy(name))
    return all_rows
