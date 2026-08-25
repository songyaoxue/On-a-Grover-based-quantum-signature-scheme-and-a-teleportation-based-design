OPENQASM 3.0;
include "stdgates.inc";
gate unitary _gate_q_0 {
  U(1.2309594173407745, 3*pi/4, 7*pi/4) _gate_q_0;
}
gate unitary_1 _gate_q_0 {
  U(1.2309594173407745, -3*pi/4, -7*pi/4) _gate_q_0;
}
gate unitary_2 _gate_q_0 {
  U(1.2309594173407745, 5*pi/4, pi/4) _gate_q_0;
}
gate unitary_3 _gate_q_0 {
  U(1.2309594173407745, -5*pi/4, -pi/4) _gate_q_0;
}
gate unitary_4 _gate_q_0 {
  U(1.2309594173407745, 7*pi/4, 3*pi/4) _gate_q_0;
}
gate unitary_5 _gate_q_0 {
  U(1.2309594173407745, -7*pi/4, -3*pi/4) _gate_q_0;
}
gate unitary_6 _gate_q_0 {
  U(1.2309594173407745, pi/4, -3*pi/4) _gate_q_0;
}
gate unitary_7 _gate_q_0 {
  U(1.2309594173407745, -pi/4, 3*pi/4) _gate_q_0;
}
gate unitary_8 _gate_q_0 {
  U(1.9106332362490186, 3*pi/4, -7*pi/4) _gate_q_0;
}
gate unitary_9 _gate_q_0 {
  U(1.9106332362490186, 5*pi/4, -pi/4) _gate_q_0;
}
gate unitary_10 _gate_q_0 {
  U(1.9106332362490186, -3*pi/4, -pi/4) _gate_q_0;
}
gate unitary_11 _gate_q_0 {
  U(1.9106332362490186, 3*pi/4, -7*pi/4) _gate_q_0;
}
gate unitary_12 _gate_q_0 {
  U(1.9106332362490186, 3*pi/4, pi/4) _gate_q_0;
}
gate unitary_13 _gate_q_0 {
  U(1.9106332362490186, pi/4, -pi/4) _gate_q_0;
}
gate unitary_14 _gate_q_0 {
  U(1.9106332362490186, -3*pi/4, 3*pi/4) _gate_q_0;
}
gate unitary_15 _gate_q_0 {
  U(1.9106332362490186, -pi/4, pi/4) _gate_q_0;
}
gate unitary_16 _gate_q_0 {
  U(1.9106332362490186, 3*pi/4, -3*pi/4) _gate_q_0;
}
gate unitary_17 _gate_q_0 {
  U(1.9106332362490186, 3*pi/4, pi/4) _gate_q_0;
}
gate unitary_18 _gate_q_0 {
  U(1.2309594173407745, pi/4, pi/4) _gate_q_0;
}
gate unitary_19 _gate_q_0 {
  U(1.2309594173407745, 3*pi/4, -5*pi/4) _gate_q_0;
}
gate unitary_20 _gate_q_0 {
  U(1.2309594173407745, -pi/4, -pi/4) _gate_q_0;
}
gate unitary_21 _gate_q_0 {
  U(1.2309594173407745, 5*pi/4, -3*pi/4) _gate_q_0;
}
gate unitary_22 _gate_q_0 {
  U(1.2309594173407745, -5*pi/4, 3*pi/4) _gate_q_0;
}
gate unitary_23 _gate_q_0 {
  U(1.2309594173407745, pi/4, pi/4) _gate_q_0;
}
gate unitary_24 _gate_q_0 {
  U(1.2309594173407745, -3*pi/4, -3*pi/4) _gate_q_0;
}
gate unitary_25 _gate_q_0 {
  U(1.2309594173407745, 7*pi/4, -pi/4) _gate_q_0;
}
bit[2] swap_0;
bit[1] message;
bit[2] x1b;
bit[2] x1c;
bit[2] x2b;
bit[2] x2c;
bit[2] x3b;
bit[2] x3c;
qubit[3] alice_msg;
qubit[2] bell_AB;
qubit[2] bell_BT;
qubit[2] bell_TB;
qubit[2] verify;
qubit[2] X1_bell;
qubit[2] X1_comp;
qubit[2] X2_bell;
qubit[2] X2_comp;
qubit[2] X3_bell;
qubit[2] X3_comp;
h alice_msg[0];
h alice_msg[1];
h alice_msg[2];
barrier alice_msg[0], alice_msg[1], alice_msg[2], bell_AB[0], bell_AB[1], bell_BT[0], bell_BT[1], bell_TB[0], bell_TB[1], verify[0], verify[1], X1_bell[0], X1_bell[1], X1_comp[0], X1_comp[1], X2_bell[0], X2_bell[1], X2_comp[0], X2_comp[1], X3_bell[0], X3_bell[1], X3_comp[0], X3_comp[1];
h bell_AB[0];
cx bell_AB[0], bell_AB[1];
barrier alice_msg[0], alice_msg[1], alice_msg[2], bell_AB[0], bell_AB[1], bell_BT[0], bell_BT[1], bell_TB[0], bell_TB[1], verify[0], verify[1], X1_bell[0], X1_bell[1], X1_comp[0], X1_comp[1], X2_bell[0], X2_bell[1], X2_comp[0], X2_comp[1], X3_bell[0], X3_bell[1], X3_comp[0], X3_comp[1];
h bell_BT[0];
cx bell_BT[0], bell_BT[1];
barrier alice_msg[0], alice_msg[1], alice_msg[2], bell_AB[0], bell_AB[1], bell_BT[0], bell_BT[1], bell_TB[0], bell_TB[1], verify[0], verify[1], X1_bell[0], X1_bell[1], X1_comp[0], X1_comp[1], X2_bell[0], X2_bell[1], X2_comp[0], X2_comp[1], X3_bell[0], X3_bell[1], X3_comp[0], X3_comp[1];
h bell_TB[0];
cx bell_TB[0], bell_TB[1];
barrier alice_msg[0], alice_msg[1], alice_msg[2], bell_AB[0], bell_AB[1], bell_BT[0], bell_BT[1], bell_TB[0], bell_TB[1], verify[0], verify[1], X1_bell[0], X1_bell[1], X1_comp[0], X1_comp[1], X2_bell[0], X2_bell[1], X2_comp[0], X2_comp[1], X3_bell[0], X3_bell[1], X3_comp[0], X3_comp[1];
barrier alice_msg[0], alice_msg[1], alice_msg[2], bell_AB[0], bell_AB[1], bell_BT[0], bell_BT[1], bell_TB[0], bell_TB[1], verify[0], verify[1], X1_bell[0], X1_bell[1], X1_comp[0], X1_comp[1], X2_bell[0], X2_bell[1], X2_comp[0], X2_comp[1], X3_bell[0], X3_bell[1], X3_comp[0], X3_comp[1];
cx alice_msg[0], bell_AB[0];
h alice_msg[0];
cx alice_msg[0], X1_bell[0];
cx alice_msg[0], X1_comp[0];
cx bell_AB[0], X1_bell[1];
cx bell_AB[0], X1_comp[1];
unitary X1_bell[0];
unitary_1 X1_bell[0];
unitary_2 X1_bell[1];
unitary_3 X1_bell[1];
unitary_4 X1_comp[0];
unitary_5 X1_comp[0];
unitary_6 X1_comp[1];
unitary_7 X1_comp[1];
cx bell_AB[0], bell_AB[1];
cz alice_msg[0], bell_AB[1];
barrier alice_msg[0], alice_msg[1], alice_msg[2], bell_AB[0], bell_AB[1], bell_BT[0], bell_BT[1], bell_TB[0], bell_TB[1], verify[0], verify[1], X1_bell[0], X1_bell[1], X1_comp[0], X1_comp[1], X2_bell[0], X2_bell[1], X2_comp[0], X2_comp[1], X3_bell[0], X3_bell[1], X3_comp[0], X3_comp[1];
unitary_8 alice_msg[2];
barrier alice_msg[0], alice_msg[1], alice_msg[2], bell_AB[0], bell_AB[1], bell_BT[0], bell_BT[1], bell_TB[0], bell_TB[1], verify[0], verify[1], X1_bell[0], X1_bell[1], X1_comp[0], X1_comp[1], X2_bell[0], X2_bell[1], X2_comp[0], X2_comp[1], X3_bell[0], X3_bell[1], X3_comp[0], X3_comp[1];
cx bell_AB[1], bell_BT[0];
h bell_AB[1];
cx bell_AB[1], X2_bell[0];
cx bell_AB[1], X2_comp[0];
cx bell_BT[0], X2_bell[1];
cx bell_BT[0], X2_comp[1];
unitary_9 X2_bell[0];
unitary_10 X2_bell[0];
unitary_11 X2_bell[1];
unitary_12 X2_bell[1];
unitary_13 X2_comp[0];
unitary_14 X2_comp[0];
unitary_15 X2_comp[1];
unitary_16 X2_comp[1];
cx bell_BT[0], bell_BT[1];
cz bell_AB[1], bell_BT[1];
barrier alice_msg[0], alice_msg[1], alice_msg[2], bell_AB[0], bell_AB[1], bell_BT[0], bell_BT[1], bell_TB[0], bell_TB[1], verify[0], verify[1], X1_bell[0], X1_bell[1], X1_comp[0], X1_comp[1], X2_bell[0], X2_bell[1], X2_comp[0], X2_comp[1], X3_bell[0], X3_bell[1], X3_comp[0], X3_comp[1];
unitary_17 alice_msg[2];
barrier alice_msg[0], alice_msg[1], alice_msg[2], bell_AB[0], bell_AB[1], bell_BT[0], bell_BT[1], bell_TB[0], bell_TB[1], verify[0], verify[1], X1_bell[0], X1_bell[1], X1_comp[0], X1_comp[1], X2_bell[0], X2_bell[1], X2_comp[0], X2_comp[1], X3_bell[0], X3_bell[1], X3_comp[0], X3_comp[1];
h verify[0];
cswap verify[0], bell_BT[1], alice_msg[2];
h verify[0];
barrier alice_msg[0], alice_msg[1], alice_msg[2], bell_AB[0], bell_AB[1], bell_BT[0], bell_BT[1], bell_TB[0], bell_TB[1], verify[0], verify[1], X1_bell[0], X1_bell[1], X1_comp[0], X1_comp[1], X2_bell[0], X2_bell[1], X2_comp[0], X2_comp[1], X3_bell[0], X3_bell[1], X3_comp[0], X3_comp[1];
cx bell_BT[1], bell_TB[0];
h bell_BT[1];
cx bell_BT[1], X3_bell[0];
cx bell_BT[1], X3_comp[0];
cx bell_TB[0], X3_bell[1];
cx bell_TB[0], X3_comp[1];
unitary_18 X3_bell[0];
unitary_19 X3_bell[0];
unitary_20 X3_bell[1];
unitary_21 X3_bell[1];
unitary_22 X3_comp[0];
unitary_23 X3_comp[0];
unitary_24 X3_comp[1];
unitary_25 X3_comp[1];
cx bell_TB[0], bell_TB[1];
cz bell_BT[1], bell_TB[1];
barrier alice_msg[0], alice_msg[1], alice_msg[2], bell_AB[0], bell_AB[1], bell_BT[0], bell_BT[1], bell_TB[0], bell_TB[1], verify[0], verify[1], X1_bell[0], X1_bell[1], X1_comp[0], X1_comp[1], X2_bell[0], X2_bell[1], X2_comp[0], X2_comp[1], X3_bell[0], X3_bell[1], X3_comp[0], X3_comp[1];
barrier alice_msg[0], alice_msg[1], alice_msg[2], bell_AB[0], bell_AB[1], bell_BT[0], bell_BT[1], bell_TB[0], bell_TB[1], verify[0], verify[1], X1_bell[0], X1_bell[1], X1_comp[0], X1_comp[1], X2_bell[0], X2_bell[1], X2_comp[0], X2_comp[1], X3_bell[0], X3_bell[1], X3_comp[0], X3_comp[1];
h verify[1];
cswap verify[1], bell_TB[1], alice_msg[1];
h verify[1];
h bell_TB[1];
swap_0[0] = measure verify[0];
swap_0[1] = measure verify[1];
message[0] = measure bell_TB[1];
x1b[0] = measure X1_bell[0];
x1b[1] = measure X1_bell[1];
x1c[0] = measure X1_comp[0];
x1c[1] = measure X1_comp[1];
x2b[0] = measure X2_bell[0];
x2b[1] = measure X2_bell[1];
x2c[0] = measure X2_comp[0];
x2c[1] = measure X2_comp[1];
x3b[0] = measure X3_bell[0];
x3b[1] = measure X3_bell[1];
x3c[0] = measure X3_comp[0];
x3c[1] = measure X3_comp[1];
