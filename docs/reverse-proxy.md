# Reverse Proxy Examples

Below are minimal examples for running Kaajd behind HTTPS with a reverse proxy.

## Caddy

```caddyfile
kaajd.example.com {
    reverse_proxy 127.0.0.1:5000
}
```

With Docker Compose, expose Kaajd on localhost and let Caddy handle TLS.

## nginx

```nginx
server {
    listen 80;
    server_name kaajd.example.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Add TLS by using Certbot (`listen 443 ssl`) or by using a managed ingress/controller.
