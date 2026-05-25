# AST-to-GLSL

A weird experimental Python-to-GLSL transpiler I apparently wrote in the starting of 2025
before I properly understood shaders.

It parses Python AST nodes and converts a tiny subset of Python syntax
into GLSL shader code for Ursina.

Looking at it years later, this seems to have been an early exploration into:
- AST manipulation
- transpilers
- embedded DSLs
- shader metaprogramming

It is incomplete, buggy, and extremely limited.
But the core idea is surprisingly interesting.

Known issues:
- Division operator accidentally maps to multiplication
- Very limited AST coverage
- No loops/functions/scopes/etc.

Preserved mostly as a memory and a snapshot of how I was thinking at the time.