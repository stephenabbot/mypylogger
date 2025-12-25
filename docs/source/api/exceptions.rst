Exceptions Module
=================

The exceptions module defines custom exceptions for specific error conditions in mypylogger.

Exception Classes
-----------------

.. autoclass:: mypylogger.exceptions.MypyloggerError
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: mypylogger.exceptions.ConfigurationError
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: mypylogger.exceptions.FormattingError
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: mypylogger.exceptions.HandlerError
   :members:
   :undoc-members:
   :show-inheritance:

Exception Hierarchy
-------------------

All mypylogger exceptions inherit from ``MypyloggerError``, allowing for easy exception handling:

.. code-block:: text

   MypyloggerError
   ├── ConfigurationError
   ├── FormattingError
   └── HandlerError

Usage Examples
--------------

**Catching All mypylogger Exceptions**

.. code-block:: python

   from mypylogger import get_logger
   from mypylogger.exceptions import MypyloggerError
   
   try:
       logger = get_logger("myapp")
       logger.info("Application started")
   except MypyloggerError as e:
       print(f"Logging error: {e}")
       # Application continues running normally

**Handling Specific Exception Types**

.. code-block:: python

   from mypylogger import get_logger
   from mypylogger.exceptions import ConfigurationError, HandlerError
   
   try:
       logger = get_logger("myapp")
       logger.info("Processing request")
   except ConfigurationError as e:
       print(f"Configuration issue: {e}")
       # Handle configuration problems
   except HandlerError as e:
       print(f"Handler setup failed: {e}")
       # Handle handler creation issues
   except Exception as e:
       print(f"Unexpected error: {e}")
       # Handle any other errors

**Exception in Configuration**

.. code-block:: python

   import os
   from mypylogger.config import ConfigResolver
   from mypylogger.exceptions import ConfigurationError
   
   try:
       # Simulate configuration error
       os.environ["LOG_FILE_DIR"] = "/invalid/path/that/cannot/be/created"
       resolver = ConfigResolver()
       config = resolver.resolve_config()
   except ConfigurationError as e:
       print(f"Configuration failed: {e}")
       # mypylogger will fall back to safe defaults

**Exception in Formatting**

.. code-block:: python

   from mypylogger import get_logger
   from mypylogger.exceptions import FormattingError
   
   logger = get_logger("format_test")
   
   try:
       # This won't actually raise an exception due to graceful handling
       # but shows how you could catch formatting errors if they occurred
       logger.info("Message with complex data", extra={"data": {"nested": "value"}})
   except FormattingError as e:
       print(f"Formatting failed: {e}")
       # mypylogger falls back to plain text format

Error Handling Philosophy
-------------------------

mypylogger follows a **graceful degradation** approach:

* **Never crash the application** - Logging errors are handled internally
* **Fall back to safe defaults** - When operations fail, use working alternatives
* **Clear error messages** - Provide actionable information for debugging
* **Use stderr for library errors** - Keep library errors separate from application logs
* **Silent fallbacks** - Continue working even when preferred options fail

**Internal Error Handling**

Most mypylogger exceptions are handled internally and won't be raised to your application:

.. code-block:: python

   # These scenarios are handled gracefully without raising exceptions:
   
   # 1. Invalid log directory - falls back to temp directory
   os.environ["LOG_FILE_DIR"] = "/root/logs"  # Permission denied
   
   # 2. Invalid log level - falls back to INFO
   os.environ["LOG_LEVEL"] = "INVALID"
   
   # 3. JSON serialization failure - falls back to plain text
   logger.info("Message", extra={"circular": circular_reference})
   
   # Your application continues running normally in all cases

**When Exceptions Are Raised**

Exceptions are only raised in exceptional circumstances where mypylogger cannot provide a reasonable fallback:

.. code-block:: python

   from mypylogger.exceptions import ConfigurationError
   
   # This might raise ConfigurationError if the system is severely compromised
   try:
       config = ConfigResolver().resolve_config()
   except ConfigurationError:
       # Even this is rare - mypylogger tries very hard to work

This design ensures that logging issues never prevent your application from running, while still providing visibility into any problems that occur.