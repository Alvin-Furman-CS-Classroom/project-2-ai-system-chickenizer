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

    """tell:
    Adds clauses to knowledge base.
    """
    def tell(self, clauses:list[sp.Expr]):
        self.clauses.extend(clauses)
        self.clauses_for_rendering.extend(clauses)
        self.rebuild_kb()
    
    """ask:
    Checks if knowledge base entails a given query.
    """
    def ask(self, query:sp.Expr):
        return not sp.satisfiable(sp.And(self.kb, sp.Not(query)))

    """rebuild_kb:
    Rebuilds knowledge base from the clauses.
    """
    def rebuild_kb(self):
        if not self.clauses:
            self.kb = sp.And()
        else:
            self.kb = sp.And(*self.clauses)
    
    def validate_kb(self):
        return sp.satisfiable(self.kb)

    """is_cnf:
    Checks if knowledge base is in CNF (Conjunctive Normal Form).
    """
    def is_cnf(self):
        #rules of CNF: each clause is OR of literals, top level is AND of clauses
        return all(isinstance(clause, sp.Or) for clause in self.clauses)
    
    """to_cnf:
    Converts knowledge base to CNF.
    """
    def to_cnf(self):
        self.kb = sp.to_cnf(self.kb)
        self.clauses = [clause for clause in self.kb.args]

    """render_kb:
    Renders knowledge base as a string.
    """
    def render_kb(self):
        output = ""
        for clause in self.clauses_for_rendering:
            if type(clause) == sp.Implies:
                output = output + "(" + str(clause.args[0]) + " -> " + str(clause.args[1]) + "), "
            elif type(clause) == sp.Equivalent:
                output = output + "(" + str(clause.args[0]) + " <=> " + str(clause.args[1]) + "), "
            else:
                output = output + str(clause) + ", "
        print(output[:-2].strip())

    """forward_chain:
    # Forward chains the knowledge base to entailed facts.
    """
    def forward_chain(self, query:sp.Expr):
        path = []
        facts = self.clauses.copy()
        if query in facts: 
            # print("query in facts:", query)
            return [query]

        new_facts_added = True
        while new_facts_added:
            new_facts_added = False
            for clause in self.clauses:
                # print("clause:", clause)
                if len(clause.args) != 0:
                    if not clause.args[0] in facts:
                        continue
                    if clause.args[-1] in facts:
                        continue

                    new_facts_added = True
                    facts.append(clause.args[-1])
                    path.append(clause)
                    if clause.args[-1] == query:
                        # print("query found in clause:", clause)
                        return path
        return []

    """backward_chain: 
    Backward chains the knowledge base to the query.
    """
    def backward_chain(self, query:sp.Expr, visited=None):
        if visited == None:
            visited = set()

        
        if query in visited:
            # print("query already visited:", query)
            return []

        visited.add(query)
        
        # Base case
        if query in self.clauses:
            # print("query in clauses:", query)
            return [query]

        for clause in self.clauses:
            if len(clause.args) != 0:
                if clause.args[-1] == query:
                    recur_path = self.backward_chain(clause.args[0], visited)
                    # print("recur_path:", recur_path)
                    if recur_path != []:
                        # print("recur_path + [clause, query]:", recur_path + [clause, query])
                        return recur_path + [clause]#, query]
        return []
        
class ChickenKB(KnowledgeBase):
    def __init__(self):
        super().__init__()
        rnd_history = {}
        rnd = 0
        #preadding the "p1_stays" symbol to the knowledge base, since we operate under worst-case scenario assumptions
        #This is a placeholder--across multiple rounds, we'd want p1 to be able to change their aggression
    
    def reset_kb(self):
        self.clauses = []
        self.clauses_for_rendering = []
        self.kb = sp.And()
        self.rnd = 0
        round_history = {}


def render_path(path:list[sp.Expr], forward:bool = True) -> str:
    output = ""
    if forward: delimiter = " => "
    else: delimiter = " <= "
    for clause in path: 
        if type(clause) == sp.Implies:
            output = output + "(" + str(clause.args[0]) + " -> " + str(clause.args[1]) + ")" + delimiter        
        elif type(clause) == sp.Equivalent:
            output = output + "(" + str(clause.args[0]) + " <=> " + str(clause.args[1]) + ")" + delimiter
        
        else:
            output = output + str(clause) + delimiter
    return output[:-len(delimiter)].strip()

def main():
    our_kb = ChickenKB()
    # Create symbols for all the variables we'll use
    p1_stays = sp.Symbol("p1_stays")
    # grudge = sp.Symbol("grudge")
    # p2_stays = sp.Symbol("p2_stays")
    p2_swerves = sp.Symbol("p2_swerves")
    
    our_kb.tell([p1_stays, sp.Implies(p1_stays, p2_swerves)])
    print("Does KB entail p2_swerves?", our_kb.ask(p2_swerves))
    our_kb.render_kb()

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
    print("Forward chaining:", render_path((our_kb.forward_chain(p2_swerves)), " => "))
    print("Backward chaining:", render_path((our_kb.backward_chain(p2_swerves)), " <= "))

if __name__ == "__main__":
    main()