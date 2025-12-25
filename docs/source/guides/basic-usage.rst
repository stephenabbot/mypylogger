Basic Usage Guide
=================

This guide covers fundamental mypylogger usage patterns and best practices for JSON logging.

JSON Logging Setup
------------------

**Zero Configuration Setup**

mypylogger works immediately with no configuration required:

.. code-block:: python

   from mypylogger import get_logger
   
   logger = get_logger(__name__)
   logger.info("Application started")

**Output** (formatted for readability):

.. code-block:: json

   {
     "time": "2025-01-21T10:30:45.123456Z",
     "levelname": "INFO", 
     "name": "myapp.main",
     "message": "Application started"
   }

**Key JSON Features**:

* **Consistent structure**: Every log entry has the same JSON schema
* **Timestamp first**: ``time`` field always appears first for easy parsing
* **ISO 8601 timestamps**: Standard format with microsecond precision
* **Flat structure**: No nested objects, optimized for log aggregation tools
* **Machine readable**: Ready for Splunk, ELK stack, CloudWatch without transformation

Getting Started
---------------

**Basic logger creation**:

.. code-block:: python

   from mypylogger import get_logger
   
   # Recommended: Use __name__ for automatic module naming
   logger = get_logger(__name__)
   
   # Custom name for specific components
   db_logger = get_logger("database")
   api_logger = get_logger("api_client")

Logger Naming
-------------

**Recommended pattern**: Use ``__name__`` for module-level loggers:

.. code-block:: python

   # In myapp/users.py
   from mypylogger import get_logger
   
   logger = get_logger(__name__)  # Creates logger named "myapp.users"

**Custom names**: Use descriptive names for specific components:

.. code-block:: python

   # For specific subsystems
   db_logger = get_logger("database")
   api_logger = get_logger("api")
   auth_logger = get_logger("authentication")

Structured Logging with Custom Fields
-------------------------------------

**Adding Context with Extra Fields**

Use the ``extra`` parameter to add structured data to your logs:

.. code-block:: python

   logger.info("User login successful", extra={
       "user_id": "user_12345",
       "session_id": "sess_abcdef",
       "ip_address": "192.168.1.100",
       "login_method": "password",
       "duration_ms": 245
   })

**Output**:

.. code-block:: json

   {
     "time": "2025-01-21T10:30:45.123456Z",
     "levelname": "INFO",
     "name": "auth.service", 
     "message": "User login successful",
     "user_id": "user_12345",
     "session_id": "sess_abcdef",
     "ip_address": "192.168.1.100",
     "login_method": "password",
     "duration_ms": 245
   }

**Advanced Structured Logging Patterns**

*Request Tracking*:

.. code-block:: python

   import uuid
   
   def process_api_request(request_data):
       request_id = str(uuid.uuid4())
       
       logger.info("API request started", extra={
           "request_id": request_id,
           "endpoint": "/api/users",
           "method": "POST",
           "content_length": len(request_data)
       })
       
       try:
           result = handle_request(request_data)
           
           logger.info("API request completed", extra={
               "request_id": request_id,
               "status_code": 200,
               "response_size": len(result),
               "processing_time_ms": 150
           })
           
           return result
           
       except ValidationError as e:
           logger.warning("API request validation failed", extra={
               "request_id": request_id,
               "status_code": 400,
               "validation_errors": e.errors,
               "error_type": "validation"
           })
           raise

*Business Metrics Logging*:

.. code-block:: python

   def process_payment(amount, currency, user_id):
       logger.info("Payment processing started", extra={
           "user_id": user_id,
           "amount": amount,
           "currency": currency,
           "payment_processor": "stripe",
           "transaction_type": "purchase"
       })
       
       # ... payment processing logic ...
       
       logger.info("Payment completed successfully", extra={
           "user_id": user_id,
           "amount": amount,
           "currency": currency,
           "transaction_id": "txn_abc123",
           "processing_fee": 2.50,
           "net_amount": amount - 2.50,
           "payment_method": "credit_card"
       })

**Best Practices for Custom Fields**:

* **Consistent naming**: Use snake_case for field names (``user_id``, not ``userId``)
* **Include context**: Add relevant identifiers (user_id, request_id, session_id)
* **Use simple types**: Strings, numbers, booleans work best with log aggregation
* **Avoid nesting**: Keep structure flat for better searchability
* **Standard fields**: Use common field names across your application

Log Levels
----------

Use appropriate log levels for different types of information:

.. code-block:: python

   # Debug: Detailed diagnostic information
   logger.debug("Processing user data", extra={"user_id": "12345"})
   
   # Info: General application flow
   logger.info("User logged in successfully", extra={"user_id": "12345"})
   
   # Warning: Something unexpected but not an error
   logger.warning("API rate limit approaching", extra={"requests_remaining": 10})
   
   # Error: An error occurred but application can continue
   logger.error("Failed to send email", extra={"user_id": "12345", "error": "SMTP timeout"})
   
   # Critical: Serious error that may cause application to abort
   logger.critical("Database connection lost", extra={"database": "primary"})

Error Logging
-------------

Proper error logging with exception information:

.. code-block:: python

   def process_user_data(user_id):
       try:
           # Process data
           result = perform_operation(user_id)
           logger.info("Data processed successfully", extra={
               "user_id": user_id,
               "records_processed": len(result)
           })
           return result
           
       except ValidationError as e:
           logger.error("Data validation failed", extra={
               "user_id": user_id,
               "validation_error": str(e),
               "error_type": "validation"
           })
           raise
           
       except DatabaseError as e:
           logger.error("Database operation failed", extra={
               "user_id": user_id,
               "database_error": str(e),
               "error_type": "database"
           })
           raise
           
       except Exception as e:
           logger.critical("Unexpected error occurred", extra={
               "user_id": user_id,
               "error": str(e),
               "error_type": "unexpected"
           })
           raise

Performance Considerations
--------------------------

**Immediate flush**: mypylogger flushes immediately by default for reliability:

.. code-block:: python

   # This is automatically flushed to ensure logs aren't lost
   logger.info("Critical operation completed")

**High-frequency logging**: For applications with very high log volume:

.. code-block:: python

   # Consider log level filtering
   import os
   os.environ["LOG_LEVEL"] = "WARNING"  # Only log warnings and above
   
   # Or use conditional logging for debug information
   if logger.isEnabledFor(logging.DEBUG):
       logger.debug("Expensive debug operation", extra=expensive_debug_data())

Common Patterns
---------------

**Request tracking**:

.. code-block:: python

   import uuid
   
   def handle_request(request):
       request_id = str(uuid.uuid4())
       
       logger.info("Request started", extra={
           "request_id": request_id,
           "method": request.method,
           "path": request.path
       })
       
       try:
           result = process_request(request)
           logger.info("Request completed", extra={
               "request_id": request_id,
               "status": "success",
               "duration_ms": result.duration
           })
           return result
           
       except Exception as e:
           logger.error("Request failed", extra={
               "request_id": request_id,
               "error": str(e),
               "status": "error"
           })
           raise

**Application lifecycle**:

.. code-block:: python

   def main():
       logger.info("Application starting", extra={"version": "1.0.0"})
       
       try:
           initialize_components()
           logger.info("Components initialized successfully")
           
           run_application()
           
       except KeyboardInterrupt:
           logger.info("Application interrupted by user")
       except Exception as e:
           logger.critical("Application failed to start", extra={"error": str(e)})
           raise
       finally:
           cleanup_resources()
           logger.info("Application shutdown complete")

Best Practices Summary
----------------------

1. **Use ``__name__`` for logger names** - Provides clear module identification
2. **Include relevant context** - Add user_id, request_id, etc. in ``extra``
3. **Choose appropriate log levels** - Don't overuse INFO or DEBUG
4. **Log errors with context** - Include error details and relevant state
5. **Be consistent** - Use the same field names across your application
6. **Keep it simple** - Avoid complex nested structures in log data