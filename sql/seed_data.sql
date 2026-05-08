-- seed_data.sql
INSERT INTO roles (role_name) VALUES ('customer'), ('teller'), ('admin'), ('fraud_analyst');

-- Create a sample admin user (password: 'admin123' hashed)
-- Note: In a real app, use the Flask app to create users with bcrypt.
-- This is just for initial structure.
INSERT INTO users (username, email, password_hash, role_id) 
VALUES ('admin', 'admin@banksim.com', 'admin123', 3);

UPDATE users 
SET password_hash = 'admin123', is_active = TRUE 
WHERE username = 'admin';





-- 1. Create User
INSERT INTO users (username, email, password_hash, role_id) 
VALUES ('hassan', 'hassan@example.com', 'customer123', 1) RETURNING user_id;

-- 2. Create Customer (Use the ID from the previous step, e.g., 2)
INSERT INTO customers (user_id, first_name, last_name, city, country)
VALUES (2, 'Hassan', 'Sarfraz', 'Lahore', 'Pakistan');

-- 3. Create Account
INSERT INTO accounts (account_number, customer_id, account_type, balance)
VALUES ('PK99-BANK-0001', 1, 'savings', 5000.00);




-- 1. Create User "Affan"
INSERT INTO users (username, email, password_hash, role_id) 
VALUES ('affan', 'affan@example.com', 'affan123', 1);

-- 2. Create Customer Profile for Affan
INSERT INTO customers (user_id, first_name, last_name, city, country)
VALUES ( (SELECT user_id FROM users WHERE username='affan'), 'Affan', 'Zarrar', 'Islamabad', 'Pakistan');

-- 3. Create a Checking Account for Affan with $5,000
INSERT INTO accounts (account_number, customer_id, account_type, balance)
VALUES ('PK-BANK-0002', 
        (SELECT customer_id FROM customers WHERE user_id=(SELECT user_id FROM users WHERE username='affan')), 
        'checking', 5000.00);

