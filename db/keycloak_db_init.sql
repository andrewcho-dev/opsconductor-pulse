-- Create dedicated Keycloak database and user
-- Replace PLACEHOLDER at runtime using KC_DB_USER_PASSWORD from env.

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'keycloak') THEN
    CREATE USER keycloak WITH PASSWORD 'PLACEHOLDER';
  END IF;
END $$;

ALTER USER keycloak WITH PASSWORD 'PLACEHOLDER';

SELECT 'CREATE DATABASE keycloak_db OWNER keycloak'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak_db')\gexec

GRANT ALL PRIVILEGES ON DATABASE keycloak_db TO keycloak;
