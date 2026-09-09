# %% [markdown]
# # ¿Está bien asignado el esfuerzo comercial?
#
# **Caso:** fuerza comercial en farma. 50 delegados, 2.000 médicos, dos años de histórico
# (2024 y 2025) de visitas y prescripción a nivel médico-mes. Precio 18 €/unidad.
#
# **Pregunta de Dirección Comercial:** ¿está bien asignado el esfuerzo? Si no, ¿dónde, qué
# cambiar y cuánto vale el cambio? Con la misma plantilla y el mismo número de visitas.
#
# ## Resumen ejecutivo
#
# 1. **La regla actual se cumple a rajatabla:** los A reciben ~13 visitas al año, los B ~4 y
#    los C ~1,5. La segmentación es buena (solo 30 de 2.000 médicos están en el segmento
#    "equivocado" según su volumen real de categoría). El problema no es a quién se etiqueta
#    como A, sino **cuántas veces se le visita**.
# 2. **La cuota responde a la visita, pero se satura.** Un médico sin visitas tiene ~12 % de
#    cuota; con 3 a 5 visitas al año, ~21 %; a partir de 8-10 visitas la curva es plana
#    (~23,5 %). La curva es la misma para A, B y C. Lo confirman los cambios dentro del
#    mismo médico entre 2024 y 2025: la primera visita mueve ~3,6 puntos de cuota, la
#    décima ~0,15 y la vigésima ~0,05.
# 3. **Por eso el esfuerzo está mal repartido:** el 22,5 % de las visitas de 2025 son la
#    décima o posterior al mismo médico (casi todas a médicos A), mientras 1.000
#    médicos-año (sobre todo B y C) no reciben ninguna. La décima visita a un A vale
#    ~600 €; la quinta a un B, ~700 €; la segunda a un C, ~700 €. La primera visita a un B
#    sin visitar vale más de 3.000 €.
# 4. **Recomendación:** pasar de 13 / 4 / 1,5 visitas al año a **≈ 9-10 / 5 / 2 (A / B / C)**,
#    ajustando por volumen de categoría de cada médico, dentro de la cartera de cada
#    delegado y sin mover una sola visita de un delegado a otro.
# 5. **Valor:** **≈ +2,4 M€ al año** (+8 % de ventas, cuota global de 19,9 % a ~21,5 %) a
#    coste cero. Las variantes del modelo dan entre 2,25 y 2,5 M€; si solo se materializara
#    la mitad del efecto estimado, 1,2 M€. Solo con "nadie a cero" ya se ganan ~1,3 M€.
# 6. **Por dónde empezar y cuánto fiarse del número.** La mitad de la ganancia está en menos
#    de 200 médicos y unas 1.000 visitas (sección 4.2). Una sola curva explica el 90 % de los
#    cambios de cuota entre médicos: no hay subgrupos que respondan distinto. Simulando que solo
#    parte del efecto es causal y que el plan se ejecuta a medias, el valor mediano es ≈ 1,9 M€ y
#    supera 1,5 M€ en el 93 % de los escenarios. Un piloto de seis meses en una región basta para
#    comprobarlo con menos de 15 médicos por grupo.
#
# El detalle, el método y los límites están en las secciones siguientes. Las cifras
# finales se guardan en `output/resumen_cifras.json` y el plan por delegado y por médico
# en `output/plan_visitas_2026.xlsx`.

# %% [markdown]
# ## 0. Preparación
#
# Decisiones de partida (la auditoría completa de los datos está en 0.1; ver también la
# sección 8, Límites y supuestos):
#
# - **Duplicados.** `visitas.csv` tiene 255 filas con el mismo delegado, médico y fecha
#   (253 pares y un triple, con `id_visita` distintos). Se tratan como doble registro del
#   sistema y se eliminan. La sensibilidad a esta decisión se mide en la sección 4.1.
# - **Grano de análisis: médico-año.** La fuerza comercial decide frecuencias anuales y
#   los efectos de la visita duran meses (sección 3.3), así que el año es la unidad natural.
# - **Potencial = volumen real de categoría del médico** (`unidades_categoria`), no la
#   etiqueta A/B/C. La etiqueta sirve para comunicar; el volumen, para calcular.

# %%
from pathlib import Path
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import optimize

try:
    display
except NameError:  # ejecución como script
    display = print

try:
    ROOT = Path(__file__).resolve().parent  # como script: la carpeta donde está analisis.py, se lance desde donde se lance
except NameError:
    ROOT = Path.cwd()  # en el notebook no existe __file__: se usa la carpeta de trabajo
DATA, OUT = ROOT / "2_datos", ROOT / "output"
assert DATA.exists(), f"No encuentro la carpeta 2_datos/ en {ROOT}. Debe estar junto a analisis.py (o ser la carpeta de trabajo del notebook)."
OUT.mkdir(exist_ok=True)

PRECIO = 18.0  # €/unidad, constante en todo el periodo (enunciado)
COSTE_VISITA = 72.0  # € coste medio totalmente cargado (enunciado)

# Paleta: gris para "hoy", azul para "plan", naranja para el coste. Segmentos en rampa azul.
C_ACTUAL, C_PLAN, C_ACENTO = "#898781", "#2a78d6", "#eb6834"
C_TINTA, C_TINTA2, C_GRID = "#0b0b0b", "#52514e", "#e1e0d9"
C_SEG = {"A": "#1c5cab", "B": "#3987e5", "C": "#86b6ef"}
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#c3c2b7",
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": C_GRID, "grid.linewidth": 0.8,
    "axes.titlesize": 12, "axes.titleweight": "semibold", "axes.titlelocation": "left",
    "axes.labelcolor": C_TINTA2, "xtick.color": C_TINTA2, "ytick.color": C_TINTA2,
    "figure.dpi": 110, "savefig.dpi": 200, "legend.frameon": False, "figure.figsize": (8, 4.5),
})
pd.set_option("display.width", 160)
pd.set_option("display.float_format", lambda x: f"{x:,.3f}")


def eur(x, dec=2):
    """Formato en millones de euros."""
    return f"{x / 1e6:,.{dec}f} M€"


def guardar(fig, nombre):
    fig.tight_layout()
    fig.savefig(OUT / f"{nombre}.png", bbox_inches="tight")
    if "get_ipython" in globals():  # en el notebook se muestra; como script solo se guarda
        plt.show()
    else:
        plt.close(fig)


# %%
med = pd.read_csv(DATA / "maestro_medicos.csv")
dele = pd.read_csv(DATA / "maestro_delegados.csv")
vis_raw = pd.read_csv(DATA / "visitas.csv", parse_dates=["fecha"])
pre = pd.read_csv(DATA / "prescripciones.csv")

# Comprobaciones de integridad (el enunciado la garantiza; se verifica igualmente)
assert len(med) == 2000 and len(dele) == 50 and len(vis_raw) == 16917 and len(pre) == 48000
assert vis_raw.id_medico.isin(med.id_medico).all() and vis_raw.id_delegado.isin(dele.id_delegado).all()
assert med.id_delegado_asignado.isin(dele.id_delegado).all()
assert (pre.unidades_producto <= pre.unidades_categoria).all() and (pre.unidades_categoria > 0).all()
assert pre.groupby("id_medico").size().eq(24).all()
assert not pre.duplicated(["id_medico", "mes"]).any()
# Cada visita la hace el delegado asignado al médico
assert (vis_raw.merge(med, on="id_medico").eval("id_delegado == id_delegado_asignado")).all()

# %% [markdown]
# ### 0.1 Auditoría de calidad de datos
#
# El enunciado avisa de que los datos salen "tal cual" del sistema. Antes de limpiar nada se
# mide qué imperfecciones hay y se decide qué hacer con cada una. Solo una (los duplicados)
# cambia los números; las demás condicionan qué análisis tiene sentido hacer y cuáles no.

# %%
def auditoria():
    filas = []

    def add(comprobacion, resultado, decision):
        filas.append({"comprobación": comprobacion, "resultado": resultado, "decisión": decision})

    nulos = {n: int(t.isna().sum().sum()) for n, t in [("médicos", med), ("delegados", dele), ("visitas", vis_raw), ("prescripciones", pre)]}
    add("Valores nulos", ", ".join(f"{k} {v}" for k, v in nulos.items()), "Nada que imputar")
    add("Integridad referencial (id_medico, id_delegado)", "completa en las tres tablas", "Se usa tal cual")
    misma = vis_raw.merge(med, on="id_medico").eval("id_delegado == id_delegado_asignado").mean()
    add("Visita hecha por el delegado asignado al médico", f"{misma:.0%} de las visitas", "La cartera de cada delegado es id_delegado_asignado")
    add("id_visita repetido", f"{int(vis_raw.id_visita.duplicated().sum())} casos", "Ninguno")
    sobran = int(vis_raw.duplicated(["id_delegado", "id_medico", "fecha"]).sum())
    add("Mismo delegado, mismo médico, mismo día", f"{sobran} filas sobrantes (253 pares y 1 triple, ids no consecutivos)", "Se eliminan como doble registro; sensibilidad en 4.1")
    add("Rango de fechas de visita", f"{vis_raw.fecha.min().date()} a {vis_raw.fecha.max().date()}", "Coincide con los 24 meses de prescripción")
    dias = vis_raw.fecha.dt.dayofweek.value_counts(normalize=True)
    add("Visitas en sábado o domingo", f"{dias.get(5, 0) + dias.get(6, 0):.0%} (reparto uniforme entre los 7 días)", "Fechas sin calendario real: no se analiza por día de la semana")
    pares = med[["region", "brick"]].drop_duplicates().shape[0]
    add("Códigos de brick", f"{med.brick.nunique()} códigos pero {pares} pares región-brick (NOR-xx se repite en Noreste y Noroeste)", "El brick no se usa; la unidad es el médico y su delegado")
    dpb = med.groupby(["region", "brick"]).id_delegado_asignado.nunique()
    add("Delegados por brick", f"de {dpb.min()} a {dpb.max()}", "El brick no es un territorio de delegado")
    cpd = med.id_delegado_asignado.value_counts()
    add("Médicos por delegado", f"de {cpd.min()} a {cpd.max()}", "Carteras muy desiguales; el plan respeta la de cada uno")
    vpd = vis_raw.groupby(["id_delegado", vis_raw.fecha.dt.year]).size()
    add("Visitas por delegado y año", f"media {vpd.mean():.0f}, de {vpd.min()} a {vpd.max()} (el briefing habla de 6-10 al día)", "La capacidad es el volumen observado, no el del briefing")
    nunca = int((~med.id_medico.isin(vis_raw.id_medico)).sum())
    add("Médicos sin ninguna visita en dos años", f"{nunca} de 2.000", "Se analizan como visitas = 0")
    add("Prescripción: producto ≤ categoría, sin ceros, 24 meses por médico, sin duplicados", "se cumple en las 48.000 filas", "Tabla limpia")
    cat_y = pre.groupby(["id_medico", pre.mes.str[:4]]).unidades_categoria.sum().unstack()
    add("Volumen de categoría 2024 frente a 2025 por médico", f"correlación {cat_y.iloc[:, 0].corr(cat_y.iloc[:, 1]):.3f}", "El potencial es estable: 2025 sirve de base para 2026")
    add("Segmento A/B/C", "un solo snapshot (Marketing lo revisa cada año)", "No se puede medir el cambio de segmento; se usa el volumen real")
    return pd.DataFrame(filas)


auditoria_df = auditoria()
with pd.option_context("display.max_colwidth", 110):
    display(auditoria_df)

# %%
# Duplicados: mismo delegado, mismo médico, mismo día
dup = vis_raw.duplicated(["id_delegado", "id_medico", "fecha"])
print(f"Visitas registradas: {len(vis_raw):,} | duplicadas mismo día: {dup.sum()} | válidas: {(~dup).sum():,}")
vis = vis_raw[~dup].copy()
vis["anio"] = vis.fecha.dt.year
pre["anio"] = pre.mes.str[:4].astype(int)

# Anclas de negocio
ventas = pre.groupby("anio").unidades_producto.sum() * PRECIO
cuota_global = pre.groupby("anio").unidades_producto.sum() / pre.groupby("anio").unidades_categoria.sum()
print("Ventas:", {a: eur(v) for a, v in ventas.items()}, "| Cuota global:", cuota_global.round(4).to_dict())

# %% [markdown]
# ### Tabla médico-año
# Una fila por médico y año: visitas recibidas, unidades de categoría y de producto, cuota.

# %%
py = pre.groupby(["id_medico", "anio"], as_index=False)[["unidades_categoria", "unidades_producto"]].sum()
vy = vis.groupby(["id_medico", "anio"]).size().rename("visitas").reset_index()
dy = py.merge(vy, on=["id_medico", "anio"], how="left").fillna({"visitas": 0}).merge(med, on="id_medico")
dy["visitas"] = dy.visitas.astype(int)
dy["cuota"] = dy.unidades_producto / dy.unidades_categoria
assert len(dy) == 4000
dy.head()

# %% [markdown]
# ## 1. Cómo se reparte hoy el esfuerzo
#
# La regla "los A se visitan más que los B y los B más que los C" se cumple, y con
# intensidad: un A recibe 9 veces más visitas que un C. La pregunta es si esa intensidad
# está justificada por la respuesta del médico, no por su potencial.

# %%
def reparto(df):
    g = df.groupby("segmento_potencial").agg(
        medicos=("id_medico", "size"), visitas=("visitas", "sum"),
        categoria=("unidades_categoria", "sum"), producto=("unidades_producto", "sum"),
    )
    g["visitas_por_medico"] = g.visitas / g.medicos
    g["pct_visitas"] = g.visitas / g.visitas.sum()
    g["pct_categoria"] = g.categoria / g.categoria.sum()
    g["cuota"] = g.producto / g.categoria
    g["sin_visitas"] = df[df.visitas == 0].groupby("segmento_potencial").size()
    return g


reparto_25 = reparto(dy[dy.anio == 2025])
display(reparto_25.round(3))
print("Médicos-año con 0 visitas (2024+2025):", (dy.visitas == 0).sum(),
      "| médicos sin ninguna visita en dos años:", (dy.groupby("id_medico").visitas.sum() == 0).sum())

# %%
# ¿Está bien puesta la etiqueta A/B/C? Comparación con el ranking real por volumen de categoría
d25 = dy[dy.anio == 2025].sort_values("unidades_categoria", ascending=False).reset_index(drop=True)
nA, nB = (med.segmento_potencial == "A").sum(), (med.segmento_potencial == "B").sum()
d25["segmento_por_volumen"] = np.where(d25.index < nA, "A", np.where(d25.index < nA + nB, "B", "C"))
tabla_seg = pd.crosstab(d25.segmento_potencial, d25.segmento_por_volumen, margins=True)
display(tabla_seg)
mal_segmentados = int((d25.segmento_potencial != d25.segmento_por_volumen).sum())
print(f"Médicos cuya etiqueta no coincide con su volumen real: {mal_segmentados} de 2.000. "
      "La segmentación no es el problema.")

# %%
# Distribución de visitas por médico en 2025: los extremos son el problema
bins = [-1, 0, 2, 5, 9, 14, 19, 29, 100]
etiquetas = ["0", "1-2", "3-5", "6-9", "10-14", "15-19", "20-29", "30+"]
dy["tramo"] = pd.cut(dy.visitas, bins=bins, labels=etiquetas)
dist = pd.crosstab(dy[dy.anio == 2025].tramo, dy[dy.anio == 2025].segmento_potencial)

fig, ax = plt.subplots()
abajo = np.zeros(len(dist))
for s in ["A", "B", "C"]:
    ax.bar(dist.index.astype(str), dist[s], bottom=abajo, color=C_SEG[s], label=f"Segmento {s}", width=0.7)
    abajo += dist[s].to_numpy()
for i, tot in enumerate(abajo):
    ax.text(i, tot + 8, f"{int(tot)}", ha="center", va="bottom", fontsize=9, color=C_TINTA2)
ax.set_title("Médicos por número de visitas recibidas en 2025")
ax.set_xlabel("Visitas al año"); ax.set_ylabel("Médicos"); ax.legend()
guardar(fig, "01_distribucion_visitas")

visitas_10mas = int((dy[dy.anio == 2025].visitas - 9).clip(lower=0).sum())
presupuesto_25 = int(dy[dy.anio == 2025].visitas.sum())
print(f"Visitas 2025 (sin duplicados): {presupuesto_25:,}. De ellas, {visitas_10mas:,} "
      f"({visitas_10mas / presupuesto_25:.0%}) son la décima o posterior al mismo médico.")

# %% [markdown]
# ## 2. ¿Responde la prescripción a la visita?
#
# ### 2.1 Corte transversal: cuota según visitas recibidas, por segmento
#
# A igual número de visitas, la cuota es prácticamente la misma sea el médico A, B o C.
# Y la curva se aplana claramente a partir de 8-10 visitas al año.

# %%
curva_obs = (dy.groupby(["segmento_potencial", "tramo"], observed=True)
             .agg(n=("cuota", "size"), visitas=("visitas", "mean"), cuota=("cuota", "mean")))
display(curva_obs.cuota.unstack(0).round(3))
display(curva_obs.n.unstack(0))

# %% [markdown]
# ### 2.2 Cambios dentro del mismo médico (primeras diferencias 2024 → 2025)
#
# El corte transversal podría estar sesgado (quizá se visita más a quien ya prescribía más).
# Por eso la estimación central usa **cambios dentro del mismo médico**: cuando a un médico
# le suben o bajan las visitas de un año al otro, ¿cambia su cuota? Esto elimina cualquier
# diferencia fija entre médicos. El resultado es el mismo: la respuesta es fuerte al
# principio y casi nula a partir de 10 visitas.

# %%
W = dy.pivot(index="id_medico", columns="anio", values=["visitas", "cuota", "unidades_categoria"])
v24, v25 = W["visitas"][2024].to_numpy(float), W["visitas"][2025].to_numpy(float)
dcuota = (W["cuota"][2025] - W["cuota"][2024]).to_numpy()
dvis = v25 - v24
seg_w = med.set_index("id_medico").loc[W.index, "segmento_potencial"]

nivel = pd.cut(v24, [-1, 0, 2, 5, 9, 14, 19, 100], labels=["0", "1-2", "3-5", "6-9", "10-14", "15-19", "20+"])
filas = []
for niv in nivel.categories:
    m = nivel == niv
    if m.sum() < 30 or dvis[m].std() == 0:
        continue
    ols = sm.OLS(dcuota[m], sm.add_constant(dvis[m])).fit(cov_type="HC1")
    filas.append({"visitas_2024": niv, "medicos": int(m.sum()), "pp_cuota_por_visita": 100 * ols.params[1],
                  "t": ols.tvalues[1], "visitas_medias": v24[m].mean()})
fd_niveles = pd.DataFrame(filas).set_index("visitas_2024")
display(fd_niveles.round(2))

fig, ax = plt.subplots()
ax.bar(fd_niveles.index.astype(str), fd_niveles.pp_cuota_por_visita, color=C_PLAN, width=0.65)
for i, v in enumerate(fd_niveles.pp_cuota_por_visita):
    ax.text(i, v + 0.05, f"{v:.2f}", ha="center", va="bottom", fontsize=9, color=C_TINTA2)
ax.set_title("Puntos de cuota que gana el médico por cada visita adicional, según cuántas ya recibía")
ax.set_xlabel("Visitas recibidas en 2024"); ax.set_ylabel("Puntos porcentuales de cuota por visita")
guardar(fig, "02_respuesta_marginal")

# %% [markdown]
# ### 2.3 ¿Cuánto tarda el efecto? (panel mensual, efectos fijos por médico)
#
# Una visita mueve la cuota desde el mismo mes y el efecto sigue vivo seis meses después.
# Por eso el análisis anual captura el efecto casi completo dentro del mismo año.

# %%
vm = vis.groupby(["id_medico", vis.fecha.dt.strftime("%Y-%m")]).size().rename("v").reset_index().rename(columns={"fecha": "mes"})
pm = pre.merge(vm, on=["id_medico", "mes"], how="left").fillna({"v": 0}).sort_values(["id_medico", "mes"])
pm["cuota"] = pm.unidades_producto / pm.unidades_categoria
LAGS = [f"v_lag{k}" for k in range(7)]
for k in range(7):
    pm[f"v_lag{k}"] = pm.groupby("id_medico").v.shift(k)
pm_ok = pm.dropna(subset=LAGS)
dentro = pm_ok[["cuota"] + LAGS] - pm_ok.groupby("id_medico")[["cuota"] + LAGS].transform("mean")
ols_m = sm.OLS(dentro.cuota, dentro[LAGS]).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(pm_ok.id_medico)[0]})
efecto_mensual = pd.DataFrame({"pp_cuota": 100 * ols_m.params, "t": ols_m.tvalues}).round(2)
efecto_mensual.index = [f"mes t-{k}" for k in range(7)]
display(efecto_mensual)

# ¿Hay selección? Médicos sin visitas en 2024 que empiezan a recibirlas en 2025: su cuota
# ANTES de la primera visita, frente a la de los médicos que siguen sin visitas.
primera_25 = vis[vis.anio == 2025].groupby("id_medico").fecha.min()
nuevos = primera_25.index.difference(vis[vis.anio == 2024].id_medico.unique())
antes = pm[pm.id_medico.isin(nuevos)].copy()
antes["mes_dt"] = pd.to_datetime(antes.mes)
antes = antes[(antes.mes_dt < antes.id_medico.map(primera_25)) & (antes.mes_dt >= antes.id_medico.map(primera_25) - pd.DateOffset(months=6))]
nunca = pm[~pm.id_medico.isin(vis.id_medico.unique())]
print(f"Médicos que pasan de 0 visitas en 2024 a alguna en 2025: {len(nuevos)}. Su cuota en los 6 meses previos a la "
      f"primera visita: {antes.cuota.mean():.1%}; cuota de los médicos nunca visitados: {nunca.cuota.mean():.1%}.")

# %% [markdown]
# ### 2.4 La curva de respuesta
#
# Ajustamos una curva de saturación sencilla, `cuota = base_médico + D · v / (v + h)`, donde `v`
# son las visitas al año. `D` es la ganancia máxima de cuota que aporta la visita y `h` es el
# número de visitas con el que se alcanza la mitad de esa ganancia. Se estima **sobre los cambios
# dentro del mismo médico** (primeras diferencias), no sobre niveles, y se comprueba que la
# misma curva sirve para A, B y C.

# %%
def g(v, D, h):
    """Ganancia de cuota (en tanto por uno) por recibir v visitas al año."""
    return D * v / (v + h)


def ajustar_fd(v_a, v_b, dc, p0=(0.15, 2.5)):
    """Ajuste por mínimos cuadrados de D y h sobre primeras diferencias: dc = g(v_b) - g(v_a)."""
    res = optimize.least_squares(lambda p: g(v_b, *p) - g(v_a, *p) - dc, p0, bounds=([0, 0.05], [1, 60]))
    return float(res.x[0]), float(res.x[1])


D, h = ajustar_fd(v24, v25, dcuota)
V_all, C_all = dy.visitas.to_numpy(float), dy.cuota.to_numpy()
s0 = float(np.mean(C_all - g(V_all, D, h)))  # cuota base media (0 visitas)
print(f"Curva (primeras diferencias): D = {D:.4f}, h = {h:.2f} | cuota base media = {s0:.3f} | techo = {s0 + D:.3f}")

# Robustez: la misma curva por segmento y sobre niveles
ajustes = {}
for s in ["A", "B", "C"]:
    m = (seg_w == s).to_numpy()
    ajustes[f"FD segmento {s}"] = ajustar_fd(v24[m], v25[m], dcuota[m])
res_niv = optimize.least_squares(lambda p: p[0] + g(V_all, p[1], p[2]) - C_all, [0.12, 0.13, 1.7], bounds=([0, 0, 0.05], [1, 1, 60]))
ajustes["Niveles (todos)"] = (float(res_niv.x[1]), float(res_niv.x[2]))
ajustes["FD todos (central)"] = (D, h)
tabla_ajustes = pd.DataFrame(ajustes, index=["D", "h"]).T
tabla_ajustes["cuota extra con 5 visitas"] = tabla_ajustes.apply(lambda r: g(5, r.D, r.h), axis=1)
tabla_ajustes["cuota extra con 15 visitas"] = tabla_ajustes.apply(lambda r: g(15, r.D, r.h), axis=1)
display(tabla_ajustes.round(3))

# Pendiente del modelo vs pendiente observada por nivel (validación)
vm_ = fd_niveles.visitas_medias
fd_niveles["pp_modelo_una_visita_mas"] = 100 * (g(vm_ + 1, D, h) - g(vm_, D, h))
display(fd_niveles[["medicos", "pp_cuota_por_visita", "pp_modelo_una_visita_mas"]].round(2))

# %%
fig, ax = plt.subplots()
vv = np.linspace(0, 30, 200)
ax.plot(vv, 100 * (s0 + g(vv, D, h)), color=C_TINTA, lw=2, label="Curva usada para valorar (cambios dentro del médico)")
ax.plot(vv, 100 * (res_niv.x[0] + g(vv, *ajustes["Niveles (todos)"])), color=C_ACTUAL, lw=1.5, ls="--", label="Ajuste sobre niveles (referencia)")
for s in ["A", "B", "C"]:
    c = curva_obs.loc[s]
    ax.scatter(c.visitas, 100 * c.cuota, s=np.sqrt(c.n) * 4, color=C_SEG[s], label=f"Observado segmento {s}", zorder=3, edgecolor="white", linewidth=0.5)
for s, x in reparto_25.visitas_por_medico.items():
    ax.axvline(x, color=C_SEG[s], lw=1, ls=":", ymax=0.92)
    ax.text(x, 100 * (s0 + D) + (2.2 if s != "B" else 1.2), f"hoy {s}: {x:.1f}", ha="center", fontsize=8.5, color=C_SEG[s])
ax.set_ylim(10, 30.5); ax.set_xlim(-0.5, 30)
ax.set_title("Cuota del médico según visitas recibidas al año (el tamaño del punto es el número de médicos)")
ax.set_xlabel("Visitas al año"); ax.set_ylabel("Cuota de nuestro producto (%)")
ax.legend(loc="lower right", fontsize=9)
guardar(fig, "03_curva_respuesta")

# %% [markdown]
# ## 3. Cuánto vale cada visita, en euros
#
# Valor de una visita = volumen de categoría del médico × ganancia de cuota × 18 €. Como la
# ganancia de cuota depende de cuántas visitas ya recibe, la décima visita a un A vale mucho
# menos que la primera a un B, aunque el A tenga el triple de volumen.

# %%
base = dy[dy.anio == 2025].set_index("id_medico")  # potencial (categoría) y asignación actual
cat, v_act, seg = base.unidades_categoria.astype(float), base.visitas.astype(float), base.segmento_potencial


def delta_unidades(v_new, v_old, D=D, h=h):
    return cat * (g(v_new, D, h) - g(v_old, D, h))


valor_siguiente = delta_unidades(v_act + 1, v_act) * PRECIO
valor_ultima = delta_unidades(v_act, (v_act - 1).clip(lower=0)) * PRECIO
tabla_valor = pd.DataFrame({
    "visitas_por_medico": v_act.groupby(seg).mean(),
    "categoria_media": cat.groupby(seg).mean(),
    "eur_una_visita_mas": valor_siguiente.groupby(seg).mean(),
    "eur_ultima_visita": valor_ultima[v_act > 0].groupby(seg).mean(),
})
display(tabla_valor.round(0))

# Valor de la visita k-ésima para el médico mediano de cada segmento
ks = np.arange(1, 21)
cat_mediana = cat.groupby(seg).median()
fig, ax = plt.subplots()
for s in ["A", "B", "C"]:
    val = cat_mediana[s] * (g(ks, D, h) - g(ks - 1, D, h)) * PRECIO
    ax.plot(ks, val, color=C_SEG[s], lw=2, marker="o", ms=4, label=f"Médico {s} mediano ({cat_mediana[s]:,.0f} uds. de categoría al año)".replace(",", "."))
    ax.text(ks[-1] + 0.3, val[-1], s, color=C_SEG[s], va="center", fontsize=9)
ax.axhline(COSTE_VISITA, color=C_ACENTO, lw=1.2, ls="--")
ax.text(20.5, COSTE_VISITA + 60, f"coste de la visita: {COSTE_VISITA:.0f} €", color=C_ACENTO, ha="right", fontsize=9)
ax.set_yscale("log"); ax.set_yticks([50, 100, 300, 1000, 3000, 10000]); ax.set_yticklabels(["50", "100", "300", "1.000", "3.000", "10.000"])
ax.set_xticks(range(1, 21))
ax.set_title("Euros de venta anual que aporta la visita número k a un médico (escala logarítmica)")
ax.set_xlabel("Número de visita en el año"); ax.set_ylabel("€ por visita"); ax.legend(fontsize=9)
guardar(fig, "04_valor_visita_k")

k_val = pd.DataFrame({s: cat_mediana[s] * (g(ks, D, h) - g(ks - 1, D, h)) * PRECIO for s in "ABC"}, index=ks).round(0)
display(k_val.loc[[1, 2, 3, 5, 8, 10, 14, 20]].T)

# %% [markdown]
# ## 4. La reasignación: mismas visitas, mejor repartidas
#
# Con la curva estimada, el reparto que maximiza unidades es el que **iguala el valor de la
# última visita** entre médicos: se asignan las visitas una a una a quien más aporta en ese
# momento (asignación greedy, óptima porque la curva es cóncava).
#
# Se calculan tres versiones:
#
# - **Óptimo global:** una única bolsa de visitas para toda la compañía (cota superior).
# - **Óptimo dentro de cada delegado:** cada delegado mantiene exactamente sus visitas de 2025
#   y las reparte mejor entre sus propios médicos. **Es el plan recomendado**, porque es
#   ejecutable el lunes: no cambia territorios, cargas ni costes.
# - **Regla sencilla por segmento** (para comunicar): la misma frecuencia para todos los
#   médicos de un segmento.

# %%
def asignacion_optima(cat, presupuesto, D=D, h=h, vmax=40):
    """Reparte `presupuesto` visitas entre médicos con volumen `cat` maximizando unidades."""
    ks = np.arange(1, vmax + 1)
    ganancia = np.outer(cat.to_numpy(float), g(ks, D, h) - g(ks - 1, D, h))  # ganancia de la visita k a cada médico
    elegidas = np.argsort(ganancia, axis=None)[::-1][: int(presupuesto)]
    return pd.Series(np.bincount(elegidas // vmax, minlength=len(cat)), index=cat.index)


def valor_plan(v_plan, D=D, h=h):
    """Ventas anuales adicionales (€) de una asignación frente a la actual, con la curva (D, h)."""
    return float(delta_unidades(v_plan, v_act, D, h).sum() * PRECIO)


unidades_25 = base.unidades_producto.sum()

# a) Óptimo global
v_global = asignacion_optima(cat, presupuesto_25)
# b) Óptimo dentro de cada delegado (plan recomendado)
v_plan = pd.Series(0, index=cat.index)
for _, ids in base.groupby("id_delegado_asignado").groups.items():
    v_plan.loc[ids] = asignacion_optima(cat.loc[ids], v_act.loc[ids].sum())
assert v_plan.sum() == presupuesto_25
assert (v_plan.groupby(base.id_delegado_asignado).sum() == v_act.groupby(base.id_delegado_asignado).sum()).all()
# c) Regla sencilla: frecuencia fija por segmento (redondeo del plan), sin superar el presupuesto
regla = v_plan.groupby(seg).mean().round().astype(int)
v_regla = seg.map(regla).astype(float)
while v_regla.sum() > presupuesto_25:  # si la regla se pasa del presupuesto, se recorta a los A
    regla["A"] -= 1; v_regla = seg.map(regla).astype(float)
# d) "Nadie a cero": dos visitas a cada médico sin visitar, quitadas a quien recibe más de 12
v_nadie0 = v_act.copy(); ceros = v_nadie0 == 0; v_nadie0[ceros] = 2
por_quitar = int(2 * ceros.sum())
while por_quitar > 0:
    i = v_nadie0.idxmax(); v_nadie0[i] -= 1; por_quitar -= 1

escenarios = pd.DataFrame({
    "Óptimo global": v_global, "Plan (óptimo por delegado)": v_plan,
    f"Regla {regla['A']}/{regla['B']}/{regla['C']}": v_regla, "Nadie a cero": v_nadie0, "Hoy (2025)": v_act,
})
resumen_esc = pd.DataFrame({
    "visitas": escenarios.sum(),
    "A": escenarios.groupby(seg).mean().loc["A"], "B": escenarios.groupby(seg).mean().loc["B"], "C": escenarios.groupby(seg).mean().loc["C"],
    "ventas_extra_M€": [valor_plan(escenarios[c]) / 1e6 for c in escenarios],
})
resumen_esc["pct_ventas"] = resumen_esc["ventas_extra_M€"] * 1e6 / ventas[2025]
resumen_esc["cuota_global"] = (unidades_25 + resumen_esc["ventas_extra_M€"] * 1e6 / PRECIO) / cat.sum()
display(resumen_esc.round(3))

# %%
delta_eur = delta_unidades(v_plan, v_act) * PRECIO
valor_base = float(delta_eur.sum())
bridge = delta_eur.groupby(seg).sum()  # neto por segmento
perdida = float(delta_eur[v_plan < v_act].sum())  # lo que se pierde en los médicos a los que se quitan visitas
ganancia = delta_eur[v_plan > v_act].groupby(seg).sum()  # lo que se gana en los médicos que reciben más
n_bajan = (v_plan < v_act).groupby(seg).sum()
print("Plan recomendado:", eur(valor_base), f"({valor_base / ventas[2025]:+.1%} de ventas)",
      "| neto por segmento:", {s: eur(v) for s, v in bridge.items()})
print("Se pierde", eur(-perdida), f"en {int(n_bajan.sum())} médicos que reciben menos visitas (A: {n_bajan['A']}, B: {n_bajan['B']}, C: {n_bajan['C']});",
      "se gana", {s: eur(v) for s, v in ganancia.items()}, "en los que reciben más.")

fig, ax = plt.subplots(figsize=(8, 4.5))
pasos = [(f"Se pierde en los\n{int(n_bajan.sum())} médicos que\nreciben menos visitas", perdida),
         (f"Se gana en A\n({int((v_plan > v_act)[seg == 'A'].sum())} médicos)", ganancia["A"]),
         (f"Se gana en B\n({int((v_plan > v_act)[seg == 'B'].sum())} médicos)", ganancia["B"]),
         (f"Se gana en C\n({int((v_plan > v_act)[seg == 'C'].sum())} médicos)", ganancia["C"])]
acum = 0
for i, (nombre, val) in enumerate(pasos):
    ax.bar(i, val / 1e6, bottom=acum / 1e6, color=C_ACENTO if val < 0 else C_PLAN, width=0.6)
    y_txt = (acum + val) / 1e6 + 0.06 if val > 0 else acum / 1e6 + 0.06  # la pérdida se etiqueta sobre la línea de cero
    ax.text(i, y_txt, f"{val / 1e6:+.2f}", ha="center", va="bottom", fontsize=10, color=C_TINTA)
    acum += val
ax.bar(4, acum / 1e6, color=C_TINTA, width=0.6)
ax.text(4, acum / 1e6 + 0.06, f"{acum / 1e6:+.2f} M€", ha="center", va="bottom", fontsize=11, fontweight="semibold", color=C_TINTA)
ax.set_xticks(range(5)); ax.set_xticklabels([p[0] for p in pasos] + ["Neto al año"], fontsize=9)
ax.set_ylim(min(perdida / 1e6, 0) - 0.2, acum / 1e6 + 0.4)
ax.axhline(0, color="#c3c2b7", lw=1)
ax.set_ylabel("Ventas adicionales (M€ / año)"); ax.set_title("De dónde sale el valor: mismas visitas, mejor repartidas")
guardar(fig, "05_puente_valor")

# %%
# Cómo cambia la frecuencia por médico: hoy vs plan, por segmento
fig, ax = plt.subplots(figsize=(7, 4))
x = np.arange(3); w = 0.36
hoy = v_act.groupby(seg).mean(); plan_m = v_plan.groupby(seg).mean()
ax.bar(x - w / 2, hoy, w, color=C_ACTUAL, label="Hoy (2025)")
ax.bar(x + w / 2, plan_m, w, color=C_PLAN, label="Plan")
for i, s in enumerate("ABC"):
    ax.text(i - w / 2, hoy[s] + 0.2, f"{hoy[s]:.1f}", ha="center", fontsize=10, color=C_TINTA2)
    ax.text(i + w / 2, plan_m[s] + 0.2, f"{plan_m[s]:.1f}", ha="center", fontsize=10, color=C_PLAN, fontweight="semibold")
    rango = f"{int(v_plan[seg == s].min())}-{int(v_plan[seg == s].max())}"
    ax.text(i + w / 2, -1.6, f"rango {rango}", ha="center", fontsize=8.5, color=C_TINTA2)
ax.set_xticks(x); ax.set_xticklabels([f"Segmento {s}\n({(seg == s).sum()} médicos)" for s in "ABC"])
ax.set_ylim(-2.2, 16); ax.set_ylabel("Visitas al año por médico"); ax.set_title("Frecuencia media por segmento: hoy y plan")
ax.legend()
guardar(fig, "06_frecuencia_hoy_vs_plan")

# %% [markdown]
# ### 4.1 Robustez: ¿cuánto depende el valor del modelo?
#
# El plan se fija (el de arriba) y se vuelve a valorar con curvas alternativas: la ajustada
# sobre niveles, una curva distinta por segmento, un remuestreo bootstrap de médicos,
# la versión sin eliminar duplicados y un escenario en el que solo se materializa la mitad
# del efecto estimado.

# %%
rng = np.random.default_rng(42)
n = len(v24)
boot, boot_params = [], []
for _ in range(300):
    idx = rng.integers(0, n, n)
    Db, hb = ajustar_fd(v24[idx], v25[idx], dcuota[idx])
    boot.append(valor_plan(v_plan, Db, hb))
    boot_params.append((Db, hb))
ic_boot = np.percentile(boot, [2.5, 97.5])

# Curva por segmento: cada médico se valora con la curva de su segmento
val_seg = sum(float((delta_unidades(v_plan, v_act, *ajustes[f"FD segmento {s}"])[seg == s]).sum()) for s in "ABC") * PRECIO

# Sin eliminar duplicados
vy_raw = vis_raw[vis_raw.fecha.dt.year == 2025].groupby("id_medico").size().reindex(cat.index, fill_value=0).astype(float)
v_plan_raw = pd.Series(0, index=cat.index)
for _, ids in base.groupby("id_delegado_asignado").groups.items():
    v_plan_raw.loc[ids] = asignacion_optima(cat.loc[ids], vy_raw.loc[ids].sum())
val_raw = float((cat * (g(v_plan_raw, D, h) - g(vy_raw, D, h))).sum() * PRECIO)

robustez = pd.DataFrame({
    "ventas_extra_M€": {
        "Central (FD, sin duplicados)": valor_base / 1e6,
        "Curva ajustada sobre niveles": valor_plan(v_plan, *ajustes["Niveles (todos)"]) / 1e6,
        "Curva distinta por segmento": val_seg / 1e6,
        "Bootstrap IC 95 % (inferior)": ic_boot[0] / 1e6,
        "Bootstrap IC 95 % (superior)": ic_boot[1] / 1e6,
        "Manteniendo los duplicados": val_raw / 1e6,
        "Solo se materializa el 50 % del efecto": valor_base / 2e6,
    }
})
display(robustez.round(2))
rango_prudente = (robustez["ventas_extra_M€"].min(), robustez["ventas_extra_M€"].max())

# %% [markdown]
# ### 4.2 Distribuciones: dónde está el valor, cuánto varía la respuesta y qué probabilidad tiene el número
#
# Las medias resumen; las distribuciones dicen por dónde empezar, si una sola curva basta y
# cuánto vale el plan en un escenario malo. Cuatro miradas:
#
# a. **Concentración del valor** entre médicos: cuántos aportan la mitad de la ganancia.
# b. **Heterogeneidad de la respuesta**: si la curva media esconde subgrupos que responden distinto.
# c. **El valor como distribución**: 4.000 escenarios combinando la incertidumbre de la curva, la
#    parte del efecto que es causal y la parte del plan que se ejecuta.
# d. **Ruido mensual y potencia del piloto**: cuántos médicos y meses hacen falta para ver el efecto.

# %%
# a) Concentración del valor
gan = pd.DataFrame({"eur": delta_eur, "dv": v_plan - v_act, "seg": seg})
gan = gan[gan.eur > 0].sort_values("eur", ascending=False)
gan["acum"] = gan.eur.cumsum() / gan.eur.sum()
concentracion = pd.DataFrame(
    [{"parte_ganancia_bruta": q, "medicos": int((gan.acum < q).sum()) + 1,
      "visitas_anadidas": int(gan.dv.iloc[: int((gan.acum < q).sum()) + 1].sum())} for q in [0.5, 0.8, 0.9, 1.0]]
).set_index("parte_ganancia_bruta")
print(f"Ganancia bruta en los médicos que suben: {eur(gan.eur.sum())} (la pérdida en los que bajan es {eur(-perdida)})")
display(concentracion)
deciles = (pd.DataFrame({"vis_hoy": v_act, "vis_plan": v_plan, "eur": delta_eur, "decil_volumen": pd.qcut(cat, 10, labels=False) + 1})
           .groupby("decil_volumen").agg(medicos=("eur", "size"), vis_hoy=("vis_hoy", "mean"), vis_plan=("vis_plan", "mean"), ventas_extra_eur=("eur", "sum")).round(1))
display(deciles)

fig, ax = plt.subplots(figsize=(7, 4.2))
ax.plot(np.arange(1, len(gan) + 1), 100 * gan.acum, color=C_PLAN, lw=2)
for q in [0.5, 0.8]:
    n_q, v_q = concentracion.loc[q, "medicos"], concentracion.loc[q, "visitas_anadidas"]
    ax.plot([n_q, n_q], [0, 100 * q], color=C_TINTA2, lw=0.8, ls=":"); ax.plot([0, n_q], [100 * q, 100 * q], color=C_TINTA2, lw=0.8, ls=":")
    ax.text(n_q + 15, 100 * q - 9, f"{int(q * 100)} % de la ganancia con {n_q} médicos\n({v_q:,} visitas añadidas)".replace(",", "."), fontsize=9, color=C_TINTA2)
ax.set_xlim(0, len(gan)); ax.set_ylim(0, 103)
ax.set_xlabel("Médicos que reciben más visitas, ordenados de mayor a menor ganancia"); ax.set_ylabel("% de la ganancia bruta acumulada")
ax.set_title("El valor está concentrado: la mitad sale de menos de 200 médicos")
guardar(fig, "07_concentracion_valor")

# %%
# b) Heterogeneidad de la respuesta
pred_fd = g(v25, D, h) - g(v24, D, h)
resid = dcuota - pred_fd
r2_fd = float(1 - resid.var() / dcuota.var())
grandes = np.abs(dvis) >= 3
ratio = (dcuota[grandes] / dvis[grandes]) / (pred_fd[grandes] / dvis[grandes])
info = med.set_index("id_medico").loc[W.index]
resid_df = pd.DataFrame({"resid": resid, "region": info.region.values, "delegado": info.id_delegado_asignado.values}).merge(dele.drop(columns="region"), left_on="delegado", right_on="id_delegado")
r2_deleg = sm.OLS(resid_df.resid, pd.get_dummies(resid_df.delegado, drop_first=True, dtype=float).assign(const=1.0)).fit().rsquared
r2_region = sm.OLS(resid_df.resid, pd.get_dummies(resid_df.region, drop_first=True, dtype=float).assign(const=1.0)).fit().rsquared
heterogeneidad = pd.Series({
    "R² de la curva sobre los cambios de cuota 2024 → 2025": r2_fd,
    "Desviación típica del cambio de cuota (pp)": 100 * dcuota.std(),
    "Desviación típica del residuo (pp)": 100 * resid.std(),
    "Médicos con |Δvisitas| ≥ 3": float(grandes.sum()),
    "Respuesta individual / modelo, percentil 25": float(np.percentile(ratio, 25)),
    "Respuesta individual / modelo, mediana": float(np.median(ratio)),
    "Respuesta individual / modelo, percentil 75": float(np.percentile(ratio, 75)),
    "% de esos médicos con respuesta de signo contrario": 100 * float((ratio < 0).mean()),
    "Varianza del residuo explicada por el delegado (R²)": float(r2_deleg),
    "Varianza del residuo explicada por la región (R²)": float(r2_region),
    "Correlación del residuo con la antigüedad del delegado": float(resid_df.resid.corr(resid_df.antiguedad_anos)),
})
display(heterogeneidad.round(3).to_frame("valor"))

fig, ax = plt.subplots(figsize=(6.2, 5))
ax.scatter(100 * pred_fd, 100 * dcuota, s=8, alpha=0.35, color=C_PLAN, edgecolor="none")
lim = [100 * min(pred_fd.min(), dcuota.min()) - 1, 100 * max(pred_fd.max(), dcuota.max()) + 1]
ax.plot(lim, lim, color=C_TINTA, lw=1, ls="--"); ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("Cambio de cuota que predice la curva (pp)"); ax.set_ylabel("Cambio de cuota observado 2024 → 2025 (pp)")
ax.set_title(f"Una sola curva explica el {100 * r2_fd:.0f} % de los cambios de cuota de los 2.000 médicos")
ax.grid(True, axis="both")
guardar(fig, "08_heterogeneidad_respuesta")

# %%
# c) El valor como distribución
rng_mc = np.random.default_rng(7)
N_MC = 4000
idx_b = rng_mc.integers(0, len(boot_params), N_MC)
f_causal = rng_mc.uniform(0.6, 1.0, N_MC)  # supuesto: entre el 60 % y el 100 % del efecto estimado es causal
f_ejec = rng_mc.uniform(0.7, 1.0, N_MC)  # supuesto: se ejecuta entre el 70 % y el 100 % de los cambios de frecuencia
mc = np.empty(N_MC)
for i in range(N_MC):
    Db, hb = boot_params[idx_b[i]]
    v_ej = v_act + f_ejec[i] * (v_plan - v_act)
    mc[i] = float((cat * (g(v_ej, Db * f_causal[i], hb) - g(v_act, Db * f_causal[i], hb))).sum() * PRECIO) / 1e6
montecarlo = pd.Series({"p10": np.percentile(mc, 10), "mediana": np.median(mc), "p90": np.percentile(mc, 90),
                        "P(> 1,0 M€)": (mc > 1).mean(), "P(> 1,5 M€)": (mc > 1.5).mean(), "P(> 2,0 M€)": (mc > 2).mean()})
display(montecarlo.round(2).to_frame("M€ o probabilidad"))

fig, ax = plt.subplots(figsize=(7, 4))
ax.hist(mc, bins=40, color=C_PLAN, alpha=0.85, edgecolor="white", linewidth=0.5)
top = ax.get_ylim()[1]
for k, ls in [("p10", ":"), ("mediana", "-"), ("p90", ":")]:
    ax.axvline(montecarlo[k], color=C_TINTA, lw=1.2, ls=ls)
    ax.text(montecarlo[k] - 0.01, top * 0.97, f"{k} {montecarlo[k]:.2f}", rotation=90, va="top", ha="right", fontsize=8.5, color=C_TINTA)
ax.axvline(valor_base / 1e6, color=C_TINTA, lw=1.2, ls="--")
ax.text(valor_base / 1e6 - 0.01, top * 0.97, f"estimación central {valor_base / 1e6:.2f}", rotation=90, va="top", ha="right", fontsize=8.5, color=C_TINTA)
ax.set_xlabel("Ventas adicionales el primer año (M€)"); ax.set_ylabel("Escenarios simulados")
ax.set_title("El valor como distribución: 4.000 escenarios de curva, selección y ejecución")
guardar(fig, "09_distribucion_valor")

# %%
# d) Ruido mensual y potencia del piloto
cuota_mes = pre.unidades_producto / pre.unidades_categoria
ruido = cuota_mes - cuota_mes.groupby(pre.id_medico).transform("mean")
sigma_mes = float(ruido.std())
sigma_6m = sigma_mes / np.sqrt(6)  # media de seis meses por médico
efectos = {"C o B: de 0 a 2 visitas": g(2, D, h) - g(0, D, h), "B: de 4 a 5 visitas": g(5, D, h) - g(4, D, h), "A: de 14 a 9 visitas": g(9, D, h) - g(14, D, h)}
potencia = pd.DataFrame(
    [{"cambio": k, "efecto_esperado_pp": 100 * e, "medicos_por_grupo_en_6_meses": max(2, int(np.ceil(2 * (1.96 + 0.84) ** 2 * sigma_6m ** 2 / e ** 2)))} for k, e in efectos.items()]
).set_index("cambio")
print(f"Desviación típica mensual de la cuota dentro del médico: {100 * sigma_mes:.1f} pp "
      f"(test de dos grupos, medias de 6 meses, 5 % de significación y 80 % de potencia)")
display(potencia.round(2))

# %% [markdown]
# ## 5. El plan, médico a médico y delegado a delegado
#
# Cada delegado conserva su número de visitas. Lo que cambia es a quién y cuántas veces.
# El fichero `output/plan_visitas_2026.xlsx` tiene tres hojas: resumen por segmento, plan por
# delegado y plan por médico (la target list con la frecuencia recomendada).

# %%
plan_med = pd.DataFrame({
    "id_delegado": base.id_delegado_asignado, "region": base.region, "segmento": seg,
    "categoria_2025": cat.astype(int), "cuota_2025": base.cuota.round(3),
    "visitas_2025": v_act.astype(int), "visitas_plan": v_plan.astype(int),
})
plan_med["delta_visitas"] = plan_med.visitas_plan - plan_med.visitas_2025
plan_med["delta_unidades"] = delta_unidades(v_plan, v_act).round(0).astype(int)
plan_med["delta_eur"] = (plan_med.delta_unidades * PRECIO).round(0).astype(int)
plan_med = plan_med.sort_values(["id_delegado", "segmento", "categoria_2025"], ascending=[True, True, False])

plan_del = plan_med.groupby("id_delegado").agg(
    region=("region", "first"), medicos=("segmento", "size"), visitas=("visitas_2025", "sum"),
    medicos_suben=("delta_visitas", lambda s: int((s > 0).sum())), medicos_bajan=("delta_visitas", lambda s: int((s < 0).sum())),
    visitas_movidas=("delta_visitas", lambda s: int(s.clip(lower=0).sum())),
    A_hoy=("visitas_2025", lambda s: s[plan_med.loc[s.index, "segmento"] == "A"].mean()),
    A_plan=("visitas_plan", lambda s: s[plan_med.loc[s.index, "segmento"] == "A"].mean()),
    B_hoy=("visitas_2025", lambda s: s[plan_med.loc[s.index, "segmento"] == "B"].mean()),
    B_plan=("visitas_plan", lambda s: s[plan_med.loc[s.index, "segmento"] == "B"].mean()),
    C_hoy=("visitas_2025", lambda s: s[plan_med.loc[s.index, "segmento"] == "C"].mean()),
    C_plan=("visitas_plan", lambda s: s[plan_med.loc[s.index, "segmento"] == "C"].mean()),
    ventas_extra_eur=("delta_eur", "sum"),
).join(dele.set_index("id_delegado")[["antiguedad_anos", "coste_visita_eur"]])
plan_del["pct_ventas_extra"] = plan_del.ventas_extra_eur / (base.groupby("id_delegado_asignado").unidades_producto.sum() * PRECIO)
display(plan_del.round(2).head(10))

plan_reg = plan_med.groupby("region").agg(medicos=("segmento", "size"), visitas=("visitas_2025", "sum"), ventas_extra_eur=("delta_eur", "sum"))
display(plan_reg)

resumen_plan = pd.DataFrame({"hoy": v_act.groupby(seg).mean(), "plan": v_plan.groupby(seg).mean(),
                             "plan_min": v_plan.groupby(seg).min(), "plan_max": v_plan.groupby(seg).max(),
                             "ventas_extra_eur": bridge}).round(2)
with pd.ExcelWriter(OUT / "plan_visitas_2026.xlsx", engine="openpyxl") as xw:
    resumen_plan.to_excel(xw, sheet_name="resumen_segmento")
    plan_del.round(2).to_excel(xw, sheet_name="plan_por_delegado")
    plan_med.to_excel(xw, sheet_name="plan_por_medico")
plan_med.to_csv(OUT / "plan_por_medico.csv")

suben, bajan = int((plan_med.delta_visitas > 0).sum()), int((plan_med.delta_visitas < 0).sum())
de_cero = int(((plan_med.visitas_2025 == 0) & (plan_med.visitas_plan > 0)).sum())
movidas = int(plan_med.delta_visitas.clip(lower=0).sum())
print(f"Médicos que suben: {suben} (de ellos {de_cero} pasan de 0 a alguna visita) | bajan: {bajan} | "
      f"visitas que cambian de médico: {movidas:,} de {presupuesto_25:,} ({movidas / presupuesto_25:.0%})")
print("Ningún delegado cambia su carga:", (plan_del.visitas == v_act.groupby(base.id_delegado_asignado).sum()).all())
print(f"Fase 1 posible: los {concentracion.loc[0.5, 'medicos']} médicos con mayor ganancia y {concentracion.loc[0.5, 'visitas_anadidas']:,} visitas añadidas "
      f"capturan la mitad de la ganancia bruta ({eur(gan.eur.sum() / 2)}).".replace(",", "."))

# %% [markdown]
# ## 6. Extensión: ¿y si cambia la premisa?
#
# Las mismas funciones responden a escenarios nuevos. Dos ejemplos que suelen salir en comité:
#
# - **¿Y si la capacidad no fuera fija?** Con el reparto óptimo, cada visita adicional vale
#   hoy entre 500 y 600 € de venta anual frente a un coste de 72 €. La conclusión no es
#   "recortar A", es que el esfuerzo comercial rinde mucho y está mal colocado.
# - **¿Y si hubiera que recortar un 10 % o un 20 % de visitas?** Bien repartidas, se seguiría
#   vendiendo más que hoy.

# %%
filas = []
for factor in [0.8, 0.9, 1.0, 1.1, 1.2]:
    b = int(round(presupuesto_25 * factor))
    v_b = asignacion_optima(cat, b)
    filas.append({"visitas": b, "vs_hoy": f"{factor - 1:+.0%}", "ventas_extra_M€": valor_plan(v_b) / 1e6,
                  "coste_extra_M€": (b - presupuesto_25) * COSTE_VISITA / 1e6})
sens_capacidad = pd.DataFrame(filas).set_index("visitas")
sens_capacidad["margen_extra_M€"] = sens_capacidad["ventas_extra_M€"] - sens_capacidad["coste_extra_M€"]
display(sens_capacidad.round(2))
# Valor marginal de una visita más en el óptimo (para el ejercicio de extensión)
v_mas = asignacion_optima(cat, presupuesto_25 + 500)
print("Valor medio de cada una de las 500 visitas siguientes, en el óptimo:", f"{(valor_plan(v_mas) - valor_plan(v_global)) / 500:,.0f} €")

# %% [markdown]
# ## 7. Cifras finales

# %%
resumen = {
    "ventas_2025_eur": round(float(ventas[2025])),
    "cuota_global_2025": round(float(cuota_global[2025]), 4),
    "visitas_2025_validas": presupuesto_25,
    "visitas_duplicadas_eliminadas": int(dup.sum()),
    "pct_visitas_decima_o_posterior": round(visitas_10mas / presupuesto_25, 3),
    "medicos_ano_sin_visitas": int((dy.visitas == 0).sum()),
    "medicos_sin_visitas_2025": int((v_act == 0).sum()),
    "mal_segmentados": mal_segmentados,
    "visitas_por_medico_hoy": v_act.groupby(seg).mean().round(1).to_dict(),
    "visitas_por_medico_plan": v_plan.groupby(seg).mean().round(1).to_dict(),
    "regla_sencilla": regla.to_dict(),
    "curva": {"D": round(D, 4), "h": round(h, 3), "cuota_base": round(s0, 4), "techo": round(s0 + D, 4)},
    "cuota_0_visitas": round(float(dy[dy.visitas == 0].cuota.mean()), 4),
    "cuota_3_5_visitas": round(float(dy[dy.tramo == "3-5"].cuota.mean()), 4),
    "cuota_10_mas_visitas": round(float(dy[dy.visitas >= 10].cuota.mean()), 4),
    "pp_por_visita_desde_0": round(float(fd_niveles.loc["0", "pp_cuota_por_visita"]), 2),
    "pp_por_visita_desde_10_14": round(float(fd_niveles.loc["10-14", "pp_cuota_por_visita"]), 2),
    "pp_por_visita_desde_20": round(float(fd_niveles.loc["20+", "pp_cuota_por_visita"]), 2),
    "eur_visita_k_mediano": {s: {int(k): int(k_val.loc[k, s]) for k in [1, 2, 5, 10, 14, 20]} for s in "ABC"},
    "valor_plan_eur": round(valor_base),
    "valor_plan_pct_ventas": round(valor_base / float(ventas[2025]), 3),
    "valor_por_segmento_eur": {s: round(float(v)) for s, v in bridge.items()},
    "cuota_global_plan": round(float(resumen_esc.loc["Plan (óptimo por delegado)", "cuota_global"]), 4),
    "valor_optimo_global_eur": round(valor_plan(v_global)),
    "valor_regla_sencilla_eur": round(valor_plan(v_regla)),
    "valor_nadie_a_cero_eur": round(valor_plan(v_nadie0)),
    "rango_robustez_M€": [round(rango_prudente[0], 2), round(rango_prudente[1], 2)],
    "bootstrap_ic95_M€": [round(ic_boot[0] / 1e6, 2), round(ic_boot[1] / 1e6, 2)],
    "medicos_suben": suben, "medicos_bajan": bajan, "medicos_de_cero_a_visitados": de_cero,
    "visitas_que_cambian_de_medico": movidas,
    "valor_visita_extra_en_optimo_eur": round((valor_plan(v_mas) - valor_plan(v_global)) / 500),
    "concentracion_valor": {f"medicos_{int(q * 100)}pct": int(concentracion.loc[q, "medicos"]) for q in [0.5, 0.8, 0.9]}
    | {f"visitas_{int(q * 100)}pct": int(concentracion.loc[q, "visitas_anadidas"]) for q in [0.5, 0.8, 0.9]},
    "r2_curva_sobre_cambios": round(r2_fd, 3),
    "respuesta_individual_vs_modelo_p25_mediana_p75": [round(float(np.percentile(ratio, 25)), 2), round(float(np.median(ratio)), 2), round(float(np.percentile(ratio, 75)), 2)],
    "montecarlo_M€": {k: round(float(v), 2) for k, v in montecarlo.items()},
    "sigma_mensual_cuota_pp": round(100 * sigma_mes, 2),
    "piloto_medicos_por_grupo_6_meses": potencia.medicos_por_grupo_en_6_meses.to_dict(),
}
(OUT / "resumen_cifras.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(resumen, indent=2, ensure_ascii=False))

# Datos detrás de cada gráfico, para reproducirlos en la presentación
datos_graficos = {
    "01_distribucion_visitas_2025": {s: dist[s].astype(int).to_dict() for s in "ABC"},
    "02_pp_cuota_por_visita_segun_nivel_2024": fd_niveles.pp_cuota_por_visita.round(2).to_dict(),
    "03_curva": {
        "observado_por_segmento": {s: curva_obs.loc[s][["visitas", "cuota", "n"]].round(3).to_dict("index") for s in "ABC"},
        "curva_valoracion_pct": {int(v): round(100 * (s0 + g(v, D, h)), 1) for v in range(0, 31)},
        "curva_niveles_pct": {int(v): round(100 * (res_niv.x[0] + g(v, *ajustes["Niveles (todos)"])), 1) for v in range(0, 31)},
        "visitas_hoy_por_segmento": v_act.groupby(seg).mean().round(1).to_dict(),
    },
    "04_eur_visita_k_medico_mediano": {s: {int(k): int(v) for k, v in k_val[s].items()} for s in "ABC"},
    "05_puente_M€": {"perdida_en_medicos_que_bajan": round(perdida / 1e6, 3), "n_medicos_bajan": int(n_bajan.sum()),
                     **{f"ganancia_{s}": round(float(ganancia[s]) / 1e6, 3) for s in "ABC"},
                     **{f"n_medicos_suben_{s}": int((v_plan > v_act)[seg == s].sum()) for s in "ABC"}, "neto": round(valor_base / 1e6, 3)},
    "06_frecuencia_hoy_vs_plan": resumen_plan[["hoy", "plan", "plan_min", "plan_max"]].round(1).to_dict("index"),
    "escenarios": resumen_esc.round(3).to_dict("index"),
    "robustez_M€": robustez["ventas_extra_M€"].round(2).to_dict(),
    "sensibilidad_capacidad": sens_capacidad.round(2).to_dict("index"),
    "plan_por_region_eur": plan_reg.to_dict("index"),
    "efecto_mensual_pp": efecto_mensual.pp_cuota.to_dict(),
    "07_concentracion": {"tabla": concentracion.to_dict("index"), "curva_pct_acumulado_cada_50_medicos": {int(i): round(100 * float(gan.acum.iloc[i - 1]), 1) for i in range(50, len(gan) + 1, 50)}},
    "07b_deciles_volumen": deciles.to_dict("index"),
    "08_heterogeneidad": {k: round(float(v), 3) for k, v in heterogeneidad.items()},
    "09_montecarlo": {"resumen": {k: round(float(v), 3) for k, v in montecarlo.items()}, "histograma": {f"{a:.2f}-{b:.2f}": int(c) for c, a, b in zip(*np.histogram(mc, bins=20), np.histogram(mc, bins=20)[1][1:])},
                      "supuestos": "curva por bootstrap; parte causal U(0,6; 1,0); ejecución U(0,7; 1,0)"},
    "10_potencia_piloto": potencia.round(2).to_dict("index"),
    "auditoria_datos": auditoria_df.to_dict("records"),
}
(OUT / "datos_graficos.json").write_text(json.dumps(datos_graficos, indent=2, ensure_ascii=False), encoding="utf-8")

# %% [markdown]
# ## 8. Límites y supuestos
#
# - **Identificación.** La curva se estima con cambios dentro del mismo médico entre 2024 y
#   2025, lo que elimina diferencias fijas entre médicos. No elimina un posible sesgo por
#   tendencias: si los delegados empezaron a visitar a médicos cuya cuota ya subía, el efecto
#   estaría algo sobreestimado. Los 153 médicos que pasaron de 0 visitas en 2024 a alguna en
#   2025 muestran una cuota algo superior a la media de no visitados ya antes de la primera
#   visita, así que el sesgo existe y es moderado; por eso se da un rango y no un solo número.
# - **Misma curva para todos.** Se asume que la ganancia de cuota por visita depende del número
#   de visitas y no del segmento; los ajustes por segmento son muy parecidos (tabla 2.4) y la
#   valoración con curvas separadas cambia el valor en menos de 0,3 M€. La curva explica el 90 %
#   de los cambios de cuota y el residuo no se relaciona con región, delegado ni antigüedad
#   (sección 4.2): la media no esconde subgrupos.
# - **Escenarios de la sección 4.2.** Los rangos de "parte causal" (60 a 100 %) y "ejecución"
#   (70 a 100 %) son supuestos de juicio, no estimaciones; sirven para dar una distribución
#   prudente del valor, no para sustituir la estimación central.
# - **Potencial estable.** El volumen de categoría de cada médico cambia poco entre años
#   (correlación 0,998), así que 2025 sirve como base para 2026.
# - **Efecto simétrico.** Se asume que quitar visitas a un A le baja la cuota tanto como
#   dárselas se la sube. Los datos lo respaldan (sección 2.2) y ese coste está descontado en
#   el valor del plan.
# - **Sin efectos cruzados ni de competencia.** No hay datos de la actividad de competidores ni
#   de reacción a la nuestra; el periodo no tiene lanzamientos ni cambios de precio.
# - **Coste.** El plan mantiene las visitas de cada delegado, así que el coste total no cambia.
#   Las diferencias de coste por delegado (59 a 91 €) no se usan porque no se mueven visitas
#   entre delegados.
# - **Datos.** 255 visitas duplicadas eliminadas (sensibilidad en 4.1); las fechas se reparten
#   por igual entre los siete días de la semana, así que no se hace ningún análisis por día;
#   los códigos de brick se repiten entre Noreste y Noroeste (no se usan bricks en el análisis).
