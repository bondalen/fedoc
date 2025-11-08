# Multigraph Architecture Overview (2025-11-07)

## Database State
- PostgreSQL 16.10 with Apache AGE.
- Graphs created: `mg_blocks`, `mg_designs` (via `ag_catalog.create_graph`).
- Vertex labels: `block_type`, `design_node` (each has columns `id graphid`, `properties agtype`, `name text`).
- Edge labels: `block_edge`, `design_edge` (columns `id graphid`, `start_id graphid`, `end_id graphid`, `properties agtype`).
- Primary keys added on all `id` columns.
- Self-loop prevention using `CHECK (NOT ag_catalog.graphid_eq(start_id, end_id))`.
- Bidirectional uniqueness enforced with `CREATE UNIQUE INDEX ... (LEAST(start_id,end_id), GREATEST(start_id,end_id))` on both edge tables.

## Relational Schema (schema `mg`)
- `mg.projects(id serial pk, name unique, description, created_at timestamptz default now())`.
- `mg.design_to_block(design_id graphid pk, block_id graphid)` with foreign keys to `mg_designs.design_node` and `mg_blocks.block_type`.
- `mg.design_edge_to_project(edge_id graphid, project_id integer)` with composite PK `(edge_id, project_id)` and foreign keys to `mg_designs.design_edge` and `mg.projects`.
- Support indexes: `idx_design_to_block_block_id`, `idx_design_edge_to_project_project_id`.

## Pending Actions
- Implement trigger `mg.prevent_bidirectional_duplicate` once dollar-quoting issue resolved (not required for PG >= 15, but keep in backlog).
- Seed reference data (core block types, sample designs).
- Build new codebase in `mgsrc/` per plan: backend REST API, frontend client, MCP service.
