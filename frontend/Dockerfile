# ----------------------------------------------------------------------------------------------
#     Build image
#       - intermediary image
#       - WORKDIR inherits from the node-compiler: /build
# ----------------------------------------------------------------------------------------------
ARG NGINX_BASE_IMAGE
ARG NODE_COMPILER_IMAGE
# Stage 1: SSH Key Fetcher
FROM nexus-rennes.ateme.net:10443/common/ssh-key-fetcher AS key

# Stage 2: Build Application
FROM $NODE_COMPILER_IMAGE AS builder

# Copy SSH keys from the key stage
COPY --from=key /root/.ssh/* /root/.ssh/

# Environment Variables
ENV BACKEND_HOST=localhost

# WORKDIR creates the directory if not exists: https://docs.docker.com/engine/reference/builder/#workdir
WORKDIR /workspace/app

# Copy sources
# No need to remove node_modules and package-lock.json, it's ignored thanks to .dockerignore file
COPY ./ /workspace/

# Install dependencies and build the application
# Prune after the `npm run build` to insure having the mandatory build packages
RUN cd /workspace/login-service\
  && npm install --no-audit\
  && cd /workspace/app\
  && npm install --no-audit\
  && npm run build\
  && npm prune --production\
  && cd /workspace/user-profile\
  && npm install --no-audit\
  && npm run build\
  && npm prune --production
# ----------------------------------------------------------------------------------------------
#     Release image
#       - contains only the production-mandatory node modules, no dev dependencies
#       - does NOT contains the SSH key (or may lead to security issues)
#       - runs with a DEFAULT nginx user to avoid unecessary root rights
# ----------------------------------------------------------------------------------------------
# Stage 3: Release Image
FROM $NGINX_BASE_IMAGE
LABEL maintainer="PILOT"

# Copy nginx configuration
COPY default.conf /ateme/nginx/conf.d/default.conf
COPY entrypoint.sh /home/entrypoint.sh
# Copy json-stringify.py script into /usr/local/bin
COPY json-stringify.py /usr/local/bin/json-stringify.py

# Copy builded application files
COPY --from=builder /workspace/app/dist /ateme/nginx/html/
COPY --from=builder /workspace/user-profile/dist /ateme/nginx/html/user-profile

RUN mkdir /ateme/nginx/html-copy
# Copy html configuration
RUN cp -r /ateme/nginx/html/* /ateme/nginx/html-copy/
# Create temp directories needed by nginx
RUN mkdir /tmp/client_body_temp /tmp/proxy_temp /tmp/fastcgi_temp /tmp/uwsgi_temp /tmp/scgi_temp

# Create symlinks to redirect nginx logs to stdout and stderr docker log collector
# https://kubernetes.io/docs/concepts/cluster-administration/logging/#log-rotation
RUN  ln -sf /dev/stdout /var/log/nginx/access.log \
  && ln -sf /dev/stderr /var/log/nginx/error.log

# Own (as user 2000) all directories under /ateme and /tmp
RUN chown -R 2000:2000 /ateme /tmp

# Expose port 81
EXPOSE 81

# entrypoint manage BASE_URL variable
ENTRYPOINT ["/home/entrypoint.sh"]

# Start nginx server
CMD ["nginx", "-g", "daemon off;"]
