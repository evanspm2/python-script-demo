# Checker: Automating Network Circuit Migration Safety

**Checker** is a production-grade, modular Python utility designed to automate per-circuit prechecks and postchecks during network migrations. Whether migrating circuits between devices or shifting targeted subsets on a single node, Checker eliminates manual verification errors by running automated state telemetry captures and diff evaluations.

Launched seamlessly via **Jenkins**, the engine handles target node connections, populates a persistent state database, handles analytical diff logs, and delivers a complete verification summary right to the engineer's inbox.

---

## 🔗 Live Documentation & Presentation
The full production documentation, architectural flows, and user guides are hosted via GitHub Pages:
👉 **[View the Live Documentation Site](https://github.io)**

---

## 🛠️ System Design & Architecture

Checker is built using a clean, **modular, object-oriented design** pattern utilizing decoupled Python classes with tightly defined methods and attributes for network interaction, state processing, and data parsing.

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

### Core Pipeline Capabilities
* **State Persistence:** Integrates a localized **SQLite3** database layer to perfectly bridge metrics across execution windows (comparing precheck vs. postcheck runs).
* **Granular Diff Analysis:** Leverages advanced text analysis blocks to output a high-level summary table alongside interactive HTML files detailing precise command diffs.
* **Vendor & Service Agility:** The initial release targets **Juniper MX platforms** supporting **9 unique signature profiles** (BGP, VPLS, L2VPN, and single-router Local Hairpins) with abstract patterns ready for multi-vendor extension.

---

## 🧰 Integrated Core Libraries
* **Infrastructure Automation:** `netmiko`, `grpc`
* **Data Processing & Validation:** `sqlite3`, `difflib`, `ipaddress`
* **Reporting Utilities:** `smtplib`, `email`

---

## 🚀 Quick Start Summary

For deep setup instructions, configuration matrices, and database tables, please consult the [Full User Guide](https://github.iouser-guide).

1. **Pipeline Execution:** Trigger the workflow from Jenkins passing target node identifiers and the migration circuit scope array.
2. **Analysis Cycle:** The script executes device checks, maps interfaces, applies signature matching rules, and commits run metadata to SQLite3.
3. **Delivery:** The engineer receives an automated alert containing clear, green/red operational differentials within 60 seconds of execution.

---

## 📂 Project Repository Layout

* [`script.py`](./script.py) — Core application source code, modules, and classes.
* [`docs/`](./docs) — Markdown source documentation powered by Jekyll and the *Just the Docs* theme.
