alter table public.skills enable row level security;
alter table public.skill_prerequisites enable row level security;
alter table public.skill_misconceptions enable row level security;
alter table public.misconceptions enable row level security;
alter table public.template_families enable row level security;
alter table public.templates enable row level security;
alter table public.template_misconceptions enable row level security;
alter table public.worksheet_blueprints enable row level security;
alter table public.generated_worksheets enable row level security;
alter table public.generated_questions enable row level security;
alter table public.student_mastery enable row level security;

create policy "public read skills"
on public.skills
for select
using (true);

create policy "public read skill_prerequisites"
on public.skill_prerequisites
for select
using (true);

create policy "public read skill_misconceptions"
on public.skill_misconceptions
for select
using (true);

create policy "public read misconceptions"
on public.misconceptions
for select
using (true);

create policy "public read template_families"
on public.template_families
for select
using (true);

create policy "public read templates"
on public.templates
for select
using (true);

create policy "public read template_misconceptions"
on public.template_misconceptions
for select
using (true);

create policy "public read worksheet_blueprints"
on public.worksheet_blueprints
for select
using (true);

-- No anon/authenticated policies for generated tables.
-- Server-side access should use the service key, which bypasses RLS.

