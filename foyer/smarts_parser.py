import itertools
import plyplus
import parmed.periodic_table as pt


smarts_grammar = plyplus.Grammar("""
    start: string;

    // Rules
    @string: chain nonlastbranch* lastbranch?;
    @chain: atom chain | atom;
    @nonlastbranch: LPAR branch RPAR;
    @lastbranch: branch;
    branch: string;
    atom: LBRACKET or_expression RBRACKET atom_label?;
    atom_label: NUM;
    ?or_expression: (or_expression or_symbol)? and_expression;
    ?and_expression: (and_expression and_symbol)? atom_id;
    @and_symbol: SEMI | AMP;
    @or_symbol: COMMA;
    atom_id: atom_symbol | HASH atomic_num | any_atom | DOLLAR LPAR matches_string RPAR | has_label | 'D' neighbor_count | 'R' ring_size;
    atom_symbol: SYMBOL;
    atomic_num: NUM;
    any_atom: STAR;
    matches_string: string ;
    has_label: LABEL ;
    neighbor_count: NUM;
    ring_size: NUM;

    // Tokens
    HASH: '\#';
    LBRACKET: '\[';
    RBRACKET: '\]';
    LPAR: '\(';
    RPAR: '\)';
    COMMA: '\,';
    SEMI: '\;';
    AMP: '\&';
    STAR: '\*';
    DOLLAR: '\$';
    NUM: '[\d]+';
    LABEL: '\%[a-z_]+([0-9][a-z_]?)*' ;
    // Tokens for chemical elements
    SYMBOL: 'C[laroudsemf]?|Os?|N[eaibdpos]?|S[icernbmg]?|P[drmtboau]?|H[eofgas]?|A[lrsgutcm]|B[eraik]?|Dy|E[urs]|F[erm]?|G[aed]|I[nr]?|Kr?|L[iaur]|M[gnodt]|R[buhenaf]|T[icebmalh]|U|V|W|Xe|Yb?|Z[nr]';

""")


def parse(expr):
    tree = smarts_grammar.parse(expr)
    assert tree.tail
    return tree

def show_result(s):
    t = parse(s)
    print("parsing: {}\nresult :{}\n".format(s,t))


def find_atomtypes(atoms, rules):
    for atom in atoms:
        atom.whitelist = set()
        atom.blacklist = set()

    found_something = True
    while(found_something):
        found_something = False
        for atom in atoms:
            for rule in rules:
                if rule not in atom.whitelist and rule not in atom.blacklist:
                    if rule.matches(atom):
                        atom.whitelist.add(rule)
                        atom.blacklist |= rule.overrides
                        found_something = True



class Rule(object):
    def __init__(self, name, smarts_string, overrides=None):
        self.name = name
        self.smarts_string = smarts_string
        self.ast = smarts_grammar.parse(smarts_string)
        self.ast.calc_parents()
        if overrides:
            self.overrides = set(overrides)
        else:
            self.overrides = set()

    def __repr__(self):
        return 'Rule({},{},{})'.format(self.name, self.smarts_string, self.overrides)

    def start_atom_expr(self):
        return self.ast.tail[0].tail[0]

    def _neighbor_atom_exprs(self, atom_expr):
        # the parent is an 'atom', which may have siblings
        atom = atom_expr.parent()
        if atom.is_last_kid:
            # we have reached the end of a branch: no neighbors here
            return []
        else:
            if atom.next_kid.head == 'atom':
                # we only have one neighbor, which is an atom
                # let's return the atom_expr it contains
                return [atom.next_kid.tail[0]]
            else:
                # we may have multiple neighbors: one or more branches, possibly followed by an atom
                assert atom.next_kid.head == 'branch'
                current_neighbor = atom.next_kid
                neighbor_atom_exprs = []
                while current_neighbor:
                    if current_neighbor.head == 'branch':
                        # add the expression of the first atom of the branch to the list
                        neighbor_atom_exprs.append(current_neighbor.tail[0].tail[0])
                    if current_neighbor.head == 'atom':
                        # add the expression of the atom to the list
                        neighbor_atom_exprs.append(current_neighbor.tail[0])
                        # this is an atom after the last branch (or there was no branch), so there are no more neighbors
                        break
                    if current_neighbor.is_last_kid:
                        # no more neighbors
                        break

                    # there are more neighbors
                    current_neighbor = current_neighbor.next_kid

                return neighbor_atom_exprs

    def matches(self, atom):
        return self._matches(atom, self.start_atom_expr())

    def _matches(self, atom, atom_expr):

        # check if atom matches atom_expr
        if self._atom_expr_matches(atom_expr, atom):
            # let's check if neighbors match (recursively)

            # get all neighbors in rule
            neighbor_atom_exprs = self._neighbor_atom_exprs(atom_expr)
            # print('Rule: {}'.format(self.smarts_string))
            # print('Neighbor exprs of {} are {}'.format(atom_expr, neighbor_atom_exprs))

            if not neighbor_atom_exprs:
                # no expressions given for neighbor atoms: it's a match
                return True

            # get all neighbors in graph
            neighbor_atoms = atom.bond_partners

            # compute all combinations of rule-atom to graph-atom pairings
            assert(len(neighbor_atoms) >= len(neighbor_atom_exprs))
            possible_match_sets = [zip(x, neighbor_atom_exprs) for x in itertools.permutations(neighbor_atoms, len(neighbor_atom_exprs))]

            # for all possible matchings of neighbor atoms to neighbor expressions
            for possible_match_set in possible_match_sets:

                # for all pair in a match set we check if all can be satisfied
                for neighbor_atom, neighbor_atom_expr in possible_match_set:
                    # check recursively if they match
                    if not self._matches(neighbor_atom, neighbor_atom_expr):
                        break
                else:
                    # we get here if we did not break in the loop
                    return True

            # none of the matchings work
            return False

        else:
            # the current atom did not match
            return False

    def _atom_expr_matches(self, atom_expr, atom):
        if atom_expr.head == 'and_expression':
            return self._atom_expr_matches(atom_expr.tail[0], atom) and self._atom_expr_matches(atom_expr.tail[1], atom)
        elif atom_expr.head == 'or_expression':
            return self._atom_expr_matches(atom_expr.tail[0], atom) or self._atom_expr_matches(atom_expr.tail[1], atom)
        elif atom_expr.head == 'atom_id':
            return self._atom_id_matches(atom_expr.tail[0], atom)
        else:
            raise TypeError('Expected and_expression, or_expression, or atom_id, got {}'.format(atom_expr.head))

    def _atom_id_matches(self, atom_id, atom):
        if atom_id.head == 'any_atom':
            return True
        elif atom_id.head == 'atomic_num':
            return atom.atomic_number == int(atom_id.tail[0])
        elif atom_id.head == 'atom_symbol':
            return atom.atomic_number == pt.AtomicNum[str(atom_id.tail[0])]
        elif atom_id.head == 'has_label':
            label = atom_id.tail[0][1:] # cut the % sign from the beginning
            return label in (rule.name for rule in atom.whitelist)
        elif atom_id.head == 'neighbor_count':
            return len(atom.bond_partners) == int(atom_id.tail[0])
        elif atom_id.head == 'ring_size':
            raise NotImplementedError('ring_size feature is not yet implemented')
        elif atom_id.head == 'matches_string':
            raise NotImplementedError('matches_string feature is not yet implemented')

if __name__ == '__main__':

    # TODO: set up test cases to catch precedence issues
    # x = '[#1&#2,#3]'
    # show_result(x)
    # y = '[#1,#2&#3]'
    # show_result(y)

    from topos import Topos
    topos = Topos()

    ethanol = topos.load_topo("64-17-5")

    from smarts_opls import opls_rules

    find_atomtypes(ethanol.atoms, opls_rules)

    for atom in ethanol.atoms:
        print("{}: whitelist: {}, blacklist: {}".format(atom, atom.whitelist, atom.blacklist))