{{/*
Expand the name of the chart.
*/}}
{{- define "comfyui-3d-pack.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "comfyui-3d-pack.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "comfyui-3d-pack.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "comfyui-3d-pack.labels" -}}
helm.sh/chart: {{ include "comfyui-3d-pack.chart" . }}
{{ include "comfyui-3d-pack.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "comfyui-3d-pack.selectorLabels" -}}
app.kubernetes.io/name: {{ include "comfyui-3d-pack.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "comfyui-3d-pack.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "comfyui-3d-pack.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return the proper ComfyUI-3D-Pack image name
*/}}
{{- define "comfyui-3d-pack.image" -}}
{{- $registryName := .Values.image.registry -}}
{{- $repositoryName := .Values.image.repository -}}
{{- $tag := .Values.image.tag | toString -}}
{{- if .Values.global.imageRegistry }}
    {{- printf "%s/%s:%s" .Values.global.imageRegistry $repositoryName $tag -}}
{{- else -}}
    {{- printf "%s/%s:%s" $registryName $repositoryName $tag -}}
{{- end -}}
{{- end -}}

{{/*
Return the proper secret name
*/}}
{{- define "comfyui-3d-pack.secretName" -}}
{{- if .Values.secrets.existingSecret }}
    {{- .Values.secrets.existingSecret }}
{{- else }}
    {{- include "comfyui-3d-pack.fullname" . }}
{{- end }}
{{- end }}

{{/*
Return the models PVC name
*/}}
{{- define "comfyui-3d-pack.models.pvcName" -}}
{{- if .Values.persistence.models.existingClaim }}
    {{- .Values.persistence.models.existingClaim }}
{{- else }}
    {{- printf "%s-models" (include "comfyui-3d-pack.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Return the output PVC name
*/}}
{{- define "comfyui-3d-pack.output.pvcName" -}}
{{- if .Values.persistence.output.existingClaim }}
    {{- .Values.persistence.output.existingClaim }}
{{- else }}
    {{- printf "%s-output" (include "comfyui-3d-pack.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Return the object storage secret name
*/}}
{{- define "comfyui-3d-pack.objectStorageSecretName" -}}
{{- if .Values.objectStorage.existingSecret }}
    {{- .Values.objectStorage.existingSecret }}
{{- else }}
    {{- printf "%s-object-storage" (include "comfyui-3d-pack.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Return Redis fullname
*/}}
{{- define "comfyui-3d-pack.redis.fullname" -}}
{{- printf "%s-redis" (include "comfyui-3d-pack.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/*
Renders a value that contains template.
Usage:
{{ include "common.tplvalues.render" ( dict "value" .Values.path.to.the.Value "context" $) }}
*/}}
{{- define "common.tplvalues.render" -}}
    {{- if typeIs "string" .value }}
        {{- tpl .value .context }}
    {{- else }}
        {{- tpl (.value | toYaml) .context }}
    {{- end }}
{{- end -}}
