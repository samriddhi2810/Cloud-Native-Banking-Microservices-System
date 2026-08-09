# 🏦 LedgerMesh — Cloud-Native Banking Microservices System

A banking system built as independent microservices — separate services for users, transactions, and notifications, each containerized and orchestrated together with Docker Compose (Kubernetes-ready via Minikube).

---

## Architecture

```
┌─────────────┐
│  frontend    │  Streamlit UI (port 8501)
└──────┬───────┘
       │ REST
       ▼
┌─────────────┐      ┌────────────────────┐      ┌──────────────────────┐
│ user-service │◄────►│ transaction-service │─────►│ notification-service │
│ (port 8000)  │ REST │  (port 8001)        │ REST │  (port 8002)          │
└──────┬───────┘      └─────────┬───────────┘      └──────────────────────┘
       │                        │
       └────────────┬───────────┘
                     ▼
              ┌─────────────┐
              │    mysql     │  (port 3306)
              └─────────────┘
```

- **user-service** — registration, login (JWT), password reset, balance storage/updates
- **transaction-service** — deposits, withdrawals, transfers, transaction history; calls user-service for balance checks/updates and notification-service to notify users
- **notification-service** — records per-user notifications triggered by transaction events
- **frontend** — Streamlit dashboard for login/register, deposits/withdrawals, transfers, and transaction history

---

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy, PyMySQL
- **Auth:** JWT (python-jose), bcrypt password hashing (passlib)
- **Database:** MySQL 8.0
- **Frontend:** Streamlit
- **Infra:** Docker, Docker Compose, Kubernetes (Minikube)

---

## How to Run

```bash
docker-compose up --build
```

Then open **http://localhost:8501**.

Docker Compose builds all four services, waits for MySQL to pass a healthcheck before starting the app services, and networks everything using internal service names (`mysql`, `user-service`, `transaction-service`, `notification-service`) rather than `localhost`.

### Optional environment overrides
Set a real `JWT_SECRET_KEY` before running in anything beyond local/demo use:
```bash
export JWT_SECRET_KEY=$(openssl rand -hex 32)
docker-compose up --build
```

---

## Security & Reliability

- **Concurrency-safe balance updates** — `update-balance` takes a row-level lock (`with_for_update()`) so concurrent requests against the same account serialize instead of racing, preventing an account from going negative under load.
- **No credential exposure** — password hashes never leave user-service in an API response; a dedicated serializer strips them before any user object is returned.
- **Single source of truth for auth** — only user-service holds the JWT secret and issues/verifies tokens; other services and the frontend resolve identity by calling `/me` rather than decoding tokens themselves.
- **Credentials never in the URL** — login, registration, and password reset all take JSON request bodies, not query params.
- **Ownership-verified password resets** — resetting a password requires the account's current password, not just a username.
- **Explicit error handling** — expected failures (not found, bad input) return proper 4xx status codes; only genuinely unexpected errors surface as 500s, and downstream network failures return a distinct 502.

### Design note
`transfer()` currently makes two sequential calls to user-service (deduct from sender, then credit receiver). At larger scale this would move to a saga / compensating-transaction pattern, or be collapsed into a single atomic internal endpoint, to guarantee consistency if the second call fails.

---

## Security Notes
- Passwords are hashed with bcrypt, never stored or transmitted in plaintext
- JWTs are short-lived (60 min) and only user-service verifies/issues them
- Password hashes never leave user-service's response boundary

---

## Future Improvements
- Saga pattern / compensating transactions for `transfer()`
- API Gateway in front of the three backend services
- Kubernetes manifests (currently Docker Compose only, though Minikube-deployable)
- Persistent storage for notification-service (currently in-memory)
