API Reference
=============

This section provides detailed documentation for all public functions and classes in mypylogger.

.. toctree::
   :maxdepth: 2

   core
   config
   exceptions
   formatters
   handlers

Overview
--------

mypylogger provides a simple, focused API for JSON logging:

* :func:`mypylogger.get_logger` - Main function to get configured loggers
* :func:`mypylogger.get_version` - Get library version information
* Configuration classes for environment-driven setup
* Custom exceptions for graceful error handling
* JSON formatters with source location tracking
* Handler management with automatic fallback logic

The API follows standard Python logging patterns while providing sensible defaults for JSON output.

Quick Start
-----------

.. code-block:: python

   from mypylogger import get_logger
   
   # Get a logger and start logging
   logger = get_logger(__name__)
   logger.info("Hello, structured logging!")
   
   # Output: {"timestamp":"2025-01-21T10:30:45.123456Z","level":"INFO","message":"Hello, structured logging!",...}

Key Features
------------

* **Zero configuration required** - Works out of the box with sensible defaults
* **Environment-driven configuration** - No code changes between environments
* **Automatic source location tracking** - Module, filename, function, and line number
* **Graceful error handling** - Never crashes your application
* **JSON output** - Consistent, parseable structured logs
* **Multiple output destinations** - Console and optional file logging
* **Immediate flush** - Real-time log visibility for development and production