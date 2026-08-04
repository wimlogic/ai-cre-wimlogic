# 🏠 AIHOME WIMLOGIC

An open-source AI-powered Property Intelligence platform built on the WIMLOGIC AI Orchestration Platform.

> Analyze properties, organize projects, manage property images, execute AI workflows, and generate actionable property intelligence.

---

# Overview

AIHOME WIMLOGIC is an open-source business application demonstrating how modern AI can assist property owners, investors, contractors, and real estate professionals.

Instead of embedding AI logic directly into the application, AIHOME leverages the **WIMLOGIC AI Orchestration Platform**, separating business functionality from AI workflow execution.

This architecture enables reusable AI workflows across multiple business applications.

---

# Key Features

### 🏘 Project Management

- Projects
- Properties
- Property portfolio management

### 📷 Property Images

- Image upload
- Image organization
- Image version management

### 🤖 AI Property Intelligence

Generate AI-powered reports including:

- Property condition analysis
- Renovation recommendations
- Risk identification
- Room classification
- Damage detection
- Business intelligence reports

### 🎨 AI Design Studio *(In Progress)*

Future capabilities include:

- AI room redesign
- Interior design concepts
- Exterior visualization
- Before & after rendering
- Multiple design styles

### 📊 Workflow Results

- AI workflow history
- Execution status
- Reports
- Generated assets

---

# Architecture

AIHOME uses a **two-layer architecture**.

```
┌───────────────────────────────┐
│      AIHOME WIMLOGIC          │
│   Business Application Layer  │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│     WIMLOGIC Platform         │
│ AI Workflow Orchestration     │
│ AI Agents                     │
│ Knowledge Management          │
│ Governance                    │
│ Model Routing                 │
└───────────────┬───────────────┘
                │
                ▼
 OpenAI • Gemini • Anthropic • ...
```

AIHOME never communicates directly with Large Language Models (LLMs).

All AI execution is handled through the WIMLOGIC Platform using the WACP (WIMLOGIC Application Communication Protocol).

## WACP SDK

AIHOME integrates with the WIMLOGIC Platform through the
**WACP SDK — WIMLOGIC Application Communication Protocol Software
Development Kit**.

The SDK provides a standardized integration layer between business
applications and the WIMLOGIC AI orchestration platform.

It supports:

- Job submission
- Business-intent routing
- Correlation and idempotency
- Workflow status tracking
- Structured result retrieval
- Generated asset retrieval
- Error and rejection handling
- Application-to-platform authentication
- WACP protocol validation

```text
AIHOME WIMLOGIC
       │
       │ WACP SDK
       ▼
WIMLOGIC Platform
       │
       ├── WIM Module
       ├── Workflow Runtime
       ├── AI Agents
       └── AI Providers

### SDK Availability

The WACP SDK is included with this Community Edition for connecting
AIHOME to compatible WIMLOGIC Platform deployments.

### Platform Integration

AIHOME Community Edition includes the WACP integration specification
and client interface.

Access to the managed WIMLOGIC Platform and its production WACP SDK may
require a separate commercial license or service agreement.

---

# Technology Stack

## Frontend

- React
- Vite
- TypeScript
- Enterprise UI

## Backend

- FastAPI
- SQLAlchemy 2.x
- Pydantic v2
- MySQL / MariaDB

---

# Docker Deployment

AIHOME WIMLOGIC includes a complete Docker development environment for simplified installation and deployment.

## Prerequisites

Install the following software before getting started:

- Docker Desktop 4.x or later
- Docker Compose
- Git

Verify Docker installation:

```bash
docker --version
docker compose version
```

---

## Clone Repository

```bash
git clone https://github.com/wimlogic/ai-cre-wimlogic.git
cd ai-cre-wimlogic
```

---

## Configure Environment

Copy the backend environment template:

### Windows PowerShell

```powershell
copy backend\.env.example backend\.env
```

### Linux / macOS

```bash
cp backend/.env.example backend/.env
```

Edit **backend/.env** and configure:

- Database credentials
- OpenAI API Key
- Google API Key (optional)
- WACP API credentials
- DEV-TOOLS Runtime URL

---

## Start AIHOME

Build and start all services:

```bash
docker compose up --build -d
```

Docker automatically starts:

- MariaDB
- AIHOME Backend
- AIHOME Frontend

---

## Verify Deployment

Check container status:

```bash
docker ps
```

Expected:

- ✅ MariaDB (healthy)
- ✅ AIHOME Backend (healthy)
- ✅ AIHOME Frontend (healthy)

---

## Application URLs

Frontend

```
http://localhost:4173
```

Backend API

```
http://localhost:8030
```

Swagger API Documentation

```
http://localhost:8030/docs
```

Health Check

```
http://localhost:8030/health
```

---

## Docker Commands

Start

```bash
docker compose up --build -d
```

Stop

```bash
docker compose down
```

Restart

```bash
docker compose down
docker compose up --build -d
```

View running containers

```bash
docker ps
```

View backend logs

```bash
docker logs aihome-backend
```

View frontend logs

```bash
docker logs aihome-frontend
```

View database logs

```bash
docker logs aihome-mariadb
```

---

## Persistent Storage

The Docker environment uses persistent storage to preserve application data.

### MariaDB Database

Database files are stored in a Docker volume and remain available after containers are recreated.

### Uploaded Images

Property images are stored in:

```
backend/uploads
```

Uploaded files remain available after rebuilding or restarting containers.

---

## Docker Architecture

```
                Docker Compose
                      │
      ┌───────────────┼───────────────┐
      │               │               │
      ▼               ▼               ▼
  MariaDB        AIHOME Backend   AIHOME Frontend
      │               │               │
      └───────────────┼───────────────┘
                      │
                WIMLOGIC Platform
                      │
              OpenAI • Gemini • Claude
```

---

## Health Monitoring

Docker automatically monitors all services.

Health checks are configured for:

- MariaDB
- AIHOME Backend
- AIHOME Frontend

Containers automatically report their runtime health status through Docker Compose.

---

# Screenshots

<img width="2041" height="1260" alt="AI-HOME STUDIO" src="https://github.com/user-attachments/assets/376bf55a-6beb-41f7-ab25-66a5385e99b9" />
<img width="2043" height="1261" alt="AI-HOME - ORCHASTRATION " src="https://github.com/user-attachments/assets/35f11f3a-55fe-4943-8147-232f386f74e4" />

---

# Roadmap

## Version 1.x

- ✅ Property Management
- ✅ AI Property Intelligence
- ✅ Workflow Integration
- ✅ WACP Integration

## Version 2.x

- 🚧 AI Design Studio
- 🚧 Image Enhancement
- 🚧 Design Concepts
- 🚧 Property Intelligence Expansion

---

# Relationship to WIMLOGIC

AIHOME is an open-source business application built on top of the **WIMLOGIC AI Orchestration Platform**.

The platform is responsible for:

- AI Workflow Execution
- AI Agent Orchestration
- Prompt Management
- AI Provider Integration
- Workflow Runtime
- Governance
- Result Aggregation

This separation allows multiple business applications to share the same AI infrastructure.

---

# Community Edition

AIHOME WIMLOGIC is released as an **Open Source Community Edition**.

Contributions, suggestions, and discussions are welcome.

---

# License

AIHOME WIMLOGIC Community Edition is licensed under the
[Apache License 2.0](LICENSE).

You may use, modify, and distribute this software, including for
commercial purposes, subject to the terms of the Apache License 2.0.

Copyright © 2026 WIMLOGIC.

---

# About WIMLOGIC

WIMLOGIC is a reusable AI orchestration platform designed to power multiple AI business solutions through workflows, AI agents, governance, and enterprise integrations.

Current ecosystem:

- 🏠 AIHOME WIMLOGIC
- 🛒 AI-ECOM WIMLOGIC
- ⚙️ DEV-TOOLS WIMLOGIC

---

© 2026 WIMLOGIC. All Rights Reserved.
