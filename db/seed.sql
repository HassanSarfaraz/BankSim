-- CS232 - Database Management System
-- Project: SecureBank Management System
-- Seed Data

-- 1. Branches
INSERT INTO branches (name, city, address, phone) VALUES
('GIKI Branch', 'Topi', 'GIK Institute, Topi, Swabi', '0938-271858'),
('Islamabad Blue Area', 'Islamabad', 'Block A, Blue Area, Islamabad', '051-1234567'),
('Lahore Gulberg', 'Lahore', 'Gulberg III, Lahore', '042-7654321');

-- 2. Users (Passwords are 'Manager@123', 'Acc@123', 'Cust@123' - but stored as plain for now or hashed later)
-- Note: In a real app, these would be bcrypt hashes.
-- For seeding purposes, I will use dummy hashes that the backend would recognize or I'll update them later.
INSERT INTO users (username, password_hash, role) VALUES
('manager1', '$2b$12$KIXpYtP.Xb0D.Gv9Z9l6.O.p.Xb0D.Gv9Z9l6.O.p.Xb0D.Gv', 'manager'),
('accountant1', '$2b$12$KIXpYtP.Xb0D.Gv9Z9l6.O.p.Xb0D.Gv9Z9l6.O.p.Xb0D.Gv', 'accountant'),
('customer1', '$2b$12$KIXpYtP.Xb0D.Gv9Z9l6.O.p.Xb0D.Gv9Z9l6.O.p.Xb0D.Gv', 'customer');

-- 3. Customers
INSERT INTO customers (user_id, cnic, full_name, dob, email, phone, address) VALUES
(3, '12345-6789012-3', 'Muhammad Shahnawaz', '2000-01-01', 'shahnawaz@example.com', '0300-1234567', 'Hostel 4, GIKI');

-- 4. Employees
INSERT INTO employees (user_id, branch_id, role, salary) VALUES
(1, 1, 'Branch Manager', 150000.00),
(2, 1, 'Senior Accountant', 80000.00);

-- 5. Accounts
INSERT INTO accounts (customer_id, branch_id, account_type, balance) VALUES
(1, 1, 'savings', 50000.00),
(1, 1, 'current', 10000.00);

-- 6. Sample Transactions
INSERT INTO transactions (from_account, to_account, amount, txn_type, description) VALUES
(NULL, 1, 50000.00, 'deposit', 'Initial deposit'),
(NULL, 2, 10000.00, 'deposit', 'Opening current account');

-- 7. Sample Loans
INSERT INTO loans (account_id, loan_type, principal_amount, interest_rate, term_months, remaining_balance, status) VALUES
(1, 'Personal Loan', 200000.00, 12.5, 24, 200000.00, 'approved');

-- 8. Sample Cards
INSERT INTO cards (account_id, card_number, card_type, expiry_date, cvv) VALUES
(1, '4242424242424242', 'debit', '2028-12-31', '123');
