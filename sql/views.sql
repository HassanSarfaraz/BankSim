-- views.sql

-- Active customer accounts overview
CREATE VIEW active_accounts_view AS
SELECT 
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    a.account_number,
    a.account_type,
    a.balance,
    a.status
FROM customers c
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
CREATE VIEW open_fraud_alerts_view AS
SELECT 
    fa.alert_id,
    fa.alert_type,
    fa.severity,
    fa.created_at,
    a.account_number
FROM fraud_alerts fa
JOIN accounts a ON fa.account_id = a.account_id
WHERE fa.status = 'open'
ORDER BY fa.created_at DESC;
