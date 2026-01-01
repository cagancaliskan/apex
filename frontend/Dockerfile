# Frontend Dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy source
COPY . .

# Build for production
RUN npm run build

# Expose port
EXPOSE 5173

# Development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
