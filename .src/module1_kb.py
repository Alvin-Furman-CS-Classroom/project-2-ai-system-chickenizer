# Module 1: Strategy Logic Encoder, Knowledge Base
"""Strategy Logic Encoder and Knowledge Base for the Chickenizer system.

Provides KnowledgeBase (tell/ask, CNF, forward/backward chaining) and ChickenKB
for encoding game strategies and outcomes in propositional logic.
"""

# Dependencies:
# from typing import Any
import sympy as sp


class KnowledgeBase:
    """Propositional logic knowledge base with tell/ask, CNF, and forward/backward chaining."""

    def __init__(self):
        """Initialize empty knowledge base with clauses list and SymPy And structure."""

        self.clauses = []
        self.clauses_for_rendering = []

        #CNF knowledge base, "AND of ORs" rather than "OR of ANDs"
        self.kb = sp.And()

    def tell(self, clauses: list[sp.Expr]) -> None:
        """Add clauses to the knowledge base and rebuild the internal KB.

        Args:
            clauses: List of SymPy expressions (facts or rules) to add.

        Returns:
            None.
        """

        self.clauses.extend(clauses)
        self.clauses_for_rendering.extend(clauses)
        self.rebuild_kb()

    def ask(self, query: sp.Expr) -> bool:
        """Check if knowledge base entails given query.

        Args:
            query: A SymPy expression to check for entailment.

        Returns:
            True if KB entails query, False otherwise.
        """

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

    def validate_kb(self) -> bool:
        """Check whether the knowledge base is satisfiable (no contradiction).

        Returns:
            True if KB is satisfiable, False if unsatisfiable.
        """

        return sp.satisfiable(self.kb)

    def is_cnf(self) -> bool:
        """Check if knowledge base is in CNF (Conjunctive Normal Form).

        Returns:
            True if every clause is an sp.Or, False otherwise.
        """
        #rules of CNF: each clause is OR of literals, top level is AND of clauses
        return all(isinstance(clause, sp.Or) for clause in self.clauses)

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

    def forward_chain(self, query: sp.Expr) -> list[sp.Expr]:
        """Forward chain from known facts to derive the query if possible.

        Args:
            query: SymPy expression that is the goal to derive.

        Returns:
            List of clauses (implications) that were used to derive query, or [] if not derivable.
        """

        path = []
        facts = self.clauses.copy()
        if query in facts: 
            return [query]

        new_facts_added = True
        while new_facts_added:
            new_facts_added = False
            for clause in self.clauses:
                if len(clause.args) != 0:
                    if not clause.args[0] in facts:
                        continue
                    if clause.args[-1] in facts:
                        continue

                    new_facts_added = True
                    facts.append(clause.args[-1])
                    path.append(clause)
                    if clause.args[-1] == query:
                        return path
        return []

    def backward_chain(self, query: sp.Expr, visited=None) -> list[sp.Expr]:
        """Backward chain from the query goal back to supporting facts.

        Args:
            query: SymPy expression that is the goal to prove.
            visited: Set of already-visited goals (used internally to avoid cycles).

        Returns:
            List of clauses from facts to query that form a proof path, or [] if not derivable.
        """

        if visited is None:
            visited = set()

        
        if query in visited:
            return []

        visited.add(query)
        
        # Base case
        if query in self.clauses:
            return [query]

        for clause in self.clauses:
            if len(clause.args) != 0:
                if clause.args[-1] == query:
                    recur_path = self.backward_chain(clause.args[0], visited)
                    if recur_path:
                        return recur_path + [clause]

        return []
        
        
class ChickenKB(KnowledgeBase):
    """Knowledge base specialized for the Chicken game (strategy rules and outcomes)."""

    def __init__(self):
        """Initialize an empty Chicken KB (extends KnowledgeBase)."""

        super().__init__()
        self.rnd_history = {}
        self.rnd = 0
        #preadding the "p1_stays" symbol to the knowledge base, since we operate under worst-case scenario assumptions
        #This is a placeholder--across multiple rounds, we'd want p1 to be able to change their aggression

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
    # Create symbols for all the variables we'll use
    p1_stays = sp.Symbol("p1_stays")
    # grudge = sp.Symbol("grudge")
    # p2_stays = sp.Symbol("p2_stays")
    p2_swerves = sp.Symbol("p2_swerves")
    
    our_kb.tell([p1_stays, sp.Implies(p1_stays, p2_swerves)])
    print("Does KB entail p2_swerves?", our_kb.ask(p2_swerves))
    print(our_kb.render_kb())

    # old statements, from before ask/tell paradigm
    # our_kb.add_clause(sp.Implies(p1_stays, grudge))
    # our_kb.add_clause(sp.Equivalent(grudge, p2_stays))
    # our_kb.add_clause(sp.Implies(sp.Not(p1_stays), sp.Not(grudge)))
    # our_kb.add_clause(sp.Equivalent(sp.Not(p2_stays), p2_swerves))

    # print("Entailment", our_kb.entails(sp.Not(p1_stays)))
    # print("Is CNF", our_kb.is_cnf())
    # our_kb.render_kb()
    # print("CNF", our_kb.to_cnf())
    # print("Is CNF now?", our_kb.is_cnf())
    # our_kb.render_kb()
    # print(our_kb.validate_kb())

    # test forward and backward chaining
    print("Forward chaining:", render_path((our_kb.forward_chain(p2_swerves))))
    print("Backward chaining:", render_path((our_kb.backward_chain(p2_swerves)), False))

if __name__ == "__main__":
    main()  