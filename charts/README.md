# user-management

![Helm](https://img.shields.io/badge/Helm-3.0-0F1689.svg?logo=helm&logoColor=ffffff)
![Kubernetes](https://img.shields.io/badge/Kubernetes-1.23-326DE6.svg?logo=kubernetes&logoColor=ffffff)

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [User Management overview](#user-management-overview)
- [Deploying the application](#deploying-the-application)
  - [Prerequisites](#prerequisites)
    - [Installed kubernetes cluster](#installed-kubernetes-cluster)
    - [Helm (v3) installed on your kubernetes cluster](#helm-v3-installed-on-your-kubernetes-cluster)
  - [Deploying the application](#deploying-the-application-1)
    - [Deploy the application](#deploy-the-application)
    - [Check User Management deployment](#check-user-management-deployment)
  - [Removing the application](#removing-the-application)
  - [Upgrading the application](#upgrading-the-application)
  - [Using the frontend](#using-the-frontend)
    - [Important information for Frontend deployment](#important-information-for-frontend-deployment)
- [Values](#values)
- [Useful commands](#useful-commands)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## User Management overview

The objective of the User Management Micro-services is to manage the users of a complete micro-services product.

## Deploying the application

### Prerequisites
Find below the requirements for deploying the application on a Kubernetes cluster.

#### Installed kubernetes cluster
You must have a kubernetes v1.20 cluster installed. If you do not have it yet, follow the provided [Kubernetes Deployment guide by DevOps team](https://myateme.atlassian.net/wiki/spaces/DEVOPS/pages/1446183131/Using+Cloud+Deployer).

#### Helm (v3) installed on your kubernetes cluster
you must have the helm packager installed on your k8s cluster.

### Deploying the application

**Requirements:** Client tools `kubectl` and `helm` should be installed.

There are 2 ways to deploy:
- Get the charts from `hub-release.ateme.net`, copy them to the cluster and launch them with `helm install`
- Clone the repo on your local machine and then specify the kubeconfig to use
- Mongodb instance deploy, you can deploy mongodb chart with the following commands:

```bash
helm repo add mongodb https://hub-release.ateme.net/chartrepo/mongodb
helm install \
  -n mongo \
  --create-namespace \
  mongo \
  mongodb/mongodb \
  --version 16.0.3-1 \
  --set="mongodb.replicaCount=1" \
  --set="mongodb.metrics.enabled=false" \
  --set="mongodb.persistence.enabled=false"
```

Copy the DNS name from NOTES.txt output, by example: `mongo-mongodb-0.mongo-mongodb-headless.mongo.svc.cluster.local:27017`, this will be needed during user-management chart deployment.

#### Deploy the application

To deploy the application, you must run the following command:

```bash
release_name=user-management
namespace=ateme
helm install $release_name --namespace=$namespace --create-namespace . --set="global.database.remote.url=mongodb://mongo-mongodb-0.mongo-mongodb-headless.mongo.svc.cluster.local:27017" --set "global.database.incluster=false"
```

```bash
NAME: user-management-ateme
LAST DEPLOYED: Thu Nov  4 18:04:58 2021
NAMESPACE: user-management-ateme
STATUS: deployed
REVISION: 1
NOTES:
1. Get the URL of the User Management UI by running the following commands:
  export HOST=$(kubectl get ingress user-management-ateme-ingress --namespace user-management-ateme -o jsonpath="{.status.loadBalancer.ingress}" | sed -E 's/.*(hostname|ip):([^],]*).*/\2/')
  echo http://$HOST/user-management-ateme
  echo https://$HOST/user-management-ateme

2. Get the URL of the User Management API by running the following commands:
  export INGRESS_IP=$(kubectl get ingress user-management-ateme-ingress --namespace user-management-ateme -o jsonpath="{.status.loadBalancer.ingress}" | sed -E 's/.*(hostname|ip):([^],]*).*/\2/')
  echo http://$HOST/user-management-ateme/api
  echo https://$HOST/user-management-ateme/api
```

`--create-namespace` option is only to place when namespace hasn't been already declared.
You can customize `release_name`and `namespace` variable. You can add `--wait` in order to wait until all services ready.

#### Check User Management deployment

Check the deployment with the following command:
```bash
kubectl --namespace $namespace get deployments
```

```bash
NAME                                            READY   UP-TO-DATE   AVAILABLE   AGE
user-management-ateme-frontend                1/1     1            1           67s
user-management-ateme-usermanagement          1/1     1            1           67s
```

In order to check all application services are running correctly, run:

```bash
kubectl --namespace $namespace get pods
```

```bash
NAME                                                            READY   STATUS    RESTARTS   AGE
user-management-ateme-frontend-6df67dd88c-fb6nt               1/1     Running   0          2m3s
user-management-ateme-usermanagement-ddc54b9bb-zjswr          1/1     Running   2          2m3s
```

Finally, check that there are services defined for all deployments:

```bash
kubectl --namespace $namespace get svc
```

```bash
NAME                                            TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)             AGE
user-management-ateme-frontend                ClusterIP   10.233.14.244   <none>        2525/TCP            2d18h
user-management-ateme-usermanagement          ClusterIP   10.233.36.133   <none>        2529/TCP            2d18h
```

### Removing the application

To entirely clean up your deployment, run the following command:

```bash
helm delete $project --namespace $namespace
```

```bash
release "user-management-ateme" uninstalled
```

After removal, make sure that there are no remaining deployments/pods:
```bash
kubectl --namespace $namespace get all
```

```bash
No resources found in user-management-ateme namespace.
```

### Upgrading the application

We don't have an upgrade process yet. TODO define a procedure.

### Using the frontend

You can access to frontend behind `http://$HOST/<release-name>`, host being the ingress host.

A detailed documentation on how to use the frontend can be found here :
[//]: # (TO BE DEFINED)

#### Important information for Frontend deployment

If you are planning to deploy different instances of the application (in Standalone mode - outside of PMF), you need to specify an unique identifier for each instance.
To do so, you must add the variable `APP_ID` in the `values.yaml` file under the path `frontend.extraEnvVars`:
```yaml
frontend:
  extraEnvVars:
  - name: APP_ID
    value: "<GENESIS_1_ID>"
```

## Values

### Root

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| clusterDomain | string | `"cluster.local"` | Default Kubernetes cluster domain |

### Global

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| global.app.configuration.mode | string | `"single"` | Define application mode (single or HA) |
| global.database.incluster | bool | `true` | Define if database in cluster mode |
| global.database.port | string | `"27017"` | Define database port to expose |
| global.database.remote.url | string | `nil` | Define remote database url |
| global.registry.address | string | `"nexus-dev.ateme.net:10443"` | Registry address to pull the images from |
| global.registry.folderName | string | `"products/pilot/manager-foundations"` | Folder where are located the images on the registry |
| global.registry.private | bool | `true` | `true` if the registry requires credentials, else `false` |
| global.registry.user.login | string | `"myuser"` | Required when `global.registry.private` is `true`, set the username to use as credentials |
| global.registry.user.password | string | `"mypassword"` | Required when `global.registry.private` is `true`, set the password to use as credentials |
| global.cluster.name | string | `"local"` | Name of the cluster |
| global.system.application.name | string | `"user-management"` | Application name (required by Devops) |
| global.system.application.version | string | `"continuous"` | Application version (required by Devops) |
| global.system.application.deployingWithPfs | bool | `false` | Whether the application is deployed in PMF context |
| global.system.images.pullPolicy | string | `"IfNotPresent"` | Pull policy |
| global.compatibility.openshift | object | `{"adaptSecurityContext":"auto"}` | Enable compatibility mode for security context (for OpenShift compatibility) |

### Ingress

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| ingress.enabled | bool | `true` | Flag to enable the ingress |

### Pre-Upgrade Job

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| preUpgradeJob.automountServiceAccountToken | bool | `true` | Mount a ServiceAccount's credentials |
| preUpgradeJob.image.repository | string | `"base-image-kubectl"` | Repository to fetch the preUpgradeJob image from |
| preUpgradeJob.image.tag | string | `"1.30.7"` | Tag of the preUpgradeJob image to fetch |
| preUpgradeJob.podLabels | object | `{}` | Labels to add to the preUpgradeJob pod |
| preUpgradeJob.resources | object | `{"limits":{"cpu":"100m","memory":"256Mi"},"requests":{"cpu":"50m","memory":"128Mi"}}` | See https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/ |
| preUpgradeJob.nodeSelector | object | `{}` | See https://kubernetes.io/docs/tasks/configure-pod-container/assign-pods-nodes/#create-a-pod-that-gets-scheduled-to-your-chosen-node |
| preUpgradeJob.affinity | object | `{}` | See https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/#affinity-and-anti-affinity |

### Backend

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| backend.enabled | bool | `true` | Flag to enable UM Backend |
| backend.image.repository | string | `"user-management/backend"` | Repository to fetch the backend image from |
| backend.image.tag | string | `"14.13.2"` | Tag of the backend image to fetch |
| backend.logLevel | string | `"INFO"` | Level of the logging |
| backend.maxWorkers | int | `5` | Define how many workers to set for LDAP operations |
| backend.ldapSyncPeriod | int | `86400` | Ldap sync period (in seconds) |
| backend.ldapLogDetailLevel | int | `0` | Ldap log detail level (0: OFF, ..., 255: EXTENDED). Requires logLevel set to DEBUG. LDAP logging configuration See python-ldap documentation: https://www.python-ldap.org/en/latest/reference/ldap.html#ldap.set_option See ldap3 original documentation for reference: https://ldap3.readthedocs.io/en/latest/logging.html |
| backend.ldapNetworkTimeout | int | `10` | Ldap network timeout (in seconds) |
| backend.tokenIpValidation | bool | `false` | Flag to enable/disable the token ip validation |
| backend.scopesPageLimit | int | `200` | Maximum number of scopes returned per page when getting scopes from the API 0 means no limit |
| backend.service.type | string | `"ClusterIP"` | Type of the service (ClusterIP, NodePort) |
| backend.service.ports.http | int | `2529` | Port of the service |
| backend.containerPorts.http | int | `2529` | Port of the container |
| backend.updateStrategy.type | string | `"RollingUpdate"` | Define the strategy to use for updating the deployment (RollingUpdate or Recreate) |
| backend.updateStrategy.rollingUpdate.maxUnavailable | int | `1` | Optional field that specifies the maximum number of Pods that can be unavailable during the update process |
| backend.defaultValuesSecretName | string | `""` | Name of the secret that will contain the default values (users, scopes, etc.) <sup>(1)</sup> |
| backend.ingress.auth.class | string | `"nginx"` | Define the ingress class of the Auth Ingress |
| backend.ingress.auth.extraPaths | list | `[]` | Extra paths to use in the Ingress |
| backend.ingress.auth.hostname | string | `""` | Hostname to use in the Ingress |
| backend.ingress.auth.extraHosts | list | `[]` | Extra hosts to use in the Ingress |
| backend.ingress.auth.tls | list | `[]` | TLS configuration for the Ingress (see https://kubernetes.io/docs/concepts/services-networking/ingress/#tls) |
| backend.ingress.auth.annotations | object | `{"nginx.ingress.kubernetes.io/auth-method":"POST","nginx.ingress.kubernetes.io/auth-response-headers":"X-User, X-IDP-Name","nginx.ingress.kubernetes.io/auth-url":"http://{{ .Release.Name }}-umbackend.{{ .Release.Namespace }}.svc.cluster.local:{{ .Values.backend.service.ports.http }}/token_introspection","nginx.ingress.kubernetes.io/proxy-body-size":"20M","nginx.ingress.kubernetes.io/rewrite-target":"/$1","nginx.ingress.kubernetes.io/ssl-redirect":"false","nginx.ingress.kubernetes.io/use-regex":"true","nginx.org/path-regex":"case_sensitive","nginx.org/rewrite-target":"/$1"}` | Annotations to use in the Ingress |
| backend.ingress.auth.additionalAnnotations | object | `{}` | Additional annotations to use in the Ingress |
| backend.ingress.auth.path | string | `"/{{ .Release.Name }}/users/(?!(?:ping|readiness|token|refresh_token|admin|definition|documentation|public/configuration|authenticate_mode|idp_sso/[a-zA-Z0-9_.-]+|saml/callback/[a-zA-Z0-9_.-]+|idp_metadata/[a-zA-Z0-9_.-]+)(?:/|$))(.*)"` | Path to use in the Ingress |
| backend.ingress.auth.pathType | string | `"ImplementationSpecific"` | Type of the path to use in the Ingress |
| backend.ingress.noauth.class | string | `"nginx"` | Define the ingress class of the NoAuth Ingress |
| backend.ingress.noauth.extraPaths | list | `[]` | Extra paths to use in the Ingress |
| backend.ingress.noauth.hostname | string | `""` | Hostname to use in the Ingress |
| backend.ingress.noauth.extraHosts | list | `[]` | Extra hosts to use in the Ingress |
| backend.ingress.noauth.tls | list | `[]` | TLS configuration for the Ingress (see https://kubernetes.io/docs/concepts/services-networking/ingress/#tls) |
| backend.ingress.noauth.annotations | object | `{"nginx.ingress.kubernetes.io/proxy-body-size":"20M","nginx.ingress.kubernetes.io/rewrite-target":"/$1","nginx.ingress.kubernetes.io/ssl-redirect":"false","nginx.org/path-regex":"case_sensitive","nginx.org/rewrite-target":"/$1"}` | Annotations to use in the Ingress |
| backend.ingress.noauth.additionalAnnotations | object | `{}` | Additional annotations to use in the Ingress |
| backend.ingress.noauth.path | string | `"/{{ .Release.Name }}/users/(ping|readiness|token|refresh_token|admin|definition|documentation|public/configuration|authenticate_mode|idp_sso/[a-zA-Z0-9_.-]+|saml/callback/[a-zA-Z0-9_.-]+|idp_metadata/[a-zA-Z0-9_.-]+)$"` | Path to use in the Ingress |
| backend.ingress.noauth.pathType | string | `"ImplementationSpecific"` | Type of the path to use in the Ingress |
| backend.livenessProbe.enabled | bool | `true` | Enable default livenessProbe |
| backend.livenessProbe.initialDelaySeconds | int | `60` | Initial delay seconds for livenessProbe |
| backend.livenessProbe.periodSeconds | int | `10` | Period seconds for livenessProbe |
| backend.livenessProbe.timeoutSeconds | int | `5` | Timeout seconds for livenessProbe |
| backend.livenessProbe.failureThreshold | int | `10` | Failure threshold for livenessProbe |
| backend.livenessProbe.successThreshold | int | `1` | Success threshold for livenessProbe |
| backend.readinessProbe.enabled | bool | `true` | Enable default readinessProbe |
| backend.readinessProbe.initialDelaySeconds | int | `10` | Initial delay seconds for readinessProbe |
| backend.readinessProbe.periodSeconds | int | `10` | Period seconds for readinessProbe |
| backend.readinessProbe.timeoutSeconds | int | `5` | Timeout seconds for readinessProbe |
| backend.readinessProbe.failureThreshold | int | `3` | Failure threshold for readinessProbe |
| backend.readinessProbe.successThreshold | int | `1` | Success threshold for readinessProbe |
| backend.startupProbe.enabled | bool | `false` | Enable default startupProbe |
| backend.startupProbe.initialDelaySeconds | int | `0` | Initial delay seconds for startupProbe |
| backend.startupProbe.periodSeconds | int | `10` | Period seconds for startupProbe |
| backend.startupProbe.timeoutSeconds | int | `5` | Timeout seconds for startupProbe |
| backend.startupProbe.failureThreshold | int | `6` | Failure threshold for startupProbe |
| backend.startupProbe.successThreshold | int | `1` | Success threshold for startupProbe |
| backend.customLivenessProbe | object | `{}` | Custom livenessProbe that overrides the default one |
| backend.customReadinessProbe | object | `{}` | Custom readinessProbe that overrides the default one |
| backend.customStartupProbe | object | `{}` | Custom startupProbe that overrides the default one |
| backend.podLabels | object | `{}` | Labels to add to the UM backend pod |
| backend.podSecurityContext | object | `{"enabled":true,"fsGroup":3000,"seccompProfile":{"type":"RuntimeDefault"}}` | Pod security context (an `enabled` field is required), see https://kubernetes.io/docs/tasks/configure-pod-container/security-context/ |
| backend.containerSecurityContext | object | `{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]},"enabled":true,"privileged":false,"readOnlyRootFilesystem":true,"runAsGroup":2000,"runAsNonRoot":true,"runAsUser":2000}` | Container security context (an `enabled` field is required), see https://kubernetes.io/docs/tasks/configure-pod-container/security-context/ |
| backend.resources | object | `{"limits":{"cpu":"600m","memory":"256Mi"},"requests":{"cpu":"200m","memory":"128Mi"}}` | See https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/ |
| backend.nodeAffinity | object | `{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchExpressions":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists"}]}]}}` | See https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/#affinity-and-anti-affinity |
| backend.nodeSelector | object | `{}` | See https://kubernetes.io/docs/tasks/configure-pod-container/assign-pods-nodes/#create-a-pod-that-gets-scheduled-to-your-chosen-node |
| backend.tolerations | list | `[]` | See https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/ |
| backend.topologySpreadConstraints | list | `[]` | See https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/ |

### Frontend

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| frontend.enabled | bool | `true` | Flag to enable UM Frontend |
| frontend.envFromConfigMapName | string | `nil` | environment variables from configMap to pass to the container |
| frontend.workerProcesses | int | `2` | Sets the maximum number of worker processes |
| frontend.debugEntrypoint | bool | `false` | Enable xtrace mode to print out each command executed in entrypoint script |
| frontend.image.repository | string | `"user-management/frontend"` | Repository to fetch the frontend image from |
| frontend.image.tag | string | `"14.13.2"` | Tag of the frontend image to fetch |
| frontend.containerPorts.http | int | `2529` | Port of the container |
| frontend.service.type | string | `"ClusterIP"` | Type of the service (ClusterIP, NodePort) |
| frontend.service.ports.http | int | `2525` | Port of the service |
| frontend.updateStrategy.type | string | `"RollingUpdate"` | Define the strategy to use for updating the deployment (RollingUpdate or Recreate) |
| frontend.updateStrategy.rollingUpdate.maxUnavailable | int | `1` | Optional field that specifies the maximum number of Pods that can be unavailable during the update process. |
| frontend.extraEnvVars | list | `[{"name":"BASE_URL","value":"/{{ .Release.Name }}/"}]` | Additional environment variables to pass to the container |
| frontend.ingress.noauth.class | string | `"nginx"` | Define the ingress class of the NoAuth Ingress |
| frontend.ingress.noauth.extraPaths | list | `[]` | Extra paths to use in the Ingress |
| frontend.ingress.noauth.hostname | string | `""` | Hostname to use in the Ingress |
| frontend.ingress.noauth.extraHosts | list | `[]` | Extra hosts to use in the Ingress |
| frontend.ingress.noauth.tls | list | `[]` | TLS configuration for the Ingress (see https://kubernetes.io/docs/concepts/services-networking/ingress/#tls) |
| frontend.ingress.noauth.annotations | object | `{"nginx.ingress.kubernetes.io/proxy-body-size":"20M","nginx.ingress.kubernetes.io/rewrite-target":"/$1","nginx.ingress.kubernetes.io/ssl-redirect":"false","nginx.org/path-regex":"case_sensitive","nginx.org/rewrite-target":"/$1"}` | Annotations to use in the Ingress |
| frontend.ingress.noauth.additionalAnnotations | object | `{}` | Additional annotations to use in the Ingress |
| frontend.ingress.noauth.path | string | `"/{{ .Release.Name }}/?(.*)"` | Path to use in the Ingress |
| frontend.ingress.noauth.pathType | string | `"ImplementationSpecific"` | Type of the path to use in the Ingress |
| frontend.livenessProbe.enabled | bool | `true` | Enable default livenessProbe |
| frontend.livenessProbe.initialDelaySeconds | int | `10` | Initial delay seconds for livenessProbe |
| frontend.livenessProbe.periodSeconds | int | `10` | Period seconds for livenessProbe |
| frontend.livenessProbe.timeoutSeconds | int | `5` | Timeout seconds for livenessProbe |
| frontend.livenessProbe.failureThreshold | int | `10` | Failure threshold for livenessProbe |
| frontend.livenessProbe.successThreshold | int | `1` | Success threshold for livenessProbe |
| frontend.readinessProbe.enabled | bool | `true` | Enable default readinessProbe |
| frontend.readinessProbe.initialDelaySeconds | int | `0` | Initial delay seconds for readinessProbe |
| frontend.readinessProbe.periodSeconds | int | `10` | Period seconds for readinessProbe |
| frontend.readinessProbe.timeoutSeconds | int | `5` | Timeout seconds for readinessProbe |
| frontend.readinessProbe.failureThreshold | int | `10` | Failure threshold for readinessProbe |
| frontend.readinessProbe.successThreshold | int | `1` | Success threshold for readinessProbe |
| frontend.startupProbe.enabled | bool | `false` | Enable default startupProbe |
| frontend.startupProbe.initialDelaySeconds | int | `0` | Initial delay seconds for startupProbe |
| frontend.startupProbe.periodSeconds | int | `10` | Period seconds for startupProbe |
| frontend.startupProbe.timeoutSeconds | int | `5` | Timeout seconds for startupProbe |
| frontend.startupProbe.failureThreshold | int | `6` | Failure threshold for startupProbe |
| frontend.startupProbe.successThreshold | int | `1` | Success threshold for startupProbe |
| frontend.customLivenessProbe | object | `{}` | Custom livenessProbe that overrides the default one |
| frontend.customReadinessProbe | object | `{}` | Custom readinessProbe that overrides the default one |
| frontend.customStartupProbe | object | `{}` | Custom startupProbe that overrides the default one |
| frontend.podLabels | object | `{}` | Labels to add to the UM frontend pod |
| frontend.podSecurityContext | object | `{"enabled":true,"fsGroup":3000,"seccompProfile":{"type":"RuntimeDefault"}}` | Pod security context (an `enabled` field is required), see https://kubernetes.io/docs/tasks/configure-pod-container/security-context/ |
| frontend.containerSecurityContext | object | `{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]},"enabled":true,"privileged":false,"readOnlyRootFilesystem":true,"runAsGroup":2000,"runAsNonRoot":true,"runAsUser":2000}` | Container security context (an `enabled` field is required), see https://kubernetes.io/docs/tasks/configure-pod-container/security-context/ |
| frontend.resources | object | `{"limits":{"cpu":"50m","memory":"256Mi"},"requests":{"cpu":"50m","memory":"128Mi"}}` | See https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/ |
| frontend.nodeAffinity | object | `{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchExpressions":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists"}]}]}}` | See https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/#affinity-and-anti-affinity |
| frontend.nodeSelector | object | `{}` | See https://kubernetes.io/docs/tasks/configure-pod-container/assign-pods-nodes/#create-a-pod-that-gets-scheduled-to-your-chosen-node |
| frontend.tolerations | list | `[]` | See https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/ |
| frontend.topologySpreadConstraints | list | `[]` | See https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/ |

### Auth-Controller

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| authcontroller.enabled | bool | `true` | Flag to enable UM AuthController. |
| authcontroller.modeF5.enabled | bool | `false` | Flag to enable F5 mode in auth-controller, which allows to adapt to F5 upstream name (X-API-URL case) |
| authcontroller.serviceAccount.create | bool | `true` | Controls whether a ServiceAccount should be created |
| authcontroller.serviceAccount.name | string | `""` | ServiceAccount name (if empty, uses a default name) |
| authcontroller.serviceAccount.annotations | object | `{}` | Annotations to add to the ServiceAccount |
| authcontroller.serviceAccount.automount | bool | `true` | Controls whether credentials are automatically mounted |
| authcontroller.clusterScoped | bool | `true` | Whether the auth-controller should watch all annotated namespaces or only the one where it is deployed |
| authcontroller.role.create | bool | `false` | Flag to enable the creation of a Role/RoleBinding for the auth-controller. |
| authcontroller.role.name | string | `""` | Role name (if empty, uses a default name) |
| authcontroller.role.basicRules | list | `[{"apiGroups":[""],"resources":["configmaps"],"verbs":["get","watch","list","patch"]},{"apiGroups":[""],"resources":["services"],"verbs":["get"]},{"apiGroups":[""],"resources":["events"],"verbs":["create","patch"]},{"apiGroups":["networking.k8s.io"],"resources":["ingresses"],"verbs":["get","watch","list","patch"]}]` | Basic Role rules |
| authcontroller.role.additionalRules | list | `[]` | Additional rules |
| authcontroller.clusterRole.create | bool | `true` | Flag to enable the creation of a ClusterRole/ClusterRoleBinding for the auth-controller. |
| authcontroller.clusterRole.name | string | `""` | ClusterRole name (if empty, uses a default name) |
| authcontroller.clusterRole.basicRules | list | `[{"apiGroups":[""],"resources":["configmaps"],"verbs":["get","watch","list","patch"]},{"apiGroups":[""],"resources":["services"],"verbs":["get"]},{"apiGroups":[""],"resources":["events"],"verbs":["create","patch"]},{"apiGroups":["networking.k8s.io"],"resources":["ingresses"],"verbs":["get","watch","list","patch"]},{"apiGroups":[""],"resources":["namespaces"],"verbs":["get","list","watch"]}]` | Basic ClusterRole rules |
| authcontroller.clusterRole.additionalRules | list | `[]` | Additional rules |
| authcontroller.image.repository | string | `"user-management/auth-controller"` | Repository to fetch the auth-controller image from |
| authcontroller.image.tag | string | `"14.13.2"` | Tag of the auth-controller image to fetch |
| authcontroller.logLevel | string | `"INFO"` | Level of the logging |
| authcontroller.labelSelectorNamespace | string | `""` | Label selector to filter the namespaces to be watched by the auth-controller |
| authcontroller.labelSelectorConfigmap | string | `"ateme.com/user-management=configuration"` | Label selector(s) to filter the config maps to be watched, separated by commas if several |
| authcontroller.labelSelectorIngress | string | `"ateme.com/user-management=configuration"` | Label selector(s) to filter the ingresses to be watched, separated by commas if several |
| authcontroller.controllerIngressClass | string | `""` | Controller Ingress Class Value |
| authcontroller.rateLimiterMaxDelay | string | `"30s"` | Maximum delay for the ingress reconciler exponential backoff rate limiter (in duration format, e.g., 30s, 1m) |
| authcontroller.additionalArgs | list | `[]` | Additional arguments to be passed to the auth-controller |
| authcontroller.postAuthDataTimeout | int | `240` | Maximum delay (in seconds) before aborting tries to post authData |
| authcontroller.podSecurityContext | object | `{"enabled":true,"fsGroup":3000,"seccompProfile":{"type":"RuntimeDefault"}}` | Pod security context (an `enabled` field is required), see https://kubernetes.io/docs/tasks/configure-pod-container/security-context/ |
| authcontroller.containerSecurityContext | object | `{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]},"enabled":true,"privileged":false,"readOnlyRootFilesystem":true,"runAsGroup":2000,"runAsNonRoot":true,"runAsUser":2000}` | Container security context (an `enabled` field is required), see https://kubernetes.io/docs/tasks/configure-pod-container/security-context/ |
| authcontroller.resources | object | `{"limits":{"cpu":"100m","memory":"256Mi"},"requests":{"cpu":"50m","memory":"128Mi"}}` | See https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/ |
| authcontroller.podLabels | object | `{}` | Labels to add to the UM auth-controller pod |
| authcontroller.nodeAffinity | object | `{"requiredDuringSchedulingIgnoredDuringExecution":{"nodeSelectorTerms":[{"matchExpressions":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists"}]}]}}` | See https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/#affinity-and-anti-affinity |
| authcontroller.nodeSelector | object | `{}` | See https://kubernetes.io/docs/tasks/configure-pod-container/assign-pods-nodes/#create-a-pod-that-gets-scheduled-to-your-chosen-node |
| authcontroller.tolerations | list | `[]` | See https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/ |
| authcontroller.topologySpreadConstraints | list | `[]` | See https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/ |
| authcontroller.livenessProbe.enabled | bool | `true` | Enable livenessProbe |
| authcontroller.livenessProbe.tcpSocket.port | int | `9440` | Port of the tcpSocket livenessProbe |
| authcontroller.livenessProbe.initialDelaySeconds | int | `10` | Initial delay seconds for livenessProbe |
| authcontroller.livenessProbe.periodSeconds | int | `10` | Period seconds for livenessProbe |
| authcontroller.livenessProbe.timeoutSeconds | int | `5` | Timeout seconds for livenessProbe |
| authcontroller.livenessProbe.failureThreshold | int | `10` | Failure threshold for livenessProbe |
| authcontroller.livenessProbe.successThreshold | int | `1` | Success threshold for livenessProbe |

### Database

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| database.url | string | `"mongodb+srv://{{ .Release.Name }}-mongodb-headless.{{ .Release.Namespace }}.svc.cluster.local/?ssl=false"` | Database url used by the backend |
| database.certificate.enabled | bool | `false` | Flag to enable database certificate |
| database.certificate.createSecret | bool | `true` | Flag to enable the creation of the certificate secret |
| database.certificate.secretName | string | `"mongo-tls-secret"` | Name of the secret holding certificates |
| database.certificate.data | string | `""` | Database certificate data for connection (mandatory if `certificate.enabled` and `certificate.createSecret`) |
| database.certificate.name | string | `"cert.pem"` | Name of certificate file |

**(1)** Avoid adding default actions and scopes when `auth-loader` is used because they could be conflicting.
If it is still necessary, make sure they have different prefixes.

This secret will be mounted as volume in the User Management Backend.

Actions, scopes, users and admin must be in separated files.

The expected secret data-model is:
```yaml
DEFAULT_ACTIONS: |  # static key for actions filename in the secret
  [
    {
      "name": "get_ping",
      "prefix": "test",
      "description": "Get ping",
      "label": "Get ping",
      "request": {
        "method": "GET",
        "route": "/ping"
      }
    },
    ...
    {
      others actions
    }
  ]
DEFAULT_SCOPES: |   # static key for scopes filename in the secret
  [
    {
        "id": "test:operator",
        "label": "Test",
        "default": True,
        "content": [
          {
            "action": "test:get_ping",
            "policy": "allow",
            "resource": {}
          }
        ],
        "title": "Test operator",
        "description": "Scope operator for testing purpose"
    },
    ...
    {
      others scopes
    }
  ]
DEFAULT_USERS: |  # static key for users filename in the secret
  [
    {
      "username": "A user",
      "password": "its_password",
      "scopes": [
          "test:operator"
      ]
    },
    ...
    {
      others users
    }
  ]
DEFAULT_ADMIN: |  # static key for admin filename in the secret
  {
    "username": "The admin",
    "password": "its_password",
  }
```

## Useful commands
There is a list of commands that may be useful in order to retrieve information from kubernetes services:

- `kubectl --namespace $namespace logs -f <pod_id>`: display the logs of the pod you want to debug. The pod id can be retrieved from `kubect --namespace $namespace get po`.
<br/>*Example*: `kubectl --namespace ateme logs -f user-management-ateme-api-5f546c9946-l58qg`

- `kubectl --namespace $namespace describe {pod, service, deployment} <id>`: displays different kind of information abourt pod/service/deployment you want to check. By example you can check the image used by a pod.
<br/>*Example*: `kubect --namespace ateme describe pod user-management-ateme-api-5f546c9946-l58qg`
