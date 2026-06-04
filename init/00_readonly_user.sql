-- ============================================================
-- 00_readonly_user.sql — Usuario de solo lectura para acceso público
-- ============================================================
-- Este script corre ANTES que los de schema, solo crea el usuario.
-- Los permisos sobre las tablas se otorgan en 99_grant_readonly.sql

CREATE USER readonly WITH PASSWORD 'readonly123';
GRANT CONNECT ON DATABASE utn_bd TO readonly;
GRANT USAGE ON SCHEMA public TO readonly;
