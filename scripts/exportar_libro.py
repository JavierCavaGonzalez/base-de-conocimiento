"""Monta un proyecto de libro Quarto (PDF y EPUB) a partir del sitio.

Uso:
    python scripts/exportar_libro.py --perfil gratis   [--salida _libro]
    python scripts/exportar_libro.py --perfil completo --privado ../estudio-privado [--salida _libro] [--incluir-borradores]

Perfiles:
  gratis    capítulos de libro/ y los enunciados públicos de ejercicios/ (lo mismo que la web).
  completo  igual, pero los ejercicios se toman enteros, con solución, del repositorio privado
            (suscriptores/ejercicios/*.qmd). Solo los que tengan estado aprobado o final, salvo
            --incluir-borradores. Es la edición para suscriptores.

Después:  quarto render <salida> --to pdf   |   quarto render <salida> --to epub
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
CABECERA = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?", re.S)
MARCA_SOLUCION = "<!-- solucion -->"


def cabecera(ruta: Path) -> dict:
    m = CABECERA.match(ruta.read_text(encoding="utf-8"))
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--perfil", choices=("gratis", "completo"), required=True)
    ap.add_argument("--privado", default="../estudio-privado")
    ap.add_argument("--salida", default="_libro")
    ap.add_argument("--incluir-borradores", action="store_true")
    ap.add_argument("--titulo", default="IA y agentes en Business Central")
    ap.add_argument("--autor", default="Javier Cava González")
    args = ap.parse_args(argv)

    salida = (RAIZ / args.salida).resolve()
    if salida.exists():
        shutil.rmtree(salida)
    (salida / "libro").mkdir(parents=True)
    (salida / "ejercicios").mkdir(parents=True)

    sitio = yaml.safe_load((RAIZ / "_quarto.yml").read_text(encoding="utf-8"))
    capitulos: list[str] = []
    for barra in sitio.get("website", {}).get("sidebar", []):
        if barra.get("id") != "libro":
            continue
        for item in barra.get("contents", []):
            if isinstance(item, dict) and "contents" in item:
                for sub in item["contents"]:
                    ruta = sub if isinstance(sub, str) else sub.get("href")
                    if ruta and ruta != "libro/index.qmd":
                        capitulos.append(ruta)
    if not capitulos:
        capitulos = sorted(str(p.relative_to(RAIZ)) for p in (RAIZ / "libro").glob("*.qmd") if p.name != "index.qmd")

    for rel in capitulos:
        origen = RAIZ / rel
        if not origen.exists():
            print(f"AVISO: no existe {rel}; se omite")
            continue
        if str(cabecera(origen).get("estado", "")) == "pendiente":
            print(f"Omitido (pendiente de escribir): {rel}")
            continue
        shutil.copy2(origen, salida / "libro" / origen.name)
    for extra in ("img", "capturas"):
        if (RAIZ / "libro" / extra).is_dir():
            shutil.copytree(RAIZ / "libro" / extra, salida / "libro" / extra)

    ejercicios: list[Path] = []
    if args.perfil == "completo":
        privado = Path(args.privado)
        if not privado.is_absolute():
            privado = (RAIZ / privado).resolve()
        carpeta = privado / "suscriptores" / "ejercicios"
        if not carpeta.is_dir():
            sys.exit(f"No existe {carpeta}. Indica --privado con la ruta del repositorio privado.")
        for p in sorted(carpeta.glob("*.qmd")):
            if p.name.endswith(".publico.qmd"):
                continue
            estado = str(cabecera(p).get("estado", "borrador"))
            if estado not in ("aprobado", "final") and not args.incluir_borradores:
                print(f"Omitido (estado {estado}): {p.name}")
                continue
            texto = p.read_text(encoding="utf-8").replace(MARCA_SOLUCION + "\n", "")
            (salida / "ejercicios" / p.name).write_text(texto, encoding="utf-8")
            ejercicios.append(salida / "ejercicios" / p.name)
    else:
        for p in sorted((RAIZ / "ejercicios").glob("*.qmd")):
            if p.name == "index.qmd":
                continue
            shutil.copy2(p, salida / "ejercicios" / p.name)
            ejercicios.append(salida / "ejercicios" / p.name)

    portada = (RAIZ / "libro" / "index.qmd").read_text(encoding="utf-8")
    m = CABECERA.match(portada)
    cuerpo_portada = portada[m.end():] if m else portada
    cuerpo_portada = cuerpo_portada.replace("](01-", "](libro/01-")
    edicion = "Edición completa para suscriptores (con soluciones)" if args.perfil == "completo" else "Edición gratuita (sin soluciones)"
    (salida / "index.qmd").write_text(f"---\ntitle: \"Prólogo\"\n---\n\n{edicion}. Generado desde la web; la versión viva está en https://javiercavagonzalez.github.io/base-de-conocimiento/\n\n{cuerpo_portada}", encoding="utf-8")

    for f in ("fuentes.yml", "styles.css"):
        if (RAIZ / f).exists():
            shutil.copy2(RAIZ / f, salida / f)

    config = {
        "project": {"type": "book", "output-dir": "_book"},
        "lang": "es",
        "book": {
            "title": args.titulo,
            "subtitle": "¿Le darías las llaves del ERP a un agente?" + (" · edición completa" if args.perfil == "completo" else ""),
            "author": args.autor,
            "chapters": ["index.qmd"] + [f"libro/{Path(c).name}" for c in capitulos if (salida / "libro" / Path(c).name).exists()],
            "appendices": [f"ejercicios/{e.name}" for e in ejercicios],
        },
        "format": {
            "pdf": {"documentclass": "scrbook", "toc": True, "number-sections": True, "colorlinks": True},
            "epub": {"toc": True, "number-sections": True},
        },
        "execute": {"enabled": False},
    }
    (salida / "_quarto.yml").write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Libro montado en {salida} ({len(capitulos)} capítulos, {len(ejercicios)} ejercicios, perfil {args.perfil}).")
    print(f"Ahora: quarto render {args.salida} --to epub   |   quarto render {args.salida} --to pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
