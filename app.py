# -*- coding: utf-8 -*-
import math
import json
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="HPP Load Planner — Matemàtica + 3D", layout="wide")

# ==========================================================
# CONFIG CONTENIDORS (mm) — FIXOS
# ==========================================================
L1_MM = 880.0
L2_MM = 1190.0
NAME_L1 = "Contenidor petit"
NAME_L2 = "Contenidor gran"

# ==========================================================
# COSTOS FIXOS (confirmats) — JA INCLOUEN MÀ D’OBRA
# ==========================================================
COST_420 = 43.90    # €/cicle (inclou mà d'obra)
COST_525 = 50.42    # €/cicle (inclou mà d'obra)

# ==========================================================
# LONGITUD ÚTIL VASIJA — FIXA (sense input)
# ==========================================================
LEN_420_MM = 3700.0
LEN_525_MM = 4630.0

# ==========================================================
# 3D DEFAULTS (sense sliders)
# ==========================================================
CYL_SEGMENTS = 18
CAPS = True
SHOW_WIREFRAME = True
WIRE_NSEG = 34
WIRE_WIDTH = 4
SHRINK_FACTOR = 0.985

# ==========================================================
#              MATEMÀTICA CILÍNDRICA
# ==========================================================
def genera_hexagonal_optimitzat(R_tanc, r_amp):
    millor_configuracio = []
    max_ampolles = 0
    pas_y = r_amp * math.sqrt(3)
    pas_x = 2 * r_amp
    angles = [math.radians(a) for a in range(0, 30, 5)]
    offsets_x = [i * (pas_x / 4) for i in range(4)]
    offsets_y = [i * (pas_y / 4) for i in range(4)]
    limit_r2 = (R_tanc - r_amp) ** 2

    for angle in angles:
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        for ox in offsets_x:
            for oy in offsets_y:
                centres = []
                rang_max = int(R_tanc / r_amp) + 2
                for fila in range(-rang_max, rang_max):
                    y_base = fila * pas_y + oy
                    offset_fila = r_amp if fila % 2 != 0 else 0
                    for col in range(-rang_max, rang_max):
                        x_base = col * pas_x + offset_fila + ox
                        x_rot = x_base * cos_a - y_base * sin_a
                        y_rot = x_base * sin_a + y_base * cos_a
                        if x_rot * x_rot + y_rot * y_rot <= limit_r2:
                            centres.append((x_rot, y_rot))
                if len(centres) > max_ampolles:
                    max_ampolles = len(centres)
                    millor_configuracio = centres
    return millor_configuracio


def genera_horizontals(R_tanc, h_amp, d_amp):
    centres_horitzontals = []
    r_amp = d_amp / 2.0

    y_actual = -R_tanc + r_amp
    while y_actual + r_amp <= R_tanc:
        y_extrem = abs(y_actual) + r_amp
        if y_extrem >= R_tanc:
            y_actual += d_amp
            continue

        x_max = math.sqrt(R_tanc ** 2 - y_extrem ** 2)
        espai_disponible = 2 * x_max
        quantes = int(espai_disponible // h_amp)

        if quantes > 0:
            inici_x = -(quantes * h_amp) / 2.0 + (h_amp / 2.0)
            for i in range(quantes):
                x_pos = inici_x + i * h_amp
                centres_horitzontals.append((x_pos, y_actual))

        y_actual += d_amp
    return centres_horitzontals


# ==========================================================
#              MATEMÀTICA RECTANGULAR
# ==========================================================
def genera_rectangular_optimitzat(R_tanc, dim_x, dim_y):
    millor_configuracio = []
    millor_angle = 0
    max_envasos = 0

    angles = [math.radians(a) for a in range(0, 90, 1)]
    divs = 5.0
    offsets_x = [i * (dim_x / divs) for i in range(int(divs))]
    offsets_y = [i * (dim_y / divs) for i in range(int(divs))]

    R2 = R_tanc ** 2
    dx2 = dim_x / 2.0
    dy2 = dim_y / 2.0

    for angle in angles:
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        for ox in offsets_x:
            for oy in offsets_y:
                centres = []
                rang_x = int(R_tanc / dim_x) + 2
                rang_y = int(R_tanc / dim_y) + 2

                for col in range(-rang_x, rang_x):
                    for fila in range(-rang_y, rang_y):
                        x_base = col * dim_x + ox
                        y_base = fila * dim_y + oy

                        c1_x, c1_y = x_base + dx2, y_base + dy2
                        c2_x, c2_y = x_base - dx2, y_base + dy2
                        c3_x, c3_y = x_base + dx2, y_base - dy2
                        c4_x, c4_y = x_base - dx2, y_base - dy2

                        if (c1_x ** 2 + c1_y ** 2 <= R2 and
                            c2_x ** 2 + c2_y ** 2 <= R2 and
                            c3_x ** 2 + c3_y ** 2 <= R2 and
                            c4_x ** 2 + c4_y ** 2 <= R2):

                            x_rot = x_base * cos_a - y_base * sin_a
                            y_rot = x_base * sin_a + y_base * cos_a
                            centres.append((x_rot, y_rot))

                if len(centres) > max_envasos:
                    max_envasos = len(centres)
                    millor_configuracio = centres
                    millor_angle = angle

    return millor_configuracio, millor_angle


# ==========================================================
#        STATS (capacitat i % volum)
# ==========================================================
def stats_cilindric(d_tanc, l_tanc, d_amp, h_amp):
    R_tanc = d_tanc / 2.0
    r_amp = d_amp / 2.0

    centres_v = genera_hexagonal_optimitzat(R_tanc, r_amp)
    per_layer = len(centres_v)
    layers = math.floor(l_tanc / h_amp)
    total_verticals = per_layer * layers

    h_restant = l_tanc - (layers * h_amp)
    capes_tombades = int(math.floor(h_restant / d_amp))
    total_tombades = 0
    if capes_tombades > 0:
        centres_h = genera_horizontals(R_tanc, h_amp, d_amp)
        total_tombades = capes_tombades * len(centres_h)

    total = int(total_verticals + total_tombades)

    v_tanc = math.pi * (R_tanc ** 2) * l_tanc
    v_ampolla = math.pi * (r_amp ** 2) * h_amp
    v_ocupat = v_ampolla * total
    perc = (v_ocupat / v_tanc) * 100 if v_tanc > 0 else 0

    return total, perc


def stats_rectangular(d_tanc, l_tanc, w_env, d_env, h_env):
    R_tanc = d_tanc / 2.0

    centres_v, _ = genera_rectangular_optimitzat(R_tanc, w_env, d_env)
    per_layer = len(centres_v)
    layers = math.floor(l_tanc / h_env)
    total_verticals = per_layer * layers

    h_restant = l_tanc - (layers * h_env)

    capes_a = int(math.floor(h_restant / w_env))
    centres_a, _ = genera_rectangular_optimitzat(R_tanc, h_env, d_env) if capes_a > 0 else ([], 0)
    total_a = capes_a * len(centres_a)

    capes_b = int(math.floor(h_restant / d_env))
    centres_b, _ = genera_rectangular_optimitzat(R_tanc, w_env, h_env) if capes_b > 0 else ([], 0)
    total_b = capes_b * len(centres_b)

    total_tombades = total_a if total_a >= total_b else total_b
    total = int(total_verticals + total_tombades)

    v_tanc = math.pi * (R_tanc ** 2) * l_tanc
    v_env = w_env * d_env * h_env
    v_ocupat = v_env * total
    perc = (v_ocupat / v_tanc) * 100 if v_tanc > 0 else 0

    return total, perc


# ==========================================================
#   OPTIMITZACIÓ MÀQUINA: combinacions FIXES per cicle
# ==========================================================
def fixed_mix_per_cycle(machine_name, vessel_len_mm, L1_mm, L2_mm, cap_L1, cap_L2):
    """
    ÚNIQUES combinacions permeses:
      - H420: 4 petits  OR  3 grans
      - H525: 5 petits  OR  3 grans + 1 petit
    """
    if "420" in machine_name:
        combos = [(4, 0), (0, 3)]
    else:
        combos = [(5, 0), (1, 3)]

    rows = []
    for (k_p, k_g) in combos:
        used = k_p * float(L1_mm) + k_g * float(L2_mm)
        if used <= float(vessel_len_mm) and (k_p + k_g) > 0:
            units = int(k_p) * int(cap_L1) + int(k_g) * int(cap_L2)
            rows.append({
                "k_petit": int(k_p),
                "k_gran": int(k_g),
                "contenidors/cicle": int(k_p + k_g),
                "unitats/cicle": int(units),
            })

    return pd.DataFrame(rows)


def pick_best_mix(df_mix, N, cost_per_cycle, objective: str):
    if df_mix is None or df_mix.empty:
        return None, None

    df = df_mix.copy()
    df["cicles"] = df["unitats/cicle"].apply(lambda u: int(math.ceil(N / u)) if u > 0 else 10**9)
    df["cost_total"] = df["cicles"] * float(cost_per_cycle)

    if objective == "Minimitzar cicles":
        sort_by = ["cicles", "cost_total", "unitats/cicle"]
        asc =     [True,    True,        False]
    elif objective == "Minimitzar cost total":
        sort_by = ["cost_total", "cicles", "unitats/cicle"]
        asc =     [True,         True,     False]
    elif objective == "Maximitzar unitats/cicle":
        sort_by = ["unitats/cicle", "cicles", "cost_total"]
        asc =     [False,          True,     True]
    else:  # Balanced
        sort_by = ["cicles", "cost_total", "unitats/cicle"]
        asc =     [True,    True,         False]

    df = df.sort_values(by=sort_by, ascending=asc, kind="mergesort").reset_index(drop=True)
    return df.iloc[0].to_dict(), df


def units_last_container_last_cycle(N, k_petit, k_gran, cap_petit, cap_gran):
    """
    Supòsit:
    - A cada cicle omples contenidors en aquest ordre: primer GRANS, després PETITS.
    - Retorna quantes unitats té l'últim contenidor de l'últim cicle.
    """
    caps = ([int(cap_gran)] * int(k_gran)) + ([int(cap_petit)] * int(k_petit))
    if not caps:
        return 0, 0, 0

    units_per_cycle = int(k_petit) * int(cap_petit) + int(k_gran) * int(cap_gran)
    if units_per_cycle <= 0:
        return 0, caps[-1], 10**9

    cycles = int(math.ceil(int(N) / units_per_cycle))
    rem = int(int(N) - (cycles - 1) * units_per_cycle)

    if rem == 0:
        return int(caps[-1]), int(caps[-1]), cycles

    for cap in caps:
        if rem > cap:
            rem -= cap
        else:
            return int(rem), int(cap), cycles

    return int(caps[-1]), int(caps[-1]), cycles


def machine_key(best, objective):
    if best is None:
        return (10**9, float("inf"), 0)

    c = int(best["cicles"])
    cost = float(best["cost_total"])
    u = int(best["unitats/cicle"])

    if objective == "Minimitzar cicles":
        return (c, cost, -u)
    elif objective == "Minimitzar cost total":
        return (cost, c, -u)
    elif objective == "Maximitzar unitats/cicle":
        return (-u, c, cost)
    else:
        return (c, cost, -u)


# ==========================================================
#   TEXTOS (plan operatiu + export)
# ==========================================================
def plan_text(machine_name, best_row, N, cap_petit, cap_gran, objective, name_L1, name_L2, cost_per_cycle):
    if best_row is None:
        return f"- {machine_name}: cap combinació vàlida."

    k_p = int(best_row["k_petit"])
    k_g = int(best_row["k_gran"])
    u_cycle = int(best_row["unitats/cicle"])
    cycles = int(best_row["cicles"])
    cost_total = float(best_row["cost_total"])
    u_last, cap_last, _ = units_last_container_last_cycle(int(N), k_p, k_g, int(cap_petit), int(cap_gran))

    lines = []
    lines.append(f"**{machine_name}**")
    lines.append(f"- **Cost fix (inclou mà d'obra):** {float(cost_per_cycle):.2f} €/cicle")
    lines.append(f"- **Configuració per cicle:** {k_g}×{name_L2} + {k_p}×{name_L1}")
    lines.append(f"- **Rendiment:** {u_cycle} u/cicle  →  **{cycles} cicles** per fer N={int(N)}")
    lines.append(f"- **Cost total estimat:** {cost_total:.2f} €")
    lines.append(f"- **Últim contenidor de l’últim cicle:** {u_last} u (capacitat contenidor: {cap_last})")

    if objective == "Minimitzar cicles":
        lines.append("- **Objectiu:** menys cicles.")
    elif objective == "Minimitzar cost total":
        lines.append("- **Objectiu:** menor cost total.")
    elif objective == "Maximitzar unitats/cicle":
        lines.append("- **Objectiu:** màxim throughput (u/cicle).")
    else:
        lines.append("- **Objectiu:** equilibrat (cicles → cost).")

    return "\n".join(lines)


def build_plan_txt(
    N, d_tanc, forma, objective,
    cap_petit, cap_gran, perc_petit, perc_gran,
    best_420, best_525,
    chosen_machine,
):
    def row_summary(machine, best):
        if best is None:
            return f"- {machine}: cap combinació possible."
        return (
            f"- {machine}: k_petit={int(best['k_petit'])}, k_gran={int(best['k_gran'])}, "
            f"unitats/cicle={int(best['unitats/cicle'])}, cicles={int(best['cicles'])}, "
            f"cost_total={float(best['cost_total']):.2f}€"
        )

    lines = []
    lines.append("HPP LOAD PLANNER — PLA DE PRODUCCIÓ")
    lines.append("")
    lines.append("INPUTS")
    lines.append(f"- N (unitats comanda): {int(N)}")
    lines.append(f"- Diàmetre tanc: {float(d_tanc):.1f} mm")
    lines.append(f"- Forma producte: {forma}")
    lines.append(f"- Objectiu: {objective}")
    lines.append("")
    lines.append("CONTENIDORS (CAPACITAT)")
    lines.append(f"- {NAME_L1} ({int(L1_MM)} mm): {int(cap_petit)} u  | ocupació volum: {float(perc_petit):.2f}%")
    lines.append(f"- {NAME_L2} ({int(L2_MM)} mm): {int(cap_gran)} u  | ocupació volum: {float(perc_gran):.2f}%")
    lines.append("")
    lines.append("MÀQUINES (COST FIX €/CICLE + LONGITUD ÚTIL)")
    lines.append(f"- HIPERBARIC 420: {COST_420:.2f} €/cicle | longitud útil: {float(LEN_420_MM):.0f} mm")
    lines.append(f"- HIPERBARIC 525: {COST_525:.2f} €/cicle | longitud útil: {float(LEN_525_MM):.0f} mm")
    lines.append("")
    lines.append("RESULTATS (RESUM)")
    lines.append(row_summary("HIPERBARIC 420", best_420))
    lines.append(row_summary("HIPERBARIC 525", best_525))
    lines.append("")
    lines.append(f"RECOMANACIÓ: {chosen_machine}")
    lines.append("")

    best_winner = best_420 if chosen_machine.endswith("420") else best_525
    if best_winner is not None:
        k_p = int(best_winner["k_petit"])
        k_g = int(best_winner["k_gran"])
        u_last, cap_last, cycles = units_last_container_last_cycle(int(N), k_p, k_g, int(cap_petit), int(cap_gran))
        lines.append("DETALL OPERATIU (RECOMANACIÓ)")
        lines.append(f"- Cicles totals: {cycles}")
        lines.append(f"- Configuració per cicle: {k_g}×{NAME_L2} + {k_p}×{NAME_L1}")
        lines.append(f"- Últim contenidor (últim cicle): {u_last} u (capacitat {cap_last})")
        lines.append("")

    return "\n".join(lines)


def build_export_payload(
    N, d_tanc, forma, objective,
    cap_petit, cap_gran, perc_petit, perc_gran,
    best_420, best_525,
    chosen_machine
):
    return {
        "inputs": {
            "N": int(N),
            "d_tanc_mm": float(d_tanc),
            "forma": forma,
            "objective": objective,
        },
        "contenidors": {
            "petit": {"length_mm": float(L1_MM), "capacitat_unitats": int(cap_petit), "ocupacio_pct": float(perc_petit)},
            "gran":  {"length_mm": float(L2_MM), "capacitat_unitats": int(cap_gran),  "ocupacio_pct": float(perc_gran)},
        },
        "maquines": {
            "HIPERBARIC 420": {"vessel_len_mm": float(LEN_420_MM), "cost_eur_per_cycle": float(COST_420), "best": best_420},
            "HIPERBARIC 525": {"vessel_len_mm": float(LEN_525_MM), "cost_eur_per_cycle": float(COST_525), "best": best_525},
        },
        "recomanacio": {
            "machine": chosen_machine,
        }
    }


# ==========================================================
#   COST REAL (DECISIÓ OPTIM vs RÀPID)
#   IMPORTANT: el cost/cicle ja inclou mà d’obra → NO sumem cost d’operari.
#   L’únic que usem dels temps és una decisió “operativa” basada en cicles i throughput.
#
#   Per modelar PERFECTE la diferència OPTIM vs RÀPID (si cost/cicle és tot-inclòs),
#   falta una dada: com canvia el cost/cicle amb el temps/ritme real (normalment NO canvia).
#   Si realment és fix, la decisió econòmica depèn només de cicles (i de densitat).
# ==========================================================
def best_total_cost_cycles_only(df_mix, N, cost_per_cycle):
    if df_mix is None or df_mix.empty:
        return None, None

    df = df_mix.copy()
    df["cicles"] = df["unitats/cicle"].apply(lambda u: int(math.ceil(N / u)) if u > 0 else 10**9)
    df["cost_total"] = df["cicles"] * float(cost_per_cycle)
    df = df.sort_values(by=["cost_total", "cicles", "unitats/cicle"], ascending=[True, True, False], kind="mergesort").reset_index(drop=True)
    return df.iloc[0].to_dict(), df


# ==========================================================
#         COORDS 3D (centres)
# ==========================================================
def coords_cyl_all(d_tanc, l_tanc, d_amp, h_amp):
    R_tanc = d_tanc / 2.0
    r_amp = d_amp / 2.0

    centres_v = genera_hexagonal_optimitzat(R_tanc, r_amp)
    layers_v = math.floor(l_tanc / h_amp)

    xs, ys, zs, typ = [], [], [], []

    for k in range(layers_v):
        z = (k * h_amp) + (h_amp / 2.0)
        for (x, y) in centres_v:
            xs.append(x); ys.append(y); zs.append(z); typ.append("V")

    h_restant = l_tanc - (layers_v * h_amp)
    capes_tombades = int(math.floor(h_restant / d_amp))
    if capes_tombades > 0:
        centres_h = genera_horizontals(R_tanc, h_amp, d_amp)
        for capa in range(capes_tombades):
            z = (layers_v * h_amp) + r_amp + (capa * d_amp)
            for (x, y) in centres_h:
                xs.append(x); ys.append(y); zs.append(z); typ.append("H")

    return pd.DataFrame({"x": xs, "y": ys, "z": zs, "type": typ})


def coords_rect_all(d_tanc, l_tanc, w_env, d_env, h_env):
    R_tanc = d_tanc / 2.0

    centres_v, _ = genera_rectangular_optimitzat(R_tanc, w_env, d_env)
    layers_v = math.floor(l_tanc / h_env)

    xs, ys, zs, typ = [], [], [], []

    for k in range(layers_v):
        z = (k * h_env) + (h_env / 2.0)
        for (x, y) in centres_v:
            xs.append(x); ys.append(y); zs.append(z); typ.append("V")

    h_restant = l_tanc - (layers_v * h_env)

    capes_a = int(math.floor(h_restant / w_env))
    centres_a, _ = genera_rectangular_optimitzat(R_tanc, h_env, d_env) if capes_a > 0 else ([], 0)
    total_a = capes_a * len(centres_a)

    capes_b = int(math.floor(h_restant / d_env))
    centres_b, _ = genera_rectangular_optimitzat(R_tanc, w_env, h_env) if capes_b > 0 else ([], 0)
    total_b = capes_b * len(centres_b)

    z_base = layers_v * h_env

    if total_a >= total_b and total_a > 0:
        for capa in range(capes_a):
            z = z_base + (capa * w_env) + (w_env / 2.0)
            for (x, y) in centres_a:
                xs.append(x); ys.append(y); zs.append(z); typ.append("A")
    elif total_b > 0:
        for capa in range(capes_b):
            z = z_base + (capa * d_env) + (d_env / 2.0)
            for (x, y) in centres_b:
                xs.append(x); ys.append(y); zs.append(z); typ.append("B")

    return pd.DataFrame({"x": xs, "y": ys, "z": zs, "type": typ})


# ==========================================================
#     Mesh builders + wireframe
# ==========================================================
def add_box_mesh(vertices, faces, center, sx, sy, sz):
    cx, cy, cz = center
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0

    v = [
        (cx - hx, cy - hy, cz - hz),
        (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy + hy, cz - hz),
        (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz),
        (cx + hx, cy - hy, cz + hz),
        (cx + hx, cy + hy, cz + hz),
        (cx - hx, cy + hy, cz + hz),
    ]
    base = len(vertices)
    vertices.extend(v)

    f = [
        (0, 1, 2), (0, 2, 3),
        (4, 6, 5), (4, 7, 6),
        (0, 5, 1), (0, 4, 5),
        (3, 2, 6), (3, 6, 7),
        (0, 3, 7), (0, 7, 4),
        (1, 5, 6), (1, 6, 2),
    ]
    faces.extend([(base + a, base + b, base + c) for (a, b, c) in f])


def add_cylinder_mesh(vertices, faces, center, radius, length, axis="Z", nseg=12, caps=True):
    cx, cy, cz = center
    r = radius
    h = length
    base = len(vertices)

    angles = np.linspace(0, 2 * np.pi, nseg, endpoint=False)
    ca = np.cos(angles)
    sa = np.sin(angles)

    if axis == "Z":
        z0 = cz - h / 2.0
        z1 = cz + h / 2.0
        bottom = [(cx + r * ca[i], cy + r * sa[i], z0) for i in range(nseg)]
        top = [(cx + r * ca[i], cy + r * sa[i], z1) for i in range(nseg)]
    elif axis == "X":
        x0 = cx - h / 2.0
        x1 = cx + h / 2.0
        bottom = [(x0, cy + r * ca[i], cz + r * sa[i]) for i in range(nseg)]
        top = [(x1, cy + r * ca[i], cz + r * sa[i]) for i in range(nseg)]
    else:
        raise ValueError("axis must be 'Z' or 'X'")

    vertices.extend(bottom)
    vertices.extend(top)

    for i in range(nseg):
        j = (i + 1) % nseg
        b0 = base + i
        b1 = base + j
        t0 = base + nseg + i
        t1 = base + nseg + j
        faces.append((b0, t0, t1))
        faces.append((b0, t1, b1))

    if caps:
        if axis == "Z":
            c_bot = (cx, cy, cz - h / 2.0)
            c_top = (cx, cy, cz + h / 2.0)
        else:
            c_bot = (cx - h / 2.0, cy, cz)
            c_top = (cx + h / 2.0, cy, cz)

        c_bot_idx = len(vertices)
        vertices.append(c_bot)
        c_top_idx = len(vertices)
        vertices.append(c_top)

        for i in range(nseg):
            j = (i + 1) % nseg
            faces.append((c_bot_idx, base + j, base + i))
            faces.append((c_top_idx, base + nseg + i, base + nseg + j))


def mesh_from_boxes(centers_xyz, sx, sy, sz):
    vertices = []
    faces = []
    for (x, y, z) in centers_xyz:
        add_box_mesh(vertices, faces, (x, y, z), sx, sy, sz)
    return np.array(vertices, dtype=float), np.array(faces, dtype=int)


def mesh_from_cylinders(centers_xyz, radius, length, axis, nseg, caps=True):
    vertices = []
    faces = []
    for (x, y, z) in centers_xyz:
        add_cylinder_mesh(vertices, faces, (x, y, z), radius, length, axis=axis, nseg=nseg, caps=caps)
    return np.array(vertices, dtype=float), np.array(faces, dtype=int)


def tank_surface(d_tanc, l_tanc):
    R = d_tanc / 2.0
    theta = np.linspace(0, 2 * np.pi, 60)
    z = np.linspace(0, l_tanc, 2)
    Theta, Z = np.meshgrid(theta, z)
    X = R * np.cos(Theta)
    Y = R * np.sin(Theta)
    return X, Y, Z


def add_mesh_trace(fig, v, f, name, opacity=1.0):
    if v.size == 0 or f.size == 0:
        return
    fig.add_trace(go.Mesh3d(
        x=v[:, 0], y=v[:, 1], z=v[:, 2],
        i=f[:, 0], j=f[:, 1], k=f[:, 2],
        opacity=opacity,
        name=name,
        hoverinfo="skip",
        flatshading=True,
        lighting=dict(ambient=0.30, diffuse=0.85, specular=0.55, roughness=0.35, fresnel=0.15),
        lightposition=dict(x=2500, y=2500, z=2500),
    ))


def add_wireframe_trace(fig, x, y, z, name="Contorns", width=3, opacity=0.98):
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z,
        mode="lines",
        name=name,
        hoverinfo="skip",
        line=dict(width=width),
        opacity=opacity
    ))


def cylinder_wireframe_points(center, radius, length, axis="Z", nseg=34, n_long=8):
    cx, cy, cz = center
    r = radius
    h = length

    ang = np.linspace(0, 2 * np.pi, nseg, endpoint=True)
    ca = np.cos(ang)
    sa = np.sin(ang)

    xs, ys, zs = [], [], []

    def add_polyline(px, py, pz):
        xs.extend(px); ys.extend(py); zs.extend(pz)
        xs.append(None); ys.append(None); zs.append(None)

    if axis == "Z":
        z0 = cz - h / 2.0
        z1 = cz + h / 2.0
        add_polyline(list(cx + r * ca), list(cy + r * sa), [z0] * len(ang))
        add_polyline(list(cx + r * ca), list(cy + r * sa), [z1] * len(ang))
        for k in range(n_long):
            a = 2 * math.pi * k / n_long
            x = cx + r * math.cos(a)
            y = cy + r * math.sin(a)
            add_polyline([x, x], [y, y], [z0, z1])
    else:
        x0 = cx - h / 2.0
        x1 = cx + h / 2.0
        add_polyline([x0] * len(ang), list(cy + r * ca), list(cz + r * sa))
        add_polyline([x1] * len(ang), list(cy + r * ca), list(cz + r * sa))
        for k in range(n_long):
            a = 2 * math.pi * k / n_long
            y = cy + r * math.cos(a)
            z = cz + r * math.sin(a)
            add_polyline([x0, x1], [y, y], [z, z])

    return xs, ys, zs


def boxes_wireframe_points(centers_xyz, sx, sy, sz):
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7)
    ]

    xs, ys, zs = [], [], []
    for (cx, cy, cz) in centers_xyz:
        v = [
            (cx - hx, cy - hy, cz - hz),
            (cx + hx, cy - hy, cz - hz),
            (cx + hx, cy + hy, cz - hz),
            (cx - hx, cy + hy, cz - hz),
            (cx - hx, cy - hy, cz + hz),
            (cx + hx, cy - hy, cz + hz),
            (cx + hx, cy + hy, cz + hz),
            (cx - hx, cy + hy, cz + hz),
        ]
        for (a, b) in edges:
            xa, ya, za = v[a]
            xb, yb, zb = v[b]
            xs.extend([xa, xb, None])
            ys.extend([ya, yb, None])
            zs.extend([za, zb, None])

    return xs, ys, zs


def add_units_label(fig, units_text: str, l_tanc: float):
    z_pos = -0.10 * float(l_tanc)
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[z_pos],
        mode="text",
        text=[units_text],
        textposition="middle center",
        hoverinfo="skip",
        showlegend=False
    ))


def render_3d_cyl(fig_title, d_tanc, l_tanc, d_amp, h_amp, units_in_container: int):
    df = coords_cyl_all(d_tanc, l_tanc, d_amp, h_amp)
    v_centers = df[df["type"] == "V"][["x", "y", "z"]].to_numpy()
    h_centers = df[df["type"] == "H"][["x", "y", "z"]].to_numpy()

    fig = go.Figure()
    X, Y, Z = tank_surface(d_tanc, l_tanc)
    fig.add_trace(go.Surface(x=X, y=Y, z=Z, opacity=0.07, showscale=False, hoverinfo="skip", name="Tanc"))

    r = (d_amp / 2.0) * SHRINK_FACTOR
    h_vis = h_amp * SHRINK_FACTOR

    if len(v_centers) > 0:
        vmesh, vfaces = mesh_from_cylinders(v_centers, radius=r, length=h_vis, axis="Z",
                                            nseg=CYL_SEGMENTS, caps=CAPS)
        add_mesh_trace(fig, vmesh, vfaces, "Vertical", opacity=1.0)

        if SHOW_WIREFRAME:
            xw, yw, zw = [], [], []
            for (x, y, z) in v_centers:
                xs, ys, zs = cylinder_wireframe_points((x, y, z), r, h_vis, axis="Z",
                                                       nseg=WIRE_NSEG, n_long=8)
                xw += xs; yw += ys; zw += zs
            add_wireframe_trace(fig, xw, yw, zw, name="Contorns Vertical", width=WIRE_WIDTH)

    if len(h_centers) > 0:
        hmesh, hfaces = mesh_from_cylinders(h_centers, radius=r, length=h_vis, axis="X",
                                            nseg=CYL_SEGMENTS, caps=CAPS)
        add_mesh_trace(fig, hmesh, hfaces, "Tombada", opacity=1.0)

        if SHOW_WIREFRAME:
            xw, yw, zw = [], [], []
            for (x, y, z) in h_centers:
                xs, ys, zs = cylinder_wireframe_points((x, y, z), r, h_vis, axis="X",
                                                       nseg=WIRE_NSEG, n_long=8)
                xw += xs; yw += ys; zw += zs
            add_wireframe_trace(fig, xw, yw, zw, name="Contorns Tombada", width=WIRE_WIDTH)

    add_units_label(fig, f"{int(units_in_container)} u dins del contenidor", l_tanc)

    fig.update_layout(
        title=fig_title,
        scene=dict(xaxis_title="X (mm)", yaxis_title="Y (mm)", zaxis_title="Z (mm)", aspectmode="data"),
        margin=dict(l=0, r=0, t=35, b=0),
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_3d_rect(fig_title, d_tanc, l_tanc, w_env, d_env, h_env, units_in_container: int):
    df = coords_rect_all(d_tanc, l_tanc, w_env, d_env, h_env)
    v_centers = df[df["type"] == "V"][["x", "y", "z"]].to_numpy()
    a_centers = df[df["type"] == "A"][["x", "y", "z"]].to_numpy()
    b_centers = df[df["type"] == "B"][["x", "y", "z"]].to_numpy()

    fig = go.Figure()
    X, Y, Z = tank_surface(d_tanc, l_tanc)
    fig.add_trace(go.Surface(x=X, y=Y, z=Z, opacity=0.07, showscale=False, hoverinfo="skip", name="Tanc"))

    wv = w_env * SHRINK_FACTOR
    dv = d_env * SHRINK_FACTOR
    hv = h_env * SHRINK_FACTOR

    if len(v_centers) > 0:
        vmesh, vfaces = mesh_from_boxes(v_centers, sx=wv, sy=dv, sz=hv)
        add_mesh_trace(fig, vmesh, vfaces, "Vertical", opacity=1.0)
        if SHOW_WIREFRAME:
            xw, yw, zw = boxes_wireframe_points(v_centers, wv, dv, hv)
            add_wireframe_trace(fig, xw, yw, zw, name="Contorns Vertical", width=WIRE_WIDTH)

    if len(a_centers) > 0:
        amesh, afaces = mesh_from_boxes(a_centers, sx=hv, sy=dv, sz=wv)
        add_mesh_trace(fig, amesh, afaces, "Tombada_A", opacity=1.0)
        if SHOW_WIREFRAME:
            xw, yw, zw = boxes_wireframe_points(a_centers, hv, dv, wv)
            add_wireframe_trace(fig, xw, yw, zw, name="Contorns Tombada_A", width=WIRE_WIDTH)

    if len(b_centers) > 0:
        bmesh, bfaces = mesh_from_boxes(b_centers, sx=wv, sy=hv, sz=dv)
        add_mesh_trace(fig, bmesh, bfaces, "Tombada_B", opacity=1.0)
        if SHOW_WIREFRAME:
            xw, yw, zw = boxes_wireframe_points(b_centers, wv, hv, dv)
            add_wireframe_trace(fig, xw, yw, zw, name="Contorns Tombada_B", width=WIRE_WIDTH)

    add_units_label(fig, f"{int(units_in_container)} u dins del contenidor", l_tanc)

    fig.update_layout(
        title=fig_title,
        scene=dict(xaxis_title="X (mm)", yaxis_title="Y (mm)", zaxis_title="Z (mm)", aspectmode="data"),
        margin=dict(l=0, r=0, t=35, b=0),
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)


# ==========================================================
# UI
# ==========================================================
st.title("HPP Load Planner — Matemàtica + 3D")

with st.sidebar:
    st.header("Inputs")
    N = st.number_input("Unitats comanda (N)", min_value=1, value=2000, step=10)
    d_tanc = st.number_input("Diàmetre del tanc (mm)", min_value=1.0, value=380.0, step=1.0)
    forma = st.selectbox("Forma producte", ["Cilíndric", "Rectangular"])

    st.subheader("Objectiu d'optimització (ideal)")
    objective = st.selectbox(
        "Tria l'objectiu",
        [
            "Minimitzar cicles",
            "Minimitzar cost total",
            "Maximitzar unitats/cicle",
            "Balanced (cicles → cost)"
        ],
        index=0
    )

    st.subheader("Màquines (fixes)")
    st.caption(f"HIPERBARIC 420 — {COST_420:.2f} €/cicle (inclou mà d'obra) | longitud útil {LEN_420_MM:.0f} mm")
    st.caption(f"HIPERBARIC 525 — {COST_525:.2f} €/cicle (inclou mà d'obra) | longitud útil {LEN_525_MM:.0f} mm")

col1, col2 = st.columns([1.2, 1.0])

name_420 = "HIPERBARIC 420"
name_525 = "HIPERBARIC 525"


def show_best_line(machine_name, best_row, cap_p, cap_g, cost_per_cycle):
    if best_row is None:
        st.warning(f"{machine_name}: cap combinació possible.")
        return None

    k_p = int(best_row["k_petit"])
    k_g = int(best_row["k_gran"])
    u_last, cap_last, _ = units_last_container_last_cycle(int(N), k_p, k_g, cap_p, cap_g)

    st.write(
        f"**{machine_name}** → **{k_p}×{NAME_L1} + {k_g}×{NAME_L2}** | "
        f"**{int(best_row['unitats/cicle'])} u/cicle** | "
        f"cicles: **{int(best_row['cicles'])}** | "
        f"cost total: **{float(best_row['cost_total']):.2f} €** | "
        f"**últim contenidor (últim cicle): {u_last} u** (cap {cap_last})"
    )
    return best_row


def combos_dropdown(machine_title, df_scored):
    st.markdown(f"**{machine_title} — Combinacions possibles**")
    if df_scored is None or df_scored.empty:
        st.info("Sense combinacions.")
        return

    options = []
    for _, r in df_scored.iterrows():
        kp = int(r["k_petit"]); kg = int(r["k_gran"])
        options.append(
            f"{kg}×{NAME_L2} + {kp}×{NAME_L1}  —  "
            f"{int(r['unitats/cicle'])} u/cicle | {int(r['cicles'])} cicles | {float(r['cost_total']):.2f} €"
        )

    idx = st.selectbox("Tria combinació", list(range(len(options))), format_func=lambda i: options[i], key=f"combo_{machine_title}")
    row = df_scored.iloc[int(idx)].to_dict()
    st.caption(f"Detall: k_petit={int(row['k_petit'])}, k_gran={int(row['k_gran'])} | contenidors/cicle={int(row['contenidors/cicle'])}")
    st.write("")


# ==========================================================
# CILÍNDRIC
# ==========================================================
if forma == "Cilíndric":
    with col1:
        st.subheader("Paràmetres cilíndric")
        d_amp = st.number_input("Diàmetre ampolla (mm)", min_value=0.1, value=50.0, step=0.5)
        h_amp = st.number_input("Alçada ampolla (mm)", min_value=0.1, value=150.0, step=0.5)

    cap_petit, perc_petit = stats_cilindric(d_tanc, L1_MM, d_amp, h_amp)
    cap_gran, perc_gran = stats_cilindric(d_tanc, L2_MM, d_amp, h_amp)

    with col2:
        st.subheader("Capacitats (contenidors)")
        st.write(f"**{NAME_L1}** ({int(L1_MM)} mm): **{cap_petit} u** | ocupat **{perc_petit:.2f}%**")
        st.write(f"**{NAME_L2}** ({int(L2_MM)} mm): **{cap_gran} u** | ocupat **{perc_gran:.2f}%**")

        st.markdown("### Pla de producció (ideal)")
        mix_420 = fixed_mix_per_cycle(name_420, LEN_420_MM, L1_MM, L2_MM, cap_petit, cap_gran)
        mix_525 = fixed_mix_per_cycle(name_525, LEN_525_MM, L1_MM, L2_MM, cap_petit, cap_gran)

        best_420, scored_420 = pick_best_mix(mix_420, int(N), COST_420, objective) if not mix_420.empty else (None, mix_420)
        best_525, scored_525 = pick_best_mix(mix_525, int(N), COST_525, objective) if not mix_525.empty else (None, mix_525)

        _ = show_best_line(name_420, best_420, cap_petit, cap_gran, COST_420)
        _ = show_best_line(name_525, best_525, cap_petit, cap_gran, COST_525)

        chosen_machine = name_420 if machine_key(best_420, objective) <= machine_key(best_525, objective) else name_525
        st.success(f"🏭 Màquina recomanada: **{chosen_machine}**")

        st.markdown("---")
        st.subheader("Conclusió (què fer a planta)")
        best_winner = best_420 if chosen_machine == name_420 else best_525
        cost_winner = COST_420 if chosen_machine == name_420 else COST_525

        colC1, colC2 = st.columns([1.2, 0.8])
        with colC1:
            st.markdown(
                plan_text(
                    machine_name=chosen_machine,
                    best_row=best_winner,
                    N=int(N),
                    cap_petit=int(cap_petit),
                    cap_gran=int(cap_gran),
                    objective=objective,
                    name_L1=NAME_L1,
                    name_L2=NAME_L2,
                    cost_per_cycle=cost_winner,
                )
            )
        with colC2:
            st.info(
                "✅ **Workflow**\n\n"
                "1) Prepara els contenidors segons la combinació recomanada.\n"
                "2) Repeteix els cicles fins completar la comanda.\n"
                "3) A l’últim cicle, l’últim contenidor pot quedar parcial (unitats indicades)."
            )

        st.markdown("---")
        st.subheader("Combinacions possibles")
        combos_dropdown("HIPERBARIC 420", scored_420)
        combos_dropdown("HIPERBARIC 525", scored_525)

        # ==========================================================
        # DECISIÓ OPTIM vs RÀPID (cost/cicle all-in)
        # ==========================================================
        st.markdown("---")
        st.subheader("Decisió: OPTIM vs RÀPID (cost/cicle ja inclou mà d'obra)")

        st.markdown(
            "Com que el **cost/cicle és tot-inclòs**, el cost total depèn principalment dels **cicles**.\n\n"
            "Els temps de càrrega els fem servir com a criteri de **workflow** (si la diferència de temps és gran, potser preferiu RÀPID)."
        )

        colD1, colD2 = st.columns(2)
        with colD1:
            t_load_optim = st.number_input("Temps carregar 1 contenidor (OPTIM) (min)", min_value=0.0, value=3.0, step=0.1, key="t_load_opt_simple_cyl")
            t_load_rapid = st.number_input("Temps carregar 1 contenidor (RÀPID) (min)", min_value=0.0, value=2.0, step=0.1, key="t_load_rap_simple_cyl")
        with colD2:
            with st.expander("Avançat (per modelar RÀPID): densitat"):
                st.markdown("**Dada clau**: quanta densitat perds fent RÀPID.")
                factor_rapid = st.slider("Factor densitat RÀPID", min_value=0.50, max_value=1.00, value=0.85, step=0.01, key="factor_rapid_simple_cyl")

        cap_p_rap = max(1, int(round(int(cap_petit) * float(factor_rapid))))
        cap_g_rap = max(1, int(round(int(cap_gran) * float(factor_rapid))))

        # millor opció per cost (només cicles)
        mix_420_opt = fixed_mix_per_cycle(name_420, LEN_420_MM, L1_MM, L2_MM, int(cap_petit), int(cap_gran))
        mix_525_opt = fixed_mix_per_cycle(name_525, LEN_525_MM, L1_MM, L2_MM, int(cap_petit), int(cap_gran))
        mix_420_rap = fixed_mix_per_cycle(name_420, LEN_420_MM, L1_MM, L2_MM, int(cap_p_rap), int(cap_g_rap))
        mix_525_rap = fixed_mix_per_cycle(name_525, LEN_525_MM, L1_MM, L2_MM, int(cap_p_rap), int(cap_g_rap))

        best_420_opt, _ = best_total_cost_cycles_only(mix_420_opt, int(N), COST_420)
        best_525_opt, _ = best_total_cost_cycles_only(mix_525_opt, int(N), COST_525)
        best_420_rap, _ = best_total_cost_cycles_only(mix_420_rap, int(N), COST_420)
        best_525_rap, _ = best_total_cost_cycles_only(mix_525_rap, int(N), COST_525)

        candidates = []
        if best_420_opt: candidates.append(("OPTIM", name_420, best_420_opt, COST_420, t_load_optim))
        if best_525_opt: candidates.append(("OPTIM", name_525, best_525_opt, COST_525, t_load_optim))
        if best_420_rap: candidates.append(("RÀPID", name_420, best_420_rap, COST_420, t_load_rapid))
        if best_525_rap: candidates.append(("RÀPID", name_525, best_525_rap, COST_525, t_load_rapid))

        rows = []
        for mode, mach, br, cost_cycle, t_load in candidates:
            k_p = int(br["k_petit"]); k_g = int(br["k_gran"])
            cont_per_cycle = int(k_p + k_g)
            cycles = int(br["cicles"])
            cont_total = cycles * cont_per_cycle  # aprox (simple i entenedor)
            time_total_min = float(cont_total) * float(t_load)
            rows.append({
                "Mode": mode,
                "Màquina": mach,
                "k_petit": k_p,
                "k_gran": k_g,
                "Cicles": cycles,
                "Cost TOTAL (€)": float(br["cost_total"]),
                "Temps càrrega total (min)": time_total_min,
            })

        df_dec = pd.DataFrame(rows).sort_values(by=["Cost TOTAL (€)", "Cicles", "Temps càrrega total (min)"], ascending=[True, True, True])
        st.dataframe(df_dec, use_container_width=True)

        best_row = df_dec.iloc[0].to_dict()
        st.metric("Recomanació (mínim cost all-in)", f"{best_row['Mode']} — {best_row['Màquina']}")

        # ==========================================================
        # EXPORTAR
        # ==========================================================
        st.markdown("---")
        st.subheader("Descarregar pla de producció")

        payload = build_export_payload(
            N=N, d_tanc=d_tanc, forma=forma, objective=objective,
            cap_petit=cap_petit, cap_gran=cap_gran, perc_petit=perc_petit, perc_gran=perc_gran,
            best_420=best_420, best_525=best_525,
            chosen_machine=chosen_machine
        )

        plan_txt = build_plan_txt(
            N=N, d_tanc=d_tanc, forma=forma, objective=objective,
            cap_petit=cap_petit, cap_gran=cap_gran, perc_petit=perc_petit, perc_gran=perc_gran,
            best_420=best_420, best_525=best_525,
            chosen_machine=chosen_machine
        )

        cE1, cE2 = st.columns([1, 1])
        with cE1:
            st.download_button(
                "⬇️ Descarregar pla de producció (TXT)",
                data=plan_txt,
                file_name="hpp_pla_produccio.txt",
                mime="text/plain"
            )
        with cE2:
            st.download_button(
                "⬇️ Descarregar dades (JSON)",
                data=json.dumps(payload, indent=2, ensure_ascii=False),
                file_name="hpp_pla_produccio.json",
                mime="application/json"
            )

    st.markdown("---")
    st.subheader("3D — Comparació contenidor petit vs contenidor gran")
    cA, cB = st.columns(2)
    with cA:
        render_3d_cyl(f"{NAME_L1} ({int(L1_MM)} mm)", d_tanc, L1_MM, d_amp, h_amp, units_in_container=int(cap_petit))
    with cB:
        render_3d_cyl(f"{NAME_L2} ({int(L2_MM)} mm)", d_tanc, L2_MM, d_amp, h_amp, units_in_container=int(cap_gran))

# ==========================================================
# RECTANGULAR
# ==========================================================
else:
    with col1:
        st.subheader("Paràmetres rectangular")
        w_env = st.number_input("Amplada (X) (mm)", min_value=0.1, value=40.0, step=0.5)
        d_env = st.number_input("Profunditat (Y) (mm)", min_value=0.1, value=60.0, step=0.5)
        h_env = st.number_input("Alçada (Z) (mm)", min_value=0.1, value=150.0, step=0.5)

    cap_petit, perc_petit = stats_rectangular(d_tanc, L1_MM, w_env, d_env, h_env)
    cap_gran, perc_gran = stats_rectangular(d_tanc, L2_MM, w_env, d_env, h_env)

    with col2:
        st.subheader("Capacitats (contenidors)")
        st.write(f"**{NAME_L1}** ({int(L1_MM)} mm): **{cap_petit} u** | ocupat **{perc_petit:.2f}%**")
        st.write(f"**{NAME_L2}** ({int(L2_MM)} mm): **{cap_gran} u** | ocupat **{perc_gran:.2f}%**")

        st.markdown("### Pla de producció (ideal)")
        mix_420 = fixed_mix_per_cycle(name_420, LEN_420_MM, L1_MM, L2_MM, cap_petit, cap_gran)
        mix_525 = fixed_mix_per_cycle(name_525, LEN_525_MM, L1_MM, L2_MM, cap_petit, cap_gran)

        best_420, scored_420 = pick_best_mix(mix_420, int(N), COST_420, objective) if not mix_420.empty else (None, mix_420)
        best_525, scored_525 = pick_best_mix(mix_525, int(N), COST_525, objective) if not mix_525.empty else (None, mix_525)

        _ = show_best_line(name_420, best_420, cap_petit, cap_gran, COST_420)
        _ = show_best_line(name_525, best_525, cap_petit, cap_gran, COST_525)

        chosen_machine = name_420 if machine_key(best_420, objective) <= machine_key(best_525, objective) else name_525
        st.success(f"🏭 Màquina recomanada: **{chosen_machine}**")

        st.markdown("---")
        st.subheader("Conclusió (què fer a planta)")
        best_winner = best_420 if chosen_machine == name_420 else best_525
        cost_winner = COST_420 if chosen_machine == name_420 else COST_525

        colC1, colC2 = st.columns([1.2, 0.8])
        with colC1:
            st.markdown(
                plan_text(
                    machine_name=chosen_machine,
                    best_row=best_winner,
                    N=int(N),
                    cap_petit=int(cap_petit),
                    cap_gran=int(cap_gran),
                    objective=objective,
                    name_L1=NAME_L1,
                    name_L2=NAME_L2,
                    cost_per_cycle=cost_winner,
                )
            )
        with colC2:
            st.info(
                "✅ **Workflow**\n\n"
                "1) Prepara els contenidors segons la combinació recomanada.\n"
                "2) Repeteix els cicles fins completar la comanda.\n"
                "3) A l’últim cicle, l’últim contenidor pot quedar parcial (unitats indicades)."
            )

        st.markdown("---")
        st.subheader("Combinacions possibles")
        combos_dropdown("HIPERBARIC 420", scored_420)
        combos_dropdown("HIPERBARIC 525", scored_525)

        st.markdown("---")
        st.subheader("Decisió: OPTIM vs RÀPID (cost/cicle ja inclou mà d'obra)")

        colD1, colD2 = st.columns(2)
        with colD1:
            t_load_optim = st.number_input("Temps carregar 1 contenidor (OPTIM) (min)", min_value=0.0, value=3.0, step=0.1, key="t_load_opt_simple_rect")
            t_load_rapid = st.number_input("Temps carregar 1 contenidor (RÀPID) (min)", min_value=0.0, value=2.0, step=0.1, key="t_load_rap_simple_rect")
        with colD2:
            with st.expander("Avançat (per modelar RÀPID): densitat"):
                factor_rapid = st.slider("Factor densitat RÀPID", min_value=0.50, max_value=1.00, value=0.85, step=0.01, key="factor_rapid_simple_rect")

        cap_p_rap = max(1, int(round(int(cap_petit) * float(factor_rapid))))
        cap_g_rap = max(1, int(round(int(cap_gran) * float(factor_rapid))))

        mix_420_opt = fixed_mix_per_cycle(name_420, LEN_420_MM, L1_MM, L2_MM, int(cap_petit), int(cap_gran))
        mix_525_opt = fixed_mix_per_cycle(name_525, LEN_525_MM, L1_MM, L2_MM, int(cap_petit), int(cap_gran))
        mix_420_rap = fixed_mix_per_cycle(name_420, LEN_420_MM, L1_MM, L2_MM, int(cap_p_rap), int(cap_g_rap))
        mix_525_rap = fixed_mix_per_cycle(name_525, LEN_525_MM, L1_MM, L2_MM, int(cap_p_rap), int(cap_g_rap))

        best_420_opt, _ = best_total_cost_cycles_only(mix_420_opt, int(N), COST_420)
        best_525_opt, _ = best_total_cost_cycles_only(mix_525_opt, int(N), COST_525)
        best_420_rap, _ = best_total_cost_cycles_only(mix_420_rap, int(N), COST_420)
        best_525_rap, _ = best_total_cost_cycles_only(mix_525_rap, int(N), COST_525)

        candidates = []
        if best_420_opt: candidates.append(("OPTIM", name_420, best_420_opt, COST_420, t_load_optim))
        if best_525_opt: candidates.append(("OPTIM", name_525, best_525_opt, COST_525, t_load_optim))
        if best_420_rap: candidates.append(("RÀPID", name_420, best_420_rap, COST_420, t_load_rapid))
        if best_525_rap: candidates.append(("RÀPID", name_525, best_525_rap, COST_525, t_load_rapid))

        rows = []
        for mode, mach, br, cost_cycle, t_load in candidates:
            k_p = int(br["k_petit"]); k_g = int(br["k_gran"])
            cont_per_cycle = int(k_p + k_g)
            cycles = int(br["cicles"])
            cont_total = cycles * cont_per_cycle
            time_total_min = float(cont_total) * float(t_load)
            rows.append({
                "Mode": mode,
                "Màquina": mach,
                "k_petit": k_p,
                "k_gran": k_g,
                "Cicles": cycles,
                "Cost TOTAL (€)": float(br["cost_total"]),
                "Temps càrrega total (min)": time_total_min,
            })

        df_dec = pd.DataFrame(rows).sort_values(by=["Cost TOTAL (€)", "Cicles", "Temps càrrega total (min)"], ascending=[True, True, True])
        st.dataframe(df_dec, use_container_width=True)
        best_row = df_dec.iloc[0].to_dict()
        st.metric("Recomanació (mínim cost all-in)", f"{best_row['Mode']} — {best_row['Màquina']}")

        st.markdown("---")
        st.subheader("Descarregar pla de producció")

        payload = build_export_payload(
            N=N, d_tanc=d_tanc, forma=forma, objective=objective,
            cap_petit=cap_petit, cap_gran=cap_gran, perc_petit=perc_petit, perc_gran=perc_gran,
            best_420=best_420, best_525=best_525,
            chosen_machine=chosen_machine
        )

        plan_txt = build_plan_txt(
            N=N, d_tanc=d_tanc, forma=forma, objective=objective,
            cap_petit=cap_petit, cap_gran=cap_gran, perc_petit=perc_petit, perc_gran=perc_gran,
            best_420=best_420, best_525=best_525,
            chosen_machine=chosen_machine
        )

        cE1, cE2 = st.columns([1, 1])
        with cE1:
            st.download_button(
                "⬇️ Descarregar pla de producció (TXT)",
                data=plan_txt,
                file_name="hpp_pla_produccio.txt",
                mime="text/plain"
            )
        with cE2:
            st.download_button(
                "⬇️ Descarregar dades (JSON)",
                data=json.dumps(payload, indent=2, ensure_ascii=False),
                file_name="hpp_pla_produccio.json",
                mime="application/json"
            )

    st.markdown("---")
    st.subheader("3D — Comparació contenidor petit vs contenidor gran")
    cA, cB = st.columns(2)
    with cA:
        render_3d_rect(f"{NAME_L1} ({int(L1_MM)} mm)", d_tanc, L1_MM, w_env, d_env, h_env, units_in_container=int(cap_petit))
    with cB:
        render_3d_rect(f"{NAME_L2} ({int(L2_MM)} mm)", d_tanc, L2_MM, w_env, d_env, h_env, units_in_container=int(cap_gran))
