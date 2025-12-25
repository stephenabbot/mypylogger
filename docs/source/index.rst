mypylogger Documentation
========================

Welcome to mypylogger v0.2.0 - a zero-dependency JSON logging library with sensible defaults for Python applications.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   api/index
   guides/index
   examples/index
   performance/index

Overview
--------

mypylogger does ONE thing exceptionally well: structured JSON logs that work everywhere—from local development to AWS Lambda to Kubernetes.

**What makes mypylogger different:**

* **Zero Dependencies** (pure Python standard library)
* **Clean, Predictable JSON Output**
* **Developer-Friendly Defaults**
* **Standard Python Patterns**

Key Features
------------

* Zero-configuration JSON logging
* Environment-driven configuration
* Immediate flush for real-time monitoring
* Compatible with existing Python logging ecosystem
* Works in restricted environments (Lambda, containers, air-gapped systems)

Quick Example
-------------

.. code-block:: python

   from mypylogger import get_logger

   logger = get_logger(__name__)
   logger.info("Application started", extra={"version": "1.0.0"})

Output:

.. code-block:: json

   {"time":"2025-01-21T10:30:45.123456Z","levelname":"INFO","name":"myapp","message":"Application started","version":"1.0.0"}

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`