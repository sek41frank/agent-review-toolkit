# agent-review-toolkit

Give an AI-generated change a second review, with a clear input packet and verifiable execution records.

[中文使用说明](README.zh-CN.md) · [Example packet](examples/packet.md) · [Validation record](VALIDATION.md)

This small Python CLI runs two sequential reviewers through **OpenCode v2**. The scanner identifies possible findings. The reviewer receives the original packet and the scanner response, then confirms, rejects, or adds findings. Both responses and their execution records are saved locally.

The second reviewer sees the first response; this is not a blinded independent review. `REVIEW_COMPLETED` means the responses passed the recorded identity and consistency checks. A person still decides whether the findings are correct and what to change.

For example, an AI has written an importer and its normal-path tests pass. To check whether restarting after a crash could import records twice, put the requirements, code, and test results in a packet and run a review.

## Prepare your own packet

Copy [the example](examples/packet.md) and replace its requirements, relevant code (with file names), and tests or known limitations. Describe expected failure/retry behavior and distinguish tested behavior from assumptions. Packets must be UTF-8 Markdown and no larger than 128 KiB. Reviewers only see the material you provide; include any necessary context explicitly.

## Read the result

| Result | Meaning |
| --- | --- |
| `REVIEW_COMPLETED` | Both stages passed identity and consistency checks; a person must assess the findings |
| `FAILED` | The review did not complete; inspect the failure in `result.json` |
| Preflight or argument error | An error appears in the terminal; an output directory may not exist yet |
| No findings | No issue was reported for this packet; it does not prove the code is defect-free |

## Requirements

- Python 3.10 or newer; no third-party Python dependencies.
- macOS or Linux (POSIX). Windows is not supported in this first release.
- OpenCode **v2** with locally saved provider authentication. The CLI checks the major version and required flags before any model request. See the [v2 command reference](https://opencode.ai/v2/docs/cli/commands/).
- Access to the models you select. Real reviews send the packet to your configured providers and can incur usage charges.

OpenCode v1 has a different CLI/configuration protocol and is rejected. Passing the preflight only verifies the CLI version and flags; it does not verify authentication, provider availability, or the model's review quality.

## Quick start

Download or clone this repository, open a terminal in it, then run:

```sh
python3 review.py --check-cli
cp models.example.json models.local.json
```

Edit `models.local.json` to choose models available in your OpenCode account. Each model is `provider/model` or `provider/model#variant`. The example IDs are examples, not a promise of availability for every account. List your available models with `opencode models`.

```sh
mkdir -p runs
python3 review.py --config models.local.json \
  --packet examples/packet.md --output runs/example-001
```

If OpenCode is not in `PATH`, add `--cli /path/to/opencode` to both commands. The output directory must be new, its parent must exist, and its ancestors must not be symlinks. Use a new output name for every run.

Open `runs/example-001/REVIEW.md`, then read `scanner.text.md` and `reviewer.text.md`. The example is a synthetic import function with a retry bug. [Expected findings](examples/expected-findings.md) are hand-written teaching notes, not recorded model output.

## What is checked

- An explicit UTF-8 packet is copied and SHA-256 hashed.
- Each subprocess uses a bounded timeout; failures do not automatically retry.
- Requested provider/model, and variant when explicitly requested, are checked against exported metadata. Observed variants are recorded even when not requested.
- Session IDs, non-empty completed assistant responses, and run/export text consistency are checked.
- Scanner and reviewer agents receive deny-all tool permissions. Exports containing tool calls are rejected.
- Failures produce a failed status when an output directory can be created. An early argument/configuration/output error exits without a completed result.

These checks verify the CLI's reported execution metadata. They do not independently attest a provider's backend model or prove that review findings are true.

## Outputs and boundaries

`REVIEW.md` is the readable index. `result.json` records status, CLI version, model/session metadata, reported cost fields, and errors. The directory also contains the packet, packet hash, both responses, the second-stage input, raw exports, and process logs. Treat these files as potentially sensitive; `runs/` is excluded from Git.

The wrapper uses an environment allowlist and OpenCode's permission configuration. It is **not an operating-system sandbox**. OpenCode runs as your user and can use its own configuration, authentication, logs, and session store. Review runs use a new output directory as their working directory. Input packet contents remain untrusted data in the review instructions.

Authenticate using OpenCode's saved local credentials. Provider API keys supplied only through shell environment variables are intentionally not inherited. The sample GitHub Actions workflow runs offline tests only and requires no model credentials.

`--timeout` is a per-process limit in seconds (default 180), not a total review deadline. The tool does not modify the reviewed project, apply findings, create PR comments, or publish results. There is no automatic redaction: include only material you intend to send to your chosen providers.

Exit codes: `0` for completed and verified execution; `1` for a recorded review failure; `2` for an argument, configuration, preflight-only, or output setup error.

## Offline tests

```sh
python3 -m unittest discover -s tests -v
```

Tests use a fake CLI and synthetic packets. They do not contact any model provider. See [VALIDATION.md](VALIDATION.md) for the separately recorded real CLI/model validation scope.

## Status and license

Experimental v0.1.0 candidate, extracted from a local two-stage review workflow. Start with a small packet and inspect the findings. Contributions should keep the explicit-packet scope and make failure states visible; see [CONTRIBUTING.md](CONTRIBUTING.md).

MIT — see [LICENSE](LICENSE).

## Documentation languages

English and Simplified Chinese documentation cover usage, contribution, changes, validation, the sample packet, teaching notes, and the observed review summary. Switch languages using the links on each page; find the [Chinese sample](examples/packet.zh-CN.md) here. The original English sample remains unchanged to preserve its recorded hash. The Chinese translation has not had a separate live-model run. CLI options, JSON keys, status codes, and generated report headings remain English; documentation explains their meaning in both languages. Model response language depends on your packet and instructions.
