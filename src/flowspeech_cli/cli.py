from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import uuid
from pathlib import Path

from . import __version__
from ._v1 import V1Client, identifier
from .client import DEFAULT_API_URL, DEFAULT_VOICE, FlowSpeechError, api_origin, synthesize


def read_text_argument(args):
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.text:
        return args.text
    if args.segments:
        return None
    raise ValueError("Provide text, --file or --segments")


def command_synthesize(args):
    try:
        if sum(bool(value) for value in (args.text, args.file, args.segments)) != 1:
            raise ValueError("Provide exactly one of text, --file or --segments")
        request_id = identifier(args.request_id) if args.request_id else str(uuid.uuid4())
        print(f"request_id={request_id}", file=sys.stderr, flush=True)
        result = synthesize(read_text_argument(args), voice=args.voice, api_url=args.api_url,
                            timeout=args.timeout, request_id=request_id,
                            segments=json.loads(Path(args.segments).read_text()) if args.segments else None)
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(result.audio_base64, validate=True))
        print(f"wrote {output_path} job_id={result.job_id} request_id={result.request_id}")
        return 0
    except (OSError, ValueError, FlowSpeechError) as exc:
        return report_error(exc)


def report_error(exc):
    print(f"flowspeech: {exc}", file=sys.stderr)
    if isinstance(exc, FlowSpeechError):
        print(f"code={exc.code} trace_id={exc.trace_id} request_id={exc.request_id} job_id={exc.job_id}", file=sys.stderr)
        if exc.result_url:
            print("Retry the download subcommand with the existing job ID; do not create a new recording.", file=sys.stderr)
    return 1


def command_doctor(args):
    try:
        api_origin(args.api_url)
    except ValueError as exc:
        return report_error(exc)
    print(f"flowspeech-cli {__version__}")
    print(f"default_api_url={args.api_url}")
    print("api_key=" + ("configured" if os.getenv("FLOWSPEECH_API_KEY") else "missing"))
    print("local_token_storage=disabled")
    return 0


def command_api(args):
    try:
        with V1Client(base_url=api_origin(args.api_url), timeout=args.timeout) as client:
            if args.command == "quota":
                result = client.quota()
            elif args.command == "voices":
                result = client.voices()
            elif args.command == "status":
                result = client.find_job(args.request_id) if args.request_id else client.get_job(args.job_id)
            elif args.command == "cancel":
                result = client.cancel_job(args.job_id)
            else:
                deadline = client.clock() + client.timeout
                job = client.get_job(args.job_id, deadline=deadline)
                if job["status"] != "success":
                    raise ValueError("Job has not succeeded; inspect its status before downloading")
                result = client._result(job)
                audio = client.download_audio(result["url"], deadline=deadline)
                output = Path(args.out)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(audio)
                print(f"wrote {output}")
                return 0
            print(json.dumps(result, indent=2))
            return 0
    except (OSError, ValueError, FlowSpeechError) as exc:
        return report_error(exc)


def build_parser():
    parser = argparse.ArgumentParser(prog="flowspeech", description="FlowSpeech public API v1 command-line client.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("synthesize", "doctor", "quota", "voices", "status", "cancel", "download"):
        command = commands.add_parser(name)
        command.add_argument("--api-url", default=DEFAULT_API_URL)
        command.add_argument("--timeout", type=float, default=300, help="Total operation deadline in seconds.")
        if name == "synthesize":
            command.add_argument("text", nargs="?")
            command.add_argument("--file")
            command.add_argument("--segments", help="UTF-8 JSON file containing speaker/text/voiceName turns.")
            command.add_argument("--voice", default=DEFAULT_VOICE)
            command.add_argument("--out", required=True)
            command.add_argument("--request-id", default=os.getenv("FLOWSPEECH_REQUEST_ID"))
            command.set_defaults(func=command_synthesize)
        elif name == "doctor":
            command.set_defaults(func=command_doctor)
        else:
            if name == "status":
                ids = command.add_mutually_exclusive_group(required=True)
                ids.add_argument("--job-id")
                ids.add_argument("--request-id")
            elif name in ("cancel", "download"):
                command.add_argument("--job-id", required=True)
            if name == "download":
                command.add_argument("--out", required=True)
            command.set_defaults(func=command_api)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

