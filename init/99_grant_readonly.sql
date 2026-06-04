-- ============================================================
-- 99_grant_readonly.sql — Permisos SELECT al usuario readonly
-- ============================================================
-- Corre al final (orden alfabético), cuando todas las tablas ya existen.

GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly;
