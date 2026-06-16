# Runtime And Ecosystem Bindings

This directory contains non-normative binding design notes for OEBP.

The core protocol remains defined by `spec/v0.1/core.md`, JSON Schemas, and
conformance tests. Bindings may translate OEBP documents into middleware,
transport, or runtime-native representations, but they must not redefine OEBP
semantic identifiers, lifecycle states, finding codes, trace semantics, or
capability requirements.

- `transport-and-ecosystem-bindings.md` describes JSON, Protobuf, ROS 2, and
  behavior-tree binding status for v0.1.
