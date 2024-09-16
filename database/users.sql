CREATE TABLE users (
    id SERIAL PRIMARY KEY,       -- Unique identifier for each user
    username VARCHAR(50) UNIQUE NOT NULL,  -- Username must be unique
    email VARCHAR(100) UNIQUE NOT NULL,    -- Email must be unique
    password VARCHAR(255) NOT NULL,        -- Password (hashed)
    first_name VARCHAR(50) NOT NULL,       -- User's first name
    last_name VARCHAR(50) NOT NULL,        -- User's last name
    phone_number VARCHAR(15),              -- Optional phone number
    address TEXT,                          -- User's address for shipping
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- When the user registered
    last_login TIMESTAMP                   -- Last login time
);

-- example user info
INSERT INTO users (username, email, password, first_name, last_name, phone_number, address)
VALUES ('john_doe', 'john.doe@example.com', 'pwd', 'John', 'Doe', '1234567890', '123 Main St, Springfield, USA');
