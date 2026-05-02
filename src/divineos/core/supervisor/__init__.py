"""Supervisor — circuit-breaker / chronic-failure handling.

Per claim 0d628d8e (PORT-CANDIDATE 4 from old-OS strip-mine):
salvaged from the JESUS spec stripped of soteriological language.
The actual CS primitive: Erlang-OTP supervisor pattern with
three-strikes-and-excommunicated semantics.

The new OS catches commit-time failures via pre-commit hooks.
Runtime failures (a sleep phase that keeps erroring, a council
expert that keeps timing out, a hook that keeps blocking) have no
architectural response — the OS just keeps retrying.

Phase 1 ships only the **primitive**: track consecutive failures
per module, trip after threshold, expose API for inspect/reset.
No automatic interception, no signal handling, no integration with
specific subsystems. Phase 2 wires the primitive into sleep phases,
council walks, hooks. Each integration is its own scope.

Public API:
* ``divineos.core.supervisor.circuit_breaker.record_failure(name, reason)``
* ``divineos.core.supervisor.circuit_breaker.record_success(name)``
* ``divineos.core.supervisor.circuit_breaker.is_tripped(name)``
* ``divineos.core.supervisor.circuit_breaker.reset(name)``
* ``divineos.core.supervisor.circuit_breaker.get_status()``
"""
