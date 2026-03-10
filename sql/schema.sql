create extension if not exists pgcrypto;

create table if not exists skills (
    skill_id varchar primary key,
    curriculum varchar not null,
    grade int not null,
    term int not null,
    strand varchar not null,
    topic varchar not null,
    subtopic varchar,
    name varchar not null,
    description text not null,
    caps_code varchar not null,
    difficulty_bands_supported jsonb not null,
    recommended_question_types jsonb not null,
    prerequisite_skill_ids jsonb not null default '[]'::jsonb,
    misconception_tags jsonb not null default '[]'::jsonb,
    active boolean not null default true
);

create table if not exists skill_prerequisites (
    id uuid primary key default gen_random_uuid(),
    skill_id varchar not null references skills(skill_id),
    prerequisite_skill_id varchar not null references skills(skill_id),
    unique (skill_id, prerequisite_skill_id)
);

create table if not exists misconceptions (
    id uuid primary key default gen_random_uuid(),
    code varchar unique not null,
    name varchar not null,
    description text not null
);

create table if not exists skill_misconceptions (
    id uuid primary key default gen_random_uuid(),
    skill_id varchar not null references skills(skill_id),
    misconception_id uuid not null references misconceptions(id),
    unique (skill_id, misconception_id)
);

create table if not exists template_families (
    id uuid primary key default gen_random_uuid(),
    family_code varchar unique not null,
    skill_id varchar not null references skills(skill_id),
    name varchar not null,
    description text not null,
    supports_visual boolean not null default false,
    supports_theme boolean not null default false,
    active boolean not null default true
);

create table if not exists templates (
    template_id varchar primary key,
    template_code varchar unique not null,
    skill_id varchar not null references skills(skill_id),
    family_id varchar not null,
    name varchar not null,
    question_type varchar not null,
    template_text text not null,
    instructions_template text,
    variable_schema jsonb not null,
    difficulty_profiles jsonb not null,
    constraints jsonb not null default '[]'::jsonb,
    answer_formula jsonb not null,
    distractor_rules jsonb not null default '[]'::jsonb,
    explanation_template text not null,
    rendering jsonb not null,
    theme_supported boolean not null default false,
    visual_supported boolean not null default false,
    misconception_targets jsonb not null default '[]'::jsonb,
    active boolean not null default true
);

create table if not exists template_misconceptions (
    id uuid primary key default gen_random_uuid(),
    template_id varchar not null references templates(template_id),
    misconception_id uuid not null references misconceptions(id),
    unique (template_id, misconception_id)
);

create table if not exists worksheet_blueprints (
    id varchar primary key,
    blueprint_code varchar unique not null,
    worksheet_type varchar not null,
    structure_json jsonb not null,
    active boolean not null default true
);

create table if not exists generated_worksheets (
    id varchar primary key,
    request_json jsonb not null,
    output_json jsonb not null,
    status varchar not null,
    created_at timestamp default now()
);

create table if not exists generated_questions (
    id varchar primary key,
    worksheet_id varchar not null references generated_worksheets(id),
    template_id varchar not null,
    skill_id varchar not null,
    question_position int not null,
    question_json jsonb not null,
    answer_json jsonb not null,
    metadata_json jsonb not null
);
