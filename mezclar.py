#!/usr/bin/env python3
"""Une la lista personal con la lista publica de deportes de iptv-org.

Ejecutar: python3 mezclar.py
La lista resultante se publica como public/playlist.m3u.
"""

from __future__ import annotations

import os
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / 'canales_base.m3u'
OUTPUT = HERE / 'public' / 'playlist.m3u'
SPORTS_URL = os.environ.get(
    'SPORTS_URL', 'https://iptv-org.github.io/iptv/categories/sports.m3u'
)


def channels(data: str):
    if not data.lstrip('\ufeff').lstrip().startswith('#EXTM3U'):
        raise ValueError('La fuente no tiene encabezado #EXTM3U')
    pending = []
    for raw in data.splitlines():
        line = raw.strip()
        if line.startswith('#EXTINF:'):
            pending = [line]
        elif pending and line.startswith('#'):
            pending.append(line)
        elif pending and line.startswith(('http://', 'https://', 'rtmp://', 'rtsp://')):
            yield pending + [line]
            pending = []
        elif line and not line.startswith('#'):
            pending = []


def set_group(entry: list[str], group: str) -> list[str]:
    meta = entry[0]
    if re.search(r'group-title="[^"]*"', meta):
        meta = re.sub(r'group-title="[^"]*"', f'group-title="{group}"', meta, count=1)
    else:
        meta = meta.replace(',', f' group-title="{group}",', 1)
    return [meta] + entry[1:]


def main():
    base_data = BASE.read_text(encoding='utf-8-sig')
    base = list(channels(base_data))
    if len(base) < 40:
        raise ValueError('La lista de origen parece incompleta')

    request = urllib.request.Request(
        SPORTS_URL,
        headers={'User-Agent': 'Mozilla/5.0 (playlist-merge; GitHub Pages)'}
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        sport_data = response.read().decode('utf-8-sig')
    sports = list(channels(sport_data))
    if len(sports) < 20:
        raise ValueError('La lista de deportes parece incompleta; no se publicara')

    seen = set()
    merged = []
    counter = Counter()
    for entry, is_sport in ([(e, False) for e in base] + [(e, True) for e in sports]):
        url = entry[-1]
        if url in seen:
            continue
        seen.add(url)
        if is_sport:
            entry = set_group(entry, '05 | Deportes')
        merged.extend(entry)
        group = re.search(r'group-title="([^"]*)"', entry[0])
        counter[group.group(1) if group else '(sin categoria)'] += 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text('#EXTM3U\n' + '\n'.join(merged) + '\n', encoding='utf-8')
    print('Archivo:', OUTPUT)
    print('Canales:', len(seen))
    for group, count in counter.items():
        print(f'{group}: {count}')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
