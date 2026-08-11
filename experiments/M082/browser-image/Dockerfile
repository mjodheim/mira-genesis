# Derived from the official Playwright image, which ships the browser binaries and OS
# dependencies but not the npm module. Installing the module at build time lets the experiment
# container run with networking disabled.
FROM mcr.microsoft.com/playwright@sha256:98b1ad488de36b22d41fdd1b0c5b9cceaa78a8d2661c6ab02d2108a07c182338
WORKDIR /agent
RUN npm init -y >/dev/null 2>&1 \
 && npm install playwright@1.49.0 --no-audit --no-fund \
 && npm cache clean --force
ENV NODE_PATH=/agent/node_modules
