# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-29

### Added

- Client for the Instapaper API v2: bookmarks, folders, tags, highlights, and the current user.
- Pagination with `bookmarks.iterate()` and change syncing with `bookmarks.changes()` and `bookmarks.sync()`.
- `bookmarks.list()` returns a page you can loop over, index, and take the `len` of directly.
- Parsed article text with `bookmarks.parse()`, including Instaparser keys for non-personal use.
- OAuth 2 helpers for building the authorization URL and exchanging a code for an access token.
- Typed models and an exception hierarchy keyed on HTTP status.
