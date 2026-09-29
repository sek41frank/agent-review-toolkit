# Candidate validation

[English](VALIDATION.md) | [简体中文](VALIDATION.zh-CN.md)

This records observed results separately from intended compatibility.

## Environment and CLI preflight

- Date: 2026-09-29.
- Platform: macOS; Python 3.12.14.
- Actual CLI output: `opencode v2.0.19`.
- Candidate `--check-cli` completed successfully; required run/export flags were present.

## Offline tests

`python3 -B -m unittest discover -s tests -v`: **23 tests passed** locally.

These use a fake CLI and synthetic inputs. Coverage includes two-stage success, session/model/text mismatch, absent/incomplete output, tool-call rejection, timeouts, output preservation, configuration parsing, optional model variant, relative CLI resolution, v1/incompatible CLI rejection, FIFO rejection, interruption cleanup, preflight descendant cleanup, and failure-report link integrity.

An independent local review also reproduced the FIFO and interruption boundaries with real local processes: non-regular packet/config files were rejected promptly, and a model-like child process was terminated after Ctrl-C. No unresolved high-priority findings remained in that local code review.

## Real synthetic-packet smoke run

The candidate ran both stages against real configured providers using only `examples/packet.md`.

- Final status: `REVIEW_COMPLETED`.
- Scanner requested and exported metadata: `deepseek/deepseek-flash#low`.
- Reviewer requested and exported metadata: `opencode/claude-sonnet-5#medium`.
- Both stages: `VERIFIED` by the wrapper's model/session/text checks.
- Packet SHA-256: `3cdd0ca87155671264a2c95992adf74ced1d8bc63f569cf3d0f1db3982e3d399`.
- Reviewed wrapper SHA-256: `a03037ca999d5cd6b9f7af07d7d74fcd247510bf596c459467a84650105aadd3`.
- Both responses identified the example's crash/retry and same-batch duplicate-ID failures. See [observed summary](examples/observed-review-summary.md).

This is one observed run, not a promise of model availability or deterministic findings. Model identities here are the CLI's exported metadata. Raw session exports and logs are kept out of the public candidate.

## Remaining validation limits

- GitHub CI has not run. The proposed macOS/Linux and Python 3.10/3.12 matrix is not yet verified across all combinations.
- Other OpenCode v2 patch versions and providers were not tested live.
- The real synthetic smoke above ran before the final probe/report fixes. The final revision passed all 23 offline tests and a fresh real CLI preflight; the live model pair was not rerun after these local fixes.

- The Chinese example is a companion translation; no separate live-model run was performed on it.

## Authorized source cross-review

The source review packet was reviewed read-only by `deepseek/deepseek-flash#low` and `opencode/claude-sonnet-5#medium`. Both exported identities and responses passed verification. No tool calls were allowed. Packet SHA-256: `bef08696c3e5f38eda67ab761e34003be5a3808363ee294ac58f2bc459b762d4`.

Two accepted findings were fixed afterward: preflight timeout/interruption must terminate the process group, and failed review indexes must not link to absent artifacts. Three regression tests were added. A claim about unbounded POSIX `subprocess.run` communication was not confirmed; the actual accepted defect was descendant cleanup. Other speculative observations were not treated as confirmed defects.

Final source SHA-256: `15fd39c1672b62a9639f509ce0daa5bb5dc986bce9ad1b78961a1958700649e6`. The external models reviewed the preceding revision; the final patch passed independent local incremental review, including all three new tests. Review completion is not automatic release approval.
