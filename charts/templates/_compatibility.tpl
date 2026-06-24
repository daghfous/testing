{{/*
ATEME - User Management Chart
Security Context Compatibility Helper

This template provides OpenShift compatibility by adapting securityContext
to work with the restricted-v2 SecurityContextConstraint (SCC).

OpenShift dynamically assigns user IDs, so we remove hardcoded user/group
values when deploying to OpenShift environments.
*/}}

{{/* vim: set filetype=mustache: */}}

{{/* 
Detect if the platform is OpenShift by checking for the security API.
Usage:
{{- include "common.compatibility.isOpenshift" . -}}
*/}}
{{- define "common.compatibility.isOpenshift" -}}
{{- if .Capabilities.APIVersions.Has "security.openshift.io/v1" -}}
{{- true -}}
{{- end -}}
{{- end -}}

{{/*
Render a securityContext compatible with OpenShift's restricted-v2 SCC.

In OpenShift mode, this removes fields that conflict with dynamic UID/GID assignment:
  - fsGroup
  - runAsUser
  - runAsGroup
  - seLinuxOptions (if empty)

Usage:
{{- include "common.compatibility.renderSecurityContext" (dict "secContext" .Values.containerSecurityContext "context" $) -}}

Parameters:
  - secContext: The securityContext object from values
  - context: The template context ($)
*/}}
{{- define "common.compatibility.renderSecurityContext" -}}
{{- $adaptedContext := .secContext -}}

{{- if (((.context.Values.global).compatibility).openshift) -}}
  {{- if or (eq .context.Values.global.compatibility.openshift.adaptSecurityContext "force") (and (eq .context.Values.global.compatibility.openshift.adaptSecurityContext "auto") (include "common.compatibility.isOpenshift" .context)) -}}
    {{/* Remove fields incompatible with OpenShift restricted-v2 SCC */}}
    {{- $adaptedContext = omit $adaptedContext "fsGroup" "runAsUser" "runAsGroup" -}}
    {{- if not .secContext.seLinuxOptions -}}
      {{/* Remove empty seLinuxOptions to avoid validation errors */}}
      {{- $adaptedContext = omit $adaptedContext "seLinuxOptions" -}}
    {{- end -}}
  {{- end -}}
{{- end -}}

{{/* Clean up empty seLinuxOptions if global setting is enabled */}}
{{- if and (((.context.Values.global).compatibility).omitEmptySeLinuxOptions) (not .secContext.seLinuxOptions) -}}
  {{- $adaptedContext = omit $adaptedContext "seLinuxOptions" -}}
{{- end -}}

{{/* Remove capabilities when running in privileged mode (they're ignored anyway) */}}
{{- if $adaptedContext.privileged -}}
  {{- $adaptedContext = omit $adaptedContext "capabilities" -}}
{{- end -}}

{{/* Remove the 'enabled' flag used for conditional rendering */}}
{{- omit $adaptedContext "enabled" | toYaml -}}
{{- end -}}