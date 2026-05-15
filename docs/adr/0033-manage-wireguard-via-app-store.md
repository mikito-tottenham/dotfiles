---
title: "Manage WireGuard via Mac App Store"
status: "accepted"
date: "2026-05-15"
worked_at: "2026-05-15T06:36:36Z"
agent_model: "GPT-5"
---

# ADR-0033: Manage WireGuard via Mac App Store

## Context

SQEX access currently relies on an Interlink Group VPN WG contract, which uses WireGuard.
On this Mac, WireGuard is installed as the App Store application and is visible to macOS as a Network Extension VPN service.
Existing automation can control that service with `scutil --nc`, so the application does not need to be operated manually for routine status, connect, and disconnect workflows.

Homebrew provides `wireguard-tools`, but that is a CLI userspace/tooling path and does not represent the same macOS Network Extension service that the existing automation controls.

## Decision

Manage the WireGuard macOS application through `Brewfile` using Homebrew Bundle's `mas` support:

- install `mas` with Homebrew
- install App Store app `WireGuard` with id `1451685025`
- do not add `wireguard-tools` unless a future workflow explicitly needs CLI-only WireGuard operation

WireGuard tunnel profiles, private keys, and provider-issued configuration remain user-local state and are not stored in git.

## Consequences

New machines can restore the WireGuard application through `brew bundle` after App Store authentication is available.
Existing `scutil --nc` based automation remains compatible with the App Store application.
If a future workflow requires `wg` or `wg-quick`, that should be treated as a separate CLI operation and added deliberately.
