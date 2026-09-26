---
layout: default
title: Development Guide
nav_order: 3
---

# Development Guide

This guide details data schemas, object tracking strategies, and core engine signature parsing details utilized during program operations.

## 🗄️ Database Schema & State Mapping

The system relies on an internal database to evaluate telemetry changes across temporal execution points.

### 1. Run Table
Tracks global pipeline properties, time contexts, metrics, and parameters passed during orchestrator execution phases.

| Table Column                 | Data Type               |
| ---------------------------- | ----------------------- |
| row_id                       | Primary Key             |
| user_run_mode                | String                  |
| user_email_address           | String                  |
| user_circuit_list            | JSON encoded list       |
| device_name                  | String                  |
| device_model                 | String                  |
| time                         | String                  |
| date                         | String                  |
| mx_interface_polls_precheck  | JSON encoded dictionary |
| mx_interface_polls_postcheck | JSON encoded dictionary |

### 2. Circuit Table
Maps distinct physical structures, operational states, signature classifications, and historical payload blocks matched to targeted nodes.

| Table Column                                  | Data Type               |
| --------------------------------------------- | ----------------------- |
| row_id                                        | Primary Key             |
| run_table_row_id_last_precheck                | Foreign key             |
| run_table_row_id_last_postcheck               | Foreign key             |
| circuit_name                                  | String                  |
| service_type_precheck                         | String                  |
| service_type_postcheck                        | String                  |
| device_name_precheck                          | String                  |
| device_name_postcheck                         | String                  |
| device_model_precheck                         | String                  |
| device_model_postcheck                        | String                  |
| mx_circuit_interfaces_precheck                | JSON encoded dictionary |
| mx_circuit_interfaces_postcheck               | JSON encoded dictionary |
| mx_bgp_neighbor_state_precheck                | String                  |
| mx_bgp_show_neighbor_state_precheck           | String                  |
| mx_bgp_neighbor_state_postcheck               | String                  |
| mx_bgp_show_neighbor_state_postcheck          | String                  |
| mx_bgp_irb_neighbor_state_precheck            | String                  |
| mx_bgp_irb_show_neighbor_state_precheck       | String                  |
| mx_bgp_irb_neighbor_state_postcheck           | String                  |
| mx_bgp_irb_show_neighbor_state_postcheck      | String                  |
| mx_static_arp_count_precheck                  | String                  |
| mx_static_show_arp_count_precheck             | String                  |
| mx_static_arp_count_postcheck                 | String                  |
| mx_static_show_arp_count_postcheck            | String                  |
| mx_vpls_number_remote_pe_up_precheck          | String                  |
| mx_vpls_show_number_remote_pe_up_precheck     | String                  |
| mx_vpls_number_remote_pe_up_postcheck         | String                  |
| mx_vpls_show_number_remote_pe_up_postcheck    | String                  |
| mx_vpls_mac_count_precheck                    | String                  |
| mx_vpls_show_mac_count_precheck               | String                  |
| mx_vpls_mac_count_postcheck                   | String                  |
| mx_vpls_show_mac_count_postcheck              | String                  |
| mx_l2vpn_number_remote_pe_up_precheck         | String                  |
| mx_l2vpn_show_number_remote_pe_up_precheck    | String                  |
| mx_l2vpn_number_remote_pe_up_postcheck        | String                  |
| mx_l2vpn_show_number_remote_pe_up_postcheck   | String                  |
| mx_hairpin_eline_mac_count_precheck           | String                  |
| mx_hairpin_eline_show_mac_count_precheck      | String                  |
| mx_hairpin_eline_mac_count_postcheck          | String                  |
| mx_hairpin_eline_show_mac_count_postcheck     | String                  |
| mx_hairpin_elan_evpl_mac_count_precheck       | String                  |
| mx_hairpin_elan_evpl_show_mac_count_precheck  | String                  |
| mx_hairpin_elan_evpl_mac_count_postcheck      | String                  |
| mx_hairpin_elan_evpl_show_mac_count_postcheck | String                  |

---

## 🔍 Signature Profiles & Match Logic

The application isolates network telemetry into **13 distinct structural signature rules** to evaluate state attributes safely.

| Profile Name                  | Search Order |
| ----------------------------- | ------------ |
| mx_vpls_logical               | 1            |
| mx_static_logical             | 2            |
| mx_bgp_logical                | 3            |
| mx_eline_hairpin              | 4            |
| mx_elan_evpl_hairpin_logical  | 5            |
| mx_l2vpn_logical              | 6            |
| mx_bgp_irb_vpls_logical       | 7            |
| mx_vpls_physical              | 8            |
| mx_static_physical            | 9            |
| mx_bgp_physical               | 10           |
| mx_elan_evpl_hairpin_physical | 11           |
| mx_l2vpn_physical             | 12           |
| mx_bgp_irb_vpls_physical      | 13           |

| Term                             | Search Order |
| -------------------------------- | ------------ |
| Circuit Name                     | 1            |
| Interface Name Period            | 2            |
| Physical Interface Tagging       | 3            |
| Physical Interface Encapsulation | 4            |
| Logical Unit 0 Family            | 5            |
| Logical Unit Encapsulation       | 6            |
| Routing Instance Type            | 7            |
| Routing Instance Protocol        | 8            |
| BGP Neighbor                     | 9            |
| Interface Count                  | 10           |
| Netcracker Circuit Type          | 11           |

### Core Profiles Matrix
* **Routing Assertions:** `BGP`, `BGP IRB`, and `Static` mapping modules.

| Profile         | Term                             | Input Value |     | Profile        | Term                             | Input Value                              |
| --------------- | -------------------------------- | ----------- | --- | -------------- | -------------------------------- | ---------------------------------------- |
| mx_bgp_physical | Circuit Name                     | internet    |     | mx_bgp_logical | Circuit Name                     | internet                                 |
| mx_bgp_physical | Interface Name Period            | period_no   |     | mx_bgp_logical | Interface Name Period            | period_yes                               |
| mx_bgp_physical | Physical Interface Tagging       | untagged    |     | mx_bgp_logical | Physical Interface Tagging       | tagged                                   |
| mx_bgp_physical | Physical Interface Encapsulation | none        |     | mx_bgp_logical | Physical Interface Encapsulation | \[flexible-ethernet-services,vlan-vpls\] |
| mx_bgp_physical | Logical Unit 0 Family            | inet        |     | mx_bgp_logical | Logical Unit 0 Family            | \__IQNORE__                              |
| mx_bgp_physical | Logical Unit x Encapsulation     | \__IQNORE__ |     | mx_bgp_logical | Logical Unit x Encapsulation     | none                                     |
| mx_bgp_physical | Routing Instance Type            | \__IQNORE__ |     | mx_bgp_logical | Routing Instance Type            | \__IQNORE__                              |
| mx_bgp_physical | Routing Instance Protocol        | \__IQNORE__ |     | mx_bgp_logical | Routing Instance Protocol        | \__IQNORE__                              |
| mx_bgp_physical | BGP Neighbor                     | check       |     | mx_bgp_logical | BGP Neighbor Check               | check                                    |
| mx_bgp_physical | Interface Count                  | 1           |     | mx_bgp_logical | Interface Count                  | 1                                        |
| mx_bgp_physical | Netcracker Circuit Type          | \__IQNORE__ |     | mx_bgp_logical | Netcracker Circuit Type          | \__IQNORE__                              |

| Profile                  | Term                             | Input Value   |     | Profile                 | Term                             | Input Value                              |
| ------------------------ | -------------------------------- | ------------- | --- | ----------------------- | -------------------------------- | ---------------------------------------- |
| mx_bgp_irb_vpls_physical | Circuit Name                     | internet      |     | mx_bgp_irb_vpls_logical | Circuit Name                     | internet                                 |
| mx_bgp_irb_vpls_physical | Physical Interface Tagging       | untagged      |     | mx_bgp_irb_vpls_logical | Physical Interface Tagging       | tagged                                   |
| mx_bgp_irb_vpls_physical | Physical Interface Encapsulation | ethernet-vpls |     | mx_bgp_irb_vpls_logical | Physical Interface Encapsulation | \[flexible-ethernet-services,vlan-vpls\] |
| mx_bgp_irb_vpls_physical | Logical Unit 0 Family            | vpls          |     | mx_bgp_irb_vpls_logical | Logical Unit 0 Family            | \__IQNORE__                              |
| mx_bgp_irb_vpls_physical | Logical Unit x Encapsulation     | \__IQNORE__   |     | mx_bgp_irb_vpls_logical | Logical Unit x Encapsulation     | vlan-vpls                                |
| mx_bgp_irb_vpls_physical | Routing Instance Type            | \__IQNORE__   |     | mx_bgp_irb_vpls_logical | Routing Instance Type            | \__IQNORE__                              |
| mx_bgp_irb_vpls_physical | Routing Instance Protocol        | \__IQNORE__   |     | mx_bgp_irb_vpls_logical | Routing Instance Protocol        | \__IQNORE__                              |
| mx_bgp_irb_vpls_physical | BGP Neighbor                     | \__IQNORE__   |     | mx_bgp_irb_vpls_logical | BGP Neighbor                     | \__IQNORE__                              |
| mx_bgp_irb_vpls_physical | Interface Count                  | 1             |     | mx_bgp_irb_vpls_logical | Interface Count                  | 1                                        |
| mx_bgp_irb_vpls_physical | Netcracker Circuit Type          | \__IQNORE__   |     | mx_bgp_irb_vpls_logical | Netcracker Circuit Type          | \__IQNORE__                  

| Profile            | Term                             | Input Value |     | Profile           | Term                             | Input Value                    |
| ------------------ | -------------------------------- | ----------- | --- | ----------------- | -------------------------------- | ------------------------------ |
| mx_static_physical | Circuit Name                     | internet    |     | mx_static_logical | Circuit Name                     | internet                       |
| mx_static_physical | Physical Interface Tagging       | untagged    |     | mx_static_logical | Physical Interface Tagging       | tagged                         |
| mx_static_physical | Physical Interface Encapsulation | none        |     | mx_static_logical | Physical Interface Encapsulation | \[flexible-ethernet-services\] |
| mx_static_physical | Logical Unit 0 Family            | inet        |     | mx_static_logical | Logical Unit 0 Family            | \__IQNORE__                    |
| mx_static_physical | Logical Unit x Encapsulation     | \__IQNORE__ |     | mx_static_logical | Logical Unit x Encapsulation     | none                           |
| mx_static_physical | Routing Instance Type            | \__IQNORE__ |     | mx_static_logical | Routing Instance Type            | \__IQNORE__                    |
| mx_static_physical | Routing Instance Protocol        | \__IQNORE__ |     | mx_static_logical | Routing Instance Protocol        | \__IQNORE__                    |
| mx_static_physical | BGP Neighbor                     | \__IQNORE__ |     | mx_static_logical | BGP Neighbor                     | \__IQNORE__                    |
| mx_static_physical | Interface Count                  | 1           |     | mx_static_logical | Interface Count                  | 1                              |
| mx_static_physical | Netcracker Circuit Type          | \__IQNORE__ |     | mx_static_logical | Netcracker Circuit Type          | \__IQNORE__                    |

* **Multi-Node Foundations:** Modern multi-router edge layers covering standard `VPLS` and `L2VPN` topologies.

| Profile          | Term                             | Input Value   |     | Profile         | Term                             | Input Value                              |
| ---------------- | -------------------------------- | ------------- | --- | --------------- | -------------------------------- | ---------------------------------------- |
| mx_vpls_physical | Circuit Name                     | ethernet      |     | mx_vpls_logical | Circuit Name                     | ethernet                                 |
| mx_vpls_physical | Interface Name Period            | period_no     |     | mx_vpls_logical | Interface Name Period            | period_yes                               |
| mx_vpls_physical | Physical Interface Tagging       | untagged      |     | mx_vpls_logical | Physical Interface Tagging       | tagged                                   |
| mx_vpls_physical | Physical Interface Encapsulation | ethernet-vpls |     | mx_vpls_logical | Physical Interface Encapsulation | \[flexible-ethernet-services,vlan-vpls\] |
| mx_vpls_physical | Logical Unit 0 Family            | vpls          |     | mx_vpls_logical | Logical Unit 0 Family            | \__IQNORE__                              |
| mx_vpls_physical | Logical Unit x Encapsulation     | \__IQNORE__   |     | mx_vpls_logical | Logical Unit x Encapsulation     | vlan-vpls                                |
| mx_vpls_physical | Routing Instance Type            | vpls          |     | mx_vpls_logical | Routing Instance Type            | vpls                                     |
| mx_vpls_physical | Routing Instance Protocol        | vpls          |     | mx_vpls_logical | Routing Instance Protocol        | vpls                                     |
| mx_vpls_physical | BGP Neighbor                     | \__IQNORE__   |     | mx_vpls_logical | BGP Neighbor                     | \__IQNORE__                              |
| mx_vpls_physical | Interface Count                  | 1             |     | mx_vpls_logical | Interface Count                  | 1                                        |
| mx_vpls_physical | Netcracker Circuit Type          | \__IQNORE__   |     | mx_vpls_logical | Netcracker Circuit Type          | \__IQNORE__                              |

| Profile           | Term                             | Input Value  |     | Profile          | Term                             | Input Value                             |
| ----------------- | -------------------------------- | ------------ | --- | ---------------- | -------------------------------- | --------------------------------------- |
| mx_l2vpn_physical | Circuit Name                     | ethernet     |     | mx_l2vpn_logical | Circuit Name                     | ethernet                                |
| mx_l2vpn_physical | Physical Interface Tagging       | untagged     |     | mx_l2vpn_logical | Physical Interface Tagging       | tagged                                  |
| mx_l2vpn_physical | Physical Interface Encapsulation | ethernet-ccc |     | mx_l2vpn_logical | Physical Interface Encapsulation | \[flexible-ethernet-services,vlan-ccc\] |
| mx_l2vpn_physical | Logical Unit 0 Family            | ccc          |     | mx_l2vpn_logical | Logical Unit 0 Family            | \__IQNORE__                             |
| mx_l2vpn_physical | Logical Unit x Encapsulation     | \__IQNORE__  |     | mx_l2vpn_logical | Logical Unit x Encapsulation     | vlan-ccc                                |
| mx_l2vpn_physical | Routing Instance Type            | l2vpn        |     | mx_l2vpn_logical | Routing Instance Type            | l2vpn                                   |
| mx_l2vpn_physical | Routing Instance Protocol        | l2vpn        |     | mx_l2vpn_logical | Routing Instance Protocol        | l2vpn                                   |
| mx_l2vpn_physical | BGP Neighbor                     | \__IQNORE__  |     | mx_l2vpn_logical | BGP Neighbor                     | \__IQNORE__                             |
| mx_l2vpn_physical | Interface Count                  | 1            |     | mx_l2vpn_logical | Interface Count                  | 1                                       |
| mx_l2vpn_physical | Netcracker Circuit Type          | \__IQNORE__  |     | mx_l2vpn_logical | Netcracker Circuit Type          | \__IQNORE__     

* **Single-Router Local Hairpins:** High-performance specialized check profiles managing local `ELINE Hairpins` and `ELAN/EVPL Hairpins`.

| Profile                       | Term                             | Input Value   |     | Profile                      | Term                             | Input Value                              |
| ----------------------------- | -------------------------------- | ------------- | --- | ---------------------------- | -------------------------------- | ---------------------------------------- |
| mx_elan_evpl_hairpin_physical | Circuit Name                     | ethernet      |     | mx_elan_evpl_hairpin_logical | Circuit Name                     | ethernet                                 |
| mx_elan_evpl_hairpin_physical | Physical Interface Tagging       | untagged      |     | mx_elan_evpl_hairpin_logical | Physical Interface Tagging       | tagged                                   |
| mx_elan_evpl_hairpin_physical | Physical Interface Encapsulation | ethernet-vpls |     | mx_elan_evpl_hairpin_logical | Physical Interface Encapsulation | \[flexible-ethernet-services,vlan-vpls\] |
| mx_elan_evpl_hairpin_physical | Logical Unit 0 Family            | vpls          |     | mx_elan_evpl_hairpin_logical | Logical Unit 0 Family            | \__IQNORE__                              |
| mx_elan_evpl_hairpin_physical | Logical Unit x Encapsulation     | \__IQNORE__   |     | mx_elan_evpl_hairpin_logical | Logical Unit x Encapsulation     | vlan-vpls                                |
| mx_elan_evpl_hairpin_physical | Routing Instance Type            | vpls          |     | mx_elan_evpl_hairpin_logical | Routing Instance Type            | vpls                                     |
| mx_elan_evpl_hairpin_physical | Routing Instance Protocol        | none          |     | mx_elan_evpl_hairpin_logical | Routing Instance Protocol        | none                                     |
| mx_elan_evpl_hairpin_physical | BGP Neighbor                     | \__IQNORE__   |     | mx_elan_evpl_hairpin_logical | BGP Neighbor                     | \__IQNORE__                              |
| mx_elan_evpl_hairpin_physical | Interface Count                  | 1             |     | mx_elan_evpl_hairpin_logical | Interface Count                  | 1                                        |
| mx_elan_evpl_hairpin_physical | Netcracker Circuit Type          | elan, evpl    |     | mx_elan_evpl_hairpin_logical | Netcracker Circuit Type          | elan, evpl                               |

| Profile          | Term                             | Input Value   |
| ---------------- | -------------------------------- | ------------- |
| mx_eline_hairpin | Circuit Name                     | ethernet      |
| mx_eline_hairpin | Physical Interface Tagging       | untagged      |
| mx_eline_hairpin | Physical Interface Encapsulation | ethernet-vpls |
| mx_eline_hairpin | Logical Unit 0 Family            | vpls          |
| mx_eline_hairpin | Logical Unit x Encapsulation     | \__IQNORE__   |
| mx_eline_hairpin | Routing Instance Type            | none          |
| mx_eline_hairpin | Routing Instance Protocol        | none          |
| mx_eline_hairpin | BGP Neighbor                     | \__IQNORE__   |
| mx_eline_hairpin | Interface Count                  | 2             |
| mx_eline_hairpin | Netcracker Circuit Type          | \[eline\]     |

### Interface & Matcher Ingestion Logic
The module captures raw runtime arrays, parses target attributes dynamically using internal regular matching classes, and routes data frames into their respective profile engine routines for differential text rendering.

![](images/image9.png)

### Modular, object-oriented system design

![](images/image17.png)