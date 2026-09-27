---
layout: default
title: Overview
nav_order: 1
permalink: /
---


# Peter Evans
**[Git Hub](https://github.com/evanspm2)** | **[Linked In](https://www.linkedin.com/in/evanspm/)** | 

<br>
<br>
<br>

<img src="images/flag.webp" alt="Description" width="300">

💻 **[Raw Python Script](https://github.com/evanspm2/python-script-demo/blob/main/script.py)**

# Project Overview: Checker

**Checker** is a robust, production-grade network automation utility built in Python to perform **per-circuit prechecks and postchecks**. It streamlines the process of migrating circuits between network devices or migrating targeted subsets of circuits on a single platform, replacing manual state verification with a highly reliable, automated pipeline.

Designed for seamless enterprise integration, **Checker is launched via Jenkins** with minimal parameters. The engine logs directly into targeted infrastructure, collects state telemetry, updates a persistent database, and automatically distributes a comprehensive verification report to engineers. 

The initial release natively supports **Juniper MX series routers**, providing **13 distinct signature profiles** that cover a broad spectrum of production circuit types. The application is architected with scalability in mind, featuring abstract foundations ready to support future hardware vendors and circuit profiles.

---

## 🚀 Key Features

* **Multi-Stage Telemetry Diff Analysis:** Captures live execution states during both pre-migration and post-migration windows, running deep analytical evaluations to ensure zero network degradation.
* **Automated Reporting Suite:** Dispatches an automated email report containing a high-level summary table, granular per-circuit diff analyses, and an interactive HTML attachment showing raw `show command` differentials.
* **State Persistence:** Utilizes a lightweight, embedded **SQLite3** database engine to reliably preserve circuit telemetry across disconnected execution windows (precheck vs. postcheck runs).
* **Enterprise CI/CD Alignment:** Built to work as a programmatic step inside automated pipelines—version-controlled natively and triggered as a downstream task within modern orchestrators.

---

## 🛠️ Architecture & Core Logic

Checker is engineered around a clean, **modular, object-oriented system design**. The codebase leverages decoupled classes with clearly defined attributes and methods to handle device connectivity, state modeling, and data formatting independently.

```text
 [Jenkins Trigger] ──> [Checker Engine (Python)] ──> [Netmiko / gRPC] ──> [Juniper MX]
                              │                                              │
                              ├──> [SQLite3 State DB]                        ▼
                              │                                       [State Captures]
                              ▼                                              │
                       [Difflib Engine] <────────────────────────────────────┘
                              │
                              └──> [smtplib / email] ──> [HTML & Summary Report]
```

### Integrated Automation Engine & Core Libraries
The application relies on a robust mixture of standard and specialized Python libraries to communicate with and evaluate infrastructure safely:
* **Network Infrastructure & Telemetry:** `netmiko` for secure terminal automation, alongside `grpc` hooks for high-performance operational state gathering.
* **State Analysis & Validation:** `difflib` for text-based operational diffs, and `ipaddress` for strict structural validation of network boundaries.
* **Persistence & APIs:** `sqlite3` to coordinate data layers between runs, and `requests` for external orchestration hooks.
* **Communication Suite:** `smtplib` and `email` modules configured to build and securely route rich HTML reporting blocks.
* **System Utilities:** `datetime`, `os`, and `time` for granular execution logging and environment configuration tracking.