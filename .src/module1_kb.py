# Module 1: Strategy Logic Encoder, Knowledge Base


# Dependencies:
from typing import Any


import sympy as sp

class KnowledgeBase:
    def __init__(self):
        self.clauses = []

        #symbol set that grows parallel to the clauses list
        self.symbols = set[sp.Symbol]()

        #CNF knowledge base that grows parallel to the clauses list
        self.kb = sp.And() #applying AND between each item in clauses

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
        self.clauses.extend(clauses)
        self.rebuild_kb()

    
def main():
    our_kb = KnowledgeBase()
    our_kb.add_symbol(sp.Symbol("P"))
    print(our_kb.kb)


if __name__ == "__main__":
    main()