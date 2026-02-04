# Chickenizer

## Overview

Chickenizer is an AI system for analyzing the game of Chicken, a strategic interaction model where players choose between cooperation (swerve) and competition (stay). The system explores how sequential play, strategy specification, and optimal action combinations affect outcomes when players can commit to actions through turn-taking.

The system integrates multiple AI techniques: propositional logic encodes strategy rules and game constraints into a knowledge base; search algorithms find optimal action combinations that maximize a player's outcomes under worst-case opponent behavior; game theory computes Nash equilibria to identify stable strategy pairs; and multi-agent simulation executes sequential games to observe actual outcomes.

This theme suits AI exploration because it requires reasoning about strategic interactions, logical representation of rules and constraints, optimization under uncertainty, and equilibrium analysis. The sequential nature introduces commitment and information asymmetry, while strategy specification demands formal logical encoding. The system addresses cooperation incentives in high-stakes scenarios with potential for mutually negative outcomes, with applications to real-world situations like the ratcheting of political rhetoric.

The five modules work together as follows: Module 1 (Strategy Logic Encoder) provides the foundational knowledge base and validated strategies for all subsequent modules. Module 2 (Optimal Strategy Search) uses these strategies to find best-case worst-case outcomes. Module 3 (Nash Equilibrium Solver) computes theoretical equilibria. Module 4 (Game Engine) simulates actual game play. Module 5 (Analysis & Comparison) synthesizes outputs from all modules to compare theoretical predictions with simulated reality.

## Team

- Greyson Henry
- Will Zoeller

## Proposal

See [PROPOSAL.md](PROPOSAL.md) for the full project proposal.

The proposal outlines Chickenizer as an AI system that analyzes the game of Chicken using propositional logic, search algorithms, game theory, and multi-agent simulation. The system consists of five modules that progressively build from logical strategy encoding to comprehensive analysis comparing theoretical predictions with simulated outcomes.

## Module Plan

Your system must include 5-6 modules. Fill in the table below as you plan each module.

| Module | Topic(s) | Inputs | Outputs | Depends On | Checkpoint |
| ------ | -------- | ------ | ------- | ---------- | ---------- |
| 1 | Propositional Logic (Entailment, Knowledge Bases, Inference Methods, Chaining, CNF, Resolution) | User-defined strategy rules in logical form, action constraints, game rules | Knowledge base in CNF format, validated strategy representation, consistency check results, inferred logical consequences | None | 1 |
| 2 | Search (A*, Uniform Cost, Constraint Satisfaction) | Game structure (payoff matrix, action space, turn order), strategy rules from Module 1, target player, search parameters | Optimal action combination, search path, cost/utility values | Module 1 | 2 |
| 3 | Game theory (Nash equilibrium computation) | Validated strategy pair from Module 1, game structure, equilibrium type preference | Nash equilibria, equilibrium payoffs, optimal response functions, equilibrium existence proof | Module 1 | 3 |
| 4 | Game theory (Sequential games, minimax, game simulation) | Payoff matrix, two strategies from Module 1, turn order, optional strategy parameters | Game outcome record (actions, payoffs, game state trace, turn sequence) | Module 1 | 4 |
| 5 | Analysis techniques, visualization | Optimal combinations from Module 2, Nash equilibria from Module 3, game outcomes from Module 4, strategy metadata | Comparative analysis report, visualization data, insights summary | Modules 1, 2, 3, 4 | 5 |
| 6 (optional) |  |  |  |  |  |

## Repository Layout

```
your-repo/
├── src/                              # main system source code
├── unit_tests/                       # unit tests (parallel structure to src/)
├── integration_tests/                # integration tests (new folder for each module)
├── .claude/skills/code-review/SKILL.md  # rubric-based agent review
├── AGENTS.md                         # instructions for your LLM agent
└── README.md                         # system overview and checkpoints
```

## Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd project-2-ai-system-chickenizer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Dependencies

The system uses the following Python libraries:
- **nashpy**: For Nash equilibrium computation
- **sympy**: For Boolean logic, implications and directionality, KB building
- **numpy**: For numerical operations and matrix handling
- **matplotlib**: For visualization and plotting
- **seaborn**: For enhanced statistical visualizations
- **pytest**: For unit and integration testing

### Environment Variables

No environment variables are currently required. Configuration is handled through module parameters and input files.

## Running

### Running Individual Modules

Each module can be run independently:

```bash
# Module 1: Strategy Logic Encoder & Knowledge Base
python src/module1_kb.py

# Module 2: Optimal Strategy Combination Search
python src/module2_search.py

# Module 3: Nash Equilibrium Solver
python src/module3_equilibrium.py

# Module 4: Chicken Game Engine & Simulation
python src/module4_simulation.py

# Module 5: Strategy Analysis & Comparison
python src/module5_analysis.py
```

### Running Full System Demo

To run a complete demonstration of all modules working together:

```bash
python src/main.py
```

### Example Usage

```bash
# Run with custom strategy rules
python src/module1_kb.py --strategy-rules strategy_config.json

# Run search with specific parameters
python src/module2_search.py --target-player hero --depth-limit 10

# Run simulation with custom payoff matrix
python src/module4_simulation.py --payoff-matrix payoffs.json --turn-order hero
```

## Testing

**Unit Tests** (`unit_tests/`): Mirror the structure of `src/`. Each module should have corresponding unit tests.

**Integration Tests** (`integration_tests/`): Create a new subfolder for each module beyond the first, demonstrating how modules work together.

### Running Tests

Run all unit tests:
```bash
pytest unit_tests/
```

Run all integration tests:
```bash
pytest integration_tests/
```

Run tests for a specific module:
```bash
pytest unit_tests/test_module1.py
pytest integration_tests/module2/
```

Run tests with verbose output:
```bash
pytest -v unit_tests/
```

### Test Data

Test data is included in the test directories:
- **Unit tests**: Each module has test fixtures and mock data in its corresponding test file
- **Integration tests**: Each module integration test folder contains sample strategy configurations, payoff matrices, and expected outputs

Example test data includes:
- Sample strategy rules (logical formulas)
- Payoff matrices for the Chicken game
- Expected knowledge base outputs (CNF clauses)
- Sample game outcomes and traces

## Checkpoint Log

| Checkpoint | Date | Modules Included | Status | Evidence |
| ---------- | ---- | ---------------- | ------ | -------- |
| 1 | Wednesday, Feb 11 | Module 1 |  |  |
| 2 | Thursday, Feb 26 | Module 2 |  |  |
| 3 | Thursday, March 19 | Module 3 |  |  |
| 4 | Thursday, April 2 | Module 4 |  |  |
| 5 | Thursday, April 16 | Module 5 |  |  |

## Required Workflow (Agent-Guided)

Before each module:

1. Write a short module spec in this README (inputs, outputs, dependencies, tests).
2. Ask the agent to propose a plan in "Plan" mode.
3. Review and edit the plan. You must understand and approve the approach.
4. Implement the module in `src/`.
5. Unit test the module, placing tests in `unit_tests/` (parallel structure to `src/`).
6. For modules beyond the first, add integration tests in `integration_tests/` (new subfolder per module).
7. Run a rubric review using the code-review skill at `.claude/skills/code-review/SKILL.md`.

Keep `AGENTS.md` updated with your module plan, constraints, and links to APIs/data sources.

## References

### Libraries and Frameworks

- **nashpy**: Nash equilibrium computation library for Python
  - Documentation: https://nashpy.readthedocs.io/
- **numpy**: Fundamental package for scientific computing with Python
  - Documentation: https://numpy.org/doc/
- **sympy**: Symbol objects for propositional logic
  - Documentation: https://docs.sympy.org/
- **matplotlib**: Comprehensive library for creating static, animated, and interactive visualizations
  - Documentation: https://matplotlib.org/
- **seaborn**: Statistical data visualization library built on matplotlib
  - Documentation: https://seaborn.pydata.org/
- **pytest**: Testing framework for Python
  - Documentation: https://docs.pytest.org/

### Course Materials

- Project Instructions: https://csc-343.path.app/projects/project-2-ai-system/ai-system.project.md
- Code Elegance Rubric: https://csc-343.path.app/rubrics/code-elegance.rubric.md
- Course Schedule: https://csc-343.path.app/resources/course.schedule.md
- Project Rubric: https://csc-343.path.app/projects/project-2-ai-system/ai-system.rubric.md

### Game Theory References

- Nash, J. F. (1950). Equilibrium points in n-person games. Proceedings of the National Academy of Sciences.
- Game of Chicken: A classic game theory model of strategic interaction and cooperation
