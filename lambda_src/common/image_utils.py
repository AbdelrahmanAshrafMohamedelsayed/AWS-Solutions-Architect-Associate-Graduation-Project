from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any

from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

STATUS_PENDING = "PENDING"
STATUS_PROCESSING = "PROCESSING"
STATUS_PROCESSED = "PROCESSED"
STATUS_FAILED = "FAILED"

SUPPORTED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}

SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_image_id() -> str:
    return str(uuid.uuid4())


def json_response(status_code: int, body: dict[str, Any], allowed_origin: str = "*") -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json",
            "access-control-allow-origin": allowed_origin,
        },
        "body": json.dumps(body),
    }


def parse_json_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body")
    if body is None:
        return {}
    if isinstance(body, dict):
        return body
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON.") from exc


def validate_upload_payload(payload: dict[str, Any]) -> dict[str, str]:
    filename = str(payload.get("filename", "")).strip()
    content_type = str(payload.get("contentType", "")).strip().lower()

    if not filename:
        raise ValueError("filename is required.")
    if content_type not in SUPPORTED_CONTENT_TYPES:
        supported = ", ".join(sorted(SUPPORTED_CONTENT_TYPES))
        raise ValueError(f"contentType must be one of: {supported}.")

    suffix = PurePosixPath(filename).suffix.lower()
    allowed_suffix = SUPPORTED_CONTENT_TYPES[content_type]
    if content_type == "image/jpeg" and suffix == ".jpeg":
        suffix = ".jpg"
    if suffix != allowed_suffix:
        raise ValueError(f"filename extension must match {content_type}.")

    return {
        "filename": sanitize_filename(filename),
        "contentType": content_type,
    }


def sanitize_filename(filename: str) -> str:
    name = PurePosixPath(filename).name.strip()
    sanitized = SAFE_FILENAME_RE.sub("-", name).strip(".-")
    return sanitized or "upload.jpg"


def build_source_key(image_id: str, filename: str) -> str:
    return f"uploads/{image_id}/{sanitize_filename(filename)}"


def extract_image_id_from_source_key(source_key: str) -> str:
    parts = PurePosixPath(source_key).parts
    if len(parts) < 3 or parts[0] != "uploads":
        raise ValueError("S3 object key must use uploads/{imageId}/{filename}.")
    return parts[1]


def build_processed_keys(image_id: str) -> dict[str, str]:
    return {
        "thumbnailKey": f"processed/{image_id}/thumbnail.jpg",
        "displayKey": f"processed/{image_id}/display.jpg",
    }


def parse_s3_records_from_sqs_event(event: dict[str, Any]) -> list[dict[str, str]]:
    parsed_records: list[dict[str, str]] = []

    for sqs_record in event.get("Records", []):
        body = json.loads(sqs_record["body"])
        for s3_record in body.get("Records", []):
            bucket = s3_record["s3"]["bucket"]["name"]
            key = s3_record["s3"]["object"]["key"].replace("+", " ")
            parsed_records.append(
                {
                    "imageId": extract_image_id_from_source_key(key),
                    "sourceBucket": bucket,
                    "sourceKey": key,
                }
            )

    return parsed_records


def render_processed_images(
    image_bytes: bytes,
    watermark_text: str,
    thumbnail_max_px: int,
    display_max_px: int,
) -> dict[str, Any]:
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            source = ImageOps.exif_transpose(source)
            metadata = {
                "sourceWidth": source.width,
                "sourceHeight": source.height,
                "sourceFormat": source.format or "UNKNOWN",
            }
            rgba_source = source.convert("RGBA")
    except UnidentifiedImageError as exc:
        raise ValueError("Unsupported or corrupt image file.") from exc

    display = ImageOps.contain(rgba_source.copy(), (display_max_px, display_max_px))
    thumbnail = ImageOps.contain(rgba_source.copy(), (thumbnail_max_px, thumbnail_max_px))

    return {
        "thumbnailBytes": _to_jpeg_bytes(_apply_watermark(thumbnail, watermark_text)),
        "displayBytes": _to_jpeg_bytes(_apply_watermark(display, watermark_text)),
        "metadata": metadata,
    }


def _apply_watermark(image: Image.Image, watermark_text: str) -> Image.Image:
    if not watermark_text:
        return image

    watermarked = image.copy()
    draw = ImageDraw.Draw(watermarked)
    text_bbox = draw.textbbox((0, 0), watermark_text)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    margin = max(8, min(watermarked.size) // 24)
    padding = max(6, margin // 2)
    x = max(margin, watermarked.width - text_width - margin - padding)
    y = max(margin, watermarked.height - text_height - margin - padding)

    draw.rounded_rectangle(
        (x - padding, y - padding, x + text_width + padding, y + text_height + padding),
        radius=4,
        fill=(0, 0, 0, 150),
    )
    draw.text((x, y), watermark_text, fill=(255, 255, 255, 230))
    return watermarked


def _to_jpeg_bytes(image: Image.Image) -> bytes:
    rgb = Image.new("RGB", image.size, "white")
    if image.mode == "RGBA":
        rgb.paste(image, mask=image.getchannel("A"))
    else:
        rgb.paste(image)

    buffer = BytesIO()
    rgb.save(buffer, format="JPEG", quality=88, optimize=True)
    return buffer.getvalue()

