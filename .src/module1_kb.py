# Module 1: Strategy Logic Encoder, Knowledge Base


# Dependencies:
from typing import Any
import sympy as sp


class KnowledgeBase:

    def __init__(self):
        self.clauses = []

        #symbol set that grows parallel to the clauses list
        self.symbols = set[sp.Symbol]()

        #CNF knowledge base
        self.kb = sp.And() 

    def rebuild_kb(self):
        if not self.clauses:
            self.kb = sp.And()
        else:
            self.kb = sp.And(*self.clauses)

    def add_symbol(self, symbol):
        self.symbols.add(symbol)
        self.clauses.append(symbol)
        self.rebuild_kb()

    def add_clause(self, clause):
        self.clauses.append(clause)
        self.rebuild_kb()

    def add_clauses(self, clauses):

        #note: might be useful to build strategies
        self.clauses.extend(clauses)
        self.rebuild_kb()
    
    def validate_kb(self):
        return sp.satisfiable(self.kb)

    def render_kb(self):
        output = ""
        for clause in self.clauses:
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
        self.add_symbol(sp.Symbol("p1_stays"))

def main():
    our_kb = ChickenKB()
    # Create symbols for all the variables we'll use
    p1_stays = sp.Symbol("p1_stays")
    grudge = sp.Symbol("grudge")
    p2_stays = sp.Symbol("p2_stays")
    p2_swerves = sp.Symbol("p2_swerves")
    
    our_kb.add_clause(sp.Implies(p1_stays, grudge))
    our_kb.add_clause(sp.Equivalent(grudge, p2_stays))
    our_kb.add_clause(sp.Implies(sp.Not(p1_stays), sp.Not(grudge)))
    our_kb.add_clause(sp.Equivalent(sp.Not(p2_stays), p2_swerves))
    our_kb.render_kb()
    print(our_kb.validate_kb())

if __name__ == "__main__":
    main()