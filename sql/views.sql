-- views.sql

-- Active customer accounts overview (Expanded with KYC, Credit, and Limits)
CREATE OR REPLACE VIEW active_accounts_view AS
SELECT 
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    a.account_number,
    a.account_type,
    a.balance,
    a.status,
    u.is_active,
    u.user_id,
    u.last_login,
    u.profile_image,
    (SELECT attempt_time FROM login_attempts WHERE user_id = u.user_id AND success = TRUE ORDER BY attempt_time DESC OFFSET 1 LIMIT 1) AS previous_login,
    c.kyc_status,
    c.credit_score,
    a.interest_rate,
    a.overdraft_limit,
    a.currency
FROM users u
JOIN customers c ON u.user_id = c.user_id
JOIN accounts a ON c.customer_id = a.customer_id
WHERE a.status = 'active';

-- Recent System Audit Logs
CREATE OR REPLACE VIEW recent_audit_view AS
SELECT 
    l.log_id,
    COALESCE(u.username, 'System') as actor,
    l.action,
    l.table_name,
    l.log_time
FROM audit_log l
LEFT JOIN users u ON l.user_id = u.user_id
ORDER BY l.log_time DESC
LIMIT 20;

-- Overdue loans
CREATE OR REPLACE VIEW overdue_loans_view AS
SELECT 
    l.loan_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    l.loan_type,
    l.outstanding_balance,
    l.maturity_date,
    CURRENT_DATE - l.maturity_date AS days_overdue
FROM loans l
JOIN customers c ON l.customer_id = c.customer_id
WHERE l.maturity_date < CURRENT_DATE AND l.status = 'active';

-- Open fraud alerts
CREATE OR REPLACE VIEW open_fraud_alerts_view AS
SELECT 
    fa.alert_id,
    fa.alert_type,
    fa.severity,
    fa.created_at,
    a.account_number,
    t.description as recipient_info,
    t.amount,
    c.user_id
FROM fraud_alerts fa
JOIN accounts a ON fa.account_id = a.account_id
JOIN customers c ON a.customer_id = c.customer_id
LEFT JOIN transactions t ON fa.transaction_id = t.transaction_id
WHERE fa.status = 'open'
ORDER BY fa.created_at DESC;
