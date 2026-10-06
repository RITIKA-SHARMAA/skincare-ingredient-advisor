variable "project_id" {
  description = "GCP project to deploy into."
  type        = string
}

variable "region" {
  description = "Region for Cloud Run, Cloud SQL, Artifact Registry and the bucket."
  type        = string
  default     = "asia-south1"
}

variable "billing_account_id" {
  description = "Billing account ID (XXXXXX-XXXXXX-XXXXXX) that the budget alert is attached to."
  type        = string
}

variable "budget_amount" {
  description = "Monthly budget alert threshold, in the billing account's currency."
  type        = number
  default     = 1500
}

variable "budget_currency" {
  description = "Must match the billing account's currency."
  type        = string
  default     = "INR"
}

variable "github_repository" {
  description = "owner/name of the repository allowed to deploy through Workload Identity Federation."
  type        = string
  default     = "RITIKA-SHARMAA/skincare-ingredient-advisor"
}

variable "api_image" {
  description = "Initial API image. The deploy workflow replaces it; Terraform ignores later changes."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "web_image" {
  description = "Initial web image. The deploy workflow replaces it; Terraform ignores later changes."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "cors_origins" {
  description = "Comma-separated browser origins allowed to call the API. Set to the web URL after the first apply."
  type        = string
  default     = "*"
}

variable "vertex_location" {
  description = "Vertex AI location for Gemini."
  type        = string
  default     = "global"
}

variable "vertex_model" {
  type    = string
  default = "gemini-2.5-flash"
}

variable "db_tier" {
  description = "Smallest shared-core tier; fine for a demo, not for production."
  type        = string
  default     = "db-f1-micro"
}
