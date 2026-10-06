---
name: c-cpp
description: Andres's C/C++ context — how to explain modern idioms to someone with a pre-2000s C/C++ background, and the repo/build setup for code that must run on embedded/SBC hardware (Raspberry Pi GPIO etc.). Use for any C or C++ work.
---

# C/C++ development

- Andres knows both C and C++, but his background is pre-2000s style. Expect
  him to ask about modern idioms/standards (C99/C11/C17, C++11 and later —
  RAII, smart pointers, `<functional>`/lambdas, move semantics, etc.) rather
  than assume familiarity — explain briefly when introducing them instead of
  using them silently.
- For a project targeting embedded/SBC hardware (e.g. Raspberry Pi GPIO
  work) where code must actually build and run on the target device: prefer
  two independent **non-bare** git repos (dev machine + device), synced by
  direct `git push` to the device with `receive.denyCurrentBranch =
  updateInstead` set on the device repo (push updates its working tree
  directly, no separate pull step) — plus a small local wrapper script that
  pushes, then builds and runs over ssh on the device, streaming output back.
  Confirmed working well for `Ws2818` (Raspberry Pi + WS281x LED strip); no
  GitHub/hosted remote or full local/feature branch model needed for this
  kind of single-developer, single-target project — that heavier model is
  for projects with a real shared/production remote.
