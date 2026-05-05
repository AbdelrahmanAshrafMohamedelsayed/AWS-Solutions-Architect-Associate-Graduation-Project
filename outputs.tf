output "api_gateway_url" {
  description = "HTTP API endpoint used to request pre-signed upload URLs."
  value       = aws_apigatewayv2_api.uploads.api_endpoint
}

output "source_bucket_name" {
  description = "S3 bucket where original uploads are stored."
  value       = aws_s3_bucket.source.bucket
}

output "processed_bucket_name" {
  description = "S3 bucket where processed images are stored."
  value       = aws_s3_bucket.processed.bucket
}

output "cloudfront_domain_name" {
  description = "CloudFront domain that serves processed images."
  value       = aws_cloudfront_distribution.processed.domain_name
}

output "dynamodb_table_name" {
  description = "DynamoDB table that stores image job metadata."
  value       = aws_dynamodb_table.images.name
}

output "sqs_queue_url" {
  description = "SQS queue that receives S3 upload events."
  value       = aws_sqs_queue.image_events.url
}

output "step_functions_state_machine_arn" {
  description = "Step Functions state machine ARN for image processing."
  value       = aws_sfn_state_machine.image_processing.arn
}

