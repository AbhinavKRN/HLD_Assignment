# Visit Counter Service

A scalable visit counter service with Redis sharding and caching implementation.

## Features

- Basic visit counting with Redis persistence
- Redis sharding using consistent hashing
- Application-level caching
- Write batching
- Fault tolerance
- Performance monitoring

## Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Redis

## Project Structure

```
visit_counter_assignment/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           └── counter.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── consistent_hash.py
│   │   └── redis_manager.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── counter.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── visit_counter.py
│   └── main.py
├── .env
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Setup Instructions

1. Clone the repository:
```bash
git clone <repository-url>
cd visit_counter_assignment
```

2. Create .env file:
```ini
# Redis Configuration
REDIS_NODES=redis://redis1:6379,redis://redis2:6379,redis://redis3:6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_TIMEOUT=5
REDIS_RETRY_ATTEMPTS=3

# Consistent Hashing Configuration
VIRTUAL_NODES=100

# Cache Configuration
CACHE_TTL_SECONDS=5
CACHE_CAPACITY=1000

# Batch Processing Configuration
BATCH_INTERVAL_SECONDS=5.0
BATCH_SIZE_LIMIT=1000

# Application Configuration
DEBUG=true
API_PREFIX=/api/v1
PROJECT_NAME=Visit Counter Service

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_INTERVAL_SECONDS=60
```

3. Build and start services:
```bash
docker-compose up --build -d
```

## API Documentation

### Base URL
```
http://localhost:8000/api/v1
```

### 1. Record Visit
Records a new visit for a specific page.

**Endpoint**: `/counter/visit/{page_id}`
**Method**: `POST`

#### Request
```bash
curl -X POST http://localhost:8000/api/v1/counter/visit/page1
```

#### Response
```json
{
    "status": "success",
    "message": "Visit recorded for page page1",
    "page_id": "page1",
    "timestamp": "2025-02-23T15:30:45.123456"
}
```

### 2. Get Visit Count
Retrieves the visit count for a specific page.

**Endpoint**: `/counter/visits/{page_id}`
**Method**: `GET`

#### Request
```bash
curl http://localhost:8000/api/v1/counter/visits/page1
```

#### Response
```json
{
    "visits": 42,
    "served_via": "in_memory"  // Can be "in_memory", "redis", "redis_7070", or "redis_7071"
}
```

### 3. Reset Counter
Resets the visit counter for a specific page.

**Endpoint**: `/counter/visits/{page_id}`
**Method**: `DELETE`

#### Request
```bash
curl -X DELETE http://localhost:8000/api/v1/counter/visits/page1
```

#### Response
```json
{
    "status": "success",
    "message": "Counter reset for page page1",
    "page_id": "page1"
}
```

### 4. Get Counter Metrics
Retrieves metrics about the counter service.

**Endpoint**: `/counter/metrics`
**Method**: `GET`

#### Request
```bash
curl http://localhost:8000/api/v1/counter/metrics
```

#### Response
```json
{
    "status": "healthy",
    "metrics": {
        "cache_hits": 150,
        "cache_misses": 30,
        "cache_size": 100,
        "write_buffer_size": 25
    },
    "redis_nodes": {
        "redis://redis1:6379": true,
        "redis://redis2:6379": true,
        "redis://redis3:6379": true
    },
    "last_batch_write": "2025-02-23T15:30:45.123456"
}
```

### 5. Service Status
Get detailed service status including Redis health.

**Endpoint**: `/status`
**Method**: `GET`

#### Request
```bash
curl http://localhost:8000/status
```

#### Response
```json
{
    "status": "healthy",
    "uptime": "1:23:45.678901",
    "total_requests": 1234,
    "redis_status": {
        "nodes": 3,
        "healthy_nodes": 3,
        "node_status": {
            "redis://redis1:6379": true,
            "redis://redis2:6379": true,
            "redis://redis3:6379": true
        }
    },
    "counter_status": {
        "cache_size": 100,
        "write_buffer_size": 25
    },
    "version": "1.0.0",
    "debug_mode": true
}
```

## Testing Examples

### 1. Basic Flow Test
```bash
# Record a visit
curl -X POST http://localhost:8000/api/v1/counter/visit/page1

# Get the count
curl http://localhost:8000/api/v1/counter/visits/page1

# Reset the counter
curl -X DELETE http://localhost:8000/api/v1/counter/visits/page1
```

### 2. Cache Test
```bash
# Make multiple rapid requests to test caching
for i in {1..5}; do 
    curl http://localhost:8000/api/v1/counter/visits/page1
    echo ""
    sleep 1
done
```

### 3. Load Test
```bash
# Record multiple visits
for i in {1..10}; do 
    curl -X POST http://localhost:8000/api/v1/counter/visit/page1 &
done
```

### 4. Sharding Test
```bash
# Create visits for multiple pages
for i in {1..5}; do 
    curl -X POST http://localhost:8000/api/v1/counter/visit/page$i
done

# Check counts across shards
for i in {1..5}; do 
    curl http://localhost:8000/api/v1/counter/visits/page$i
done
```

## Monitoring

### Redis Status
```bash
# Connect to Redis instances
docker exec -it visit_counter_assignment-redis1-1 redis-cli
docker exec -it visit_counter_assignment-redis2-1 redis-cli
docker exec -it visit_counter_assignment-redis3-1 redis-cli
```

### Application Logs
```bash
# View logs
docker-compose logs -f app

# View Redis logs
docker-compose logs -f redis1
docker-compose logs -f redis2
docker-compose logs -f redis3
```

## Troubleshooting

1. If the server doesn't start:
```bash
# Check logs
docker-compose logs app

# Restart the service
docker-compose restart app
```

2. If Redis connection fails:
```bash
# Check Redis status
docker-compose ps

# Restart Redis instances
docker-compose restart redis1 redis2 redis3
```

3. Clean restart:
```bash
# Stop all services
docker-compose down

# Remove volumes
docker-compose down -v

# Rebuild and start
docker-compose up --build -d
```

## Notes

1. Cache entries expire after 5 seconds
2. Write operations are batched every 5 seconds
3. Redis sharding uses consistent hashing
4. Health checks run every 30 seconds
5. Rate limiting is not implemented in the current version

## Error Codes

- `200`: Success
- `404`: Page not found
- `500`: Internal server error

## Response Headers

- `X-Process-Time`: Time taken to process the request in seconds
- `Content-Type`: application/json
