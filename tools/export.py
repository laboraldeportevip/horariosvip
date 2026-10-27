"""Exporta un mes de "Horarios VIP" a data.json de solo lectura para la web de los trabajadores.

Uso: python3 export.py <carpeta_db> <AAAA-MM> <salida.json>
La carpeta_db contiene months/<AAAA-MM>.json, workers/*.json y config/calendar.json
(tal como los guarda ArtifactData con out_dir).

Privacidad: no se exportan motivos ni notas. Vacaciones salen como "Vacaciones";
cualquier otra ausencia (baja, médico, descanso pedido, compensación...) sale como "Libre".
"""
import calendar
import datetime
import glob
import json
import os
import sys

STORES = {
    "dv": {"name": "Deporte VIP Alcázar", "short": "01 Alcázar", "loc": "alc"},
    "dt": {"name": "Deporte VIP Tomelloso", "short": "02 Tomelloso", "loc": "tom"},
    "sv": {"name": "Street VIP", "short": "04 Street", "loc": "alc"},
    "ov": {"name": "Outlet VIP", "short": "05 Outlet", "loc": "alc"},
}
ORDER = ["dv", "sv", "ov", "dt"]


def main(base, ym, out):
    month = json.load(open(os.path.join(base, "months", ym + ".json")))
    cal = json.load(open(os.path.join(base, "config", "calendar.json")))
    workers = {}
    for f in glob.glob(os.path.join(base, "workers", "*.json")):
        wid = os.path.basename(f)[:-5]
        workers[wid] = json.load(open(f))

    y, m = map(int, ym.split("-"))
    ndays = calendar.monthrange(y, m)[1]
    a = month.get("a") or {}
    absences = month.get("abs") or {}

    def iso(d):
        return f"{y:04d}-{m:02d}-{d:02d}"

    def dow(d):  # 0 = domingo, como en el panel
        return (datetime.date(y, m, d).weekday() + 1) % 7

    def is_open_override(loc, d):
        return iso(d) in ((cal.get("open") or {}).get(loc) or {})

    def hol_name(loc, d):
        return ((cal.get("closed") or {}).get(loc) or {}).get(iso(d))

    def closed(loc, d):
        if is_open_override(loc, d):
            return False
        return dow(d) == 0 or bool(hol_name(loc, d))

    def resolve(wid, d):
        w = workers.get(wid, {})
        ab = (absences.get(wid) or {}).get(str(d))
        if ab and not ab.get("c"):
            ab = None
        r = (a.get(wid) or {}).get(str(d))
        o, explicit = {}, False
        if r:
            for k, v in r.items():
                if k in ("_", "m"):
                    explicit = explicit or bool(v)
                    continue
                if v:
                    o[k] = v
                    explicit = True
        absent = bool(ab) and not ab.get("h")
        if not explicit:
            f = (w.get("fixed") or {}).get(str(dow(d)))
            if f and w.get("base") and not absent:
                if isinstance(f, str):
                    if not closed(STORES[w["base"]]["loc"], d):
                        o[w["base"]] = f
                else:
                    for k, v in f.items():
                        if k in STORES and not closed(STORES[k]["loc"], d):
                            o[k] = v
        if absent:
            o = {}
        if ab and ab.get("h"):
            h = ab["h"]
            for k in list(o):
                if o[k] == "C":
                    o[k] = "T" if h == "M" else "M"
                elif o[k] == h:
                    del o[k]
        # baja automática por fechas de la ficha
        if w.get("bajaHasta") and iso(d) <= w["bajaHasta"] and (not w.get("bajaDesde") or iso(d) >= w["bajaDesde"]):
            if not (r and explicit):
                o, ab = {}, {"c": "B"}
        return o, ab

    people = []
    for wid, w in sorted(workers.items(), key=lambda kv: (kv[1].get("order", 99), kv[1].get("name", ""))):
        if w.get("active") is False or w.get("soloNomina"):
            continue
        days = []
        any_entry = False
        for d in range(1, ndays + 1):
            o, ab = resolve(wid, d)
            shifts = [{"s": k, "t": o[k]} for k in ORDER if o.get(k) in ("M", "T", "C")]
            if shifts:
                any_entry = True
                days.append({"d": d, "shifts": shifts})
            elif ab and ab.get("c") == "V":
                any_entry = True
                days.append({"d": d, "off": "Vacaciones"})
            else:
                days.append({"d": d, "off": "Libre"})
        if any_entry:
            people.append({"id": wid, "name": w.get("name", wid), "days": days})

    closures = {}
    for d in range(1, ndays + 1):
        info = {}
        for loc in ("alc", "tom"):
            if is_open_override(loc, d) and dow(d) == 0:
                info[loc] = "Abre (domingo de apertura)"
            elif is_open_override(loc, d):
                info[loc] = "Abre (festivo de apertura)"
            elif hol_name(loc, d):
                info[loc] = "Cerrado: " + hol_name(loc, d)
        if info:
            closures[str(d)] = info

    data = {
        "ym": ym,
        "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
        "stores": STORES,
        "shifts": {"M": "Mañana · 10–14", "T": "Tarde · 17–21", "C": "Completo · 10–14 y 17–21"},
        "days": closures,
        "people": people,
    }
    with open(out, "w") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print(f"{len(people)} personas exportadas a {out}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
