-- ============================================================
-- Migración 001 — Tablas iniciales + RLS
-- Proyecto: IAchitecter — Presupuestos de Obra
-- Fecha: 2026-04-16
-- Idempotente: segura de re-ejecutar
-- ============================================================
-- ROLLBACK (ejecutar en orden inverso para deshacer):
--   DROP TABLE IF EXISTS audit_trail CASCADE;
--   DROP TABLE IF EXISTS error_logs CASCADE;
--   DROP TABLE IF EXISTS execution_logs CASCADE;
--   DROP TABLE IF EXISTS projects CASCADE;
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- Tabla: projects
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID        REFERENCES auth.users NOT NULL,
  name        TEXT        NOT NULL,
  description TEXT,
  status      TEXT        NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'archived', 'deleted')),
  metadata    JSONB       DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects (user_id);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS projects_updated_at ON projects;
CREATE TRIGGER projects_updated_at
  BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  CREATE POLICY "projects_owner_all" ON projects
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ------------------------------------------------------------
-- Tabla: execution_logs
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS execution_logs (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID        REFERENCES auth.users,
  project_id    UUID        REFERENCES projects ON DELETE SET NULL,
  function_name TEXT        NOT NULL,
  parameters    JSONB,
  result        JSONB,
  status        TEXT        NOT NULL CHECK (status IN ('success', 'error', 'timeout')),
  error_msg     TEXT,
  duration_ms   INTEGER,
  input_hash    TEXT,
  start_time    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_execution_logs_project_id  ON execution_logs (project_id);
CREATE INDEX IF NOT EXISTS idx_execution_logs_function    ON execution_logs (function_name);
CREATE INDEX IF NOT EXISTS idx_execution_logs_start_time  ON execution_logs (start_time DESC);
CREATE INDEX IF NOT EXISTS idx_execution_logs_status      ON execution_logs (status);

ALTER TABLE execution_logs ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  CREATE POLICY "execution_logs_owner_select" ON execution_logs
    FOR SELECT
    USING (
      user_id = auth.uid()
      OR project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ------------------------------------------------------------
-- Tabla: error_logs
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS error_logs (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_id  UUID        REFERENCES execution_logs ON DELETE SET NULL,
  function_name TEXT        NOT NULL,
  error_type    TEXT        NOT NULL
                  CHECK (error_type IN ('ValidationError','TimeoutError','LogicError','SystemError','DispatchError')),
  error_message TEXT        NOT NULL,
  stack_trace   TEXT,
  context       JSONB       DEFAULT '{}',
  recovered     BOOLEAN     NOT NULL DEFAULT false,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_error_logs_function     ON error_logs (function_name);
CREATE INDEX IF NOT EXISTS idx_error_logs_error_type   ON error_logs (error_type);
CREATE INDEX IF NOT EXISTS idx_error_logs_created_at   ON error_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_execution_id ON error_logs (execution_id);

ALTER TABLE error_logs ENABLE ROW LEVEL SECURITY;
-- Solo service role puede insertar/leer error_logs directamente

-- ------------------------------------------------------------
-- Tabla: audit_trail  (INMUTABLE — sin UPDATE ni DELETE)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_trail (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID        REFERENCES auth.users NOT NULL,
  project_id  UUID        REFERENCES projects ON DELETE SET NULL,
  action      TEXT        NOT NULL
                CHECK (action IN ('upload','generate','adjust','export','delete','view')),
  object_type TEXT,
  object_id   UUID,
  old_value   JSONB,
  new_value   JSONB,
  ip_address  INET,
  user_agent  TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_trail_user_id    ON audit_trail (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_trail_project_id ON audit_trail (project_id);
CREATE INDEX IF NOT EXISTS idx_audit_trail_action     ON audit_trail (action);
CREATE INDEX IF NOT EXISTS idx_audit_trail_created_at ON audit_trail (created_at DESC);

ALTER TABLE audit_trail ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  CREATE POLICY "audit_trail_owner_select" ON audit_trail
    FOR SELECT
    USING (user_id = auth.uid());
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

COMMIT;
