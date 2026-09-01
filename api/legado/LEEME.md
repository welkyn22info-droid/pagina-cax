Esta carpeta se llena desde la máquina enterprise con el código Python real
de valoración, pasivo, funding ratio y cupos, junto con `README_LEGADO.md` y
`contrato_datos.md` (sección 21 de la especificación, Tarea 1 y 3).

No contiene código todavía. `api/legado/*.py` está excluido por
`.gitignore` para que ningún archivo real de CAXDAC se suba a este
repositorio compartido por accidente. Ver `DECISIONES.md` en la raíz.

Mientras tanto, el flujo completo se prueba con funciones equivalentes en
`api/app/legado_simulado/`, con las mismas firmas documentadas en
`DECISIONES.md`. El día que el código real llegue aquí, cada envoltorio en
`api/app/motor/procesos/` cambia una sola línea de import.
