OPENQASM 3.0;
include "stdgates.inc";
gate unitary _gate_q_0 {
  U(1.9106332362490186, 3*pi/4, -7*pi/4) _gate_q_0;
}
gate unitary_0 _gate_q_0 {
  U(1.9106332362490186, 3*pi/4, pi/4) _gate_q_0;
}
bit[1] c;
qubit[1] q;
unitary q[0];
unitary_0 q[0];
c[0] = measure q[0];
