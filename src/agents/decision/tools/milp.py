"""H6: S1 MILP (Optimizasyon_Modeli). PuLP (CBC) → scipy.milp yedeği → None (MILP_YAPILAMADI)."""
from __future__ import annotations

from typing import Optional

EPS = 1e-4  # eşit maliyetli alternatif optimumlarda tüm transfer edilebilir stoğu seç (tampon)


def solve_milp(p: dict) -> Optional[dict]:
    """p: S0, d, t_b, t_c (None → COD yok), B, pen, R, T_max, A_max, MOQ, c_A, F_A, F_T, F_C, a_T, a_A, M."""
    for solver in (_pulp, _scipy, _enumerate):
        try:
            sol = solver(p)
        except Exception:  # kütüphane/çözücü yok → bir sonraki yedek
            continue
        if sol is not None:
            return sol
    return None


def _enumerate(p):
    """Saf Python yedeği: 4 ikili değişkenin 16 bileşimi × kapalı form LP (model küçük ve yapısı sabit)."""
    import itertools
    best = None
    t_c = p["t_c"] if p["t_c"] is not None else p["t_b"]
    for zT, zA, yC, w in itertools.product((0, 1), repeat=4):
        if yC and p["t_c"] is None:
            continue
        if p["a_T"] * zT > p["S0"] / p["d"] + 1e-9 or p["a_A"] * zA > p["S0"] / p["d"] + 1e-9:
            continue
        xT = p["T_max"] * zT
        gerek = (p["t_b"] - (p["t_b"] - t_c) * yC + p["B"]) * p["d"] - p["S0"] - xT   # kg cinsinden kalan açık
        xA, u = 0.0, 0.0
        if zA:
            hedef = max(0.0, gerek) if p["c_A"] <= p["pen"] / p["d"] or not w else 0.0
            xA = min(p["A_max"], max(p["MOQ"], hedef))
            if p["MOQ"] > p["A_max"]:
                continue
        kalan = gerek - xA
        if kalan > 1e-9:
            if not w:
                continue
            u = kalan / p["d"]
            if u > p["M"]:
                continue
        amac = p["F_T"] * zT + p["c_A"] * xA + p["F_A"] * zA + p["F_C"] * yC + p["pen"] * u + p["R"] * w
        if best is None or amac - EPS * xT < best["_k"] - 1e-9:
            best = {"durum": "OPTIMAL", "x_T": xT, "x_A": xA, "y_C": yC, "amac_try": amac, "cozucu": "enumerasyon",
                    "_k": amac - EPS * xT}
    if best:
        best.pop("_k")
        return best
    return {"durum": "COZUMSUZ"}


def _pulp(p):
    import pulp
    m = pulp.LpProblem("nexus_s1", pulp.LpMinimize)

    def var(name, lo=None, hi=None, cat="Continuous"):
        if hasattr(m, "add_variable"):  # PuLP ≥ 4
            return m.add_variable(name, lowBound=lo, upBound=hi, cat=cat)
        return pulp.LpVariable(name, lowBound=lo, upBound=hi, cat=cat)

    xT = var("x_T", 0, p["T_max"]); zT = var("z_T", cat="Binary")
    xA = var("x_A", 0, p["A_max"]); zA = var("z_A", cat="Binary")
    yC = var("y_C", cat="Binary"); u = var("u", 0); w = var("w", cat="Binary")
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
    if not pulp.listSolvers(onlyAvailable=True):
        return None
    st = m.solve()
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
