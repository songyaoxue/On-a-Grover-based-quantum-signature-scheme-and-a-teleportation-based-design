OPENQASM 3.0;
include "stdgates.inc";
gate unitary _gate_q_0 {
  U(1.9106332362490186, 5*pi/4, -pi/4) _gate_q_0;
}
gate unitary_0 _gate_q_0 {
  U(1.9106332362490186, -3*pi/4, -pi/4) _gate_q_0;
}
bit[2] c;
qubit[2] q;
h q[0];
cx q[0], q[1];
x q[1];
unitary q[1];
unitary_0 q[1];
x q[1];
cx q[0], q[1];
h q[0];
c[0] = measure q[0];
c[1] = measure q[1];
