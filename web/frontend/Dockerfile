# Build context is web/frontend/.
FROM node:26-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install
COPY . .
RUN npm run build

# Unprivileged image runs as uid 101 and listens on 8080 — no root, no chown,
# so it works under cap_drop: ALL + read-only rootfs.
FROM nginxinc/nginx-unprivileged:1.31-alpine
# The official image trails Alpine's security releases (libtiff was behind), so
# patches are applied on top of it, then the unprivileged user is restored.
USER root
RUN apk upgrade --no-cache
USER 101
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
