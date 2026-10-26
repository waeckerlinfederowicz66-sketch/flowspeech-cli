# Validation: flowspeech-cli 0.2.0

Date: 2026-10-26. Final release-gate follow-up in an isolated migration checkout.
Both source and actual final artifacts pass 167 tests (previous baseline 99).
The final archives supersede all earlier local 0.2.0 candidates.

## Commands and results

- Python 3.12.14; httpx 0.28.1 and pytest 8.4.2.
- Source: ../langchain-flowspeech/.venv/bin/python -m pytest -q --basetemp=.test-tmp/release-gate-ids
  -> 167 passed (0.55s).
- ../langchain-flowspeech/.venv/bin/python -m build --no-isolation -> sdist and wheel-from-sdist succeeded.
- Build tools: hatchling 1.27.0, build 1.3.0, twine 6.2.0.
- ../langchain-flowspeech/.venv/bin/python -m twine check dist/*.whl dist/*.tar.gz -> both PASSED.
- ../langchain-flowspeech/.venv/bin/python scripts/verify_artifacts.py dist/*.whl dist/*.tar.gz -> passed.
- ../langchain-flowspeech/.venv/bin/python -m pip install --no-index --no-deps --force-reinstall dist/*.whl
  -> final rebuilt wheel installed locally; no dependency downloads.
- ../langchain-flowspeech/.venv/bin/python -m pytest -q -o pythonpath= --basetemp=.test-tmp/release-final-wheel
  -> 167 passed (0.55s).
- Import origins explicitly verified under site-packages, not src. Installed
  adapter SHA-256 equals the reviewed source.
- ../langchain-flowspeech/.venv/bin/python -m pip check -> no broken requirements.
- git diff --check -> passed.
- Installed flowspeech --version -> flowspeech 0.2.0.
- Installed distribution Repository metadata matches the canonical GitHub URL.

## Final artifacts

- dist/flowspeech_cli-0.2.0-py3-none-any.whl: 14333 bytes, 10 members
  SHA-256: 1a43a71f0249418f84029059ac39bbcae1eb993d642a6ff0f43a6006988a9e43
- dist/flowspeech_cli-0.2.0.tar.gz: 21796 bytes, 18 members
  SHA-256: 5290e122fae746a4afe6a24802494ca5e5b67479e80434185a427e6dca2597af

Archive inspection verified version metadata, safe member paths, forbidden
development files, secret patterns and private local path leakage. No matches
or unintended runtime files were found. Final artifact code was tested, not
only source. VALIDATION.md is intentionally excluded from these archives.

## Release-gate coverage

- 37 shared WAV tests cover RIFF length/chunk/padding bounds, PCM tag 1, 24000 Hz,
  mono 16-bit, block alignment 2, byte rate 48000, nonempty even data length,
  duplicate/missing format or data chunks, malformed extensions, ancillary chunks,
  every truncation offset and deadline checks during parsing.
- Malformed audio raises typed invalid_audio, keeps request/job/result recovery
  identifiers and cannot trigger another create or audio retry.
- 31 shared identifier tests require a valid requestId on submission, polling,
  lookup and cancellation; reject mismatches and normalize both expected and
  returned UUIDs before comparison. Successful results always contain requestId.
- Existing coverage includes single/multi input mapping, legacy-option rejection,
  stable idempotency/body retries, every pending and terminal status, result deletion,
  quota/voices, recovery, cancellation, API errors, Retry-After and total deadlines.
- Downloads are bounded and credential-free even with polluted injected clients
  and redirects. API redirects are refused. Slow transport/stream tests verify
  the caller's absolute deadline.
- Socket connect/connect_ex are blocked automatically in every test. HTTP uses
  fake transports; audio fixtures are locally synthesized, never production output.

## Shared adapter

All three source copies and their installed/extracted artifact copies are identical.

- Adapter SHA-256: f1e49e7eb2915eb7e796ab869d364e02c5987de8347b07aafef381b5a5764ade
- tests/test_wav_validation.py SHA-256: 36bd7ebfd01c0ffe389ecd42747abcee74576d24a4e704b15e75fa93721afbcc
- tests/test_job_identifiers.py SHA-256: cd6e76f062472482094cc3c7dfc004b033e58a00250a4c948192b5edd182ff80

The adapter and these tests are stable for reuse in the separately owned SDK.
No SDK or MCP files were changed by this worker.

## Contract verification

The original server was read-only. public-api.ts normalizes UUIDs, and
the job serializer always emits requestId. The WAV storage code emits
PCM 24000 Hz mono16, block alignment 2 and byte rate 48000. The quota response
contains subscription and limits alongside quota; entitlement is only an optional
compatibility alias, not a required field.

## Safety and limitations

No production requests, credentials, paid generation, email, commits, pushes,
publication or workflow/OIDC changes were made by this worker. Existing changes
were preserved. No end-to-end production verification is claimed.
A single in-flight HTTP request may finish cleanup after the local caller deadline;
it cannot submit a retry or another recording. Recover accepted jobs with their
original request/job UUID instead of submitting new input.

## Canonical source

The coordinator established
https://github.com/waeckerlinfederowicz66-sketch/flowspeech-cli.
pyproject.toml Repository metadata, the built wheel metadata and PROVENANCE.md
now identify it. The reconstruction history and checksum of the published 0.1.0
wheel remain documented. This checkout still has no local commits; existing
workflows were untouched. The coordinator owns source publication and PyPI OIDC.

## Changed files in this follow-up (10)

- src/flowspeech_cli/_v1.py
- tests/test_wav_validation.py
- tests/test_job_identifiers.py
- pyproject.toml
- PROVENANCE.md
- README.md
- CHANGELOG.md
- RELEASE.md
- VALIDATION.md
- scripts/verify_artifacts.py

Earlier migration files remain in place; this list only describes this release-gate
follow-up. Generated dist/, test outputs, environments and artifact extractions
are ignored build outputs. See RELEASE.md for coordinator-only release steps.
Confirm registry version availability and upload only the reviewed final hashes.
