# mypylogger Performance

**Performance characteristics and benchmarks**

## Current Status

⚠️ **Formal benchmarks pending** - Performance testing infrastructure is being established.

This document outlines expected performance characteristics based on code architecture and known Python logging behavior. Formal benchmarks will be added soon.

## Expected Performance Profile

### Design Characteristics

| Aspect | Characteristic |
|--------|---------------|
| **Overhead** | Low - minimal processing beyond standard Python logging |
| **Memory** | <1MB runtime footprint |
| **Blocking** | Synchronous - logs block until written |
| **I/O** | Immediate flush for real-time monitoring |
| **Serialization** | Native Python JSON encoder |

### Known Performance Considerations

1. **Stack Frame Inspection** - Adds overhead for source location tracking
   - Limited to 20 frames maximum
   - Skipped frames cached during traversal
   - Fallback to record data if inspection times out

2. **JSON Serialization** - Per-log overhead
   - Native `json.dumps()` for every log call
   - No batch processing
   - Graceful fallback to plain text on failure

3. **Synchronous I/O** - Blocks on write
   - Console: Immediate flush to stdout
   - File: Immediate write to disk
   - No async support

4. **String Formatting** - Standard Python overhead
   - ISO 8601 timestamp formatting per log
   - Relative path resolution per log
   - Message interpolation via standard logging

## Performance Best Practices

### 1. Use Appropriate Log Levels

```python
# ❌ BAD - Always evaluates expensive operation
logger.debug(f"State: {expensive_debug_dump()}")

# ✅ GOOD - Only evaluates if DEBUG enabled
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"State: {expensive_debug_dump()}")
```

### 2. Minimize Extra Fields

```python
# ❌ BAD - Many serialized fields
logger.info("Event", extra={
    "field1": val1, "field2": val2, ..., "field20": val20
})

# ✅ GOOD - Only essential fields
logger.info("Event", extra={"request_id": req_id, "user_id": user_id})
```

### 3. Avoid Logging in Hot Paths

```python
# ❌ BAD - Logs on every iteration
for item in million_items:
    logger.debug(f"Processing {item}")  # 1M log calls!

# ✅ GOOD - Batch or sample
for i, item in enumerate(million_items):
    if i % 1000 == 0:  # Log every 1000th item
        logger.info(f"Progress: {i}/{len(million_items)}")
```

### 4. Use Lazy String Formatting

```python
# ❌ BAD - Always formats string
logger.debug(f"User {user.name} did {action}")

# ✅ GOOD - Only formats if level enabled
logger.debug("User %s did %s", user.name, action)
```

### 5. Pre-compute Expensive Values

```python
# ❌ BAD - Computes on every log call
logger.info("Metrics", extra={"avg": sum(values)/len(values)})

# ✅ GOOD - Compute once
avg = sum(values) / len(values)
logger.info("Metrics", extra={"avg": avg})
```

## Performance Comparison

**Note**: These are estimates pending formal benchmarks.

### Expected Overhead Per Log Call

| Operation | Estimated Time |
|-----------|---------------|
| Minimal log (no extra) | ~50-100 µs |
| With 5 extra fields | ~100-200 µs |
| With stack inspection | +20-50 µs |
| JSON serialization | ~30-80 µs |
| File write + flush | +100-500 µs (I/O dependent) |

### Memory Footprint

| Component | Size |
|-----------|------|
| Installed package | <100 KB |
| Runtime import | <500 KB |
| Per-logger instance | <10 KB |
| Per-log record | ~1-5 KB (depends on message + extra) |

## When NOT to Use mypylogger

Consider alternatives for:

❌ **High-frequency logging** (>10,000 logs/second)
- Use: Async logging libraries (e.g., aiologger)
- Reason: Synchronous I/O becomes bottleneck

❌ **Performance-critical hot paths**
- Use: Conditional logging or sampling
- Reason: Every log call has overhead

❌ **Real-time systems with strict latency requirements**
- Use: Buffered or async logging
- Reason: Immediate flush adds latency

❌ **Extremely resource-constrained environments**
- Use: Null logger or minimal logging
- Reason: JSON serialization and stack inspection have overhead

## Optimization Roadmap

Planned performance improvements:

### Short Term
- [ ] Establish pytest-benchmark infrastructure
- [ ] Baseline benchmarks for common operations
- [ ] Document actual overhead measurements

### Medium Term
- [ ] Optional batch logging mode
- [ ] Configurable flush behavior
- [ ] Lazy stack frame inspection (opt-in)

### Long Term
- [ ] Optional async handler support
- [ ] C extension for hot path optimization (if warranted)
- [ ] Performance regression testing in CI

## Benchmark Infrastructure

**Status**: In development

Planned benchmarks:
- Log call overhead (minimal, with extra fields)
- JSON serialization performance
- Stack frame inspection overhead
- File I/O throughput
- Memory usage under load
- Concurrent logging performance

**Benchmark tool**: pytest-benchmark (already in dev dependencies)

**Run benchmarks** (when available):
```bash
uv run pytest tests/performance/ --benchmark-only
```

## Known Bottlenecks

Based on code inspection:

1. **Stack frame traversal** (`_extract_source_location`)
   - Walks up to 20 frames per log
   - Unavoidable for source location tracking
   - Mitigation: Already optimized with early exit

2. **JSON serialization** (`json.dumps`)
   - Native Python implementation
   - Per-call overhead
   - Mitigation: Keep extra fields minimal

3. **Immediate flush** (console handler)
   - Forces I/O completion before return
   - Required for real-time monitoring
   - Mitigation: Disable file logging if not needed

4. **ISO 8601 formatting** (`strftime`)
   - Per-log timestamp conversion
   - Standard Python overhead
   - Mitigation: None - required for standard format

## Contributing Benchmarks

To add performance benchmarks:

1. Add tests to `tests/performance/` directory
2. Use pytest-benchmark fixtures
3. Test realistic scenarios (not just micro-benchmarks)
4. Document test environment (CPU, Python version, OS)
5. Include comparison baselines

Example:
```python
def test_log_overhead(benchmark):
    logger = get_logger("perf_test")
    benchmark(logger.info, "Test message")
```

---

**Performance questions?** Open an issue: https://github.com/stabbotco1/mypylogger/issues

**Next:** [Back to docs](README.md) | [FEATURES.md](FEATURES.md) | [SECURITY.md](SECURITY.md)
