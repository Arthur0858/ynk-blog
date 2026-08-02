#!/usr/bin/env python3
"""Generate responsive WebP variants for ParentTech guide cards."""

from pathlib import Path

from PIL import Image


SITE_DIR = Path(__file__).resolve().parents[1]
HOME_IMAGES = (
    "senior-phone-guide-thumbnail.jpg",
    "scam-call-safety-guide-thumbnail-v2.jpg",
    "video-calling-guide-thumbnail.jpg",
    "living-alone-safety-guide-thumbnail.jpg",
    "parent-tech-quick-start-kit-cover.jpg",
)


def main() -> None:
    count = 0
    sources = sorted((SITE_DIR / "assets" / "guides").glob("*.jpg"))
    sources.extend(SITE_DIR / "assets" / name for name in HOME_IMAGES)
    for source in sources:
        with Image.open(source) as original:
            image = original.convert("RGB")
            for width in (480, 720):
                height = round(image.height * width / image.width)
                target = source.with_name(f"{source.stem}-{width}.webp")
                image.resize((width, height), Image.Resampling.LANCZOS).save(target, "WEBP", quality=78, method=6)
                count += 1
    print(f"generated {count} responsive guide images")


if __name__ == "__main__":
    main()
