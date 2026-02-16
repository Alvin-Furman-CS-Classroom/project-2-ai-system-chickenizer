"""Unit tests for Module 1: Knowledge Base and ChickenKB classes.

This test suite is organized into the following test classes:
- TestKnowledgeBase: Basic KB operations (tell, ask, rebuild, validate, render, CNF)
- TestChickenKB: Chicken game-specific scenarios and strategies
- TestEssentialKBFunctionality: Core KB features (entailment, CNF, resolution, chaining, conflict reporting)
- TestFutureFunctionality: Placeholder tests for future enhancements
- TestForwardBackwardChaining: Explicit tests for forward/backward chain methods
- TestInvalidInputs: Error handling and input validation tests

Tests cover basic operations, CNF conversion, entailment, forward/backward chaining,
conflict reporting, resolution inference, consequence inference, and Chicken game-specific scenarios.
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
render_path = module1_kb.render_path


class TestKnowledgeBase:
    """Test cases for the base KnowledgeBase class."""
    
    def test_initialization(self):
        """Test that KB initializes with empty clauses."""
        kb = KnowledgeBase()
        assert kb.clauses == []
        assert kb.clauses_for_rendering == []
        assert kb.kb == sp.And()
    
    def test_tell_single_clause(self):
        """Test telling a single clause to the KB."""
        kb = KnowledgeBase()
        symbol = sp.Symbol("test_symbol")
        kb.tell([symbol])
        
        assert symbol in kb.clauses
        assert symbol in kb.clauses_for_rendering
        assert len(kb.clauses) == 1
    
    def test_tell_multiple_clauses(self):
        """Test telling multiple clauses at once."""
        kb = KnowledgeBase()
        s1 = sp.Symbol("s1")
        s2 = sp.Symbol("s2")
        s3 = sp.Symbol("s3")
        
        kb.tell([s1, s2, s3])
        
        assert len(kb.clauses) == 3
        assert len(kb.clauses_for_rendering) == 3
        assert s1 in kb.clauses and s1 in kb.clauses_for_rendering
        assert s2 in kb.clauses and s2 in kb.clauses_for_rendering
        assert s3 in kb.clauses and s3 in kb.clauses_for_rendering
    
    def test_tell_implication(self):
        """Test telling an implication clause."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        clause = sp.Implies(p, q)
        
        kb.tell([clause])
        
        assert clause in kb.clauses
        assert clause in kb.clauses_for_rendering
        assert len(kb.clauses) == 1
    
    def test_tell_equivalent(self):
        """Test telling an equivalence clause."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        clause = sp.Equivalent(p, q)
        
        kb.tell([clause])
        
        assert clause in kb.clauses
        assert len(kb.clauses) == 1
    
    def test_tell_negation(self):
        """Test telling a negation clause."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        clause = sp.Not(p)
        
        kb.tell([clause])
        
        assert clause in kb.clauses
        assert len(kb.clauses) == 1
    
    def test_tell_and(self):
        """Test telling an AND clause."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        clause = sp.And(p, q)
        
        kb.tell([clause])
        
        assert clause in kb.clauses
        assert len(kb.clauses) == 1
    
    def test_tell_or(self):
        """Test telling an OR clause."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        clause = sp.Or(p, q)
        
        kb.tell([clause])
        
        assert clause in kb.clauses
        assert len(kb.clauses) == 1
    
    def test_tell_multiple_clauses_list(self):
        """Test telling multiple clauses at once."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        clauses = [
            sp.Implies(p, q),
            sp.Implies(q, r),
            sp.Or(p, r)
        ]
        
        kb.tell(clauses)
        
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
        kb.tell([p])
        assert kb.kb == sp.And(p)
    
    def test_rebuild_kb_multiple_clauses(self):
        """Test rebuilding KB with multiple clauses."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        kb.tell([p, q])
        assert kb.kb == sp.And(p, q)
    
    def test_validate_kb_satisfiable_simple(self):
        """Test validation of a satisfiable KB."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        kb.tell([p])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_validate_kb_satisfiable_complex(self):
        """Test validation of a complex satisfiable KB."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        kb.tell([sp.Implies(p, q), sp.Implies(q, r), p])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_validate_kb_unsatisfiable_contradiction(self):
        """Test validation of an unsatisfiable KB with direct contradiction."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        kb.tell([p, sp.Not(p)])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is False
        assert conflict_report is not None
    
    def test_validate_kb_unsatisfiable_chain(self):
        """Test validation of an unsatisfiable KB with logical chain."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.tell([sp.Implies(p, q), p, sp.Not(q)])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is False
        assert conflict_report is not None
    
    def test_render_kb_empty(self):
        """Test rendering an empty KB."""
        kb = KnowledgeBase()
        assert kb.render_kb() == ""
    
    def test_render_kb_symbols(self):
        """Test rendering KB with symbols."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        kb.tell([p, q])
        assert kb.render_kb() == "p, q"
    
    def test_render_kb_implications(self):
        """Test rendering KB with implications."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        kb.tell([sp.Implies(p, q)])
        assert kb.render_kb() == "(p -> q)"
    
    def test_render_kb_equivalences(self):
        """Test rendering KB with equivalences."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        kb.tell([sp.Equivalent(p, q)])
        assert kb.render_kb() == "(p <=> q)"
    
    def test_render_kb_mixed_clauses(self):
        """Test rendering KB with mixed clause types."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        kb.tell([p, sp.Implies(p, q), sp.Equivalent(q, r)])
        output = kb.render_kb()
        assert output == "p, (p -> q), (q <=> r)"
    
    def test_tell_rebuilds_kb(self):
        """Test that tell automatically rebuilds KB."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        clause = sp.Implies(p, q)
        kb.tell([clause])
        assert kb.kb == sp.And(clause)
    
    def test_tell_multiple_rebuilds_kb(self):
        """Test that tell with multiple clauses automatically rebuilds KB."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        kb.tell([p, q])
        assert kb.kb == sp.And(p, q)
    
    def test_complex_logical_formula(self):
        """Test KB with complex nested logical formulas."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        # Complex formula: (p -> q) AND (q -> r) AND (p OR r)
        kb.tell([sp.Implies(p, q), sp.Implies(q, r), sp.Or(p, r)])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_xor_representation(self):
        """Test representing XOR (exclusive or) using implications."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        # p XOR q = (p -> ~q) AND (q -> ~p) AND (p OR q)
        kb.tell([sp.Implies(p, sp.Not(q)), sp.Implies(q, sp.Not(p)), sp.Or(p, q)])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None


class TestChickenKB:
    """Test cases for the ChickenKB class, focused on strategy and outcome representation."""
    
    def test_initialization(self):
        """Test that ChickenKB initializes as empty KB."""
        kb = ChickenKB()
        assert len(kb.clauses) == 0
        assert len(kb.clauses_for_rendering) == 0
    
    def test_strategy_grudge_representation(self):
        """Test representing a grudge strategy: if opponent stays, I stay."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        grudge = sp.Symbol("grudge")
        
        # Grudge strategy: if p1 stays, then grudge is true
        # If grudge is true, then p2 stays
        kb.tell([sp.Implies(p1_stays, grudge), sp.Equivalent(grudge, p2_stays)])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_strategy_tit_for_tat(self):
        """Test representing tit-for-tat strategy."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        p2_swerves = sp.Symbol("p2_swerves")
        
        # Tit-for-tat: p1's action matches p2's previous action
        # This is simplified - in full implementation would track previous round
        kb.tell([sp.Equivalent(p1_stays, p2_stays), sp.Equivalent(p1_swerves, p2_swerves)])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_strategy_always_swerve(self):
        """Test representing always-swerve strategy."""
        kb = ChickenKB()
        p1_swerves = sp.Symbol("p1_swerves")
        
        # Always swerve: p1_swerves is always true
        kb.tell([p1_swerves])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_strategy_always_stay(self):
        """Test representing always-stay strategy."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        
        # Always stay: p1_stays is always true
        kb.tell([p1_stays])
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_outcome_collision(self):
        """Test representing collision outcome: both players stay."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        collision = sp.Symbol("collision")
        
        # Collision occurs when both stay
        kb.tell([sp.Equivalent(collision, sp.And(p1_stays, p2_stays))])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_outcome_mutual_cooperation(self):
        """Test representing mutual cooperation: both swerve."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        p2_swerves = sp.Symbol("p2_swerves")
        mutual_cooperation = sp.Symbol("mutual_cooperation")
        
        # Mutual cooperation: both swerve
        kb.tell([sp.Equivalent(mutual_cooperation, sp.And(p1_swerves, p2_swerves))])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_action_mutual_exclusivity(self):
        """Test that stay and swerve are mutually exclusive for a player."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        
        # A player cannot both stay and swerve
        kb.tell([sp.Implies(p1_stays, sp.Not(p1_swerves))])
        kb.tell([sp.Implies(p1_swerves, sp.Not(p1_stays))])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_action_completeness(self):
        """Test that a player must either stay or swerve."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        
        # A player must choose one action
        kb.tell([sp.Or(p1_stays, p1_swerves)])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_strategy_conditional_response(self):
        """Test representing conditional response strategy."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        
        # Conditional: if p2 stays, then p1 swerves (chicken out)
        kb.tell([sp.Implies(p2_stays, p1_swerves)])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_strategy_escalation(self):
        """Test representing escalation strategy: respond in kind."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        p2_swerves = sp.Symbol("p2_swerves")
        
        # Escalation: match opponent's action
        kb.tell([sp.Implies(p2_stays, p1_stays)])
        kb.tell([sp.Implies(p2_swerves, p1_swerves)])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
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
        kb.tell([sp.Equivalent(p1_wins, sp.And(p1_stays, p2_swerves))])
        # p2 wins if p2 stays and p1 swerves
        kb.tell([sp.Equivalent(p2_wins, sp.And(p2_stays, p1_swerves))])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_inconsistent_strategy(self):
        """Test that inconsistent strategies are detected as unsatisfiable."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        
        # Contradictory: p1 both stays and swerves
        kb.tell([p1_stays])
        kb.tell([p1_swerves])
        kb.tell([sp.Implies(p1_stays, sp.Not(p1_swerves))])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is False
        assert conflict_report is not None
    
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
        kb.tell([sp.Implies(p1_stays, grudge)])
        kb.tell([sp.Equivalent(grudge, p2_stays)])
        kb.tell([sp.Equivalent(collision, sp.And(p1_stays, p2_stays))])
        kb.tell([sp.Implies(p1_stays, sp.Not(p1_swerves))])
        kb.tell([sp.Implies(p2_stays, sp.Not(p2_swerves))])
        
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_render_chicken_kb(self):
        """Test rendering ChickenKB with strategy clauses."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        grudge = sp.Symbol("grudge")
        p2_stays = sp.Symbol("p2_stays")
        kb.tell([sp.Implies(p1_stays, grudge)])
        kb.tell([sp.Equivalent(grudge, p2_stays)])
        output = kb.render_kb()
        assert "p1_stays" in output
        assert "grudge" in output
        assert "p2_stays" in output
        assert output == "(p1_stays -> grudge), (grudge <=> p2_stays)"


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
        
        kb.tell([sp.Implies(p, q)])
        kb.tell([p])
        
        # KB should entail q - use ask() method
        assert kb.ask(q) is True  # KB entails q
    
    def test_entailment_checking_chain(self):
        """Test entailment through logical chain: (p -> q), (q -> r), p entails r."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        kb.tell([sp.Implies(p, q)])
        kb.tell([sp.Implies(q, r)])
        kb.tell([p])
        
        # KB should entail r - use ask() method
        assert kb.ask(r) is True  # KB entails r
    
    def test_entailment_checking_does_not_entail(self):
        """Test that KB does not entail a query when it shouldn't."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.tell([p])
        # KB does not contain q, so should not entail q
        assert kb.ask(q) is False  # KB does not entail q
    
    def test_entailment_interface(self):
        """Test that KB has an ask() method for querying."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.tell([sp.Implies(p, q), p])
        
        # Use ask() method for entailment checking
        assert kb.ask(q) is True
    
    def test_cnf_conversion_implication(self):
        """Test that implications should be convertible to CNF: (p -> q) = (~p OR q)."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.tell([sp.Implies(p, q)])
        
        # Future: kb.to_cnf() should convert (p -> q) to (~p OR q)
        # CNF form of (p -> q) is (~p OR q)
        cnf_clause = sp.Or(sp.Not(p), q)
        cnf_kb = KnowledgeBase()
        cnf_kb.tell([cnf_clause])
        
        # Both should be logically equivalent
        # Test by checking if KB U {~cnf} is unsatisfiable
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.tell([sp.Not(cnf_clause)])
        test_kb.rebuild_kb()
        
        # If original KB entails CNF form, then they're equivalent
        # This is a simplified check - full CNF conversion would be more thorough
        is_sat, _ = test_kb.validate_kb()
        assert is_sat is False
    
    def test_cnf_conversion_equivalent(self):
        """Test that equivalences should be convertible to CNF."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.tell([sp.Equivalent(p, q)])
        
        # CNF form of (p <-> q) is (~p OR q) AND (p OR ~q)
        cnf_kb = KnowledgeBase()
        cnf_kb.tell([sp.Or(sp.Not(p), q)])
        cnf_kb.tell([sp.Or(p, sp.Not(q))])
        
        # Both should be logically equivalent
        # Test by checking mutual entailment
        test1 = KnowledgeBase()
        test1.clauses = kb.clauses.copy()
        test1.tell([sp.Not(sp.And(sp.Or(sp.Not(p), q), sp.Or(p, sp.Not(q))))])
        test1.rebuild_kb()
        
        test2 = KnowledgeBase()
        test2.clauses = cnf_kb.clauses.copy()
        test2.tell([sp.Not(sp.Equivalent(p, q))])
        test2.rebuild_kb()
        
        # Both should be unsatisfiable if equivalent
        is_sat1, _ = test1.validate_kb()
        is_sat2, _ = test2.validate_kb()
        assert is_sat1 is False
        assert is_sat2 is False
    
    def test_cnf_validation(self):
        """Test that KB should be able to validate if it's in CNF format."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        # Add clauses that are already in CNF (disjunctions of literals)
        kb.tell([sp.Or(p, q)])
        kb.tell([sp.Or(sp.Not(p), r)])
        kb.tell([sp.Or(q, sp.Not(r))])
        
        # Future: kb.is_cnf() should return True
        # For now, verify these are valid CNF clauses
        is_sat, _ = kb.validate_kb()
        assert is_sat is True
    
    def test_cnf_validation_not_cnf(self):
        """Test that KB should detect when clauses are not in CNF."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        # Add clause that is NOT in CNF (has nested AND)
        kb.tell([sp.And(p, q)])
        
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
        kb.tell([sp.Or(p, q)])
        kb.tell([sp.Or(sp.Not(p), r)])
        
        # Resolution should infer (q OR r)
        # Future: kb.resolve() should return [q OR r]
        # Verify that (q OR r) is entailed
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.tell([sp.Not(sp.Or(q, r))])  # Add ~(q OR r) = (~q AND ~r)
        test_kb.tell([sp.And(sp.Not(q), sp.Not(r))])
        test_kb.rebuild_kb()
        
        # If KB entails (q OR r), then KB U {~(q OR r)} is unsatisfiable
        is_sat, _ = test_kb.validate_kb()
        assert is_sat is False
    
    def test_forward_chaining(self):
        """Test forward chaining inference method."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        s = sp.Symbol("s")
        
        # Rules: p -> q, q -> r, r -> s
        # Facts: p
        kb.tell([sp.Implies(p, q)])
        kb.tell([sp.Implies(q, r)])
        kb.tell([sp.Implies(r, s)])
        kb.tell([p])
        
        # Forward chaining should infer: q, then r, then s
        # Future: kb.forward_chain() should return [q, r, s]
        # Verify that s is entailed using ask()
        assert kb.ask(s) is True  # KB entails s
    
    def test_backward_chaining(self):
        """Test backward chaining inference method."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        # Rules: p -> q, q -> r
        # Goal: prove r
        kb.tell([sp.Implies(p, q)])
        kb.tell([sp.Implies(q, r)])
        kb.tell([p])
        
        # Backward chaining: to prove r, need q; to prove q, need p; p is given
        # Future: kb.backward_chain(r) should return True
        # Verify that r is entailed using ask()
        assert kb.ask(r) is True  # KB entails r
    
    def test_infer_logical_consequences(self):
        """Test inferring all logical consequences from KB."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        kb.tell([sp.Implies(p, q)])
        kb.tell([sp.Implies(q, r)])
        kb.tell([p])
        
        # Future: kb.infer_consequences() should return all entailed facts
        # Should include: q, r, and potentially others depending on implementation
        # For now, verify that q and r are both entailed using ask()
        assert kb.ask(q) is True
        assert kb.ask(r) is True
    
    def test_conflict_reporting_direct_contradiction(self):
        """Test that KB should report which clauses conflict when inconsistent."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        
        kb.tell([p])
        kb.tell([sp.Not(p)])
        
        # validate_kb() returns (False, conflict_report)
        # conflict_report should identify that p and ~p conflict
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is False
        assert conflict_report is not None
        assert conflict_report.conflict_type == "direct"
        assert len(conflict_report.conflicting_clauses) == 2
    
    def test_conflict_reporting_chain_contradiction(self):
        """Test conflict reporting for contradictions through logical chain."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.tell([sp.Implies(p, q)])
        kb.tell([p])
        kb.tell([sp.Not(q)])
        
        # conflict_report should identify the chain: p -> q, p, ~q
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is False
        assert conflict_report is not None
        assert conflict_report.conflict_type == "chain"
        assert len(conflict_report.conflicting_clauses) == 3
    
    def test_conflict_reporting_multiple_conflicts(self):
        """Test conflict reporting when multiple conflicts exist."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.tell([p])
        kb.tell([sp.Not(p)])
        kb.tell([q])
        kb.tell([sp.Not(q)])
        
        # conflict_report should identify conflicts
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is False
        assert conflict_report is not None
        # May detect first conflict (direct) or multiple
        assert conflict_report.conflict_type in ["direct", "minimal", "all"]
    
    def test_strategy_inference_chicken_kb(self):
        """Test inferring strategy consequences in ChickenKB context."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        grudge = sp.Symbol("grudge")
        p2_stays = sp.Symbol("p2_stays")
        
        # Strategy rules
        kb.tell([p1_stays])  # Add p1_stays as a fact
        kb.tell([sp.Implies(p1_stays, grudge)])
        kb.tell([sp.Equivalent(grudge, p2_stays)])
        
        # Since p1_stays is in KB, should be able to infer grudge and p2_stays
        # Future: kb.infer_strategy_consequences() should return [grudge, p2_stays]
        # Verify entailment using ask() method
        assert kb.ask(grudge) is True
        assert kb.ask(p2_stays) is True
    
    def test_cnf_output_format(self):
        """Test that KB output should be in CNF format as specified in proposal."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        # Add non-CNF clause
        kb.tell([sp.Implies(p, q)])
        
        # Future: kb.get_cnf() should return KB in CNF format
        # CNF of (p -> q) is (~p OR q)
        # For now, verify we can construct the CNF equivalent
        cnf_kb = KnowledgeBase()
        cnf_kb.tell([sp.Or(sp.Not(p), q)])
        
        # Both should be logically equivalent
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.tell([sp.Not(sp.Or(sp.Not(p), q))])
        test_kb.rebuild_kb()
        is_sat, _ = test_kb.validate_kb()
        assert is_sat is False


class TestFutureFunctionality:
    """Test cases for functionality that may be added in the future."""
    
    def test_entailment_checking(self):
        """Test checking if KB entails a query (future functionality)."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        kb.tell([sp.Implies(p, q)])
        kb.tell([sp.Implies(q, r)])
        kb.tell([p])
        
        # Use ask() method for entailment checking
        assert kb.ask(r) is True  # KB should entail r
    
    def test_cnf_conversion(self):
        """Test that KB maintains CNF structure (future functionality)."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        r = sp.Symbol("r")
        
        # Add clauses that should be in CNF
        kb.tell([sp.Or(p, q)])  # Already CNF
        kb.tell([sp.Or(sp.Not(p), r)])  # Already CNF
        
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
        kb.tell([sp.Or(p, q)])
        kb.tell([sp.Or(sp.Not(p), r)])
        
        # Future: kb.resolve() should infer (q OR r)
        # For now, verify KB is satisfiable
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_query_answering(self):
        """Test answering queries about the KB (future functionality)."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        kb.tell([sp.Implies(p, q)])
        kb.tell([p])
        
        # Future: kb.query(q) should return True
        # For now, verify KB is consistent with q
        test_kb = KnowledgeBase()
        test_kb.clauses = kb.clauses.copy()
        test_kb.tell([q])
        test_kb.rebuild_kb()
        
        is_sat, _ = test_kb.validate_kb()
        assert is_sat is True  # KB is consistent with q
    
    def test_strategy_consistency_check(self):
        """Test checking if a strategy is internally consistent (future functionality)."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p1_swerves = sp.Symbol("p1_swerves")
        p2_stays = sp.Symbol("p2_stays")
        
        # Strategy: if p2 stays, then p1 swerves
        kb.tell([sp.Implies(p2_stays, p1_swerves)])
        
        # Future: kb.is_strategy_consistent() should check for contradictions
        # For now, verify satisfiability
        is_sat, conflict_report = kb.validate_kb()
        assert is_sat is True
        assert conflict_report is None
    
    def test_outcome_prediction(self):
        """Test predicting game outcomes from strategies (future functionality)."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        collision = sp.Symbol("collision")
        
        # Define collision outcome
        kb.tell([sp.Equivalent(collision, sp.And(p1_stays, p2_stays))])
        
        # Future: kb.predict_outcome(p1_stays=True, p2_stays=True) should return collision=True
        # For now, verify the relationship is encoded
        test_kb = ChickenKB()
        test_kb.clauses = kb.clauses.copy()
        test_kb.tell([p1_stays])
        test_kb.tell([p2_stays])
        test_kb.tell([collision])
        test_kb.rebuild_kb()
        
        is_sat, _ = test_kb.validate_kb()
        assert is_sat is True  # Consistent with collision
    
    def test_strategy_comparison(self):
        """Test comparing different strategies (future functionality)."""
        kb1 = ChickenKB()
        kb2 = ChickenKB()
        
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        
        # Strategy 1: always stay
        kb1.tell([p1_stays])
        
        # Strategy 2: conditional - if p2 stays, then p1 swerves
        p1_swerves = sp.Symbol("p1_swerves")
        kb2.tell([sp.Implies(p2_stays, p1_swerves)])
        
        # Future: kb1.compare(kb2) should identify differences
        # For now, verify both are valid
        is_sat1, _ = kb1.validate_kb()
        is_sat2, _ = kb2.validate_kb()
        assert is_sat1 is True
        assert is_sat2 is True


class TestForwardBackwardChaining:
    """Test cases for forward_chain and backward_chain methods (assumes correct implementation)."""

    def test_chain_simple_implication(self):
        """Test forward chaining: p1_stays -> p2_swerves, given p1_stays, query p2_swerves."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_swerves = sp.Symbol("p2_swerves")
        kb.tell([p1_stays, sp.Implies(p1_stays, p2_swerves)])

        assert render_path(kb.forward_chain(p2_swerves)) == "(p1_stays -> p2_swerves)"
        assert render_path(kb.backward_chain(p2_swerves), False) == "p1_stays <= (p1_stays -> p2_swerves)"

    def test_chain_of_implications(self):
        """Test forward chaining: p1_stays -> grudge -> p2_stays, given p1_stays, query p2_stays."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_stays = sp.Symbol("p2_stays")
        grudge = sp.Symbol("grudge")
        kb.tell([p1_stays, sp.Implies(p1_stays, grudge), sp.Implies(grudge, p2_stays)])

        assert render_path(kb.forward_chain(p2_stays)) == "(p1_stays -> grudge) => (grudge -> p2_stays)"
        assert render_path(kb.backward_chain(p2_stays), False) == "p1_stays <= (p1_stays -> grudge) <= (grudge -> p2_stays)"

    def test_chain_query_is_direct_fact(self):
        """Test forward/backward chaining when query is a direct fact in the KB."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        kb.tell([p1_stays])

        assert render_path(kb.forward_chain(p1_stays)) == "p1_stays"
        assert render_path(kb.backward_chain(p1_stays), False) == "p1_stays"

    def test_chain_query_not_derivable(self):
        """Test forward/backward chaining when query is not derivable (rules only, no facts)."""
        kb = ChickenKB()
        p1_stays = sp.Symbol("p1_stays")
        p2_swerves = sp.Symbol("p2_swerves")
        collision = sp.Symbol("collision")
        kb.tell([sp.Implies(p1_stays, p2_swerves), sp.Implies(p2_swerves, collision)])

        assert render_path(kb.forward_chain(collision)) == ""
        assert render_path(kb.backward_chain(collision), False) == ""




class TestInvalidInputs:
    """Test cases for invalid input handling and error cases."""
    
    def test_tell_with_non_list(self):
        """Test that tell() raises TypeError when given non-list input."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        with pytest.raises(TypeError):
            kb.tell(p)  # Single expression, not a list
    
    def test_tell_with_non_expression_in_list(self):
        """Test that tell() raises TypeError when list contains non-SymPy expressions."""
        kb = KnowledgeBase()
        with pytest.raises(TypeError):
            kb.tell(["not_a_symbol", 42])
    
    def test_ask_with_non_expression(self):
        """Test that ask() raises TypeError when query is not a SymPy expression."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        kb.tell([p])
        with pytest.raises(TypeError):
            kb.ask("not_a_symbol")
    
    def test_forward_chain_with_non_expression(self):
        """Test that forward_chain() raises TypeError when query is not a SymPy expression."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        kb.tell([p])
        with pytest.raises(TypeError):
            kb.forward_chain("not_a_symbol")
    
    def test_backward_chain_with_non_expression(self):
        """Test that backward_chain() raises TypeError when query is not a SymPy expression."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        kb.tell([p])
        with pytest.raises(TypeError):
            kb.backward_chain("not_a_symbol")
    
    def test_resolve_with_non_cnf_clauses(self):
        """Test that resolve() handles non-CNF clauses."""
        kb = KnowledgeBase()
        p = sp.Symbol("p")
        q = sp.Symbol("q")
        
        # Resolve expects CNF (sp.Or or single literals)
        # Passing implications should return None
        result = kb.resolve(sp.Implies(p, q), sp.Implies(q, p))
        assert result is None
    
    def test_empty_list_to_tell(self):
        """Test that tell() handles empty list gracefully."""
        kb = KnowledgeBase()
        kb.tell([])  # Should not error
        assert len(kb.clauses) == 0
        assert kb.render_kb() == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
