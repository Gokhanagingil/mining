FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install --ignore-scripts

COPY . .
RUN npm run build

FROM node:20-alpine AS runtime

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev --ignore-scripts

COPY --from=builder /app/dist ./dist

RUN mkdir -p /data/storage /data/parquet /data/artifacts

EXPOSE 3001

CMD ["node", "dist/main"]
