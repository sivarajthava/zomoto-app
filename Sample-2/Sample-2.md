# Antigravity Build Plan — Magicpin Vera AI Challenge

## 1. Purpose

This document is the execution plan for building the Magicpin Vera AI Challenge project using **Google Antigravity**.

The project requirements are defined in:

```text
problem-statement.md
```

Antigravity must treat `problem-statement.md` as the primary business and technical specification.

The objective is to build a complete, testable, deployable application rather than a prototype that only generates AI messages.

---

# 2. Development Rules for Antigravity

Before starting implementation, follow these rules.

## Rule 1 — Read the specification first

Read:

```text
problem-statement.md
```

Do not start coding until you understand:

* API contract
* Context model
* Decision engine
* Conversation state
* Suppression
* LLM abstraction
* Validation
* Testing
* Docker
* Evaluation requirements

---

## Rule 2 — Do not build everything at once

Work phase-by-phase.

After each phase:

1. Run tests
2. Run the application
3. Inspect the implementation
4. Fix failures
5. Show a concise implementation summary
6. Wait for the next phase instruction

Do not proceed to the next major phase if the current phase is broken.

---

## Rule 3 — Deterministic first

The first working implementation must NOT depend on an external LLM.

Build:

```text
Context
  ↓
Decision Engine
  ↓
Message Strategy
  ↓
Deterministic Template
```

Only after this works should the LLM be introduced.

---

## Rule 4 — LLM must never own business decisions

The LLM can:

* Interpret natural language
* Generate message wording
* Generate concise responses

The LLM must NOT independently decide:

* Whether a trigger is valid
* Whether outreach is allowed
* Whether suppression applies
* Which merchant is eligible
* Which customer is eligible
* Whether facts are true
* Whether an unsupported statistic can be used

Those decisions belong to application code.

---

## Rule 5 — Never invent data

All generated claims must originate from supplied context.

If the application does not know a fact:

```text
DO NOT INVENT IT.
```

---

## Rule 6 — Tests are mandatory

Every major component must have tests.

Do not mark a phase complete simply because the code compiles.

---

# 3. Phase 0 — Workspace Inspection

## Objective

Understand the current Antigravity workspace before modifying anything.

### Prompt 0.1 — Inspect Workspace

```text
You are working on the Magicpin Vera AI Challenge.

Before writing any code, inspect the entire current workspace.

Read:
- problem-statement.md
- README.md if present
- existing source files
- configuration files
- test files
- Docker files
- environment files

Do not modify any files yet.

Determine:
1. Current project structure
2. Existing technology/framework
3. Existing dependencies
4. Existing implementation
5. Existing tests
6. Existing configuration
7. Missing components required by problem-statement.md

Return:
- Current architecture summary
- Existing files relevant to the project
- Missing components
- Recommended implementation sequence

Do not generate code yet.
```

### Gate

Verify that Antigravity correctly understands the existing repository.

---

# 4. Phase 1 — Architecture Design

## Objective

Create the technical architecture before implementation.

### Prompt 1.1 — Architecture

```text
Read problem-statement.md completely.

Design the production architecture for the Vera AI Challenge.

The architecture must include:

- REST API
- Context repository
- Context versioning
- Merchant model
- Category model
- Customer model
- Trigger model
- Conversation state
- Suppression engine
- Eligibility engine
- Decision engine
- Message strategy
- Deterministic template engine
- LLM abstraction
- Prompt builder
- Structured LLM output parser
- Hallucination validator
- CTA validator
- Persistence layer
- Logging
- Configuration
- Testing architecture

Use clean architecture / modular architecture principles.

Keep business logic independent of:
- FastAPI
- database
- LLM provider
- HTTP layer

Produce:
1. Architecture diagram
2. Component responsibilities
3. Dependency direction
4. Domain objects
5. Interfaces
6. Data flow
7. Error-handling strategy
8. Testing strategy

Do not implement the code yet.
```

### Prompt 1.2 — Architecture Review

```text
Review the architecture you just designed against every requirement in problem-statement.md.

Create a requirement-to-component traceability matrix.

Columns:

Requirement
Component
Implementation approach
Test approach
Potential risk

Identify:
- missing requirements
- unnecessary complexity
- possible coupling
- scalability concerns
- testability concerns

Do not modify code.
```

---

# 5. Phase 2 — Project Bootstrap

## Objective

Create the basic runnable application.

### Prompt 2.1 — Bootstrap

```text
Implement Phase 1 of the Vera project.

Create the application foundation using:

Python
FastAPI
Pydantic
pytest
httpx

Use a clean modular structure.

Create:

README.md
problem-statement.md if missing
.gitignore
.env.example
Dockerfile
docker-compose.yml
pyproject.toml

Create the application entry point.

Requirements:

- Application starts locally
- Application starts in Docker
- Configuration comes from environment variables
- No secrets are hard-coded
- Logging is configured
- Health endpoint is available

Do not implement the decision engine yet.

Run:
- unit tests
- application startup test
- Docker build

Fix all failures before finishing.
```

### Prompt 2.2 — Bootstrap Verification

```text
Verify the Phase 2 implementation.

Run:
1. pytest
2. application startup
3. GET /v1/healthz
4. Docker build
5. Docker startup

Inspect the generated project for:
- hard-coded secrets
- circular dependencies
- unnecessary dependencies
- poor module boundaries

Fix any problems found.

Return:
- test result
- Docker result
- endpoint result
- files created
- issues fixed
```

### Gate

Do not continue until:

```text
pytest = PASS
application startup = PASS
Docker build = PASS
health endpoint = PASS
```

---

# 6. Phase 3 — API Contract

## Objective

Implement all required endpoints without business logic.

Required:

```text
GET  /v1/healthz
GET  /v1/metadata
POST /v1/context
POST /v1/tick
POST /v1/reply
```

### Prompt 3.1 — API Models

```text
Implement the Vera API contract from problem-statement.md.

Create strongly typed Pydantic request and response models for:

- HealthResponse
- MetadataResponse
- ContextRequest
- ContextResponse
- TickRequest
- TickResponse
- ActionResponse
- ReplyRequest
- ReplyResponse

Validate:
- required fields
- enum values
- timestamps
- context scope
- IDs
- optional customer context

Do not implement real business logic yet.

Use placeholder service implementations where necessary.

Add API contract tests.
```

### Prompt 3.2 — API Controllers

```text
Implement the five required API endpoints.

Keep controllers thin.

Controllers must:
- validate requests
- invoke application services
- return response DTOs
- map domain errors to HTTP responses

Do not place business rules inside controllers.

Add integration tests using FastAPI TestClient/httpx.

Run all tests.
```

### Prompt 3.3 — API Contract Review

```text
Review every API endpoint against problem-statement.md.

Verify:
- HTTP method
- path
- request schema
- response schema
- status codes
- validation behavior
- error behavior

Create a contract test covering every endpoint.

Do not change the public API unless the specification requires it.
```

---

# 7. Phase 4 — Domain Model

## Objective

Create the domain model independently of the API.

### Prompt 4.1 — Domain Objects

```text
Implement the core Vera domain model.

Create domain models for:

Category
Merchant
MerchantPerformance
Offer
Customer
Trigger
Conversation
ConversationMessage
Action
SuppressionRecord
ContextVersion

Use immutable/value-object patterns where appropriate.

Domain objects must not depend on FastAPI.

Add unit tests for:
- validation
- equality
- serialization where needed
- state transitions
```

### Prompt 4.2 — Domain Review

```text
Review the domain model.

Check whether the model supports all scenarios in problem-statement.md:

- dentist
- salon
- restaurant
- gym
- pharmacy
- merchant trigger
- customer trigger
- suppression
- conversation
- context updates
- versioning

Identify missing domain concepts.

Fix only genuine domain-model gaps.
```

---

# 8. Phase 5 — Context Repository

## Objective

Implement context storage before decision logic.

### Prompt 5.1 — Repository Interface

```text
Create repository interfaces for:

ContextRepository
ConversationRepository
SuppressionRepository

Keep the interfaces independent of storage technology.

Required ContextRepository operations:

save_context()
get_context()
get_latest_context()
list_contexts()
delete_context()
```

### Prompt 5.2 — In-Memory Repository

```text
Implement an in-memory repository suitable for local development and tests.

Implement:

- context storage
- version handling
- idempotency
- stale-version rejection
- thread safet
```
