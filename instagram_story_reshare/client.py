from __future__ import annotations

import json
import sys
import tempfile
import urllib.request
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, TwoFactorRequired
from instagrapi.types import StoryMedia, StoryMention, UserShort
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

PromptHandler = Callable[[str], str]


@dataclass
class StoryReshareResult:
    source_story_pk: str
    source_story_id: str
    source_owner_pk: str
    source_owner_username: str
    source_media_type: int
    source_media_url: str
    downloaded_to: str
    posted_story_pk: str
    posted_story_id: str
    mode: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class InstagramStoryReshareClient:
    """
    Practical wrapper around instagrapi for desktop story repost workflows.

    This posts a new story from downloaded source media. It does not guarantee a
    byte-for-byte reproduction of Instagram's native mention-reshare flow.
    """

    def __init__(
        self,
        session_path: str | Path = "sessions/instagram_session.json",
        logger: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.session_path = self._resolve_session_path(session_path)
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logger or (lambda message: None)
        self.client = Client()
        self.client.delay_range = [1, 2]

    def _log(self, message: str) -> None:
        self.logger(message)

    def _prompt_code(self, label: str) -> str:
        raise RuntimeError(f"Interactive prompt required for: {label}")

    def login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        sessionid: Optional[str] = None,
        verification_code_handler: Optional[PromptHandler] = None,
    ) -> None:
        verification_code_handler = verification_code_handler or self._prompt_code

        if sessionid:
            self._log("Importing sessionid into the mobile client session.")
            self.client.login_by_sessionid(sessionid)
            self._persist_saved_sessionid(sessionid)
            self._dump_settings()
            return

        if self.session_path.exists():
            self._log(f"Loading saved session from {self.session_path}.")
            self.client.load_settings(self.session_path)
            try:
                if username and password:
                    self.client.login(username, password)
                else:
                    self.client.get_timeline_feed()
                self._dump_settings()
                return
            except Exception as exc:
                self._log(f"Saved session could not be reused: {exc}")
                saved_sessionid = self._read_saved_sessionid()
                if saved_sessionid:
                    self._log("Retrying with saved sessionid from the session file.")
                    try:
                        self.client = Client()
                        self.client.delay_range = [1, 2]
                        self.client.login_by_sessionid(saved_sessionid)
                        self._dump_settings()
                        return
                    except Exception as session_exc:
                        self._log(f"Saved sessionid failed and will be removed: {session_exc}")
                        self._clear_saved_sessionid()

        if not username or not password:
            raise ValueError("username and password are required when no valid saved session exists")

        self.client.challenge_code_handler = lambda _username, _choice: verification_code_handler(
            f"challenge_code:{_username}"
        )

        try:
            self._log("Performing password login.")
            self.client.login(username, password)
        except TwoFactorRequired:
            code = verification_code_handler(f"two_factor_code:{username}")
            self._log("Submitting 2FA verification code.")
            self.client.login(username, password, verification_code=code)
        except ChallengeRequired:
            code = verification_code_handler(f"challenge_code:{username}")
            self._log("Retrying login after challenge code prompt.")
            self.client.login(username, password, verification_code=code)

        self._dump_settings()

    def _dump_settings(self) -> None:
        self.client.dump_settings(self.session_path)
        sessionid = self._extract_sessionid()
        if sessionid:
            self._persist_saved_sessionid(sessionid)
        self._log(f"Session saved to {self.session_path}.")

    def _extract_sessionid(self) -> Optional[str]:
        private = getattr(self.client, "private", None)
        cookie_jar = getattr(private, "cookies", None)
        if not cookie_jar:
            return None
        cookies = cookie_jar.get_dict()
        return cookies.get("sessionid")

    def _persist_saved_sessionid(self, sessionid: str) -> None:
        data: Dict[str, Any] = {}
        if self.session_path.exists():
            try:
                data = json.loads(self.session_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}

        data["_codex_saved_sessionid"] = sessionid
        self.session_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _read_saved_sessionid(self) -> Optional[str]:
        if not self.session_path.exists():
            return None

        try:
            data = json.loads(self.session_path.read_text(encoding="utf-8"))
        except Exception:
            return None

        value = data.get("_codex_saved_sessionid")
        return value.strip() if isinstance(value, str) and value.strip() else None

    def _clear_saved_sessionid(self) -> None:
        if not self.session_path.exists():
            return

        try:
            data = json.loads(self.session_path.read_text(encoding="utf-8"))
        except Exception:
            return

        if "_codex_saved_sessionid" not in data:
            return

        del data["_codex_saved_sessionid"]
        self.session_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _app_base_dir() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent.parent

    @classmethod
    def _resolve_session_path(cls, session_path: str | Path) -> Path:
        path = Path(session_path)
        if path.is_absolute():
            return path
        return cls._app_base_dir() / path

    def export_runtime_metadata(self) -> Dict[str, Any]:
        private = getattr(self.client, "private", None)
        cookie_jar = getattr(private, "cookies", None)
        cookies = cookie_jar.get_dict() if cookie_jar else {}
        return {
            "base_url": "https://i.instagram.com/api/v1/",
            "session_path": str(self.session_path.resolve()),
            "user_id": str(self.client.user_id or ""),
            "username": getattr(self.client, "username", None),
            "uuid": getattr(self.client, "uuid", None),
            "phone_id": getattr(self.client, "phone_id", None),
            "android_device_id": getattr(self.client, "android_device_id", None),
            "app_id": getattr(self.client, "app_id", None),
            "user_agent": getattr(self.client, "user_agent", None),
            "cookies": cookies,
        }

    def inspect_story(self, story_identifier: str) -> Dict[str, Any]:
        story_pk = self._story_pk_from_identifier(story_identifier)
        story = self.client.story_info(story_pk)
        owner = story.user
        media_url = str(story.thumbnail_url if story.media_type == 1 else story.video_url)
        return {
            "story_pk": str(story.pk),
            "story_id": str(story.id),
            "code": getattr(story, "code", None),
            "taken_at": story.taken_at.isoformat() if getattr(story, "taken_at", None) else None,
            "expiring_at": story.expiring_at.isoformat() if getattr(story, "expiring_at", None) else None,
            "media_type": story.media_type,
            "media_url": media_url,
            "thumbnail_url": str(getattr(story, "thumbnail_url", "") or ""),
            "video_url": str(getattr(story, "video_url", "") or ""),
            "owner_pk": str(owner.pk),
            "owner_username": owner.username,
            "mention_count": len(getattr(story, "mentions", []) or []),
            "raw_story_link": f"https://www.instagram.com/stories/{owner.username}/{story.pk}/",
        }

    def repost_story(
        self,
        story_identifier: str,
        mention_original_author: bool = False,
        extra_story_config: Optional[Dict[str, Any]] = None,
        publish_mode: str = "reupload",
    ) -> StoryReshareResult:
        story_pk = self._story_pk_from_identifier(story_identifier)
        story = self.client.story_info(story_pk)
        owner = self.client.user_info_v1(story.user.pk)
        media_url = str(story.thumbnail_url if story.media_type == 1 else story.video_url)
        download_dir = Path(tempfile.mkdtemp(prefix="ig-story-reshare-"))
        downloaded_path = self.client.story_download(story.pk, folder=download_dir)
        upload_path = self._normalize_story_media_for_upload(downloaded_path, story.media_type)
        if story.media_type == 1:
            upload_path = self._build_repost_story_image(Path(upload_path), owner.username, str(owner.profile_pic_url or ""))
        mentions = []
        medias = []

        if mention_original_author:
            # Stretch the tappable mention across the visible reposted media area.
            # If Instagram honors the mention hotspot, tapping most of the image
            # should route to the original author's profile.
            mentions.append(
                StoryMention(
                    user=UserShort(pk=owner.pk, username=owner.username, profile_pic_url=owner.profile_pic_url),
                    x=0.5,
                    y=0.56,
                    width=0.76,
                    height=0.67,
                )
            )
            self._log(f"Adding large tappable mention overlay for @{owner.username}.")

        if publish_mode == "reupload_with_story_media_attachment":
            self._log(f"Using experimental story attachment with media_pk={story.pk}.")
            medias.append(
                StoryMedia(
                    media_pk=int(story.pk),
                    x=0.5,
                    y=0.56,
                    width=0.78,
                    height=0.78,
                )
            )

        extra_story_config = extra_story_config or {}
        self._log(f"Uploading story derived from source story {story.pk} with mode={publish_mode}.")
        if story.media_type == 1:
            published = self.client.photo_upload_to_story(
                upload_path,
                mentions=mentions,
                medias=medias,
                extra_data=extra_story_config,
            )
        else:
            published = self.client.video_upload_to_story(
                upload_path,
                mentions=mentions,
                medias=medias,
                extra_data=extra_story_config,
            )

        return StoryReshareResult(
            source_story_pk=str(story.pk),
            source_story_id=str(story.id),
            source_owner_pk=str(owner.pk),
            source_owner_username=owner.username,
            source_media_type=story.media_type,
            source_media_url=media_url,
            downloaded_to=str(upload_path),
            posted_story_pk=str(published.pk),
            posted_story_id=str(published.id),
            mode=publish_mode,
        )

    def _normalize_story_media_for_upload(self, downloaded_path: Path | str, media_type: int) -> str:
        path = Path(downloaded_path)
        if media_type != 1:
            return str(path)

        allowed_suffixes = {".jpg", ".jpeg", ".png", ".webp"}
        if path.suffix.lower() in allowed_suffixes:
            return str(path)

        normalized_path = path.with_suffix(".jpg")
        self._log(f"Converting image to JPEG for upload: {path.name} -> {normalized_path.name}")

        with Image.open(path) as image:
            converted = image.convert("RGB")
            converted.save(normalized_path, format="JPEG", quality=95)

        return str(normalized_path)

    def _build_repost_story_image(self, image_path: Path, owner_username: str, profile_pic_url: str) -> str:
        canvas_size = (1080, 1920)
        card_width = 820
        card_height = 1280
        card_top = 250
        card_left = (canvas_size[0] - card_width) // 2
        card_bounds = (card_left, card_top, card_left + card_width, card_top + card_height)
        card_radius = 34

        with Image.open(image_path) as original:
            base = original.convert("RGB")
            background = self._build_background(base, canvas_size)
            card = self._build_story_card(base, owner_username, profile_pic_url, (card_width, card_height), card_radius)
            background.alpha_composite(card, (card_left, card_top))

        output_path = image_path.with_name(f"{image_path.stem}_repost.jpg")
        background.convert("RGB").save(output_path, format="JPEG", quality=95)
        self._log(f"Built repost story image with author header: {output_path.name}")
        return str(output_path)

    def _build_background(self, image: Image.Image, canvas_size: tuple[int, int]) -> Image.Image:
        background = ImageOps.fit(image, canvas_size, Image.Resampling.LANCZOS).convert("RGBA")
        background = background.filter(ImageFilter.GaussianBlur(radius=34))
        background = ImageEnhance.Brightness(background).enhance(0.72)
        background = ImageEnhance.Color(background).enhance(0.22)

        # Instagram's repost background reads mostly like a soft, uniform gray
        # derived from the image rather than a decorative pattern.
        gray_overlay = Image.new("RGBA", canvas_size, (158, 160, 162, 150))
        composed = Image.alpha_composite(background, gray_overlay)

        top_glow = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(top_glow)
        draw.rectangle((0, 0, canvas_size[0], canvas_size[1]), fill=(118, 120, 122, 16))
        draw.ellipse((-60, -120, canvas_size[0] + 60, 540), fill=(255, 255, 255, 16))
        draw.ellipse((-120, 1320, canvas_size[0] + 120, 2080), fill=(0, 0, 0, 20))
        composed = Image.alpha_composite(composed, top_glow)

        vignette = Image.new("L", canvas_size, 0)
        vignette_draw = ImageDraw.Draw(vignette)
        vignette_draw.ellipse((-160, -40, canvas_size[0] + 160, canvas_size[1] + 280), fill=205)
        vignette = vignette.filter(ImageFilter.GaussianBlur(radius=140))
        edge_shadow = Image.new("RGBA", canvas_size, (0, 0, 0, 36))
        return Image.composite(edge_shadow, composed, ImageOps.invert(vignette))

    def _build_story_card(
        self,
        image: Image.Image,
        owner_username: str,
        profile_pic_url: str,
        card_size: tuple[int, int],
        card_radius: int,
    ) -> Image.Image:
        width, height = card_size
        card = Image.new("RGBA", card_size, (0, 0, 0, 0))
        header_height = 0
        avatar_size = 58
        avatar_left = 26
        avatar_top = 24
        text_left = avatar_left + avatar_size + 18
        text_top = 28

        media_area = (0, header_height, width, height)
        fitted_media = self._fit_image_to_box(image, width, height - header_height)

        media_mask = Image.new("L", (width, height - header_height), 0)
        media_mask_draw = ImageDraw.Draw(media_mask)
        media_mask_draw.rounded_rectangle(
            (0, 0, width, height - header_height),
            radius=card_radius,
            fill=255,
        )
        media_layer = Image.new("RGBA", (width, height - header_height), (0, 0, 0, 0))
        media_layer.alpha_composite(fitted_media, (0, 0))
        card.paste(media_layer, (media_area[0], media_area[1]), media_mask)

        header_shadow = Image.new("RGBA", card_size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(header_shadow)
        shadow_draw.rounded_rectangle((0, 0, width, 146), radius=card_radius, fill=(0, 0, 0, 52))
        header_shadow = header_shadow.filter(ImageFilter.GaussianBlur(radius=12))
        card.alpha_composite(header_shadow, (0, 0))

        profile_image = self._load_profile_image(profile_pic_url, avatar_size)
        card.alpha_composite(profile_image, (avatar_left, avatar_top))

        username_font = self._load_font(36, bold=True)
        draw = ImageDraw.Draw(card)
        draw.text(
            (text_left, text_top),
            owner_username,
            fill=(255, 255, 255, 238),
            font=username_font,
            stroke_width=1,
            stroke_fill=(0, 0, 0, 36),
        )
        return card

    def _load_profile_image(self, profile_pic_url: str, avatar_size: int) -> Image.Image:
        avatar = Image.new("RGBA", (avatar_size, avatar_size), (90, 90, 90, 255))
        try:
            with urllib.request.urlopen(profile_pic_url, timeout=10) as response:
                profile_bytes = response.read()
            with Image.open(BytesIO(profile_bytes)) as profile_image:
                fitted = ImageOps.fit(profile_image.convert("RGB"), (avatar_size, avatar_size), Image.Resampling.LANCZOS)
                avatar = fitted.convert("RGBA")
        except Exception as exc:
            self._log(f"Could not load profile image, using fallback avatar: {exc}")

        mask = Image.new("L", (avatar_size, avatar_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
        framed = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
        framed.paste(avatar, (0, 0), mask)
        return framed

    def _fit_image_to_box(self, image: Image.Image, width: int, height: int) -> Image.Image:
        return ImageOps.fit(image.convert("RGBA"), (width, height), Image.Resampling.LANCZOS)

    def _load_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        ]
        for candidate in candidates:
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
        return ImageFont.load_default()

    def _story_pk_from_identifier(self, story_identifier: str) -> str:
        value = story_identifier.strip()
        if value.isdigit():
            return value
        if "/stories/" in value:
            return self.client.story_pk_from_url(value)
        raise ValueError(
            "story_identifier must be either a numeric story pk or a full "
            "https://www.instagram.com/stories/<user>/<story_pk>/ URL"
        )

    @staticmethod
    def parse_extra_story_config(raw_json: str) -> Dict[str, Any]:
        text = raw_json.strip()
        if not text:
            return {}
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("extra story config must be a JSON object")
        return parsed

    @staticmethod
    def default_story_payload_for_media(media_type: int) -> Dict[str, Any]:
        if media_type == 2:
            return {
                "source_type": "4",
                "clips": {
                    "source_type": "4",
                    "camera_position": "back",
                },
            }
        return {"source_type": "4"}
