CLI Application Examples
========================

Examples for command-line applications and scripts with comprehensive logging patterns.

Data Processing Script
----------------------

Complete CLI script with progress logging and error handling:

.. code-block:: python

   #!/usr/bin/env python3
   """
   Data processing CLI tool with comprehensive logging.
   
   Usage:
       python process_data.py file1.txt file2.txt --verbose --log-file /var/log/processor.log
   """
   
   import argparse
   import sys
   import time
   import signal
   from pathlib import Path
   from typing import List, Optional
   from mypylogger import get_logger
   
   class DataProcessor:
       """Data processor with comprehensive logging."""
       
       def __init__(self, logger):
           self.logger = logger
           self.processed_files = 0
           self.total_lines = 0
           self.start_time = time.time()
           self.interrupted = False
           
           # Set up signal handlers for graceful shutdown
           signal.signal(signal.SIGINT, self._signal_handler)
           signal.signal(signal.SIGTERM, self._signal_handler)
       
       def _signal_handler(self, signum, frame):
           """Handle shutdown signals gracefully."""
           signal_name = signal.Signals(signum).name
           self.logger.warning("Received shutdown signal", extra={
               "signal": signal_name,
               "processed_files": self.processed_files,
               "total_lines_processed": self.total_lines,
               "runtime_seconds": round(time.time() - self.start_time, 2)
           })
           self.interrupted = True
       
       def setup_logging(self, verbose: bool, log_file: Optional[str] = None) -> None:
           """Configure logging based on CLI arguments."""
           import os
           
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
               
               self.logger.info("File logging configured", extra={
                   "log_file": str(log_path),
                   "log_directory": str(log_path.parent)
               })
       
       def validate_files(self, file_paths: List[str]) -> tuple[List[Path], List[str]]:
           """Validate input files and return valid/invalid lists."""
           valid_files = []
           invalid_files = []
           
           for file_path_str in file_paths:
               file_path = Path(file_path_str)
               
               if not file_path.exists():
                   self.logger.warning("File not found", extra={
                       "file_path": str(file_path),
                       "validation_error": "file_not_found"
                   })
                   invalid_files.append(str(file_path))
                   continue
               
               if not file_path.is_file():
                   self.logger.warning("Path is not a file", extra={
                       "file_path": str(file_path),
                       "validation_error": "not_a_file"
                   })
                   invalid_files.append(str(file_path))
                   continue
               
               if not file_path.suffix.lower() in ['.txt', '.log', '.csv']:
                   self.logger.warning("Unsupported file type", extra={
                       "file_path": str(file_path),
                       "file_extension": file_path.suffix,
                       "validation_error": "unsupported_file_type"
                   })
                   invalid_files.append(str(file_path))
                   continue
               
               valid_files.append(file_path)
           
           self.logger.info("File validation completed", extra={
               "total_files": len(file_paths),
               "valid_files": len(valid_files),
               "invalid_files": len(invalid_files)
           })
           
           return valid_files, invalid_files
       
       def process_file(self, file_path: Path) -> int:
           """Process a single file with detailed logging."""
           file_start_time = time.time()
           
           self.logger.info("Processing file started", extra={
               "file_path": str(file_path),
               "file_size_bytes": file_path.stat().st_size,
               "file_extension": file_path.suffix
           })
           
           try:
               with open(file_path, 'r', encoding='utf-8') as f:
                   lines = f.readlines()
               
               processed_lines = []
               batch_size = 1000
               
               for i, line in enumerate(lines):
                   if self.interrupted:
                       self.logger.warning("Processing interrupted", extra={
                           "file_path": str(file_path),
                           "lines_processed": i,
                           "total_lines": len(lines)
                       })
                       break
                   
                   # Simulate processing (convert to uppercase, strip whitespace)
                   processed_line = line.strip().upper()
                   processed_lines.append(processed_line)
                   
                   # Log progress every batch_size lines
                   if (i + 1) % batch_size == 0:
                       progress_percent = round((i + 1) / len(lines) * 100, 1)
                       self.logger.debug("Processing progress", extra={
                           "file_path": str(file_path),
                           "lines_processed": i + 1,
                           "total_lines": len(lines),
                           "progress_percent": progress_percent,
                           "processing_rate_lines_per_sec": round((i + 1) / (time.time() - file_start_time), 2)
                       })
               
               # Write processed data back to file (with .processed extension)
               output_path = file_path.with_suffix(f"{file_path.suffix}.processed")
               with open(output_path, 'w', encoding='utf-8') as f:
                   f.write('\n'.join(processed_lines))
               
               duration = time.time() - file_start_time
               
               self.logger.info("File processing completed", extra={
                   "file_path": str(file_path),
                   "output_path": str(output_path),
                   "lines_processed": len(processed_lines),
                   "duration_seconds": round(duration, 2),
                   "processing_rate_lines_per_sec": round(len(processed_lines) / duration, 2) if duration > 0 else 0
               })
               
               return len(processed_lines)
               
           except UnicodeDecodeError as e:
               self.logger.error("File encoding error", extra={
                   "file_path": str(file_path),
                   "error": str(e),
                   "error_type": "UnicodeDecodeError",
                   "encoding_attempted": "utf-8"
               })
               raise
           
           except PermissionError as e:
               self.logger.error("File permission error", extra={
                   "file_path": str(file_path),
                   "error": str(e),
                   "error_type": "PermissionError"
               })
               raise
           
           except Exception as e:
               self.logger.error("File processing failed", extra={
                   "file_path": str(file_path),
                   "error": str(e),
                   "error_type": type(e).__name__,
                   "duration_seconds": round(time.time() - file_start_time, 2)
               })
               raise
       
       def process_files(self, file_paths: List[str]) -> dict:
           """Process multiple files and return summary statistics."""
           self.logger.info("Batch processing started", extra={
               "total_files": len(file_paths),
               "start_time": time.strftime("%Y-%m-%d %H:%M:%S")
           })
           
           # Validate files first
           valid_files, invalid_files = self.validate_files(file_paths)
           
           if not valid_files:
               self.logger.error("No valid files to process")
               return {
                   "success": False,
                   "processed_files": 0,
                   "failed_files": len(file_paths),
                   "total_lines": 0,
                   "invalid_files": invalid_files
               }
           
           successful_files = []
           failed_files = []
           total_lines_processed = 0
           
           for file_path in valid_files:
               if self.interrupted:
                   self.logger.warning("Batch processing interrupted")
                   break
               
               try:
                   lines_processed = self.process_file(file_path)
                   successful_files.append(str(file_path))
                   total_lines_processed += lines_processed
                   self.processed_files += 1
                   self.total_lines += lines_processed
                   
               except Exception as e:
                   failed_files.append(str(file_path))
                   self.logger.error("Failed to process file", extra={
                       "file_path": str(file_path),
                       "error": str(e)
                   })
           
           duration = time.time() - self.start_time
           
           summary = {
               "success": len(failed_files) == 0 and not self.interrupted,
               "processed_files": len(successful_files),
               "failed_files": len(failed_files) + len(invalid_files),
               "total_lines": total_lines_processed,
               "duration_seconds": round(duration, 2),
               "average_processing_rate": round(total_lines_processed / duration, 2) if duration > 0 else 0,
               "successful_files": successful_files,
               "failed_files": failed_files + invalid_files,
               "interrupted": self.interrupted
           }
           
           self.logger.info("Batch processing completed", extra=summary)
           
           return summary
   
   def main():
       """Main CLI entry point."""
       parser = argparse.ArgumentParser(
           description="Process text files with comprehensive logging",
           formatter_class=argparse.RawDescriptionHelpFormatter,
           epilog="""
   Examples:
       %(prog)s file1.txt file2.txt
       %(prog)s *.txt --verbose
       %(prog)s data/*.log --log-file /var/log/processor.log
       %(prog)s input.csv --verbose --log-file ./processing.log
           """
       )
       
       parser.add_argument(
           "files",
           nargs="+",
           help="Files to process (supports .txt, .log, .csv)"
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
       parser.add_argument(
           "--version",
           action="version",
           version="Data Processor 1.0.0"
       )
       
       args = parser.parse_args()
       
       # Initialize logger and processor
       logger = get_logger(__name__)
       processor = DataProcessor(logger)
       
       # Configure logging
       processor.setup_logging(args.verbose, args.log_file)
       
       logger.info("CLI application started", extra={
           "command_line_args": vars(args),
           "file_count": len(args.files),
           "verbose_mode": args.verbose,
           "file_logging_enabled": bool(args.log_file)
       })
       
       try:
           # Process files
           summary = processor.process_files(args.files)
           
           # Exit with appropriate code
           if summary["success"]:
               logger.info("All files processed successfully", extra={
                   "final_summary": summary
               })
               sys.exit(0)
           else:
               logger.error("Processing completed with errors", extra={
                   "final_summary": summary
               })
               sys.exit(1)
               
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

Database Migration Script
-------------------------

CLI script for database operations with transaction logging:

.. code-block:: python

   #!/usr/bin/env python3
   """
   Database migration CLI tool with comprehensive logging.
   
   Usage:
       python migrate_db.py --config config.json --dry-run
       python migrate_db.py --config config.json --apply --log-file migrations.log
   """
   
   import argparse
   import json
   import sys
   import time
   from pathlib import Path
   from typing import Dict, List, Any
   from mypylogger import get_logger
   
   class DatabaseMigrator:
       """Database migration tool with comprehensive logging."""
       
       def __init__(self, config_path: str, logger):
           self.logger = logger
           self.config = self._load_config(config_path)
           self.migration_id = f"migration_{int(time.time())}"
           
       def _load_config(self, config_path: str) -> Dict[str, Any]:
           """Load and validate configuration file."""
           config_file = Path(config_path)
           
           self.logger.info("Loading configuration", extra={
               "config_path": str(config_file),
               "migration_id": self.migration_id
           })
           
           try:
               if not config_file.exists():
                   raise FileNotFoundError(f"Configuration file not found: {config_file}")
               
               with open(config_file, 'r') as f:
                   config = json.load(f)
               
               # Validate required configuration keys
               required_keys = ["database_url", "migrations_dir", "backup_dir"]
               missing_keys = [key for key in required_keys if key not in config]
               
               if missing_keys:
                   raise ValueError(f"Missing required configuration keys: {missing_keys}")
               
               self.logger.info("Configuration loaded successfully", extra={
                   "config_path": str(config_file),
                   "migration_id": self.migration_id,
                   "database_url": config["database_url"].split("@")[-1] if "@" in config["database_url"] else config["database_url"],  # Hide credentials
                   "migrations_dir": config["migrations_dir"],
                   "backup_dir": config["backup_dir"]
               })
               
               return config
               
           except json.JSONDecodeError as e:
               self.logger.error("Invalid JSON in configuration file", extra={
                   "config_path": str(config_file),
                   "migration_id": self.migration_id,
                   "error": str(e),
                   "error_type": "JSONDecodeError"
               })
               raise
           
           except Exception as e:
               self.logger.error("Failed to load configuration", extra={
                   "config_path": str(config_file),
                   "migration_id": self.migration_id,
                   "error": str(e),
                   "error_type": type(e).__name__
               })
               raise
       
       def discover_migrations(self) -> List[Dict[str, Any]]:
           """Discover available migration files."""
           migrations_dir = Path(self.config["migrations_dir"])
           
           self.logger.info("Discovering migrations", extra={
               "migrations_dir": str(migrations_dir),
               "migration_id": self.migration_id
           })
           
           try:
               if not migrations_dir.exists():
                   self.logger.warning("Migrations directory does not exist", extra={
                       "migrations_dir": str(migrations_dir),
                       "migration_id": self.migration_id
                   })
                   return []
               
               migration_files = []
               for file_path in migrations_dir.glob("*.sql"):
                   migration_info = {
                       "file_path": str(file_path),
                       "file_name": file_path.name,
                       "file_size": file_path.stat().st_size,
                       "modified_time": file_path.stat().st_mtime
                   }
                   migration_files.append(migration_info)
               
               # Sort by filename (assuming numbered migrations)
               migration_files.sort(key=lambda x: x["file_name"])
               
               self.logger.info("Migration discovery completed", extra={
                   "migrations_dir": str(migrations_dir),
                   "migration_id": self.migration_id,
                   "migrations_found": len(migration_files),
                   "migration_files": [m["file_name"] for m in migration_files]
               })
               
               return migration_files
               
           except Exception as e:
               self.logger.error("Failed to discover migrations", extra={
                   "migrations_dir": str(migrations_dir),
                   "migration_id": self.migration_id,
                   "error": str(e),
                   "error_type": type(e).__name__
               })
               raise
       
       def create_backup(self) -> str:
           """Create database backup before migration."""
           backup_dir = Path(self.config["backup_dir"])
           backup_file = backup_dir / f"backup_{self.migration_id}.sql"
           
           self.logger.info("Creating database backup", extra={
               "backup_file": str(backup_file),
               "migration_id": self.migration_id
           })
           
           try:
               # Ensure backup directory exists
               backup_dir.mkdir(parents=True, exist_ok=True)
               
               # Simulate database backup (in real implementation, use pg_dump, mysqldump, etc.)
               backup_start_time = time.time()
               
               # Simulate backup process
               time.sleep(0.1)  # Simulate backup time
               
               # Create dummy backup file
               with open(backup_file, 'w') as f:
                   f.write(f"-- Database backup created at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                   f.write(f"-- Migration ID: {self.migration_id}\n")
                   f.write("-- This is a simulated backup file\n")
               
               backup_duration = time.time() - backup_start_time
               
               self.logger.info("Database backup completed", extra={
                   "backup_file": str(backup_file),
                   "migration_id": self.migration_id,
                   "backup_size_bytes": backup_file.stat().st_size,
                   "backup_duration_seconds": round(backup_duration, 2)
               })
               
               return str(backup_file)
               
           except Exception as e:
               self.logger.error("Failed to create database backup", extra={
                   "backup_file": str(backup_file),
                   "migration_id": self.migration_id,
                   "error": str(e),
                   "error_type": type(e).__name__
               })
               raise
       
       def apply_migration(self, migration_info: Dict[str, Any], dry_run: bool = False) -> bool:
           """Apply a single migration with logging."""
           migration_start_time = time.time()
           
           self.logger.info("Applying migration", extra={
               "migration_file": migration_info["file_name"],
               "migration_id": self.migration_id,
               "dry_run": dry_run,
               "file_size_bytes": migration_info["file_size"]
           })
           
           try:
               # Read migration file
               with open(migration_info["file_path"], 'r') as f:
                   migration_sql = f.read()
               
               if dry_run:
                   self.logger.info("Dry run - migration would be applied", extra={
                       "migration_file": migration_info["file_name"],
                       "migration_id": self.migration_id,
                       "sql_length": len(migration_sql),
                       "sql_preview": migration_sql[:200] + "..." if len(migration_sql) > 200 else migration_sql
                   })
                   return True
               
               # Simulate database execution
               self.logger.debug("Executing migration SQL", extra={
                   "migration_file": migration_info["file_name"],
                   "migration_id": self.migration_id,
                   "sql_length": len(migration_sql)
               })
               
               # Simulate execution time
               time.sleep(0.05)
               
               migration_duration = time.time() - migration_start_time
               
               self.logger.info("Migration applied successfully", extra={
                   "migration_file": migration_info["file_name"],
                   "migration_id": self.migration_id,
                   "duration_seconds": round(migration_duration, 2),
                   "sql_length": len(migration_sql)
               })
               
               return True
               
           except Exception as e:
               self.logger.error("Failed to apply migration", extra={
                   "migration_file": migration_info["file_name"],
                   "migration_id": self.migration_id,
                   "error": str(e),
                   "error_type": type(e).__name__,
                   "duration_seconds": round(time.time() - migration_start_time, 2)
               })
               return False
       
       def run_migrations(self, dry_run: bool = False) -> Dict[str, Any]:
           """Run all pending migrations."""
           start_time = time.time()
           
           self.logger.info("Migration process started", extra={
               "migration_id": self.migration_id,
               "dry_run": dry_run,
               "start_time": time.strftime("%Y-%m-%d %H:%M:%S")
           })
           
           try:
               # Discover migrations
               migrations = self.discover_migrations()
               
               if not migrations:
                   self.logger.warning("No migrations found")
                   return {
                       "success": True,
                       "migrations_applied": 0,
                       "migrations_failed": 0,
                       "backup_created": False
                   }
               
               # Create backup (only if not dry run)
               backup_file = None
               if not dry_run:
                   backup_file = self.create_backup()
               
               # Apply migrations
               successful_migrations = []
               failed_migrations = []
               
               for migration_info in migrations:
                   success = self.apply_migration(migration_info, dry_run)
                   
                   if success:
                       successful_migrations.append(migration_info["file_name"])
                   else:
                       failed_migrations.append(migration_info["file_name"])
               
               duration = time.time() - start_time
               
               summary = {
                   "success": len(failed_migrations) == 0,
                   "migrations_applied": len(successful_migrations),
                   "migrations_failed": len(failed_migrations),
                   "total_migrations": len(migrations),
                   "duration_seconds": round(duration, 2),
                   "backup_created": backup_file is not None,
                   "backup_file": backup_file,
                   "successful_migrations": successful_migrations,
                   "failed_migrations": failed_migrations,
                   "dry_run": dry_run
               }
               
               if summary["success"]:
                   self.logger.info("All migrations completed successfully", extra={
                       "migration_id": self.migration_id,
                       "summary": summary
                   })
               else:
                   self.logger.error("Some migrations failed", extra={
                       "migration_id": self.migration_id,
                       "summary": summary
                   })
               
               return summary
               
           except Exception as e:
               self.logger.error("Migration process failed", extra={
                   "migration_id": self.migration_id,
                   "error": str(e),
                   "error_type": type(e).__name__,
                   "duration_seconds": round(time.time() - start_time, 2)
               })
               raise
   
   def main():
       """Main CLI entry point."""
       parser = argparse.ArgumentParser(
           description="Database migration tool with comprehensive logging",
           formatter_class=argparse.RawDescriptionHelpFormatter
       )
       
       parser.add_argument(
           "--config",
           required=True,
           help="Path to configuration JSON file"
       )
       parser.add_argument(
           "--dry-run",
           action="store_true",
           help="Show what would be done without applying changes"
       )
       parser.add_argument(
           "--apply",
           action="store_true",
           help="Apply migrations (required if not dry-run)"
       )
       parser.add_argument(
           "--log-file",
           help="Path to log file"
       )
       parser.add_argument(
           "-v", "--verbose",
           action="store_true",
           help="Enable verbose logging"
       )
       
       args = parser.parse_args()
       
       # Validate arguments
       if not args.dry_run and not args.apply:
           parser.error("Must specify either --dry-run or --apply")
       
       # Configure logging
       import os
       if args.verbose:
           os.environ["LOG_LEVEL"] = "DEBUG"
       if args.log_file:
           os.environ["LOG_TO_FILE"] = "true"
           os.environ["LOG_FILE_DIR"] = str(Path(args.log_file).parent)
       
       logger = get_logger(__name__)
       
       logger.info("Database migration tool started", extra={
           "command_line_args": vars(args),
           "dry_run_mode": args.dry_run
       })
       
       try:
           # Initialize migrator
           migrator = DatabaseMigrator(args.config, logger)
           
           # Run migrations
           summary = migrator.run_migrations(dry_run=args.dry_run)
           
           # Exit with appropriate code
           if summary["success"]:
               logger.info("Migration process completed successfully")
               sys.exit(0)
           else:
               logger.error("Migration process completed with errors")
               sys.exit(1)
               
       except Exception as e:
           logger.error("Migration tool failed", extra={
               "error": str(e),
               "error_type": type(e).__name__
           }, exc_info=True)
           sys.exit(1)
   
   if __name__ == "__main__":
       main()

Monitoring Script
-----------------

System monitoring CLI with periodic logging:

.. code-block:: python

   #!/usr/bin/env python3
   """
   System monitoring CLI tool with periodic logging.
   
   Usage:
       python monitor_system.py --interval 30 --duration 3600
       python monitor_system.py --config monitor.json --log-file /var/log/monitor.log
   """
   
   import argparse
   import json
   import os
   import sys
   import time
   import signal
   import psutil
   from pathlib import Path
   from typing import Dict, Any, Optional
   from mypylogger import get_logger
   
   class SystemMonitor:
       """System monitoring tool with comprehensive logging."""
       
       def __init__(self, config: Dict[str, Any], logger):
           self.logger = logger
           self.config = config
           self.monitoring = False
           self.start_time = time.time()
           self.samples_collected = 0
           
           # Set up signal handlers
           signal.signal(signal.SIGINT, self._signal_handler)
           signal.signal(signal.SIGTERM, self._signal_handler)
       
       def _signal_handler(self, signum, frame):
           """Handle shutdown signals gracefully."""
           signal_name = signal.Signals(signum).name
           self.logger.info("Received shutdown signal", extra={
               "signal": signal_name,
               "samples_collected": self.samples_collected,
               "monitoring_duration": round(time.time() - self.start_time, 2)
           })
           self.monitoring = False
       
       def collect_system_metrics(self) -> Dict[str, Any]:
           """Collect comprehensive system metrics."""
           try:
               # CPU metrics
               cpu_percent = psutil.cpu_percent(interval=1)
               cpu_count = psutil.cpu_count()
               cpu_freq = psutil.cpu_freq()
               
               # Memory metrics
               memory = psutil.virtual_memory()
               swap = psutil.swap_memory()
               
               # Disk metrics
               disk_usage = psutil.disk_usage('/')
               disk_io = psutil.disk_io_counters()
               
               # Network metrics
               network_io = psutil.net_io_counters()
               
               # Process metrics
               process_count = len(psutil.pids())
               
               # Load average (Unix-like systems)
               load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
               
               metrics = {
                   "timestamp": time.time(),
                   "cpu": {
                       "percent": cpu_percent,
                       "count": cpu_count,
                       "frequency_mhz": cpu_freq.current if cpu_freq else None
                   },
                   "memory": {
                       "total_bytes": memory.total,
                       "available_bytes": memory.available,
                       "used_bytes": memory.used,
                       "percent": memory.percent,
                       "swap_total_bytes": swap.total,
                       "swap_used_bytes": swap.used,
                       "swap_percent": swap.percent
                   },
                   "disk": {
                       "total_bytes": disk_usage.total,
                       "used_bytes": disk_usage.used,
                       "free_bytes": disk_usage.free,
                       "percent": (disk_usage.used / disk_usage.total) * 100,
                       "read_bytes": disk_io.read_bytes if disk_io else 0,
                       "write_bytes": disk_io.write_bytes if disk_io else 0
                   },
                   "network": {
                       "bytes_sent": network_io.bytes_sent,
                       "bytes_recv": network_io.bytes_recv,
                       "packets_sent": network_io.packets_sent,
                       "packets_recv": network_io.packets_recv
                   },
                   "system": {
                       "process_count": process_count,
                       "load_avg_1min": load_avg[0],
                       "load_avg_5min": load_avg[1],
                       "load_avg_15min": load_avg[2]
                   }
               }
               
               return metrics
               
           except Exception as e:
               self.logger.error("Failed to collect system metrics", extra={
                   "error": str(e),
                   "error_type": type(e).__name__
               })
               raise
       
       def check_thresholds(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
           """Check metrics against configured thresholds."""
           alerts = []
           
           thresholds = self.config.get("thresholds", {})
           
           # CPU threshold
           cpu_threshold = thresholds.get("cpu_percent", 80)
           if metrics["cpu"]["percent"] > cpu_threshold:
               alerts.append({
                   "type": "cpu_high",
                   "metric": "cpu_percent",
                   "value": metrics["cpu"]["percent"],
                   "threshold": cpu_threshold,
                   "severity": "warning"
               })
           
           # Memory threshold
           memory_threshold = thresholds.get("memory_percent", 85)
           if metrics["memory"]["percent"] > memory_threshold:
               alerts.append({
                   "type": "memory_high",
                   "metric": "memory_percent",
                   "value": metrics["memory"]["percent"],
                   "threshold": memory_threshold,
                   "severity": "warning"
               })
           
           # Disk threshold
           disk_threshold = thresholds.get("disk_percent", 90)
           if metrics["disk"]["percent"] > disk_threshold:
               alerts.append({
                   "type": "disk_high",
                   "metric": "disk_percent",
                   "value": metrics["disk"]["percent"],
                   "threshold": disk_threshold,
                   "severity": "critical"
               })
           
           # Load average threshold
           load_threshold = thresholds.get("load_avg_1min", metrics["cpu"]["count"] * 2)
           if metrics["system"]["load_avg_1min"] > load_threshold:
               alerts.append({
                   "type": "load_high",
                   "metric": "load_avg_1min",
                   "value": metrics["system"]["load_avg_1min"],
                   "threshold": load_threshold,
                   "severity": "warning"
               })
           
           return {"alerts": alerts, "alert_count": len(alerts)}
       
       def log_metrics(self, metrics: Dict[str, Any], alerts: Dict[str, Any]) -> None:
           """Log collected metrics and any alerts."""
           # Log basic metrics
           self.logger.info("System metrics collected", extra={
               "sample_number": self.samples_collected,
               "cpu_percent": metrics["cpu"]["percent"],
               "memory_percent": metrics["memory"]["percent"],
               "disk_percent": round(metrics["disk"]["percent"], 1),
               "load_avg_1min": metrics["system"]["load_avg_1min"],
               "process_count": metrics["system"]["process_count"],
               "alert_count": alerts["alert_count"]
           })
           
           # Log detailed metrics in debug mode
           self.logger.debug("Detailed system metrics", extra={
               "sample_number": self.samples_collected,
               "metrics": metrics
           })
           
           # Log alerts
           for alert in alerts["alerts"]:
               if alert["severity"] == "critical":
                   self.logger.error("System alert - critical", extra={
                       "alert": alert,
                       "sample_number": self.samples_collected
                   })
               else:
                   self.logger.warning("System alert - warning", extra={
                       "alert": alert,
                       "sample_number": self.samples_collected
                   })
       
       def run_monitoring(self) -> Dict[str, Any]:
           """Run continuous system monitoring."""
           interval = self.config.get("interval_seconds", 60)
           duration = self.config.get("duration_seconds", 3600)
           
           self.logger.info("System monitoring started", extra={
               "interval_seconds": interval,
               "duration_seconds": duration,
               "end_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + duration))
           })
           
           self.monitoring = True
           end_time = self.start_time + duration
           
           try:
               while self.monitoring and time.time() < end_time:
                   sample_start_time = time.time()
                   
                   # Collect metrics
                   metrics = self.collect_system_metrics()
                   
                   # Check thresholds
                   alerts = self.check_thresholds(metrics)
                   
                   # Log metrics and alerts
                   self.log_metrics(metrics, alerts)
                   
                   self.samples_collected += 1
                   
                   # Calculate sleep time to maintain interval
                   sample_duration = time.time() - sample_start_time
                   sleep_time = max(0, interval - sample_duration)
                   
                   if sleep_time > 0:
                       time.sleep(sleep_time)
               
               total_duration = time.time() - self.start_time
               
               summary = {
                   "success": True,
                   "samples_collected": self.samples_collected,
                   "total_duration_seconds": round(total_duration, 2),
                   "average_interval_seconds": round(total_duration / self.samples_collected, 2) if self.samples_collected > 0 else 0,
                   "monitoring_completed": not self.monitoring or time.time() >= end_time
               }
               
               self.logger.info("System monitoring completed", extra=summary)
               
               return summary
               
           except Exception as e:
               self.logger.error("System monitoring failed", extra={
                   "error": str(e),
                   "error_type": type(e).__name__,
                   "samples_collected": self.samples_collected,
                   "duration_seconds": round(time.time() - self.start_time, 2)
               })
               raise
   
   def load_config(config_path: Optional[str], args: argparse.Namespace) -> Dict[str, Any]:
       """Load configuration from file or command line arguments."""
       config = {}
       
       # Load from file if provided
       if config_path:
           config_file = Path(config_path)
           if config_file.exists():
               with open(config_file, 'r') as f:
                   config = json.load(f)
       
       # Override with command line arguments
       if args.interval:
           config["interval_seconds"] = args.interval
       if args.duration:
           config["duration_seconds"] = args.duration
       
       # Set defaults
       config.setdefault("interval_seconds", 60)
       config.setdefault("duration_seconds", 3600)
       config.setdefault("thresholds", {
           "cpu_percent": 80,
           "memory_percent": 85,
           "disk_percent": 90
       })
       
       return config
   
   def main():
       """Main CLI entry point."""
       parser = argparse.ArgumentParser(
           description="System monitoring tool with comprehensive logging",
           formatter_class=argparse.RawDescriptionHelpFormatter
       )
       
       parser.add_argument(
           "--config",
           help="Path to configuration JSON file"
       )
       parser.add_argument(
           "--interval",
           type=int,
           help="Monitoring interval in seconds (default: 60)"
       )
       parser.add_argument(
           "--duration",
           type=int,
           help="Monitoring duration in seconds (default: 3600)"
       )
       parser.add_argument(
           "--log-file",
           help="Path to log file"
       )
       parser.add_argument(
           "-v", "--verbose",
           action="store_true",
           help="Enable verbose logging"
       )
       
       args = parser.parse_args()
       
       # Configure logging
       if args.verbose:
           os.environ["LOG_LEVEL"] = "DEBUG"
       if args.log_file:
           os.environ["LOG_TO_FILE"] = "true"
           os.environ["LOG_FILE_DIR"] = str(Path(args.log_file).parent)
       
       logger = get_logger(__name__)
       
       logger.info("System monitoring tool started", extra={
           "command_line_args": vars(args)
       })
       
       try:
           # Load configuration
           config = load_config(args.config, args)
           
           logger.info("Configuration loaded", extra={
               "config": config
           })
           
           # Initialize monitor
           monitor = SystemMonitor(config, logger)
           
           # Run monitoring
           summary = monitor.run_monitoring()
           
           # Exit with appropriate code
           if summary["success"]:
               logger.info("Monitoring completed successfully")
               sys.exit(0)
           else:
               logger.error("Monitoring completed with errors")
               sys.exit(1)
               
       except KeyboardInterrupt:
           logger.info("Monitoring interrupted by user")
           sys.exit(0)
           
       except Exception as e:
           logger.error("Monitoring tool failed", extra={
               "error": str(e),
               "error_type": type(e).__name__
           }, exc_info=True)
           sys.exit(1)
   
   if __name__ == "__main__":
       main()