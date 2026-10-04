# Body Control Module High-Level Design

Document ID: HLD-BCM-0042
Revision: Rev A
Classification: Internal
Status: Approved for development

## 1 Introduction

This High-Level Design describes the AUTOSAR Classic Platform architecture of the Body
Control Module (BCM) for the X200 vehicle programme. It covers software components,
ports, interfaces, signals and the integration into the basic software stack.

### 1.1 Scope

The document covers the application layer software components, the runtime environment
configuration and the relevant basic software modules. Hardware design is out of scope.

### 1.2 Abbreviations

SWC software component, RTE runtime environment, BSW basic software, DE data element,
PDU protocol data unit, DID data identifier.

## 2 Architecture Overview

The BCM application layer consists of five software components running on a single core.
All inter-component communication uses the RTE. External communication uses CAN FD
through the Com module.

## 3 Software Components

### 3.1 SWC_DoorControl

SWC_DoorControl manages central locking, individual door actuation and the child lock.
It owns the lock state machine for all four doors.

PPort DoorStatus provides the interface IF_DoorStatus of kind SenderReceiver.
RPort LockCommand requires the interface IF_LockCommand of kind ClientServer.
Runnable Re_DoorControl_Main executes every 10 ms.
Runnable Re_DoorControl_Init executes at startup.

SWC_DoorControl sends Sig_DoorLockState to SWC_Gateway.
SWC_DoorControl requires Sig_VehicleSpeed from SWC_SpeedMonitor.

### 3.2 SWC_LightControl

SWC_LightControl manages exterior lighting including indicators, hazard lights and the
welcome lighting sequence.

PPort LightStatus provides the interface IF_LightStatus of kind SenderReceiver.
RPort IgnitionState requires the interface IF_IgnitionState of kind SenderReceiver.
Runnable Re_LightControl_Main executes every 20 ms.

SWC_LightControl receives Sig_IgnitionStatus from SWC_PowerMode.
SWC_LightControl sends Sig_IndicatorRequest to SWC_Gateway.

### 3.3 SWC_WindowControl

SWC_WindowControl manages the four power windows including the anti-pinch function.

PPort WindowPosition provides the interface IF_WindowPosition of kind SenderReceiver.
RPort MotorCurrent requires the interface IF_MotorCurrent of kind SenderReceiver.
Runnable Re_WindowControl_Main executes every 5 ms.

SWC_WindowControl requires Sig_VehicleSpeed from SWC_SpeedMonitor.
SWC_WindowControl sends Sig_WindowPosition to SWC_Gateway.

### 3.4 SWC_Gateway

SWC_Gateway routes application signals to and from the vehicle network and performs
signal gateway functions between CAN FD and LIN.

PPort NetworkTx provides the interface IF_NetworkTx of kind SenderReceiver.
RPort NetworkRx requires the interface IF_NetworkRx of kind SenderReceiver.
Runnable Re_Gateway_Main executes every 10 ms.

SWC_Gateway sends BcmStatus_PDU to Com.
SWC_Gateway receives VehicleState_PDU from Com.

### 3.5 SWC_PowerMode

SWC_PowerMode derives the ECU power mode from the ignition line and the network
management state.

PPort PowerModeStatus provides the interface IF_PowerModeStatus of kind ModeSwitch.
Runnable Re_PowerMode_Main executes every 50 ms.

SWC_PowerMode provides Sig_IgnitionStatus to SWC_LightControl.
SWC_PowerMode calls EcuM for the shutdown request.

### 3.6 SWC_SpeedMonitor

SWC_SpeedMonitor receives the wheel speed information and publishes the vehicle speed.

PPort VehicleSpeed provides the interface IF_VehicleSpeed of kind SenderReceiver.
Runnable Re_SpeedMonitor_Main executes every 10 ms.

SWC_SpeedMonitor publishes Sig_VehicleSpeed to SWC_DoorControl.

### 3.7 SWC_DiagnosticHandler

SWC_DiagnosticHandler implements the application part of the diagnostic services and
the fault memory interface.

PPort DiagnosticData provides the interface IF_DiagnosticData of kind ClientServer.
Runnable Re_DiagnosticHandler_Main executes every 100 ms.

SWC_DiagnosticHandler calls Dem for event reporting.
SWC_DiagnosticHandler requires Sig_DoorLockState from SWC_DoorControl.

## 4 Interface Catalogue

| Interface | Kind | Provider | Consumer | Data Element |
| --- | --- | --- | --- | --- |
| IF_DoorStatus | SenderReceiver | SWC_DoorControl | SWC_Gateway | DE_DoorLockState |
| IF_LockCommand | ClientServer | SWC_Gateway | SWC_DoorControl | DE_LockRequest |
| IF_LightStatus | SenderReceiver | SWC_LightControl | SWC_Gateway | DE_LightState |
| IF_IgnitionState | SenderReceiver | SWC_PowerMode | SWC_LightControl | DE_IgnitionState |
| IF_WindowPosition | SenderReceiver | SWC_WindowControl | SWC_Gateway | DE_WindowPosition |
| IF_MotorCurrent | SenderReceiver | SWC_WindowControl | SWC_WindowControl | DE_MotorCurrent |
| IF_VehicleSpeed | SenderReceiver | SWC_SpeedMonitor | SWC_DoorControl | DE_VehicleSpeed |
| IF_NetworkTx | SenderReceiver | SWC_Gateway | Com | DE_NetworkFrame |
| IF_PowerModeStatus | ModeSwitch | SWC_PowerMode | BswM | DE_PowerMode |
| IF_DiagnosticData | ClientServer | SWC_DiagnosticHandler | Dcm | DE_DiagnosticRecord |

## 5 Signal Catalogue

| Signal | CAN ID | Length | Cycle | Producer | Consumer |
| --- | --- | --- | --- | --- | --- |
| Sig_DoorLockState | 0x120 | 1 byte | 100 ms | SWC_DoorControl | SWC_Gateway |
| Sig_VehicleSpeed | 0x0A1 | 2 bytes | 10 ms | SWC_SpeedMonitor | SWC_DoorControl |
| Sig_IgnitionStatus | 0x0B2 | 1 byte | 50 ms | SWC_PowerMode | SWC_LightControl |
| Sig_IndicatorRequest | 0x133 | 1 byte | 20 ms | SWC_LightControl | SWC_Gateway |
| Sig_WindowPosition | 0x141 | 2 bytes | 20 ms | SWC_WindowControl | SWC_Gateway |
| Sig_AmbientLight | 0x152 | 1 byte | 500 ms | SWC_LightControl | SWC_Gateway |

## 6 Basic Software Configuration

The following basic software modules are configured for this ECU.

Com handles signal packing and unpacking for CAN FD frames.
PduR routes PDUs between CanIf, Com and Dcm.
CanIf provides the hardware abstraction for the CAN controller.
CanTp performs segmentation for diagnostic messages.
Dcm implements the UDS diagnostic server.
Dem manages the event memory and diagnostic trouble codes.
NvM stores the persistent configuration and the learned window end positions.
Fee provides the flash emulation for NvM.
EcuM controls the startup and shutdown sequence.
BswM arbitrates the mode requests.
Os provides the scheduling of the 5 ms, 10 ms, 20 ms, 50 ms and 100 ms tasks.
WdgM supervises the alive counters of the application components.
Rte generates the component connections and the task bodies.

## 7 Functional Flow: Central Locking

1. The user presses the lock button on the key fob.
2. SWC_Gateway receives VehicleState_PDU from Com containing the request.
3. SWC_Gateway sends the lock request through IF_LockCommand to SWC_DoorControl.
4. SWC_DoorControl requires Sig_VehicleSpeed from SWC_SpeedMonitor for the speed lock check.
5. SWC_DoorControl actuates the lock motors and updates the lock state machine.
6. SWC_DoorControl sends Sig_DoorLockState to SWC_Gateway.
7. SWC_Gateway sends BcmStatus_PDU to Com for transmission on CAN FD.

## 8 Timing and Resources

The 5 ms task holds Re_WindowControl_Main only. The 10 ms task holds
Re_DoorControl_Main, Re_Gateway_Main and Re_SpeedMonitor_Main. The worst case
execution time budget for the 10 ms task is 3.2 ms.

## 9 Open Points

The ambient light handling for Sig_AmbientLight is not yet allocated to a consumer
component. The welcome lighting timing is to be confirmed with the vehicle integration
team.
