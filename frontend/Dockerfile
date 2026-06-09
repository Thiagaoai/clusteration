FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
COPY frontend/index.html /usr/share/nginx/html/index.html
COPY frontend/css /usr/share/nginx/html/css
COPY frontend/js /usr/share/nginx/html/js
COPY frontend/img /usr/share/nginx/html/img

EXPOSE 80
