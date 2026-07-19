# =============================================================================
# Dockerfile do frontend — multi-stage (§4.1). Build com Node; imagem final so
# com Nginx alpine servindo estaticos (runtime ~poucos MB, cabe nos 100 MB §1.1).
# =============================================================================

# ---- Estagio 1: build da SPA ----
FROM node:20-alpine AS builder
WORKDIR /build

# Cache de dependencias: copia manifests primeiro. `npm ci` = build deterministico
# a partir do package-lock.json versionado (mais rapido e reprodutivel).
COPY package.json package-lock.json ./
RUN npm ci

# Codigo + build de producao (estaticos em /build/dist).
COPY . .
RUN npm run build

# ---- Estagio 2: runtime (Nginx estatico) ----
FROM nginx:1.27-alpine AS runtime

# Config propria (SPA fallback + proxy /api). Remove a default.
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/nginx.conf /etc/nginx/conf.d/app.conf
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
