from typing import List
import numpy as np
from numpy import linalg as LA
from scipy.special import binom

from BasisState import BasisState, state_number_to_occupations

def binomial(c, k):
    return int(binom(c, k))

class KitaevHamiltonianBlock:
    def __init__(self, _N: int, _Q: int, J: 'DisorderParameter' = None, block: 'Mat' = None):
        self.N = _N
        self.Q = _Q
        self.diagonalized = False
        if J is None:
            if block is not None:
                self.matrix = block
            return np.zeros((self.dim(), self.dim()))
        return self.initialize_block_matrix(J)

    # Initialize the matrix. Only go over states that don't trivially vanish.
    def initialize_block_matrix(self, J: 'DisorderParameter') -> None:
        N = self.N
        self.matrix = np.zeros((self.dim(), self.dim()))

        # Overall Hamiltonian coefficient.
        # Factor of 4 is because we are only summing over i<j and k<l
        coefficient = 1. / pow(2. * N, 3. / 2.) * 4.

        # Loop over disorder elements
        for i in range(N):
            for j in range(i + 1, N):
                for k in range(N):
                    for l in range(k + 1, N):
                        self.add_hamiltonian_term_contribution(J, i, j, k, l)
        self.matrix *= coefficient

    def add_term_and_state_contribution(self,
                                        J: 'DisorderParameter',
                                        i: int, j: int,
                                        k: int, l: int,
                                        indices: List[int]) -> None:
        ket = BasisState(indices)
        bra = self.act_with_c_operators(i, j, k, l, ket)

        if bra.is_zero():
            return

        if bra.charge() != self.Q:
            print(i, ",", j, ",", k, ",", l)
            print("ket.charge=", ket.charge(), "bra.charge=", bra.charge(), " Q=", self.Q)
        assert bra.charge() == self.Q
        ket_n: int = ket.get_state_number()
        bra_n: int = bra.get_state_number()

        assert bra_n >= 0
        assert bra_n < self.dim()
        self.matrix[bra_n, ket_n] += J.elem(i, j, k, l) * complex(bra.coefficient)

    def insert_index_and_shift(self, indices: List[int], i: int) -> None:
        inserted = False

        _iter = indices.begin()
        while _iter != indices.end():
            _iter += 1
            if _iter >= i:
                if not inserted:
                    indices.insert(iter, i)
                    inserted = True
                _iter += 1

        if not inserted:
            # Reached the end without inserting, so insert it here
            indices.insert(_iter, i)

    # ??? Nothing is being modified by this method
    def shift_starting_at_index(self,
                                indices: List[int], i: int) -> None:
        _iter = indices.begin()
        while _iter != indices.end():
            _iter += 1
            if _iter >= i:
                _iter += 1

    def add_hamiltonian_term_contribution(self,
                                          J: 'DisorderParameter',
                                          i: int, j: int,
                                          k: int, l: int) -> None:
        # ??? Can this method be further abstracted out to avoid repetition?
        assert i < j
        assert k < l

        if i == k and j == l:
            # Loop over the allowed ket states.
            # The two indices k,l on (c_k c_l) must appear in the ket,
            # and then the (c*_i c^*j) restore the same indices.
            # In the ket we turn on k,l, and we need to choose the
            # remaining Q-2 amond the remaining N-2 locations.
            # So we loop over (N-2) choose (Q-2) combinations, and then
            # insert k,l indices in the appropriate places.
            for n in range(binomial(self.N - 2, self.Q - 2)):
                indices: List[int] = state_number_to_occupations(n, Q - 2)
                self.insert_index_and_shift(indices, k)
                self.insert_index_and_shift(indices, l)
                self.add_term_and_state_contribution(J, i, j, k, l, indices)
        elif i == k:
            # For the state not to be annihilated by this term,
            # it must include k,l and it must not include j.
            for n in range(binomial(self.N - 3, self.Q - 2)):
                indices: List[int] = state_number_to_occupations(n, Q - 2)
                self.insert_index_and_shift(indices, k)

                if (j < l):
                    self.shift_starting_at_index(indices, j)
                    self.insert_index_and_shift(indices, l)
                else:
                    assert l < j
                    self.insert_index_and_shift(indices, l)
                    self.shift_starting_at_index(indices, j)

                self.add_term_and_state_contribution(J, i, j, k, l, indices)
        elif (j == l):
            # For the state not to be annihilated by this term,
            # it must include k,l and it must not include i.
            for n in range(binomial(self.N - 3, self.Q - 2)):
                indices: List[int] = state_number_to_occupations(n, Q - 2)

                if (i < k):
                    self.shift_starting_at_index(indices, i)
                    self.insert_index_and_shift(indices, k)
                else:
                    assert(k < i)
                    self.insert_index_and_shift(indices, k)
                    self.shift_starting_at_index(indices, i)

                self.insert_index_and_shift(indices, l)
                self.add_term_and_state_contribution(J, i, j, k, l, indices)
        elif i == l:
            # Order is k < i=l < j
            for n in range(binomial(self.N - 3, self.Q - 2)):
                indices: List[int] = state_number_to_occupations(n, Q - 2)
                self.insert_index_and_shift(indices, k)
                self.insert_index_and_shift(indices, l)
                self.shift_starting_at_index(indices, j)
                self.add_term_and_state_contribution(J, i, j, k, l, indices)
        elif j == k:
            # Order is i < j=k < l
            for n in range(binomial(self.N - 3, self.Q - 2)):
                indices: List[int] = state_number_to_occupations(n, Q - 2)
                self.shift_starting_at_index(indices, i)
                self.insert_index_and_shift(indices, k)
                self.insert_index_and_shift(indices, l)
                self.add_term_and_state_contribution(J, i, j, k, l, indices)
        else:
            assert i != k
            assert i != l
            assert j != k
            assert j != l

            # All i,j,k,l are different.
            # For the state not to be annihilated by this term,
            # it must include k,l and it must not include i,j.
            for n in range(binomial(self.N - 4, self.Q - 2)):
                indices: List[int] = state_number_to_occupations(n, Q - 2)

                # All allowed permutations (i<j and k<l):
                # i j k l (i.e. i < j < k < l)
                # i k j l
                # k i j l
                # i k l j
                # k i l j
                # k l i j

                if (i < j and j < k and k < l):
                    self.shift_starting_at_index(indices, i)
                    self.shift_starting_at_index(indices, j)
                    self.insert_index_and_shift(indices, k)
                    self.insert_index_and_shift(indices, l)
                elif (i < k and k < j and j < l):
                    self.shift_starting_at_index(indices, i)
                    self.insert_index_and_shift(indices, k)
                    self.shift_starting_at_index(indices, j)
                    self.insert_index_and_shift(indices, l)
                elif (k < i and i < j and j < l):
                    self.insert_index_and_shift(indices, k)
                    self.shift_starting_at_index(indices, i)
                    self.shift_starting_at_index(indices, j)
                    self.insert_index_and_shift(indices, l)
                elif (i < k and k < l and l < j):
                    self.shift_starting_at_index(indices, i)
                    self.insert_index_and_shift(indices, k)
                    self.insert_index_and_shift(indices, l)
                    self.shift_starting_at_index(indices, j)
                elif (k < i and i < l and l < j):
                    self.insert_index_and_shift(indices, k)
                    self.shift_starting_at_index(indices, i)
                    self.insert_index_and_shift(indices, l)
                    self.shift_starting_at_index(indices, j)
                elif (k < l and l < i and i < j):
                    self.insert_index_and_shift(indices, k)
                    self.insert_index_and_shift(indices, l)
                    self.shift_starting_at_index(indices, i)
                    self.shift_starting_at_index(indices, j)
                self.add_term_and_state_contribution(J, i, j, k, l, indices)

    # Compute:
    # c^\dagger_i c^\dagger_j c_k c_l |ket>
    def act_with_c_operators(self,
                             i: int, j: int,
                             k: int, l: int,
                             ket: BasisState) -> BasisState:
        ket.annihilate(l)
        ket.annihilate(k)
        ket.create(j)
        ket.create(i)
        return ket

    def dim(self) -> int:
        return int(binomial(self.N, self.Q))

# TODO understand the syntax
# complex KitaevHamiltonianBlock::operator()(n: int n, int m) {
#     return self.matrix(n, m)
# }

    # TODO: this is Eigen-specific code
    def diagonalize(self, full_diagonalization: bool) -> None:
        if self.diagonalized:
            return

        if (full_diagonalization):
            w, v = LA.eig(self.matrix)
            self.evs = w
            self.U = v
        else:
            # Only compute the eigenvalues
            self.evs = LA.eigvals(self.matrix)

        self.diagonalized = True

    def is_diagonalized(self) -> bool:
        return self.diagonalized

    def eigenvalues(self) -> np.ndarray:
        assert self.diagonalized
        return self.evs

    def D_matrix(self) -> 'Mat':
        assert(self.diagonalized)
        D = np.zeros((self.dim(), self.dim()))

        for i in range(self.dim()):
            D[i, i] = self.evs(i)

        return D

    def U_matrix(self) -> 'Mat':
        assert self.diagonalized
        return self.U

class NaiveKitaevHamiltonianBlock(KitaevHamiltonianBlock):
    def __init__(self, _N: int, _Q: int, J: 'DisorderParameter') -> 'KitaevHamiltonianBlock[_N, _Q]':
        self.N = _N
        self.Q = _Q
        self.initialize_block_matrix_naive_implementation(J)

    # A slow and straightforward implementation
    def initialize_block_matrix_naive_implementation(self, J: 'DisorderParameter') -> None:
        N = self.N
        Q = self.Q
        self.matrix = np.zeros((self.dim(), self.dim()))

        # Overall Hamiltonian coefficient.
        # Factor of 4 is because we are only summing over i<j and k<l
        coefficient: float = 1. / pow(2. * N, 3. / 2.) * 4.

        # n is the state number of the ket
        for ket_n in range(self.dim()):
            ket = BasisState(state_number=ket_n, Q=Q)

            # Act with all the Hamiltonian terms
            for i in range(N):
                for j in range(i + 1, N):
                    for k in range(N):
                        for l in range(k + 1, N):
                            bra = self.act_with_c_operators(i, j, k, l, ket)

                            if bra.is_zero():
                                continue

                            assert bra.charge() == Q
                            # ??? where does the method get_state_number() come from?
                            bra_n: int = bra.get_state_number()

                            assert bra_n >= 0
                            assert bra_n < self.dim()
                            # ??? What is the datatype of J (DisorderParameter)?
                            self.matrix[bra_n, ket_n] += J.elem(i, j, k, l) * complex(bra.coefficient)
        self.matrix *= coefficient
