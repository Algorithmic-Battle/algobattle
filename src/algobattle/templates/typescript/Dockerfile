FROM node:20

WORKDIR /algobattle
COPY package*.json ./
RUN npm ci

COPY tsconfig.json ./
COPY src src/
RUN npm run build

WORKDIR /
CMD [ "npm", "run", "--prefix", "/algobattle", "start" ]
