## Summary

Describe the change in 2-5 sentences.

## Why this change exists

Explain the problem being solved.

## Scope

Select one primary scope:

- [ ] infrastructure scaffold
- [ ] service/database hardening
- [ ] app integration
- [ ] feature work
- [ ] docs / governance
- [ ] bug fix

## What changed

- 
- 
- 

## What intentionally did not change

- 
- 

## Risk assessment

- [ ] low risk
- [ ] moderate risk
- [ ] high risk

Why:

## Optional-service behavior

If this PR touches optional services, confirm degraded behavior:

- [ ] database remains optional where intended
- [ ] external API failures degrade gracefully
- [ ] AI-dependent features fail safely
- [ ] non-critical UI blocks do not silently corrupt state
- [ ] not applicable

## Drift check

Confirm the following:

- [ ] this PR does not introduce duplicate source-of-truth modules
- [ ] this PR does not reduce existing org-repo feature breadth for cleanup convenience
- [ ] this PR does not mix unrelated concerns
- [ ] this PR does not silently alter portfolio, options, or backtesting semantics

## Files of interest for review

- 
- 
- 

## Validation

Describe what was checked.

- [ ] startup path reviewed
- [ ] error-handling path reviewed
- [ ] degraded-service path reviewed
- [ ] docs updated where needed
- [ ] template/checklist completed honestly

## Follow-on work

List any intended next steps.
