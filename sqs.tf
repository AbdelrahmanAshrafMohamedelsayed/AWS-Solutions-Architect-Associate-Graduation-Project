resource "aws_sqs_queue" "image_events_dlq" {
  name                      = "${local.name_prefix}-image-events-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "image_events" {
  name                       = "${local.name_prefix}-image-events"
  visibility_timeout_seconds = 180
  message_retention_seconds  = 345600
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.image_events_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue_policy" "image_events" {
  queue_url = aws_sqs_queue.image_events.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowSourceBucketEvents"
        Effect    = "Allow"
        Principal = { Service = "s3.amazonaws.com" }
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.image_events.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_s3_bucket.source.arn
          }
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

resource "aws_lambda_event_source_mapping" "image_events" {
  event_source_arn                   = aws_sqs_queue.image_events.arn
  function_name                      = aws_lambda_function.workflow_starter.arn
  batch_size                         = 5
  maximum_batching_window_in_seconds = 5
}

