Migration Guide
===============

Guide for migrating from other logging libraries to mypylogger.

From Python Standard Logging
-----------------------------

**Before (standard logging)**:

.. code-block:: python

   import logging
   
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   
   logger = logging.getLogger(__name__)
   logger.info("Application started")

**After (mypylogger)**:

.. code-block:: python

   from mypylogger import get_logger
   
   logger = get_logger(__name__)
   logger.info("Application started")

Key differences:
* No manual configuration needed
* Automatic JSON formatting
* Environment-driven configuration

From Loguru
-----------

**Before (loguru)**:

.. code-block:: python

   from loguru import logger
   
   logger.add("app.log", format="{time} {level} {message}")
   logger.info("User {user} logged in", user="john")

**After (mypylogger)**:

.. code-block:: python

   import os
   from mypylogger import get_logger
   
   os.environ["LOG_TO_FILE"] = "true"
   logger = get_logger(__name__)
   logger.info("User logged in", extra={"user": "john"})

From Structlog
--------------

**Before (structlog)**:

.. code-block:: python

   import structlog
   
   structlog.configure(
       processors=[structlog.processors.JSONRenderer()],
       wrapper_class=structlog.make_filtering_bound_logger(20),
   )
   
   logger = structlog.get_logger()
   logger.info("User action", user_id="123", action="login")

**After (mypylogger)**:

.. code-block:: python

   from mypylogger import get_logger
   
   logger = get_logger(__name__)
   logger.info("User action", extra={"user_id": "123", "action": "login"})

Migration Checklist
--------------------

1. **Replace logger imports**:
   - Change to ``from mypylogger import get_logger``
   - Update logger creation to ``get_logger(__name__)``

2. **Update configuration**:
   - Remove manual logging configuration
   - Set environment variables for configuration

3. **Convert structured data**:
   - Move structured data to ``extra`` parameter
   - Ensure field names are consistent

4. **Update log levels**:
   - Use environment variable ``LOG_LEVEL`` instead of code configuration

5. **File logging**:
   - Set ``LOG_TO_FILE=true`` and ``LOG_FILE_DIR`` instead of manual handlers

Compatibility Considerations
----------------------------

* mypylogger uses standard Python logging underneath
* Existing log handlers can be added if needed
* Log levels work the same way
* Exception logging works identically

Benefits of Migration
---------------------

* **Simpler configuration**: Environment-driven setup
* **Consistent output**: Predictable JSON format
* **Zero dependencies**: Pure Python standard library only
* **Better defaults**: Works out of the box
* **Container friendly**: Environment variable configuration