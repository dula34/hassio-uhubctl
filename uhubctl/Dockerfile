ARG BUILD_FROM=ghcr.io/hassio-addons/base:20.1.1

FROM ${BUILD_FROM}

# Install build dependencies and compile uhubctl
RUN \
    set -e \
    && apk add --no-cache --virtual .build-dependencies \
        build-base \
        linux-headers \
        libusb-dev \
        git && \
    git clone https://github.com/mvp/uhubctl.git /tmp/uhubctl && \
    cd /tmp/uhubctl && \
    make && \
    make install && \
    apk del .build-dependencies && \
    rm -rf /tmp/uhubctl

# Copy application files
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Set execution permissions
RUN chmod a+x run.sh

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "python3 main.py" > /dev/null || exit 1

CMD ["/app/run.sh"]
