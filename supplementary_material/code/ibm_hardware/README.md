# IBM Hardware Data Processing

This directory contains offline analysis of existing IBM result files and hardware-oriented circuit utilities. The included existing data are stored in `../../data/ibm_hardware_existing/`.

The default workflow is offline. It does not initialize IBM Runtime, query a backend, or submit a job. Online access requires explicit user selection and valid credentials. Job submission remains separately guarded and must not be inferred from ordinary module execution.

The composed circuit-level candidate in Figure 7 corresponds to `m=1`. Rows for `m=2,4,8` derived from single-test estimates are analytical compositions, not direct repeated hardware executions. This three-Bell-pair candidate is not a hardware implementation of the physical-copy batch with `5*lambda+3` Bell pairs.
