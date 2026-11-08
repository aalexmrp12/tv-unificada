#!/usr/bin/env python3
"""Genera public/playlist.m3u para TiviMate desde listas publicas.

Sustituye mezclar.py del repositorio tv-unificada.
No necesita dependencias externas. Se ejecuta con el workflow existente.
"""
from __future__ import annotations

import re
import sys
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
BASE = ROOT / 'canales_base.m3u'
OUTPUT = ROOT / 'public' / 'playlist.m3u'

# Orden = prioridad. Cantidad por fuente limitada para mantener fluidez en Fire TV.
# Ninguna fuente garantiza que todos sus streams reproduzcan.
@dataclass(frozen=True)
class Source:
    name: str
    url: str
    group: str
    max_entries: int
    focus: str = 'all'

SOURCES = [
    Source('Mexico y Latam (comunidad)', 'https://raw.githubusercontent.com/CharlieII/IPTV_mexico/refs/heads/main/lista.m3u', '06 | Mexico y Latinoamerica', 280),
    Source('Mexico (iptv-org)', 'https://iptv-org.github.io/iptv/countries/mx.m3u', '04 | TV abierta MX', 220),
    Source('Deportes', 'https://iptv-org.github.io/iptv/categories/sports.m3u', '05 | Deportes', 300, 'prioritize_latam'),
    Source('Caricaturas', 'https://iptv-org.github.io/iptv/categories/animation.m3u', '01 | Caricaturas', 120, 'prioritize_latam'),
    Source('Infantiles', 'https://iptv-org.github.io/iptv/categories/kids.m3u', '01 | Caricaturas', 120, 'prioritize_latam'),
    Source('Peliculas', 'https://iptv-org.github.io/iptv/categories/movies.m3u', '02 | Peliculas', 150, 'prioritize_latam'),
    Source('Series', 'https://iptv-org.github.io/iptv/categories/series.m3u', '03 | Series', 150, 'prioritize_latam'),
    Source('Teleonline', 'https://teleonline.github.io/listas/tv.m3u8', '07 | TV internacional', 250, 'spanish_regions'),
    Source('Free-TV alternativas', 'https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8', '07 | TV internacional', 150, 'spanish_regions'),
]

MAX_TOTAL = 1650
ATTR_GROUP = re.compile(r'group-title="[^"]*"', re.I)
ATTR_LANG = re.compile(r'tvg-language="([^"]*)"', re.I)
COUNTRY_PRIORITY = re.compile(r'(?:\b(?:mx|es|ar|co|cl|pe|uy|ve|us)\b|mexic|espa[ñn]|latin|hispan|spanish|english)', re.I)


def download(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (TV-Unificada/2.0)'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        # Evitar bajar archivos gigantes por errores de servidor.
        data = resp.read(12_000_001)
    if len(data) > 12_000_000:
        raise ValueError('La fuente excede el limite de 12 MB')
    return data.decode('utf-8-sig', errors='replace')


def parse_m3u(data: str) -> list[list[str]]:
    if not data.lstrip('\ufeff \t\r\n').startswith('#EXTM3U'):
        raise ValueError('No comienza con #EXTM3U')
    result, pending = [], []
    for raw in data.splitlines():
        line = raw.strip()
        if line.startswith('#EXTINF:'):
            pending = [line]
        elif pending and line.startswith('#'):
            pending.append(line)
        elif pending and line.startswith(('https://', 'http://', 'rtsp://', 'rtmp://')):
            result.append(pending + [line])
            pending = []
        elif line and not line.startswith('#'):
            pending = []
    return result


def set_group(entry: list[str], group: str) -> list[str]:
    first = entry[0]
    if ATTR_GROUP.search(first):
        first = ATTR_GROUP.sub(lambda _: f'group-title="{group}"', first, count=1)
    elif ',' in first:
        first = first.replace(',', f' group-title="{group}",', 1)
    return [first, *entry[1:]]


def is_pluto(entry: list[str]) -> bool:
    # Quita nuevos canales de Pluto, incluidos redirects jmp2.uk/plu-*.
    meta = entry[0].lower()
    url = entry[-1].lower()
    host = urlsplit(url).netloc
    return any((
        'pluto.tv' in host,
        'plutotv' in host,
        'jmp2.uk/plu-' in url,
        'plutotv' in url,
        'pluto' in meta.split(',', 1)[0],
    ))


def priority(entry: list[str]) -> int:
    meta = entry[0]
    score = 0
    if COUNTRY_PRIORITY.search(meta):
        score += 5
    lang = ATTR_LANG.search(meta)
    if lang and re.search(r'spanish|english|es|en', lang.group(1), re.I):
        score += 3
    if re.search(r'mexic|latam|latin', meta, re.I):
        score += 5
    return score


def relevant_spanish(entry: list[str]) -> bool:
    meta = entry[0]
    return bool(re.search(r'mexic|espa[ñn]|latin|spanish|argentin|colombi|chile|per[uú]|uruguay|venezuel|hispan|deportes|infantil|cine|serie|cartoon', meta, re.I))


def choose(entries: list[list[str]], source: Source) -> list[list[str]]:
    entries = [e for e in entries if not is_pluto(e)]
    if source.focus == 'spanish_regions':
        entries = [e for e in entries if relevant_spanish(e)]
    if source.focus == 'prioritize_latam':
        # Estabilidad del orden original dentro del nivel de preferencia.
        entries = sorted(entries, key=priority, reverse=True)
    return entries[:source.max_entries]


def main() -> None:
    base = parse_m3u(BASE.read_text(encoding='utf-8-sig'))
    if len(base) < 40:
        raise ValueError('La lista personal tiene menos de 40 canales')

    seen_urls: set[str] = set()
    merged: list[str] = []
    categories = Counter()
    sources_ok = 0
    per_source = Counter()

    def add(entry: list[str], source: str) -> bool:
        url = entry[-1].strip()
        if url in seen_urls or len(seen_urls) >= MAX_TOTAL:
            return False
        seen_urls.add(url)
        merged.extend(entry)
        group = ATTR_GROUP.search(entry[0])
        categories[group.group(0) if group else 'Sin categoria'] += 1
        per_source[source] += 1
        return True

    for entry in base:
        add(entry, 'Lista original')  # Mantener incluso los Pluto originales.

    for src in SOURCES:
        if len(seen_urls) >= MAX_TOTAL:
            break
        try:
            original = parse_m3u(download(src.url))
            if not original:
                raise ValueError('Lista vacia')
            for entry in choose(original, src):
                add(set_group(entry, src.group), src.name)
            sources_ok += 1
            print(f'{src.name}: {len(original)} entradas leidas, {per_source[src.name]} canales nuevos')
        except Exception as exc:
            print(f'AVISO: {src.name} no disponible: {exc}', file=sys.stderr)

    if sources_ok < 2 or len(seen_urls) < 80:
        raise ValueError('No hubo suficientes fuentes disponibles: se conserva la publicacion anterior')

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text('#EXTM3U\n' + '\n'.join(merged) + '\n', encoding='utf-8', newline='\n')
    print(f'TOTAL: {len(seen_urls)} canales (limite {MAX_TOTAL})')
    print(f'Salida: {OUTPUT}')
    for name, count in per_source.items():
        print(f'  {name}: {count}')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
