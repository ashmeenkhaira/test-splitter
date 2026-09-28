# pytest-timesplit

A pytest plugin that splits your test suite across parallel CI machines using how
long each test actually takes, so every machine finishes at about the same time.

On a fork of Airbyte's Python CDK (4,677 tests, 4 machines), the slowest machine
finished in **288s instead of 392s** with an even split by test count: **26% faster**
(median of 3 runs), at the same CI cost. [Benchmark details](#benchmark-airbyte-python-cdk)

## Why

When tests are split across machines, the CI job is only as fast as the slowest
machine. Splitting by test count ignores that one test can take minutes while
thousands take milliseconds, so whichever machine gets the slow tests holds
everyone up. pytest-timesplit records each test's duration and uses it to balance
the machines.

## Install

```bash
pip install git+https://github.com/ashmeenkhaira/test-splitter
```

pytest finds the plugin automatically once it is installed.

## Usage

**1. Record timings.** Run the whole suite once, without `--shard`:

```bash
pytest
```

This writes `.test-durations.json` to your project root (pytest's rootdir): each
test's ID and its duration in seconds (setup + call + teardown). Commit this file.

**2. Run one shard.** On each machine, say which shard it is and how many there are:

```bash
pytest --shard 1 --num-shards 4
```

GitHub Actions example:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false          # let every shard finish even if one fails
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.13"
      - run: pip install -r requirements.txt    # your project's dependencies
      - run: pip install git+https://github.com/ashmeenkhaira/test-splitter
      - run: pytest --shard ${{ matrix.shard }} --num-shards 4
```

Each shard also saves its own timings to `.test-durations.shard<N>.json`. Add
`.test-durations.shard*.json` to your `.gitignore`.

## How it works

Every machine collects the full list of tests, splits it the same way, and keeps
only its own part. The machines never need to talk to each other, and every test
runs exactly once.

The split is greedy, longest test first: sort the tests by recorded time, then
give each one to the machine with the least total time so far. Five tests on two
machines:

| tests: 8s, 5s, 4s, 3s, 2s | machine A | machine B | slowest |
|---|---|---|---|
| split by count, in order | 8 + 4 + 2 = 14s | 5 + 3 = 8s | 14s |
| timesplit, longest first | 8 + 3 = 11s | 5 + 4 + 2 = 11s | **11s** |

A test with no recorded time (a new test, or no timings file at all) counts as
1 second. With no timings file, this becomes an even split by count.

## Benchmark: Airbyte Python CDK

**Setup.** A [fork](https://github.com/ashmeenkhaira/airbyte-python-cdk/tree/timesplit-bench)
of [airbytehq/airbyte-python-cdk](https://github.com/airbytehq/airbyte-python-cdk),
running Airbyte's own CI test command
(`poetry run coverage run -m pytest -m "not linting and not super_slow and not flaky"`):
4,677 tests on GitHub-hosted `ubuntu-latest` machines. Each run starts three
setups at the same time:

- **1 machine**: the whole suite
- **split by count**: 4 machines, no timings file, so the tests are spread evenly by count
- **timesplit**: 4 machines, using timings recorded in an earlier full run

Each number is the slowest machine's time, from its first log line to pytest's
final summary. It includes checkout and installing dependencies, but not time
spent waiting for GitHub to assign a machine.

| slowest machine | run 1 | run 2 | run 3 | **median** |
|---|---|---|---|---|
| 1 machine | 690s | 901s | 696s | **696s** |
| split by count, 4 machines | 436s | 365s | 392s | **392s** |
| timesplit, 4 machines | 271s | 288s | 297s | **288s** |

- **26% faster** than splitting by count (21–38% across runs, faster in all 3),
  and **2.4× faster** than one machine.
- **Same cost as splitting by count:** 17 / 19 / 18 billed minutes vs 19 / 19 / 18.
  Four machines do cost more than one (12 / 16 / 12), because each machine repeats
  checkout and install.
- **Why not 4× faster?** One test, `test_jsonl_decoder_memory_usage`, takes
  124–231s on its own. No split can finish before its longest test, and
  timesplit's slowest machine was that test plus about 30s of others.
- Workflow: [`bench.yml`](https://github.com/ashmeenkhaira/airbyte-python-cdk/blob/timesplit-bench/.github/workflows/bench.yml)
  · [all runs](https://github.com/ashmeenkhaira/airbyte-python-cdk/actions/workflows/bench.yml)

**Side finding.** Splitting exposed 3 order-dependent tests in the CDK. They pass
when the whole suite runs in order and fail when it is split, the same way in every run:

- `test_source_declarative_w_custom_components.py::test_register_components_from_file_is_gated`
- `test_default_file_based_stream.py::TestFileBasedErrorCollector::test_yield_and_raise_collected`
- `test_default_file_based_stream.py::TestFileBasedErrorCollector::test_collect_parsing_error[Multiple errors]`

The slowest machine in each run passed cleanly, so the times above are unaffected.

## When it doesn't help

On [networkx](https://github.com/networkx/networkx) (10,882 tests, one run),
timesplit's slowest machine took 110s, against 93s for splitting by count:

- The slowest test took 65s in the full run but about 19s in a shard, so its
  recorded time misled the split.
- 91% of its tests take under 10 ms, so an even split by count was already balanced.

Timesplit helps most when a few tests take much longer than the rest and their
times are stable.

## Status and limitations

- Not on PyPI yet; install from GitHub.
- Timings are refreshed only by a full run without `--shard`. Shards save their
  own timings, but merging them back into `.test-durations.json` isn't built yet.
- A partial run (for example `pytest -k login`) overwrites `.test-durations.json`
  with just those tests.
- Not tested together with pytest-xdist.

## Related

[pytest-split](https://github.com/jerry-git/pytest-split) is a mature plugin that
also splits by recorded duration. This project is a from-scratch implementation,
built to learn pytest's plugin hooks and to measure the effect on a real codebase.
