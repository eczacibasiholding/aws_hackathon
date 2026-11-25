"""H6: S1 MILP (Optimizasyon_Modeli). PuLP (CBC) → scipy.milp yedeği → None (MILP_YAPILAMADI)."""
from __future__ import annotations

from typing import Optional

EPS = 1e-4  # eşit maliyetli alternatif optimumlarda tüm transfer edilebilir stoğu seç (tampon)


def solve_milp(p: dict) -> Optional[dict]:
    """p: S0, d, t_b, t_c (None → COD yok), B, pen, R, T_max, A_max, MOQ, c_A, F_A, F_T, F_C, a_T, a_A, M."""
    try:
        return _pulp(p)
    except ImportError:
        pass
    try:
        return _scipy(p)
    except ImportError:
        return None


def _pulp(p):
    import pulp
    m = pulp.LpProblem("nexus_s1", pulp.LpMinimize)
    xT = pulp.LpVariable("x_T", 0, p["T_max"]); zT = pulp.LpVariable("z_T", cat="Binary")
    xA = pulp.LpVariable("x_A", 0, p["A_max"]); zA = pulp.LpVariable("z_A", cat="Binary")
    yC = pulp.LpVariable("y_C", cat="Binary"); u = pulp.LpVariable("u", 0); w = pulp.LpVariable("w", cat="Binary")
    obj = p["F_T"] * zT + p["c_A"] * xA + p["F_A"] * zA + p["F_C"] * yC + p["pen"] * u + p["R"] * w
    m += obj - EPS * xT
    t_c = p["t_c"] if p["t_c"] is not None else p["t_b"]
    if p["t_c"] is None:
        m += yC == 0
    m += (p["S0"] + xT + xA) / p["d"] + u >= p["t_b"] - (p["t_b"] - t_c) * yC + p["B"]
    m += xT <= p["T_max"] * zT
    m += xA <= p["A_max"] * zA
    m += xA >= p["MOQ"] * zA
    m += u <= p["M"] * w
    m += p["a_T"] * zT <= p["S0"] / p["d"]
    m += p["a_A"] * zA <= p["S0"] / p["d"]
    st = m.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=30))
    durum = pulp.LpStatus[st]
    if durum != "Optimal":
        return {"durum": "COZUMSUZ" if durum == "Infeasible" else "ZAMAN_ASIMI"}
    return {"durum": "OPTIMAL", "x_T": xT.value(), "x_A": xA.value(), "y_C": int(round(yC.value())),
            "amac_try": pulp.value(obj), "cozucu": "PuLP/CBC"}


def _scipy(p):
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    # [xT, zT, xA, zA, yC, u, w]
    t_c = p["t_c"] if p["t_c"] is not None else p["t_b"]
    c = np.array([-EPS, p["F_T"], p["c_A"], p["F_A"], p["F_C"], p["pen"], p["R"]])
    A = [[1 / p["d"], 0, 1 / p["d"], 0, p["t_b"] - t_c, 1, 0],
         [1, -p["T_max"], 0, 0, 0, 0, 0], [0, 0, 1, -p["A_max"], 0, 0, 0], [0, 0, 1, -p["MOQ"], 0, 0, 0],
         [0, 0, 0, 0, 0, 1, -p["M"]], [0, p["a_T"], 0, 0, 0, 0, 0], [0, 0, 0, p["a_A"], 0, 0, 0]]
    lo = [p["t_b"] + p["B"] - p["S0"] / p["d"], -np.inf, -np.inf, 0, -np.inf, -np.inf, -np.inf]
    hi = [np.inf, 0, 0, np.inf, 0, p["S0"] / p["d"], p["S0"] / p["d"]]
    ub_y = 1 if p["t_c"] is not None else 0
    r = milp(c, constraints=LinearConstraint(np.array(A), lo, hi), integrality=[0, 1, 0, 1, 1, 0, 1],
             bounds=Bounds([0, 0, 0, 0, 0, 0, 0], [p["T_max"], 1, p["A_max"], 1, ub_y, np.inf, 1]))
    if not r.success:
        return {"durum": "COZUMSUZ"}
    x = r.x
    return {"durum": "OPTIMAL", "x_T": x[0], "x_A": x[2], "y_C": int(round(x[4])),
            "amac_try": float(r.fun + EPS * x[0]), "cozucu": "scipy.milp"}
