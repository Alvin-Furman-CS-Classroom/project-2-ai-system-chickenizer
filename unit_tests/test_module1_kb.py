"""
Unit tests for Module 1: Knowledge Base and ChickenKB classes.

Tests cover:
- Basic KB operations (add_symbol, add_clause, add_clauses)
- KB validation (satisfiability)
- KB rendering
- Edge cases and error handling
- ChickenKB-specific functionality for strategy and outcome representation
- Future functionality (entailment, inference, CNF validation)
"""

import pytest
import sympy as sp
import sys
import importlib.util
from pathlib import Path

# Load module from .src directory
src_path = Path(__file__).parent.parent / ".src" / "module1_kb.py"
spec = importlib.util.spec_from_file_location("module1_kb", src_path)
module1_kb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module1_kb)

KnowledgeBase = module1_kb.KnowledgeBase
ChickenKB = module1_kb.ChickenKB


class TestKnowledgeBase:
    """Test cases for the base KnowledgeBase class."""
    
    def test_initialization(self):
        """Test that KB initializes with empty clauses and symbols."""
        kb = KnowledgeBase()
        assert kb.clauses == []
        assert kb.symbols == set()
        assert kb.kb == sp.And()
    
    def test_add_symbol(self):
        """Test adding a symbol to the KB."""
        kb = KnowledgeBase()
        symbol = sp.Symbol("test_symbol")
        kb.add_symbol(symbol)
        
        assert symbol in kb.symbols
        assert symbol in kb.clauses
        assert len(kb.clauses) == 1
    
    def test_add_multiple_symbols(self):
        """Test adding multiple symbols."""
        kb = KnowledgeBase()
        s1 = sp.Symbol("s1")
        s2 = sp.Symbol("s2")
        s3 = sp.Symbol("s3")
        
        kb.add_symbol(s1)
        kb.add_symbol(s2)
        kb.add_symbol(s3)
        
        assert len(kb.symbols) == 3
        assert len(kb.clauses) == 3
        assert s1 in kb.symbols and s1 in kb.clauses
        assert s2 in kb.symbols and s2 in kb.clauses
        assert s3 in kb.symbols and s3 in kb.clauses
    
    def test_add_clause_implication(self):
        """Test adding an implication clause."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        clause = sp.Implies(p, q)
        
        kb.add_clause(clause)
        
        assert clause in kb.clauses
        assert len(kb.clauses) == 1
    
    def test_add_clause_equivalent(self):
        """Test adding an equivalence clause."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        clause = sp.Equivalent(p, q)
        
        kb.add_clause(clause)
        
        assert clause in kb.clauses
        assert len(kb.clauses) == 1
    
    def test_add_clause_negation(self):
        """Test adding a negation clause."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        clause = sp.Not(p)
        
        kb.add_clause(clause)
        
        assert clause in kb.clauses
        assert len(kb.clauses) == 1
    
    def test_add_clause_and(self):
        """Test adding an AND clause."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        clause = sp.And(p, q)
        
        kb.add_clause(clause)
        
        assert clause in kb.clauses
        assert len(kb.clauses) == 1
    
    def test_add_clause_or(self):
        """Test adding an OR clause."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        clause = sp.Or(p, q)
        
        kb.add_clause(clause)
        
        assert clause in kb.clauses
        assert len(kb.clauses) == 1
    
    def test_add_clauses_list(self):
        """Test adding multiple clauses at once."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        clauses = [
            sp.Implies(p, q),
            sp.Implies(q, r),
            sp.Or(p, r)
        ]
        
        kb.add_clauses(clauses)
        
        assert len(kb.clauses) == 3
        assert all(clause in kb.clauses for clause in clauses)
    
    def test_rebuild_kb_empty(self):
        """Test rebuilding KB with no clauses."""
        kb = KnowledgeBase()
        kb.rebuild_kb()
        assert kb.kb == sp.And()
    
    def test_rebuild_kb_single_clause(self):
        """Test rebuilding KB with one clause."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        kb.add_clause(p)
        assert kb.kb == sp.And(p)
    
    def test_rebuild_kb_multiple_clauses(self):
        """Test rebuilding KB with multiple clauses."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        kb.add_clause(p)
        kb.add_clause(q)
        assert kb.kb == sp.And(p, q)
    
    def test_validate_kb_satisfiable_simple(self):
        """Test validation of a satisfiable KB."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        kb.add_clause(p)
        
        result = kb.validate_kb()
        assert result is not False  # Should return a model or True
    
    def test_validate_kb_satisfiable_complex(self):
        """Test validation of a complex satisfiable KB."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        kb.add_clause(sp.Implies(p, q))
        kb.add_clause(sp.Implies(q, r))
        kb.add_clause(p)
        
        result = kb.validate_kb()
        assert result is not False
    
    def test_validate_kb_unsatisfiable_contradiction(self):
        """Test validation of an unsatisfiable KB with direct contradiction."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        kb.add_clause(p)
        kb.add_clause(sp.Not(p))
        
        result = kb.validate_kb()
        assert result is False
    
    def test_validate_kb_unsatisfiable_chain(self):
        """Test validation of an unsatisfiable KB with logical chain."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.add_clause(sp.Implies(p, q))
        kb.add_clause(p)
        kb.add_clause(sp.Not(q))
        
        result = kb.validate_kb()
        assert result is False
    
    def test_render_kb_empty(self, capsys):
        """Test rendering an empty KB."""
        kb = KnowledgeBase()
        kb.render_kb()
        captured = capsys.readouterr()
        # Empty KB should print nothing or empty string
        assert captured.out == "" or captured.out.strip() == ""
    
    def test_render_kb_symbols(self, capsys):
        """Test rendering KB with symbols."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        kb.add_clause(p)
        kb.add_clause(q)
        
        kb.render_kb()
        captured = capsys.readouterr()
        output = captured.out.strip()
        assert "p" in output
        assert "q" in output
    
    def test_render_kb_implications(self, capsys):
        """Test rendering KB with implications."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        kb.add_clause(sp.Implies(p, q))
        
        kb.render_kb()
        captured = capsys.readouterr()
        output = captured.out.strip()
        assert "->" in output
        assert "p" in output
        assert "q" in output
    
    def test_render_kb_equivalences(self, capsys):
        """Test rendering KB with equivalences."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        kb.add_clause(sp.Equivalent(p, q))
        
        kb.render_kb()
        captured = capsys.readouterr()
        output = captured.out.strip()
        assert "<=>" in output
        assert "p" in output
        assert "q" in output
    
    def test_render_kb_mixed_clauses(self, capsys):
        """Test rendering KB with mixed clause types."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        kb.add_clause(p)
        kb.add_clause(sp.Implies(p, q))
        kb.add_clause(sp.Equivalent(q, r))
        
        kb.render_kb()
        captured = capsys.readouterr()
        output = captured.out.strip()
        assert "p" in output
        assert "->" in output
        assert "<=>" in output
    
    def test_add_symbol_rebuilds_kb(self):
        """Test that add_symbol automatically rebuilds KB."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        kb.add_symbol(p)
        assert kb.kb == sp.And(p)
    
    def test_add_clause_rebuilds_kb(self):
        """Test that add_clause automatically rebuilds KB."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        clause = sp.Implies(p, q)
        kb.add_clause(clause)
        assert kb.kb == sp.And(clause)
    
    def test_add_clauses_rebuilds_kb(self):
        """Test that add_clauses automatically rebuilds KB."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        clauses = [p, q]
        kb.add_clauses(clauses)
        assert kb.kb == sp.And(p, q)
    
    def test_complex_logical_formula(self):
        """Test KB with complex nested logical formulas."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        # Complex formula: (p -> q) AND (q -> r) AND (p OR r)
        kb.add_clause(sp.Implies(p, q))
        kb.add_clause(sp.Implies(q, r))
        kb.add_clause(sp.Or(p, r))
        
        result = kb.validate_kb()
        assert result is not False
    
    def test_xor_representation(self):
        """Test representing XOR (exclusive or) using implications."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        # p XOR q = (p -> ~q) AND (q -> ~p) AND (p OR q)
        kb.add_clause(sp.Implies(p, sp.Not(q)))
        kb.add_clause(sp.Implies(q, sp.Not(p)))
        kb.add_clause(sp.Or(p, q))
        
        result = kb.validate_kb()
        assert result is not False


class TestChickenKB:
    """Test cases for the ChickenKB class, focused on strategy and outcome representation."""
    
    def test_initialization(self):
        """Test that ChickenKB initializes with p1_stays symbol."""
        kb = ChickenKB()
        assert len(kb.clauses) == 1
        assert len(kb.symbols) == 1
        assert sp.Symbol("p1_stays") in kb.symbols
        assert sp.Symbol("p1_stays") in kb.clauses
    
    def test_strategy_grudge_representation(self):
        """Test representing a grudge strategy: if opponent stays, I stay."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        grudge = sp.Symbol("grudge")
        
        # Grudge strategy: if p1 stays, then grudge is true
        # If grudge is true, then p2 stays
        kb.add_clause(sp.Implies(p1_stays, grudge))
        kb.add_clause(sp.Equivalent(grudge, p2_stays))
        
        result = kb.validate_kb()
        assert result is not False
    
    def test_strategy_tit_for_tat(self):
        """Test representing tit-for-tat strategy."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        p2_swerves = sp.Symbol("p2_swerves")
        
        # Tit-for-tat: p1's action matches p2's previous action
        # This is simplified - in full implementation would track previous round
        kb.add_clause(sp.Equivalent(p1_stays, p2_stays))
        kb.add_clause(sp.Equivalent(p1_swerves, p2_swerves))
        
        result = kb.validate_kb()
        assert result is not False
    
    def test_strategy_always_swerve(self):
        """Test representing always-swerve strategy."""
        kb = ChickenKB()
        p1_swerves = sp.Symbol("p1_swerves")
        
        # Always swerve: p1_swerves is always true
        kb.add_clause(p1_swerves)
        
        result = kb.validate_kb()
        assert result is not False
    
    def test_strategy_always_stay(self):
        """Test representing always-stay strategy."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        
        # Always stay: p1_stays is always true (already in KB)
        # This should be consistent
        result = kb.validate_kb()
        assert result is not False
    
    def test_outcome_collision(self):
        """Test representing collision outcome: both players stay."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        collision = sp.Symbol("collision")
        
        # Collision occurs when both stay
        kb.add_clause(sp.Equivalent(collision, sp.And(p1_stays, p2_stays)))
        
        result = kb.validate_kb()
        assert result is not False
    
    def test_outcome_mutual_cooperation(self):
        """Test representing mutual cooperation: both swerve."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        p2_swerves = sp.Symbol("p2_swerves")
        mutual_cooperation = sp.Symbol("mutual_cooperation")
        
        # Mutual cooperation: both swerve
        kb.add_clause(sp.Equivalent(mutual_cooperation, 
                                    sp.And(p1_swerves, p2_swerves)))
        
        result = kb.validate_kb()
        assert result is not False
    
    def test_action_mutual_exclusivity(self):
        """Test that stay and swerve are mutually exclusive for a player."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        
        # A player cannot both stay and swerve
        kb.add_clause(sp.Implies(p1_stays, sp.Not(p1_swerves)))
        kb.add_clause(sp.Implies(p1_swerves, sp.Not(p1_stays)))
        
        result = kb.validate_kb()
        assert result is not False
    
    def test_action_completeness(self):
        """Test that a player must either stay or swerve."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        
        # A player must choose one action
        kb.add_clause(sp.Or(p1_stays, p1_swerves))
        
        result = kb.validate_kb()
        assert result is not False
    
    def test_strategy_conditional_response(self):
        """Test representing conditional response strategy."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        
        # Conditional: if p2 stays, then p1 swerves (chicken out)
        kb.add_clause(sp.Implies(p2_stays, p1_swerves))
        
        result = kb.validate_kb()
        assert result is not False
    
    def test_strategy_escalation(self):
        """Test representing escalation strategy: respond in kind."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        p2_swerves = sp.Symbol("p2_swerves")
        
        # Escalation: match opponent's action
        kb.add_clause(sp.Implies(p2_stays, p1_stays))
        kb.add_clause(sp.Implies(p2_swerves, p1_swerves))
        
        result = kb.validate_kb()
        assert result is not False
    
    def test_payoff_conditions(self):
        """Test representing payoff conditions based on outcomes."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        p2_swerves = sp.Symbol("p2_swerves")
        p1_wins = sp.Symbol("p1_wins")
        p2_wins = sp.Symbol("p2_wins")
        
        # p1 wins if p1 stays and p2 swerves
        kb.add_clause(sp.Equivalent(p1_wins, sp.And(p1_stays, p2_swerves)))
        # p2 wins if p2 stays and p1 swerves
        kb.add_clause(sp.Equivalent(p2_wins, sp.And(p2_stays, p1_swerves)))
        
        result = kb.validate_kb()
        assert result is not False
    
    def test_inconsistent_strategy(self):
        """Test that inconsistent strategies are detected as unsatisfiable."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        
        # Contradictory: p1 both stays and swerves
        kb.add_clause(p1_stays)
        kb.add_clause(p1_swerves)
        kb.add_clause(sp.Implies(p1_stays, sp.Not(p1_swerves)))
        
        result = kb.validate_kb()
        assert result is False
    
    def test_complex_strategy_combination(self):
        """Test a complex combination of strategy rules."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        p2_swerves = sp.Symbol("p2_swerves")
        grudge = sp.Symbol("grudge")
        collision = sp.Symbol("collision")
        
        # Multiple strategy rules
        kb.add_clause(sp.Implies(p1_stays, grudge))
        kb.add_clause(sp.Equivalent(grudge, p2_stays))
        kb.add_clause(sp.Equivalent(collision, sp.And(p1_stays, p2_stays)))
        kb.add_clause(sp.Implies(p1_stays, sp.Not(p1_swerves)))
        kb.add_clause(sp.Implies(p2_stays, sp.Not(p2_swerves)))
        
        result = kb.validate_kb()
        assert result is not False
    
    def test_render_chicken_kb(self, capsys):
        """Test rendering ChickenKB with strategy clauses."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        grudge = sp.Symbol("grudge")
        p2_stays = sp.Symbol("p2_stays")
        
        kb.add_clause(sp.Implies(p1_stays, grudge))
        kb.add_clause(sp.Equivalent(grudge, p2_stays))
        
        kb.render_kb()
        captured = capsys.readouterr()
        output = captured.out.strip()
        assert "p1_stays" in output
        assert "->" in output
        assert "<=>" in output


class TestEssentialKBFunctionality:
    """Test cases for essential KB functionality required by the proposal.
    
    These test core knowledge base operations that should be implemented:
    - Entailment checking (KB entails query)
    - CNF conversion and validation
    - Inference methods (resolution, chaining)
    - Logical consequence inference
    - Conflict reporting
    """
    
    def test_entailment_checking_modus_ponens(self):
        """Test entailment: KB with (p -> q) and p should entail q."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.add_clause(sp.Implies(p, q))
        kb.add_clause(p)
        
        # KB should entail q
        # Test by checking if KB U {~q} is unsatisfiable
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.add_clause(sp.Not(q))
        test_kb.rebuild_kb()
        
        assert test_kb.validate_kb() is False  # KB entails q
    
    def test_entailment_checking_chain(self):
        """Test entailment through logical chain: (p -> q), (q -> r), p entails r."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        kb.add_clause(sp.Implies(p, q))
        kb.add_clause(sp.Implies(q, r))
        kb.add_clause(p)
        
        # KB should entail r
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.add_clause(sp.Not(r))
        test_kb.rebuild_kb()
        
        assert test_kb.validate_kb() is False  # KB entails r
    
    def test_entailment_checking_does_not_entail(self):
        """Test that KB does not entail a query when it shouldn't."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.add_clause(p)
        # KB does not contain q, so should not entail q
        
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.add_clause(sp.Not(q))
        test_kb.rebuild_kb()
        
        assert test_kb.validate_kb() is not False  # KB does not entail q
    
    def test_entailment_interface(self):
        """Test that KB should have an entails() method for querying."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.add_clause(sp.Implies(p, q))
        kb.add_clause(p)
        
        # Future: kb.entails(q) should return True
        # This test documents the expected interface
        # For now, manually verify using satisfiability
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.add_clause(sp.Not(q))
        test_kb.rebuild_kb()
        assert test_kb.validate_kb() is False
    
    def test_cnf_conversion_implication(self):
        """Test that implications should be convertible to CNF: (p -> q) = (~p OR q)."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.add_clause(sp.Implies(p, q))
        
        # Future: kb.to_cnf() should convert (p -> q) to (~p OR q)
        # CNF form of (p -> q) is (~p OR q)
        cnf_clause = sp.Or(sp.Not(p), q)
        cnf_kb = KnowledgeBase()
        cnf_kb.add_clause(cnf_clause)
        
        # Both should be logically equivalent
        # Test by checking if KB U {~cnf} is unsatisfiable
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.add_clause(sp.Not(cnf_clause))
        test_kb.rebuild_kb()
        
        # If original KB entails CNF form, then they're equivalent
        # This is a simplified check - full CNF conversion would be more thorough
        assert test_kb.validate_kb() is False
    
    def test_cnf_conversion_equivalent(self):
        """Test that equivalences should be convertible to CNF."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.add_clause(sp.Equivalent(p, q))
        
        # CNF form of (p <-> q) is (~p OR q) AND (p OR ~q)
        cnf_kb = KnowledgeBase()
        cnf_kb.add_clause(sp.Or(sp.Not(p), q))
        cnf_kb.add_clause(sp.Or(p, sp.Not(q)))
        
        # Both should be logically equivalent
        # Test by checking mutual entailment
        test1 = KnowledgeBase()
        test1.clauses = kb.clauses.copy()
        test1.add_clause(sp.Not(sp.And(sp.Or(sp.Not(p), q), sp.Or(p, sp.Not(q)))))
        test1.rebuild_kb()
        
        test2 = KnowledgeBase()
        test2.clauses = cnf_kb.clauses.copy()
        test2.add_clause(sp.Not(sp.Equivalent(p, q)))
        test2.rebuild_kb()
        
        # Both should be unsatisfiable if equivalent
        assert test1.validate_kb() is False
        assert test2.validate_kb() is False
    
    def test_cnf_validation(self):
        """Test that KB should be able to validate if it's in CNF format."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        # Add clauses that are already in CNF (disjunctions of literals)
        kb.add_clause(sp.Or(p, q))
        kb.add_clause(sp.Or(sp.Not(p), r))
        kb.add_clause(sp.Or(q, sp.Not(r)))
        
        # Future: kb.is_cnf() should return True
        # For now, verify these are valid CNF clauses
        assert kb.validate_kb() is not False
    
    def test_cnf_validation_not_cnf(self):
        """Test that KB should detect when clauses are not in CNF."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        # Add clause that is NOT in CNF (has nested AND)
        kb.add_clause(sp.And(p, q))
        
        # Future: kb.is_cnf() should return False
        # For now, verify the clause exists
        assert len(kb.clauses) == 1
        assert isinstance(kb.clauses[0], sp.And)
    
    def test_resolution_inference(self):
        """Test resolution inference: from (p OR q) and (~p OR r), infer (q OR r)."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        # KB: (p OR q), (~p OR r)
        kb.add_clause(sp.Or(p, q))
        kb.add_clause(sp.Or(sp.Not(p), r))
        
        # Resolution should infer (q OR r)
        # Future: kb.resolve() should return [q OR r]
        # Verify that (q OR r) is entailed
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.add_clause(sp.Not(sp.Or(q, r)))  # Add ~(q OR r) = (~q AND ~r)
        test_kb.add_clause(sp.And(sp.Not(q), sp.Not(r)))
        test_kb.rebuild_kb()
        
        # If KB entails (q OR r), then KB U {~(q OR r)} is unsatisfiable
        assert test_kb.validate_kb() is False
    
    def test_forward_chaining(self):
        """Test forward chaining inference method."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        s = sp.Symbol("s")
        
        # Rules: p -> q, q -> r, r -> s
        # Facts: p
        kb.add_clause(sp.Implies(p, q))
        kb.add_clause(sp.Implies(q, r))
        kb.add_clause(sp.Implies(r, s))
        kb.add_clause(p)
        
        # Forward chaining should infer: q, then r, then s
        # Future: kb.forward_chain() should return [q, r, s]
        # Verify that s is entailed
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.add_clause(sp.Not(s))
        test_kb.rebuild_kb()
        
        assert test_kb.validate_kb() is False  # KB entails s
    
    def test_backward_chaining(self):
        """Test backward chaining inference method."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        # Rules: p -> q, q -> r
        # Goal: prove r
        kb.add_clause(sp.Implies(p, q))
        kb.add_clause(sp.Implies(q, r))
        kb.add_clause(p)
        
        # Backward chaining: to prove r, need q; to prove q, need p; p is given
        # Future: kb.backward_chain(r) should return True
        # Verify that r is entailed
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.add_clause(sp.Not(r))
        test_kb.rebuild_kb()
        
        assert test_kb.validate_kb() is False  # KB entails r
    
    def test_infer_logical_consequences(self):
        """Test inferring all logical consequences from KB."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        kb.add_clause(sp.Implies(p, q))
        kb.add_clause(sp.Implies(q, r))
        kb.add_clause(p)
        
        # Future: kb.infer_consequences() should return all entailed facts
        # Should include: q, r, and potentially others depending on implementation
        # For now, verify that q and r are both entailed
        test_q = KnowledgeBase()
        test_q.clauses = kb.clauses.copy()
        test_q.add_clause(sp.Not(q))
        test_q.rebuild_kb()
        assert test_q.validate_kb() is False
        
        test_r = KnowledgeBase()
        test_r.clauses = kb.clauses.copy()
        test_r.add_clause(sp.Not(r))
        test_r.rebuild_kb()
        assert test_r.validate_kb() is False
    
    def test_conflict_reporting_direct_contradiction(self):
        """Test that KB should report which clauses conflict when inconsistent."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        
        kb.add_clause(p)
        kb.add_clause(sp.Not(p))
        
        # Future: kb.validate_kb() should return (False, conflict_report)
        # conflict_report should identify that p and ~p conflict
        # For now, verify it's unsatisfiable
        result = kb.validate_kb()
        assert result is False
    
    def test_conflict_reporting_chain_contradiction(self):
        """Test conflict reporting for contradictions through logical chain."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.add_clause(sp.Implies(p, q))
        kb.add_clause(p)
        kb.add_clause(sp.Not(q))
        
        # Future: conflict_report should identify the chain: p -> q, p, ~q
        # For now, verify it's unsatisfiable
        result = kb.validate_kb()
        assert result is False
    
    def test_conflict_reporting_multiple_conflicts(self):
        """Test conflict reporting when multiple conflicts exist."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.add_clause(p)
        kb.add_clause(sp.Not(p))
        kb.add_clause(q)
        kb.add_clause(sp.Not(q))
        
        # Future: conflict_report should identify both conflicts
        # For now, verify it's unsatisfiable
        result = kb.validate_kb()
        assert result is False
    
    def test_strategy_inference_chicken_kb(self):
        """Test inferring strategy consequences in ChickenKB context."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        grudge = sp.Symbol("grudge")
        p2_stays = sp.Symbol("p2_stays")
        
        # Strategy rules
        kb.add_clause(sp.Implies(p1_stays, grudge))
        kb.add_clause(sp.Equivalent(grudge, p2_stays))
        
        # Since p1_stays is in KB, should be able to infer grudge and p2_stays
        # Future: kb.infer_strategy_consequences() should return [grudge, p2_stays]
        # Verify entailment
        test_grudge = KnowledgeBase()
        test_grudge.clauses = kb.clauses.copy()
        test_grudge.add_clause(sp.Not(grudge))
        test_grudge.rebuild_kb()
        assert test_grudge.validate_kb() is False
        
        test_p2 = KnowledgeBase()
        test_p2.clauses = kb.clauses.copy()
        test_p2.add_clause(sp.Not(p2_stays))
        test_p2.rebuild_kb()
        assert test_p2.validate_kb() is False
    
    def test_cnf_output_format(self):
        """Test that KB output should be in CNF format as specified in proposal."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        # Add non-CNF clause
        kb.add_clause(sp.Implies(p, q))
        
        # Future: kb.get_cnf() should return KB in CNF format
        # CNF of (p -> q) is (~p OR q)
        # For now, verify we can construct the CNF equivalent
        cnf_kb = KnowledgeBase()
        cnf_kb.add_clause(sp.Or(sp.Not(p), q))
        
        # Both should be logically equivalent
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.add_clause(sp.Not(sp.Or(sp.Not(p), q)))
        test_kb.rebuild_kb()
        assert test_kb.validate_kb() is False


class TestFutureFunctionality:
    """Test cases for functionality that may be added in the future."""
    
    def test_entailment_checking(self):
        """Test checking if KB entails a query (future functionality)."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        kb.add_clause(sp.Implies(p, q))
        kb.add_clause(sp.Implies(q, r))
        kb.add_clause(p)
        
        # Future: kb.entails(r) should return True
        # For now, we can manually check by adding ~r and checking satisfiability
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.add_clause(sp.Not(r))
        test_kb.rebuild_kb()
        
        # If KB with ~r is unsatisfiable, then KB entails r
        is_unsatisfiable = test_kb.validate_kb() is False
        assert is_unsatisfiable  # KB should entail r
    
    def test_cnf_conversion(self):
        """Test that KB maintains CNF structure (future functionality)."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        # Add clauses that should be in CNF
        kb.add_clause(sp.Or(p, q))  # Already CNF
        kb.add_clause(sp.Or(sp.Not(p), r))  # Already CNF
        
        # Future: kb.to_cnf() should convert to CNF
        # For now, verify clauses are added correctly
        assert len(kb.clauses) == 2
    
    def test_resolution_inference(self):
        """Test resolution-based inference (future functionality)."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        # KB: (p OR q), (~p OR r)
        kb.add_clause(sp.Or(p, q))
        kb.add_clause(sp.Or(sp.Not(p), r))
        
        # Future: kb.resolve() should infer (q OR r)
        # For now, verify KB is satisfiable
        result = kb.validate_kb()
        assert result is not False
    
    def test_query_answering(self):
        """Test answering queries about the KB (future functionality)."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.add_clause(sp.Implies(p, q))
        kb.add_clause(p)
        
        # Future: kb.query(q) should return True
        # For now, verify KB is consistent with q
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.add_clause(q)
        test_kb.rebuild_kb()
        
        result = test_kb.validate_kb()
        assert result is not False  # KB is consistent with q
    
    def test_strategy_consistency_check(self):
        """Test checking if a strategy is internally consistent (future functionality)."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        p2_stays = sp.Symbol("p2_stays")
        
        # Strategy: if p2 stays, then p1 swerves
        kb.add_clause(sp.Implies(p2_stays, p1_swerves))
        
        # Future: kb.is_strategy_consistent() should check for contradictions
        # For now, verify satisfiability
        result = kb.validate_kb()
        assert result is not False
    
    def test_outcome_prediction(self):
        """Test predicting game outcomes from strategies (future functionality)."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        collision = sp.Symbol("collision")
        
        # Define collision outcome
        kb.add_clause(sp.Equivalent(collision, sp.And(p1_stays, p2_stays)))
        
        # Future: kb.predict_outcome(p1_stays=True, p2_stays=True) should return collision=True
        # For now, verify the relationship is encoded
        test_kb = ChickenKB()
        test_kb.clauses = kb.clauses.copy()
        test_kb.add_clause(p1_stays)
        test_kb.add_clause(p2_stays)
        test_kb.add_clause(collision)
        test_kb.rebuild_kb()
        
        result = test_kb.validate_kb()
        assert result is not False  # Consistent with collision
    
    def test_strategy_comparison(self):
        """Test comparing different strategies (future functionality)."""
        kb1 = ChickenKB()
        kb2 = ChickenKB()
        
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        
        # Strategy 1: always stay
        # (p1_stays already in KB)
        
        # Strategy 2: conditional - if p2 stays, then p1 swerves
        p1_swerves = sp.Symbol("p1_swerves")
        kb2.add_clause(sp.Implies(p2_stays, p1_swerves))
        
        # Future: kb1.compare(kb2) should identify differences
        # For now, verify both are valid
        assert kb1.validate_kb() is not False
        assert kb2.validate_kb() is not False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
