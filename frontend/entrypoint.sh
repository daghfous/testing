#! /bin/sh
# Exit on first non null returncode
set -o errexit

if [ "$ENTRYPOINT_DEBUG" = true ]; then
    set -o xtrace
fi

_echo() {
  echo "$(date '+%d/%m/%Y %H:%M:%S') - $*"
}

# Copy assets to /ateme/nginx/html/ directory in order to mount an empty volume
_echo "Copy assets to /ateme/nginx/html/"
mkdir -p /ateme/nginx/html
cp -r /ateme/nginx/html-copy/* /ateme/nginx/html/

# Create env directory and env.json from environment variables
# This allows the frontend to dynamically load configuration at runtime
# The file is created at /var/www/html/env/env.json to match Kubernetes configmap mount path
if [ "${BASE_URL}" ]; then
  _echo "Creating env.json from environment variables"
  mkdir -p /var/www/html/env
  cat > /var/www/html/env/env.json <<EOF
{
  "BASE_URL": "${BASE_URL}",
  "USER_MANAGEMENT_URL": "${USER_MANAGEMENT_URL:-${USER_MGT_URL}}",
  "RELEASE_NAME": "${RELEASE_NAME}",
  "DEPLOYING_WITH_PMF": ${DEPLOYING_WITH_PMF:-false},
  "APP_VERSION": "${APP_VERSION}",
  "APP_ID": "${APP_ID}",
  "VITE_TOP_MENU_MANIFEST_PATH": "${VITE_TOP_MENU_MANIFEST_PATH}",
  "VITE_USER_PROFILE_MANIFEST_PATH": "${VITE_USER_PROFILE_MANIFEST_PATH}",
  "VITE_ALARMS_BADGE_MANIFEST_PATH": "${VITE_ALARMS_BADGE_MANIFEST_PATH}",
  "VITE_LOGIN_URL": "${VITE_LOGIN_URL:-${LOGIN_URL}}",
  "LOG_LEVEL": "${LOG_LEVEL}",
  "VITE_FAILOVER_SERVICE_MANIFEST_PATH": "${VITE_FAILOVER_SERVICE_MANIFEST_PATH}",
  "VITE_TOP_MENU_STATIC_CONFIG": ${VITE_TOP_MENU_STATIC_CONFIG:-'{}'}
}
EOF
fi

## start nginx server
_echo "Start nginx server"
exec "$@"
