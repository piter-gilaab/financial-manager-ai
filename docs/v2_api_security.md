# V2 Phase 3 — API Security and Privacy

Status: **VALIDATED FOR LOCAL SINGLE-USER SCOPE**.

The API has no authentication, accounts or multitenancy. Session IDs are not
security credentials. The default server entry point binds loopback only. CORS
is disabled by default and can be configured only with explicit origins;
wildcards are rejected and credentials are disabled.

Request schemas forbid unknown fields and close operations/parameters. No route
accepts a server filesystem path, SQL, formula, Python expression, adapter,
provider, arbitrary column/grouping or algorithm selector. Multipart bodies are
parsed incrementally and files are bounded before onboarding. Temporary names
are server-owned and cleaned after handoff; the application factory does not
mutate Starlette parser globals.

Errors contain stable code/field/safe message only. Tests assert absence of
stack traces, absolute paths, registry artifacts and raw input content. Prompt
injection and fake evidence handles remain inert. OpenAPI contains no auth claim,
Forecasting/RAG endpoint or public-hosting assumption.

Host access, OS permissions, encryption, backups and deployment firewall remain
operator responsibilities; this is not an enterprise security certification.

