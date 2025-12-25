Installation
============

System Requirements
-------------------

**Minimum Requirements:**

* **Python 3.8 or higher** - mypylogger supports Python 3.8, 3.9, 3.10, 3.11, and 3.12
* **pip 20.0 or higher** - For reliable package installation
* **Operating System** - Linux, macOS, Windows (all supported)

**Recommended Environment:**

* **Virtual environment** - Isolates dependencies and prevents conflicts
* **Latest pip** - ``python -m pip install --upgrade pip``
* **64-bit Python** - For optimal performance in production environments

**Memory and Storage:**

* **RAM** - Minimal memory footprint (<1MB)
* **Disk Space** - <100KB installed size
* **Dependencies** - Zero runtime dependencies (pure Python standard library)

Installation Methods
--------------------

Standard Installation
~~~~~~~~~~~~~~~~~~~~~

Install mypylogger from PyPI using pip:

.. code-block:: bash

   pip install mypylogger

This installs the latest stable version with all required dependencies.

Virtual Environment Installation (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For isolated installation, use a virtual environment:

.. code-block:: bash

   # Create virtual environment
   python -m venv mypylogger-env
   
   # Activate virtual environment
   # On Linux/macOS:
   source mypylogger-env/bin/activate
   # On Windows:
   mypylogger-env\Scripts\activate
   
   # Install mypylogger
   pip install mypylogger

User-Level Installation
~~~~~~~~~~~~~~~~~~~~~~~

Install for current user only (no admin privileges required):

.. code-block:: bash

   pip install --user mypylogger

Upgrade Installation
~~~~~~~~~~~~~~~~~~~~

Upgrade to the latest version:

.. code-block:: bash

   pip install --upgrade mypylogger

Specific Version Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install a specific version:

.. code-block:: bash

   pip install mypylogger==0.2.0

Installation Verification
-------------------------

Quick Verification
~~~~~~~~~~~~~~~~~~

Verify the installation by importing the library:

.. code-block:: python

   from mypylogger import get_logger
   
   logger = get_logger("installation_test")
   logger.info("Installation successful!")

**Expected Output:**

.. code-block:: json

   {"time":"2025-01-21T10:30:45.123456Z","levelname":"INFO","name":"installation_test","message":"Installation successful!"}

Complete Verification
~~~~~~~~~~~~~~~~~~~~~

Run a comprehensive verification test:

.. code-block:: python

   import sys
   from mypylogger import get_logger, get_version
   
   # Check version
   print(f"mypylogger version: {get_version()}")
   print(f"Python version: {sys.version}")
   
   # Test basic functionality
   logger = get_logger("verification")
   logger.info("Testing basic logging")
   logger.info("Testing structured logging", extra={"test_id": "001", "status": "success"})
   
   print("✓ Installation verification completed successfully!")

**Expected Output:**

.. code-block:: text

   mypylogger version: 0.2.0
   Python version: 3.11.0 (main, Oct 24 2022, 18:26:48) [MSC v.1933 64 bit (AMD64)]
   {"time":"2025-01-21T10:30:45.123456Z","levelname":"INFO","name":"verification","message":"Testing basic logging"}
   {"time":"2025-01-21T10:30:45.123457Z","levelname":"INFO","name":"verification","message":"Testing structured logging","test_id":"001","status":"success"}
   ✓ Installation verification completed successfully!

Package Information Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check installed package details:

.. code-block:: bash

   # List installed packages
   pip list | grep mypylogger
   
   # Show package information
   pip show mypylogger
   
   # Check package files
   pip show -f mypylogger

Troubleshooting
---------------

Common Installation Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~

**ImportError: No module named 'mypylogger'**

*Symptoms:* Python cannot find the mypylogger module

*Solutions:*

1. Verify installation: ``pip list | grep mypylogger``
2. Check Python environment: ``which python`` and ``which pip``
3. Reinstall package: ``pip uninstall mypylogger && pip install mypylogger``
4. Use absolute path: ``python -m pip install mypylogger``

**Permission denied errors**

*Symptoms:* ``PermissionError`` or ``Access denied`` during installation

*Solutions:*

1. Use user installation: ``pip install --user mypylogger``
2. Use virtual environment (recommended):

   .. code-block:: bash

      python -m venv venv
      source venv/bin/activate  # Linux/macOS
      # or venv\Scripts\activate  # Windows
      pip install mypylogger

3. Run with elevated privileges (not recommended):

   .. code-block:: bash

      # Linux/macOS
      sudo pip install mypylogger
      
      # Windows (run as Administrator)
      pip install mypylogger

**Python version compatibility issues**

*Symptoms:* ``Requires Python >=3.8`` error

*Solutions:*

1. Check Python version: ``python --version``
2. Upgrade Python to 3.8 or higher
3. Use pyenv for version management:

   .. code-block:: bash

      # Install pyenv (Linux/macOS)
      curl https://pyenv.run | bash
      
      # Install Python 3.11
      pyenv install 3.11.0
      pyenv global 3.11.0

4. Use conda for version management:

   .. code-block:: bash

      conda create -n mypylogger python=3.11
      conda activate mypylogger
      pip install mypylogger

**Network and proxy issues**

*Symptoms:* Connection timeouts or SSL errors

*Solutions:*

1. Use trusted hosts: ``pip install --trusted-host pypi.org --trusted-host pypi.python.org mypylogger``
2. Configure proxy: ``pip install --proxy http://proxy.company.com:8080 mypylogger``
3. Use alternative index: ``pip install -i https://pypi.org/simple/ mypylogger``

**Dependency conflicts**

*Symptoms:* ``ResolutionImpossible`` or dependency version conflicts

*Solutions:*

1. Use virtual environment (isolates dependencies)
2. Check conflicting packages: ``pip check``
3. Force reinstall: ``pip install --force-reinstall mypylogger``
4. Use dependency resolver: ``pip install --use-feature=2020-resolver mypylogger``

**Installation in restricted environments**

*Symptoms:* Corporate firewalls or air-gapped systems

*Solutions:*

1. Download wheel file manually from PyPI
2. Install from local file: ``pip install mypylogger-0.2.0-py3-none-any.whl``
3. Use internal PyPI mirror if available
4. Bundle dependencies: ``pip download mypylogger`` then ``pip install --no-index --find-links . mypylogger``

Platform-Specific Issues
~~~~~~~~~~~~~~~~~~~~~~~~~

**Windows-specific issues:**

* Use ``py`` launcher: ``py -m pip install mypylogger``
* Long path support: Enable in Windows settings
* PowerShell execution policy: ``Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser``

**macOS-specific issues:**

* Xcode command line tools: ``xcode-select --install``
* Homebrew Python conflicts: Use ``python3`` and ``pip3`` explicitly
* System Integrity Protection: Use virtual environments instead of system Python

**Linux-specific issues:**

* Missing Python headers: ``sudo apt-get install python3-dev`` (Ubuntu/Debian)
* SELinux restrictions: Check ``getenforce`` and adjust policies if needed
* Package manager conflicts: Use virtual environments to avoid system package conflicts

Getting Help
~~~~~~~~~~~~

If you continue to experience issues:

1. **Check the FAQ** in our documentation
2. **Search existing issues** on GitHub: https://github.com/username/mypylogger/issues
3. **Create a new issue** with:
   - Python version (``python --version``)
   - Operating system and version
   - Complete error message
   - Installation command used
   - Virtual environment details (if applicable)

Development Installation
------------------------

For Contributors and Developers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to contribute to mypylogger or modify the source code:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/username/mypylogger.git
   cd mypylogger
   
   # Install in development mode
   pip install -e .
   
   # Install development dependencies
   pip install -e ".[dev]"

Using UV (Recommended for Development)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

mypylogger uses UV for fast dependency management:

.. code-block:: bash

   # Install UV
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Clone and setup
   git clone https://github.com/username/mypylogger.git
   cd mypylogger
   
   # Install dependencies
   uv sync
   
   # Run tests
   uv run pytest
   
   # Format code
   uv run ruff format .

Docker Installation
~~~~~~~~~~~~~~~~~~~

For containerized environments:

.. code-block:: dockerfile

   FROM python:3.11-slim
   
   # Install mypylogger
   RUN pip install mypylogger
   
   # Your application code
   COPY . /app
   WORKDIR /app
   
   CMD ["python", "app.py"]

Next Steps
----------

After successful installation:

1. **Read the Quick Start Guide** - :doc:`quickstart` for immediate usage
2. **Explore Configuration Options** - :doc:`guides/configuration` for environment setup
3. **Check API Documentation** - :doc:`api/index` for detailed function reference
4. **Review Examples** - :doc:`examples/index` for real-world usage patterns