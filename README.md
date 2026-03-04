# RSS Attendance & User Management System

> **Production-ready** Python/FastAPI attendance tracking system with Docker, Nginx, Prometheus, and Grafana.

---

## 🗂️ Project Structure

```
RSS/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + Prometheus instrumentation
│   ├── config.py            # Pydantic settings (env vars)
│   ├── database.py          # SQLAlchemy engine & session
│   ├── models.py            # ORM models: User, Attendance, PasswordResetToken
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── security.py          # bcrypt hashing + JWT utilities
│   ├── dependencies.py      # get_current_user / get_current_admin deps
│   ├── seed.py              # Creates default admin on first boot
│   └── routers/
│       ├── auth.py          # /api/auth/*
│       ├── users.py         # /api/users/*
│       ├── attendance.py    # /api/attendance/*
│       └── admin.py         # /api/admin/*
│   └── static/
│       ├── index.html       # SPA (Home / Dashboard / Admin)
│       ├── style.css        # Dark-mode, animations, responsive
│       └── app.js           # Vanilla JS front-end logic
├── nginx/
│   └── nginx.conf           # Reverse proxy + rate limiting
├── mysql/
│   └── init.sql             # DB initialization
├── monitoring/
│   ├── prometheus.yml       # Prometheus scrape config
│   └── grafana/
│       ├── provisioning/    # Auto-provision datasource + dashboards
│       └── dashboards/      # Pre-built API monitoring dashboard
├── Dockerfile               # Multi-stage Python image
├── docker-compose.yml       # Full stack (5 services)
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Docker Desktop installed and running
- Docker Compose v2+

### 2. Clone & Configure
```bash
git clone <your-repo>
cd RSS
cp .env.example .env
# Edit .env if you want to change secrets
```

### 3. Launch Everything
```bash
docker-compose up -d --build
```

### 4. Access the Services

| Service    | URL                           | Credentials        |
|-----------|-------------------------------|--------------------|
| Web App   | http://localhost              | See below          |
| Swagger   | http://localhost/docs         | —                  |
| Prometheus| http://localhost:9090         | —                  |
| Grafana   | http://localhost:3000         | admin / grafana123 |

### 5. Default Admin Account
```
Email:    admin@rss.com
Password: Admin@123
```

---

## 📡 API Endpoints

### Authentication (`/api/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/register` | Register new user |
| POST | `/login` | Login, returns JWT |
| POST | `/forgot-password` | Request reset token |
| POST | `/reset-password` | Reset with token |

### Users (`/api/users`) – JWT required
| Method | Path | Description |
|--------|------|-------------|
| GET | `/me` | Get own profile |
| PUT | `/me` | Update profile |
| PUT | `/me/change-password` | Change password |

### Attendance (`/api/attendance`) – JWT required
| Method | Path | Description |
|--------|------|-------------|
| POST | `/mark` | Mark today's attendance (once per day) |
| GET | `/today` | Check if already marked today |
| GET | `/history` | Paginated attendance history |

### Admin (`/api/admin`) – Admin JWT required
| Method | Path | Description |
|--------|------|-------------|
| GET | `/stats` | System-wide statistics |
| GET | `/users` | List all users |
| DELETE | `/users/{id}` | Deactivate a user |
| GET | `/attendance` | All attendance (optional date filter) |
| GET | `/attendance/daily-summary` | Daily counts for chart |

### Monitoring
| Path | Description |
|------|-------------|
| `GET /metrics` | Prometheus metrics endpoint |
| `GET /health` | Health check |

---

## 🗄️ Database Schema

### `users` table
| Column | Type | Notes |
|--------|------|-------|
| id | INT PK | Auto-increment |
| name | VARCHAR(100) | Required |
| email | VARCHAR(150) | Unique, indexed |
| phone | VARCHAR(20) | Optional |
| state | VARCHAR(100) | Optional |
| city | VARCHAR(100) | Optional |
| hashed_password | VARCHAR(255) | bcrypt |
| role | ENUM | user / admin |
| is_active | BOOL | Soft delete |
| created_at | DATETIME | Auto |
| updated_at | DATETIME | Auto on update |

### `attendance` table
| Column | Type | Notes |
|--------|------|-------|
| id | INT PK | Auto-increment |
| user_id | INT FK | → users.id |
| date | DATE | Indexed, one per user/day |
| marked_at | DATETIME | Timestamp |
| ip_address | VARCHAR(45) | Client IP |
| notes | TEXT | Optional |

### `password_reset_tokens` table
| Column | Type | Notes |
|--------|------|-------|
| id | INT PK | |
| user_id | INT FK | → users.id |
| token | VARCHAR(255) | Unique, indexed |
| is_used | BOOL | One-time use |
| expires_at | DATETIME | 1-hour TTL |
| created_at | DATETIME | Auto |

---

## 📊 Grafana Dashboards

The pre-provisioned dashboard (`rss_dashboard.json`) displays:
- **Avg API Response Time** (ms)
- **Requests per Second**
- **Active Connections** (in-progress)
- **5xx Error Rate**
- **HTTP Requests by Status Code** (time series)
- **Request Duration Percentiles** (p50, p90, p99)

Access: http://localhost:3000 → Login → Dashboards → Browse → RSS

---

## 🔐 Security Features
- **bcrypt** password hashing (cost factor 12 by default)
- **JWT HS256** tokens with 24-hour expiration
- **Role-based access** (user / admin) enforced on every protected route
- **Rate limiting** in Nginx: 30 req/min for API, 10 req/min for auth endpoints
- **Security headers**: X-Frame-Options, X-Content-Type-Options, XSS-Protection
- **Soft delete** for users (data never removed, just deactivated)
- **One-time reset tokens** with 1-hour expiry

---

## ☁️ AWS Deployment (EC2 + Docker)

### Step-by-Step

1. **Launch EC2 instance**
   - AMI: Amazon Linux 2023 or Ubuntu 22.04
   - Instance type: t3.small (minimum), t3.medium recommended
   - Security group: allow ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
   - Add 20 GB EBS volume

2. **Install Docker on EC2**
   ```bash
   # Amazon Linux 2023
   sudo dnf install docker -y
   sudo systemctl start docker && sudo systemctl enable docker
   sudo usermod -aG docker ec2-user
   
   # Docker Compose plugin
   sudo dnf install docker-compose-plugin -y
   ```

3. **Transfer project & configure**
   ```bash
   # From your local machine
   scp -r ./RSS ec2-user@<EC2-IP>:~/
   ssh ec2-user@<EC2-IP>
   cd RSS
   cp .env.example .env
   nano .env  # Set strong secrets
   ```

4. **Add SSL with Certbot** (recommended)
   ```bash
   sudo dnf install certbot -y
   # Use standalone mode or nginx plugin after pointing your domain
   ```

5. **Launch**
   ```bash
   docker compose up -d --build
   ```

6. **Set up Auto-restart**
   ```bash
   # Docker already uses unless-stopped policy
   # For OS reboot resilience:
   sudo systemctl enable docker
   ```

### AWS Architecture Recommendation

```
Internet → Route 53 → Application Load Balancer (HTTPS) → EC2 (Docker)
                                                         → RDS MySQL (instead of local MySQL)
                                                         → CloudWatch (instead of Prometheus/Grafana)
```

For production scale:
- Replace MySQL container → **Amazon RDS MySQL** (managed, backups, multi-AZ)
- Replace Grafana → **Amazon Managed Grafana** or **CloudWatch Dashboards**
- Add **ECR** to store Docker images
- Use **ECS Fargate** instead of raw EC2 for container orchestration
- Add **Secrets Manager** for credentials instead of `.env` files

---

## 🛠️ Local Development (without Docker)

```bash
pip install -r requirements.txt
# Set environment variables or create .env with MYSQL_HOST=localhost
python -m app.seed        # Seed admin user
uvicorn app.main:app --reload --port 8000
# Visit http://localhost:8000
```
#   r s s  
 