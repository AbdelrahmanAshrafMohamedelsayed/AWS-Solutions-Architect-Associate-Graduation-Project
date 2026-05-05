resource "aws_cloudwatch_log_group" "upload_url" {
  name              = "/aws/lambda/${local.name_prefix}-upload-url"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "workflow_starter" {
  name              = "/aws/lambda/${local.name_prefix}-workflow-starter"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "processor" {
  name              = "/aws/lambda/${local.name_prefix}-processor"
  retention_in_days = 14
}

resource "aws_lambda_function" "upload_url" {
  function_name = "${local.name_prefix}-upload-url"
  role          = aws_iam_role.upload_url_lambda.arn
  handler       = "upload_url.app.handler"
  runtime       = "python3.12"
  filename      = var.lambda_package_file
  timeout       = 15
  memory_size   = 256

  environment {
    variables = {
      SOURCE_BUCKET          = aws_s3_bucket.source.bucket
      METADATA_TABLE         = aws_dynamodb_table.images.name
      UPLOAD_EXPIRES_SECONDS = "900"
      ALLOWED_ORIGIN         = "*"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.upload_url,
    aws_iam_role_policy_attachment.upload_url_basic,
    aws_iam_role_policy.upload_url
  ]
}

resource "aws_lambda_function" "workflow_starter" {
  function_name = "${local.name_prefix}-workflow-starter"
  role          = aws_iam_role.workflow_starter_lambda.arn
  handler       = "workflow_starter.app.handler"
  runtime       = "python3.12"
  filename      = var.lambda_package_file
  timeout       = 30
  memory_size   = 256

  environment {
    variables = {
      STATE_MACHINE_ARN = aws_sfn_state_machine.image_processing.arn
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.workflow_starter,
    aws_iam_role_policy_attachment.workflow_starter_basic,
    aws_iam_role_policy.workflow_starter
  ]
}

resource "aws_lambda_function" "processor" {
  function_name = "${local.name_prefix}-processor"
  role          = aws_iam_role.processor_lambda.arn
  handler       = "processor.app.handler"
  runtime       = "python3.12"
  filename      = var.lambda_package_file
  timeout       = 60
  memory_size   = 1024

  environment {
    variables = {
      PROCESSED_BUCKET = aws_s3_bucket.processed.bucket
      WATERMARK_TEXT   = var.watermark_text
      THUMBNAIL_MAX_PX = tostring(var.thumbnail_max_px)
      DISPLAY_MAX_PX   = tostring(var.display_max_px)
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.processor,
    aws_iam_role_policy_attachment.processor_basic,
    aws_iam_role_policy.processor
  ]
}

