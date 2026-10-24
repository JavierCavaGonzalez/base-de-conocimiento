"""Funciones comunes de los scripts del repositorio.

Requiere Python 3.11 o superior y PyYAML (`pip install pyyaml`).
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent

CABECERA = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?", re.S)


def hoy() -> dt.date:
    """Fecha de hoy en la zona horaria de Javi (Europe/Madrid)."""
    try:
        from zoneinfo import ZoneInfo

        return dt.datetime.now(ZoneInfo("Europe/Madrid")).date()
    except Exception:  # sin base de datos de zonas horarias
        return dt.date.today()


def semana_iso(fecha: dt.date) -> str:
    """Semana ISO con el formato AAAA-sNN (por ejemplo 2026-s44)."""
    anio, semana, _ = fecha.isocalendar()
    return f"{anio}-s{semana:02d}"


def leer_cabecera(ruta: Path):
    """Devuelve (cabecera, cuerpo). La cabecera es None si el archivo no la tiene."""
    texto = ruta.read_text(encoding="utf-8")
    m = CABECERA.match(texto)
    if not m:
        return None, texto
    datos = yaml.safe_load(m.group(1))
    if datos is None:
        datos = {}
    if not isinstance(datos, dict):
        raise ValueError(f"{ruta}: la cabecera no es un diccionario YAML")
    return datos, texto[m.end():]


def escribir_con_cabecera(ruta: Path, cabecera: dict, cuerpo: str) -> None:
    texto = "---\n" + volcar_yaml(cabecera) + "---\n" + cuerpo
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


def volcar_yaml(datos) -> str:
    return yaml.safe_dump(datos, allow_unicode=True, sort_keys=False, default_flow_style=False)


def ruta_registro() -> Path:
    """`fuentes/registro.yml` en el privado, `fuentes.yml` en el público."""
    for candidata in ("fuentes/registro.yml", "fuentes.yml"):
        p = RAIZ / candidata
        if p.exists():
            return p
    return RAIZ / "fuentes" / "registro.yml"


def cargar_registro():
    """Devuelve (lista de fuentes, ruta)."""
    p = ruta_registro()
    if not p.exists():
        return [], p
    datos = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if isinstance(datos, dict):
        fuentes = datos.get("fuentes") or []
    else:
        fuentes = datos
    return list(fuentes), p


def ids_registro() -> set[str]:
    fuentes, _ = cargar_registro()
    return {str(f.get("id")) for f in fuentes if isinstance(f, dict) and f.get("id")}


def valor_claude_md(clave: str, por_defecto: str | None = None) -> str | None:
    """Lee un valor de configuración de CLAUDE.md (línea `- CLAVE: valor`)."""
    p = RAIZ / "CLAUDE.md"
    if not p.exists():
        return por_defecto
    m = re.search(rf"^-\s*{re.escape(clave)}:\s*(.+?)\s*$", p.read_text(encoding="utf-8"), re.M)
    return m.group(1).strip() if m else por_defecto


def rellenar_plantilla(nombre: str, valores: dict) -> str:
    texto = (RAIZ / "plantillas" / nombre).read_text(encoding="utf-8")
    for clave, valor in valores.items():
        texto = texto.replace("{{" + clave + "}}", str(valor))
    return texto
