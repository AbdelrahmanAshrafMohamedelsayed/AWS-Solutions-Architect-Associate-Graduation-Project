variable "project_name" {
  description = "Project name used as a prefix for AWS resources."
  type        = string
  default     = "saa-image-pipeline"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{2,40}$", var.project_name))
    error_message = "project_name must be 3-41 characters using lowercase letters, numbers, and hyphens."
  }
}

variable "aws_region" {
  description = "AWS region where regional resources will be deployed."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name used in resource names and tags."
  type        = string
  default     = "dev"

  validation {
    condition     = can(regex("^[a-z0-9-]{2,16}$", var.environment))
    error_message = "environment must be 2-16 characters using lowercase letters, numbers, and hyphens."
  }
}

variable "notification_email" {
  description = "Optional email address subscribed to image processing completion and failure notifications."
  type        = string
  default     = ""
}

variable "watermark_text" {
  description = "Text rendered onto processed image variants."
  type        = string
  default     = "SAA Demo"
}

variable "thumbnail_max_px" {
  description = "Maximum width or height for thumbnail images."
  type        = number
  default     = 320
}

variable "display_max_px" {
  description = "Maximum width or height for display images."
  type        = number
  default     = 1280
}

variable "lambda_package_file" {
  description = "Path to the Lambda deployment zip created by scripts/package_lambdas.sh."
  type        = string
  default     = "build/lambda-package.zip"
}

