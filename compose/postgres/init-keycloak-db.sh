#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'keycloak') THEN
      CREATE USER keycloak WITH PASSWORD '${KC_DB_USER_PASSWORD}';
    END IF;
  END \$\$;

  ALTER USER keycloak WITH PASSWORD '${KC_DB_USER_PASSWORD}';

  SELECT 'CREATE DATABASE keycloak_db OWNER keycloak'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak_db')\gexec

  GRANT ALL PRIVILEGES ON DATABASE keycloak_db TO keycloak;
EOSQL
