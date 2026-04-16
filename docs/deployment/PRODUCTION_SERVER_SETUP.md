# Production Server Setup Guide

This guide covers preparing a single Ubuntu/Debian server for ProcessMiner deployment.

## Prerequisites

- Ubuntu 22.04+ or Debian 12+ (fresh or existing server)
- Root or sudo access
- At least 4 GB RAM (8 GB recommended)
- At least 20 GB free disk space
- Network access to GitHub (for git clone/pull)

---

## 1. System Updates

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git wget unzip jq
```

## 2. Install Docker

```bash
# Install Docker (official method)
curl -fsSL https://get.docker.com | sudo sh

# Add your user to docker group (avoids needing sudo for docker commands)
sudo usermod -aG docker $USER

# Apply group change (or log out and back in)
newgrp docker

# Verify
docker --version
docker compose version
```

> **Note**: Docker Compose V2 is included with modern Docker installations as `docker compose` (no hyphen). The deploy scripts use this format.

## 3. Create Deploy User

It's recommended to create a dedicated deploy user rather than deploying as root.

```bash
# Create user
sudo adduser --disabled-password --gecos "" deploy

# Add to docker group
sudo usermod -aG docker deploy

# Create deploy directory
sudo mkdir -p /opt/mining
sudo chown deploy:deploy /opt/mining
```

## 4. SSH Key Setup

The GitHub Actions workflow connects via SSH. You need to set up key-based authentication.

### On your local machine (or in GitHub Actions):

```bash
# Generate a dedicated deploy key (if you don't have one)
ssh-keygen -t ed25519 -C "deploy@mining" -f ~/.ssh/mining_deploy_key -N ""
```

### On the server:

```bash
# Switch to deploy user
sudo su - deploy

# Set up authorized_keys
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Add the public key (paste the content of mining_deploy_key.pub)
echo "ssh-ed25519 AAAA... deploy@mining" >> ~/.ssh/authorized_keys
```

### Get the known_hosts entry (for DEPLOY_KNOWN_HOSTS secret):

```bash
# Run this from any machine that can reach the server
ssh-keyscan -p 22 YOUR_SERVER_IP
```

Save this output — you'll paste it into the `DEPLOY_KNOWN_HOSTS` GitHub Secret.

## 5. Firewall Configuration

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow application ports (for direct access without reverse proxy)
sudo ufw allow 5173/tcp   # Web UI
sudo ufw allow 3001/tcp   # API
sudo ufw allow 8000/tcp   # Worker (optional, usually internal only)

# Enable firewall
sudo ufw enable
sudo ufw status
```

> **Security Note**: In production with a reverse proxy, you should only expose ports 22, 80, and 443. See [Future: Reverse Proxy](#future-reverse-proxy) below.

## 6. Directory Structure

The deploy scripts expect this structure:

```
/opt/mining/              # DEPLOY_PATH
├── .git/                 # Git repository (created by first deploy)
├── .env                  # Environment file (written by deploy script)
├── .deploy-previous-sha  # Rollback tracking (written by deploy script)
├── apps/
├── services/
├── infra/
│   └── docker-compose.yml
├── scripts/
└── ...
```

The first deploy will clone the repository automatically. No manual git clone is needed.

## 7. Docker Data Directories

Docker volumes are managed by Docker Compose and persist across deployments. The following volumes are defined:

| Volume | Purpose | Survives Redeploy |
|--------|---------|-------------------|
| `postgres_data` | PostgreSQL database | ✅ Yes |
| `data_storage` | Uploaded CSV files | ✅ Yes |
| `data_parquet` | Converted Parquet files | ✅ Yes |
| `data_artifacts` | Analysis artifacts | ✅ Yes |

> **Important**: Deploy scripts NEVER delete Docker volumes. Your data is safe across deployments.

## 8. Resource Limits (Optional)

For production stability, consider setting Docker resource limits:

```bash
# Check available resources
free -h
df -h
docker system info
```

## 9. Log Rotation (Recommended)

Docker container logs can grow large. Set up log rotation:

```bash
# Create Docker daemon config
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
EOF

# Restart Docker
sudo systemctl restart docker
```

---

## Pre-Deploy Checklist

Before running the first deployment, verify:

- [ ] Docker and Docker Compose are installed and working
- [ ] Deploy user exists and is in the `docker` group
- [ ] SSH key authentication works for the deploy user
- [ ] Deploy directory (`/opt/mining`) exists and is owned by the deploy user
- [ ] Firewall allows SSH (port 22) and application ports (5173, 3001, 8000)
- [ ] GitHub Secrets are configured (see [Secrets Guide](./SECRETS_AND_ENV_MANAGEMENT.md))
- [ ] Server has internet access (for git pull and Docker image downloads)

### Test SSH access:

```bash
# From your local machine, test with the deploy key
ssh -i ~/.ssh/mining_deploy_key -p 22 deploy@YOUR_SERVER_IP "echo 'SSH works'"
```

### Test Docker:

```bash
# On the server as deploy user
docker run --rm hello-world
docker compose version
```

---

## First Deploy

Once the server is ready and GitHub Secrets are configured:

1. Go to the repository on GitHub
2. Navigate to **Actions** → **Deploy to Production**
3. Click **Run workflow** → select `main` branch → click **Run workflow**
4. Monitor the workflow in the Actions tab

Or simply push/merge to `main` — the deploy will trigger automatically.

---

## Future: Reverse Proxy

For production use, you should add a reverse proxy. This is not required for the first deployment but is strongly recommended before exposing the application publicly.

### Recommended: Caddy (automatic HTTPS)

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

Example Caddyfile (`/etc/caddy/Caddyfile`):

```
yourdomain.com {
    handle /api/* {
        reverse_proxy localhost:3001
    }
    handle /health {
        reverse_proxy localhost:3001
    }
    handle /worker/* {
        reverse_proxy localhost:8000
    }
    handle {
        reverse_proxy localhost:5173
    }
}
```

### Alternative: Nginx with Let's Encrypt

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

### After adding reverse proxy:

- Update firewall: only allow ports 22, 80, 443
- Block direct access to 3001, 5173, 8000
- Update `CORS_ORIGIN` in `.env` to your domain
- Update `VITE_API_URL` to use your domain

---

## Future: Hardening Checklist

These are recommended improvements for production use beyond the initial deployment:

- [ ] Set up reverse proxy (Nginx or Caddy) with HTTPS
- [ ] Restrict firewall to ports 22, 80, 443 only
- [ ] Configure `fail2ban` for SSH brute-force protection
- [ ] Set up automated OS security updates (`unattended-upgrades`)
- [ ] Configure database backups (pg_dump cron job)
- [ ] Set up monitoring (e.g., Prometheus + Grafana, or a lightweight alternative)
- [ ] Move secrets from GitHub Secrets to server-side management (Vault, etc.)
- [ ] Enable Docker content trust
- [ ] Set up log aggregation
- [ ] Configure swap space if RAM is limited

---

## Troubleshooting

### Docker Compose fails to start

```bash
cd /opt/mining/infra
docker compose --env-file /opt/mining/.env logs
docker compose --env-file /opt/mining/.env ps
```

### Port already in use

```bash
sudo lsof -i :5173
sudo lsof -i :3001
sudo lsof -i :8000
```

### Disk space issues

```bash
df -h
docker system df
# Careful cleanup (does NOT remove volumes)
docker system prune -f
```

### Permission denied

```bash
# Ensure deploy user owns the directory
sudo chown -R deploy:deploy /opt/mining

# Ensure deploy user is in docker group
groups deploy
```
