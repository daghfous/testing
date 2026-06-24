# UserManagement backend Dockerfile
# Args:
# * PYTHON_COMPILER_IMAGE: Image use for building wheels
# * PYTHON_DISTROLESS_BASE_IMAGE: Distroless Image use for final image
# * PACKAGE_PRETEND_VERSION: Python package version
ARG PYTHON_COMPILER_IMAGE
ARG PYTHON_DISTROLESS_BASE_IMAGE

FROM $PYTHON_COMPILER_IMAGE AS builder
ARG PACKAGE_PRETEND_VERSION=0.0.0

WORKDIR /opt

# Install build and runtime dependencies
# both dev and runtime packages are needed at build time to build python-ldap
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.9 \
    python3-dev=3.11.2-1+b1 \
    libldap2-dev=2.5.13+dfsg-5 \
    libsasl2-dev=2.1.28+dfsg-10 \
    libssl-dev=3.0.20-1~deb12u2 \
    libxmlsec1-dev=1.2.37-2 \
    pkg-config=1.8.1-1 

# First copy requirements
COPY requirements.txt .

# Create virtualenv and ensure that pip and setuptools are up-to-date.
RUN python -m venv /venv --upgrade-deps

RUN /venv/bin/pip install --no-cache-dir --no-deps -rrequirements.txt

# Next we copy source code
COPY  . .
RUN SETUPTOOLS_SCM_PRETEND_VERSION=${PACKAGE_PRETEND_VERSION} /venv/bin/pip install --no-cache-dir --no-deps .

# Create a new directory called /runtime_libs 
# Define a small shell function get_libs → safely extracts .so paths from any binary or library
# Starts from _ldap*.so as the root, 
# Iteratively (while) collects dependencies of dependencies until no new libs are found
# Deduplicates (sort -u) and copies them all to /runtime_libs/
RUN mkdir -p /runtime_libs && \
    get_libs() { \
    for f in "$@"; do \
    ldd "$f" 2>/dev/null | awk '/=>/ {print $3}' | grep -v '^$'; \
    done; \
    }; \
    libs=$(get_libs /venv/lib/python3.11/site-packages/_ldap*.so); \
    seen=""; \
    while [ -n "$libs" ]; do \
    new_libs=""; \
    for lib in $libs; do \
    case " $seen " in \
    *" $lib "*) continue ;; \
    *) \
    seen="$seen $lib"; \
    new_libs="$new_libs $(get_libs "$lib")"; \
    ;; \
    esac; \
    done; \
    libs=$new_libs; \
    done; \
    echo "$seen" | tr ' ' '\n' | sort -u | grep -v '^$' | xargs -I{} cp -v {} /runtime_libs/

# In the final image, the python binary is expected to be in /venv/bin/python
# Ensure the exexutable is available at this location
RUN ln -fs /usr/bin/python /venv/bin/python

# This removes the directory containing test certificates included by python-ldap
RUN rm -rf /venv/lib/python3.11/site-packages/slapdtest/certs

# Final stage: distroless image
FROM $PYTHON_DISTROLESS_BASE_IMAGE AS final

# Copy virtualenv
COPY --from=builder /venv /venv

# Copy pinned runtime libraries required by python-ldap
COPY --from=builder /runtime_libs/ /usr/lib/x86_64-linux-gnu/

# Set LD_LIBRARY_PATH so python-ldap can find libraries
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/:${LD_LIBRARY_PATH:-}

# Expose default um_backend port
EXPOSE 2529

# Update `PATH` to be able to call venv binaries (python and entrypoints) 
ENV PATH=/venv/bin:$PATH

# Define `ateme.um_backend` python module as entrypoint
ENTRYPOINT ["python", "-m", "ateme.um_backend"]
