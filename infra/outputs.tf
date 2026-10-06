output "api_url" {value=google_cloud_run_v2_service.api.uri} output "web_url" {value=google_cloud_run_v2_service.web.uri} output "bucket" {value=google_storage_bucket.labels.name}
