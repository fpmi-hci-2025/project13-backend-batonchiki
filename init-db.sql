-- PostgreSQL init script - create database only if it doesn't exist
SELECT 'CREATE DATABASE app OWNER app'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'app')\gexec
