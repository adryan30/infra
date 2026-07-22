locals {
  compartment_ocid = var.compartment_ocid != "" ? var.compartment_ocid : var.tenancy_ocid
}

# ---------------------------------------------------------------------------
# OCI KMS — software-protected key (Always Free)
# ---------------------------------------------------------------------------

resource "oci_kms_vault" "vault_unseal" {
  compartment_id = local.compartment_ocid
  display_name   = var.vault_display_name
  vault_type     = "DEFAULT"
}

resource "oci_kms_key" "vault_unseal" {
  compartment_id      = local.compartment_ocid
  display_name        = var.key_display_name
  management_endpoint = oci_kms_vault.vault_unseal.management_endpoint
  protection_mode     = "SOFTWARE"

  key_shape {
    algorithm = "AES"
    length    = 32
  }

  depends_on = [oci_kms_vault.vault_unseal]
}

# ---------------------------------------------------------------------------
# Dedicated IAM user + API key for HashiCorp Vault (API-key seal auth).
# Instance principal is unreliable here: cluster nodes span tenancies and
# Vault pods need a stable principal that can call KMS over the network.
# ---------------------------------------------------------------------------

resource "tls_private_key" "vault_unseal" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "oci_identity_user" "vault_unseal" {
  compartment_id = var.tenancy_ocid
  name           = "hashicorp-vault-kms-unseal"
  description    = "API-key principal for HashiCorp Vault ocikms auto-unseal"
  email          = var.vault_unseal_user_email
}

resource "oci_identity_group" "vault_unseal" {
  compartment_id = var.tenancy_ocid
  name           = "hashicorp-vault-kms-unseal"
  description    = "Can use the HashiCorp Vault auto-unseal KMS key"
}

resource "oci_identity_user_group_membership" "vault_unseal" {
  group_id = oci_identity_group.vault_unseal.id
  user_id  = oci_identity_user.vault_unseal.id
}

resource "oci_identity_api_key" "vault_unseal" {
  user_id   = oci_identity_user.vault_unseal.id
  key_value = tls_private_key.vault_unseal.public_key_pem
}

resource "oci_identity_policy" "vault_unseal" {
  compartment_id = local.compartment_ocid
  name           = "hashicorp-vault-kms-unseal"
  description    = "Allow HashiCorp Vault unseal user to use the auto-unseal key"

  statements = [
    "Allow group ${oci_identity_group.vault_unseal.name} to use keys in compartment id ${local.compartment_ocid} where target.key.id = '${oci_kms_key.vault_unseal.id}'",
    "Allow group ${oci_identity_group.vault_unseal.name} to use key-delegate in compartment id ${local.compartment_ocid} where target.key.id = '${oci_kms_key.vault_unseal.id}'",
  ]

  depends_on = [
    oci_kms_key.vault_unseal,
    oci_identity_user_group_membership.vault_unseal,
  ]
}

# ---------------------------------------------------------------------------
# Kubernetes secret consumed by the Vault Helm chart (extraVolumes + env).
# ---------------------------------------------------------------------------

locals {
  oci_config = <<-EOT
    [DEFAULT]
    user=${oci_identity_user.vault_unseal.id}
    fingerprint=${oci_identity_api_key.vault_unseal.fingerprint}
    key_file=/vault/userconfig/vault-oci-kms/oci_api_key.pem
    tenancy=${var.tenancy_ocid}
    region=${var.region}
  EOT
}

resource "kubernetes_secret_v1" "vault_oci_kms" {
  metadata {
    name      = "vault-oci-kms"
    namespace = "vault"
    labels = {
      "app.kubernetes.io/name"       = "vault"
      "app.kubernetes.io/component"  = "oci-kms-seal"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  data = {
    config                           = local.oci_config
    "oci_api_key.pem"                = tls_private_key.vault_unseal.private_key_pem
    VAULT_SEAL_TYPE                  = "ocikms"
    VAULT_OCIKMS_SEAL_KEY_ID         = oci_kms_key.vault_unseal.id
    VAULT_OCIKMS_CRYPTO_ENDPOINT     = oci_kms_vault.vault_unseal.crypto_endpoint
    VAULT_OCIKMS_MANAGEMENT_ENDPOINT = oci_kms_vault.vault_unseal.management_endpoint
  }

  type = "Opaque"
}
