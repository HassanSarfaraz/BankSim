-- ===========================================================================
-- SecureBank — Views for Reporting & Analytics
-- ===========================================================================

-- Account summary (Manager / Accountant reporting)
CREATE OR REPLACE VIEW v_account_summary AS
SELECT
    a.account_id,
    c.full_name   AS customer_name,
    c.cnic,
    b.name        AS branch_name,
    a.type        AS account_type,
    a.balance,
    a.status,
    a.daily_limit,
    a.created_at
FROM accounts a
JOIN customers c ON a.customer_id = c.customer_id
JOIN branches  b ON a.branch_id   = b.branch_id;


-- Branch performance (total deposits, account count per branch)
CREATE OR REPLACE VIEW v_branch_performance AS
SELECT
    b.branch_id,
    b.name        AS branch_name,
    b.city,
    COUNT(a.account_id)  AS total_accounts,
    COALESCE(SUM(a.balance), 0) AS total_deposits,
    ROUND(AVG(a.balance), 2)    AS avg_balance
FROM branches b
LEFT JOIN accounts a ON b.branch_id = a.branch_id
GROUP BY b.branch_id, b.name, b.city;


-- Monthly transaction summary
CREATE OR REPLACE VIEW v_monthly_transactions AS
SELECT
    DATE_TRUNC('month', t.timestamp) AS month,
    COUNT(*)                          AS txn_count,
    SUM(t.amount)                     AS total_amount,
    AVG(t.amount)                     AS avg_amount
FROM transactions t
WHERE t.status = 'completed'
GROUP BY DATE_TRUNC('month', t.timestamp)
ORDER BY month DESC;


-- Large / suspicious transactions (amount > 500,000)
CREATE OR REPLACE VIEW v_suspicious_transactions AS
SELECT
    t.txn_id,
    t.amount,
    t.txn_type,
    t.timestamp,
    t.from_account,
    t.to_account,
    c1.full_name AS sender,
    c2.full_name AS receiver
FROM transactions t
LEFT JOIN accounts fa ON t.from_account = fa.account_id
LEFT JOIN accounts ta ON t.to_account   = ta.account_id
LEFT JOIN customers c1 ON fa.customer_id = c1.customer_id
LEFT JOIN customers c2 ON ta.customer_id = c2.customer_id
WHERE t.amount > 500000
ORDER BY t.timestamp DESC;
