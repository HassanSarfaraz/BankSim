-- views.sql

-- Active customer accounts overview
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
    u.profile_image
FROM users u
JOIN customers c ON u.user_id = c.user_id
JOIN accounts a ON c.customer_id = a.customer_id
WHERE a.status = 'active';

-- Overdue loans
CREATE VIEW overdue_loans_view AS
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
