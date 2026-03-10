# PROJECT_MASTER_SPEC
## Smart Home / Smart Building Platform
### Repository-Aligned Master Specification

## 1. Purpose

This repository defines a modular smart-home and smart-building platform for prototype development, staged deployment, and future commercial productization.

The platform is intended to support:

- DIY and prototype devices such as ESP32, STM32, RP2040, Linux edge devices, and similar hardware
- future commercial and industrial hardware
- local-first automation
- optional cloud extensions
- multi-protocol communication
- installer workflows
- project generation from building design
- device simulation during development
- long-term extensibility toward a complete smart-building operating system

This file is the primary architectural reference for the repository and should be treated as the main source of truth for future development.

---

## 2. Current Repository Alignment

The current repository already contains major structural components aligned with the intended architecture.

Existing or scaffolded areas include:

- cloud services
- edge controller
- device registry
- automation engine
- telemetry service
- project engine
- system generator
- protocol bridges
- installer platform
- monitoring
- device SDK
- examples and simulator-related structure
- capability schema and documentation
- Copilot development orchestrator
- CI / validation structure

This means the project is already beyond a blank starter and should now be developed by strengthening specifications, implementing the first complete control loop, and refining service boundaries.

---

## 3. Core Design Principles

### 3.1 Local-First Architecture

The system must function fully locally without internet access.

Local deployment is a first-class operating mode, not a fallback.

Local services may include:

- local MQTT broker
- local automation engine
- local device registry
- local dashboards
- local telemetry storage
- local protocol bridges
- local provisioning tools

The system must continue to function when cloud services are unavailable.

---

### 3.2 Cloud-Optional Architecture

Cloud services are optional extensions.

Cloud may provide:

- remote access
- cross-site management
- aggregated telemetry
- AI services
- firmware distribution
- backups
- installer account management
- notification services

No critical building function should require cloud connectivity unless explicitly configured for that deployment.

---

### 3.3 Protocol Abstraction

The system must not be tied to one hardware vendor, board family, or field protocol.

Supported protocols may include:

- MQTT
- CAN
- CANopen
- RS485
- Modbus RTU
- Modbus TCP
- Ethernet
- WiFi
- Bluetooth
- Zigbee
- Thread
- Matter
- KNX
- BACnet
- HTTP REST
- WebSocket

All protocol-specific implementations must be translated into the internal platform model based on events, MQTT, and device capabilities.

---

### 3.4 Event-Driven Architecture

The platform is event-driven.

Core flow:

device event  
→ protocol bridge or native MQTT publish  
→ MQTT event routing  
→ automation engine  
→ resulting command or state change  
→ device update  

Example:

motion detected  
→ automation rule triggered  
→ light control command published  
→ light state changes  

This architecture allows loose coupling, scalability, simulation, and protocol independence.

---

### 3.5 Capability-Based Device Model

The system must not hardcode behavior by vendor or board type when the same function can be represented by capabilities.

Devices must be described abstractly by:

- identity
- type
- protocol
- capabilities
- inputs
- outputs
- sensors
- metadata
- state

This allows the same automation logic to work across:

- ESP32 relay node
- Modbus relay module
- KNX relay actuator
- future commercial relay products

---

## 4. High-Level Architecture

The platform consists of these main layers:

Applications  
Cloud Platform  
Edge Controller  
Messaging Layer  
Protocol Translation Layer  
Device Layer  

### 4.1 Device Layer

This layer includes real and simulated devices.

Examples:

- ESP32 nodes
- STM32 nodes
- RP2040 nodes
- Linux-based nodes
- industrial controllers
- relay modules
- dimmers
- thermostats
- environmental sensors
- cameras
- AI edge modules
- protocol-connected third-party devices

Devices may communicate over:

- CAN
- RS485
- Ethernet
- WiFi
- Bluetooth
- Zigbee
- Thread
- MQTT-native IP

---

### 4.2 Protocol Translation Layer

This layer converts field-specific or vendor-specific messages into the platform’s internal model.

Expected bridge types include:

- Modbus bridge
- KNX bridge
- BACnet bridge
- CAN bridge
- future Zigbee / Matter bridge
- future proprietary hardware bridge

Bridge outputs must be normalized into MQTT events and capability-aware payloads.

---

### 4.3 Messaging Layer

MQTT is the primary internal messaging backbone.

MQTT connects:

- devices
- simulators
- protocol bridges
- device registry
- automation engine
- telemetry service
- dashboards
- cloud bridge
- installer tools
- AI services

MQTT is the default event bus for device-oriented communication.

---

### 4.4 Edge Controller Layer

Each building installation should include an edge controller.

Responsibilities:

- host or connect to local MQTT broker
- manage local device registry
- execute local automation
- expose local APIs if needed
- bridge local protocols
- support provisioning workflows
- store local state and telemetry
- continue functioning independently of cloud

Possible hardware:

- mini PC
- industrial PC
- Raspberry Pi
- VM on local server
- future dedicated controller hardware

---

### 4.5 Cloud Platform Layer

Cloud services are optional but supported.

Possible functions:

- remote access
- project synchronization
- aggregated telemetry
- multi-site fleet management
- centralized notifications
- AI analysis
- firmware distribution
- account and role management

Cloud must never break local building operation if unavailable.

---

## 5. MQTT Protocol Standard

### 5.1 Standard Topic Layout

All platform services and devices should align with a consistent topic structure.

Base topics:

platform/{house}/{device}/status  
platform/{house}/{device}/telemetry  
platform/{house}/{device}/control  
platform/{house}/{device}/event  
platform/{house}/{device}/config  

Optional topics:

platform/{house}/{device}/log  
platform/{house}/{device}/debug  
platform/{house}/{device}/ota  
platform/discovery  

Example:

platform/home01/device123/telemetry

Example payload:

{
  "temperature": 22.4,
  "humidity": 45
}

---

### 5.2 QoS Strategy

Recommended defaults:

- QoS 0 for frequent telemetry
- QoS 1 for commands and configuration
- QoS 2 for critical events when guaranteed delivery is required

---

### 5.3 Discovery

Devices should announce themselves through discovery.

Discovery topic:

platform/discovery

Example discovery payload:

{
  "device_id": "device123",
  "device_type": "relay_module",
  "protocol": "mqtt",
  "firmware_version": "1.0.0",
  "capabilities": ["relay_output", "power_monitor"]
}

---

### 5.4 Command Model

Commands should be explicit and capability-aware.

Example control payload:

{
  "relay1": true
}

Example event payload:

{
  "event": "motion_detected",
  "value": true
}

---

### 5.5 State Publication

Devices should publish state updates so dashboards and automation logic remain synchronized.

Examples:

- relay state
- sensor values
- online status
- firmware version
- diagnostic status

---

## 6. Universal Device Capability Schema

All devices must declare capabilities.

### 6.1 Capability Categories

#### Outputs

- relay_output
- pwm_output
- analog_output
- dimmer_output
- scene_output

#### Inputs

- digital_input
- analog_input
- pulse_input
- encoder_input
- button_input

#### Sensors

- temperature
- humidity
- motion
- presence
- light_level
- co2
- gas
- smoke
- water_leak
- pressure
- vibration

#### Media

- video_stream
- audio_stream
- image_capture

#### Energy

- power_monitor
- energy_meter
- voltage_monitor
- current_monitor

#### HVAC / Environmental Control

- thermostat_control
- fan_control
- heating_control
- ventilation_control

#### Security

- door_contact
- lock_control
- alarm_output
- glass_break_detection

#### AI / Advanced

- ai_detection
- occupancy_estimation
- object_detection
- face_recognition
- plate_recognition

---

### 6.2 Example Device Profiles

Relay module:

device_type: relay_module

capabilities:
- relay_output
- power_monitor

Environment sensor:

device_type: environment_sensor

capabilities:
- temperature
- humidity
- co2

Camera node:

device_type: camera_node

capabilities:
- video_stream
- motion
- ai_detection

---

## 7. Supported Device Universe

The platform should support, immediately or over time, the following device groups.

### 7.1 Infrastructure

- central controller
- edge controller
- cloud bridge
- MQTT bridge
- fieldbus gateway
- protocol gateway

### 7.2 Lighting

- relay light controller
- dimmer module
- PWM LED driver
- RGB controller
- RGBW controller
- 0-10V dimmer
- DMX controller

### 7.3 User Interfaces

- wall switch
- touch panel
- smart button
- scene keypad
- rotary dimmer
- mobile UI
- voice bridge

### 7.4 Environmental Sensors

- temperature sensor
- humidity sensor
- CO2 sensor
- air quality sensor
- light sensor
- weather station

### 7.5 Motion and Presence

- PIR sensor
- motion sensor
- presence sensor
- mmWave occupancy sensor

### 7.6 Security

- door sensor
- window sensor
- smart lock
- alarm siren
- panic button
- glass break sensor

### 7.7 Cameras and AI

- IP camera
- AI camera
- face recognition node
- package detection camera
- license plate camera

### 7.8 Energy

- power meter
- solar inverter monitor
- battery monitor
- EV charger interface
- energy optimization module

### 7.9 HVAC

- thermostat
- floor heating controller
- heat pump bridge
- fan controller
- ventilation controller

### 7.10 Garage and Outdoor

- garage controller
- gate motor controller
- irrigation controller
- outdoor lighting controller
- pool controller

### 7.11 Industrial and IO

- analog input module
- analog output module
- digital input module
- digital output module
- 4-20mA interface
- pulse counter
- encoder interface

---

## 8. Local vs Cloud Operating Modes

The platform must support three operating modes.

### 8.1 Local Mode

Everything runs locally.

Includes:

- automation
- devices
- dashboards
- telemetry
- provisioning
- protocol bridges

No cloud dependency.

---

### 8.2 Hybrid Mode

Core control remains local while cloud adds optional features.

Cloud may provide:

- remote access
- analytics
- backups
- notifications
- firmware distribution

This is expected to be the most common real deployment mode.

---

### 8.3 Cloud Mode

Used for centralized fleet-style management, special enterprise cases, or highly managed installations.

Even in this mode, local safety-critical behavior should be preserved where possible.

---

## 9. Security Architecture

### 9.1 Device Security

Devices should support:

- unique device IDs
- secure identity
- certificate-based authentication where practical
- signed firmware
- secure boot where supported
- OTA package validation

---

### 9.2 Network Security

The system should support:

- TLS for MQTT and HTTP
- VPN or secure tunneling for remote access
- firewall isolation
- network segmentation where needed

---

### 9.3 Access Control

The platform should support role-based access.

Typical roles:

- customer
- installer
- administrator
- service technician
- developer
- cloud operator

---

### 9.4 Auditability

The system should record important administrative and operational actions for diagnostics and support.

Examples:

- device provisioning
- user role changes
- firmware deployment
- installer actions
- security-relevant login events

---

## 10. Firmware Reference Architecture

A reference embedded firmware architecture must exist for real device development, not just simulators.

Recommended structure:

bootloader  
security_layer  
network_manager  
mqtt_client  
device_identity  
capability_handler  
io_manager  
sensor_manager  
automation_client  
ota_updater  
diagnostics  
local_config_storage  

### 10.1 Boot Workflow

boot  
→ initialize hardware  
→ load stored configuration  
→ connect network  
→ publish discovery  
→ register with server  
→ receive configuration  
→ start runtime tasks  

### 10.2 Firmware Targets

Supported now or later:

- ESP32
- STM32
- RP2040
- Linux device agents
- future dedicated hardware

### 10.3 Firmware Goals

Firmware should support:

- consistent discovery
- configuration application
- telemetry publication
- command handling
- safe state reporting
- OTA readiness
- local fallback behavior where applicable

---

## 11. Device SDK

A shared SDK should exist for implementing new devices consistently.

SDK modules should include:

- MQTT client wrapper
- topic builder
- discovery support
- configuration manager
- capability declaration
- OTA hooks
- diagnostics hooks
- state publication helpers

The SDK should help both simulated and real hardware implementations follow the same platform rules.

---

## 12. House Designer and Customer Project System

The customer-facing platform should eventually support visual smart-system planning.

Expected area:

web/house_designer/

Features:

- room layout design
- floor structure
- device placement
- automation preferences
- equipment overview
- project summary
- bill of materials generation
- optional pricing and order preparation

Suggested stack:

- React
- Three.js
- floorplanner libraries

This is a future-facing commercial product feature and not required to complete the first technical prototype.

---

## 13. Project Engine and System Generator

The project engine and system generator should convert project intent into deployable system definitions.

Generated outputs may include:

- device topology
- automation rules
- network layout
- installation plan
- bill of materials
- provisioning plan
- optional ordering list

This layer bridges customer design, installer workflow, and actual system deployment.

---

## 14. Installer Platform

The repository already includes installer-related structure and this should remain a first-class subsystem.

Installer features should include:

- open project
- scan devices
- assign device to room
- apply provisioning
- run diagnostics
- test relays and outputs
- validate sensors
- finalize installation
- maintenance mode

Provisioning flow:

device boot  
→ installer scans QR code or ID  
→ assign room / role  
→ configuration applied  
→ test executed  
→ installation finalized  

---

## 15. Telemetry and Historical Storage

The platform must support historical telemetry.

Examples:

- temperature history
- humidity history
- energy consumption
- device uptime
- automation activity
- network health

Possible storage technologies:

- TimescaleDB
- InfluxDB
- ClickHouse

Local retention should be supported. Cloud sync is optional.

---

## 16. Observability and Monitoring

The repository already includes monitoring structure and this should be treated as required infrastructure, not an afterthought.

Recommended monitoring stack:

- Prometheus
- Grafana
- OpenTelemetry
- Loki or similar log system

Important metrics:

- device uptime
- MQTT throughput
- registry health
- automation execution count
- service health
- bridge status
- telemetry ingestion health
- edge controller performance

---

## 17. Device Simulation Environment

A simulator is essential for rapid development and is already aligned with the current repository direction.

Expected location:

examples/devices/  
and/or  
tools/device_simulator/

Simulated devices may include:

- relay node
- temperature sensor
- motion sensor
- thermostat
- power meter

Simulated devices must behave like real platform devices:

- publish discovery
- publish telemetry
- receive control
- publish status

---

## 18. First Functional Prototype Goal

The first complete prototype milestone should be this loop:

simulated or real device  
→ MQTT publish  
→ device registry update  
→ automation engine evaluates rule  
→ control message published  
→ simulated or real device action  
→ state published back  

Once this works, the platform has a true end-to-end operational core.

This should be treated as the most important near-term milestone.

---

## 19. Suggested Development Priorities

Recommended near-term order:

1. verify MQTT backbone behavior
2. verify device discovery and registry update
3. verify automation rule execution
4. verify simulator-to-control loop
5. verify persistent telemetry path
6. strengthen firmware reference template
7. strengthen installer provisioning path
8. refine project/system generation
9. add cloud bridge functionality
10. expand protocol bridges

---

## 20. Repository Structure Guidance

The current repository already contains substantial structure. Future work should preserve clear separation of concerns.

Representative structure:

cloud_services/  
installer_platform/  
monitoring/  
services/  
schemas/  
examples/  
docs/  

Service areas are expected to include:

- device_registry
- automation_engine
- telemetry
- project_engine
- system_generator
- edge_controller
- protocol bridges
- AI-related services
- MQTT-related helpers or services

The structure should remain modular and avoid turning into a monolith.

---

## 21. Copilot Guidance

Copilot should treat this document as the primary architecture reference.

Rules for Copilot:

1. Follow this file as the main system specification.
2. Prefer modular service design.
3. Do not hardcode device behavior when capability abstraction can be used.
4. Use MQTT as the central event bus for device-related communication.
5. Keep local operation functional without cloud.
6. Treat protocol bridges as normalization layers into the internal MQTT/capability model.
7. Prefer configuration-driven design over board-specific assumptions.
8. Preserve compatibility between simulator devices and future real hardware.

---

## 22. Alignment With Current Copilot Scaffold

The current Copilot-generated repository is already substantially aligned with the intended architecture.

Clearly aligned areas include:

- MQTT-centered design
- device registry
- automation engine
- protocol bridges
- edge controller
- cloud services
- device SDK direction
- monitoring / observability
- installer platform presence
- schema-driven device capability work
- simulator / example direction
- orchestrated development workflow

The biggest remaining need is not large structural change, but a clear and stable master reference document so further development stays aligned.

This file fulfills that role.

---

## 23. Long-Term Goal

The long-term goal is to create a universal smart-building platform capable of controlling and coordinating:

- lighting
- climate
- energy
- security
- automation
- cameras and AI services
- commercial building devices
- industrial-connected systems

The system should scale from:

single home  
→ apartment building  
→ commercial building  
→ industrial site  

---

## 24. Instruction to Future Contributors

When contributing to this repository:

- follow PROJECT_MASTER_SPEC.md
- preserve local-first design
- use capability abstraction
- maintain MQTT-centered event flow
- avoid unnecessary coupling between services
- keep simulators and real devices aligned
- design for future hardware replacement without rewriting the platform