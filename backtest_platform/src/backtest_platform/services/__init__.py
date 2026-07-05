"""Clean-architecture service layer (W5.1).

Physical landing zone for use-case / service clusters extracted out of the
legacy top-level packages. Each subpackage owns one cohesive service (e.g.
``risk_gate``). Old import paths keep working via re-export shims during the
migration window.
"""
