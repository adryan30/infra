{{/*
Sphere role password pack.

sphere.rolePassword renders ExternalSecret (generate) + PushSecret (Vault) for one
managed Sphere role. Callers stay as thin files under templates/storage/passwords/.

Required:
  role — Sphere role / secret suffix (sphere-<role>, storage/sphere-<role>)

Optional:
  database          — DB name in URI/pgpass (default: role)
  creationPolicy    — ESO target creationPolicy (omit = Owner; app uses Merge)
  shortHost         — host in uri / jdbc-uri (default: sphere-rw.storage.svc.cluster.local)
  fqdnHost          — host in fqdn-* keys (default: sphere-rw.storage.svc.cluster.local)
  fqdnUriDialect    — postgresql | psycopg2 | ado.net (default: postgresql)
  includeIdentity   — emit port/host/user/username (default true; app omits)
*/}}

{{- define "sphere.rolePassword" -}}
{{- $role := required "sphere.rolePassword: role is required" .role -}}
{{- $db := default $role .database -}}
{{- $shortHost := default "sphere-rw.storage.svc.cluster.local" .shortHost -}}
{{- $fqdnHost := default "sphere-rw.storage.svc.cluster.local" .fqdnHost -}}
{{- $dialect := default "postgresql" .fqdnUriDialect -}}
{{- if and (ne $dialect "postgresql") (ne $dialect "psycopg2") (ne $dialect "ado.net") -}}
{{- fail (printf "sphere.rolePassword: unknown fqdnUriDialect %q (want postgresql|psycopg2|ado.net)" $dialect) -}}
{{- end -}}
{{- $includeIdentity := true -}}
{{- if hasKey . "includeIdentity" -}}{{- $includeIdentity = .includeIdentity -}}{{- end -}}
{{- $secretName := printf "sphere-%s" $role -}}
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: {{ $role }}-user
  namespace: storage
spec:
  refreshInterval: "24h"
  target:
    name: {{ $secretName }}
{{- if .creationPolicy }}
    # Pre-existing secret not owned by this ExternalSecret; Owner cannot adopt it.
    creationPolicy: {{ .creationPolicy }}
{{- end }}
    template:
      metadata:
        labels:
          cnpg.io/reload: "true"
      data:
        password: "{{ `{{ .password }}` }}"
        pgpass: "sphere-rw:5432:{{ $db }}:{{ $role }}:{{`{{ .password }}`}}"
        jdbc-uri: "jdbc:postgresql://{{ $shortHost }}:5432/{{ $db }}?password={{`{{ .password | urlquery }}`}}&user={{ $role }}"
        uri: "postgresql://{{ $role }}:{{`{{ .password | urlquery }}`}}@{{ $shortHost }}:5432/{{ $db }}"
        fqdn-jdbc-uri: "jdbc:postgresql://{{ $fqdnHost }}:5432/{{ $db }}?password={{`{{ .password | urlquery }}`}}&user={{ $role }}"
{{- if eq $dialect "postgresql" }}
        fqdn-uri: "postgresql://{{ $role }}:{{`{{ .password | urlquery }}`}}@{{ $fqdnHost }}:5432/{{ $db }}"
{{- else if eq $dialect "psycopg2" }}
        fqdn-uri: "postgresql+psycopg2://{{ $role }}:{{`{{ .password | urlquery }}`}}@{{ $fqdnHost }}:5432/{{ $db }}"
{{- else }}
        fqdn-uri: "Host={{ $fqdnHost }};Database={{ $db }};Username={{ $role }};Password={{ `{{ .password }}` }};Include Error Detail=true;Timeout=30;CommandTimeout=3600;"
{{- end }}
{{- if $includeIdentity }}
        port: "5432"
        host: "sphere-rw"
        user: {{ $role | quote }}
        username: {{ $role | quote }}
{{- end }}
  dataFrom:
    - sourceRef:
        generatorRef:
          apiVersion: generators.external-secrets.io/v1alpha1
          kind: ClusterGenerator
          name: "cnpg-passgen"
---
apiVersion: external-secrets.io/v1alpha1
kind: PushSecret
metadata:
  name: {{ $role }}-user-pushsecret
  namespace: storage
spec:
  deletionPolicy: Delete
  refreshInterval: 10s
  secretStoreRefs:
    - name: vault
      kind: ClusterSecretStore
  selector:
    secret:
      name: {{ $secretName }}
  data:
    - match:
        remoteRef:
          remoteKey: storage/{{ $secretName }}
{{- end -}}
