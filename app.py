# -*- coding: utf-8 -*-
# HPP Load Planner — ORDENAT vs RANDOM
# Millores implementades:
# - Presets reals d'envasos/productes
# - Família producte: Sòlid / Líquid
# - 3D amb horitzontals a la part superior del contenidor
# - Inputs més clars pel PM

import math
import json
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# ==========================================================
# PAGE
# ==========================================================
st.set_page_config(page_title="HPP Load Planner — ORDENAT vs RANDOM", layout="wide")

# ==========================================================
# CONFIG CONTENIDORS (mm) — FIXOS
# ==========================================================
L1_MM = 880.0
L2_MM = 1190.0
NAME_L1 = "Contenidor petit"
NAME_L2 = "Contenidor gran"

# ==========================================================
# COST FIX / CICLE (SENSE MOD) — FIX
# H525: 50.42 - 13.78 = 36.64 €/cicle
# H420: 43.90 - 11.20 = 32.70 €/cicle
# ==========================================================
NONLAB_420 = 32.70
NONLAB_525 = 36.64

# ==========================================================
# LONGITUD ÚTIL VASIJA — FIXA
# ==========================================================
LEN_420_MM = 3700.0
LEN_525_MM = 4630.0

# ==========================================================
# 3D DEFAULTS
# ==========================================================
CYL_SEGMENTS = 18
CAPS = True
SHOW_WIREFRAME = True
WIRE_NSEG = 34
WIRE_WIDTH = 4
SHRINK_FACTOR = 0.985

# ==========================================================
# PRESETS PRODUCTE
# ==========================================================
PRODUCT_PRESETS = {
    "Personalitzat": {
        "family": "Sòlid",
        "shape": "Cilíndric",
        "d": 50.0,
        "h": 150.0,
        "w": 40.0,
        "depth": 60.0,
        "hz": 150.0,
    },
    "Xoriç (Ø80 x 1050)": {
        "family": "Sòlid",
        "shape": "Cilíndric",
        "d": 80.0,
        "h": 1050.0,
        "w": 40.0,
        "depth": 60.0,
        "hz": 150.0,
    },
    "Llonganissa (Ø65 x 1050)": {
        "family": "Sòlid",
        "shape": "Cilíndric",
        "d": 65.0,
        "h": 1050.0,
        "w": 40.0,
        "depth": 60.0,
        "hz": 150.0,
    },
    "Pernil simple (80 x 190 x 400)": {
        "family": "Sòlid",
        "shape": "Rectangular",
        "d": 50.0,
        "h": 150.0,
        "w": 80.0,
        "depth": 190.0,
        "hz": 400.0,
    },
    "Pernil doble (80 x 190 x 800)": {
        "family": "Sòlid",
        "shape": "Rectangular",
        "d": 50.0,
        "h": 150.0,
        "w": 80.0,
        "depth": 190.0,
        "hz": 800.0,
    },
}

# ==========================================================
# COMPATIBILITAT DE COMBINACIÓ (base preparada)
# ==========================================================
def families_are_compatible(families):
    fams = [str(f).strip().lower() for f in families if str(f).strip()]
    return len(set(fams)) <= 1


# ==========================================================
#              MATEMÀTICA CILÍNDRICA (packing)
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
                rang_max = int(R_tanc / max(r_amp, 1e-9)) + 2
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

        x_max = math.sqrt(max(0.0, R_tanc ** 2 - y_extrem ** 2))
        espai_disponible = 2 * x_max
        quantes = int(espai_disponible // max(h_amp, 1e-9))

        if quantes > 0:
            inici_x = -(quantes * h_amp) / 2.0 + (h_amp / 2.0)
            for i in range(quantes):
                x_pos = inici_x + i * h_amp
                centres_horitzontals.append((x_pos, y_actual))

        y_actual += d_amp
    return centres_horitzontals


# ==========================================================
#              MATEMÀTICA RECTANGULAR (packing)
# ==========================================================
def genera_rectangular_optimitzat(R_tanc, dim_x, dim_y):
    millor_configuracio = []
    millor_angle = 0.0
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
                rang_x = int(R_tanc / max(dim_x, 1e-9)) + 2
                rang_y = int(R_tanc / max(dim_y, 1e-9)) + 2

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
# LAYOUTS ÒPTIMS — horitzontals sempre al tram final
# ==========================================================
def best_cyl_layout_accessible(d_tanc, l_tanc, d_amp, h_amp):
    R_tanc = d_tanc / 2.0
    r_amp = d_amp / 2.0

    centres_v = genera_hexagonal_optimitzat(R_tanc, r_amp)
    per_layer_v = len(centres_v)

    centres_h = genera_horizontals(R_tanc, h_amp, d_amp)
    per_layer_h = len(centres_h)

    best = {
        "total": 0,
        "anchor_frac": None,
        "n_h_layers": 0,
        "h_start": None,
        "h_end": None,
        "v_left_layers": 0,
        "v_right_layers": 0,
        "centres_v": centres_v,
        "centres_h": centres_h,
    }

    # Tot vertical
    all_v_layers = int(math.floor(l_tanc / max(h_amp, 1e-9)))
    all_v_total = all_v_layers * per_layer_v
    if all_v_total > best["total"]:
        best.update({
            "total": int(all_v_total),
            "anchor_frac": None,
            "n_h_layers": 0,
            "h_start": None,
            "h_end": None,
            "v_left_layers": int(all_v_layers),
            "v_right_layers": 0,
        })

    # Amb banda horitzontal, sempre col·locada al final per mantenir el 3D "a dalt"
    max_h_layers = int(math.floor(l_tanc / max(d_amp, 1e-9)))
    for n_h in range(1, max_h_layers + 1):
        band_len = n_h * d_amp
        if band_len > l_tanc:
            continue

        v_left_layers = int(math.floor((l_tanc - band_len) / max(h_amp, 1e-9)))
        h_start = l_tanc - band_len
        h_end = l_tanc
        v_right_layers = 0

        total = v_left_layers * per_layer_v + n_h * per_layer_h

        if total > best["total"]:
            best.update({
                "total": int(total),
                "anchor_frac": None,
                "n_h_layers": int(n_h),
                "h_start": float(h_start),
                "h_end": float(h_end),
                "v_left_layers": int(v_left_layers),
                "v_right_layers": int(v_right_layers),
            })

    return best


def best_rect_layout_accessible(d_tanc, l_tanc, w_env, d_env, h_env):
    R_tanc = d_tanc / 2.0

    centres_v, _ = genera_rectangular_optimitzat(R_tanc, w_env, d_env)
    per_layer_v = len(centres_v)

    best = {
        "total": 0,
        "mode": "V",
        "anchor_frac": None,
        "n_h_layers": 0,
        "h_start": None,
        "h_end": None,
        "v_left_layers": 0,
        "v_right_layers": 0,
        "centres_v": centres_v,
        "centres_h": [],
        "layer_thickness": 0.0,
        "sx": w_env,
        "sy": d_env,
        "sz": h_env,
    }

    # Tot vertical
    all_v_layers = int(math.floor(l_tanc / max(h_env, 1e-9)))
    all_v_total = all_v_layers * per_layer_v
    if all_v_total > best["total"]:
        best.update({
            "total": int(all_v_total),
            "mode": "V",
            "v_left_layers": int(all_v_layers),
            "v_right_layers": 0,
            "n_h_layers": 0,
            "h_start": None,
            "h_end": None,
        })

    # Opció A: tombat amb gruix w_env, al tram final
    centres_a, _ = genera_rectangular_optimitzat(R_tanc, h_env, d_env)
    per_layer_a = len(centres_a)
    max_a_layers = int(math.floor(l_tanc / max(w_env, 1e-9)))

    for n_h in range(1, max_a_layers + 1):
        band_len = n_h * w_env
        if band_len > l_tanc:
            continue

        v_left_layers = int(math.floor((l_tanc - band_len) / max(h_env, 1e-9)))
        h_start = l_tanc - band_len
        h_end = l_tanc
        v_right_layers = 0

        total = v_left_layers * per_layer_v + n_h * per_layer_a

        if total > best["total"]:
            best.update({
                "total": int(total),
                "mode": "A",
                "anchor_frac": None,
                "n_h_layers": int(n_h),
                "h_start": float(h_start),
                "h_end": float(h_end),
                "v_left_layers": int(v_left_layers),
                "v_right_layers": int(v_right_layers),
                "centres_h": centres_a,
                "layer_thickness": float(w_env),
            })

    # Opció B: tombat amb gruix d_env, al tram final
    centres_b, _ = genera_rectangular_optimitzat(R_tanc, w_env, h_env)
    per_layer_b = len(centres_b)
    max_b_layers = int(math.floor(l_tanc / max(d_env, 1e-9)))

    for n_h in range(1, max_b_layers + 1):
        band_len = n_h * d_env
        if band_len > l_tanc:
            continue

        v_left_layers = int(math.floor((l_tanc - band_len) / max(h_env, 1e-9)))
        h_start = l_tanc - band_len
        h_end = l_tanc
        v_right_layers = 0

        total = v_left_layers * per_layer_v + n_h * per_layer_b

        if total > best["total"]:
            best.update({
                "total": int(total),
                "mode": "B",
                "anchor_frac": None,
                "n_h_layers": int(n_h),
                "h_start": float(h_start),
                "h_end": float(h_end),
                "v_left_layers": int(v_left_layers),
                "v_right_layers": int(v_right_layers),
                "centres_h": centres_b,
                "layer_thickness": float(d_env),
            })

    return best


# ==========================================================
#        STATS (capacitat i % volum)
# ==========================================================
def stats_cilindric(d_tanc, l_tanc, d_amp, h_amp):
    layout = best_cyl_layout_accessible(d_tanc, l_tanc, d_amp, h_amp)
    total = int(layout["total"])

    R_tanc = d_tanc / 2.0
    r_amp = d_amp / 2.0
    v_tanc = math.pi * (R_tanc ** 2) * l_tanc
    v_ampolla = math.pi * (r_amp ** 2) * h_amp
    v_ocupat = v_ampolla * total
    perc = (v_ocupat / v_tanc) * 100 if v_tanc > 0 else 0.0

    return total, perc


def stats_rectangular(d_tanc, l_tanc, w_env, d_env, h_env):
    layout = best_rect_layout_accessible(d_tanc, l_tanc, w_env, d_env, h_env)
    total = int(layout["total"])

    R_tanc = d_tanc / 2.0
    v_tanc = math.pi * (R_tanc ** 2) * l_tanc
    v_env = w_env * d_env * h_env
    v_ocupat = v_env * total
    perc = (v_ocupat / v_tanc) * 100 if v_tanc > 0 else 0.0

    return total, perc


# ==========================================================
#   COORDS 3D (centres)
# ==========================================================
def coords_cyl_all(d_tanc, l_tanc, d_amp, h_amp):
    layout = best_cyl_layout_accessible(d_tanc, l_tanc, d_amp, h_amp)
    centres_v = layout["centres_v"]
    centres_h = layout["centres_h"]

    xs, ys, zs, typ = [], [], [], []

    for k in range(layout["v_left_layers"]):
        z = (k * h_amp) + (h_amp / 2.0)
        for (x, y) in centres_v:
            xs.append(x); ys.append(y); zs.append(z); typ.append("V")

    if layout["n_h_layers"] > 0 and layout["h_start"] is not None:
        for j in range(layout["n_h_layers"]):
            z = layout["h_start"] + (d_amp / 2.0) + (j * d_amp)
            for (x, y) in centres_h:
                xs.append(x); ys.append(y); zs.append(z); typ.append("H")

    if layout["n_h_layers"] > 0 and layout["h_end"] is not None:
        base_right = layout["h_end"]
        for k in range(layout["v_right_layers"]):
            z = base_right + (k * h_amp) + (h_amp / 2.0)
            for (x, y) in centres_v:
                xs.append(x); ys.append(y); zs.append(z); typ.append("V")

    return pd.DataFrame({"x": xs, "y": ys, "z": zs, "type": typ})


def coords_rect_all(d_tanc, l_tanc, w_env, d_env, h_env):
    layout = best_rect_layout_accessible(d_tanc, l_tanc, w_env, d_env, h_env)
    centres_v = layout["centres_v"]
    centres_h = layout["centres_h"]

    xs, ys, zs, typ = [], [], [], []

    for k in range(layout["v_left_layers"]):
        z = (k * h_env) + (h_env / 2.0)
        for (x, y) in centres_v:
            xs.append(x); ys.append(y); zs.append(z); typ.append("V")

    if layout["n_h_layers"] > 0 and layout["h_start"] is not None:
        for j in range(layout["n_h_layers"]):
            z = layout["h_start"] + (layout["layer_thickness"] / 2.0) + (j * layout["layer_thickness"])
            for (x, y) in centres_h:
                xs.append(x); ys.append(y); zs.append(z); typ.append(layout["mode"])

    if layout["n_h_layers"] > 0 and layout["h_end"] is not None:
        base_right = layout["h_end"]
        for k in range(layout["v_right_layers"]):
            z = base_right + (k * h_env) + (h_env / 2.0)
            for (x, y) in centres_v:
                xs.append(x); ys.append(y); zs.append(z); typ.append("V")

    return pd.DataFrame({"x": xs, "y": ys, "z": zs, "type": typ})


# ==========================================================
#   OPTIMITZACIÓ MÀQUINA: combinacions FIXES per cicle
# ==========================================================
def fixed_mix_per_cycle(machine_name, vessel_len_mm, cap_L1, cap_L2):
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
        used = k_p * float(L1_MM) + k_g * float(L2_MM)
        if used <= float(vessel_len_mm) and (k_p + k_g) > 0:
            units = int(k_p) * int(cap_L1) + int(k_g) * int(cap_L2)
            rows.append({
                "k_petit": int(k_p),
                "k_gran": int(k_g),
                "contenidors_per_cicle": int(k_p + k_g),
                "unitats_per_cicle": int(units),
            })

    return pd.DataFrame(rows)


def units_last_container_last_cycle(N, k_petit, k_gran, cap_petit, cap_gran):
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


# ==========================================================
#   COST + PLA per màquina (ORDENAT vs RANDOM)
# ==========================================================
def evaluate_machine(
    machine_name: str,
    vessel_len_mm: float,
    nonlab_cost_cycle: float,
    cap_p_ordered: int, cap_g_ordered: int,
    N: int,
    labor_cost_per_hour: float,
    t_per_container_ordered: float,
    t_per_container_random: float,
    t_process_minutes: float,
    density_factor_random: float,
):
    def score_mode(mode: str):
        if mode == "ORDENAT":
            cap_p = int(cap_p_ordered)
            cap_g = int(cap_g_ordered)
            t_cont = float(t_per_container_ordered)
            dens = 1.0
        else:
            cap_p = max(1, int(round(int(cap_p_ordered) * float(density_factor_random))))
            cap_g = max(1, int(round(int(cap_g_ordered) * float(density_factor_random))))
            t_cont = float(t_per_container_random)
            dens = float(density_factor_random)

        mix = fixed_mix_per_cycle(machine_name, vessel_len_mm, cap_p, cap_g)
        if mix is None or mix.empty:
            return None, mix

        rows = []
        for _, r in mix.iterrows():
            kp = int(r["k_petit"])
            kg = int(r["k_gran"])
            cont_per_cycle = int(r["contenidors_per_cicle"])
            u_cycle = int(r["unitats_per_cicle"])
            cycles = int(math.ceil(int(N) / u_cycle)) if u_cycle > 0 else 10**9

            minutes_load_cycle = float(cont_per_cycle) * float(t_cont)
            minutes_total_cycle = minutes_load_cycle + float(t_process_minutes)

            labor_cycle = (minutes_total_cycle / 60.0) * float(labor_cost_per_hour)
            cost_cycle_real = float(nonlab_cost_cycle) + float(labor_cycle)
            cost_total = float(cycles) * cost_cycle_real
            cost_per_unit = cost_total / float(N) if float(N) > 0 else 0.0
            total_order_time_min = float(cycles) * float(minutes_total_cycle)
            total_order_time_h = total_order_time_min / 60.0

            u_last, cap_last, _ = units_last_container_last_cycle(int(N), kp, kg, cap_p, cap_g)

            rows.append({
                "machine": machine_name,
                "mode": mode,
                "density_factor": dens,
                "k_petit": kp,
                "k_gran": kg,
                "containers_per_cycle": cont_per_cycle,
                "units_per_cycle": u_cycle,
                "cycles": cycles,
                "minutes_total_per_cycle": minutes_total_cycle,
                "labor_eur_per_cycle": labor_cycle,
                "real_eur_per_cycle": cost_cycle_real,
                "total_cost": cost_total,
                "cost_per_unit": cost_per_unit,
                "total_order_time_min": total_order_time_min,
                "total_order_time_h": total_order_time_h,
                "cap_p_used": cap_p,
                "cap_g_used": cap_g,
                "last_container_units": u_last,
                "last_container_cap": cap_last,
            })

        df = pd.DataFrame(rows).sort_values(
            by=["total_cost", "cycles", "units_per_cycle"],
            ascending=[True, True, False],
            kind="mergesort"
        ).reset_index(drop=True)

        return df.iloc[0].to_dict(), df

    best_ord, df_ord = score_mode("ORDENAT")
    best_rnd, df_rnd = score_mode("RANDOM")
    return best_ord, df_ord, best_rnd, df_rnd


# ==========================================================
# 3D HELPERS (mesh + wireframe)
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
st.title("HPP Load Planner — ORDENAT vs RANDOM")

with st.sidebar:
    st.header("Inputs generals")
    N = st.number_input("Unitats comanda (N)", min_value=1, value=2000, step=10)
    d_tanc = st.number_input("Diàmetre del tanc (mm)", min_value=1.0, value=380.0, step=1.0)

    st.divider()
    st.header("Tipus d'envàs / producte")
    preset_name = st.selectbox("Preset de producte", list(PRODUCT_PRESETS.keys()))
    preset = PRODUCT_PRESETS[preset_name]

    family = st.selectbox(
        "Família producte",
        ["Sòlid", "Líquid"],
        index=0 if preset["family"] == "Sòlid" else 1
    )

    forma = st.selectbox(
        "Forma producte",
        ["Cilíndric", "Rectangular"],
        index=0 if preset["shape"] == "Cilíndric" else 1
    )

    st.divider()
    st.header("Economia")
    labor_cost_per_hour = st.number_input("Cost mà d'obra (€/hora)", min_value=0.0, value=18.0, step=0.5)

    st.divider()
    st.header("Temps (min)")
    t_ordered = st.number_input("ORDENAT (min/contenidor)", min_value=0.0, value=3.0, step=0.1)
    t_random = st.number_input("RANDOM (min/contenidor)", min_value=0.0, value=2.0, step=0.1)
    t_process = st.number_input("Procés (min/cicle)", min_value=0.0, value=7.5, step=0.1)

    st.divider()
    st.header("Pèrdua densitat (RANDOM)")
    density_factor_random = st.slider("Factor densitat RANDOM", min_value=0.50, max_value=1.00, value=0.85, step=0.01)

    st.divider()
    st.caption("Cost fix sense MOD (€/cicle):")
    st.caption(f"- HIPERBARIC 420: {NONLAB_420:.2f} €/cicle")
    st.caption(f"- HIPERBARIC 525: {NONLAB_525:.2f} €/cicle")

col1, col2 = st.columns([1.15, 0.85])

# ==========================================================
# INPUTS geometria i capacitats ORDENAT
# ==========================================================
if forma == "Cilíndric":
    with col1:
        st.subheader("Paràmetres cilíndrics")
        default_d = preset["d"] if preset["shape"] == "Cilíndric" else 50.0
        default_h = preset["h"] if preset["shape"] == "Cilíndric" else 150.0
        d_amp = st.number_input("Diàmetre envàs (mm)", min_value=0.1, value=float(default_d), step=0.5)
        h_amp = st.number_input("Llarg / alçada envàs (mm)", min_value=0.1, value=float(default_h), step=0.5)

    cap_p, perc_p = stats_cilindric(d_tanc, L1_MM, d_amp, h_amp)
    cap_g, perc_g = stats_cilindric(d_tanc, L2_MM, d_amp, h_amp)

else:
    with col1:
        st.subheader("Paràmetres rectangulars")
        default_w = preset["w"] if preset["shape"] == "Rectangular" else 40.0
        default_depth = preset["depth"] if preset["shape"] == "Rectangular" else 60.0
        default_hz = preset["hz"] if preset["shape"] == "Rectangular" else 150.0

        w_env = st.number_input("Amplada (X) (mm)", min_value=0.1, value=float(default_w), step=0.5)
        d_env = st.number_input("Profunditat (Y) (mm)", min_value=0.1, value=float(default_depth), step=0.5)
        h_env = st.number_input("Llargada / Alçada útil (Z) (mm)", min_value=0.1, value=float(default_hz), step=0.5)

    cap_p, perc_p = stats_rectangular(d_tanc, L1_MM, w_env, d_env, h_env)
    cap_g, perc_g = stats_rectangular(d_tanc, L2_MM, w_env, d_env, h_env)

with col2:
    st.subheader("Lectura ràpida")
    st.write(f"**Preset seleccionat:** {preset_name}")
    st.write(f"**Família:** {family}")
    st.write(f"**Forma:** {forma}")
    st.write("")
    st.subheader("Capacitats (ORDENAT / ideal)")
    st.write(f"**{NAME_L1}** ({int(L1_MM)} mm): **{cap_p} u** | ocupació **{perc_p:.2f}%**")
    st.write(f"**{NAME_L2}** ({int(L2_MM)} mm): **{cap_g} u** | ocupació **{perc_g:.2f}%**")

# ==========================================================
# AVALUACIÓ per màquina
# ==========================================================
name_420 = "HIPERBARIC 420"
name_525 = "HIPERBARIC 525"

best_420_ord, df_420_ord, best_420_rnd, df_420_rnd = evaluate_machine(
    machine_name=name_420,
    vessel_len_mm=LEN_420_MM,
    nonlab_cost_cycle=NONLAB_420,
    cap_p_ordered=int(cap_p),
    cap_g_ordered=int(cap_g),
    N=int(N),
    labor_cost_per_hour=float(labor_cost_per_hour),
    t_per_container_ordered=float(t_ordered),
    t_per_container_random=float(t_random),
    t_process_minutes=float(t_process),
    density_factor_random=float(density_factor_random),
)

best_525_ord, df_525_ord, best_525_rnd, df_525_rnd = evaluate_machine(
    machine_name=name_525,
    vessel_len_mm=LEN_525_MM,
    nonlab_cost_cycle=NONLAB_525,
    cap_p_ordered=int(cap_p),
    cap_g_ordered=int(cap_g),
    N=int(N),
    labor_cost_per_hour=float(labor_cost_per_hour),
    t_per_container_ordered=float(t_ordered),
    t_per_container_random=float(t_random),
    t_process_minutes=float(t_process),
    density_factor_random=float(density_factor_random),
)

candidates = [b for b in [best_420_ord, best_420_rnd, best_525_ord, best_525_rnd] if b is not None]
df_all = pd.DataFrame(candidates)
if df_all.empty:
    st.error("No hi ha cap combinació vàlida amb les restriccions actuals.")
    st.stop()

df_all = df_all.sort_values(
    by=["total_cost", "cycles", "units_per_cycle"],
    ascending=[True, True, False],
    kind="mergesort"
).reset_index(drop=True)

# ==========================================================
# TAULA comparació
# ==========================================================
st.divider()
st.subheader("Comparació completa (totes les opcions)")

df_show = df_all.rename(columns={
    "machine": "Màquina",
    "mode": "Mode",
    "density_factor": "Factor_densitat",
    "k_gran": "k_gran",
    "k_petit": "k_petit",
    "units_per_cycle": "unitats/cicle",
    "cycles": "cicles",
    "minutes_total_per_cycle": "min_total/cicle",
    "labor_eur_per_cycle": "MOD_real_€/cicle",
    "real_eur_per_cycle": "cost_real_€/cicle",
    "total_cost": "cost_total",
    "cost_per_unit": "cost_per_unit",
    "total_order_time_min": "temps_total_comanda_min",
    "total_order_time_h": "temps_total_comanda_h",
    "last_container_units": "ultim_contenidor_ultim_cicle_u",
    "last_container_cap": "ultim_contenidor_cap",
})

st.dataframe(
    df_show[
        [
            "Màquina", "Mode", "Factor_densitat",
            "k_gran", "k_petit",
            "unitats/cicle", "cicles",
            "min_total/cicle", "MOD_real_€/cicle", "cost_real_€/cicle",
            "cost_total", "cost_per_unit",
            "temps_total_comanda_h", "temps_total_comanda_min",
            "ultim_contenidor_ultim_cicle_u", "ultim_contenidor_cap",
        ]
    ],
    use_container_width=True
)

# ==========================================================
# PLA FINAL
# ==========================================================
st.divider()
st.header("✅ Pla de producció FINAL (òptim)")

winner = df_all.iloc[0].to_dict()
second_best = df_all.iloc[1].to_dict() if len(df_all) > 1 else winner

best_cost = float(winner['total_cost'])
second_best_cost = float(second_best['total_cost'])
savings_eur = max(0.0, second_best_cost - best_cost)
savings_pct = (savings_eur / second_best_cost * 100.0) if second_best_cost > 0 else 0.0

st.success(f"Recomanació: **{winner['mode']}** a **{winner['machine']}**")

st.subheader("📊 Quadre executiu")
st.markdown(
    """
    <style>
    .kpi-card {
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 0.6rem;
        padding: 0.65rem 0.75rem;
        background: rgba(250, 250, 250, 0.6);
        min-height: 84px;
    }
    .kpi-label {
        font-size: 0.78rem;
        color: #6b7280;
        margin-bottom: 0.2rem;
        line-height: 1.2;
    }
    .kpi-value {
        font-size: 1.02rem;
        font-weight: 600;
        line-height: 1.25;
        word-break: break-word;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

kpi1, kpi2, kpi3, kpi4, kpi5, kpi6, kpi7 = st.columns([2.0, 1.0, 1.1, 0.9, 1.2, 1.1, 1.4])
with kpi1:
    st.markdown(
        f"""<div class="kpi-card"><div class="kpi-label">Màquina recomanada</div><div class="kpi-value">{str(winner['machine'])}</div></div>""",
        unsafe_allow_html=True,
    )
with kpi2:
    st.markdown(
        f"""<div class="kpi-card"><div class="kpi-label">Mode recomanat</div><div class="kpi-value">{str(winner['mode'])}</div></div>""",
        unsafe_allow_html=True,
    )
with kpi3:
    st.markdown(
        f"""<div class="kpi-card"><div class="kpi-label">Cost total</div><div class="kpi-value">{float(winner['total_cost']):.2f} €</div></div>""",
        unsafe_allow_html=True,
    )
with kpi4:
    st.markdown(
        f"""<div class="kpi-card"><div class="kpi-label">Cicles totals</div><div class="kpi-value">{int(winner['cycles'])}</div></div>""",
        unsafe_allow_html=True,
    )
with kpi5:
    st.markdown(
        f"""<div class="kpi-card"><div class="kpi-label">Cost per unitat</div><div class="kpi-value">{float(winner['cost_per_unit']):.4f} € / unitat</div></div>""",
        unsafe_allow_html=True,
    )
with kpi6:
    st.markdown(
        f"""<div class="kpi-card"><div class="kpi-label">Temps total comanda</div><div class="kpi-value">{float(winner['total_order_time_h']):.2f} h</div></div>""",
        unsafe_allow_html=True,
    )
with kpi7:
    st.markdown(
        f"""<div class="kpi-card"><div class="kpi-label">Estalvi vs alternativa</div><div class="kpi-value">{savings_eur:.2f} € ({savings_pct:.1f}%)</div></div>""",
        unsafe_allow_html=True,
    )

st.markdown(
    f"""
**Resultat**
- **Preset:** {preset_name}  
- **Família:** {family}  
- **Forma:** {forma}  
- **Configuració per cicle:** {int(winner['k_gran'])}×{NAME_L2} + {int(winner['k_petit'])}×{NAME_L1}  
- **Unitats/cicle:** {int(winner['units_per_cycle'])}  
- **Cicles totals:** {int(winner['cycles'])}  
- **Cost fix sense MOD (€/cicle):** {NONLAB_420:.2f} (H420) | {NONLAB_525:.2f} (H525)  
- **Cost mà d'obra (€/hora):** {float(labor_cost_per_hour):.2f} €/h  
- **Temps procés (min/cicle):** {float(t_process):.2f} min  
- **Temps total/cicle (càrrega + procés):** {float(winner['minutes_total_per_cycle']):.2f} min  
- **MOD real €/cicle:** {float(winner['labor_eur_per_cycle']):.2f} €  
- **Cost real €/cicle:** {float(winner['real_eur_per_cycle']):.2f} €  
- **Cost total:** **{float(winner['total_cost']):.2f} €**  
- **Cost per unitat:** **{float(winner['cost_per_unit']):.4f} € / unitat**  
- **Temps total comanda:** **{float(winner['total_order_time_h']):.2f} h** ({float(winner['total_order_time_min']):.2f} min)  
- **Últim contenidor (últim cicle):** {int(winner['last_container_units'])} u (cap {int(winner['last_container_cap'])})
"""
)

st.info(
    f"La configuració recomanada redueix el cost en {savings_eur:.2f} € ({savings_pct:.1f}%) respecte la segona millor opció."
)

# ==========================================================
# 3D només si guanya ORDENAT
# ==========================================================
if str(winner["mode"]) == "ORDENAT":
    st.subheader("3D (només si la recomanació és ORDENAT) — disposició dins dels contenidors")
    st.caption("La disposició 3D mostra la configuració que maximitza la capacitat.")

    cA, cB = st.columns(2)
    if forma == "Cilíndric":
        with cA:
            render_3d_cyl(f"{NAME_L1} ({int(L1_MM)} mm)", d_tanc, L1_MM, d_amp, h_amp, units_in_container=int(cap_p))
        with cB:
            render_3d_cyl(f"{NAME_L2} ({int(L2_MM)} mm)", d_tanc, L2_MM, d_amp, h_amp, units_in_container=int(cap_g))
    else:
        with cA:
            render_3d_rect(f"{NAME_L1} ({int(L1_MM)} mm)", d_tanc, L1_MM, w_env, d_env, h_env, units_in_container=int(cap_p))
        with cB:
            render_3d_rect(f"{NAME_L2} ({int(L2_MM)} mm)", d_tanc, L2_MM, w_env, d_env, h_env, units_in_container=int(cap_g))
else:
    st.info("Mode recomanat = RANDOM → no mostrem animació 3D (segons criteri del projecte).")

# ==========================================================
# EXPORTS
# ==========================================================
st.divider()
st.subheader("Descarregar pla de producció")

payload = {
    "inputs": {
        "N": int(N),
        "d_tanc_mm": float(d_tanc),
        "preset": preset_name,
        "family": family,
        "forma": forma,
        "labor_cost_per_hour": float(labor_cost_per_hour),
        "t_ordered_min_per_container": float(t_ordered),
        "t_random_min_per_container": float(t_random),
        "t_process_min_per_cycle": float(t_process),
        "density_factor_random": float(density_factor_random),
    },
    "cost_fix_sense_MOD": {
        "HIPERBARIC 420": float(NONLAB_420),
        "HIPERBARIC 525": float(NONLAB_525),
    },
    "capacitats_ordenat": {
        "petit": {"length_mm": float(L1_MM), "cap_unitats": int(cap_p), "ocupacio_pct": float(perc_p)},
        "gran":  {"length_mm": float(L2_MM), "cap_unitats": int(cap_g), "ocupacio_pct": float(perc_g)},
    },
    "comparacio": df_show.to_dict(orient="records"),
    "pla_final": winner,
    "total_order_time_min": float(winner["total_order_time_min"]),
    "total_order_time_h": float(winner["total_order_time_h"]),
}

plan_txt = []
plan_txt.append("HPP LOAD PLANNER — PLA DE PRODUCCIÓ FINAL")
plan_txt.append("")
plan_txt.append(f"N = {int(N)}")
plan_txt.append(f"Diàmetre tanc = {float(d_tanc):.1f} mm")
plan_txt.append(f"Preset = {preset_name}")
plan_txt.append(f"Família = {family}")
plan_txt.append(f"Forma = {forma}")
plan_txt.append("")
plan_txt.append(f"Cost fix sense MOD (€/cicle): H420={NONLAB_420:.2f} | H525={NONLAB_525:.2f}")
plan_txt.append(f"Cost mà d'obra = {float(labor_cost_per_hour):.2f} €/hora")
plan_txt.append(f"Temps ORDENAT = {float(t_ordered):.2f} min/contenidor")
plan_txt.append(f"Temps RANDOM  = {float(t_random):.2f} min/contenidor")
plan_txt.append(f"Temps PROCÉS  = {float(t_process):.2f} min/cicle")
plan_txt.append(f"Factor densitat RANDOM = {float(density_factor_random):.2f}")
plan_txt.append("")
plan_txt.append("CAPACITATS ORDENAT:")
plan_txt.append(f"- {NAME_L1}: {int(cap_p)} u (ocupació {float(perc_p):.2f}%)")
plan_txt.append(f"- {NAME_L2}: {int(cap_g)} u (ocupació {float(perc_g):.2f}%)")
plan_txt.append("")
plan_txt.append("PLA FINAL:")
plan_txt.append(f"- Màquina: {winner['machine']}")
plan_txt.append(f"- Mode: {winner['mode']}")
plan_txt.append(f"- Configuració/cicle: {int(winner['k_gran'])}×{NAME_L2} + {int(winner['k_petit'])}×{NAME_L1}")
plan_txt.append(f"- Unitats/cicle: {int(winner['units_per_cycle'])}")
plan_txt.append(f"- Cicles: {int(winner['cycles'])}")
plan_txt.append(f"- Temps total/cicle (càrrega + procés): {float(winner['minutes_total_per_cycle']):.2f} min")
plan_txt.append(f"- MOD real €/cicle: {float(winner['labor_eur_per_cycle']):.2f}")
plan_txt.append(f"- Cost real €/cicle: {float(winner['real_eur_per_cycle']):.2f}")
plan_txt.append(f"- Cost total: {float(winner['total_cost']):.2f}")
plan_txt.append(f"- Cost per unitat: {float(winner['cost_per_unit']):.4f} € / unitat")
plan_txt.append(f"- Temps total comanda: {float(winner['total_order_time_h']):.2f} h ({float(winner['total_order_time_min']):.2f} min)")
plan_txt.append(f"- Últim contenidor últim cicle: {int(winner['last_container_units'])} u (cap {int(winner['last_container_cap'])})")
plan_txt = "\n".join(plan_txt)

c1, c2 = st.columns(2)
with c1:
    st.download_button(
        "⬇️ Descarregar pla de producció (TXT)",
        data=plan_txt,
        file_name="hpp_pla_produccio_final.txt",
        mime="text/plain"
    )
with c2:
    st.download_button(
        "⬇️ Descarregar dades (JSON)",
        data=json.dumps(payload, indent=2, ensure_ascii=False),
        file_name="hpp_pla_produccio_final.json",
        mime="application/json"
    )
