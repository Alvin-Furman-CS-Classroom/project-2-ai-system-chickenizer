# Chickenizer

## System Overview

Chickenizer is an AI system for analyzing the game of Chicken, a strategic interaction model where players choose between cooperation (swerve) and competition (stay). The system explores how sequential play, strategy specification, and optimal action combinations affect outcomes when players can commit to actions through turn-taking.

The system integrates multiple AI techniques: propositional logic encodes strategy rules and game constraints into a knowledge base; search algorithms find optimal action combinations that maximize a player's outcomes under worst-case opponent behavior; game theory computes Nash equilibria to identify stable strategy pairs; and multi-agent simulation executes sequential games to observe actual outcomes.

This theme suits AI exploration because it requires reasoning about strategic interactions, logical representation of rules and constraints, optimization under uncertainty, and equilibrium analysis. The sequential nature introduces commitment and information asymmetry, while strategy specification demands formal logical encoding. The system addresses cooperation incentives in high-stakes scenarios with potential for mutually negative outcomes, with applications to real-world situations like the ratcheting of political rhetoric.

## Modules

### Module 1: Strategy Logic Encoder & Knowledge Base

**Topics:** Propositional Logic (Entailment, Knowledge Bases, Inference Methods, Chaining, CNF, Resolution)

**Input:** User-defined strategy rules in logical form (e.g., "IF villain_last_action = stay THEN hero_action = swerve"), action constraints, game rules.

**Output:** Knowledge base in CNF format (conjunction of disjunctive clauses representing rules), validated strategy representation (logical formulas), consistency check results (true/false with conflict report if false), inferred logical consequences (entailed facts about strategy behavior).

**Integration:** Encodes strategy rules and game constraints logically. Provides validated strategies and knowledge base for Modules 2, 3, and 4. Foundation for all subsequent modules.

**Prerequisites:** Propositional logic course content (entailment, CNF conversion, resolution inference, chaining).

---

### Module 2: Optimal Strategy Combination Search

**Topics:** Search (A*, Uniform Cost, Constraint Satisfaction)

**Input:** Game structure (payoff matrix, action space, turn order), strategy rules (from Module 1 knowledge base), target player (hero or villain), search parameters (depth limit, heuristic weight).

**Output:** Optimal action combination (villain action, hero action) that maximizes target player's payoff under worst-case opponent behavior, search path (sequence of states explored), cost/utility values (optimal payoff achieved, opponent's worst-case payoff).

**Integration:** Uses logical representations from Module 1 to construct valid action combinations. Searches through satisfiable combinations to find best-case worst-case outcomes. Outputs feed into Module 5 for comparison with equilibria and actual outcomes.

**Prerequisites:** Search algorithms course content (A*, uniform cost search, constraint satisfaction), Module 1 completed.

---

### Module 3: Nash Equilibrium Solver

**Topics:** Game theory (Nash equilibrium computation)

**Input:** Validated strategy pair (from Module 1), game structure (payoff matrix, action space), equilibrium type preference (pure, mixed, or both).

**Output:** Nash equilibria (list of equilibrium profiles: action pairs or probability distributions over actions), equilibrium payoffs, optimal response functions (best response mapping for each player), equilibrium existence proof (whether equilibria exist for given strategies).

**Integration:** Uses validated strategies from Module 1. Computes equilibria that Module 5 compares against optimal combinations from Module 2 and game outcomes from Module 4.

**Prerequisites:** Game theory course content (Nash equilibrium definition, existence theorems, computation methods), Module 1 completed.

---

### Module 4: Chicken Game Engine & Simulation

**Topics:** Game theory (sequential games, minimax, game simulation)

**Input:** Payoff matrix (4-tuple: both_swerve, hero_swerves_villain_stays, hero_stays_villain_swerves, both_stay), two strategies (from Module 1), turn order (first player identifier), optional strategy parameters.

**Output:** Game outcome record containing: actions taken (hero action, villain action), final payoffs (hero payoff, villain payoff), game state trace (sequence of states leading to outcome), turn sequence.

**Integration:** Provides the foundational simulation engine using strategies validated in Module 1. Tests strategies and generates actual game outcomes. Outputs feed into Module 5 for comparison against equilibria (Module 3) and optimal search results (Module 2).

**Prerequisites:** Game theory course content (sequential games, minimax, game simulation), Module 1 completed.

---

### Module 5: Strategy Analysis & Comparison

**Topics:** Analysis techniques, visualization

**Input:** Optimal combinations (from Module 2: best-case worst-case action pairs), Nash equilibria (from Module 3: equilibrium profiles and payoffs), game outcomes (from Module 4: multiple runs with different strategy pairs), strategy metadata (strategy names, descriptions).

**Output:** Comparative analysis report (equilibrium vs actual outcomes, optimal vs equilibrium payoffs, strategy effectiveness rankings), visualization data (payoff comparisons, strategy interaction matrices, outcome distributions), insights summary (when strategies match equilibria, when optimal search differs from equilibrium).

**Integration:** Synthesizes outputs from Modules 1, 2, 3, and 4 into unified analysis. Provides final system output comparing theoretical predictions (equilibria, optimal search) with simulated reality.

**Prerequisites:** Modules 1, 2, 3, and 4 completed, data analysis basics (comparison, ranking, basic visualization).

---

## Feasibility Study

_A timeline showing that each module's prerequisites align with the course schedule. Verify that you are not planning to implement content before it is taught._

| Module | Required Topic(s) | Topic Covered By | Checkpoint Due |
| ------ | ----------------- | ---------------- | -------------- |
| 1      | Propositional Logic (CNF, Resolution, Chaining) | Weeks 1-1.5 (Propositional Logic) | Wednesday, Feb 11 (Checkpoint 1) |
| 2      | Search (A*, Uniform Cost, Constraint Satisfaction) | Weeks 1.5-3 (Uninformed & Informed Search) | Thursday, Feb 26 (Checkpoint 2) |
| 3      | Game theory (Nash equilibrium) | Weeks 5.5-7 (Games and Game Theory) | Thursday, March 19 (Checkpoint 3) |
| 4      | Game theory (Sequential games, simulation) | Weeks 5.5-7 (Games and Game Theory) | Thursday, April 2 (Checkpoint 4) |
| 5      | Analysis techniques | General analysis methods | Thursday, April 16 (Checkpoint 5) |

## Coverage Rationale

Chickenizer requires these topics because strategic interaction analysis demands multiple complementary AI techniques. Propositional Logic (Module 1) enables formal encoding of strategy rules and game constraints, allowing logical reasoning about valid action combinations. Search (Module 2) finds optimal action pairs by exploring the space of satisfiable combinations—this is non-trivial search because we optimize under adversarial constraints (worst-case opponent behavior), requiring sophisticated heuristics.

Game theory (Modules 3 and 4) provides the foundational framework for understanding strategic interactions and computing equilibria. Module 3 computes Nash equilibria to identify stable strategy pairs, while Module 4 simulates sequential games to observe actual outcomes when players interact.

The trade-off is complexity vs. scope: focusing on one game (Chicken) allows deeper exploration of each AI technique rather than shallow coverage across many games. The sequential nature (turn-taking) adds commitment and information asymmetry beyond basic simultaneous games, making equilibrium analysis more interesting while remaining computationally tractable. Propositional Logic and Search are natural fits because strategies are rule-based (logical encoding) and optimization requires systematic exploration (search algorithms).
