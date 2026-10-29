
# AgentFault Lab

AgentFault Lab is a research-inspired project for evaluating AI agent reliability under controlled tool failures.

## Current Features

- Simulated business tool
- Timeout and rate-limit failure scenarios
- Malformed response simulation
- Deterministic response validation
- Automated tests using pytest

## Tech Stack

- Python
- pytest
- FastAPI (planned)
- HTTPX (planned)

## Run Locally

From the project root, activate the virtual environment and run:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
```

## Research Question

How do different recovery strategies affect task success, safety, latency, and cost under tool failures?

## Development Status

**Day 1:** Fault simulator and five automated tests implemented.

## Planned Features

- Agent task execution
- Configurable fault injection
- Bounded retries and recovery strategies
- Execution tracing
- Repeatable reliability benchmarks

## Current Limitations

No autonomous agent, recovery engine, benchmark results, or production deployment has been implemented yet.
