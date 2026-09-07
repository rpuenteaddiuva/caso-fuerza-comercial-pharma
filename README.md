# ¿Está bien asignado el esfuerzo comercial?

Caso práctico de Business Insights sobre la fuerza comercial de un laboratorio farmacéutico:
50 delegados, 2.000 médicos, dos años de visitas y prescripción (2024-2025). La pregunta de
Dirección Comercial: ¿está bien asignado el esfuerzo de visita? Si no, ¿dónde, qué cambiar y
cuánto vale el cambio, con la misma plantilla?

## Tesis

La regla actual (A ≈ 13 visitas al año, B ≈ 4, C ≈ 1,5) sigue bien el potencial, pero la
respuesta del médico a la visita **se satura a partir de 8-10 visitas al año**, y la curva es
la misma para A, B y C. Hoy el 22,5 % de las visitas son la décima o posterior al mismo médico
mientras 1.000 médicos-año no reciben ninguna. Reasignando las mismas visitas dentro de la
cartera de cada delegado (**≈ 9-10 / 5 / 2** visitas al año para A / B / C, ajustadas por volumen)
se ganan **≈ 2,4 M€ de ventas al año (+8 %)** a coste cero.

## Contenido

| Ruta | Qué es |
|---|---|
| `analisis.ipynb` | Notebook ejecutado con todo el análisis, tablas y gráficos |
| `analisis.py` | El mismo análisis como script (celdas `# %%`); es la fuente del notebook |
| `tools/build_notebook.py` | Regenera y ejecuta `analisis.ipynb` a partir de `analisis.py` |
| `2_datos/` | Los cuatro CSV del caso, sin modificar |
| `3_enunciado.docx` | Enunciado del caso y diccionario de datos |
| `output/` | Gráficos (`*.png`), plan de visitas por delegado y por médico (`plan_visitas_2026.xlsx`) y cifras finales (`resumen_cifras.json`) |

## Cómo ejecutarlo

```bash
pip install -r requirements.txt
python analisis.py                 # ejecuta todo y regenera output/
python tools/build_notebook.py     # opcional: reconstruye analisis.ipynb ejecutado
```

Python 3.12. Todo se ejecuta desde la raíz del repositorio en unos 30 segundos.

## Método en tres líneas

1. **Datos y diagnóstico:** auditoría de calidad de los cuatro ficheros con la decisión tomada
   ante cada imperfección (sección 0.1), reparto de visitas por segmento y distribución por
   médico (sección 1).
2. **Respuesta a la visita:** curva de saturación `cuota = base + D·v/(v+h)` estimada sobre
   cambios dentro del mismo médico entre 2024 y 2025, validada contra el corte transversal, un
   panel mensual con efectos fijos y ajustes por segmento (sección 2).
3. **Reasignación:** con la curva y el volumen de categoría de cada médico se reparten las
   visitas de cada delegado a quien más aporta (asignación greedy, óptima por concavidad), se
   valora en euros y se comprueba la robustez con bootstrap y curvas alternativas (secciones 3 a 6).
4. **Distribuciones:** concentración del valor entre médicos, heterogeneidad de la respuesta,
   el valor como distribución de 4.000 escenarios y potencia del piloto (sección 4.2).

Supuestos y límites, en la sección 8 del notebook.
