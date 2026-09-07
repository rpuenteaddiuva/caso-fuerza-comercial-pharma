"""Convierte analisis.py (celdas marcadas con '# %%') en analisis.ipynb y lo ejecuta.

Uso, desde la raíz del repositorio:  python tools/build_notebook.py
"""

import asyncio
import os
import re
import sys
from pathlib import Path

if sys.platform == "win32":  # evita que el cliente del kernel se quede colgado al cerrar en Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
os.environ.pop("MPLBACKEND", None)  # el kernel debe usar el backend inline para incrustar los gráficos

import nbformat  # noqa: E402
from nbconvert.preprocessors import ExecutePreprocessor  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "analisis.py").read_text(encoding="utf-8")

cells = []
for bloque in re.split(r"^# %%", src, flags=re.M)[1:]:
    cabecera, _, cuerpo = bloque.partition("\n")
    cuerpo = cuerpo.strip("\n")
    if "[markdown]" in cabecera:
        texto = "\n".join(l[2:] if l.startswith("# ") else l.lstrip("#") for l in cuerpo.splitlines())
        cells.append(nbformat.v4.new_markdown_cell(texto))
    else:
        cells.append(nbformat.v4.new_code_cell(cuerpo))

nb = nbformat.v4.new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nb.metadata["language_info"] = {"name": "python"}

kernel = sys.argv[1] if len(sys.argv) > 1 else "python3"
ExecutePreprocessor(timeout=1800, kernel_name=kernel).preprocess(nb, {"metadata": {"path": str(ROOT)}})
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbformat.write(nb, ROOT / "analisis.ipynb")
imagenes = sum(1 for c in nb.cells if c.cell_type == "code" for o in c.outputs if o.output_type == "display_data" and "image/png" in o.get("data", {}))
print(f"analisis.ipynb: {len(cells)} celdas ejecutadas con el kernel '{kernel}', {imagenes} gráficos incrustados")
if imagenes == 0:
    sys.exit("Ningún gráfico incrustado: el kernel no usó el backend inline")
