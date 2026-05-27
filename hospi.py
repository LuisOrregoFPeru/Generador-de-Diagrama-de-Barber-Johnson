import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Diagrama de Barber & Johnson",
    page_icon="🏥",
    layout="wide",
)

# ── Paleta de colores ──────────────────────────────────────────────────────────
PAL = [
    "#1a5fa8","#0f6e52","#c44a1e","#6b5acd",
    "#b84470","#3d7a3d","#9a6800","#1a7a8a","#7a3020","#3a5a9a",
]

# ── Datasets de ejemplo ────────────────────────────────────────────────────────
EJEMPLOS = {
    "Febreros HURH": pd.DataFrame([
        {"Etiqueta":"Feb-08","CF":520,"A":1945,"E":15404,"D":29},
        {"Etiqueta":"Feb-15","CF":590,"A":2059,"E":13516,"D":28},
        {"Etiqueta":"Feb-16","CF":563,"A":2100,"E":13664,"D":29},
        {"Etiqueta":"Feb-17","CF":598,"A":2111,"E":13700,"D":28},
    ]),
    "Servicios HURH": pd.DataFrame([
        {"Etiqueta":"MIR","CF":80,"A":257,"E":2220,"D":28},
        {"Etiqueta":"NML","CF":35,"A":133,"E":1019,"D":28},
        {"Etiqueta":"DIG","CF":45,"A":196,"E":1158,"D":28},
        {"Etiqueta":"URO","CF":40,"A":191,"E":1363,"D":28},
        {"Etiqueta":"NRL","CF":50,"A":161,"E":1459,"D":28},
    ]),
}

# ── Funciones de cálculo ───────────────────────────────────────────────────────
def calcular(row):
    try:
        A, CF, E, D = float(row["A"]), float(row["CF"]), float(row["E"]), float(row["D"])
        if A <= 0 or CF <= 0 or E <= 0 or D <= 0:
            return None
        return {"EM": E/A, "IO": (E/(CF*D))*100, "IS": (D*CF-E)/A, "IR": A/CF}
    except Exception:
        return None

def zona(io, io_min, io_max):
    if io > 100:   return "Sobreocupación", "🔴", "#a33218"
    if io > io_max: return f"Alta (>{io_max}%)", "🟡", "#7a4808"
    if io < io_min: return f"Baja (<{io_min}%)", "🟡", "#7a4808"
    return "Zona óptima ✓", "🟢", "#0f6e52"

# ── Construcción del diagrama Plotly ──────────────────────────────────────────
def build_figure(df, hospital, io_min, io_max, em_min_opt, em_max_opt, is_ax_min, is_ax_max):
    validos = [calcular(r) for _, r in df.iterrows()]
    validos = [c for c in validos if c]
    em_max_ax = max(
        em_max_opt * 1.4,
        max((c["EM"] for c in validos), default=0) * 1.2,
        12,
    )

    fig = go.Figure()

    # Zona sobreocupación (IS < 0)
    if is_ax_min < 0:
        fig.add_shape(
            type="rect", layer="below",
            x0=is_ax_min, y0=0, x1=0, y1=em_max_ax,
            fillcolor="rgba(195,65,25,0.06)", line_width=0,
        )
        fig.add_annotation(
            x=min(-0.1, is_ax_min*0.1), y=em_max_ax * 0.04,
            text="← Sobreocupación (IS < 0)", showarrow=False,
            font=dict(size=9, color="rgba(120,30,15,0.55)"), xanchor="right",
        )

    # Isolíneas de %IO
    em_arr = np.linspace(0, em_max_ax, 400)
    for io in [60,65,70,75,80,85,90,95,100,110,120,130]:
        k = (100 - io) / io
        is_arr = em_arr * k
        mask = (is_arr >= is_ax_min) & (is_arr <= is_ax_max)
        if not mask.any():
            continue
        is_p = np.where(mask, is_arr, np.nan)
        em_p = np.where(mask, em_arr, np.nan)

        is_opt  = (io == io_min or io == io_max)
        is_over = io > 100
        is_100  = io == 100

        color = (
            "rgba(15,110,82,0.78)"  if is_opt  else
            "rgba(160,50,24,0.50)"  if is_over else
            "rgba(0,0,0,0.35)"      if is_100  else
            "rgba(0,0,0,0.09)"
        )
        width = 1.6 if is_opt else (1.2 if is_100 else 0.7)
        dash  = "solid" if (is_opt or is_100) else "dot"

        fig.add_trace(go.Scatter(
            x=is_p, y=em_p, mode="lines",
            line=dict(color=color, width=width, dash=dash),
            showlegend=False, hoverinfo="skip",
        ))
        # Etiqueta al final de la isolínea
        idx_valid = np.where(mask)[0]
        if len(idx_valid):
            lx, ly = is_arr[idx_valid[-1]], em_arr[idx_valid[-1]]
            if lx < is_ax_max - 0.2 and ly > 0.3:
                fig.add_annotation(
                    x=lx, y=ly, text=f"{io}%", showarrow=False,
                    xanchor="left", xshift=4,
                    font=dict(size=10, color=color, family="monospace"),
                )

    # Isolíneas de IR
    ref_d = float(df.iloc[0]["D"]) if len(df) > 0 else 30
    for ir in [2.5, 3, 3.5, 4, 4.5, 5, 6]:
        S = ref_d / ir
        pts = []
        for is_v in [is_ax_min, is_ax_max]:
            em_v = S - is_v
            if 0 <= em_v <= em_max_ax:
                pts.append((is_v, em_v))
        for em_v in [0, em_max_ax]:
            is_v = S - em_v
            if is_ax_min <= is_v <= is_ax_max:
                pts.append((is_v, em_v))
        pts = sorted(set((round(x,4), round(y,4)) for x,y in pts), key=lambda p: p[1])
        if len(pts) >= 2:
            fig.add_trace(go.Scatter(
                x=[p[0] for p in pts], y=[p[1] for p in pts],
                mode="lines",
                line=dict(color="rgba(88,88,82,0.28)", width=0.7, dash="dash"),
                showlegend=False, hoverinfo="skip",
            ))
            mx = (pts[0][0]+pts[-1][0])/2
            my = (pts[0][1]+pts[-1][1])/2
            if is_ax_min+0.3 < mx < is_ax_max-0.3 and 0.4 < my < em_max_ax-0.5:
                fig.add_annotation(
                    x=mx, y=my, text=f"IR={ir}", showarrow=False,
                    xshift=5, yshift=-3,
                    font=dict(size=10, color="rgba(100,100,95,0.85)", family="monospace"),
                )

    # Zona óptima
    oz = [
        (em_min_opt*(100-io_min)/io_min, em_min_opt),
        (em_min_opt*(100-io_max)/io_max, em_min_opt),
        (em_max_opt*(100-io_max)/io_max, em_max_opt),
        (em_max_opt*(100-io_min)/io_min, em_max_opt),
    ]
    oz = [(x,y) for x,y in oz if is_ax_min<=x<=is_ax_max and 0<=y<=em_max_ax]
    if len(oz) >= 3:
        oz_x = [p[0] for p in oz] + [oz[0][0]]
        oz_y = [p[1] for p in oz] + [oz[0][1]]
        cx = sum(p[0] for p in oz)/len(oz)
        cy = sum(p[1] for p in oz)/len(oz)
        fig.add_trace(go.Scatter(
            x=oz_x, y=oz_y, mode="lines", fill="toself",
            fillcolor="rgba(15,110,82,0.10)",
            line=dict(color="rgba(15,110,82,0.55)", width=1.2, dash="dash"),
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_annotation(
            x=cx, y=cy, text="Zona óptima", showarrow=False,
            font=dict(size=11, color="rgba(10,77,57,0.80)", family="sans-serif"),
            xanchor="center",
        )

    # Puntos de datos
    for i, (_, row) in enumerate(df.iterrows()):
        c = calcular(row)
        if c is None:
            continue
        color  = PAL[i % len(PAL)]
        label  = str(row["Etiqueta"]) or f"P{i+1}"
        z_label, _, _ = zona(c["IO"], io_min, io_max)
        mid_is = (is_ax_min + is_ax_max) / 2
        tpos   = "middle right" if c["IS"] <= mid_is else "middle left"

        fig.add_trace(go.Scatter(
            x=[c["IS"]], y=[c["EM"]],
            mode="markers+text",
            marker=dict(size=14, color=color, line=dict(color="white", width=1.8)),
            text=[label],
            textposition=tpos,
            textfont=dict(size=12, family="sans-serif", color="#1a1a18"),
            name=label,
            customdata=[[
                round(c["IO"],2), round(c["EM"],2),
                round(c["IS"],2), round(c["IR"],2),
                row["CF"], z_label
            ]],
            hovertemplate=(
                f"<b>{label}</b><br>"
                "%%IO: %{customdata[0]:.2f}%% — %{customdata[5]}<br>"
                "EM: %{customdata[1]:.2f} días<br>"
                "IS: %{customdata[2]:.2f} días<br>"
                "IR: %{customdata[3]:.2f}<br>"
                f"CF: {int(float(row['CF']))}"
                "<extra></extra>"
            ),
        ))

    fig.update_layout(
        title=dict(
            text=f"Diagrama de Barber y Johnson — {hospital}",
            font=dict(size=14, family="sans-serif"), x=0,
        ),
        xaxis=dict(
            title="Intervalo de Sustitución IS (días)",
            range=[is_ax_min, is_ax_max],
            zeroline=True, zerolinewidth=1.5, zerolinecolor="rgba(0,0,0,0.3)",
            gridcolor="rgba(0,0,0,0.07)",
            tickfont=dict(family="monospace", size=11),
        ),
        yaxis=dict(
            title="Estancia Media EM (días)",
            range=[0, em_max_ax],
            zeroline=True, zerolinewidth=1.5, zerolinecolor="rgba(0,0,0,0.3)",
            gridcolor="rgba(0,0,0,0.07)",
            tickfont=dict(family="monospace", size=11),
        ),
        plot_bgcolor="#fafaf7",
        paper_bgcolor="white",
        height=540,
        margin=dict(l=65, r=30, t=55, b=65),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1, font=dict(size=11),
        ),
    )
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏥 Barber & Johnson")
    st.caption("Generador de indicadores de hospitalización")
    st.divider()

    hospital = st.text_input("Nombre del hospital / unidad", value="Hospital")

    # ── Inicializar DataFrame en session_state ────────────────────────────────
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame(
            [{"Etiqueta": "", "CF": None, "A": None, "E": None, "D": 30}
             for _ in range(4)]
        )

    st.subheader("Cargar ejemplo")
    col_e1, col_e2 = st.columns(2)
    if col_e1.button("Febreros HURH", use_container_width=True):
        st.session_state.df = EJEMPLOS["Febreros HURH"].copy()
    if col_e2.button("Servicios HURH", use_container_width=True):
        st.session_state.df = EJEMPLOS["Servicios HURH"].copy()

    st.subheader("Datos de entrada")
    st.caption("CF = Camas Funcionantes · A = Altas · E = Estancias · D = Días del período")

    edited = st.data_editor(
        st.session_state.df,
        num_rows="dynamic",
        column_config={
            "Etiqueta": st.column_config.TextColumn("Etiqueta", width="small"),
            "CF": st.column_config.NumberColumn("CF", min_value=1, format="%d"),
            "A":  st.column_config.NumberColumn("A",  min_value=1, format="%d"),
            "E":  st.column_config.NumberColumn("E",  min_value=1, format="%d"),
            "D":  st.column_config.NumberColumn("D",  min_value=1, format="%d", default=30),
        },
        use_container_width=True,
        key="data_editor",
    )
    st.session_state.df = edited

    st.divider()
    st.subheader("Configuración de zona óptima y ejes")
    c1, c2 = st.columns(2)
    with c1:
        io_min     = st.number_input("%IO mínimo",      value=75,  min_value=50, max_value=95,  step=5)
        em_min_opt = st.number_input("EM mín. (días)",  value=7.0, min_value=1.0, max_value=20.0, step=0.5)
        is_ax_min  = st.number_input("IS mín. eje",     value=-3,  min_value=-15, max_value=0,   step=1)
    with c2:
        io_max     = st.number_input("%IO máximo",      value=85,  min_value=60, max_value=99,  step=5)
        em_max_opt = st.number_input("EM máx. (días)",  value=9.0, min_value=2.0, max_value=30.0, step=0.5)
        is_ax_max  = st.number_input("IS máx. eje",     value=6,   min_value=1,  max_value=20,  step=1)

    st.divider()
    # ── Glosario compacto ──────────────────────────────────────────────────────
    with st.expander("📖 Glosario de indicadores"):
        st.markdown("""
| Sigla | Indicador | Fórmula |
|-------|-----------|---------|
| **EM** | Estancia Media | `E ÷ A` |
| **%IO** | Índice de Ocupación | `(E ÷ CF×D) × 100` |
| **IS** | Intervalo de Sustitución | `(D×CF − E) ÷ A` |
| **IR** | Índice de Rotación | `A ÷ CF` |
        """)

# ══════════════════════════════════════════════════════════════════════════════
# PANEL PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
df_valid = st.session_state.df.dropna(subset=["CF","A","E"])

# Diagrama
fig = build_figure(df_valid, hospital, io_min, io_max, em_min_opt, em_max_opt, is_ax_min, is_ax_max)
st.plotly_chart(fig, use_container_width=True)

# ── Tabla resumen ──────────────────────────────────────────────────────────────
filas = [(row, calcular(row)) for _, row in df_valid.iterrows()]
filas = [(r, c) for r, c in filas if c]

if filas:
    st.subheader("Tabla de indicadores")
    tabla = []
    for row, c in filas:
        z_label, z_emoji, _ = zona(c["IO"], io_min, io_max)
        tabla.append({
            "Etiqueta": str(row["Etiqueta"]),
            "CF": int(float(row["CF"])),
            "A":  int(float(row["A"])),
            "E":  int(float(row["E"])),
            "D":  int(float(row["D"])),
            "EM":  round(c["EM"],  2),
            "%IO": round(c["IO"],  2),
            "IS":  round(c["IS"],  2),
            "IR":  round(c["IR"],  2),
            "Zona": f"{z_emoji} {z_label}",
        })
    st.dataframe(pd.DataFrame(tabla), use_container_width=True, hide_index=True)
else:
    st.info("Introduce datos en la barra lateral para visualizar el diagrama.")

# ── Guía de interpretación ─────────────────────────────────────────────────────
with st.expander("📘 Guía de interpretación del diagrama"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.error("**IS < 0 · Sobreocupación**\n\n%IO > 100%. Más pacientes que camas. Requiere camas supletorias o reducción de demanda.")
    with col2:
        st.success("**Zona óptima**\n\n%IO 75–85%, IS 1–2 días. Equilibrio entre ocupación y reserva operativa.")
    with col3:
        st.warning("**EM alta + IS ≈ 0**\n\nEstancias prolongadas con alta ocupación. Revisar criterios de alta.")
    with col4:
        st.info("**IS > 3 · Baja ocupación**\n\nCamas frecuentemente libres (%IO < 75%). Valorar cierre temporal.")
