Framework Integration
=====================

Comprehensive guide for integrating mypylogger with popular Python frameworks and application patterns.

Flask Integration
-----------------

Production-ready Flask integration with comprehensive request logging:

**Basic Setup**

.. code-block:: python

   import os
   import time
   import uuid
   from flask import Flask, request, jsonify, g
   from mypylogger import get_logger
   
   # Configure logging for production
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "/var/log/myapp"
   os.environ["LOG_LEVEL"] = "INFO"
   
   app = Flask(__name__)
   logger = get_logger(__name__)

**Request Lifecycle Logging**

.. code-block:: python

   @app.before_request
   def before_request():
       """Set up request context and logging."""
       g.start_time = time.time()
       g.request_id = str(uuid.uuid4())
       
       logger.info("Request started", extra={
           "request_id": g.request_id,
           "method": request.method,
           "path": request.path,
           "query_string": request.query_string.decode(),
           "remote_addr": request.remote_addr,
           "user_agent": request.headers.get('User-Agent', 'Unknown'),
           "content_type": request.content_type
       })
   
   @app.after_request
   def after_request(response):
       """Log request completion."""
       duration = time.time() - g.start_time
       
       logger.info("Request completed", extra={
           "request_id": g.request_id,
           "status_code": response.status_code,
           "duration_ms": round(duration * 1000, 2),
           "response_size": response.content_length or 0
       })
       
       return response

**Error Handling**

.. code-block:: python

   @app.errorhandler(Exception)
   def handle_exception(e):
       """Global exception handler with logging."""
       logger.error("Unhandled exception", extra={
           "request_id": getattr(g, 'request_id', 'unknown'),
           "error": str(e),
           "error_type": type(e).__name__,
           "path": request.path,
           "method": request.method
       }, exc_info=True)
       
       return jsonify({"error": "Internal server error"}), 500

**Business Logic Logging**

.. code-block:: python

   @app.route("/users/<user_id>")
   def get_user(user_id):
       """Get user with comprehensive logging."""
       logger.info("Fetching user", extra={
           "request_id": g.request_id,
           "user_id": user_id,
           "operation": "get_user"
       })
       
       try:
           # Validate input
           if not user_id.isdigit():
               logger.warning("Invalid user ID format", extra={
                   "request_id": g.request_id,
                   "user_id": user_id,
                   "validation_error": "user_id must be numeric"
               })
               return jsonify({"error": "Invalid user ID"}), 400
           
           # Business logic
           user_data = fetch_user_from_db(user_id)
           
           logger.info("User fetched successfully", extra={
               "request_id": g.request_id,
               "user_id": user_id,
               "operation": "get_user"
           })
           
           return jsonify(user_data)
           
       except Exception as e:
           logger.error("Failed to fetch user", extra={
               "request_id": g.request_id,
               "user_id": user_id,
               "operation": "get_user",
               "error": str(e),
               "error_type": type(e).__name__
           })
           return jsonify({"error": "Failed to fetch user"}), 500

Django Integration
------------------

Django integration with middleware and comprehensive logging:

**Settings Configuration**

.. code-block:: python

   # settings.py
   import os
   from mypylogger import get_logger
   
   # Configure mypylogger for Django
   os.environ["APP_NAME"] = "django-app"
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "/var/log/django"
   os.environ["LOG_LEVEL"] = "INFO"
   
   MIDDLEWARE = [
       'django.middleware.security.SecurityMiddleware',
       'myapp.middleware.LoggingMiddleware',  # Add logging middleware
       'django.contrib.sessions.middleware.SessionMiddleware',
       # ... other middleware
   ]

**Logging Middleware**

.. code-block:: python

   # middleware.py
   import time
   import uuid
   from django.utils.deprecation import MiddlewareMixin
   from mypylogger import get_logger
   
   logger = get_logger(__name__)
   
   class LoggingMiddleware(MiddlewareMixin):
       """Django middleware for comprehensive request/response logging."""
       
       def process_request(self, request):
           """Log incoming requests."""
           request.start_time = time.time()
           request.request_id = str(uuid.uuid4())
           
           logger.info("Django request started", extra={
               "request_id": request.request_id,
               "method": request.method,
               "path": request.path,
               "query_string": request.META.get('QUERY_STRING', ''),
               "remote_addr": self.get_client_ip(request),
               "user_agent": request.META.get('HTTP_USER_AGENT', 'Unknown'),
               "content_type": request.content_type,
               "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None
           })
       
       def process_response(self, request, response):
           """Log request completion."""
           if hasattr(request, 'start_time'):
               duration = time.time() - request.start_time
               
               logger.info("Django request completed", extra={
                   "request_id": getattr(request, 'request_id', 'unknown'),
                   "status_code": response.status_code,
                   "duration_ms": round(duration * 1000, 2),
                   "response_size": len(response.content) if hasattr(response, 'content') else 0
               })
           
           return response
       
       def process_exception(self, request, exception):
           """Log unhandled exceptions."""
           logger.error("Django unhandled exception", extra={
               "request_id": getattr(request, 'request_id', 'unknown'),
               "error": str(exception),
               "error_type": type(exception).__name__,
               "path": request.path,
               "method": request.method,
               "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None
           }, exc_info=True)
       
       def get_client_ip(self, request):
           """Get client IP address from request."""
           x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
           if x_forwarded_for:
               ip = x_forwarded_for.split(',')[0]
           else:
               ip = request.META.get('REMOTE_ADDR')
           return ip

**View Logging**

.. code-block:: python

   # views.py
   from django.http import JsonResponse
   from django.views.decorators.csrf import csrf_exempt
   from django.contrib.auth.models import User
   from mypylogger import get_logger
   import json
   
   logger = get_logger(__name__)
   
   def get_user(request, user_id):
       """Get user with comprehensive logging."""
       request_id = getattr(request, 'request_id', 'unknown')
       
       logger.info("Fetching Django user", extra={
           "request_id": request_id,
           "user_id": user_id,
           "operation": "get_user"
       })
       
       try:
           user = User.objects.get(id=user_id)
           
           logger.info("Django user fetched successfully", extra={
               "request_id": request_id,
               "user_id": user_id,
               "operation": "get_user",
               "username": user.username
           })
           
           return JsonResponse({
               "id": user.id,
               "username": user.username,
               "email": user.email
           })
           
       except User.DoesNotExist:
           logger.warning("Django user not found", extra={
               "request_id": request_id,
               "user_id": user_id,
               "operation": "get_user"
           })
           return JsonResponse({"error": "User not found"}, status=404)
           
       except Exception as e:
           logger.error("Failed to fetch Django user", extra={
               "request_id": request_id,
               "user_id": user_id,
               "operation": "get_user",
               "error": str(e),
               "error_type": type(e).__name__
           })
           return JsonResponse({"error": "Internal server error"}, status=500)

FastAPI Integration
-------------------

FastAPI integration with dependency injection and middleware:

**Application Setup**

.. code-block:: python

   import os
   import time
   import uuid
   from typing import Optional
   from fastapi import FastAPI, HTTPException, Depends, Request
   from fastapi.middleware.base import BaseHTTPMiddleware
   from pydantic import BaseModel, EmailStr
   from mypylogger import get_logger
   
   # Configure logging for FastAPI
   os.environ["APP_NAME"] = "fastapi-app"
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "/var/log/fastapi"
   os.environ["LOG_LEVEL"] = "INFO"
   
   app = FastAPI(title="User Service", version="1.0.0")
   logger = get_logger(__name__)

**Logging Middleware**

.. code-block:: python

   class LoggingMiddleware(BaseHTTPMiddleware):
       """FastAPI middleware for request/response logging."""
       
       async def dispatch(self, request: Request, call_next):
           start_time = time.time()
           request_id = str(uuid.uuid4())
           
           # Add request_id to request state
           request.state.request_id = request_id
           
           logger.info("FastAPI request started", extra={
               "request_id": request_id,
               "method": request.method,
               "url": str(request.url),
               "path": request.url.path,
               "query_params": dict(request.query_params),
               "client_host": request.client.host if request.client else None,
               "user_agent": request.headers.get("user-agent", "Unknown")
           })
           
           try:
               response = await call_next(request)
               
               duration = time.time() - start_time
               
               logger.info("FastAPI request completed", extra={
                   "request_id": request_id,
                   "status_code": response.status_code,
                   "duration_ms": round(duration * 1000, 2)
               })
               
               return response
               
           except Exception as e:
               duration = time.time() - start_time
               
               logger.error("FastAPI request failed", extra={
                   "request_id": request_id,
                   "error": str(e),
                   "error_type": type(e).__name__,
                   "duration_ms": round(duration * 1000, 2)
               }, exc_info=True)
               
               raise
   
   app.add_middleware(LoggingMiddleware)

**Dependency Injection**

.. code-block:: python

   # Dependency for getting request ID
   def get_request_id(request: Request) -> str:
       """Dependency to get request ID from request state."""
       return getattr(request.state, 'request_id', 'unknown')
   
   # Pydantic models
   class UserCreate(BaseModel):
       name: str
       email: EmailStr
       age: Optional[int] = None
   
   class User(BaseModel):
       id: int
       name: str
       email: str
       age: Optional[int] = None

**Endpoint Implementation**

.. code-block:: python

   @app.get("/users/{user_id}", response_model=User)
   async def get_user(
       user_id: int,
       request_id: str = Depends(get_request_id)
   ):
       """Get user by ID with comprehensive logging."""
       logger.info("Fetching FastAPI user", extra={
           "request_id": request_id,
           "user_id": user_id,
           "operation": "get_user"
       })
       
       try:
           if user_id not in users_db:
               logger.warning("FastAPI user not found", extra={
                   "request_id": request_id,
                   "user_id": user_id,
                   "operation": "get_user"
               })
               raise HTTPException(status_code=404, detail="User not found")
           
           user = users_db[user_id]
           
           logger.info("FastAPI user fetched successfully", extra={
               "request_id": request_id,
               "user_id": user_id,
               "operation": "get_user",
               "user_email": user["email"]
           })
           
           return user
           
       except HTTPException:
           raise
       except Exception as e:
           logger.error("Failed to fetch FastAPI user", extra={
               "request_id": request_id,
               "user_id": user_id,
               "operation": "get_user",
               "error": str(e),
               "error_type": type(e).__name__
           })
           raise HTTPException(status_code=500, detail="Internal server error")

**Application Lifecycle Events**

.. code-block:: python

   @app.on_event("startup")
   async def startup_event():
       """Log application startup."""
       logger.info("FastAPI application starting", extra={
           "app_name": "user-service",
           "environment": os.getenv("ENVIRONMENT", "development"),
           "log_level": os.getenv("LOG_LEVEL", "INFO")
       })
   
   @app.on_event("shutdown")
   async def shutdown_event():
       """Log application shutdown."""
       logger.info("FastAPI application shutting down")

CLI Applications
----------------

Comprehensive CLI application logging patterns:

**Basic CLI Setup**

.. code-block:: python

   import argparse
   import sys
   import os
   from pathlib import Path
   from mypylogger import get_logger
   
   def setup_logging(verbose: bool, log_file: str = None) -> None:
       """Configure logging based on CLI arguments."""
       # Set log level
       if verbose:
           os.environ["LOG_LEVEL"] = "DEBUG"
       else:
           os.environ["LOG_LEVEL"] = "INFO"
       
       # Configure file logging
       if log_file:
           os.environ["LOG_TO_FILE"] = "true"
           log_path = Path(log_file)
           os.environ["LOG_FILE_DIR"] = str(log_path.parent)
           
           # Ensure log directory exists
           log_path.parent.mkdir(parents=True, exist_ok=True)

**Argument Parsing and Logging**

.. code-block:: python

   def main():
       """Main CLI entry point."""
       parser = argparse.ArgumentParser(
           description="CLI application with comprehensive logging"
       )
       
       parser.add_argument(
           "input_files",
           nargs="+",
           help="Input files to process"
       )
       parser.add_argument(
           "-v", "--verbose",
           action="store_true",
           help="Enable verbose (DEBUG) logging"
       )
       parser.add_argument(
           "--log-file",
           help="Path to log file (enables file logging)"
       )
       
       args = parser.parse_args()
       
       # Configure logging
       setup_logging(args.verbose, args.log_file)
       logger = get_logger(__name__)
       
       logger.info("CLI application started", extra={
           "command_line_args": vars(args),
           "file_count": len(args.input_files),
           "verbose_mode": args.verbose,
           "file_logging_enabled": bool(args.log_file)
       })

**Progress and Error Handling**

.. code-block:: python

       try:
           # Process files with progress logging
           total_processed = 0
           failed_files = []
           
           for i, file_path in enumerate(args.input_files):
               logger.info("Processing file", extra={
                   "file_path": file_path,
                   "file_number": i + 1,
                   "total_files": len(args.input_files),
                   "progress_percent": round((i + 1) / len(args.input_files) * 100, 1)
               })
               
               try:
                   result = process_file(file_path, logger)
                   total_processed += result
                   
                   logger.debug("File processed successfully", extra={
                       "file_path": file_path,
                       "items_processed": result
                   })
                   
               except Exception as e:
                   logger.error("Failed to process file", extra={
                       "file_path": file_path,
                       "error": str(e),
                       "error_type": type(e).__name__
                   })
                   failed_files.append(file_path)
           
           # Final summary
           logger.info("Processing completed", extra={
               "total_items_processed": total_processed,
               "successful_files": len(args.input_files) - len(failed_files),
               "failed_files": len(failed_files),
               "failed_file_list": failed_files
           })
           
           # Exit with appropriate code
           if failed_files:
               logger.error("Some files failed to process")
               sys.exit(1)
           else:
               logger.info("All files processed successfully")
               sys.exit(0)
               
       except KeyboardInterrupt:
           logger.warning("Application interrupted by user")
           sys.exit(130)  # Standard exit code for SIGINT
           
       except Exception as e:
           logger.error("Application failed with unexpected error", extra={
               "error": str(e),
               "error_type": type(e).__name__
           }, exc_info=True)
           sys.exit(1)
   
   if __name__ == "__main__":
       main()

Configuration Best Practices
-----------------------------

**Environment-Based Configuration**

.. code-block:: python

   import os
   
   # Production configuration
   if os.getenv("ENVIRONMENT") == "production":
       os.environ["LOG_LEVEL"] = "INFO"
       os.environ["LOG_TO_FILE"] = "true"
       os.environ["LOG_FILE_DIR"] = "/var/log/myapp"
   
   # Development configuration
   elif os.getenv("ENVIRONMENT") == "development":
       os.environ["LOG_LEVEL"] = "DEBUG"
       os.environ["LOG_TO_FILE"] = "false"  # Console only
   
   # Testing configuration
   elif os.getenv("ENVIRONMENT") == "test":
       os.environ["LOG_LEVEL"] = "WARNING"
       os.environ["LOG_TO_FILE"] = "false"

**Docker Integration**

.. code-block:: dockerfile

   # Dockerfile
   FROM python:3.11-slim
   
   # Set environment variables for logging
   ENV LOG_LEVEL=INFO
   ENV LOG_TO_FILE=false
   ENV APP_NAME=myapp
   
   # Create log directory (if file logging is enabled)
   RUN mkdir -p /var/log/myapp
   
   # Copy application
   COPY . /app
   WORKDIR /app
   
   # Install dependencies
   RUN pip install -r requirements.txt
   
   # Run application
   CMD ["python", "app.py"]

**Kubernetes Configuration**

.. code-block:: yaml

   # kubernetes-deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: myapp
   spec:
     template:
       spec:
         containers:
         - name: myapp
           image: myapp:latest
           env:
           - name: LOG_LEVEL
             value: "INFO"
           - name: LOG_TO_FILE
             value: "false"  # Use stdout for container logs
           - name: APP_NAME
             value: "myapp"
           - name: ENVIRONMENT
             value: "production"

Performance Considerations
--------------------------

**Async Logging for High-Throughput Applications**

.. code-block:: python

   import asyncio
   import logging
   from mypylogger import get_logger
   
   # For high-throughput applications, consider using QueueHandler
   def setup_async_logging():
       """Set up async logging for high-performance applications."""
       import logging.handlers
       import queue
       
       # Create queue for async logging
       log_queue = queue.Queue()
       
       # Get mypylogger instance
       logger = get_logger(__name__)
       
       # Add queue handler for async processing
       queue_handler = logging.handlers.QueueHandler(log_queue)
       logger.addHandler(queue_handler)
       
       # Start queue listener in background thread
       listener = logging.handlers.QueueListener(
           log_queue, 
           *logger.handlers[:-1]  # All handlers except the queue handler
       )
       listener.start()
       
       return logger, listener

**Structured Logging Best Practices**

.. code-block:: python

   # Good: Consistent field names and types
   logger.info("User action completed", extra={
       "user_id": 12345,
       "action": "login",
       "duration_ms": 150,
       "success": True,
       "ip_address": "192.168.1.1"
   })
   
   # Good: Use consistent naming conventions
   logger.error("Database operation failed", extra={
       "operation": "user_lookup",
       "table_name": "users",
       "query_duration_ms": 5000,
       "error_code": "TIMEOUT",
       "retry_count": 3
   })
   
   # Avoid: Inconsistent field names and types
   logger.info("User did something", extra={
       "userId": "12345",  # Inconsistent naming
       "Action": "LOGIN",  # Inconsistent casing
       "time": "150ms",    # String instead of number
       "ok": "yes"         # String instead of boolean
   })