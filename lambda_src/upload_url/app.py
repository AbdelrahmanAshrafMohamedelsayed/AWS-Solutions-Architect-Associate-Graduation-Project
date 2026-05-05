from __future__ import annotations

import os

import boto3

from common.image_utils import (
    STATUS_PENDING,
    build_source_key,
    json_response,
    new_image_id,
    parse_json_body,
    utc_now_iso,
    validate_upload_payload,
)

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

SOURCE_BUCKET = os.environ["SOURCE_BUCKET"]
METADATA_TABLE = os.environ["METADATA_TABLE"]
UPLOAD_EXPIRES_SECONDS = int(os.environ.get("UPLOAD_EXPIRES_SECONDS", "900"))
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")


def handler(event, _context):
    try:
        payload = validate_upload_payload(parse_json_body(event))
    except ValueError as exc:
        return json_response(400, {"message": str(exc)}, ALLOWED_ORIGIN)

    image_id = new_image_id()
    object_key = build_source_key(image_id, payload["filename"])
    created_at = utc_now_iso()

    table = dynamodb.Table(METADATA_TABLE)
    table.put_item(
        Item={
            "imageId": image_id,
            "status": STATUS_PENDING,
            "sourceBucket": SOURCE_BUCKET,
            "sourceKey": object_key,
            "originalFilename": payload["filename"],
            "contentType": payload["contentType"],
            "createdAt": created_at,
            "updatedAt": created_at,
        },
        ConditionExpression="attribute_not_exists(imageId)",
    )

    upload_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": SOURCE_BUCKET,
            "Key": object_key,
            "ContentType": payload["contentType"],
        },
        ExpiresIn=UPLOAD_EXPIRES_SECONDS,
        HttpMethod="PUT",
    )

    return json_response(
        201,
        {
            "imageId": image_id,
            "objectKey": object_key,
            "uploadUrl": upload_url,
            "expiresIn": UPLOAD_EXPIRES_SECONDS,
        },
        ALLOWED_ORIGIN,
    )

