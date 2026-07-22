provider "oci" {
  region = var.region

  # SecurityToken: use a fresh `oci session authenticate --profile <name>` profile.
  # ApiKey: set user_ocid / fingerprint / private_key_path instead.
  auth                = var.auth
  config_file_profile = var.auth == "SecurityToken" ? var.config_file_profile : null

  tenancy_ocid         = var.auth == "ApiKey" ? var.tenancy_ocid : null
  user_ocid            = var.auth == "ApiKey" ? var.user_ocid : null
  fingerprint          = var.auth == "ApiKey" ? var.fingerprint : null
  private_key_path     = var.auth == "ApiKey" ? var.private_key_path : null
  private_key_password = var.auth == "ApiKey" ? var.private_key_password : null
}

provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kubeconfig_context
}
