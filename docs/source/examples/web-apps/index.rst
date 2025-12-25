Web Application Examples
========================

Complete examples for web applications using popular Python frameworks.

Flask Application
-----------------

Complete Flask application with request logging and error handling:

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
   
   @app.route("/users/<user_id>")
   def get_user(user_id):
       """Get user by ID with comprehensive logging."""
       logger.info("Fetching user", extra={
           "request_id": g.request_id,
           "user_id": user_id,
           "operation": "get_user"
       })
       
       try:
           # Simulate database lookup
           if not user_id.isdigit():
               logger.warning("Invalid user ID format", extra={
                   "request_id": g.request_id,
                   "user_id": user_id,
                   "validation_error": "user_id must be numeric"
               })
               return jsonify({"error": "Invalid user ID"}), 400
           
           # Simulate user lookup
           user_data = {
               "id": int(user_id),
               "name": "John Doe",
               "email": "john@example.com"
           }
           
           logger.info("User fetched successfully", extra={
               "request_id": g.request_id,
               "user_id": user_id,
               "operation": "get_user",
               "result": "success"
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
   
   @app.route("/users", methods=["POST"])
   def create_user():
       """Create new user with validation logging."""
       logger.info("Creating user", extra={
           "request_id": g.request_id,
           "operation": "create_user"
       })
       
       try:
           data = request.get_json()
           if not data:
               logger.warning("No JSON data provided", extra={
                   "request_id": g.request_id,
                   "operation": "create_user"
               })
               return jsonify({"error": "JSON data required"}), 400
           
           # Validate required fields
           required_fields = ["name", "email"]
           missing_fields = [field for field in required_fields if field not in data]
           
           if missing_fields:
               logger.warning("Missing required fields", extra={
                   "request_id": g.request_id,
                   "operation": "create_user",
                   "missing_fields": missing_fields,
                   "provided_fields": list(data.keys())
               })
               return jsonify({"error": f"Missing fields: {missing_fields}"}), 400
           
           # Simulate user creation
           new_user = {
               "id": 123,
               "name": data["name"],
               "email": data["email"]
           }
           
           logger.info("User created successfully", extra={
               "request_id": g.request_id,
               "operation": "create_user",
               "user_id": new_user["id"],
               "user_email": new_user["email"]
           })
           
           return jsonify(new_user), 201
           
       except Exception as e:
           logger.error("Failed to create user", extra={
               "request_id": g.request_id,
               "operation": "create_user",
               "error": str(e),
               "error_type": type(e).__name__
           })
           return jsonify({"error": "Failed to create user"}), 500
   
   if __name__ == "__main__":
       logger.info("Flask application starting", extra={
           "app_name": "user-service",
           "environment": os.getenv("ENVIRONMENT", "development"),
           "log_level": os.getenv("LOG_LEVEL", "INFO")
       })
       app.run(debug=True, host="0.0.0.0", port=5000)

Django Application
------------------

Django middleware and settings for comprehensive logging:

**settings.py**:

.. code-block:: python

   import os
   from mypylogger import get_logger
   
   # Configure mypylogger for Django
   os.environ["APP_NAME"] = "django-app"
   os.environ["LOG_TO_FILE"] = "true"
   os.environ["LOG_FILE_DIR"] = "/var/log/django"
   os.environ["LOG_LEVEL"] = "INFO"
   
   # Django settings
   DEBUG = False
   ALLOWED_HOSTS = ['*']
   
   INSTALLED_APPS = [
       'django.contrib.admin',
       'django.contrib.auth',
       'django.contrib.contenttypes',
       'django.contrib.sessions',
       'django.contrib.messages',
       'django.contrib.staticfiles',
       'myapp',
   ]
   
   MIDDLEWARE = [
       'django.middleware.security.SecurityMiddleware',
       'myapp.middleware.LoggingMiddleware',  # Custom logging middleware
       'django.contrib.sessions.middleware.SessionMiddleware',
       'django.middleware.common.CommonMiddleware',
       'django.middleware.csrf.CsrfViewMiddleware',
       'django.contrib.auth.middleware.AuthenticationMiddleware',
       'django.contrib.messages.middleware.MessageMiddleware',
       'django.middleware.clickjacking.XFrameOptionsMiddleware',
   ]
   
   ROOT_URLCONF = 'myproject.urls'
   
   # Database configuration
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.sqlite3',
           'NAME': 'db.sqlite3',
       }
   }

**middleware.py**:

.. code-block:: python

   import time
   import uuid
   from django.utils.deprecation import MiddlewareMixin
   from mypylogger import get_logger
   
   logger = get_logger(__name__)
   
   class LoggingMiddleware(MiddlewareMixin):
       """Django middleware for request/response logging."""
       
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

**views.py**:

.. code-block:: python

   from django.http import JsonResponse
   from django.views.decorators.csrf import csrf_exempt
   from django.views.decorators.http import require_http_methods
   from django.contrib.auth.models import User
   from mypylogger import get_logger
   import json
   
   logger = get_logger(__name__)
   
   @require_http_methods(["GET"])
   def get_user(request, user_id):
       """Get user by ID with comprehensive logging."""
       request_id = getattr(request, 'request_id', 'unknown')
       
       logger.info("Fetching Django user", extra={
           "request_id": request_id,
           "user_id": user_id,
           "operation": "get_user"
       })
       
       try:
           user = User.objects.get(id=user_id)
           
           user_data = {
               "id": user.id,
               "username": user.username,
               "email": user.email,
               "first_name": user.first_name,
               "last_name": user.last_name,
               "is_active": user.is_active
           }
           
           logger.info("Django user fetched successfully", extra={
               "request_id": request_id,
               "user_id": user_id,
               "operation": "get_user",
               "username": user.username
           })
           
           return JsonResponse(user_data)
           
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
   
   @csrf_exempt
   @require_http_methods(["POST"])
   def create_user(request):
       """Create new Django user with validation logging."""
       request_id = getattr(request, 'request_id', 'unknown')
       
       logger.info("Creating Django user", extra={
           "request_id": request_id,
           "operation": "create_user"
       })
       
       try:
           data = json.loads(request.body)
           
           # Validate required fields
           required_fields = ["username", "email", "password"]
           missing_fields = [field for field in required_fields if field not in data]
           
           if missing_fields:
               logger.warning("Missing required fields for user creation", extra={
                   "request_id": request_id,
                   "operation": "create_user",
                   "missing_fields": missing_fields
               })
               return JsonResponse({"error": f"Missing fields: {missing_fields}"}, status=400)
           
           # Create user
           user = User.objects.create_user(
               username=data["username"],
               email=data["email"],
               password=data["password"],
               first_name=data.get("first_name", ""),
               last_name=data.get("last_name", "")
           )
           
           logger.info("Django user created successfully", extra={
               "request_id": request_id,
               "operation": "create_user",
               "user_id": user.id,
               "username": user.username,
               "email": user.email
           })
           
           return JsonResponse({
               "id": user.id,
               "username": user.username,
               "email": user.email
           }, status=201)
           
       except json.JSONDecodeError:
           logger.warning("Invalid JSON in request body", extra={
               "request_id": request_id,
               "operation": "create_user"
           })
           return JsonResponse({"error": "Invalid JSON"}, status=400)
           
       except Exception as e:
           logger.error("Failed to create Django user", extra={
               "request_id": request_id,
               "operation": "create_user",
               "error": str(e),
               "error_type": type(e).__name__
           })
           return JsonResponse({"error": "Failed to create user"}, status=500)

FastAPI Application
-------------------

FastAPI application with dependency injection and comprehensive logging:

.. code-block:: python

   import os
   import time
   import uuid
   from typing import Optional
   from fastapi import FastAPI, HTTPException, Depends, Request, Response
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
   
   # Logging middleware
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
   
   # Dependency for getting request ID
   def get_request_id(request: Request) -> str:
       """Dependency to get request ID from request state."""
       return getattr(request.state, 'request_id', 'unknown')
   
   # Simulated database
   users_db = {}
   next_user_id = 1
   
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
   
   @app.post("/users", response_model=User, status_code=201)
   async def create_user(
       user_data: UserCreate,
       request_id: str = Depends(get_request_id)
   ):
       """Create new user with validation logging."""
       global next_user_id
       
       logger.info("Creating FastAPI user", extra={
           "request_id": request_id,
           "operation": "create_user",
           "user_email": user_data.email
       })
       
       try:
           # Check if user already exists
           for existing_user in users_db.values():
               if existing_user["email"] == user_data.email:
                   logger.warning("FastAPI user already exists", extra={
                       "request_id": request_id,
                       "operation": "create_user",
                       "user_email": user_data.email,
                       "conflict_reason": "email_already_exists"
                   })
                   raise HTTPException(status_code=409, detail="User with this email already exists")
           
           # Create new user
           new_user = {
               "id": next_user_id,
               "name": user_data.name,
               "email": user_data.email,
               "age": user_data.age
           }
           
           users_db[next_user_id] = new_user
           next_user_id += 1
           
           logger.info("FastAPI user created successfully", extra={
               "request_id": request_id,
               "operation": "create_user",
               "user_id": new_user["id"],
               "user_email": new_user["email"]
           })
           
           return new_user
           
       except HTTPException:
           raise
       except Exception as e:
           logger.error("Failed to create FastAPI user", extra={
               "request_id": request_id,
               "operation": "create_user",
               "error": str(e),
               "error_type": type(e).__name__
           })
           raise HTTPException(status_code=500, detail="Failed to create user")
   
   @app.get("/users", response_model=list[User])
   async def list_users(
       limit: int = 10,
       offset: int = 0,
       request_id: str = Depends(get_request_id)
   ):
       """List users with pagination logging."""
       logger.info("Listing FastAPI users", extra={
           "request_id": request_id,
           "operation": "list_users",
           "limit": limit,
           "offset": offset
       })
       
       try:
           all_users = list(users_db.values())
           paginated_users = all_users[offset:offset + limit]
           
           logger.info("FastAPI users listed successfully", extra={
               "request_id": request_id,
               "operation": "list_users",
               "total_users": len(all_users),
               "returned_users": len(paginated_users),
               "limit": limit,
               "offset": offset
           })
           
           return paginated_users
           
       except Exception as e:
           logger.error("Failed to list FastAPI users", extra={
               "request_id": request_id,
               "operation": "list_users",
               "error": str(e),
               "error_type": type(e).__name__
           })
           raise HTTPException(status_code=500, detail="Failed to list users")
   
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
   
   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8000)