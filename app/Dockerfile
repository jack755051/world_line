FROM node:22-alpine AS build
WORKDIR /src

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build -- --configuration production

FROM nginx:1.27-alpine AS runtime
COPY --from=build /src/dist/app/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
