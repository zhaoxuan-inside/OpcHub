"""OpcHub host adapter for the MicroFlow4Python execution framework.

The business execution layer is MicroFlow's: contract operators + JSON flow
configs compiled into immutable releases. This package is the *host* side of
that boundary (framework README "集成与使用" step 3):

- ``operator_bridge``  projects the OpcHub operator SDK registry (226+
  single-purpose callables) into MicroFlow six-param contract operators.
- ``flow_engine``      compiles ``config/flows/opchub_flows.json`` (generated
  by ``tools/convert_scenarios.py`` from the scenario YAML assets) into a
  release and executes scenarios request-scoped (ephemeral local runs).

Business data persistence, RBAC, audit and telemetry remain OpcHub host
concerns; MicroFlow's StateStore port (durable scheduling) is a future track.
"""
