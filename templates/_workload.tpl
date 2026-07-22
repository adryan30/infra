{{/*
Workload Application shell helpers (ADR-0002) and enablement registry (ADR-0003).

Split helpers: Workload files keep source/valuesObject as YAML; these defines
own finalizers, destination server, syncPolicy profiles, and revisionHistoryLimit.

workload.enabled looks up Values.workloads.<name>.enabled. Required: root, name.
A missing registry key fails the render (fail-closed).
*/}}

{{- define "workload.enabled" -}}
{{- $root := required "workload.enabled: root is required" .root -}}
{{- $name := required "workload.enabled: name is required" .name -}}
{{- if not (hasKey $root.Values.workloads $name) -}}
{{- fail (printf "workload.enabled: Workload %q is not in the enablement registry" $name) -}}
{{- end -}}
{{- $entry := index $root.Values.workloads $name -}}
{{- if not (hasKey $entry "enabled") -}}
{{- fail (printf "workload.enabled: Workload %q is missing required field enabled" $name) -}}
{{- end -}}
{{- ternary "true" "false" $entry.enabled -}}
{{- end -}}

{{- define "workload.finalizers" -}}
- resources-finalizer.argocd.argoproj.io
{{- end -}}

{{- define "workload.destinationServer" -}}
{{- .Values.spec.destination.server | default "https://kubernetes.default.svc" -}}
{{- end -}}

{{- define "workload.revisionHistoryLimit" -}}
3
{{- end -}}

{{/*
workload.syncPolicy

Required: profile = "workload" | "platform"

Optional overrides:
  istioInjection: "enabled" | "disabled" | "omit"
    workload default: enabled; platform default: omit
  createNamespace: bool (default true)
  serverSideApply: bool (workload default true; platform default false)
  respectIgnoreDifferences: bool (workload default true; platform default false)
*/}}
{{- define "workload.syncPolicy" -}}
{{- $profile := required "workload.syncPolicy: profile is required" .profile -}}
{{- if and (ne $profile "workload") (ne $profile "platform") -}}
{{- fail (printf "workload.syncPolicy: unknown profile %q (want workload|platform)" $profile) -}}
{{- end -}}
{{- $createNamespace := true -}}
{{- if hasKey . "createNamespace" -}}{{- $createNamespace = .createNamespace -}}{{- end -}}
{{- $serverSideApply := eq $profile "workload" -}}
{{- if hasKey . "serverSideApply" -}}{{- $serverSideApply = .serverSideApply -}}{{- end -}}
{{- $respectIgnoreDifferences := eq $profile "workload" -}}
{{- if hasKey . "respectIgnoreDifferences" -}}{{- $respectIgnoreDifferences = .respectIgnoreDifferences -}}{{- end -}}
{{- $istioInjection := "omit" -}}
{{- if eq $profile "workload" -}}{{- $istioInjection = "enabled" -}}{{- end -}}
{{- if hasKey . "istioInjection" -}}{{- $istioInjection = .istioInjection -}}{{- end -}}
syncPolicy:
{{- if ne $istioInjection "omit" }}
  managedNamespaceMetadata:
    labels:
      istio-injection: {{ $istioInjection | quote }}
{{- end }}
  automated:
    enabled: true
    prune: true
    selfHeal: true
  syncOptions:
    {{- if $createNamespace }}
    - CreateNamespace=true
    {{- end }}
    {{- if $serverSideApply }}
    - ServerSideApply=true
    {{- end }}
    {{- if $respectIgnoreDifferences }}
    - RespectIgnoreDifferences=true
    {{- end }}
  retry:
    limit: 5
    backoff:
      duration: 5s
      factor: 2
      maxDuration: 3m
{{- end -}}
