# Development image: runs the Vite dev server. A production build (static files) comes in Phase 9.
FROM node:24-slim

WORKDIR /app

# Install dependencies first so Docker can cache this layer between code edits
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev"]
