# Module 1: Strategy Logic Encoder, Knowledge Base


# Dependencies:
from typing import Any
import sympy as sp


class KnowledgeBase:

    def __init__(self):
        self.clauses = []
        self.clauses_for_rendering = []

        #CNF knowledge base, "AND of ORs" rather than "OR of ANDs"
        self.kb = sp.And() 

    def tell(self, clauses:list[sp.Expr]):
        self.clauses.extend(clauses)
        self.clauses_for_rendering.extend(clauses)
        self.rebuild_kb()
    
    def ask(self, query:sp.Expr):
        return not sp.satisfiable(sp.And(self.kb, sp.Not(query)))

    def rebuild_kb(self):
        if not self.clauses:
            self.kb = sp.And()
        else:
            self.kb = sp.And(*self.clauses)
    
    def validate_kb(self):
        return sp.satisfiable(self.kb)

    def is_cnf(self):
        #rules of CNF: each clause is OR of literals, top level is AND of clauses
        return all(isinstance(clause, sp.Or) for clause in self.clauses)
    
    def to_cnf(self):
        self.kb = sp.to_cnf(self.kb)
        self.clauses = [clause for clause in self.kb.args]

    def render_kb(self):
        output = ""
        for clause in self.clauses_for_rendering:
            if type(clause) == sp.Implies:
                output = output + str(clause.args[0]) + " -> " + str(clause.args[1]) + ", "
            elif type(clause) == sp.Equivalent:
                output = output + str(clause.args[0]) + " <=> " + str(clause.args[1]) + ", "
            else:
                output = output + str(clause) + ", "
        print(output[:-2])
    
class ChickenKB(KnowledgeBase):
    def __init__(self):
        super().__init__()
        #preadding the "p1_stays" symbol to the knowledge base, since we operate under worst-case scenario assumptions
        #This is a placeholder--across multiple rounds, we'd want p1 to be able to change their aggression

def main():
    our_kb = ChickenKB()
    # Create symbols for all the variables we'll use
    p1_stays = sp.Symbol("p1_stays")
    # grudge = sp.Symbol("grudge")
    # p2_stays = sp.Symbol("p2_stays")
    p2_swerves = sp.Symbol("p2_swerves")
    
    our_kb.tell([p1_stays, sp.Implies(p1_stays, p2_swerves)])
    print("Does KB entail p2_swerves?", our_kb.entails(p2_swerves))
    our_kb.render_kb()
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

if __name__ == "__main__":
    main()