Basic Examples
==============

Complete examples demonstrating core mypylogger functionality with practical use cases.

Hello World - JSON Logging
---------------------------

The simplest possible example showing JSON output:

.. code-block:: python

   from mypylogger import get_logger
   
   logger = get_logger(__name__)
   logger.info("Hello, World!")

**Output** (formatted for readability):

.. code-block:: json

   {
     "time": "2025-01-21T10:30:45.123456Z",
     "levelname": "INFO",
     "name": "__main__",
     "message": "Hello, World!"
   }

**Key Features Demonstrated**:
* Automatic JSON formatting
* ISO 8601 timestamp with microsecond precision
* Module name detection
* Zero configuration required

Environment-Based Configuration Example
---------------------------------------

Complete example showing environment-based configuration:

.. code-block:: python

   # config_example.py
   import os
   from mypylogger import get_logger
   
   # Set configuration via environment variables
   os.environ["APP_NAME"] = "ecommerce-api"
   os.environ["LOG_LEVEL"] = "INFO"
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "/var/log/ecommerce"
   
   # Create logger - configuration is automatically applied
   logger = get_logger()
   
   def main():
       logger.info("Application starting", extra={
           "version": "1.2.3",
           "environment": os.getenv("ENVIRONMENT", "development")
       })
       
       # Simulate application work
       process_orders()
       
       logger.info("Application shutdown complete")
   
   def process_orders():
       logger.info("Processing orders batch", extra={
           "batch_size": 100,
           "queue_depth": 1500
       })
       
       # This will appear in both console AND file
       logger.info("Orders processed successfully", extra={
           "processed_count": 100,
           "failed_count": 0,
           "processing_time_ms": 2500
       })
   
   if __name__ == "__main__":
       main()

**Run with different environments**:

.. code-block:: bash

   # Development - console only, debug level
   export ENVIRONMENT="development"
   export LOG_LEVEL="DEBUG"
   export LOG_TO_FILE="false"
   python config_example.py
   
   # Production - file + console, info level
   export ENVIRONMENT="production"
   export LOG_LEVEL="INFO"
   export LOG_TO_FILE="true"
   export LOG_FILE_DIR="/var/log/ecommerce"
   python config_example.py

File Logging Configuration Example
----------------------------------

Complete example demonstrating file logging setup and directory management:

.. code-block:: python

   # file_logging_example.py
   import os
   from pathlib import Path
   from datetime import datetime
   from mypylogger import get_logger
   
   def setup_logging():
       """Configure file logging with automatic directory creation."""
       
       # Create date-based log directory
       log_date = datetime.now().strftime("%Y-%m-%d")
       log_dir = Path.home() / "logs" / "myapp" / log_date
       
       # Configure mypylogger
       os.environ["APP_NAME"] = "file-demo"
       os.environ["LOG_TO_FILE"] = "true"
       os.environ["LOG_FILE_DIR"] = str(log_dir)
       os.environ["LOG_LEVEL"] = "DEBUG"
       
       print(f"Logs will be written to: {log_dir}/file-demo.log")
       
       return get_logger()
   
   def demonstrate_file_logging():
       """Show various logging patterns with file output."""
       
       logger = setup_logging()
       
       # Application startup
       logger.info("Application started", extra={
           "pid": os.getpid(),
           "log_file": os.getenv("LOG_FILE_DIR") + "/file-demo.log"
       })
       
       # Simulate different operations
       logger.debug("Debug information", extra={
           "operation": "data_validation",
           "records_checked": 1000
       })
       
       logger.info("Processing batch", extra={
           "batch_id": "batch_001",
           "items": 250
       })
       
       logger.warning("Rate limit approaching", extra={
           "current_rate": 95,
           "limit": 100,
           "window": "1_minute"
       })
       
       # Simulate error
       try:
           raise ValueError("Simulated error for demonstration")
       except ValueError as e:
           logger.error("Processing error occurred", extra={
               "error": str(e),
               "error_type": "ValueError",
               "batch_id": "batch_001"
           })
       
       logger.info("Application shutdown", extra={
           "uptime_seconds": 30,
           "total_operations": 1250
       })
   
   if __name__ == "__main__":
       demonstrate_file_logging()
       print("Check the log file for JSON output!")

Structured Logging with Custom Fields
--------------------------------------

Advanced example showing structured logging patterns:

.. code-block:: python

   # structured_logging_example.py
   import uuid
   import time
   from datetime import datetime
   from mypylogger import get_logger
   
   # Different loggers for different components
   api_logger = get_logger("api")
   db_logger = get_logger("database")
   auth_logger = get_logger("auth")
   
   class UserService:
       """Example service demonstrating structured logging patterns."""
       
       def __init__(self):
           self.logger = get_logger("user_service")
       
       def create_user(self, email, name):
           """Create user with comprehensive logging."""
           
           user_id = str(uuid.uuid4())
           start_time = time.time()
           
           self.logger.info("User creation started", extra={
               "user_id": user_id,
               "email": email,
               "name": name,
               "operation": "create_user"
           })
           
           try:
               # Simulate validation
               self._validate_user_data(email, name, user_id)
               
               # Simulate database operation
               self._save_to_database(user_id, email, name)
               
               # Simulate sending welcome email
               self._send_welcome_email(email, user_id)
               
               duration = (time.time() - start_time) * 1000
               
               self.logger.info("User created successfully", extra={
                   "user_id": user_id,
                   "email": email,
                   "operation": "create_user",
                   "duration_ms": round(duration, 2),
                   "status": "success"
               })
               
               return user_id
               
           except Exception as e:
               duration = (time.time() - start_time) * 1000
               
               self.logger.error("User creation failed", extra={
                   "user_id": user_id,
                   "email": email,
                   "operation": "create_user",
                   "duration_ms": round(duration, 2),
                   "error": str(e),
                   "error_type": type(e).__name__,
                   "status": "error"
               })
               raise
       
       def _validate_user_data(self, email, name, user_id):
           """Validate user data with logging."""
           
           self.logger.debug("Validating user data", extra={
               "user_id": user_id,
               "email": email,
               "validation_step": "input_validation"
           })
           
           if "@" not in email:
               raise ValueError("Invalid email format")
           
           if len(name) < 2:
               raise ValueError("Name too short")
           
           self.logger.debug("User data validation passed", extra={
               "user_id": user_id,
               "validation_step": "input_validation",
               "status": "passed"
           })
       
       def _save_to_database(self, user_id, email, name):
           """Simulate database save with logging."""
           
           db_logger.info("Saving user to database", extra={
               "user_id": user_id,
               "table": "users",
               "operation": "INSERT"
           })
           
           # Simulate database delay
           time.sleep(0.1)
           
           db_logger.info("User saved to database", extra={
               "user_id": user_id,
               "table": "users",
               "operation": "INSERT",
               "rows_affected": 1
           })
       
       def _send_welcome_email(self, email, user_id):
           """Simulate email sending with logging."""
           
           email_logger = get_logger("email_service")
           
           email_logger.info("Sending welcome email", extra={
               "user_id": user_id,
               "recipient": email,
               "template": "welcome_email",
               "provider": "sendgrid"
           })
           
           # Simulate email service delay
           time.sleep(0.05)
           
           email_logger.info("Welcome email sent", extra={
               "user_id": user_id,
               "recipient": email,
               "template": "welcome_email",
               "message_id": "msg_" + str(uuid.uuid4())[:8],
               "status": "delivered"
           })
   
   def main():
       """Demonstrate structured logging in action."""
       
       api_logger.info("API server starting", extra={
           "port": 8000,
           "environment": "development",
           "version": "1.0.0"
       })
       
       user_service = UserService()
       
       # Simulate API requests
       try:
           user_id = user_service.create_user("john@example.com", "John Doe")
           
           api_logger.info("User creation API call completed", extra={
               "endpoint": "/api/users",
               "method": "POST",
               "user_id": user_id,
               "status_code": 201
           })
           
       except ValueError as e:
           api_logger.warning("User creation failed - validation error", extra={
               "endpoint": "/api/users",
               "method": "POST",
               "error": str(e),
               "status_code": 400
           })
   
   if __name__ == "__main__":
       main()

Error Handling and Exception Logging
-------------------------------------

Comprehensive error handling example:

.. code-block:: python

   # error_handling_example.py
   import random
   from mypylogger import get_logger
   
   logger = get_logger("error_demo")
   
   class DatabaseError(Exception):
       """Custom database exception."""
       pass
   
   class ValidationError(Exception):
       """Custom validation exception."""
       pass
   
   def process_order(order_id, customer_id, amount):
       """Process order with comprehensive error handling."""
       
       logger.info("Order processing started", extra={
           "order_id": order_id,
           "customer_id": customer_id,
           "amount": amount,
           "currency": "USD"
       })
       
       try:
           # Step 1: Validate order
           validate_order(order_id, customer_id, amount)
           
           # Step 2: Process payment
           payment_id = process_payment(customer_id, amount)
           
           # Step 3: Update inventory
           update_inventory(order_id)
           
           # Step 4: Send confirmation
           send_confirmation(customer_id, order_id)
           
           logger.info("Order processed successfully", extra={
               "order_id": order_id,
               "customer_id": customer_id,
               "payment_id": payment_id,
               "status": "completed"
           })
           
           return {"status": "success", "payment_id": payment_id}
           
       except ValidationError as e:
           logger.warning("Order validation failed", extra={
               "order_id": order_id,
               "customer_id": customer_id,
               "validation_error": str(e),
               "error_type": "validation",
               "status": "rejected"
           })
           return {"status": "validation_error", "error": str(e)}
           
       except DatabaseError as e:
           logger.error("Database error during order processing", extra={
               "order_id": order_id,
               "customer_id": customer_id,
               "database_error": str(e),
               "error_type": "database",
               "status": "failed"
           })
           return {"status": "database_error", "error": str(e)}
           
       except Exception as e:
           logger.critical("Unexpected error in order processing", extra={
               "order_id": order_id,
               "customer_id": customer_id,
               "unexpected_error": str(e),
               "error_type": type(e).__name__,
               "status": "critical_failure"
           })
           # Re-raise unexpected errors
           raise
   
   def validate_order(order_id, customer_id, amount):
       """Validate order with detailed logging."""
       
       logger.debug("Validating order", extra={
           "order_id": order_id,
           "validation_step": "order_validation"
       })
       
       if amount <= 0:
           raise ValidationError("Order amount must be positive")
       
       if amount > 10000:
           raise ValidationError("Order amount exceeds maximum limit")
       
       # Simulate random validation failure
       if random.random() < 0.2:
           raise ValidationError("Customer validation failed")
   
   def process_payment(customer_id, amount):
       """Process payment with error simulation."""
       
       logger.info("Processing payment", extra={
           "customer_id": customer_id,
           "amount": amount,
           "payment_processor": "stripe"
       })
       
       # Simulate random database error
       if random.random() < 0.1:
           raise DatabaseError("Payment database connection failed")
       
       payment_id = f"pay_{random.randint(1000, 9999)}"
       
       logger.info("Payment processed", extra={
           "customer_id": customer_id,
           "payment_id": payment_id,
           "amount": amount,
           "status": "charged"
       })
       
       return payment_id
   
   def update_inventory(order_id):
       """Update inventory with logging."""
       
       logger.debug("Updating inventory", extra={
           "order_id": order_id,
           "operation": "inventory_update"
       })
       
       # Simulate random database error
       if random.random() < 0.05:
           raise DatabaseError("Inventory database unavailable")
   
   def send_confirmation(customer_id, order_id):
       """Send order confirmation."""
       
       logger.info("Sending order confirmation", extra={
           "customer_id": customer_id,
           "order_id": order_id,
           "notification_type": "email"
       })
   
   def main():
       """Demonstrate error handling patterns."""
       
       logger.info("Order processing service started")
       
       # Process multiple orders to show different outcomes
       orders = [
           ("order_001", "cust_123", 99.99),
           ("order_002", "cust_456", -10.00),  # Will fail validation
           ("order_003", "cust_789", 15000.00),  # Will fail validation
           ("order_004", "cust_101", 49.99),
           ("order_005", "cust_202", 199.99),
       ]
       
       for order_id, customer_id, amount in orders:
           try:
               result = process_order(order_id, customer_id, amount)
               print(f"Order {order_id}: {result['status']}")
           except Exception as e:
               logger.critical("Unhandled exception in main loop", extra={
                   "order_id": order_id,
                   "error": str(e),
                   "error_type": type(e).__name__
               })
               print(f"Order {order_id}: critical failure")
   
   if __name__ == "__main__":
       main()