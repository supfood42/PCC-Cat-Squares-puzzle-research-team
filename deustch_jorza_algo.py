'''
pip install quantuminspire
pip install qiskit-quantuminspire
pip install qiskit-aer
pip install pylatexenc
'''

from qiskit import QuantumCircuit,transpile
from qiskit.visualization import plot_histogram
import qiskit_aer
from qiskit_aer import AerSimulator

import matplotlib.pyplot as plt
%matplotlib inline


from qiskit_quantuminspire.qi_provider import QIProvider

provider = QIProvider()
# Show all current supported backends:
for backend in provider.backends():
  print(backend, backend.status)

# first, we'll define a backend for the Tuna-5 chip
backend_tuna5 = provider.get_backend(name='Tuna-5')
qubit_priority_list_tuna5 = [2,0,1,3,4]

# now for the Tuna-9 chip
backend_tuna9 = provider.get_backend(name='Tuna-9')
qubit_priority_list_tuna9 = [0,1,2,3,4,5,6,7,8]

# now for the Tuna-17 chip
backend_tuna17 = provider.get_backend(name='Tuna-17')
qubit_priority_list_tuna17 = [0,1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,11]

# then a perfect simulator
backend_sim_perfect = AerSimulator()

# and finally a noisy simulator
from qiskit_aer.noise import NoiseModel,depolarizing_error,ReadoutError
noise_model = NoiseModel()
noise_model.add_all_qubit_quantum_error(depolarizing_error(0.02, 2), ['cx', 'cz'])
noise_model.add_all_qubit_quantum_error(depolarizing_error(4e-3, 1), ['id', 'z', 's', 'sdg', 't', 'tdg', 'x', 'rx', 'y', 'ry'])
noise_model.add_all_qubit_readout_error(ReadoutError([[0.98,0.02],[0.02,0.98]]))
backend_sim_noisy = AerSimulator(noise_model=noise_model)



from qiskit import QuantumRegister
from qiskit.circuit import Gate

# define our oracle using gates
sub_q = QuantumRegister(3)
sub_circ = QuantumCircuit(sub_q, name='u_constant')
sub_circ.x(sub_q[2])

# convert sub-circuit to gate
u_constant = sub_circ.to_instruction()

# define our oracle using gates
sub_q = QuantumRegister(3)
sub_circ = QuantumCircuit(sub_q, name='u_balanced')
sub_circ.cx(sub_q[0], sub_q[2])
sub_circ.cx(sub_q[1], sub_q[2])

# convert sub-circuit to gate
u_balanced = sub_circ.to_instruction()