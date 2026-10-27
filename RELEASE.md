# Release 0.2.1

This candidate contains the previously reviewed FlowSpeech public API v1 safety
fixes: sanitized upstream errors, interrupted-body status/cooldown preservation,
and bounded HTTP-worker lifetimes. No additional API behavior is introduced.

Only the coordinator may commit, tag, push, dispatch publication workflows, or
publish packages, after separate authorization. Preserve older publications and
tags. Use commit email waeckerlinfederowicz66@gmail.com for a future authorized commit.

## Current Verification and Gates

Run source tests with synthetic audio and mock transports only. Build fresh
0.2.1 wheels and sdists with build 1.3.0 and hatchling 1.27.0, then run twine 6.2.0
checks. Test the extracted sdist and the installed wheel with pytest's source path
disabled and imports proven to resolve to the installed target. Inspect actual
archive contents against explicit allowlists and record final SHA-256 hashes.

The 0.2.1 section of VALIDATION.md records current local checks; older sections
are historical evidence only. Exact hashes, logs, changed files and remaining
gates are in the coordinator's python-handoff.json for this release. Confirm
0.2.1 registry availability, final committed source, passing remote CI and exact
artifact hashes before publication. Do not dispatch a publish workflow as a test.

The existing publish workflow rebuilds in a separate publish job after verification;
the coordinator must address verified-versus-uploaded artifact consistency before
using it. Release-published and manual-dispatch events can reach publication.

# Historical Release 0.2.0

The text below is preserved historical evidence, not the 0.2.1 release procedure.

# Release 0.2.0

## Coordinator steps

1. Review source changes, CHANGELOG.md and VALIDATION.md.
2. Confirm 0.2.0 is still unpublished on PyPI; 0.1.0 must not be overwritten.
3. Re-run the offline suite: python -m pytest -q.
4. Build with reviewed hatchling==1.27.0 and build==1.3.0:
   python -m build --no-isolation
5. Check metadata: python -m twine check dist/*.whl dist/*.tar.gz.
6. Install the wheel in an isolated environment and re-run tests against that
   installed package (override pytest pythonpath to exclude src).
7. Inspect wheel/sdist members and verify SHA-256 checksums from VALIDATION.md.
8. Only the coordinator may commit/tag/push and upload the reviewed artifacts:
   python -m twine upload dist/*.whl dist/*.tar.gz
   Use trusted publishing or a separately supplied PyPI credential; never put it
   in source, shell history, documentation or logs.

The source tree was reconstructed from the published wheel; read PROVENANCE.md.
The canonical source repository is
https://github.com/waeckerlinfederowicz66-sketch/flowspeech-cli.
The coordinator owns its workflows and PyPI OIDC setup. The console entry point remains
flowspeech = flowspeech_cli.cli:main.

## Safety gates

No production API key or paid generation was used. Do not enable live generation
during routine packaging tests. Do not include .env, credentials, virtualenvs,
caches, tool executables, downloaded reference wheels or private content in releases.
Review VALIDATION.md for exact results and remaining integration limitations.

Preserve the existing 0.1.0 publication. Release 0.2.0 only after final coordinator
review of source, artifacts, registry availability and account authorization.
The worker has not pushed commits, published packages or changed any upstream PR.

The verified server quota contract returns subscription and limits alongside
quota. Preserve subscription; entitlement is only an optional compatibility alias.

## Reproducible tests

All network calls in the test suite are fake httpx transports. An autouse fixture
blocks socket connect/connect_ex, so a missing mock cannot consume credits.
The adapter is vendored independently in these three integrations; any future
contract fix must be applied to all copies and their matching contract tests.

## Release-gate fixes

The candidate was rebuilt after the independent WAV/timeout review. Do not upload
an older 0.2.0 archive: compare the rebuilt checksums in VALIDATION.md. Run the
complete tests against source and the actual installed/extracted artifact, including
tests/test_wav_validation.py. RIFF bounds/chunks/padding, PCM 24000 Hz mono16,
block alignment 2, byte rate 48000 and nonempty even data lengths are mandatory.
Malformed audio must produce invalid_audio and preserve recovery identifiers.

Every job must contain a valid requestId. Run tests/test_job_identifiers.py to
verify missing/mismatched ID rejection and case-insensitive UUID matching.
Returned job and request IDs are normalized to canonical lowercase UUIDs.

