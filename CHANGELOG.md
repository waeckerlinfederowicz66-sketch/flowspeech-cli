# Changelog

## Unreleased

- Keep reflected credentials and private URLs out of error messages, codes and
  trace IDs, including terminal-job errors.

- Preserve HTTP status and Retry-After when a response body is interrupted;
  do not retry known authentication failures.
- Bound active HTTP workers and reject overlapping calls on an occupied client,
  including requests that remain active after the caller's deadline.

## 0.2.0 - 2026-10-26

- Require requestId on every job response; normalize job/request UUIDs before comparison and return canonical lowercase IDs.

- Release-gate fix: structurally validate RIFF/chunk bounds and exact PCM WAV fields; reject partial samples and preserve recovery IDs on all malformed-audio errors.

- Migrate from legacy synchronous generation to public API v1 submit, poll and download.
- Add stable UUID idempotency, bounded retries, Retry-After, total deadlines and recovery IDs.
- Map single and explicit multi-speaker input; reject obsolete options and malformed responses.
- Validate success/deleted states, WAV metadata and downloaded audio; bound download sizes.
- Isolate download credentials across HTTPS redirects; reject API redirects.
- Update quota/voices handling, subscription requirements and error diagnostics.
- Add fake-transport contract tests and distribution verification.
- Preserve synthesize/doctor and Python compatibility helpers; add quota, voices, status, cancel and download.
- Reconstruct source packaging from checksum-verified 0.1.0 wheel; see PROVENANCE.md.

The 0.2.0 release assets are prepared locally. Publication is a separate coordinator action.

