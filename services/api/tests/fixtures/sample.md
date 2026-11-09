# SpecLens Sample Spec

## Introduction

This is a synthetic Markdown fixture used only for automated tests.
It contains enough text for hierarchical chunking without using confidential customer documents.

## Requirements

### Functional

The system shall accept Markdown uploads and preserve heading paths on every chunk.
The system shall reject unsupported file types with a clear validation error.
The system shall detect duplicate uploads using a SHA-256 content digest.

### Non-functional

Processing shall not block the API request thread; ingestion runs in a background worker.
Large documents shall be split into chunks of roughly six hundred to nine hundred tokens.

## Appendix

Extra filler text for chunk packing. Alpha bravo charlie delta echo foxtrot golf hotel india
juliet kilo lima mike november oscar papa quebec romeo sierra tango uniform victor whiskey
x-ray yankee zulu. Repeat once more for density: alpha bravo charlie delta echo foxtrot golf
hotel india juliet kilo lima mike november oscar papa quebec romeo sierra tango uniform.
