resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/vendedlogs/states/${local.name_prefix}-image-processing"
  retention_in_days = 14
}

resource "aws_sfn_state_machine" "image_processing" {
  name     = "${local.name_prefix}-image-processing"
  role_arn = aws_iam_role.step_functions.arn
  type     = "STANDARD"

  logging_configuration {
    include_execution_data = true
    level                  = "ALL"
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
  }

  definition = jsonencode({
    Comment = "Validate, process, store metadata, and notify for uploaded images."
    StartAt = "MarkProcessing"
    States = {
      MarkProcessing = {
        Type     = "Task"
        Resource = "arn:aws:states:::dynamodb:updateItem"
        Parameters = {
          TableName = aws_dynamodb_table.images.name
          Key = {
            imageId = { "S.$" = "$.imageId" }
          }
          UpdateExpression = "SET #status = :status, updatedAt = :updatedAt"
          ExpressionAttributeNames = {
            "#status" = "status"
          }
          ExpressionAttributeValues = {
            ":status"    = { S = "PROCESSING" }
            ":updatedAt" = { "S.$" = "$$.State.EnteredTime" }
          }
        }
        ResultPath = null
        Next       = "ProcessImage"
      }
      ProcessImage = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.processor.arn
          "Payload.$"  = "$"
        }
        OutputPath = "$.Payload"
        Next       = "StoreProcessedMetadata"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath   = "$.error"
            Next         = "MarkFailed"
          }
        ]
      }
      StoreProcessedMetadata = {
        Type     = "Task"
        Resource = "arn:aws:states:::dynamodb:updateItem"
        Parameters = {
          TableName = aws_dynamodb_table.images.name
          Key = {
            imageId = { "S.$" = "$.imageId" }
          }
          UpdateExpression = "SET #status = :status, processedBucket = :processedBucket, thumbnailKey = :thumbnailKey, displayKey = :displayKey, sourceWidth = :sourceWidth, sourceHeight = :sourceHeight, processedAt = :processedAt, updatedAt = :updatedAt REMOVE failureReason"
          ExpressionAttributeNames = {
            "#status" = "status"
          }
          ExpressionAttributeValues = {
            ":status"          = { S = "PROCESSED" }
            ":processedBucket" = { "S.$" = "$.processedBucket" }
            ":thumbnailKey"    = { "S.$" = "$.thumbnailKey" }
            ":displayKey"      = { "S.$" = "$.displayKey" }
            ":sourceWidth"     = { "N.$" = "States.Format('{}', $.metadata.sourceWidth)" }
            ":sourceHeight"    = { "N.$" = "States.Format('{}', $.metadata.sourceHeight)" }
            ":processedAt"     = { "S.$" = "$$.State.EnteredTime" }
            ":updatedAt"       = { "S.$" = "$$.State.EnteredTime" }
          }
        }
        ResultPath = null
        Next       = "PublishSuccess"
      }
      PublishSuccess = {
        Type     = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          TopicArn = aws_sns_topic.image_notifications.arn
          Subject  = "Image processed"
          "Message.$" = "States.Format('Image {} processed successfully. Display URL: https://${aws_cloudfront_distribution.processed.domain_name}/{}', $.imageId, $.displayKey)"
        }
        ResultPath = null
        End        = true
      }
      MarkFailed = {
        Type     = "Task"
        Resource = "arn:aws:states:::dynamodb:updateItem"
        Parameters = {
          TableName = aws_dynamodb_table.images.name
          Key = {
            imageId = { "S.$" = "$.imageId" }
          }
          UpdateExpression = "SET #status = :status, failureReason = :failureReason, updatedAt = :updatedAt"
          ExpressionAttributeNames = {
            "#status" = "status"
          }
          ExpressionAttributeValues = {
            ":status"        = { S = "FAILED" }
            ":failureReason" = { "S.$" = "$.error.Cause" }
            ":updatedAt"     = { "S.$" = "$$.State.EnteredTime" }
          }
        }
        ResultPath = null
        Next       = "PublishFailure"
      }
      PublishFailure = {
        Type     = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Parameters = {
          TopicArn = aws_sns_topic.image_notifications.arn
          Subject  = "Image processing failed"
          "Message.$" = "States.Format('Image {} failed during processing. Check Step Functions execution history and DynamoDB metadata.', $.imageId)"
        }
        ResultPath = null
        End        = true
      }
    }
  })

  depends_on = [
    aws_iam_role_policy.step_functions,
    aws_cloudwatch_log_group.step_functions
  ]
}

