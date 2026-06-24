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

## Change <base href=/ > for set $USER_MGT_URL
## exemple export USER_MGT_URL=/ams/
if [ "${BASE_URL}" ];
  then
  ## escape '/' USER MANAGEMENT URL
  export USER_MANAGEMENT_URL_TO_REPLACE=$(echo "$USER_MGT_URL" | sed "s/\//\\\\\//g")
  export BASE_URL_TO_REPLACE=$(echo "$BASE_URL" | sed "s/\//\\\\\//g")
  export RELEASE_NAME_TO_REPLACE=$(echo "$RELEASE_NAME" | sed "s/\//\\\\\//g")
  export DEPLOYING_WITH_PMF_TO_REPLACE=$(echo "$DEPLOYING_WITH_PMF" | sed "s/\//\\\\\//g")
  export APP_VERSION_TO_REPLACE=$(echo "$APP_VERSION" | sed "s/\//\\\\\//g")
  export APP_ID_TO_REPLACE=$(echo "$APP_ID" | sed "s/\//\\\\\//g")
  export VITE_TOP_MENU_MANIFEST_PATH_TO_REPLACE=$(echo "$VITE_TOP_MENU_MANIFEST_PATH" | sed "s/\//\\\\\//g")
  export VITE_USER_PROFILE_MANIFEST_PATH_TO_REPLACE=$(echo "$VITE_USER_PROFILE_MANIFEST_PATH" | sed "s/\//\\\\\//g")
  export VITE_ALARMS_BADGE_MANIFEST_PATH_TO_REPLACE=$(echo "$VITE_ALARMS_BADGE_MANIFEST_PATH" | sed "s/\//\\\\\//g")
  export VITE_LOGIN_URL_TO_REPLACE=$(echo "$LOGIN_URL" | sed "s/\//\\\\\//g")
  export LOG_LEVEL_TO_REPLACE=$(echo "$LOG_LEVEL" | sed "s/\//\\\\\//g")
  export VITE_FAILOVER_SERVICE_MANIFEST_PATH_TO_REPLACE=$(echo "$VITE_FAILOVER_SERVICE_MANIFEST_PATH" | sed "s/\//\\\\\//g")

  # Clean json string
  ESCAPED_JSON=$(json-stringify.py)
  export VITE_TOP_MENU_STATIC_CONFIG_TO_REPLACE=$ESCAPED_JSON
  ## replace <base href=/ >
  _echo "Processing /ateme/nginx/html/index.html ..."
  sed -i "s/<base href=\/ >/<base href=${BASE_URL_TO_REPLACE} >/g" /ateme/nginx/html/index.html

  # Replace env vars in JavaScript files
  _echo "Replacing env constants in JS"
  for filename in /ateme/nginx/html/assets/*.js /ateme/nginx/html/user-profile/assets/*.js
  do
    _echo "Processing $filename ..."
    envsubst '
      $BASE_URL_TO_REPLACE
      $RELEASE_NAME_TO_REPLACE
      $USER_MANAGEMENT_URL_TO_REPLACE
      $DEPLOYING_WITH_PMF_TO_REPLACE
      $APP_VERSION_TO_REPLACE
      $APP_ID_TO_REPLACE
      $VITE_TOP_MENU_MANIFEST_PATH_TO_REPLACE
      $VITE_USER_PROFILE_MANIFEST_PATH_TO_REPLACE
      $VITE_TOP_MENU_STATIC_CONFIG_TO_REPLACE
      $VITE_ALARMS_BADGE_MANIFEST_PATH_TO_REPLACE
      $VITE_LOGIN_URL_TO_REPLACE
      $LOG_LEVEL_TO_REPLACE
      $VITE_FAILOVER_SERVICE_MANIFEST_PATH_TO_REPLACE
    ' < "$filename" > /ateme/nginx/html/tmp.js
    mv /ateme/nginx/html/tmp.js $filename
  done
fi

## start nginx server
_echo "Start nginx server"
exec "$@"
