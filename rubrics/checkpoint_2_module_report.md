# Checkpoint 2 Module Report

**Date**: February 26, 2026  
**Module**: Module 2 (Optimal Strategy Search)  
**Checkpoint**: 2 of 5

---

## Summary

Module 2 implements depth-limited minimax search for optimal strategy selection in the Chicken game. The implementation is functional and demonstrates solid understanding of adversarial search concepts. The main gaps are: the module is embedded within `strategies.py` rather than being a standalone module, integration tests are missing, and the connection to Module 1's Knowledge Base output is not explicitly demonstrated.

---

## Part 1: Source Code Review (27 points)

### 1.1 Functionality (8 points)

| Score | 6/8 |
|-------|-----|

**What Works:**
- `MinimaxStrategy` implements depth-limited minimax search correctly
- Resilience-based evaluation function (`_evaluate_state`) works for both players
- Terminal state detection checks HP and resilience threshold
- All 126 unit tests pass, including minimax-specific tests

**Evidence:**
```python
# From strategies.py - MinimaxStrategy correctly implements minimax
def decide(self, gamestate: Dict[str, Any]) -> bool:
    best_value = float("-inf")
    best_action = False
    
    for my_action in (False, True):
        value = self._min_value(gamestate, my_action, self.depth)
        if value > best_value:
            best_value = value
            best_action = my_action
    
    return best_action
```

**Issues:**
- Module 2 is not a standalone file (`module2_search.py` does not exist)
- Search is embedded in strategy system rather than being a separate search module
- No explicit A*, Uniform Cost, or CSP implementations as listed in module plan

---

### 1.2 Code Elegance and Quality (7 points)

| Score | 5/7 |
|-------|-----|

See `checkpoint_2_elegance_report.md` for detailed analysis.

**Summary:** Code quality is solid with clear structure and good naming. Average elegance score of 3.0/4.0 maps to 5/7 points.

---

### 1.3 Documentation (4 points)

| Score | 3/4 |
|-------|-----|

**Strengths:**
- Module-level docstrings in `strategies.py` explain purpose
- Class docstrings describe strategy behaviors
- Method docstrings include Args and Returns sections
- Type hints present on most public methods

**Evidence:**
```python
class MinimaxStrategy(Strategy):
    """Depth-limited minimax strategy assuming resilience-based zero-sum game.
    
    This strategy maximizes the resilience differential U = R1 - R2 from the
    perspective of the configured player. The opponent is assumed to choose
    actions that minimize this value. Depth is measured in full rounds.
    """
```

**Issues:**
- Some helper methods lack docstrings (`_load_engine_class`)
- Type hints inconsistent in some areas
- No explicit I/O documentation for Module 2 as a whole (unlike Module 1)

---

### 1.4 I/O Clarity (3 points)

| Score | 2/3 |
|-------|-----|

**What's Clear:**
- Strategy inputs: `gamestate: Dict[str, Any]`
- Strategy outputs: `bool` (True = stay, False = swerve)
- `GameSimulator.simulate()` clearly documents its return structure

**Issues:**
- Module 2's boundary is unclear—is it `MinimaxStrategy` alone or the entire strategy system?
- README lists Module 2 inputs as "Game structure, strategy rules from Module 1" but KB integration isn't explicit
- No dedicated module file with I/O specification like Module 1 has

**From README (expected):**
> **Inputs**: Game structure (payoff matrix, action space, turn order), strategy rules from Module 1, target player, search parameters  
> **Outputs**: Optimal action combination, search path, cost/utility values

**Actual Implementation:**
- Input: gamestate dictionary (not explicitly from Module 1 KB)
- Output: boolean action (no search path or explicit utility values returned)

---

### 1.5 Topic Engagement (5 points)

| Score | 4/5 |
|-------|-----|

**Strengths:**
- **Minimax search** is correctly implemented with depth limiting
- Demonstrates understanding of adversarial search (max/min alternation)
- Evaluation function based on resilience differential
- Terminal state detection for search cutoff

**Evidence of engagement:**
```python
def _min_value(self, state, my_action, depth) -> float:
    """Opponent chooses an action that minimizes our eventual utility."""
    values = []
    for opp_action in (False, True):
        next_state = self._simulate_round(state, my_action, opp_action)
        if depth == 1 or self._is_terminal(next_state):
            values.append(self._evaluate_state(next_state))
        else:
            values.append(self._max_value(next_state, depth - 1))
    return min(values)
```

**Issues:**
- Module plan mentions "A*, Uniform Cost, Constraint Satisfaction" but only minimax is implemented
- No alpha-beta pruning optimization (though not required)
- Search doesn't explicitly use KB constraints from Module 1

---

### Part 1 Subtotal: 20/27

---

## Part 2: Testing Review (15 points)

### 2.1 Test Coverage and Design (6 points)

| Score | 4/6 |
|-------|-----|

**Unit Test Coverage:**
- `test_strategies.py`: 13 tests covering all strategy classes
- `test_engine.py`: 38 tests covering GameEngine functionality
- MinimaxStrategy tests: depth validation, behavior against known strategies

**Evidence:**
```python
class TestMinimaxStrategy:
    def test_minimax_depth_validation(self):
        with pytest.raises(ValueError, match="depth must be >= 1"):
            MinimaxStrategy("p1", depth=0)

    def test_minimax_prefers_stay_against_always_swerve(self):
        """Against an always-swerve opponent, minimax should learn to stay."""
        engine = GameEngine()
        minimax = MinimaxStrategy("p1", depth=2)
        action = minimax(engine.get_gamestate())
        assert action is True
```

**Critical Gap:**
- **Integration tests are empty**: `integration_tests/integration_tests.py` contains only `print("Hello, World!")`
- No tests showing Module 2 using Module 1's KB output
- Required for modules beyond the first per project instructions

---

### 2.2 Test Quality and Correctness (5 points)

| Score | 4/5 |
|-------|-----|

**Strengths:**
- All 126 tests pass
- Tests verify behavior, not implementation details
- Meaningful assertions (not trivial)
- Test isolation maintained

**Evidence of quality tests:**
```python
def test_minimax_vs_always_swerve_resilience_increases(self):
    """Minimax vs always-swerve should lead to positive resilience_diff for p1."""
    sim = GameSimulator(engine=engine)
    p1 = MinimaxStrategy("p1", depth=2)
    p2 = AlwaysSwerveStrategy("p2")
    result = sim.simulate(p1, p2, max_rounds=5)
    
    assert result["final_state"]["resilience_diff"] > 0
    assert result["final_state"]["p1_resilience"] > result["final_state"]["p2_resilience"]
```

**Minor Issues:**
- Some tests could have more descriptive names
- Edge case coverage for minimax could be expanded (e.g., deeper depths, various opponent strategies)

---

### 2.3 Test Documentation and Organization (4 points)

| Score | 3/4 |
|-------|-----|

**Strengths:**
- Tests organized into logical classes (`TestBasicStrategiesBehavior`, `TestMinimaxStrategy`, etc.)
- Test file docstrings explain coverage
- Test class docstrings describe purpose

**Issues:**
- Import workarounds due to `.src` directory naming
- Integration test directory structure exists but is unused

---

### Part 2 Subtotal: 11/15

---

## Part 3: GitHub Practices (8 points)

### 3.1 Commit Quality and History (4 points)

| Score | 3/4 |
|-------|-----|

**Strengths:**
- Commits show logical progression of work
- Most messages explain what changed

**Recent Commits:**
```
4bf49d3 implemented player preference into gamestate, refined strategies, implemented minimax.
b6b0625 strategy renderer and game engine more or less complete
6de43fc Tweaked tit-for-tat for proper functionality
505911c Redone strategy objects + proof-of-concept
578210e Basic game engine for gamestate gen + some unit tests
```

**Issues:**
- Some messages are vague or unprofessional: "as if this file matters anyway"
- Commits could be more granular (multiple features in single commit)

---

### 3.2 Collaboration Practices (4 points)

| Score | 2/4 |
|-------|-----|

**Observations:**
- Only `main` branch used locally
- `feedback` branch exists on remote but not used for integration
- No evidence of pull requests or code review
- Work appears committed directly to main

**Recommendations:**
- Create feature branches for new work
- Use pull requests for code review between team members
- Document PR discussions for checkpoint evidence

---

### Part 3 Subtotal: 5/8

---

## Total Score

| Section | Score | Max | Percentage |
|---------|-------|-----|------------|
| Part 1: Source Code | 20 | 27 | 74% |
| Part 2: Testing | 11 | 15 | 73% |
| Part 3: GitHub | 5 | 8 | 63% |
| **Total** | **36** | **50** | **72%** |

---

## Action Items

### Must Fix Before Submission

- [ ] **Create integration tests** in `integration_tests/module2/`:
  ```python
  # Example: test_minimax_integration.py
  def test_minimax_with_game_simulation():
      """Test MinimaxStrategy in full game simulation."""
      sim = GameSimulator()
      p1 = MinimaxStrategy("p1", depth=3)
      p2 = TitForTatStrategy("p2")
      result = sim.simulate(p1, p2, max_rounds=10)
      assert result["summary"]["rounds_played"] == 10
  ```

- [ ] **Clarify Module 2 boundaries**: Add a `module2_search.py` wrapper or document in README how `strategies.py` + `engine.py` constitute Module 2

### Should Fix

- [ ] **Use pull requests**: Create a branch for checkpoint work with team review
- [ ] **Update module plan**: Reflect actual implementation (minimax) vs planned (A*, UCS, CSP)
- [ ] **Rename `.src` to `src`**: Match README documentation and eliminate import workarounds

### Recommended

- [ ] Document how Module 2 could use Module 1's KB for strategy validation
- [ ] Add alpha-beta pruning to minimax (optimization, not required)
- [ ] Expand minimax test coverage with more opponent strategy variations

---

## Questions for Team

1. **Is minimax the complete Module 2 implementation?** The module plan mentions A*, UCS, and CSP—should this be updated?

2. **How will Module 2 integrate with Module 1's KB?** Currently, strategies don't explicitly use KB validation.

3. **Are both team members visible in commit history?** Ensure substantive contributions from both Greyson and Will are evident.
