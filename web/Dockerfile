FROM node:22-slim

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 3000

# Dev server for the scaffold. Switch to `npm run build && npm start` for prod.
CMD ["npm", "run", "dev"]
