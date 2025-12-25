Performance Documentation
=========================

Performance characteristics and optimization guidance for mypylogger.

.. toctree::
   :maxdepth: 2

   benchmarks
   optimization

Performance Overview
--------------------

mypylogger is designed for "fast enough" performance with reliability as the primary goal:

* **Logger initialization**: <10ms target
* **Single log entry**: <1ms target (with immediate flush)
* **Memory usage**: Minimal overhead per logger instance
* **Throughput**: Optimized for typical application logging (not high-frequency scenarios)

Performance Philosophy
----------------------

mypylogger prioritizes:

1. **Reliability over speed**: Immediate flush ensures logs aren't lost
2. **Simplicity over optimization**: Clear, maintainable code
3. **Predictable behavior**: Consistent performance across environments
4. **Graceful degradation**: Performance doesn't degrade under error conditions

For applications requiring extreme performance (>10k logs/second), consider specialized logging solutions.