-- CS232 - Database Management System
-- Project: SecureBank Management System
-- Indexes for Optimization

-- Indexes on foreign keys for faster joins
CREATE INDEX idx_customers_user_id ON customers(user_id);
CREATE INDEX idx_employees_user_id ON employees(user_id);
CREATE INDEX idx_employees_branch_id ON employees(branch_id);
CREATE INDEX idx_accounts_customer_id ON accounts(customer_id);
CREATE INDEX idx_accounts_branch_id ON accounts(branch_id);
CREATE INDEX idx_transactions_from_account ON transactions(from_account);
CREATE INDEX idx_transactions_to_account ON transactions(to_account);
CREATE INDEX idx_loans_account_id ON loans(account_id);
CREATE INDEX idx_cards_account_id ON cards(account_id);

-- Performance indexes for common queries
CREATE INDEX idx_transactions_created_at ON transactions(created_at DESC);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_customers_cnic ON customers(cnic);
CREATE INDEX idx_cards_number ON cards(card_number);

-- Composite index for transaction searches
CREATE INDEX idx_txn_acc_date ON transactions(from_account, created_at DESC);
CREATE INDEX idx_txn_to_acc_date ON transactions(to_account, created_at DESC);
