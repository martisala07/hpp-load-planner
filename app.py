import math
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="HPP Load Planner — 3D solids", layout="wide")

# =========================
# CONFIG CONTENIDORS (mm)
# =========================
L1_MM = 880.0
L2_MM = 1190.0

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
#        STATS + BREAKDOWN (capes, unitats/capa, etc.)
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

    centres_v, angle_v = genera_rectangular_optimitzat(R_tanc, w_env, d_env)
    per_layer = len(centres_v)
    layers = math.floor(l_tanc / h_env)
    total_verticals = per_layer * layers

    h_restant = l_tanc - (layers * h_env)

    capes_a = int(math.floor(h_restant / w_env))
    centres_a, angle_a = genera_rectangular_optimitzat(R_tanc, h_env, d_env) if capes_a > 0 else ([], 0)
    total_a = capes_a * len(centres_a)

    capes_b = int(math.floor(h_restant / d_env))
    centres_b, angle_b = genera_rectangular_optimitzat(R_tanc, w_env, h_env) if capes_b > 0 else ([], 0)
    total_b = capes_b * len(centres_b)

    total_tombades = total_a if total_a >= total_b else total_b
    total = int(total_verticals + total_tombades)

    v_tanc = math.pi * (R_tanc ** 2) * l_tanc
    v_env = w_env * d_env * h_env
    v_ocupat = v_env * total
    perc = (v_ocupat / v_tanc) * 100 if v_tanc > 0 else 0

    return total, perc


def breakdown_cilindric(d_tanc, l_tanc, d_amp, h_amp):
    R_tanc = d_tanc / 2.0
    r_amp = d_amp / 2.0

    centres_v = genera_hexagonal_optimitzat(R_tanc, r_amp)
    per_layer_v = len(centres_v)

    layers_v = int(math.floor(l_tanc / h_amp))
    total_v = per_layer_v * layers_v

    h_restant = l_tanc - layers_v * h_amp

    layers_h = int(math.floor(h_restant / d_amp))
    per_layer_h = 0
    total_h = 0
    if layers_h > 0:
        centres_h = genera_horizontals(R_tanc, h_amp, d_amp)
        per_layer_h = len(centres_h)
        total_h = per_layer_h * layers_h

    total = int(total_v + total_h)

    rows = []
    for k in range(layers_v):
        rows.append({"capa": k + 1, "tipus": "Vertical", "unitats": per_layer_v, "altura_unitat_mm": h_amp})
    for k in range(layers_h):
        rows.append({"capa": layers_v + k + 1, "tipus": "Tombada", "unitats": per_layer_h, "altura_unitat_mm": d_amp})

    df_layers = pd.DataFrame(rows)

    return {
        "per_layer_vertical": int(per_layer_v),
        "layers_vertical": int(layers_v),
        "total_vertical": int(total_v),
        "h_restant_mm": float(h_restant),
        "per_layer_tombada": int(per_layer_h),
        "layers_tombades": int(layers_h),
        "total_tombades": int(total_h),
        "total": int(total),
        "df_layers": df_layers,
    }


def breakdown_rectangular(d_tanc, l_tanc, w_env, d_env, h_env):
    R_tanc = d_tanc / 2.0

    centres_v, angle_v = genera_rectangular_optimitzat(R_tanc, w_env, d_env)
    per_layer_v = len(centres_v)

    layers_v = int(math.floor(l_tanc / h_env))
    total_v = per_layer_v * layers_v
    h_restant = l_tanc - layers_v * h_env

    layers_a = int(math.floor(h_restant / w_env))
    per_layer_a = 0
    total_a = 0
    angle_a = 0
    if layers_a > 0:
        centres_a, angle_a = genera_rectangular_optimitzat(R_tanc, h_env, d_env)
        per_layer_a = len(centres_a)
        total_a = per_layer_a * layers_a

    layers_b = int(math.floor(h_restant / d_env))
    per_layer_b = 0
    total_b = 0
    angle_b = 0
    if layers_b > 0:
        centres_b, angle_b = genera_rectangular_optimitzat(R_tanc, w_env, h_env)
        per_layer_b = len(centres_b)
        total_b = per_layer_b * layers_b

    if total_a >= total_b and total_a > 0:
        chosen = "A"
        layers_h = layers_a
        per_layer_h = per_layer_a
        total_h = total_a
        altura_capa_h = w_env
        angle_h = angle_a
    elif total_b > 0:
        chosen = "B"
        layers_h = layers_b
        per_layer_h = per_layer_b
        total_h = total_b
        altura_capa_h = d_env
        angle_h = angle_b
    else:
        chosen = "-"
        layers_h = 0
        per_layer_h = 0
        total_h = 0
        altura_capa_h = 0
        angle_h = 0

    total = int(total_v + total_h)

    rows = []
    for k in range(layers_v):
        rows.append({"capa": k + 1, "tipus": "Vertical", "unitats": per_layer_v, "altura_unitat_mm": h_env})
    for k in range(layers_h):
        rows.append({"capa": layers_v + k + 1, "tipus": f"Tombada_{chosen}", "unitats": per_layer_h, "altura_unitat_mm": altura_capa_h})

    df_layers = pd.DataFrame(rows)

    return {
        "per_layer_vertical": int(per_layer_v),
        "layers_vertical": int(layers_v),
        "total_vertical": int(total_v),
        "h_restant_mm": float(h_restant),
        "tombada_mode": chosen,
        "per_layer_tombada": int(per_layer_h),
        "layers_tombades": int(layers_h),
        "total_tombades": int(total_h),
        "angle_vertical_rad": float(angle_v),
        "angle_tombada_rad": float(angle_h),
        "total": int(total),
        "df_layers": df_layers,
    }


# ==========================================================
#                 DECISIÓ CONTENIDOR
# ==========================================================
def decideix_millor(N, cap1, perc1, cap2, perc2, nom1="L1", nom2="L2"):
    cont1 = math.ceil(N / cap1) if cap1 > 0 else 10 ** 9
    cont2 = math.ceil(N / cap2) if cap2 > 0 else 10 ** 9
    buit1 = cont1 * cap1 - N
    buit2 = cont2 * cap2 - N

    if cont1 < cont2:
        best = nom1
    elif cont2 < cont1:
        best = nom2
    else:
        if buit1 < buit2:
            best = nom1
        elif buit2 < buit1:
            best = nom2
        else:
            if perc1 > perc2:
                best = nom1
            elif perc2 > perc1:
                best = nom2
            else:
                best = nom1 if cap1 >= cap2 else nom2

    return {
        "best": best,
        "contenidors": {nom1: cont1, nom2: cont2},
        "buit": {nom1: buit1, nom2: buit2},
    }


# ==========================================================
#         COORDS 3D segons la teva lògica (centres)
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
            xs.append(x)
            ys.append(y)
            zs.append(z)
            typ.append("V")

    h_restant = l_tanc - (layers_v * h_amp)
    capes_tombades = int(math.floor(h_restant / d_amp))
    if capes_tombades > 0:
        centres_h = genera_horizontals(R_tanc, h_amp, d_amp)
        for capa in range(capes_tombades):
            z = (layers_v * h_amp) + r_amp + (capa * d_amp)
            for (x, y) in centres_h:
                xs.append(x)
                ys.append(y)
                zs.append(z)
                typ.append("H")

    return pd.DataFrame({"x": xs, "y": ys, "z": zs, "type": typ})


def coords_rect_all(d_tanc, l_tanc, w_env, d_env, h_env):
    R_tanc = d_tanc / 2.0

    centres_v, _ = genera_rectangular_optimitzat(R_tanc, w_env, d_env)
    layers_v = math.floor(l_tanc / h_env)

    xs, ys, zs, typ = [], [], [], []

    for k in range(layers_v):
        z = (k * h_env) + (h_env / 2.0)
        for (x, y) in centres_v:
            xs.append(x)
            ys.append(y)
            zs.append(z)
            typ.append("V")

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
                xs.append(x)
                ys.append(y)
                zs.append(z)
                typ.append("A")
    elif total_b > 0:
        for capa in range(capes_b):
            z = z_base + (capa * d_env) + (d_env / 2.0)
            for (x, y) in centres_b:
                xs.append(x)
                ys.append(y)
                zs.append(z)
                typ.append("B")

    return pd.DataFrame({"x": xs, "y": ys, "z": zs, "type": typ})


# ==========================================================
#     Mesh builders: cilindres i prismes COMBINATS
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
        (0, 1, 2),
        (0, 2, 3),
        (4, 6, 5),
        (4, 7, 6),
        (0, 5, 1),
        (0, 4, 5),
        (3, 2, 6),
        (3, 6, 7),
        (0, 3, 7),
        (0, 7, 4),
        (1, 5, 6),
        (1, 6, 2),
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
    v = np.array(vertices, dtype=float)
    f = np.array(faces, dtype=int)
    return v, f


def mesh_from_cylinders(centers_xyz, radius, length, axis, nseg, caps=True):
    vertices = []
    faces = []
    for (x, y, z) in centers_xyz:
        add_cylinder_mesh(vertices, faces, (x, y, z), radius, length, axis=axis, nseg=nseg, caps=caps)
    v = np.array(vertices, dtype=float)
    f = np.array(faces, dtype=int)
    return v, f


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
    fig.add_trace(
        go.Mesh3d(
            x=v[:, 0],
            y=v[:, 1],
            z=v[:, 2],
            i=f[:, 0],
            j=f[:, 1],
            k=f[:, 2],
            opacity=opacity,
            name=name,
            hoverinfo="skip",
            flatshading=True,
        )
    )


# ==========================================================
# UI
# ==========================================================
st.title("HPP Load Planner — Matemàtica Fusion + 3D (prismes i cilindres)")

with st.sidebar:
    st.header("Inputs")
    N = st.number_input("Unitats comanda (N)", min_value=1, value=2000, step=10)
    d_tanc = st.number_input("Diàmetre del tanc (mm)", min_value=1.0, value=360.0, step=1.0)

    forma = st.selectbox("Forma producte", ["Cilíndric", "Rectangular"])

    st.subheader("3D Quality / Performance")
    cyl_segments = st.slider("Segments cilindre (més = més bonic, més lent)", 8, 24, 12, 1)
    caps = st.checkbox("Tancar cilindres (caps)", value=True)

    st.subheader("Costos (opcional)")
    cost_per_cycle = st.number_input("Cost per cicle (€)", min_value=0.0, value=63.0, step=1.0)
    containers_per_cycle = st.number_input("Contenidors per cicle", min_value=1, value=2, step=1)

col1, col2 = st.columns([1.2, 1.0])

if forma == "Cilíndric":
    with col1:
        st.subheader("Paràmetres cilíndric")
        d_amp = st.number_input("Diàmetre ampolla (mm)", min_value=0.1, value=50.0, step=0.5)
        h_amp = st.number_input("Alçada ampolla (mm)", min_value=0.1, value=150.0, step=0.5)

    cap1, perc1 = stats_cilindric(d_tanc, L1_MM, d_amp, h_amp)
    cap2, perc2 = stats_cilindric(d_tanc, L2_MM, d_amp, h_amp)
    dec = decideix_millor(int(N), cap1, perc1, cap2, perc2, "L1", "L2")

    bestL = L1_MM if dec["best"] == "L1" else L2_MM
    bestCap = cap1 if bestL == L1_MM else cap2
    bestCont = dec["contenidors"][dec["best"]]
    unitats_ultim = int(N - (bestCont - 1) * bestCap) if bestCont > 1 else int(N)

    break_best = breakdown_cilindric(d_tanc, bestL, d_amp, h_amp)

    with col2:
        st.subheader("Resultat")
        st.write(
            f"**L1** ({int(L1_MM)} mm): cap **{cap1}** u | ocupat **{perc1:.2f}%** | contenidors **{dec['contenidors']['L1']}** | buit últim **{dec['buit']['L1']}** u"
        )
        st.write(
            f"**L2** ({int(L2_MM)} mm): cap **{cap2}** u | ocupat **{perc2:.2f}%** | contenidors **{dec['contenidors']['L2']}** | buit últim **{dec['buit']['L2']}** u"
        )
        st.success(f"✅ Millor opció: **{dec['best']}**  ({int(bestL)} mm)")
        st.write(f"Unitats a l’últim contenidor: **{unitats_ultim}**")

        cycles = math.ceil(bestCont / containers_per_cycle)
        st.write(f"Cicles (si {containers_per_cycle} contenidors/cicle): **{cycles}**  → Cost: **{cycles * cost_per_cycle:.2f} €**")

        st.markdown("### Desglossament per capes (millor contenidor)")
        st.write(f"Unitats per capa (vertical): **{break_best['per_layer_vertical']}**")
        st.write(
            f"Capes verticals: **{break_best['layers_vertical']}** → Total vertical: **{break_best['total_vertical']}**"
        )
        st.write(f"Alçada restant: **{break_best['h_restant_mm']:.1f} mm**")

        if break_best["layers_tombades"] > 0:
            st.write(f"Unitats per capa (tombada): **{break_best['per_layer_tombada']}**")
            st.write(
                f"Capes tombades: **{break_best['layers_tombades']}** → Total tombat: **{break_best['total_tombades']}**"
            )
        else:
            st.write("Capes tombades: **0**")

        st.write(f"**Total unitats dins el contenidor:** {break_best['total']}")

        with st.expander("Veure taula capa per capa"):
            st.dataframe(break_best["df_layers"], use_container_width=True)

    st.markdown("---")
    st.subheader("3D — Cilindres (totes les capes, verticals + tombades)")

    df = coords_cyl_all(d_tanc, bestL, d_amp, h_amp)
    n_total = len(df)

    tri_per_cyl = (2 * cyl_segments) + (2 * cyl_segments if caps else 0)
    tri_est = n_total * tri_per_cyl

    if tri_est > 2_000_000:
        st.warning(
            f"Aquest cas és molt pesat (estimació ~{tri_est:,} triangles). "
            "Si va lent: baixa 'Segments cilindre' a 8–10."
        )

    v_centers = df[df["type"] == "V"][["x", "y", "z"]].to_numpy()
    h_centers = df[df["type"] == "H"][["x", "y", "z"]].to_numpy()

    fig = go.Figure()

    X, Y, Z = tank_surface(d_tanc, bestL)
    fig.add_trace(go.Surface(x=X, y=Y, z=Z, opacity=0.08, showscale=False, hoverinfo="skip", name="Tank"))

    r = d_amp / 2.0
    if len(v_centers) > 0:
        vmesh, vfaces = mesh_from_cylinders(
            v_centers, radius=r, length=h_amp, axis="Z", nseg=cyl_segments, caps=caps
        )
        add_mesh_trace(fig, vmesh, vfaces, "Vertical", opacity=1.0)

    if len(h_centers) > 0:
        hmesh, hfaces = mesh_from_cylinders(
            h_centers, radius=r, length=h_amp, axis="X", nseg=cyl_segments, caps=caps
        )
        add_mesh_trace(fig, hmesh, hfaces, "Horizontal", opacity=1.0)

    fig.update_layout(
        scene=dict(xaxis_title="X (mm)", yaxis_title="Y (mm)", zaxis_title="Z (mm)", aspectmode="data"),
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=True,
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    with col1:
        st.subheader("Paràmetres rectangular")
        w_env = st.number_input("Amplada (X) (mm)", min_value=0.1, value=40.0, step=0.5)
        d_env = st.number_input("Profunditat (Y) (mm)", min_value=0.1, value=60.0, step=0.5)
        h_env = st.number_input("Alçada (Z) (mm)", min_value=0.1, value=150.0, step=0.5)

    cap1, perc1 = stats_rectangular(d_tanc, L1_MM, w_env, d_env, h_env)
    cap2, perc2 = stats_rectangular(d_tanc, L2_MM, w_env, d_env, h_env)
    dec = decideix_millor(int(N), cap1, perc1, cap2, perc2, "L1", "L2")

    bestL = L1_MM if dec["best"] == "L1" else L2_MM
    bestCap = cap1 if bestL == L1_MM else cap2
    bestCont = dec["contenidors"][dec["best"]]
    unitats_ultim = int(N - (bestCont - 1) * bestCap) if bestCont > 1 else int(N)

    break_best = breakdown_rectangular(d_tanc, bestL, w_env, d_env, h_env)

    with col2:
        st.subheader("Resultat")
        st.write(
            f"**L1** ({int(L1_MM)} mm): cap **{cap1}** u | ocupat **{perc1:.2f}%** | contenidors **{dec['contenidors']['L1']}** | buit últim **{dec['buit']['L1']}** u"
        )
        st.write(
            f"**L2** ({int(L2_MM)} mm): cap **{cap2}** u | ocupat **{perc2:.2f}%** | contenidors **{dec['contenidors']['L2']}** | buit últim **{dec['buit']['L2']}** u"
        )
        st.success(f"✅ Millor opció: **{dec['best']}**  ({int(bestL)} mm)")
        st.write(f"Unitats a l’últim contenidor: **{unitats_ultim}**")

        cycles = math.ceil(bestCont / containers_per_cycle)
        st.write(f"Cicles (si {containers_per_cycle} contenidors/cicle): **{cycles}**  → Cost: **{cycles * cost_per_cycle:.2f} €**")

        st.markdown("### Desglossament per capes (millor contenidor)")
        st.write(f"Unitats per capa (vertical): **{break_best['per_layer_vertical']}**")
        st.write(
            f"Capes verticals: **{break_best['layers_vertical']}** → Total vertical: **{break_best['total_vertical']}**"
        )
        st.write(f"Alçada restant: **{break_best['h_restant_mm']:.1f} mm**")

        if break_best["layers_tombades"] > 0:
            st.write(f"Mode tombat triat: **{break_best['tombada_mode']}**")
            st.write(f"Unitats per capa (tombada): **{break_best['per_layer_tombada']}**")
            st.write(
                f"Capes tombades: **{break_best['layers_tombades']}** → Total tombat: **{break_best['total_tombades']}**"
            )
        else:
            st.write("Capes tombades: **0**")

        st.write(f"**Total unitats dins el contenidor:** {break_best['total']}")

        with st.expander("Veure taula capa per capa"):
            st.dataframe(break_best["df_layers"], use_container_width=True)

    st.markdown("---")
    st.subheader("3D — Prismes (totes les capes, verticals + tombats A/B)")

    df = coords_rect_all(d_tanc, bestL, w_env, d_env, h_env)

    v_centers = df[df["type"] == "V"][["x", "y", "z"]].to_numpy()
    a_centers = df[df["type"] == "A"][["x", "y", "z"]].to_numpy()
    b_centers = df[df["type"] == "B"][["x", "y", "z"]].to_numpy()

    tri_est = (len(v_centers) + len(a_centers) + len(b_centers)) * 12
    if tri_est > 1_500_000:
        st.warning(
            f"Aquest cas és pesat (estimació ~{tri_est:,} triangles). "
            "Si va lent, et puc afegir un 'LOD' automàtic (però continuar veient-ho tot)."
        )

    fig = go.Figure()
    X, Y, Z = tank_surface(d_tanc, bestL)
    fig.add_trace(go.Surface(x=X, y=Y, z=Z, opacity=0.08, showscale=False, hoverinfo="skip", name="Tank"))

    if len(v_centers) > 0:
        vmesh, vfaces = mesh_from_boxes(v_centers, sx=w_env, sy=d_env, sz=h_env)
        add_mesh_trace(fig, vmesh, vfaces, "Vertical", opacity=1.0)

    if len(a_centers) > 0:
        amesh, afaces = mesh_from_boxes(a_centers, sx=h_env, sy=d_env, sz=w_env)
        add_mesh_trace(fig, amesh, afaces, "Horizontal_A", opacity=1.0)

    if len(b_centers) > 0:
        bmesh, bfaces = mesh_from_boxes(b_centers, sx=w_env, sy=h_env, sz=d_env)
        add_mesh_trace(fig, bmesh, bfaces, "Horizontal_B", opacity=1.0)

    fig.update_layout(
        scene=dict(xaxis_title="X (mm)", yaxis_title="Y (mm)", zaxis_title="Z (mm)", aspectmode="data"),
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)
