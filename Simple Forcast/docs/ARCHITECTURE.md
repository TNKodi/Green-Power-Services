# 📐 System Architecture Diagram

## Overall System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT                                   │
│  (API Consumer: Web App, Mobile App, Monitoring System, etc.)   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ HTTP/REST Requests
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FASTAPI APPLICATION                            │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │               API ENDPOINTS                             │    │
│  │                                                         │    │
│  │  GET  /health          → Health Check                  │    │
│  │  POST /forecast/start  → Start Forecast Job            │    │
│  │  GET  /forecast/status → Check Job Status              │    │
│  │  POST /forecast/new-asset → Process Single Asset       │    │
│  └────────────────┬───────────────────────────────────────┘    │
│                   │                                             │
│                   ▼                                             │
│  ┌────────────────────────────────────────────────────────┐    │
│  │               SERVICES LAYER                            │    │
│  │                                                         │    │
│  │  ┌─────────────────┐  ┌──────────────┐  ┌──────────┐ │    │
│  │  │ Forecast Service│  │ Job Manager  │  │ TB Client│ │    │
│  │  │                 │  │              │  │          │ │    │
│  │  │ - Orchestrate   │  │ - Track jobs │  │ - Auth   │ │    │
│  │  │ - Run models    │  │ - Update     │  │ - Assets │ │    │
│  │  │ - Write data    │  │   status     │  │ - Attrs  │ │    │
│  │  └─────────────────┘  └──────────────┘  └──────────┘ │    │
│  └────────────────┬───────────────────────────────────────┘    │
│                   │                                             │
└───────────────────┼─────────────────────────────────────────────┘
                    │
                    │ REST API Calls
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    THINGSBOARD                                   │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │  Assets    │  │ Attributes │  │ Telemetry  │               │
│  │            │  │            │  │            │               │
│  │ - Hierarchy│  │ - Device   │  │ - Forecast │               │
│  │ - Relations│  │   config   │  │   results  │               │
│  └────────────┘  └────────────┘  └────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

## Forecast Job Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                  FORECAST JOB LIFECYCLE                          │
└─────────────────────────────────────────────────────────────────┘

1. START
   │
   │ Client → POST /forecast/start {main_asset_id}
   │
   ▼
   ┌──────────────────────┐
   │  Create Job          │
   │  Status: PENDING     │ ← Returns job_id immediately
   └──────────┬───────────┘
              │
              ▼
   ┌──────────────────────┐
   │  Background Task     │
   │  Status: RUNNING     │
   └──────────┬───────────┘
              │
              ▼
   ┌──────────────────────┐
   │  Get Asset Hierarchy │
   │  (Recursive)         │
   │  Level 1 → 2 → 3     │
   └──────────┬───────────┘
              │
              ▼
   ┌──────────────────────┐
   │  For Each Asset:     │
   │  1. Read attributes  │
   │  2. Run forecast     │
   │  3. Write telemetry  │
   │  4. Update progress  │
   └──────────┬───────────┘
              │
              ▼
   ┌──────────────────────┐
   │  Job Complete        │
   │  Status: COMPLETED   │
   └──────────────────────┘

  (Client can check status anytime with GET /forecast/status/{job_id})
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA FLOW DIAGRAM                           │
└─────────────────────────────────────────────────────────────────┘

ThingsBoard                API Service              Power Model
    │                          │                         │
    │  1. Login (JWT)          │                         │
    │◄─────────────────────────┤                         │
    ├──────────────────────────►                         │
    │  (JWT Token)             │                         │
    │                          │                         │
    │  2. Get Asset Relations  │                         │
    │◄─────────────────────────┤                         │
    ├──────────────────────────►                         │
    │  (Child Asset IDs)       │                         │
    │                          │                         │
    │  3. Read Attributes      │                         │
    │◄─────────────────────────┤                         │
    ├──────────────────────────►                         │
    │  (Config Data)           │                         │
    │                          │                         │
    │                          │  4. Run Forecast        │
    │                          ├────────────────────────►│
    │                          │  (Attributes)           │
    │                          │                         │
    │                          │◄────────────────────────┤
    │                          │  (Forecast Results)     │
    │                          │                         │
    │  5. Write Telemetry      │                         │
    │◄─────────────────────────┤                         │
    ├──────────────────────────►                         │
    │  (Success)               │                         │
    │                          │                         │
```

## Component Interaction

```
┌─────────────────────────────────────────────────────────────────┐
│                   COMPONENT DIAGRAM                              │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│   API Routes     │  ← Define HTTP endpoints
└────────┬─────────┘
         │
         │ Uses
         ▼
┌──────────────────┐
│ Forecast Service │  ← Orchestrate workflow
└────────┬─────────┘
         │
         ├──────────────────────────┐
         │                          │
         │ Uses                     │ Uses
         ▼                          ▼
┌──────────────────┐       ┌──────────────────┐
│  TB Client       │       │  Job Manager     │
│                  │       │                  │
│ - Auth           │       │ - Create job     │
│ - Get assets     │       │ - Track status   │
│ - Read attrs     │       │ - Update progress│
│ - Write telem    │       └──────────────────┘
└────────┬─────────┘
         │
         │ Calls
         ▼
┌──────────────────┐
│  ThingsBoard     │  ← External system
│  REST API        │
└──────────────────┘

┌──────────────────┐
│  Power Model     │  ← Existing logic
│  (Scripts/)      │
└──────────────────┘
         ▲
         │ Imports
         │
┌──────────────────┐
│ Forecast Service │
└──────────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT OPTIONS                            │
└─────────────────────────────────────────────────────────────────┘

Option 1: Simple Deployment
────────────────────────────
┌──────────────────────┐
│   Server/VM          │
│                      │
│  ┌────────────────┐  │
│  │ Python App     │  │
│  │ (FastAPI)      │  │
│  │ Port: 8000     │  │
│  └────────────────┘  │
└──────────────────────┘


Option 2: Docker Container
──────────────────────────
┌──────────────────────┐
│   Docker Host        │
│                      │
│  ┌────────────────┐  │
│  │ Docker         │  │
│  │ Container      │  │
│  │                │  │
│  │  ┌──────────┐  │  │
│  │  │ FastAPI  │  │  │
│  │  │ App      │  │  │
│  │  └──────────┘  │  │
│  └────────────────┘  │
└──────────────────────┘


Option 3: Production Setup
──────────────────────────
┌─────────────────────────────────────────┐
│          Load Balancer (Nginx)          │
└────────┬──────────────────────┬─────────┘
         │                      │
         ▼                      ▼
┌──────────────────┐   ┌──────────────────┐
│   API Instance 1 │   │   API Instance 2 │
│   (FastAPI)      │   │   (FastAPI)      │
└────────┬─────────┘   └────────┬─────────┘
         │                      │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────┐
         │      Redis       │
         │  (Job Storage)   │
         └──────────────────┘
```

## Job Manager States

```
┌─────────────────────────────────────────────────────────────────┐
│                   JOB STATE MACHINE                              │
└─────────────────────────────────────────────────────────────────┘

                    ┌─────────┐
                    │ PENDING │  ← Job created
                    └────┬────┘
                         │
                         │ Start execution
                         ▼
                    ┌─────────┐
              ┌─────┤ RUNNING ├─────┐
              │     └────┬────┘     │
              │          │          │
   Success    │          │ Error    │
              ▼          ▼          ▼
        ┌───────────┐          ┌────────┐
        │ COMPLETED │          │ FAILED │
        └───────────┘          └────────┘
```

## Async Execution Model

```
┌─────────────────────────────────────────────────────────────────┐
│              ASYNC EXECUTION PATTERN                             │
└─────────────────────────────────────────────────────────────────┘

Client Request Thread           Background Task Thread
        │                               │
        │ POST /forecast/start          │
        ├────────────┐                  │
        │ Create Job │                  │
        │ Return ID  │                  │
        ◄────────────┘                  │
        │                               │
        │                    ┌──────────▼──────────┐
        │                    │ Process Assets      │
        │                    │ - Get hierarchy     │
        │                    │ - Read attributes   │
        │                    │ - Run forecasts     │
        │                    │ - Write telemetry   │
        │                    └──────────┬──────────┘
        │                               │
        │ GET /forecast/status/{id}     │
        ├────────────┐                  │
        │ Get Status │                  │
        ◄────────────┘                  │
        │                               │
        │                    ┌──────────▼──────────┐
        │                    │ Complete Job        │
        │                    └─────────────────────┘
        │
```

---

This architecture ensures:
- ✅ Non-blocking API responses
- ✅ Concurrent job execution
- ✅ Scalable design
- ✅ Clean separation of concerns
- ✅ Easy to maintain and extend
