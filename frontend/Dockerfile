# Frontend Dockerfile
FROM nginx:alpine

# Disable caching (see nginx.conf) - this app is actively edited/rebuilt,
# and stale browser-cached JS/CSS after a rebuild caused real confusion
# more than once during testing.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the static files
COPY index.html /usr/share/nginx/html/
COPY *.css /usr/share/nginx/html/
COPY *.js /usr/share/nginx/html/

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
