# ==============================================================================
# SatQuery AI — Frontend Dockerfile
# Multi-stage container for Vite / React application
# ==============================================================================

# Stage 1: Base dependencies
FROM node:20-alpine AS base
WORKDIR /app

# Copy dependency manifests
COPY package.json package-lock.json ./
RUN npm install

# Stage 2: Development (default for docker-compose with hot-reload)
FROM base AS dev
WORKDIR /app
COPY . .
EXPOSE 5173
ENV VITE_BACKEND_URL=http://localhost:8000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# Stage 3: Build production assets
FROM base AS build
WORKDIR /app
COPY . .
ARG VITE_BACKEND_URL=""
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
RUN npm run build

# Stage 4: Production runner with Nginx
FROM nginx:alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
