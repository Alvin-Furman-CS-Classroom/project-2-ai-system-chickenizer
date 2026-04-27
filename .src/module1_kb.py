# Module 1: Strategy Logic Encoder, Knowledge Base
"""Strategy Logic Encoder and Knowledge Base for the Chickenizer system.

Provides KnowledgeBase (tell/ask, CNF, forward/backward chaining) and ChickenKB
for encoding game strategies and outcomes in propositional logic.

Input:
    - Strategy rules: List of SymPy expressions representing logical formulas
      Example: [sp.Implies(p1_stays, p2_swerves), p1_stays]
    - Action constraints: Logical constraints on player actions
      Example: [sp.Or(p1_stays, p1_swerves)]  # Player must choose one action
    - Game rules: Rules defining game outcomes and relationships
      Example: [sp.Equivalent(collision, sp.And(p1_stays, p2_stays))]

Output:
    - Knowledge base in CNF format: Conjunction of disjunctive clauses
      Example: "p1_stays, (p1_stays -> p2_swerves)"
    - Validated strategy representation: Logical formulas with consistency check
    - Consistency check results: Tuple (is_satisfiable: bool, conflict_report: Optional[ConflictReport])
      Example: (True, None) for satisfiable KB, (False, ConflictReport(...)) for conflicts
    - Inferred logical consequences: List of all entailed facts
      Example: [p1_stays, p2_swerves] when KB contains p1_stays and (p1_stays -> p2_swerves)

Next Module Feed:
    - Validated KB (KnowledgeBase or ChickenKB instance) passed to Module 2 (Search)
    - Module 2 uses KB to generate valid action combinations for optimal strategy search
    - KB provides constraint checking: only satisfiable action combinations are explored
"""

# Dependencies:
import sympy as sp
from typing import Any, Callable, List, Optional, cast
from dataclasses import dataclass

# No-op logger: ignores all logging when kb_logger cannot be loaded
class _NoOpLogger:
    """Dummy logger that ignores every call. Used when kb_logger.py is unavailable."""

    def debug(self, msg, *args, **kwargs):
        pass

    def info(self, msg, *args, **kwargs):
        pass

    def warning(self, msg, *args, **kwargs):
        pass

    def error(self, msg, *args, **kwargs):
        pass

# start of logger loading - generated with the help of the Cursor agent and modified to fit the needs of the project.
try:
    from debug_logger import get_debug_logger
    _logger = get_debug_logger("module1_kb")
except (ImportError, FileNotFoundError, OSError):
    # try to load debug_logger.py from .src directory when running from test files
    try:
        import importlib.util
        import os
        _src_dir = os.path.dirname(os.path.abspath(__file__))
        _logger_path = os.path.join(_src_dir, "debug_logger.py")
        _spec = importlib.util.spec_from_file_location("debug_logger", _logger_path)
        if _spec is None or _spec.loader is None:
            _logger = _NoOpLogger()
        else:
            _log_mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_log_mod)
            # Dynamic import: attribute access trips pyright ``ModuleType.__getattr__``; cast factory.
            _factory = getattr(_log_mod, "get_debug_logger", None)
            if _factory is None:
                _logger = _NoOpLogger()
            else:
                _dbg_factory = cast(Callable[[str], Any], _factory)
                _logger = _dbg_factory("module1_kb")
    # ensure no crashes occur if debug_logger.py is not found
    except (ImportError, FileNotFoundError, OSError):
        _logger = _NoOpLogger()
# end of logger loading

@dataclass
class ConflictReport:
    """Report identifying conflicting clauses in an unsatisfiable knowledge base.
    
    Attributes:
        conflicting_clauses: List of clauses that are part of the conflict
        conflict_type: Type of conflict ("direct", "chain", "minimal", "all")
        description: Human-readable description of the conflict
    """

    conflicting_clauses: List[sp.Basic]
    conflict_type: str
    description: str
    
    def __str__(self) -> str:
        """Return human-readable conflict description."""
        clause_strs = [_clause_to_str(c) for c in self.conflicting_clauses]
        return f"{self.description}: {', '.join(clause_strs)}"


class KnowledgeBase:
    """Propositional logic knowledge base with tell/ask, CNF, and forward/backward chaining."""

    def __init__(self):
        """Initialize empty knowledge base with clauses list and SymPy And structure."""

        self.clauses = []
        self.clauses_for_rendering = []

        # CNF knowledge base: top-level AND of clauses (each clause is OR of literals)
        self.kb = sp.And()
        
        _logger.debug(f"Initialized {self.__class__.__name__} with empty KB")

    def _require_expr(self, value: object, *, name: str) -> sp.Basic:
        """Validate that a value is a SymPy object (Boolean formula, Symbol, etc.).

        Args:
            value: Candidate value.
            name: Parameter name for error messages.

        Returns:
            The value cast as a SymPy object.

        Raises:
            TypeError: If value is not a SymPy object.
        """

        if not isinstance(value, sp.Basic):
            _logger.error(f"TypeError: {name} must be a sympy object (sp.Basic), got {type(value).__name__}")
            raise TypeError(f"{name} must be a sympy object (sp.Basic), got {type(value).__name__}")
        return value

    def _require_expr_list(self, value: object, *, name: str) -> list[sp.Basic]:
        """Validate that a value is a list of SymPy objects.

        Args:
            value: Candidate value.
            name: Parameter name for error messages.

        Returns:
            The value cast as a list of SymPy objects.

        Raises:
            TypeError: If value is not a list, or any element is not a SymPy object.
        """

        if not isinstance(value, list):
            _logger.error(f"TypeError: {name} must be a list[sp.Basic], got {type(value).__name__}")
            raise TypeError(f"{name} must be a list[sp.Basic], got {type(value).__name__}")
        for i, item in enumerate(value):
            if not isinstance(item, sp.Basic):
                _logger.error(f"TypeError: {name}[{i}] must be a sympy object (sp.Basic), got {type(item).__name__}")
                raise TypeError(f"{name}[{i}] must be a sympy object (sp.Basic), got {type(item).__name__}")
        return value

    def tell(self, clauses: list[sp.Basic]) -> None:
        """Add clauses to the knowledge base and rebuild the internal KB.

        Args:
            clauses: List of SymPy objects (facts or rules) to add.

        Returns:
            None.
        """

        clauses = self._require_expr_list(clauses, name="clauses")

        _logger.debug(f"tell(): Adding {len(clauses)} clause(s) to KB")
        for i, clause in enumerate(clauses):
            _logger.debug(f"  Clause {i+1}: {_clause_to_str(clause)}")
        
        self.clauses.extend(clauses)
        self.clauses_for_rendering.extend(clauses)

        _logger.debug(f"KB now has {len(self.clauses)} total clause(s)")
        self.rebuild_kb()

    def ask(self, query: sp.Basic) -> bool:
        """Check if knowledge base entails given query.

        Args:
            query: A SymPy object to check for entailment.

        Returns:
            True if KB entails query, False otherwise.
        """

        query = self._require_expr(query, name="query")
        _logger.debug(f"ask(): Checking if KB entails query: {_clause_to_str(query)}")
        _logger.debug(f"  - KB has {len(self.clauses)} clause(s)")
        
        result = not sp.satisfiable(sp.And(self.kb, sp.Not(query)))
        _logger.info(f"ask(): KB {'entails' if result else 'does not entail'} query: {_clause_to_str(query)}")
        return result

    def rebuild_kb(self) -> None:
        """Rebuild the internal KB (SymPy And) from the current clauses list.

        Returns:
            None.
        """

        if not self.clauses:
            self.kb = sp.And()
            _logger.debug("rebuild_kb(): Rebuilt empty KB")
        else:
            self.kb = sp.And(*self.clauses)
            _logger.debug(f"rebuild_kb(): Rebuilt KB with {len(self.clauses)} clause(s)")

    def validate_kb(self) -> tuple[bool, Optional[ConflictReport]]:
        """Check whether the knowledge base is satisfiable (no contradiction).

        Returns:
            Tuple of (is_satisfiable: bool, conflict_report: Optional[ConflictReport]).
            If satisfiable, returns (True, None).
            If unsatisfiable, returns (False, ConflictReport) identifying conflicting clauses.
        """
        _logger.debug(f"validate_kb(): Checking satisfiability of KB with {len(self.clauses)} clause(s)")
        
        if sp.satisfiable(self.kb):
            _logger.info("validate_kb(): KB is satisfiable (no conflicts)")
            return (True, None)
        
        # KB is unsatisfiable - identify conflicts using iterative removal
        _logger.warning("validate_kb(): KB is unsatisfiable (conflicts detected)")
        conflict_report = self._find_minimal_conflict()
        _logger.warning(f"validate_kb(): Conflict report: {conflict_report}")
        return (False, conflict_report)
    
    def _find_minimal_conflict(self) -> ConflictReport:
        """Find minimal set of conflicting clauses using iterative removal.
        
        Strategy: Try removing each clause one by one. If removing a clause
        makes the KB satisfiable, that clause is part of the conflict.
        
        Returns:
            ConflictReport identifying the conflicting clauses.
        """
        _logger.debug("_find_minimal_conflict(): Starting conflict detection")
        
        # First, check for obvious direct contradictions (p and ~p)
        direct_conflict = self._check_direct_contradiction()
        if direct_conflict:
            _logger.debug(f"find_minimal_conflict(): Found direct contradiction: {direct_conflict}")
            return direct_conflict
        
        # Check for chain contradictions (p -> q, p, ~q)
        chain_conflict = self._check_chain_contradiction()
        if chain_conflict:
            _logger.debug(f"find_minimal_conflict(): Found chain contradiction: {chain_conflict}")
            return chain_conflict
        
        # Use iterative removal to find minimal conflict set
        _logger.debug(f"_find_minimal_conflict(): Using iterative removal on {len(self.clauses)} clauses")
        conflicting_indices = []
        
        # Try removing each clause to see if KB becomes satisfiable
        for i in range(len(self.clauses)):
            test_clauses = self.clauses[:i] + self.clauses[i+1:]
            if not test_clauses:
                # Empty KB is satisfiable
                conflicting_indices.append(i)
                _logger.debug(f"_find_minimal_conflict(): Clause {i} causes conflict (empty KB when removed)")
                continue
            
            test_kb = sp.And(*test_clauses)
            if sp.satisfiable(test_kb):
                # Removing this clause makes KB satisfiable, so it's part of conflict
                conflicting_indices.append(i)
                _logger.debug(f"_find_minimal_conflict(): Clause {i} ({_clause_to_str(self.clauses[i])}) is part of conflict")
        
        if conflicting_indices:
            conflicting_clauses = [self.clauses[i] for i in conflicting_indices]
            if len(conflicting_indices) == 1:
                conflict_type = "minimal"
                description = "Minimal conflict: single conflicting clause"
            else:
                conflict_type = "minimal"
                description = f"Minimal conflict: {len(conflicting_indices)} conflicting clauses"
            _logger.debug(f"_find_minimal_conflict(): Found {len(conflicting_indices)} conflicting clause(s)")
        else:
            # All clauses are needed for conflict (rare case)
            conflicting_clauses = self.clauses.copy()
            conflict_type = "all"
            description = "All clauses participate in conflict"
            _logger.debug("_find_minimal_conflict(): All clauses participate in conflict")
        
        return ConflictReport(
            conflicting_clauses=conflicting_clauses,
            conflict_type=conflict_type,
            description=description
        )
    
    def _check_direct_contradiction(self) -> Optional[ConflictReport]:
        """Check for direct contradictions (p and ~p).
        
        Returns:
            ConflictReport if direct contradiction found, None otherwise.
        """
        _logger.debug("Checking for direct contradictions")
        symbols = {}
        for clause in self.clauses:
            if isinstance(clause, sp.Symbol):
                symbols[clause] = clause
            elif isinstance(clause, sp.Not) and isinstance(clause.args[0], sp.Symbol):
                negated_symbol = clause.args[0]
                if negated_symbol in symbols:
                    # Found direct contradiction: symbol and its negation
                    _logger.debug(f"   - Found direct contradiction: {negated_symbol} and ~{negated_symbol}")
                    return ConflictReport(
                        conflicting_clauses=[symbols[negated_symbol], clause],
                        conflict_type="direct",
                        description="Direct contradiction"
                    )
        _logger.debug("   - No direct contradictions found")
        return None
    
    def _check_chain_contradiction(self) -> Optional[ConflictReport]:
        """Check for chain contradictions (p -> q, p, ~q).
        
        Returns:
            ConflictReport if chain contradiction found, None otherwise.
        """
        _logger.debug("Checking for chain contradictions")
        # Build sets for quick lookup
        facts = set()
        negations = {}
        
        for clause in self.clauses:
            if isinstance(clause, sp.Symbol):
                facts.add(clause)
            elif isinstance(clause, sp.Not) and isinstance(clause.args[0], sp.Symbol):
                negations[clause.args[0]] = clause
        
        _logger.debug(f"    Found {len(facts)} fact(s) and {len(negations)} negation(s)")
        
        # Check each implication
        for clause in self.clauses:
            if isinstance(clause, sp.Implies):
                antecedent = clause.args[0]
                consequent = clause.args[1]
                
                # Check if we have: (antecedent -> consequent), antecedent, ~consequent
                has_antecedent = antecedent in facts
                has_neg_consequent = consequent in negations
                
                if has_antecedent and has_neg_consequent:
                    conflicting = [clause, antecedent, negations[consequent]]
                    _logger.debug(f"    - Found chain contradiction: {_clause_to_str(clause)}, {_clause_to_str(antecedent)}, {_clause_to_str(negations[consequent])}")
                    return ConflictReport(
                        conflicting_clauses=conflicting,
                        conflict_type="chain",
                        description="Contradiction through logical chain"
                    )
        
        _logger.debug("   - No chain contradictions found")
        return None

    def is_cnf(self) -> bool:
        """Check if knowledge base is in CNF (Conjunctive Normal Form).

        Returns:
            True if every clause is a disjunction of literals (sp.Or) or a single literal.
        """
        # CNF: top-level AND of clauses; each clause is OR of literals OR a literal itself.
        def _is_literal(expr: sp.Basic) -> bool:
            return isinstance(expr, sp.Symbol) or (isinstance(expr, sp.Not) and isinstance(expr.args[0], sp.Symbol))

        def _is_clause(expr: sp.Basic) -> bool:
            if _is_literal(expr):
                return True
            if isinstance(expr, sp.Or):
                return all(_is_literal(arg) for arg in expr.args)
            return False

        return all(_is_clause(clause) for clause in self.clauses)

    def to_cnf(self) -> None:
        """Convert the knowledge base to Conjunctive Normal Form in place.

        Returns:
            None.
        """

        self.kb = sp.to_cnf(self.kb)
        self.clauses = [clause for clause in self.kb.args]

    def render_kb(self) -> str:
        """Render the knowledge base as a human-readable string.

        Returns:
            A string representation of the knowledge base.
        """

        pieces = [_clause_to_str(c) for c in self.clauses_for_rendering]
        return ", ".join(pieces)

    def backward_chain(self, query: sp.Basic, visited=None) -> list[sp.Basic]:
        """Backward chain from the query goal back to supporting facts.

        Args:
            query: SymPy object that is the goal to prove.
            visited: Set of already-visited goals (used internally to avoid cycles).

        Returns:
            List of clauses from facts to query that form a proof path, or [] if not derivable.
        """
        query = self._require_expr(query, name="query")

        if visited is None:
            visited = set()
            _logger.debug(f"Starting backward_chain() for query: {_clause_to_str(query)}")
        
        if query in visited:
            _logger.debug(f"backward_chain(): Query {_clause_to_str(query)} already visited (cycle detected), returning empty")
            return []

        visited.add(query)
        
        # Base case
        if query in self.clauses:
            _logger.debug(f"backward_chain(): Query {_clause_to_str(query)} is a direct fact")
            return [query]

        matching_rules = [c for c in self.clauses if isinstance(c, sp.Implies) and c.args[1] == query]
        _logger.debug(f"backward_chain(): Found {len(matching_rules)} rule(s) with consequent matching query")
        
        for rule in matching_rules:
            antecedent, consequent = rule.args
            if consequent != query:
                continue

            if isinstance(antecedent, sp.And):
                _logger.debug(f"backward_chain(): Rule has conjunctive antecedent: {_clause_to_str(antecedent)}")
                subpaths: list[sp.Basic] = []
                for a in antecedent.args:
                    p = self.backward_chain(a, visited)
                    if not p:
                        _logger.debug(f"backward_chain(): Could not prove antecedent part: {_clause_to_str(a)}")
                        break
                    subpaths.extend(p)
                else:
                    _logger.debug(f"backward_chain(): Successfully proved all antecedent parts, returning path")
                    return subpaths + [rule]
            else:
                _logger.debug(f"backward_chain(): Trying to prove antecedent: {_clause_to_str(antecedent)}")
                recur_path = self.backward_chain(antecedent, visited)
                if recur_path:
                    _logger.debug(f"backward_chain(): Successfully proved antecedent, returning path")
                    return recur_path + [rule]

        _logger.warning(f"backward_chain(): Could not prove query: {_clause_to_str(query)}")
        return []

    def forward_chain_derive_query(self, query: sp.Basic) -> list[sp.Basic]:
        """Forward chain from known facts to derive the query if possible.

        Args:
            query: SymPy object that is the goal to derive.

        Returns:
            List of clauses (implications) that were used to derive query, or [] if not derivable.
        """
        query = self._require_expr(query, name="query")
        return self.forward_chain(query)

    def infer_consequences(self) -> List[sp.Basic]:
        """Infer all logical consequences from the knowledge base.
        
        Uses forward chaining to derive all possible facts from the current KB.
        Supports both simple and conjunctive antecedents in implications.
        
        Returns:
            List of all entailed facts (atoms) that can be derived from the KB.
        """
        return self.forward_chain()
    

    def forward_chain(self, query: Optional[sp.Basic] = None) -> list[sp.Basic]:
        """
        Forward chain from known facts. Used by forward_chain_derive_query() and infer_consequences() for different purposes.

        Args:
            query: SymPy object that is the goal to derive, if any.

        Returns:
            List of clauses (implications) that were used to derive query, or a list of entailed facts (consequences) if no query is provided.
        """ 
        if query is None:
            _logger.debug("forward_chain(): Inferring all consequences (no query specified)")
        else:
            _logger.debug(f"forward_chain(): Forward chaining to derive query: {_clause_to_str(query)}")
        
        facts: set[sp.Basic] = {c for c in self.clauses if isinstance(c, sp.Symbol)}
        _logger.debug(f"forward_chain(): Starting with {len(facts)} initial fact(s)")

        # If the query is a direct fact, return it.
        if query is not None and query in facts:
            _logger.debug(f"forward_chain(): Query is a direct fact, returning immediately")
            return [query]
        
        # results is either a path to the query, or a list of entailed facts (consequences)
        results : list[sp.Basic] = []
        if query is None:
            results = list(facts.copy())

        changed = True
        iteration = 0
        while changed:
            iteration += 1
            changed = False
            _logger.debug(f"forward_chain(): Iteration {iteration}, checking {len([c for c in self.clauses if isinstance(c, sp.Implies)])} implication rule(s)")
            
            for rule in (c for c in self.clauses if isinstance(c, sp.Implies)):
                antecedent, consequent = rule.args
                
                # Check if antecedent is satisfied (supports conjunctive antecedents)
                if isinstance(antecedent, sp.And):
                    antecedent_satisfied = all(a in facts for a in antecedent.args)
                else:
                    antecedent_satisfied = antecedent in facts
                
                # If antecedent is satisfied and consequent not yet derived
                if antecedent_satisfied and consequent not in facts:
                    facts.add(consequent)
                    _logger.debug(f"forward_chain(): Derived new fact: {_clause_to_str(consequent)} from rule: {_clause_to_str(rule)}")
                    
                    # for no query, we just add the consequent to the consequences - entailing facts
                    if query is None:
                        results.append(consequent)

                    # for given query, we add the rule that derived the consequent to the consequences - entailing the query
                    else:
                        results.append(rule)
                        if consequent == query:
                            _logger.info(f"forward_chain(): Successfully derived query {_clause_to_str(query)} after {iteration} iteration(s)")
                            return results
                    
                    
                    changed = True

        # for given query, return the path that entailed the query
        if query is not None:
            if results:
                _logger.info(f"forward_chain(): Derived query path with {len(results)} step(s), but query may not be fully derived")
            else:
                _logger.warning(f"forward_chain(): Could not derive query {_clause_to_str(query)}")
            return results
        # Otherwise, return consequences
        _logger.info(f"forward_chain(): Inferred {len(results)} total consequence(s)")
        return results

    def resolve(self, clause1: sp.Basic, clause2: sp.Basic) -> Optional[sp.Basic]:
        """Perform resolution inference on two clauses.
        
        Resolution: If clause1 contains literal L and clause2 contains ~L,
        resolve to produce a new clause without L and ~L.
        
        Args:
            clause1: First clause (should be in CNF, i.e., sp.Or of literals or single literal)
            clause2: Second clause (should be in CNF, i.e., sp.Or of literals or single literal)
        
        Returns:
            Resolved clause if resolution is possible, None otherwise.
        """
        clause1 = self._require_expr(clause1, name="clause1")
        clause2 = self._require_expr(clause2, name="clause2")
        _logger.debug(f"resolve(): Attempting resolution between: {_clause_to_str(clause1)} and {_clause_to_str(clause2)}")

        # Handle single literals (SymPy may simplify sp.Or(p) to just p)
        if isinstance(clause1, sp.Symbol) or (isinstance(clause1, sp.Not) and isinstance(clause1.args[0], sp.Symbol)):
            literals1 = {clause1}
        elif isinstance(clause1, sp.Or):
            literals1 = set(clause1.args)
        else:
            _logger.debug(f"resolve(): Clause1 is not in CNF format, cannot resolve")
            return None
        
        if isinstance(clause2, sp.Symbol) or (isinstance(clause2, sp.Not) and isinstance(clause2.args[0], sp.Symbol)):
            literals2 = {clause2}
        elif isinstance(clause2, sp.Or):
            literals2 = set(clause2.args)
        else:
            _logger.debug(f"resolve(): Clause2 is not in CNF format, cannot resolve")
            return None
        
        _logger.debug(f"resolve(): Extracted {len(literals1)} literal(s) from clause1, {len(literals2)} literal(s) from clause2")
        
        # Look for complementary pair (L in clause1, ~L in clause2)
        for lit1 in literals1:
            if isinstance(lit1, sp.Symbol):
                # Check if ~lit1 is in clause2
                neg_lit1 = sp.Not(lit1)
                if neg_lit1 in literals2:
                    # Found complementary pair - resolve
                    _logger.debug(f"resolve(): Found complementary pair: {_clause_to_str(lit1)} and {_clause_to_str(neg_lit1)}")
                    new_literals = (literals1 - {lit1}) | (literals2 - {neg_lit1})
                    if not new_literals:
                        # Empty clause (contradiction)
                        _logger.info("resolve(): Resolution produced empty clause (contradiction)")
                        return sp.false
                    else: 
                        if len(new_literals) == 1:
                            result = list(new_literals)[0]

                        else:
                            result = sp.Or(*new_literals)
            
                    _logger.info(f"resolve(): Resolution successful, result: {_clause_to_str(result)}")
                    return result

            elif isinstance(lit1, sp.Not) and isinstance(lit1.args[0], sp.Symbol):
                # Check if lit1.args[0] (unnegated) is in clause2
                unnegated = lit1.args[0]
                if unnegated in literals2:
                    # Found complementary pair - resolve
                    _logger.debug(f"resolve(): Found complementary pair: {_clause_to_str(lit1)} and {_clause_to_str(unnegated)}")
                    new_literals = (literals1 - {lit1}) | (literals2 - {unnegated})
                    if not new_literals:
                        _logger.info("resolve(): Resolution produced empty clause (contradiction)")
                        return sp.false
                    else: 
                        if len(new_literals) == 1:
                            result = list(new_literals)[0]
                        else:
                            result = sp.Or(*new_literals)

                        _logger.info(f"resolve(): Resolution successful, result: {_clause_to_str(result)}")
                        return result
        
        # No complementary literals found
        _logger.debug("resolve(): No complementary literals found, resolution not possible")
        return None

class ChickenKB(KnowledgeBase):
    """Knowledge base specialized for the Chicken game (strategy rules and outcomes)."""

    def __init__(self):
        """Initialize an empty Chicken KB (extends KnowledgeBase)."""

        super().__init__()
        self.rnd_history = {}
        self.rnd = 0
        _logger.debug("ChickenKB initialized with round tracking")

    def reset_kb(self) -> None:
        """Clear all clauses and reset the KB to an empty state.

        Returns:
            None.
        """
        _logger.info(f"reset_kb(): Resetting ChickenKB (had {len(self.clauses)} clause(s), round # {self.rnd})")
        self.clauses = []
        self.clauses_for_rendering = []
        self.kb = sp.And()
        self.rnd = 0
        self.rnd_history = {}
        _logger.debug("reset_kb(): ChickenKB reset complete")

def _clause_to_str(clause: sp.Basic) -> str:
    """Format a single clause for display (Implies as 'a -> b', Equivalent as 'a <=> b', else str)."""
    if isinstance(clause, sp.Implies):
        return f"({clause.args[0]} -> {clause.args[1]})"
    if isinstance(clause, sp.Equivalent):
        return f"({clause.args[0]} <=> {clause.args[1]})"
    return str(clause)


def render_path(path: list[sp.Basic], forward: bool = True) -> str:
    """Render a path of clauses as a single string (e.g. for forward/backward chain output).

    Args:
        path: List of SymPy expressions (clauses) in the derivation path.
        forward: If True use " => " between clauses; if False use " <= ".

    Returns:
        A string representation of the path with the chosen delimiter.
    """
    delimiter = " => " if forward else " <= "
    pieces = [_clause_to_str(c) for c in path]
    return delimiter.join(pieces)


def main() -> None:
    """Run a short demo: build a Chicken KB, check entailment, render KB and chain paths."""
    _logger.info("main() started")

    our_kb = ChickenKB()

    p1_stays = sp.Symbol("p1_stays")
    p2_swerves = sp.Symbol("p2_swerves")
    
    our_kb.tell([p1_stays, sp.Implies(p1_stays, p2_swerves)])
    print("Does KB entail p2_swerves?", our_kb.ask(p2_swerves))
    print(our_kb.render_kb())

    print("Forward chaining:", render_path((our_kb.forward_chain(p2_swerves))))
    print("Backward chaining:", render_path((our_kb.backward_chain(p2_swerves)), False))

if __name__ == "__main__":
    main()  