# base-de-conocimiento

Repositorio público del libro vivo y la base de conocimiento sobre inteligencia artificial y agentes en Business Central. Es un sitio Quarto publicado en GitHub Pages. Este repositorio recibe contenido; no se escribe contenido en él.

## Reglas

1. El contenido (capítulos, fichas, conceptos, laboratorios, ejercicios, resúmenes) se redacta en el repositorio privado `estudio-privado` y llega aquí con el skill `/publicar`, siempre por pull request. Aquí solo se tocan la estructura del sitio, `_quarto.yml`, los scripts y las plantillas.
2. Nada se fusiona en la rama principal sin que Javi apruebe el pull request. La web se publica sola al fusionar.
3. `python scripts/comprobar_fuentes.py` tiene que pasar: cada id de `fuentes:` existe en `fuentes.yml` y ningún archivo aprobado contiene `[no verificado]`.
4. Ni en el contenido ni en los mensajes de commit o pull request se nombran herramientas de IA como autoras o ayuda del texto, ni se añaden líneas `Co-Authored-By`.
5. Solo datos de demostración (CRONUS). Nunca datos de clientes ni capturas de libros ajenos.
6. `fuentes.yml` se genera desde el registro del repositorio privado; no se edita aquí.

## Estructura

- `index.qmd`, `suscripcion.qmd`, `sobre.qmd`, `novedades.qmd`: páginas fijas.
- `libro/NN-slug.qmd`: capítulos. El orden está en `_quarto.yml` (sidebar «Libro»).
- `conocimiento/fichas/`, `conocimiento/conceptos/`, `conocimiento/laboratorios/`: base de conocimiento con listados automáticos.
- `ejercicios/`: enunciados públicos (y el ejercicio 0 completo).
- `escaparate/`: proyectos. `diario/`: resúmenes semanales.
- `scripts/comprobar_fuentes.py`: comprobador. `scripts/exportar_libro.py`: monta el proyecto de libro para PDF y EPUB (`--perfil gratis` o `--perfil completo`).
- `.github/workflows/publicar.yml`: renderiza y publica en GitHub Pages al fusionar en `main`.

## Comandos

- Vista previa local: `quarto preview`.
- Comprobación: `python scripts/comprobar_fuentes.py`.
- Libro gratuito: `python scripts/exportar_libro.py --perfil gratis && quarto render _libro --to epub`.
