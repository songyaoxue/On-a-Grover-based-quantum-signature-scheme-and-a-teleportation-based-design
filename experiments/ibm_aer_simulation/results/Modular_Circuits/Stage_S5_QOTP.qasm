OPENQASM 3.0;
include "stdgates.inc";
bit[1] c;
qubit[1] q;
c[0] = measure q[0];
