# Reshare Stories

Vibecoded with Codex.

Desktop tool for reposting Instagram stories where you were mentioned, without needing to use the mobile app every time.

Herramienta de escritorio para republicar historias de Instagram en las que fuiste mencionado, sin tener que usar la app del teléfono cada vez.

## What It Does

This project helps you:

- inspect an Instagram story from a URL or story PK
- authenticate with Instagram using a saved session or `sessionid`
- download the original story media
- rebuild the image into a repost-style layout
- repost it from your PC
- make the repost tappable to the original author's profile

This is built around Instagram's private mobile API behavior as exposed by open-source tooling such as `instagrapi`.

## Qué Hace

Este proyecto te permite:

- inspeccionar una historia de Instagram usando una URL o `story PK`
- autenticarte con Instagram usando una sesión guardada o `sessionid`
- descargar el contenido original de la historia
- reconstruir la imagen con un layout tipo repost
- republicarla desde la PC
- hacer que el repost sea tocable para ir al perfil del autor original

Está construido sobre el comportamiento de la API privada móvil de Instagram, apoyándose en tooling open source como `instagrapi`.

## Current Behavior

The app currently supports multiple repost modes:

- `Repost al perfil (Recomendado)`: prioritizes tappable profile access to the original story author
- `Repost con contenido enlazado`: also adds an extra attached media link
- `Reupload simple (Fallback)`: simple reupload without the extra attachment logic

For image stories, the tool generates a new JPEG before upload:

- blurred, desaturated Instagram-like background
- resized central story card
- original author's avatar and username blended into the image
- large mention hotspot over the reposted image so taps go to the original author's profile

## Estado Actual

La app actualmente soporta varios modos de repost:

- `Repost al perfil (Recomendado)`: prioriza el acceso tocable al perfil del autor original
- `Repost con contenido enlazado`: agrega además un link de media adjunta
- `Reupload simple (Fallback)`: reupload simple sin la lógica extra

Para historias de imagen, la herramienta genera un JPEG nuevo antes del upload:

- fondo blurreado y desaturado tipo Instagram
- tarjeta central con la historia redimensionada
- avatar y username del autor original integrados en la imagen
- hotspot grande de mention sobre la imagen para que el toque vaya al perfil del autor original

## Requirements

- Windows
- Python 3.9+
- an Instagram account session
- internet access

Optional:

- GitHub CLI if you want to publish or manage the repo from terminal

## Requisitos

- Windows
- Python 3.9+
- una sesión válida de Instagram
- acceso a internet

Opcional:

- GitHub CLI si querés publicar o administrar el repo desde terminal

## Setup

1. Clone or download the repository.
2. Open a terminal inside the project folder.
3. Create and prepare the virtual environment:

```powershell
.\setup_story_reshare_env.bat
```

Or manually:

```powershell
py -3.9 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Instalación

1. Cloná o descargá el repositorio.
2. Abrí una terminal dentro de la carpeta del proyecto.
3. Prepará el entorno virtual:

```powershell
.\setup_story_reshare_env.bat
```

O manualmente:

```powershell
py -3.9 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Running the App

Run the UI directly from source:

```powershell
.\.venv\Scripts\python.exe run_story_reshare_ui.py
```

You can also build a Windows executable:

```powershell
.\build_story_reshare_exe.bat
```

The executable will be generated under `dist/`.

## Ejecutar la App

Corré la UI directamente desde el código fuente:

```powershell
.\.venv\Scripts\python.exe run_story_reshare_ui.py
```

También podés generar un ejecutable para Windows:

```powershell
.\build_story_reshare_exe.bat
```

El ejecutable queda en `dist/`.

## How to Use It

1. Launch the app.
2. Keep the default session file path, or choose your own.
3. Authenticate using one of these options:
   - `sessionid` cookie
   - saved session file
   - username and password if still accepted by Instagram
4. Paste the original story URL into `Story URL o PK`.
5. Choose the repost mode.
6. Keep `Mencionar al autor original en la nueva story` enabled if you want the profile tap behavior.
7. Click:
   - `Info de sesión` to verify auth
   - `Inspeccionar story` to fetch metadata
   - `Compartir story` to repost
   - `Ejecutar todo` to run the full flow

## Cómo Usarlo

1. Abrí la app.
2. Dejá la ruta por defecto del archivo de sesión o elegí otra.
3. Autenticate con una de estas opciones:
   - cookie `sessionid`
   - archivo de sesión guardado
   - usuario y contraseña si Instagram todavía lo permite
4. Pegá la URL de la historia original en `Story URL o PK`.
5. Elegí el modo de repost.
6. Dejá activado `Mencionar al autor original en la nueva story` si querés el comportamiento de tap al perfil.
7. Usá:
   - `Info de sesión` para verificar la autenticación
   - `Inspeccionar story` para obtener metadata
   - `Compartir story` para republicar
   - `Ejecutar todo` para correr el flujo completo

## Where to Get `sessionid`

The easiest path is usually:

1. Log into Instagram on the web browser.
2. Open browser developer tools.
3. Go to site cookies for `https://www.instagram.com`.
4. Copy the value of the `sessionid` cookie only.
5. Paste that value into the app.

Important: `sessionid` is sensitive. Treat it like a login token.

## Cómo Obtener `sessionid`

La forma más simple suele ser:

1. Iniciá sesión en Instagram desde el navegador.
2. Abrí las herramientas de desarrollador.
3. Andá a las cookies del sitio `https://www.instagram.com`.
4. Copiá solo el valor de la cookie `sessionid`.
5. Pegá ese valor en la app.

Importante: `sessionid` es sensible. Tratala como un token de login.

## Notes and Limitations

- This project relies on unofficial/private Instagram behavior.
- Instagram may rate-limit, challenge, warn, or block automation attempts.
- Login by username/password may fail even when credentials are correct.
- Session reuse can expire and may require a fresh `sessionid`.
- The exact native `Add this to your story` flow is not fully replicated 1:1.
- Behavior may change as Instagram changes internal APIs.

## Notas y Limitaciones

- Este proyecto depende de comportamiento privado/no oficial de Instagram.
- Instagram puede limitar, desafiar, advertir o bloquear intentos de automatización.
- El login con usuario/contraseña puede fallar aunque las credenciales sean correctas.
- La reutilización de sesión puede expirar y requerir un `sessionid` nuevo.
- El flujo nativo exacto de `Add this to your story` no está replicado 1:1 en todos los detalles.
- El comportamiento puede cambiar si Instagram modifica sus APIs internas.

## Project Structure

- `instagram_story_reshare/client.py`: Instagram logic, login, inspection, media processing, repost flow
- `instagram_story_reshare/ui.py`: Tkinter desktop UI
- `instagram_story_reshare/cli.py`: CLI entrypoint
- `run_story_reshare_ui.py`: local launcher
- `build_story_reshare_exe.bat`: Windows executable build helper
- `docs/instagram-story-reshare.md`: research notes and endpoint documentation

## Estructura del Proyecto

- `instagram_story_reshare/client.py`: lógica de Instagram, login, inspección, procesamiento de media y repost
- `instagram_story_reshare/ui.py`: UI de escritorio en Tkinter
- `instagram_story_reshare/cli.py`: entrypoint de CLI
- `run_story_reshare_ui.py`: lanzador local
- `build_story_reshare_exe.bat`: helper para generar ejecutable Windows
- `docs/instagram-story-reshare.md`: notas de investigación y documentación técnica
