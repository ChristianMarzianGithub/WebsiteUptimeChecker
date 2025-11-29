FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* .npmrc* ./
RUN npm install || true
COPY . .
RUN npm run build || true

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY package.json ./
RUN npm install --omit=dev || true
EXPOSE 5173
CMD ["npx", "serve", "dist"]
