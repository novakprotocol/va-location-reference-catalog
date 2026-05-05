# ADR-002 — Read-Only First

## Status

Accepted for pilot.

## Decision

The pilot is read-only and does not mutate VA production systems.

## Rationale

Location data is useful for labels and reconciliation, but production writes require separate authority.

## Consequence

First production value comes from reporting, reconciliation, and validation.
