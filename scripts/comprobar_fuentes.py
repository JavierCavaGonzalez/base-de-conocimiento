"""Comprueba que el contenido cita fuentes registradas y que lo aprobado no tiene huecos.

Uso:
    python scripts/comprobar_fuentes.py [ruta ...] [--citas] [--silencioso]

Sin rutas revisa todos los .md y .qmd del repositorio salvo plantillas, skills, informes y salidas.
Funciona igual en el repositorio privado (fuentes/registro.yml) y en el público (fuentes.yml).

Errores (devuelve 1):
  - cabecera YAML inválida;
  - `fuentes:` con un id que no está en el registro;
  - `estado` desconocido;
  - archivo con `estado: aprobado` o `final` (o `publicacion: aprobado`) que contiene
    `[no verificado`, `[sugerencia]`, `[paso por confirmar]`, `[por comprobar`, `[cliente]` o un id `pendiente-...`;
  - registro con ids repetidos o entradas sin id, tipo o título.
Avisos (no bloquean): marcas `[no verificado` en borradores, ids `pendiente-...` en borradores,
  fuentes registradas sin URL ni ISBN, menciones a herramientas de IA (hay que revisar si son
  una cita de fuente o una mención de herramienta).

--citas lista, por archivo, las fuentes de la cabecera y las citas en línea encontradas,
  para que `/verificar-fuentes` las compruebe una por una.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from comun import RAIZ, cargar_registro, leer_cabecera

EXCLUIR_DIRS = {"plantillas", "_plantillas", ".claude", "verificaciones", "tareas-programadas", "_site", "_libro", ".quarto", "node_modules", ".git", "charlas", "plataformas", "vigilancia", "progreso", "suscriptores/pendiente-envio"}
EXCLUIR_ARCHIVOS = {"README.md", "CLAUDE.md", "LICENSE-CONTENIDO.md", "pull_request_template.md"}
ESTADOS = {"borrador", "aprobado", "final", "pendiente", "leyendo", "terminado"}
MARCAS_BLOQUEO = ("[no verificado", "[sugerencia]", "[paso por confirmar]", "[por comprobar", "[cliente]")
HERRAMIENTAS_IA = re.compile(r"\b(Claude|Anthropic|ChatGPT|OpenAI|Gemini|Co-Authored-By)\b", re.I)
CITA_EN_LINEA = re.compile(r"\(([^()\n]*?(?:\b(?:19|20)\d{2}\b|Microsoft Learn)[^()\n]*?)\)")


def archivos_objetivo(rutas: list[str]) -> list[Path]:
    if rutas:
        salida = []
        for r in rutas:
            p = (RAIZ / r) if not Path(r).is_absolute() else Path(r)
            if p.is_dir():
                salida.extend(sorted(x for x in p.rglob("*") if x.suffix in (".md", ".qmd")))
            else:
                salida.append(p)
        return salida
    salida = []
    for p in sorted(RAIZ.rglob("*")):
        if p.suffix not in (".md", ".qmd") or not p.is_file():
            continue
        rel = p.relative_to(RAIZ)
        partes = set(rel.parts[:-1])
        if partes & EXCLUIR_DIRS or any(str(rel).startswith(d + "/") for d in EXCLUIR_DIRS):
            continue
        if rel.name in EXCLUIR_ARCHIVOS:
            continue
        salida.append(p)
    return salida


def comprobar_registro(errores: list[str], avisos: list[str]) -> set[str]:
    fuentes, ruta = cargar_registro()
    rel = ruta.relative_to(RAIZ) if ruta.exists() else ruta.name
    vistos: set[str] = set()
    for f in fuentes:
        if not isinstance(f, dict) or not f.get("id"):
            errores.append(f"{rel}: entrada sin id: {f!r}")
            continue
        fid = str(f["id"])
        if fid in vistos:
            errores.append(f"{rel}: id repetido: {fid}")
        vistos.add(fid)
        for clave in ("tipo", "titulo"):
            if not f.get(clave):
                errores.append(f"{rel}: la fuente {fid} no tiene {clave}")
        if not f.get("url") and not f.get("isbn"):
            avisos.append(f"{rel}: la fuente {fid} no tiene url ni isbn")
    return vistos


def comprobar_archivo(p: Path, ids: set[str], errores: list[str], avisos: list[str], citas: bool) -> None:
    rel = p.relative_to(RAIZ) if p.is_relative_to(RAIZ) else p
    try:
        cab, cuerpo = leer_cabecera(p)
    except Exception as e:
        errores.append(f"{rel}: {e}")
        return
    texto = p.read_text(encoding="utf-8")
    if cab is None:
        cab = {}
    estado = cab.get("estado")
    if estado is not None and str(estado) not in ESTADOS:
        errores.append(f"{rel}: estado desconocido «{estado}» (válidos: {', '.join(sorted(ESTADOS))})")
    aprobado = str(estado) in ("aprobado", "final") or str(cab.get("publicacion", "")) == "aprobado"

    lista = cab.get("fuentes")
    ids_archivo: list[tuple[str, str]] = []
    if lista is None:
        lista = []
    if not isinstance(lista, list):
        errores.append(f"{rel}: `fuentes` tiene que ser una lista")
        lista = []
    for f in lista:
        if isinstance(f, dict):
            fid, apartado = str(f.get("id", "")), str(f.get("apartado", "") or "")
        else:
            fid, apartado = str(f), ""
        if not fid:
            errores.append(f"{rel}: fuente sin id en la cabecera")
            continue
        ids_archivo.append((fid, apartado))
        if fid.startswith("pendiente-"):
            (errores if aprobado else avisos).append(f"{rel}: fuente pendiente de registrar: {fid}")
        elif fid not in ids:
            errores.append(f"{rel}: la fuente «{fid}» no está en el registro")
        elif not apartado and isinstance(f, dict) and p.suffix == ".md" and "diario" in rel.parts:
            avisos.append(f"{rel}: la fuente {fid} no indica apartado")

    for marca in MARCAS_BLOQUEO:
        n = texto.count(marca)
        if n:
            (errores if aprobado else avisos).append(f"{rel}: {n} marca(s) {marca}" + ("" if aprobado else " (borrador)"))

    for m in HERRAMIENTAS_IA.finditer(texto):
        linea = texto.count("\n", 0, m.start()) + 1
        avisos.append(f"{rel}:{linea}: menciona «{m.group(0)}»; revisa que sea una cita de fuente y no una mención de herramienta")

    if citas:
        print(f"\n== {rel} (estado: {estado or '—'})")
        if ids_archivo:
            print("  Fuentes de la cabecera:")
            for fid, apartado in ids_archivo:
                print(f"    - {fid}" + (f" · {apartado}" if apartado else " · (sin apartado)"))
        else:
            print("  Sin fuentes en la cabecera.")
        encontradas = 0
        for i, linea in enumerate(cuerpo.splitlines(), start=1 + texto[: len(texto) - len(cuerpo)].count("\n")):
            for m in CITA_EN_LINEA.finditer(linea):
                encontradas += 1
                frase = linea.strip()
                if len(frase) > 160:
                    ini = max(0, m.start() - 100)
                    frase = "…" + linea[ini : m.end() + 20].strip() + "…"
                print(f"    {i}: ({m.group(1)}) ← {frase}")
        if not encontradas:
            print("  Sin citas en línea con año o «Microsoft Learn».")


def main(argv: list[str]) -> int:
    citas = "--citas" in argv
    silencioso = "--silencioso" in argv
    rutas = [a for a in argv if not a.startswith("--")]
    errores: list[str] = []
    avisos: list[str] = []
    ids = comprobar_registro(errores, avisos)
    archivos = archivos_objetivo(rutas)
    for p in archivos:
        if not p.exists():
            errores.append(f"{p}: no existe")
            continue
        comprobar_archivo(p, ids, errores, avisos, citas)
    if not silencioso:
        for a in avisos:
            print(f"AVISO  {a}")
    for e in errores:
        print(f"ERROR  {e}")
    print(f"\n{len(archivos)} archivos, {len(ids)} fuentes registradas, {len(errores)} errores, {len(avisos)} avisos.")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
