OPENQASM 3.0;
include "stdgates.inc";
bit[1] c;
qubit[3] q;
x q[2];
h q[0];
cswap q[0], q[1], q[2];
h q[0];
c[0] = measure q[0];
