"""Standalone configuration validator — no Telegram connectivity required.

Usage:
    uv run caciarabot-validate [--config-dir config] [--media-dir media]
    uv run python -m caciarabot.validate
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from caciarabot.bootstrap import load_configuration
from caciarabot.config.errors import ConfigError
from caciarabot.config.models import PhotoResponse, RandomPhotoResponse
from caciarabot.telegram.media import IMAGE_EXTENSIONS


def _check_media(media_dir: Path, rules: list) -> tuple[list[ConfigError], set[Path]]:
    errors: list[ConfigError] = []
    seen_media_files: set[Path] = set()

    for rule in rules:
        for response in rule.responses:
            if isinstance(response, PhotoResponse):
                path = media_dir / response.path
                if not path.is_file():
                    errors.append(
                        ConfigError(
                            file=rule.source_file,
                            line=rule.source_line,
                            message=f"missing media file: {path}",
                            record_id=rule.id,
                        )
                    )
                else:
                    seen_media_files.add(path)
            elif isinstance(response, RandomPhotoResponse):
                directory = media_dir / response.directory
                if not directory.is_dir():
                    errors.append(
                        ConfigError(
                            file=rule.source_file,
                            line=rule.source_line,
                            message=f"missing media directory: {directory}",
                            record_id=rule.id,
                        )
                    )
                else:
                    seen_media_files.update(
                        p
                        for p in directory.iterdir()
                        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
                    )

    return errors, seen_media_files


def _count_config_files(config_dir: Path) -> int:
    top_level = ["bot.jsonc", "normalization.jsonc", "limits.jsonc"]
    count = sum(1 for name in top_level if (config_dir / name).is_file())
    packs_dir = config_dir / "packs"
    if packs_dir.is_dir():
        for pack_dir in packs_dir.iterdir():
            if not pack_dir.is_dir():
                continue
            count += sum(1 for _ in pack_dir.glob("*.jsonc"))
            count += sum(1 for _ in pack_dir.glob("*.jsonl"))
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate CaciaraBot configuration.")
    parser.add_argument(
        "--config-dir", default=os.environ.get("CACIARABOT_CONFIG_DIR", "config"), type=Path
    )
    parser.add_argument(
        "--media-dir", default=os.environ.get("CACIARABOT_MEDIA_DIR", "media"), type=Path
    )
    args = parser.parse_args()

    bot_config, _normalization_options, _limits_config, rules, errors = load_configuration(
        args.config_dir
    )

    media_errors, media_files = ([], set())
    if not errors:
        media_errors, media_files = _check_media(args.media_dir, rules)

    all_errors = [*errors, *media_errors]

    if all_errors:
        print("Configuration invalid.\n", file=sys.stderr)
        for error in all_errors:
            print(str(error), file=sys.stderr)
        print(f"\n{len(all_errors)} errors", file=sys.stderr)
        sys.exit(1)

    config_file_count = _count_config_files(args.config_dir)
    print("Configuration valid.")
    print(f"{config_file_count} files")
    print(f"{len(rules)} reaction rules")
    print(f"{len(media_files)} local media files")
    print("0 errors")


if __name__ == "__main__":
    main()
