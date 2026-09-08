"""Importable DEVELOPMENT fixtures for the endogenous-controller frontier tests.

These are deliberately boring. Their only purpose is to make two different controller mechanisms
have stable executable identities so a process-death test can ask whether the lineage notices a
mechanism substitution.
"""
from __future__ import annotations


def stop_as_alpha(_context):
    from genesis.controller import Stop

    return Stop(reason="alpha mechanism")


def stop_as_beta(_context):
    from genesis.controller import Stop

    return Stop(reason="beta mechanism")
