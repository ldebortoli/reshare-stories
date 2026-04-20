from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, TwoFactorRequired
from instagrapi.types import StoryMention, UserShort
from PIL import Image

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
    ) -> StoryReshareResult:
        story_pk = self._story_pk_from_identifier(story_identifier)
        story = self.client.story_info(story_pk)
        owner = self.client.user_info_v1(story.user.pk)
        media_url = str(story.thumbnail_url if story.media_type == 1 else story.video_url)
        download_dir = Path(tempfile.mkdtemp(prefix="ig-story-reshare-"))
        downloaded_path = self.client.story_download(story.pk, folder=download_dir)
        upload_path = self._normalize_story_media_for_upload(downloaded_path, story.media_type)
        mentions = []

        if mention_original_author:
            mentions.append(
                StoryMention(
                    user=UserShort(pk=owner.pk, username=owner.username, profile_pic_url=owner.profile_pic_url),
                    x=0.5,
                    y=0.9,
                    width=0.8,
                    height=0.12,
                )
            )

        extra_story_config = extra_story_config or {}
        self._log(f"Uploading story derived from source story {story.pk}.")
        if story.media_type == 1:
            published = self.client.photo_upload_to_story(
                upload_path,
                mentions=mentions,
                extra_data=extra_story_config,
            )
        else:
            published = self.client.video_upload_to_story(
                upload_path,
                mentions=mentions,
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
            mode="reupload_story_media",
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
