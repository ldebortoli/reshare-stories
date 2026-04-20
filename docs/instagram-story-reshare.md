# Instagram story mention resharing desde PC

Fecha de esta investigación: 19 de abril de 2026.

## Resumen ejecutivo

- No encontré documentación oficial de Meta que permita, para cuentas personales normales, disparar de forma oficial el flujo equivalente a `Add this to your story` cuando otra cuenta te menciona en una story.
- Sí existe documentación oficial alrededor de otras piezas del ecosistema:
  - el Graph API permite leer `stories` de cuentas profesionales/negocio propias;
  - el sistema de webhooks/mensajería de Instagram para cuentas profesionales expone story mentions en algunos escenarios;
  - históricamente Meta documentó que `Mentions on Stories are not supported` dentro de la guía de mentions del Instagram API, según una respuesta en Stack Overflow que enlaza esa documentación oficial.
- La implementación práctica para una cuenta personal hoy pasa por la API privada usada por las apps móviles, no por la API pública.
- El flujo privado observable en librerías abiertas modernas converge en:
  1. subir el asset con `rupload_igphoto` o `rupload_igvideo`
  2. configurar/publicar con `POST https://i.instagram.com/api/v1/media/configure_to_story/`
- Lo que no quedó confirmado públicamente es el payload exacto del caso nativo donde la story ya existente se comparte como sticker porque te mencionaron. Para replicarlo 1:1 conviene capturar tráfico desde el teléfono.

## Fuentes consultadas

- Stack Overflow: respuesta que cita la doc oficial de Meta indicando que las mentions en stories no estaban soportadas por el Instagram API: [Receive Instagram stories that mentioned/tagged my business account](https://stackoverflow.com/questions/67241319/receive-instagram-stories-that-mentioned-tagged-my-business-account)
- Stack Overflow: referencias al endpoint oficial `/{ig-user-id}/stories` de Graph API para cuentas profesionales: [Instagram Stories API](https://stackoverflow.com/questions/53371614/instagram-stories-api)
- Stack Overflow: referencia al feature oficial de story mentions vía Messenger Platform / Instagram para cuentas profesionales: [Receive Instagram stories that mentioned/tagged my business account](https://stackoverflow.com/questions/67241319/receive-instagram-stories-that-mentioned-tagged-my-business-account)
- Biblioteca abierta `instagrapi`, que implementa login, descarga de stories y publicación de stories sobre la API privada móvil: [subzeroid/instagrapi](https://github.com/subzeroid/instagrapi)
- Artículo que resume el comportamiento oficial de la app: solo public accounts y mediante la mención: [9to5Mac - Instantly reshare Instagram Stories that you’ve been mentioned in to your Story](https://9to5mac.com/2018/06/07/instagram-reshare-mentioned-stories/)

## Endpoint privado más relevante

Base host móvil privada:

```text
https://i.instagram.com/api/v1/
```

Endpoints observados para publicar una story:

```text
POST /rupload_igphoto/<upload_name>
POST /rupload_igvideo/<upload_name>
POST /media/configure_to_story/
```

La hipótesis razonable para el caso “me mencionaron y toco Add this to your story” es que el endpoint final sigue siendo `POST /media/configure_to_story/`, pero con campos extra que referencian la story original y/o un sticker interno de reshare/mention.

## Headers, cookies y atributos de request

Implementaciones abiertas de la API privada agregan, entre otros, headers de esta familia:

```text
User-Agent: Instagram <app-version> Android (...)
X-IG-App-ID: <app_id>
X-IG-Device-ID: <uuid>
X-IG-Family-Device-ID: <phone_id>
X-IG-Android-ID: <android_device_id>
X-IG-Timezone-Offset: <offset>
X-IG-Connection-Type: WIFI
X-IG-Capabilities: 3brTv10=
X-Bloks-Version-Id: <bloks_version>
X-MID: <mid>
Accept-Language: <locale>
```

Cookies/tokens típicos:

```text
sessionid
csrftoken
mid
ds_user_id
ig_did
rur
shbid
shbts
```

Body típico de `media/configure_to_story/`:

```json
{
  "supported_capabilities_new": "[...]",
  "has_original_sound": "1",
  "camera_session_id": "<client_session_id>",
  "timezone_offset": "<offset>",
  "client_shared_at": "<unix_ts>",
  "story_sticker_ids": "",
  "media_folder": "Camera",
  "configure_mode": "1",
  "source_type": "4",
  "creation_surface": "camera",
  "capture_type": "normal",
  "upload_id": "<upload_id>",
  "client_timestamp": "<unix_ts>",
  "device": { "...": "..." },
  "_uid": "<user_id>",
  "_uuid": "<uuid>",
  "device_id": "<android_device_id>",
  "composition_id": "<uuid>",
  "media_transformation_info": "{...}",
  "original_media_type": "photo"
}
```

## Restricciones y riesgos

- El resharing nativo de una story donde te mencionaron existe desde 2018, pero la app solo lo ofrece cuando realmente hubo una mención clickeable.
- En la comunicación pública citada por 9to5Mac se menciona que solo las cuentas públicas pueden tener sus stories compartidas de esa manera.
- La API privada no está autorizada para uso externo. El riesgo real incluye challenge, bloqueo temporal, invalidación de sesión, checkpoints o deshabilitación de funciones.
- Bibliotecas abiertas y proyectos de automatización mencionan medidas anti-detección como rotación de User-Agent, delays y proxies, lo que sugiere controles activos por parte de Instagram.

## Qué hace la implementación incluida en este repo

La implementación dejada en este proyecto hace un workflow utilizable hoy:

1. inicia sesión con `instagrapi`
2. resuelve la story origen por URL o `story_pk`
3. descarga el asset original
4. publica una nueva story desde tu cuenta
5. opcionalmente menciona al autor original
6. permite inyectar JSON adicional al payload `configure_to_story` para experimentar con parámetros capturados del teléfono

## Resultado confirmado en pruebas

En pruebas reales de este proyecto, el comportamiento quedó separado en dos modos útiles:

1. `Repost al perfil (Recomendado)`:
   - reupload de la media de la story original
   - composición visual tipo repost
   - `StoryMention` del autor original para priorizar el tap al perfil
2. `Repost con contenido enlazado`:
   - lo anterior
   - más un attachment tipo `StoryMedia` usando el `story_pk` original

El segundo modo produjo un repost con tap-through a una entidad de contenido interna, pero no necesariamente a la story original exacta. Por eso la UI deja como recomendado el modo orientado al perfil y conserva el enlazado como alternativa.

## Archivos entregados

- `instagram_story_reshare/client.py`: lógica de login, inspección y repost
- `instagram_story_reshare/cli.py`: CLI
- `instagram_story_reshare/ui.py`: UI en Tkinter
- `run_story_reshare_ui.py`: entrypoint de escritorio
- `build_story_reshare_exe.bat`: script para generar `.exe` con PyInstaller

## Uso rápido

Instalar dependencias:

```powershell
python -m pip install -r requirements.txt
```

Inspeccionar una story:

```powershell
python -m instagram_story_reshare.cli --username TU_USUARIO --prompt-password inspect-story "https://www.instagram.com/stories/usuario/1234567890123456789/"
```

Repostearla como nueva story:

```powershell
python -m instagram_story_reshare.cli --username TU_USUARIO --prompt-password share-story "https://www.instagram.com/stories/usuario/1234567890123456789/" --mention-original-author
```

Abrir la UI:

```powershell
python run_story_reshare_ui.py
```

En la UI:

- `Repost al perfil (Recomendado)`: prioriza el tap al perfil del autor original
- `Repost con contenido enlazado`: agrega la story original como attachment adicional
- `Reupload simple (Fallback)`: sube solo la media descargada, sin ese attachment adicional

Generar ejecutable Windows:

```powershell
build_story_reshare_exe.bat
```

## Cómo detectar el payload exacto desde tu celular

Proxy HTTPS con certificado instalado:

1. Instalar en el teléfono un proxy como Proxyman, Charles, mitmproxy o HTTP Toolkit.
2. Configurar el Wi-Fi del teléfono para usar el proxy de tu PC.
3. Abrir Instagram, pedir una mención real y tocar `Add this to your story`.
4. Filtrar requests a `i.instagram.com`, `media/configure_to_story`, `rupload_igphoto` y `rupload_igvideo`.
5. Guardar headers completos, cookies, body exacto y response.

Compará dos acciones:

1. publicar una story normal desde la app
2. compartir una story en la que te mencionaron

Si ambos terminan en `media/configure_to_story/`, el diff del body normalmente deja expuesto el campo faltante.
