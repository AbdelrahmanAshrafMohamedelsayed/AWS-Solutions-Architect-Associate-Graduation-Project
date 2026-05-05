from __future__ import annotations

import os

import boto3

from common.image_utils import build_processed_keys, render_processed_images

s3 = boto3.client("s3")

PROCESSED_BUCKET = os.environ["PROCESSED_BUCKET"]
WATERMARK_TEXT = os.environ.get("WATERMARK_TEXT", "SAA Demo")
THUMBNAIL_MAX_PX = int(os.environ.get("THUMBNAIL_MAX_PX", "320"))
DISPLAY_MAX_PX = int(os.environ.get("DISPLAY_MAX_PX", "1280"))


def handler(event, _context):
    image_id = event["imageId"]
    source_bucket = event["sourceBucket"]
    source_key = event["sourceKey"]

    source_object = s3.get_object(Bucket=source_bucket, Key=source_key)
    source_bytes = source_object["Body"].read()
    rendered = render_processed_images(
        source_bytes,
        WATERMARK_TEXT,
        THUMBNAIL_MAX_PX,
        DISPLAY_MAX_PX,
    )
    keys = build_processed_keys(image_id)

    s3.put_object(
        Bucket=PROCESSED_BUCKET,
        Key=keys["thumbnailKey"],
        Body=rendered["thumbnailBytes"],
        ContentType="image/jpeg",
        ServerSideEncryption="AES256",
        Tagging=f"imageId={image_id}&variant=thumbnail",
    )
    s3.put_object(
        Bucket=PROCESSED_BUCKET,
        Key=keys["displayKey"],
        Body=rendered["displayBytes"],
        ContentType="image/jpeg",
        ServerSideEncryption="AES256",
        Tagging=f"imageId={image_id}&variant=display",
    )

    return {
        "imageId": image_id,
        "sourceBucket": source_bucket,
        "sourceKey": source_key,
        "processedBucket": PROCESSED_BUCKET,
        "thumbnailKey": keys["thumbnailKey"],
        "displayKey": keys["displayKey"],
        "metadata": rendered["metadata"],
    }

