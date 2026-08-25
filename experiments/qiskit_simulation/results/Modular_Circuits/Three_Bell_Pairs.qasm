OPENQASM 3.0;
include "stdgates.inc";
qubit[6] bell;
h bell[0];
cx bell[0], bell[1];
h bell[2];
cx bell[2], bell[3];
h bell[4];
cx bell[4], bell[5];
