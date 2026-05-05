import json
import unittest
from io import BytesIO

from PIL import Image

from lambda_src.common.image_utils import (
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_PROCESSED,
    STATUS_PROCESSING,
    build_processed_keys,
    build_source_key,
    extract_image_id_from_source_key,
    parse_s3_records_from_sqs_event,
    render_processed_images,
    validate_upload_payload,
)


class ImageUtilsTest(unittest.TestCase):
    def test_status_constants_match_documented_lifecycle(self):
        self.assertEqual(
            [STATUS_PENDING, STATUS_PROCESSING, STATUS_PROCESSED, STATUS_FAILED],
            ["PENDING", "PROCESSING", "PROCESSED", "FAILED"],
        )

    def test_validate_upload_payload_accepts_jpg(self):
        payload = validate_upload_payload(
            {
                "filename": "sample.jpg",
                "contentType": "image/jpeg",
            }
        )

        self.assertEqual(payload["filename"], "sample.jpg")
        self.assertEqual(payload["contentType"], "image/jpeg")

    def test_validate_upload_payload_rejects_invalid_content_type(self):
        with self.assertRaisesRegex(ValueError, "contentType must be one of"):
            validate_upload_payload(
                {
                    "filename": "sample.gif",
                    "contentType": "image/gif",
                }
            )

    def test_validate_upload_payload_rejects_mismatched_extension(self):
        with self.assertRaisesRegex(ValueError, "filename extension must match"):
            validate_upload_payload(
                {
                    "filename": "sample.png",
                    "contentType": "image/jpeg",
                }
            )

    def test_key_helpers_create_expected_paths(self):
        source_key = build_source_key("image-123", "../../My Upload.JPG")
        processed_keys = build_processed_keys("image-123")

        self.assertEqual(source_key, "uploads/image-123/My-Upload.JPG")
        self.assertEqual(extract_image_id_from_source_key(source_key), "image-123")
        self.assertEqual(processed_keys["thumbnailKey"], "processed/image-123/thumbnail.jpg")
        self.assertEqual(processed_keys["displayKey"], "processed/image-123/display.jpg")

    def test_parse_s3_records_from_sqs_event(self):
        s3_event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "source-bucket"},
                        "object": {"key": "uploads/image-123/sample.jpg"},
                    }
                }
            ]
        }
        sqs_event = {"Records": [{"body": json.dumps(s3_event)}]}

        records = parse_s3_records_from_sqs_event(sqs_event)

        self.assertEqual(
            records,
            [
                {
                    "imageId": "image-123",
                    "sourceBucket": "source-bucket",
                    "sourceKey": "uploads/image-123/sample.jpg",
                }
            ],
        )

    def test_render_processed_images_resizes_and_returns_jpeg_bytes(self):
        image = Image.new("RGB", (800, 600), color=(40, 120, 200))
        source = BytesIO()
        image.save(source, format="PNG")

        rendered = render_processed_images(source.getvalue(), "SAA Demo", 120, 300)

        self.assertEqual(rendered["metadata"]["sourceWidth"], 800)
        self.assertEqual(rendered["metadata"]["sourceHeight"], 600)
        self.assertGreater(len(rendered["thumbnailBytes"]), 100)
        self.assertGreater(len(rendered["displayBytes"]), 100)

        thumbnail = Image.open(BytesIO(rendered["thumbnailBytes"]))
        display = Image.open(BytesIO(rendered["displayBytes"]))
        self.assertLessEqual(max(thumbnail.size), 120)
        self.assertLessEqual(max(display.size), 300)
        self.assertEqual(thumbnail.format, "JPEG")
        self.assertEqual(display.format, "JPEG")

    def test_render_processed_images_rejects_corrupt_file(self):
        with self.assertRaisesRegex(ValueError, "Unsupported or corrupt image file"):
            render_processed_images(b"not an image", "SAA Demo", 120, 300)


if __name__ == "__main__":
    unittest.main()

