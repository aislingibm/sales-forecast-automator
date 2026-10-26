# Architectural Decision Records (ADRs)

## ADR-001: Backend Framework & Persistence Layer
- **Status**: Accepted
- **Context**: The pipeline requires high-throughput processing (<2s on 50k rows), deterministic reproducibility, typed REST APIs, and auto-generated OpenAPI documentation.
- **Decision**: Python 3.11+ with FastAPI, Pydantic v2, and SQLite with SQLAlchemy 2.0.
- **Consequences**: Zero external database infrastructure required for local testing or containerized deployments; sub-second query performance with surrogate primary key indexing.

## ADR-002: Vectorized Processing & Externalized Rules
- **Status**: Accepted
- **Context**: Report filters and legacy pivot calculations must match historical Excel calculations to the cent while remaining customizable without code changes.
- **Decision**: Use pandas for in-memory vectorized calculations and load all filter predicates and quality thresholds from `config/rules.yaml`.
- **Consequences**: Exact floating-point parity with pivot tables; instantaneous rule updates by editing YAML.

## ADR-003: Pluggable System of Record (SoR) Reconciliation
- **Status**: Accepted
- **Context**: Must reconcile synthetic forecasts against an IBM Sales Cloud System of Record without live external network dependencies or real credentials in demo builds.
- **Decision**: Define an abstract base class `SalesSystemClient` implemented by `MockSalesCloudClient` (seeded with deterministic planted variances) and a dormant `SalesCloudClient` stub disabled behind `sales_cloud.enabled: false`.
- **Consequences**: Enables 100% offline, deterministic testing of reconciliation, retry backoffs, and variance reporting while isolating live connection readiness.

## ADR-004: Zero-Build Frontend Architecture
- **Status**: Accepted
- **Context**: Self-serve dashboard must be lightweight, responsive, accessible (WCAG 2.1 AA), and require no complex Node/npm build toolchains.
- **Decision**: Vanilla HTML5, CSS3, and locally bundled Chart.js (`static/chart.umd.js`) with zero CDN dependencies.
- **Consequences**: Fast loading, zero dependency vulnerabilities, works in air-gapped/offline environments.

## ADR-005: Surrogate Primary Key for Snapshot Tables
- **Status**: Accepted
- **Context**: Ingested raw extracts may contain duplicate `sales_order_num` records (either planted or from upstream errors) that need to be captured for data quality analysis.
- **Decision**: Use an auto-incrementing integer `id` as the database primary key, keeping `sales_order_num` indexed but non-unique.
- **Consequences**: Allows complete capture of all raw records without database insertion conflicts.
