FROM node:20-slim

WORKDIR /app

RUN npm install -g pnpm

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN bash build.sh

EXPOSE 4000
CMD ["node", "release/server.cjs"]
