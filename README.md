# Horarios VIP

Horario de los trabajadores de las tiendas VIP (Deporte VIP Alcázar, Street VIP, Outlet VIP y Deporte VIP Tomelloso), solo de consulta.

- `index.html`: la página que ven los trabajadores.
- `months.json`: lista de meses publicados; la página abre el mes actual y deja pasar de un mes a otro.
- `data-AAAA-MM.json`: el cuadrante de cada mes, exportado desde "Horarios VIP" sin motivos de ausencias.
- `data.json`: copia del mes actual (por compatibilidad).
- `tools/export.py`: el script que genera `data.json`.
