-- CS232 - Database Management System
-- Project: SecureBank Management System
-- Views for Reporting

-- 1. Account Summary View
CREATE OR REPLACE VIEW v_account_summary AS
SELECT 
    a.account_id,
    c.full_name AS customer_name,
    c.cnic,
    b.name AS branch_name,
    a.account_type,
    a.balance,
    a.status,
    a.created_at
FROM accounts a
JOIN customers c ON a.customer_id = c.customer_id
JOIN branches b ON a.branch_id = b.branch_id;

-- 2. Transaction History View
CREATE OR REPLACE VIEW v_transaction_history AS
SELECT 
    t.txn_id,
    f.account_id AS from_account_id,
    cf.full_name AS sender_name,
    to_a.account_id AS to_account_id,
    ct.full_name AS receiver_name,
    t.amount,
    t.txn_type,
    t.status,
    t.description,
    t.created_at
FROM transactions t
LEFT JOIN accounts f ON t.from_account = f.account_id
LEFT JOIN customers cf ON f.customer_id = cf.customer_id
LEFT JOIN accounts to_a ON t.to_account = to_a.account_id
LEFT JOIN customers ct ON to_a.customer_id = ct.customer_id;

-- 3. Branch Performance View
CREATE OR REPLACE VIEW v_branch_performance AS
SELECT 
    b.branch_id,
    b.name,
    b.city,
    COUNT(DISTINCT a.account_id) AS total_accounts,
    SUM(a.balance) AS total_deposits,
    COUNT(DISTINCT e.employee_id) AS total_employees
FROM branches b
LEFT JOIN accounts a ON b.branch_id = a.branch_id
LEFT JOIN employees e ON b.branch_id = e.branch_id
GROUP BY b.branch_id, b.name, b.city;

-- 4. Loan Overview View
CREATE OR REPLACE VIEW v_loan_overview AS
SELECT 
    l.loan_id,
    c.full_name AS customer_name,
    l.loan_type,
    l.principal_amount,
    l.interest_rate,
    l.term_months,
    l.remaining_balance,
    l.status,
    l.applied_at
FROM loans l
JOIN accounts a ON l.account_id = a.account_id
JOIN customers c ON a.customer_id = c.customer_id;
