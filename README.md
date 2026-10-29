
# AgentFault Lab

AgentFault Lab is a Python-based project that tests AI agent reliability by simulating tool failures, validating responses, and evaluating recovery strategies through automated testing and measurable experiments.

## Current Features

- Simulated business tool
- Timeout and rate-limit failure scenarios
- Malformed response simulation
- Deterministic response validation
- Automated tests using pytest

## Technology Stack

- Python
- pytest
- FastAPI (planned)
- HTTPX (planned)

## Run Locally

Activate the virtual environment, then run:

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
