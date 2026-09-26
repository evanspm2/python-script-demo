---
layout: default
title: User Guide
nav_order: 2
---

# User Guide

This section contains operational instructions for running the utility within a standard maintenance window change flow, alongside supported baseline profiles.

## 📈 Supported Services

### Internet Services

| Platform | Service | Handoff Type | Protocol | Interface Count |
| :--- | :--- | :--- | :--- | :--- |
| MX | BGP | Physical and Logical | BGP | 1 Interface |
| MX | BGP IRB | Physical and Logical | BGP, VPLS | 1 Interface |
| MX | Static | Physical and Logical | None | 1 Interface |

### Ethernet Services

| Platform | Service | Handoff Type | Protocol | Interface Count |
| :--- | :--- | :--- | :--- | :--- |
| MX | E-LINE Multi-Router | Physical and Logical | VPLS, L2VPN | 1 Interface |
| MX | E-LAN Multi-Router | Physical and Logical | VPLS | 1 Interface |
| MX | EVPL Multi-Router | Physical and Logical | VPLS, L2VPN | 1 Interface |

### Hairpin Services

| Platform | Service | Handoff Type | Protocol | Interface Count |
| :--- | :--- | :--- | :--- | :--- |
| MX | E-LINE Single-router | Physical and Logical | VPLS | 2 Interfaces |
| MX | E-LAN Single-Router | Physical and Logical | VPLS | 1 Interface |
| MX | EVPL Single-Router | Physical and Logical | VPLS | 1 Interface |

---

## 🔄 Maintenance Process Flow

1. **Test Run:** Perform a test run one week prior to the change management window to proactively identify circuits that fail interface mapping or signature matching logic.
2. **Pre-Maintenance:** Run a definitive precheck pass immediately prior to beginning maintenance window operations.
3. **Maintenance:** Execute physical migrations or configurations.
4. **Post-Maintenance:** Fire a final postcheck loop at the conclusion of migration work to evaluate diff matrices.

![](images/image10.png)

---

## ⚙️ Step-by-Step Execution

1. Access the web interface dashboard via the internal orchestrator links.
2. Provide the targeted **Circuit List**, toggle the appropriate **Run Mode** (Precheck / Postcheck), define the target **Network Node**, and execute the build pipeline.

![](images/image13.png)

3. Open and monitor the real-time execution logs via console standard output.

![](images/image15.png)

4. The system will cleanly wrap execution and deliver an aggregated analytical validation layout securely to your email within roughly 60 seconds.

![](images/image16.png)

---

## 🐛 Bug Scrubs & Tracking

| Date | Status | Bug ID | Description |
| :--- | :--- | :--- | :--- |
| 2/19/2025 | New | 100 | EVPL signature profile will not match EVPL circuit with a protect path |
| 2/19/2025 | New | 101 | EVPL signature profile will not match when EVPL node is local to head with remote nodes |
| 2/19/2025 | New | 102 | ELAN mapping fails if split using sub-interfaces across an aggregation stack interface |
| 2/19/2025 | New | 103 | ELINE hairpin output differential restricted to interface 1 data scopes |

## Feature Requests

| Date      | Status | Request ID | Description                                                                                                       |
| --------- | ------ | ---------- | ----------------------------------------------------------------------------------------------------------------- |
| 2/19/2025 | New    | 100        | Add support for IPB                                                                                               |
| 2/19/2025 | New    | 101        | Add support for aggregation trunk                                                                                 |
| 2/19/2025 | New    | 102        | Add support for CPE trunk                                                                                         |
| 2/19/2025 | New    | 103        | Add support for customer NNI                                                                                      |
| 2/19/2025 | New    | 104        | Add support for BGP IRB VPLS                                                                                      |
| 2/19/2025 | New    | 105        | Add support for OOB management circuit. Discovered Checker Review AP 02-14-2025 11-20-AM                          |
| 2/19/2025 | New    | 106        | Add support for in-band CPE management circuit testing. Discovered Checker Review AP 02-14-2025 11-20-AM          |
| 2/20/2025 | New    | 107        | Add support for Sidera circuits ex. 10/LCRM/000069/OED. Discovered Checker Review AP 02-14-2025 11-20-AM          |
| 2/20/2025 | New    | 108        | Add support for TMO high/low interfaces using same circuit name. Discovered Checker Review AP 02-14-2025 11-20-AM |
| 2/20/2025 | New    | 109        | Add support for Fibertech circuits ex. KRCEETHTP2NHV.00001. Discovered Checker Review AP 02-14-2025 11-20-AM      |

[def]: images/image10.png