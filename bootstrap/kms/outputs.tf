output "kms_vault_id" {
  value = oci_kms_vault.vault_unseal.id
}

output "kms_key_id" {
  value = oci_kms_key.vault_unseal.id
}

output "crypto_endpoint" {
  value = oci_kms_vault.vault_unseal.crypto_endpoint
}

output "management_endpoint" {
  value = oci_kms_vault.vault_unseal.management_endpoint
}

output "kubernetes_secret" {
  value = "${kubernetes_secret_v1.vault_oci_kms.metadata[0].namespace}/${kubernetes_secret_v1.vault_oci_kms.metadata[0].name}"
}

output "migrate_hint" {
  value = <<-EOT
    After Argo syncs templates/apps/vault.yaml with ocikms seal wiring:
      kubectl -n vault delete pod vault-0
      kubectl -n vault exec -it vault-0 -- vault operator unseal -migrate
    Then restart once more and confirm Seal Type=ocikms and Sealed=false without manual unseal.
  EOT
}
