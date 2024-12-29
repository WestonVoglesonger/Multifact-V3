# Performance Benchmarks

This document provides performance benchmarks and guidelines for the System Narrative Compiler.

## Compilation Performance

The following benchmarks were run on a standard development machine (4-core CPU, 16GB RAM):

### Basic Operations

| Operation | Average Time | p95 Time | Memory Usage |
|-----------|-------------|----------|--------------|
| Simple function compilation | 2.5s | 3.2s | 150MB |
| Class compilation | 3.8s | 4.5s | 200MB |
| Multi-file project | 8.2s | 10.1s | 450MB |

### LLM Provider Comparison

| Provider | Model | Average Time | Cost per 1K tokens |
|----------|-------|--------------|-------------------|
| OpenAI | GPT-4 | 3.2s | $0.03 |
| OpenAI | GPT-3.5 | 1.8s | $0.002 |
| Groq | LLaMA2 | 1.2s | $0.0005 |
| Groq | Mixtral | 1.5s | $0.0007 |

## Memory Usage

Memory usage varies based on the complexity of the compilation task:

```python
# Memory profile for different operations
{
    "token_parsing": "50-100MB",
    "compilation": "100-300MB",
    "validation": "50-100MB",
    "total_peak": "300-500MB"
}
```

## Scaling Characteristics

### Concurrent Operations

The system is designed to handle multiple concurrent operations efficiently:

| Concurrent Users | Response Time (p95) | Memory Usage | CPU Usage |
|-----------------|---------------------|--------------|-----------|
| 1 | 2.5s | 300MB | 25% |
| 5 | 3.1s | 800MB | 60% |
| 10 | 4.2s | 1.5GB | 85% |
| 20 | 6.5s | 2.8GB | 95% |

### Database Performance

Database operations show the following characteristics:

| Operation | Average Time | p95 Time |
|-----------|-------------|----------|
| Token creation | 50ms | 120ms |
| Artifact storage | 80ms | 150ms |
| Dependency resolution | 30ms | 70ms |

## Optimization Tips

1. **Caching**
   ```python
   # Enable artifact caching
   settings = Settings(
       ENABLE_ARTIFACT_CACHE=True,
       CACHE_TTL=3600  # 1 hour
   )
   ```

2. **Batch Processing**
   ```python
   # Process multiple narratives efficiently
   async def batch_compile(narratives: List[str]) -> List[CompilationResult]:
       async with NIOrchestrator(settings) as orchestrator:
           tasks = [orchestrator.compile_narrative(n) for n in narratives]
           return await asyncio.gather(*tasks)
   ```

3. **Resource Management**
   ```python
   # Proper resource cleanup
   async with NIOrchestrator(settings) as orchestrator:
       result = await orchestrator.compile_narrative(narrative)
   # Resources automatically cleaned up
   ```

## Performance Monitoring

The system provides built-in performance monitoring:

```python
from snc.monitoring import PerformanceMonitor

monitor = PerformanceMonitor()
monitor.start_tracking()

result = await orchestrator.compile_narrative(narrative)

metrics = monitor.get_metrics()
print(f"Compilation time: {metrics.compilation_time}s")
print(f"Memory usage: {metrics.memory_usage}MB")
print(f"Token count: {metrics.token_count}")
```

## Known Performance Limitations

1. **Token Length**
   - Maximum recommended tokens per request: 4,096
   - Performance degrades significantly above 8,192 tokens

2. **Concurrent Compilations**
   - Recommended max concurrent compilations: 20
   - Scale horizontally for higher concurrency needs

3. **Memory Constraints**
   - Peak memory usage: ~150MB per active compilation
   - Recommended minimum system memory: 4GB

## Performance Tuning

### Environment Variables

```bash
# Performance-related environment variables
export SNC_MAX_CONCURRENT_COMPILATIONS=20
export SNC_CACHE_SIZE_MB=1024
export SNC_DB_POOL_SIZE=10
export SNC_LLM_TIMEOUT_SECONDS=30
```

### Configuration Options

```python
settings = Settings(
    MAX_COMPILATION_ATTEMPTS=3,
    ENABLE_ARTIFACT_CACHE=True,
    CACHE_TTL=3600,
    DB_POOL_SIZE=10,
    LLM_TIMEOUT=30,
    BATCH_SIZE=5
)
```

## Benchmarking Tools

The project includes built-in benchmarking tools:

```bash
# Run performance benchmarks
python -m snc.benchmark.run_benchmarks

# Generate performance report
python -m snc.benchmark.generate_report
```

## Performance Best Practices

1. **Resource Management**
   - Use async context managers
   - Implement proper cleanup
   - Monitor memory usage

2. **Caching Strategy**
   - Enable artifact caching
   - Use appropriate TTL values
   - Monitor cache hit rates

3. **Database Optimization**
   - Use connection pooling
   - Implement proper indexing
   - Monitor query performance

4. **LLM Provider Selection**
   - Choose based on latency requirements
   - Consider cost vs. performance
   - Implement fallback providers
