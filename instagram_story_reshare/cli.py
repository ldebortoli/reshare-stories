from __future__ import annotations

import argparse
import json
import sys
from getpass import getpass
from typing import Any, Dict

from .client import InstagramStoryReshareClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="instagram-story-reshare",
        description="Inspect and repost Instagram stories from a desktop workflow.",
    )
    parser.add_argument("--session-path", default="sessions/instagram_session.json")
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--sessionid")
    parser.add_argument(
        "--prompt-password",
        action="store_true",
        help="Prompt securely for the password if --password was not provided.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect-story", help="Fetch metadata for a story.")
    inspect_parser.add_argument("story_identifier")

    share_parser = subparsers.add_parser("share-story", help="Re-upload a story to your account.")
    share_parser.add_argument("story_identifier")
    share_parser.add_argument("--mention-original-author", action="store_true")
    share_parser.add_argument(
        "--publish-mode",
        choices=["reupload", "reupload_with_story_media_attachment"],
        default="reupload",
        help="How to publish the new story.",
    )
    share_parser.add_argument(
        "--extra-story-config-json",
        default="",
        help="Raw JSON object merged into the configure_to_story payload.",
    )

    subparsers.add_parser("session-info", help="Print the current runtime metadata.")
    return parser


def prompt_code(label: str) -> str:
    return input(f"Enter value for {label}: ").strip()


def make_client(args: argparse.Namespace) -> InstagramStoryReshareClient:
    client = InstagramStoryReshareClient(session_path=args.session_path, logger=lambda msg: print(msg, file=sys.stderr))
    password = args.password
    if not password and args.prompt_password:
        password = getpass("Instagram password: ")

    client.login(
        username=args.username,
        password=password,
        sessionid=args.sessionid,
        verification_code_handler=prompt_code,
    )
    return client


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    client = make_client(args)

    if args.command == "inspect-story":
        payload: Dict[str, Any] = client.inspect_story(args.story_identifier)
    elif args.command == "share-story":
        extra_config = client.parse_extra_story_config(args.extra_story_config_json)
        payload = client.repost_story(
            args.story_identifier,
            mention_original_author=args.mention_original_author,
            extra_story_config=extra_config,
            publish_mode=args.publish_mode,
        ).to_dict()
    elif args.command == "session-info":
        payload = client.export_runtime_metadata()
    else:
        parser.error(f"Unsupported command: {args.command}")
        return 2

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
