-- Tables and RLS policies for user-owned data (projects, user_preferences).
-- Idempotent: safe to run on a database where the tables already exist.
--
-- Storage RLS policies must be applied separately (Supabase Studio or psql)
-- because storage.objects lives in a different schema. See comment block at
-- the bottom of this file for the storage policies.

-- ---------------------------------------------------------------------------
-- projects
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    filename TEXT NOT NULL,
    solid_species TEXT NOT NULL,
    sheet_type TEXT NOT NULL,
    all_solid BOOLEAN NOT NULL DEFAULT false,
    display_units TEXT NOT NULL DEFAULT 'in',
    analysis_result JSONB NOT NULL,
    optimize_result JSONB,
    file_path TEXT NOT NULL,
    thumbnail_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_projects_user_id_created
    ON public.projects (user_id, created_at DESC);

ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS projects_select_own  ON public.projects;
DROP POLICY IF EXISTS projects_insert_own  ON public.projects;
DROP POLICY IF EXISTS projects_update_own  ON public.projects;
DROP POLICY IF EXISTS projects_delete_own  ON public.projects;

CREATE POLICY projects_select_own
    ON public.projects FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY projects_insert_own
    ON public.projects FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY projects_update_own
    ON public.projects FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY projects_delete_own
    ON public.projects FOR DELETE
    USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- user_preferences
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.user_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    enabled_suppliers TEXT[] NOT NULL DEFAULT ARRAY['woodworkers_source']::TEXT[],
    default_species TEXT,
    default_sheet_type TEXT,
    default_units TEXT NOT NULL DEFAULT 'in',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_preferences_select_own ON public.user_preferences;
DROP POLICY IF EXISTS user_preferences_insert_own ON public.user_preferences;
DROP POLICY IF EXISTS user_preferences_update_own ON public.user_preferences;
DROP POLICY IF EXISTS user_preferences_delete_own ON public.user_preferences;

CREATE POLICY user_preferences_select_own
    ON public.user_preferences FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY user_preferences_insert_own
    ON public.user_preferences FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY user_preferences_update_own
    ON public.user_preferences FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY user_preferences_delete_own
    ON public.user_preferences FOR DELETE
    USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- updated_at trigger (shared)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS projects_touch_updated_at ON public.projects;
CREATE TRIGGER projects_touch_updated_at
    BEFORE UPDATE ON public.projects
    FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at();

DROP TRIGGER IF EXISTS user_preferences_touch_updated_at ON public.user_preferences;
CREATE TRIGGER user_preferences_touch_updated_at
    BEFORE UPDATE ON public.user_preferences
    FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at();

-- ---------------------------------------------------------------------------
-- Storage RLS policies — APPLY SEPARATELY in Supabase Studio (SQL Editor),
-- since storage.objects requires storage schema privileges and is not part
-- of the "public" migration surface.
--
-- Layout convention: every object key begins with "{user_id}/{project_id}/...".
-- These policies key off the first path segment.
--
--   -- Allow each authenticated user to read/write objects under their own
--   -- user_id prefix in the 'projects' bucket.
--   CREATE POLICY projects_storage_select_own
--     ON storage.objects FOR SELECT TO authenticated
--     USING (bucket_id = 'projects'
--            AND (storage.foldername(name))[1] = auth.uid()::text);
--
--   CREATE POLICY projects_storage_insert_own
--     ON storage.objects FOR INSERT TO authenticated
--     WITH CHECK (bucket_id = 'projects'
--                 AND (storage.foldername(name))[1] = auth.uid()::text);
--
--   CREATE POLICY projects_storage_update_own
--     ON storage.objects FOR UPDATE TO authenticated
--     USING (bucket_id = 'projects'
--            AND (storage.foldername(name))[1] = auth.uid()::text)
--     WITH CHECK (bucket_id = 'projects'
--                 AND (storage.foldername(name))[1] = auth.uid()::text);
--
--   CREATE POLICY projects_storage_delete_own
--     ON storage.objects FOR DELETE TO authenticated
--     USING (bucket_id = 'projects'
--            AND (storage.foldername(name))[1] = auth.uid()::text);
--
-- Confirm the bucket itself is private (not "Public bucket") in Supabase
-- Studio → Storage → projects → Settings.
-- ---------------------------------------------------------------------------
