import streamlit as st
import requests
from jose import jwt

USER_SERVICE = "http://localhost:8000"
TXN_SERVICE = "http://localhost:8001"

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

def get_user_id_from_token(token):
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return int(decoded["sub"])

# 🎨 CLEAN NAVY + SOFT NEON THEME
st.markdown("""
<style>

/* Background */
.stApp {
    background-color: #0b1120; /* navy */
    color: #e5e7eb;
}

/* Title */
h1 {
    text-align: center;
    color: #22d3ee; /* soft neon blue */
}

/* Inputs */
.stTextInput input, .stNumberInput input {
    background-color: #111827;
    color: white;
    border-radius: 6px;
    border: 1px solid #1f2937;
}

/* Buttons */
.stButton>button {
    background-color: #06b6d4; /* neon blue */
    color: black;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}

.stButton>button:hover {
    background-color: #0891b2;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #020617;
}

</style>
""", unsafe_allow_html=True)

st.title("🏦 Banking App")
st.markdown("---")

# session state
if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "mode" not in st.session_state:
    st.session_state.mode = "login"

# AUTH UI
if st.session_state.access_token is None:

    # Top mode switch buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Login", key="nav_login"):
            st.session_state.mode = "login"

    with col2:
        if st.button("Register", key="nav_register"):
            st.session_state.mode = "register"

    with col3:
        if st.button("Reset", key="nav_reset"):
            st.session_state.mode = "reset"

    st.markdown("###")

    # 🔐 LOGIN
    if st.session_state.mode == "login":
        st.subheader("Login")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", key="login_btn"):
            res = requests.post(
                f"{USER_SERVICE}/login",
                params={"username": username, "password": password}
            )

            data = res.json()

            if "access_token" in data:
                st.session_state.access_token = data["access_token"]
                st.session_state.user_id = get_user_id_from_token(data["access_token"])

                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid credentials")

    # 🆕 REGISTER
    elif st.session_state.mode == "register":
        st.subheader("Register")

        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")

        if st.button("Create Account", key="register_btn"):
            res = requests.post(
                f"{USER_SERVICE}/register",
                params={"username": new_user, "password": new_pass}
            )

            st.success("Account created! Please login.")

            # 🔥 AUTO SWITCH BACK
            st.session_state.mode = "login"
            st.rerun()

    # 🔑 RESET PASSWORD (FIXED UX)
    elif st.session_state.mode == "reset":
        st.subheader("Reset Password")

        reset_user = st.text_input("Username")
        new_pass = st.text_input("New Password", type="password")

        if st.button("Reset Password", key="reset_btn"):
            res = requests.post(
                f"{USER_SERVICE}/reset-password",
                params={"username": reset_user, "new_password": new_pass}
            )

            st.success("Password updated!")

            # 🔥 AUTO GO BACK TO LOGIN
            st.session_state.mode = "login"
            st.rerun()

# DASHBOARD
else:
    st.sidebar.title("⚡ Neon Bank")

    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Transfer", "Transactions"]
    )

    # 🚪 Logout in sidebar
    if st.sidebar.button("Logout", key="logout_btn"):
        st.session_state.user_id = None
        st.session_state.access_token = None
        st.rerun()

    # 🏠 DASHBOARD
    if page == "Dashboard":
        st.subheader("💰 Account Overview")

        users = requests.get(f"{USER_SERVICE}/users").json()
        user = next((u for u in users if u["id"] == st.session_state.user_id), None)

        if user:
            st.metric("Balance", f"₹{user['balance']}")

        st.divider()

        # 💸 Deposit
        st.subheader("Deposit")
        dep_amt = st.number_input("Amount to deposit", min_value=0.0)

        if st.button("Deposit", key="deposit_btn"):
            requests.post(
                f"{TXN_SERVICE}/deposit",
                params={"user_id": st.session_state.user_id, "amount": dep_amt}
            )
            st.success("Deposited!")
            st.rerun()

        # 💸 Withdraw
        st.subheader("Withdraw")
        wd_amt = st.number_input("Amount to withdraw", min_value=0.0, key="withdraw")

        if st.button("Withdraw", key="withdraw_btn"):
            res = requests.post(
                f"{TXN_SERVICE}/withdrawal",
                params={"user_id": st.session_state.user_id, "amount": wd_amt}
            )
            st.success("Withdrawn!")
            st.rerun()

    # 🔁 TRANSFER PAGE
    elif page == "Transfer":
        st.subheader("💸 Transfer Money")

        receiver = st.number_input("Receiver ID", min_value=1)
        amount = st.number_input("Amount", min_value=0.0)

        if st.button("Send", key="transfer_btn"):
            requests.post(
                f"{TXN_SERVICE}/transfer",
                params={
                    "sender_id": st.session_state.user_id,
                    "receiver_id": receiver,
                    "amount": amount
                }
            )
            st.success("Transfer complete")
            st.rerun()

    # 📜 TRANSACTIONS PAGE
    elif page == "Transactions":
        st.subheader("📜 History")

        txns = requests.get(
            f"{TXN_SERVICE}/transactions/{st.session_state.user_id}"
        ).json()

        for txn in txns:
            st.write(f"{txn['type']} | ₹{txn['amount']} | {txn.get('created_at', '')}")