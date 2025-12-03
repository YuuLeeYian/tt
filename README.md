# Table Tennis Tracker

A Flask-based table tennis game tracker with ELO rating system.

## Docker Setup

This application uses `uv` for fast Python package management and runs on port **3050**.

### Prerequisites

- Docker installed on your system
- Git (optional, for cloning)

### Building the Docker Image

```bash
docker build -t table-tennis-tracker .
```

### Running the Container

**Option 1: With persistent database (recommended)**

This mounts a local directory to persist your SQLite database between container restarts:

```bash
# Create the instance directory locally first
mkdir -p instance

# Run with mounted database directory
docker run -d \
  --name tt-tracker \
  -p 3050:3050 \
  -v $(pwd)/instance:/app/instance \
  table-tennis-tracker
```

**Option 2: Without persistence (ephemeral)**

Database will be reset when container stops:

```bash
docker run -d \
  --name tt-tracker \
  -p 3050:3050 \
  table-tennis-tracker
```

### Accessing the Application

Once the container is running, open your browser and navigate to:

```
http://localhost:3050
```

### Managing the Container

**View logs:**
```bash
docker logs tt-tracker
```

**Stop the container:**
```bash
docker stop tt-tracker
```

**Start the container:**
```bash
docker start tt-tracker
```

**Remove the container:**
```bash
docker rm tt-tracker
```

**Rebuild after code changes:**
```bash
docker stop tt-tracker
docker rm tt-tracker
docker build -t table-tennis-tracker .
docker run -d --name tt-tracker -p 3050:3050 -v $(pwd)/instance:/app/instance table-tennis-tracker
```

## Features

- Player management (add, view, delete players)
- Game recording with automatic ELO calculation
- Player rankings and statistics
- Game history
- Win/loss tracking

