# Security and Safety

OEBP defines semantic behavior contracts for embodied systems. Invalid,
untrusted, or malicious behavior documents can create physical risk when they
are connected to real robots. Treat every external behavior proposal, adapter,
capability profile, context source, and registry entry as untrusted until it
passes deterministic validation and the deployment's safety supervisor.

## Reporting

Please open a private security advisory or contact the maintainers before
publicly disclosing vulnerabilities that could enable unsafe robot behavior,
validator bypass, registry poisoning, adapter abuse, or unsafe generated data.

If private advisories are unavailable for the repository, open a minimal public
issue that says a security report exists without publishing exploit details.

## In Scope

- Validator bypasses.
- Ambiguous semantics that can cause unsafe execution.
- Adapter or registry spoofing.
- Capability-profile misrepresentation.
- Unsafe handling of model-generated behavior proposals.
- Trace or provenance tampering.
- Supply-chain risks in reference implementations.

## Out of Scope

- Unsupported forks or private downstream deployments.
- Vulnerabilities in unrelated robot middleware unless OEBP integration makes
  the issue materially worse.
- Physical safety guarantees for hardware that does not implement the required
  external safety supervisor.

## Safety Boundary

OEBP validation is necessary but not sufficient for real-world execution. A
deployment MUST keep independent safety controls, emergency stop behavior,
hardware limits, operator policy, and environment-specific risk checks outside
the protocol runtime.

