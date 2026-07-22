variable "region" {
  type        = string
  description = "OCI region for the KMS vault (same region as the cluster VMs)."
  default     = "sa-saopaulo-1"
}

variable "tenancy_ocid" {
  type        = string
  description = "Tenancy OCID where the KMS vault and IAM user will live."
}

variable "compartment_ocid" {
  type        = string
  description = "Compartment for the KMS vault/key. Defaults to the tenancy (root)."
  default     = ""
}

variable "auth" {
  type        = string
  description = "OCI provider auth: ApiKey or SecurityToken."
  default     = "ApiKey"

  validation {
    condition     = contains(["ApiKey", "SecurityToken"], var.auth)
    error_message = "auth must be ApiKey or SecurityToken."
  }
}

variable "config_file_profile" {
  type        = string
  description = "OCI config profile when auth = SecurityToken."
  default     = "DEFAULT"
}

variable "user_ocid" {
  type        = string
  description = "Admin user OCID for Terraform when auth = ApiKey."
  default     = ""
}

variable "fingerprint" {
  type        = string
  description = "API key fingerprint for Terraform when auth = ApiKey."
  default     = ""
}

variable "private_key_path" {
  type        = string
  description = "Path to the Terraform API private key when auth = ApiKey."
  default     = ""
}

variable "private_key_password" {
  type        = string
  description = "Optional passphrase for private_key_path."
  default     = ""
  sensitive   = true
}

variable "kubeconfig_path" {
  type    = string
  default = "~/.kube/config"
}

variable "kubeconfig_context" {
  type    = string
  default = "shardblade-001"
}

variable "vault_display_name" {
  type        = string
  description = "Display name for the OCI KMS vault."
  default     = "shardblade-vault-unseal"
}

variable "key_display_name" {
  type        = string
  description = "Display name for the master encryption key (software-protected, Always Free)."
  default     = "hashicorp-vault-auto-unseal"
}

variable "vault_unseal_user_email" {
  type        = string
  description = "Primary email for the dedicated HashiCorp Vault KMS IAM user (required by OCI Identity)."
}

