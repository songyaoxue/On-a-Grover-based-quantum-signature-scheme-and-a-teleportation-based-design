OPENQASM 3.0;
include "stdgates.inc";
gate unitary _gate_q_0 {
  U(1.9106332362490186, 3*pi/4, -7*pi/4) _gate_q_0;
}
gate unitary_0 _gate_q_0 {
  U(1.9106332362490186, 3*pi/4, pi/4) _gate_q_0;
}
gate unitary_1 _gate_q_0 {
  U(1.9106332362490186, 3*pi/4, pi/4) _gate_q_0;
}
gate unitary_2 _gate_q_0 {
  U(1.9106332362490186, 3*pi/4, pi/4) _gate_q_0;
}
bit[3] out;
qubit[9] v7;
barrier v7[0], v7[1], v7[2], v7[3], v7[4], v7[5], v7[6], v7[7], v7[8];
h v7[3];
cx v7[3], v7[4];
barrier v7[0], v7[1], v7[2], v7[3], v7[4], v7[5], v7[6], v7[7], v7[8];
h v7[5];
cx v7[5], v7[6];
barrier v7[0], v7[1], v7[2], v7[3], v7[4], v7[5], v7[6], v7[7], v7[8];
h v7[7];
cx v7[7], v7[8];
barrier v7[0], v7[1], v7[2], v7[3], v7[4], v7[5], v7[6], v7[7], v7[8];
barrier v7[0], v7[1], v7[2], v7[3], v7[4], v7[5], v7[6], v7[7], v7[8];
cx v7[0], v7[3];
h v7[0];
cx v7[3], v7[4];
cz v7[0], v7[4];
x v7[3];
unitary v7[3];
unitary_0 v7[3];
x v7[3];
barrier v7[0], v7[1], v7[2], v7[3], v7[4], v7[5], v7[6], v7[7], v7[8];
cx v7[4], v7[5];
h v7[4];
cx v7[5], v7[6];
cz v7[4], v7[6];
z v7[5];
unitary v7[5];
unitary_1 v7[5];
z v7[5];
reset v7[0];
barrier v7[0], v7[1], v7[2], v7[3], v7[4], v7[5], v7[6], v7[7], v7[8];
h v7[0];
cswap v7[0], v7[6], v7[2];
h v7[0];
barrier v7[0], v7[1], v7[2], v7[3], v7[4], v7[5], v7[6], v7[7], v7[8];
cx v7[6], v7[7];
h v7[6];
cx v7[7], v7[8];
cz v7[6], v7[8];
x v7[7];
z v7[7];
unitary v7[7];
unitary_2 v7[7];
z v7[7];
x v7[7];
reset v7[4];
barrier v7[0], v7[1], v7[2], v7[3], v7[4], v7[5], v7[6], v7[7], v7[8];
h v7[4];
cswap v7[4], v7[8], v7[1];
h v7[4];
out[0] = measure v7[0];
out[1] = measure v7[4];
out[2] = measure v7[8];
