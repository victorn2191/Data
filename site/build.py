"""Genera site/app/index.html (documento completo) a partir del prototipo de la app.

Uso:  python site/build.py
El prototipo (mvp/app-prototype/index.html) es un fragmento HTML; aquí se le añade el esqueleto
para poder publicarlo tal cual en GitHub Pages junto a la landing (site/index.html).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "mvp" / "app-prototype" / "index.html"
DST = ROOT / "site" / "app" / "index.html"

HEAD = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>body{margin:0}[hidden]{display:none!important}</style>
</head>
<body>
"""

DST.parent.mkdir(parents=True, exist_ok=True)
DST.write_text(HEAD + SRC.read_text(encoding="utf-8") + "\n</body>\n</html>\n", encoding="utf-8")
print(f"Generado {DST.relative_to(ROOT)}")
