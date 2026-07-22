terraform {
  required_providers {
    kubernetes = {
      source = "hashicorp/kubernetes"
    }
  }
  required_version = ">= 1.8.0"
}

provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "shardblade-001"
}

resource "kubernetes_namespace" "keycloak" {
  metadata {
    name = "keycloak"
    labels = {
      istio-injection = "enabled"
    }
  }
}

resource "kubernetes_namespace" "argocd" {
  metadata {
    name = "argocd"
    labels = {
      "istio-injection" = "enabled"
    }
  }
}

resource "kubernetes_secret" "secret_vault_policy_token" {
  metadata {
    name      = "vault-policy-token"
    namespace = "vault"
  }
  data = {
    "token" = var.vault-policy-token
  }
}




resource "kubernetes_manifest" "argocd" {
  manifest = {
    apiVersion = "helm.cattle.io/v1"
    kind       = "HelmChart"

    metadata = {
      name      = "argocd"
      namespace = kubernetes_namespace.argocd.metadata[0].name
    }

    spec = {
      repo            = "https://argoproj.github.io/argo-helm"
      chart           = "argo-cd"
      targetNamespace = "argocd"
      version         = "9.1.0"
      valuesContent   = file("${path.module}/manifests/argo.yaml")
    }
  }
}


resource "kubernetes_manifest" "application_argocd_infra" {
  manifest = {
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"
    metadata = {
      finalizers = [
        "resources-finalizer.argocd.argoproj.io",
      ]
      name      = "infra"
      namespace = "argocd"
    }
    spec = {
      destination = {
        namespace = "default"
        server    = "https://kubernetes.default.svc"
      }
      project = "default"
      source = {
        path           = "./"
        repoURL        = "git@github.com:adryan30/infra.git"
        targetRevision = "HEAD"
      }
      syncPolicy = {
        automated = {
          enabled = true
          prune   = true
        }
      }
    }
  }
}

