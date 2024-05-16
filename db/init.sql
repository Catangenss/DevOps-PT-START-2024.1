CREATE DATABASE ${DB_DATABASE};

\c ${DB_DATABASE};

CREATE TABLE IF NOT EXISTS tel_numbers (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    tel_number VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS emails (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL
);

INSERT INTO emails (username, email) VALUES ('test', 'test@test.com'), ('Rayan Gosling', 'gosling@gov.ru');
INSERT INTO tel_numbers (username, tel_number) VALUES ('test', '+7 (123) 456 78 90'), ('Rayan Gosling', '+7 (111) 222 33 44');

CREATE USER ${DB_REPL_USER} REPLICATION LOGIN PASSWORD '${DB_REPL_PASSWORD}';