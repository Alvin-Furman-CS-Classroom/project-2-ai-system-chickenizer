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
from typing import Optional, List
from dataclasses import dataclass


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
            raise TypeError(f"{name} must be a list[sp.Basic], got {type(value).__name__}")
        for i, item in enumerate(value):
            if not isinstance(item, sp.Basic):
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
        self.clauses.extend(clauses)
        self.clauses_for_rendering.extend(clauses)
        self.rebuild_kb()

    def ask(self, query: sp.Basic) -> bool:
        """Check if knowledge base entails given query.

        Args:
            query: A SymPy object to check for entailment.

        Returns:
            True if KB entails query, False otherwise.
        """
        query = self._require_expr(query, name="query")
        return not sp.satisfiable(sp.And(self.kb, sp.Not(query)))

    def rebuild_kb(self) -> None:
        """Rebuild the internal KB (SymPy And) from the current clauses list.

        Returns:
            None.
        """

        if not self.clauses:
            self.kb = sp.And()
        else:
            self.kb = sp.And(*self.clauses)

    def validate_kb(self) -> tuple[bool, Optional[ConflictReport]]:
        """Check whether the knowledge base is satisfiable (no contradiction).

        Returns:
            Tuple of (is_satisfiable: bool, conflict_report: Optional[ConflictReport]).
            If satisfiable, returns (True, None).
            If unsatisfiable, returns (False, ConflictReport) identifying conflicting clauses.
        """
        if sp.satisfiable(self.kb):
            return (True, None)
        
        # KB is unsatisfiable - identify conflicts using iterative removal
        conflict_report = self._find_minimal_conflict()
        return (False, conflict_report)
    
    def _find_minimal_conflict(self) -> ConflictReport:
        """Find minimal set of conflicting clauses using iterative removal.
        
        Strategy: Try removing each clause one by one. If removing a clause
        makes the KB satisfiable, that clause is part of the conflict.
        
        Returns:
            ConflictReport identifying the conflicting clauses.
        """
        # First, check for obvious direct contradictions (p and ~p)
        direct_conflict = self._check_direct_contradiction()
        if direct_conflict:
            return direct_conflict
        
        # Check for chain contradictions (p -> q, p, ~q)
        chain_conflict = self._check_chain_contradiction()
        if chain_conflict:
            return chain_conflict
        
        # Use iterative removal to find minimal conflict set
        conflicting_indices = []
        
        # Try removing each clause to see if KB becomes satisfiable
        for i in range(len(self.clauses)):
            test_clauses = self.clauses[:i] + self.clauses[i+1:]
            if not test_clauses:
                # Empty KB is satisfiable
                conflicting_indices.append(i)
                continue
            
            test_kb = sp.And(*test_clauses)
            if sp.satisfiable(test_kb):
                # Removing this clause makes KB satisfiable, so it's part of conflict
                conflicting_indices.append(i)
        
        if conflicting_indices:
            conflicting_clauses = [self.clauses[i] for i in conflicting_indices]
            if len(conflicting_indices) == 1:
                conflict_type = "minimal"
                description = "Minimal conflict: single conflicting clause"
            else:
                conflict_type = "minimal"
                description = f"Minimal conflict: {len(conflicting_indices)} conflicting clauses"
        else:
            # All clauses are needed for conflict (rare case)
            conflicting_clauses = self.clauses.copy()
            conflict_type = "all"
            description = "All clauses participate in conflict"
        
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
        symbols = {}
        for clause in self.clauses:
            if isinstance(clause, sp.Symbol):
                symbols[clause] = clause
            elif isinstance(clause, sp.Not) and isinstance(clause.args[0], sp.Symbol):
                negated_symbol = clause.args[0]
                if negated_symbol in symbols:
                    # Found direct contradiction: symbol and its negation
                    return ConflictReport(
                        conflicting_clauses=[symbols[negated_symbol], clause],
                        conflict_type="direct",
                        description="Direct contradiction"
                    )
        return None
    
    def _check_chain_contradiction(self) -> Optional[ConflictReport]:
        """Check for chain contradictions (p -> q, p, ~q).
        
        Returns:
            ConflictReport if chain contradiction found, None otherwise.
        """
        # Build sets for quick lookup
        facts = set()
        negations = {}
        
        for clause in self.clauses:
            if isinstance(clause, sp.Symbol):
                facts.add(clause)
            elif isinstance(clause, sp.Not) and isinstance(clause.args[0], sp.Symbol):
                negations[clause.args[0]] = clause
        
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
                    return ConflictReport(
                        conflicting_clauses=conflicting,
                        conflict_type="chain",
                        description="Contradiction through logical chain"
                    )
        
        return None

    def is_cnf(self) -> bool:
        """Check if knowledge base is in CNF (Conjunctive Normal Form).

        Returns:
            True if every clause is a disjunction of literals (sp.Or) or a single literal.
        """
        # CNF: top-level AND of clauses; each clause is OR of literals OR a literal itself.
        def _is_literal(expr: sp.Expr) -> bool:
            return isinstance(expr, sp.Symbol) or (isinstance(expr, sp.Not) and isinstance(expr.args[0], sp.Symbol))

        def _is_clause(expr: sp.Expr) -> bool:
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
        
        if query in visited:
            return []

        visited.add(query)
        
        # Base case
        if query in self.clauses:
            return [query]

        for rule in (c for c in self.clauses if isinstance(c, sp.Implies)):
            antecedent, consequent = rule.args
            if consequent != query:
                continue

            if isinstance(antecedent, sp.And):
                subpaths: list[sp.Basic] = []
                for a in antecedent.args:
                    p = self.backward_chain(a, visited)
                    if not p:
                        break
                    subpaths.extend(p)
                else:
                    return subpaths + [rule]
            else:
                recur_path = self.backward_chain(antecedent, visited)
                if recur_path:
                    return recur_path + [rule]

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
    

    def forward_chain(self, query: sp.Basic = None) -> list[sp.Basic]:
        """
        Forward chain from known facts. Used by forward_chain_derive_query to derive the query if possible. If no query is provided, return all entailed facts.

        Args:
            query: SymPy object that is the goal to derive, if any.

        Returns:
            List of clauses (implications) that were used to derive query, or [] if not derivable.
        """ 
        facts: set[sp.Basic] = {c for c in self.clauses if isinstance(c, sp.Symbol)}

        # If the query is a direct fact, return it.
        if query is not None and query in facts:
            return [query]
        
        consequences: list[sp.Basic] = []
        if query is None:
            consequences = list(facts.copy())
        # else:
        #     consequences.append(query)

        changed = True
        while changed:
            changed = False
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
                    # for no query, we just add the consequent to the consequences - entailing facts
                    if query is None:
                        consequences.append(consequent)

                    # for a query, we add the rule that derived the consequent to the consequences - entailing the query
                    else:
                        consequences.append(rule)
                        if consequent == query:
                            return consequences
                    
                    
                    changed = True

        if query is not None:
            return consequences
        else:
            return []

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

        # Handle single literals (SymPy may simplify sp.Or(p) to just p)
        if isinstance(clause1, sp.Symbol) or (isinstance(clause1, sp.Not) and isinstance(clause1.args[0], sp.Symbol)):
            literals1 = {clause1}
        elif isinstance(clause1, sp.Or):
            literals1 = set(clause1.args)
        else:
            return None
        
        if isinstance(clause2, sp.Symbol) or (isinstance(clause2, sp.Not) and isinstance(clause2.args[0], sp.Symbol)):
            literals2 = {clause2}
        elif isinstance(clause2, sp.Or):
            literals2 = set(clause2.args)
        else:
            return None
        
        # Look for complementary pair (L in clause1, ~L in clause2)
        for lit1 in literals1:
            if isinstance(lit1, sp.Symbol):
                # Check if ~lit1 is in clause2
                neg_lit1 = sp.Not(lit1)
                if neg_lit1 in literals2:
                    # Found complementary pair - resolve
                    new_literals = (literals1 - {lit1}) | (literals2 - {neg_lit1})
                    if not new_literals:
                        # Empty clause (contradiction)
                        return sp.false
                    elif len(new_literals) == 1:
                        return list(new_literals)[0]
                    else:
                        return sp.Or(*new_literals)
            elif isinstance(lit1, sp.Not) and isinstance(lit1.args[0], sp.Symbol):
                # Check if lit1.args[0] (unnegated) is in clause2
                unnegated = lit1.args[0]
                if unnegated in literals2:
                    # Found complementary pair - resolve
                    new_literals = (literals1 - {lit1}) | (literals2 - {unnegated})
                    if not new_literals:
                        return sp.false
                    elif len(new_literals) == 1:
                        return list(new_literals)[0]
                    else:
                        return sp.Or(*new_literals)
        
        # No complementary literals found
        return None

class ChickenKB(KnowledgeBase):
    """Knowledge base specialized for the Chicken game (strategy rules and outcomes)."""

    def __init__(self):
        """Initialize an empty Chicken KB (extends KnowledgeBase)."""

        super().__init__()
        self.rnd_history = {}
        self.rnd = 0

    def reset_kb(self) -> None:
        """Clear all clauses and reset the KB to an empty state.

        Returns:
            None.
        """

        self.clauses = []
        self.clauses_for_rendering = []
        self.kb = sp.And()
        self.rnd = 0
        self.rnd_history = {}

def _clause_to_str(clause: sp.Expr) -> str:
    """Format a single clause for display (Implies as 'a -> b', Equivalent as 'a <=> b', else str)."""
    if isinstance(clause, sp.Implies):
        return f"({clause.args[0]} -> {clause.args[1]})"
    if isinstance(clause, sp.Equivalent):
        return f"({clause.args[0]} <=> {clause.args[1]})"
    return str(clause)


def render_path(path: list[sp.Expr], forward: bool = True) -> str:
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