# ADR-004: Stage 1 container scan and publication boundary

- Status: Accepted for Stage 1
- Decision date: 2026-10-18

## Context

Stage 1 includes optional container checks and one non-production registry. A pull request or Dockerfile must not receive registry credentials, and the published artifact must be the same artifact that passed image scanning.

## Decision

Use GHCR as the sole Stage 1 destination. Build and scan a local image in a read-only job without registry credentials. Upload the image archive and its archive hash/config ID only when publication is requested. A separate job runs after all mandatory quality and security gates; it has `packages: write`, targets the caller's fixed `non-production` GitHub Environment, does not check out or execute application code, verifies the artifact, pushes a commit-SHA tag, and compares the remote manifest's config digest with the scanned image's config ID. Both container checks and publication default to disabled. Each caller repository must create and protect the named environment before enabling publication.

The publisher accepts only a non-fork push to the caller's actual default branch and limits the destination to the caller owner's GHCR namespace. The optional publishing caller uses the same central reusable workflow as the normal PR caller. GHCR package permissions and a protected environment must be configured before publication is enabled.

ADR-006 keeps publication as a separate job within `reusable-app-ci.yml` for Stage 1. Every caller allows `packages: write` so GitHub accepts the optional publisher in the called workflow, alongside the scopes required by the nested OSV workflow. Only the guarded publisher receives a package-write runtime token; source/build, Sonar, and container jobs receive only `contents: read`; Gitleaks additionally receives `pull-requests: read` for its PR commit lookup. Same-run artifact transfer uses runtime credentials without adding an `actions: read` API-token requirement.

The builder adds OCI source, revision, title, creation-time, and workflow-run labels before scanning, so those labels travel with the image that is later verified and published. Labels provide descriptive traceability; signing, provenance, and independent verification remain future-stage work. License, vendor, and author values are supplied by the application's Dockerfile when known.

## Alternatives and trade-offs

- Build and push in one job: simpler but requires registry write permission in the same job that executes an untrusted Dockerfile; rejected.
- Rebuild in the publisher: avoids artifact transfer but does not prove the published object is the one scanned; rejected.
- Multi-registry routing: out of Stage 1; only GHCR is used.

## Consequences

- Publication needs an artifact transfer and digest checks.
- Commit tags are traceable, but remain mutable unless GHCR policy enforces immutability; downstream consumers should record/use the published digest.
- This repository does not publish an image during implementation, and no remote registry behavior has been verified.
