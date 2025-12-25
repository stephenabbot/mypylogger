Serverless Examples
===================

Examples for serverless environments like AWS Lambda.

AWS Lambda Function
-------------------

Complete Lambda function with proper logging:

.. code-block:: python

   import json
   import os
   from mypylogger import get_logger
   
   # Configure for Lambda environment
   os.environ["APP_NAME"] = "user-processor"
   os.environ["LOG_LEVEL"] = "INFO"
   
   logger = get_logger(__name__)
   
   def lambda_handler(event, context):
       # Log function invocation
       logger.info("Lambda function invoked", extra={
           "request_id": context.aws_request_id,
           "function_name": context.function_name,
           "function_version": context.function_version,
           "remaining_time_ms": context.get_remaining_time_in_millis()
       })
       
       try:
           # Process the event
           user_id = event.get('user_id')
           action = event.get('action')
           
           if not user_id or not action:
               logger.error("Missing required parameters", extra={
                   "request_id": context.aws_request_id,
                   "event": event,
                   "missing_fields": [
                       field for field in ['user_id', 'action'] 
                       if not event.get(field)
                   ]
               })
               return {
                   'statusCode': 400,
                   'body': json.dumps({'error': 'Missing required parameters'})
               }
           
           logger.info("Processing user action", extra={
               "request_id": context.aws_request_id,
               "user_id": user_id,
               "action": action
           })
           
           # Simulate processing
           result = process_user_action(user_id, action, context.aws_request_id)
           
           logger.info("User action processed successfully", extra={
               "request_id": context.aws_request_id,
               "user_id": user_id,
               "action": action,
               "result": result
           })
           
           return {
               'statusCode': 200,
               'body': json.dumps({
                   'message': 'Action processed successfully',
                   'result': result
               })
           }
           
       except Exception as e:
           logger.error("Lambda function failed", extra={
               "request_id": context.aws_request_id,
               "error": str(e),
               "error_type": type(e).__name__,
               "event": event
           })
           
           return {
               'statusCode': 500,
               'body': json.dumps({'error': 'Internal server error'})
           }
       
       finally:
           logger.info("Lambda function completed", extra={
               "request_id": context.aws_request_id,
               "remaining_time_ms": context.get_remaining_time_in_millis()
           })
   
   def process_user_action(user_id: str, action: str, request_id: str):
       logger.debug("Starting user action processing", extra={
           "request_id": request_id,
           "user_id": user_id,
           "action": action
       })
       
       # Simulate different actions
       if action == "login":
           return {"status": "logged_in", "session_id": "sess_123"}
       elif action == "logout":
           return {"status": "logged_out"}
       else:
           raise ValueError(f"Unknown action: {action}")

Container Application
---------------------

Application designed for container environments:

.. code-block:: python

   import os
   import signal
   import sys
   import time
   from mypylogger import get_logger
   
   # Container-friendly configuration
   os.environ["APP_NAME"] = os.getenv("APP_NAME", "container-app")
   os.environ["LOG_LEVEL"] = os.getenv("LOG_LEVEL", "INFO")
   os.environ["LOG_TO_FILE"] = "false"  # Use container log drivers
   
   logger = get_logger(__name__)
   
   class GracefulShutdown:
       def __init__(self):
           self.shutdown = False
           signal.signal(signal.SIGINT, self._exit_gracefully)
           signal.signal(signal.SIGTERM, self._exit_gracefully)
       
       def _exit_gracefully(self, signum, frame):
           logger.info("Shutdown signal received", extra={
               "signal": signum,
               "signal_name": signal.Signals(signum).name
           })
           self.shutdown = True
   
   def main():
       shutdown_handler = GracefulShutdown()
       
       logger.info("Container application starting", extra={
           "app_name": os.getenv("APP_NAME"),
           "log_level": os.getenv("LOG_LEVEL"),
           "python_version": sys.version
       })
       
       try:
           # Main application loop
           counter = 0
           while not shutdown_handler.shutdown:
               counter += 1
               
               logger.info("Processing cycle", extra={
                   "cycle": counter,
                   "timestamp": time.time()
               })
               
               # Simulate work
               time.sleep(5)
               
               if counter % 10 == 0:
                   logger.info("Health check", extra={
                       "cycles_completed": counter,
                       "status": "healthy"
                   })
       
       except Exception as e:
           logger.critical("Application error", extra={
               "error": str(e),
               "error_type": type(e).__name__
           })
           sys.exit(1)
       
       finally:
           logger.info("Container application shutting down", extra={
               "cycles_completed": counter
           })
   
   if __name__ == "__main__":
       main()