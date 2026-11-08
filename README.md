# TV Unificada — para TiviMate gratuito

Incluye 52 canales de la lista personal: 12 caricaturas, 14 películas, 14 series y 12 TV abierta México; además, **descarga y añade todos los canales de la lista deportiva pública de IPTV-org**.

Fuente deportiva: `https://iptv-org.github.io/iptv/categories/sports.m3u`.

## Obtener una sola URL permanente

1. Entra a https://github.com/new y crea un repositorio **público** llamado exactamente **tv-unificada** (rama principal `main`).
2. Sube **todo el contenido extraído de este ZIP** al repositorio, conservando las rutas. Importante: incluye también `.github/workflows/publicar.yml` (el directorio comienza con un punto).
3. En GitHub abre **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. Abre **Actions → Actualizar playlist M3U y publicar → Run workflow**. Debe concluir correctamente.
5. Tu URL para TiviMate será:

   `https://TU_USUARIO.github.io/tv-unificada/playlist.m3u`

   Sustituye `TU_USUARIO` por el usuario real de tu cuenta GitHub.

El workflow combina las listas y vuelve a publicarlas diariamente. Las actualizaciones de deportes no requieren cambiar la URL en TiviMate; activa la actualización automática de listas dentro de TiviMate si lo permite tu versión.

## Qué contiene

- `canales_base.m3u`: 52 canales aportados por el usuario.
- `mezclar.py`: fusiona las listas; conserva metadatos y evita URLs duplicadas.
- `.github/workflows/publicar.yml`: descarga deportes, crea `playlist.m3u` y publica en GitHub Pages.
- `public/index.html`: página sencilla con el archivo M3U.

## Probarlo en Windows antes de subirlo

Abre PowerShell dentro de la carpeta extraída:

```powershell
py -3 .\mezclar.py
```

Se creará `public\playlist.m3u` si la lista de deportes está disponible.

## Notas

- No contiene streams de pago privados ni credenciales. Los proveedores pueden retirar canales, exigir restricciones geográficas o cambiar sus URLs.
- La lista final será pública en GitHub Pages, no coloques listas IPTV privadas con usuario o token.
- GitHub Pages requiere una cuenta GitHub y la publicación manual inicial; el ZIP por sí solo no es una URL pública.
- Si falla la descarga de deportes, el flujo se detiene sin publicar una lista incompleta.
