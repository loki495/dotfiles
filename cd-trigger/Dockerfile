FROM php:8.3-cli-alpine
WORKDIR /app
COPY router.php .
CMD ["php", "-S", "0.0.0.0:8086", "-t", ".", "router.php"]
