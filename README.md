# 🏦 Cloud-Native Banking Microservices System

A full-stack banking system built using microservices architecture with FastAPI, Docker, MySQL, and Streamlit.

---

## 🚀 Features

- User registration & authentication (JWT-based)
- Deposit & withdrawal operations
- Fund transfer between users
- Transaction history tracking
- Streamlit frontend dashboard

---

## 🏗️ Architecture

- **User Service** → Handles users, authentication, balances  
- **Transaction Service** → Handles deposits, withdrawals, transfers  
- **MySQL** → Database  
- **Frontend** → Streamlit UI  

---

## ⚙️ Tech Stack

- FastAPI  
- MySQL  
- Docker  
- Streamlit  
- Python  

---

## ▶️ How to Run

### 1. Start MySQL container

```bash
docker run -d \
  --name mysql-container \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=bank \
  -p 3306:3306 \
  mysql:5.7
```

2. Run User Service
cd user-service
uvicorn app.main:app --reload

3. Run Transaction Service
cd transaction-service
uvicorn app.main:app --reload --port 8001

4. Run Frontend
cd frontend
streamlit run app.py

📸 Features Demo
Login / Register / Reset Password
Dashboard with balance
Transfer money
Transaction history

🔐 Security
Password hashing using bcrypt
JWT-based authentication

📌 Future Improvements
Kubernetes deployment
API Gateway
Authentication middleware
UI enhancements