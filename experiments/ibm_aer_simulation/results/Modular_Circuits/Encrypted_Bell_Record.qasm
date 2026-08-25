OPENQASM 3.0;
include "stdgates.inc";
bit[2] c;
qubit[2] q;
c[0] = measure q[0];
c[1] = measure q[1];
