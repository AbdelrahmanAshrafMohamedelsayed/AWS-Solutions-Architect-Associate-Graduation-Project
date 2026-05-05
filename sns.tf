resource "aws_sns_topic" "image_notifications" {
  name              = "${local.name_prefix}-image-notifications"
  kms_master_key_id = "alias/aws/sns"
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.notification_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.image_notifications.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

