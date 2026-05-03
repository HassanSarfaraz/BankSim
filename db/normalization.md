# ===========================================================================
# SecureBank Normalization Documentation
# All tables are proven to be in BCNF (Boyce-Codd Normal Form).
# ===========================================================================

## 1. users
**Attributes:** user_id, username, password_hash, role, is_active, last_login, created_at

**Functional Dependencies:**
- user_id → username, password_hash, role, is_active, last_login, created_at
- username → user_id (candidate key)

**Candidate Keys:** {user_id}, {username}

**BCNF Proof:** Every determinant (user_id, username) is a superkey. ✅ BCNF

---

## 2. branches
**Attributes:** branch_id, name, city, address, phone, created_at

**Functional Dependencies:**
- branch_id → name, city, address, phone, created_at

**Candidate Keys:** {branch_id}

**BCNF Proof:** Only determinant is the primary key. ✅ BCNF

---

## 3. customers
**Attributes:** customer_id, user_id, cnic, full_name, dob, address, phone, email, kyc_status, created_at

**Functional Dependencies:**
- customer_id → user_id, cnic, full_name, dob, address, phone, email, kyc_status, created_at
- user_id → customer_id (1-to-1 mapping)
- cnic → customer_id (unique constraint)

**Candidate Keys:** {customer_id}, {user_id}, {cnic}

**BCNF Proof:** All determinants are superkeys. ✅ BCNF

---

## 4. employees
**Attributes:** employee_id, user_id, branch_id, full_name, designation, is_active, created_at

**Functional Dependencies:**
- employee_id → user_id, branch_id, full_name, designation, is_active, created_at
- user_id → employee_id (1-to-1 mapping)

**Candidate Keys:** {employee_id}, {user_id}

**BCNF Proof:** All determinants are superkeys. ✅ BCNF

---

## 5. accounts
**Attributes:** account_id, customer_id, branch_id, type, balance, status, daily_limit, created_at

**Functional Dependencies:**
- account_id → customer_id, branch_id, type, balance, status, daily_limit, created_at

**Candidate Keys:** {account_id}

**BCNF Proof:** Only determinant is the primary key. ✅ BCNF

---

## 6. transactions
**Attributes:** txn_id, from_account, to_account, amount, txn_type, status, description, performed_by, timestamp

**Functional Dependencies:**
- txn_id → from_account, to_account, amount, txn_type, status, description, performed_by, timestamp

**Candidate Keys:** {txn_id}

**BCNF Proof:** Only determinant is the primary key. ✅ BCNF

---

## 7. loans
**Attributes:** loan_id, account_id, loan_type, amount, interest_rate, term_months, monthly_payment, amount_paid, status, approved_by, approval_date, reason, created_at

**Functional Dependencies:**
- loan_id → all other attributes

**Candidate Keys:** {loan_id}

**BCNF Proof:** Only determinant is the primary key. ✅ BCNF

---

## 8. cards
**Attributes:** card_id, account_id, card_number, card_type, expiry_date, cvv_hash, status, credit_limit, created_at

**Functional Dependencies:**
- card_id → all other attributes
- card_number → card_id (unique constraint)

**Candidate Keys:** {card_id}, {card_number}

**BCNF Proof:** All determinants are superkeys. ✅ BCNF

---

## 9. audit_policies
**Attributes:** policy_id, acc_type, daily_withdrawal_limit, overdraft_allowed, min_balance, interest_rate

**Functional Dependencies:**
- policy_id → all other attributes
- acc_type → policy_id (unique constraint, 1-to-1)

**Candidate Keys:** {policy_id}, {acc_type}

**BCNF Proof:** All determinants are superkeys. ✅ BCNF

---

## Summary
All 9 tables satisfy BCNF because every non-trivial functional dependency has a superkey as its determinant. No decomposition is needed.
