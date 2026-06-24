{{/*
Use registry credentials
*/}}
{{- define "imagePullSecret" }}
{{- printf "{\"auths\": {\"%s\": {\"auth\": \"%s\"}}}" .Values.global.registry.address (printf "%s:%s" .Values.global.registry.user.login .Values.global.registry.user.password | b64enc) | b64enc }}
{{- end }}


{{- define "um.backend.fullname" -}}
{{- if .Values.backend.fullnameOverride -}}
{{- .Values.backend.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default (printf "%s-backend" .Chart.Name) .Values.backend.nameOverride -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "um.authcontroller.fullname" -}}
{{- if .Values.authcontroller.fullnameOverride -}}
{{- .Values.authcontroller.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default (printf "%s-authcontroller" .Chart.Name) "umauthcontroller" -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}


{{/*
Returns the auth-controller ServiceAccount name.

Usage:
  From this chart:
    {{ include "um.authcontroller.serviceAccountName" . | trim }}

  From a parent chart (using user-management as a dependency):
    {{ include "um.authcontroller.serviceAccountName" (dict "context" (dict "Values" .Values.user-management "Release" .Release "Chart" (dict "Name" "user-management"))) | trim }}
*/}}
{{ define "um.authcontroller.serviceAccountName" }}
{{ $ctx := .context | default . }}
{{ if $ctx.Values.authcontroller.serviceAccount.name }}
{{ tpl $ctx.Values.authcontroller.serviceAccount.name $ctx | trunc 63 | trimSuffix "-" }}
{{ else }}
{{ include "um.authcontroller.fullname" $ctx }}
{{ end }}
{{ end }}


{{/*
Returns the auth-controller ClusterRole name.

Usage:
  From this chart:
    {{ include "um.authcontroller.clusterRoleName" . | trim }}

  From a parent chart (using user-management as a dependency):
    {{ include "um.authcontroller.clusterRoleName" (dict "context" (dict "Values" .Values.user-management "Release" .Release "Chart" (dict "Name" "user-management"))) | trim }}
*/}}
{{ define "um.authcontroller.clusterRoleName" }}
{{ $ctx := .context | default . }}
{{ if $ctx.Values.authcontroller.clusterRole.name }}
{{ tpl $ctx.Values.authcontroller.clusterRole.name $ctx | trunc 63 | trimSuffix "-" }}
{{ else }}
{{ include "um.authcontroller.fullname" $ctx }}
{{ end }}
{{ end }}


{{/*
Returns the auth-controller Role name.

Usage:
  From this chart:
    {{ include "um.authcontroller.roleName" . | trim }}

  From a parent chart (using user-management as a dependency):
    {{ include "um.authcontroller.roleName" (dict "context" (dict "Values" .Values.user-management "Release" .Release "Chart" (dict "Name" "user-management"))) | trim }}
*/}}
{{ define "um.authcontroller.roleName" }}
{{ $ctx := .context | default . }}
{{ if $ctx.Values.authcontroller.role.name }}
{{ tpl $ctx.Values.authcontroller.role.name $ctx | trunc 63 | trimSuffix "-" }}
{{ else }}
{{ include "um.authcontroller.fullname" $ctx }}
{{ end }}
{{ end }}


{{- define "um.frontend.fullname" -}}
{{- if .Values.frontend.fullnameOverride -}}
{{- .Values.frontend.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default (printf "%s-frontend" .Chart.Name) .Values.frontend.nameOverride -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}


{{/*
Create a default fully qualified database name.
We compute the sha1 digest to be sure to have 40 characters
Then we add a human readable name and truncate whole to 38 characters or 64 for comptability
*/}}
{{- define "um.backend.databaseName" -}}
{{- if .Values.backend.databaseName -}}
{{- .Values.backend.databaseName -}}
{{- else -}}
{{- $dbsha := sha1sum ((list .Values.global.cluster.name .Release.Namespace .Release.Name) | join "-") -}}
{{- if .Values.global.database.incluster -}}
{{- printf "%s-user-management" $dbsha | trunc 64 | trimSuffix "-" -}}
{{- else -}}
{{- printf "user-management-%s" $dbsha | trunc 38 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create the replicas number.
*/}}
{{- define "um.backend.replicas" -}}
    {{- if eq .Values.global.app.configuration.mode "HA" }}
    {{- printf "%d" 3 -}}
    {{- else }}
    {{- printf "%d" 1 -}}
    {{- end }}
{{- end -}}


{{/*
Create the replicas number.
*/}}
{{- define "um.frontend.replicas" -}}
    {{- if eq .Values.global.app.configuration.mode "HA" }}
    {{- printf "%d" 3 -}}
    {{- else }}
    {{- printf "%d" 1 -}}
    {{- end }}
{{- end -}}

{{/*
Create the name of the registryCredentials secrets to use
*/}}
{{- define "um.secrets.registrycredentials.name" -}}
{{ .Release.Name }}-registrycredentials
{{- end }}


{{/*
Renders a value that contains template.
Usage:
{{ include "tplvalues.render" ( dict "value" .Values.path.to.the.Value "context" $) }}
*/}}
{{- define "tplvalues.render" -}}
    {{- if typeIs "string" .value }}
        {{- tpl .value .context }}
    {{- else }}
        {{- tpl (.value | toYaml) .context }}
    {{- end }}
{{- end -}}
