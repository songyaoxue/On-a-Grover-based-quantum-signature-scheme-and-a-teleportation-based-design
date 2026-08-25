OPENQASM 3.0;
include "stdgates.inc";
qubit[2] bell;
h bell[0];
cx bell[0], bell[1];
