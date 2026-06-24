#!/bin/bash

# Exit on first non null returncode
set -o errexit

# Can't use undefined variables
set -o nounset

# Last returncode
set -o pipefail

cleanup() {
  kind delete cluster
  # Kill mongodb port-forwarding
  kill $(jobs -p)
}

if [ "${SKIP_CLEANUP:-false}" = "false" ]; then
    trap cleanup EXIT
fi

if ! command -v kind --version &> /dev/null; then
  echo "kind is not installed. Use the package manager or visit the official site https://kind.sigs.k8s.io/"
  exit 1
fi

if [ "${SKIP_CLUSTER_CREATION:-false}" = "false" ]; then
  echo "[dev-env] creating Kubernetes cluster with kind"
  kind create cluster --retain --config=kind-cfg.yaml

  kubectl wait --for=condition=ready node kind-control-plane

  echo "Kubernetes cluster:"
  kubectl get nodes -o wide
fi

kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.4/deploy/static/provider/kind/deploy.yaml

kubectl wait --namespace ingress-nginx \
    --for=condition=ready pod \
    --selector=app.kubernetes.io/component=controller \
    --timeout=480s

helm upgrade \
  --install \
  -n mongo \
  --create-namespace \
  mongo \
  mongodb/mongodb \
  --version 10.31.5-13 \
  --set="global.app.configuration.mode=single" \
  --set="global.system.images.mongodb.replicaCount=1" \
  --set="global.system.application.name=mongodb" \
  --set="global.system.application.version=10.31.5-13" \
  --set="global.registry.private=false" \
  --set="global.system.images.mongodb.metrics.enabled=false" \
  --set="global.system.images.mongodb.persistence.enabled=false"

kubectl wait --namespace mongo \
    --for=condition=ready pod \
    --selector=app.kubernetes.io/component=mongodb \
    --timeout=480s

helm upgrade \
  --install \
  --create-namespace \
  -n user \
  user \
  pmf/user-management \
  --version 4.6.0 \
  --set "global.database.remote.url=mongodb://mongo-mongodb-headless.mongo.svc.cluster.local:27017" \
  --set "global.database.incluster=false"

kubectl wait --namespace user \
    --for=condition=ready pod \
    --selector=app.kubernetes.io/component=frontend \
    --selector=app.kubernetes.io/component=backend \
    --selector=app.kubernetes.io/component=auth-loader \
    --timeout=480s

tox -e compile -- -o generate-pms-backup

kubectl port-forward -n mongo svc/mongo-mongodb-headless 27017:27017 &

tox -e tests -- --binary-path=generate-pms-backup --mongodb-url=mongodb://127.0.0.1:27017/?directConnection=true --user-url=http://127.0.0.1:3080/user
