# Body Control Module High-Level Design

Document ID: HLD-BCM-0042
Revision: Rev B
Classification: Internal
Status: Approved for development

## 1 Introduction

This High-Level Design describes the AUTOSAR Classic Platform architecture of the Body
Control Module (BCM) for the X200 vehicle programme. Rev B adds the mirror control
component and removes the separate speed monitor.

## 3 Software Components

### 3.1 SWC_DoorControl

SWC_DoorControl manages central locking, individual door actuation and the child lock.

PPort DoorStatus provides the interface IF_DoorStatus of kind SenderReceiver.
RPort LockCommand requires the interface IF_LockCommand of kind ClientServer.
Runnable Re_DoorControl_Main executes every 10 ms.

SWC_DoorControl sends Sig_DoorLockState to SWC_Gateway.
SWC_DoorControl requires Sig_VehicleSpeed from SWC_Gateway.

### 3.2 SWC_LightControl

SWC_LightControl manages exterior lighting, hazard lights and the welcome sequence.

PPort LightStatus provides the interface IF_LightStatus of kind SenderReceiver.
RPort IgnitionState requires the interface IF_IgnitionState of kind SenderReceiver.
Runnable Re_LightControl_Main executes every 20 ms.

SWC_LightControl receives Sig_IgnitionStatus from SWC_PowerMode.
SWC_LightControl sends Sig_IndicatorRequest to SWC_Gateway.
SWC_LightControl consumes Sig_AmbientLight from SWC_Gateway.

### 3.3 SWC_WindowControl

SWC_WindowControl manages the four power windows including the anti-pinch function.

PPort WindowPosition provides the interface IF_WindowPosition of kind SenderReceiver.
RPort MotorCurrent requires the interface IF_MotorCurrent of kind SenderReceiver.
Runnable Re_WindowControl_Main executes every 5 ms.

SWC_WindowControl requires Sig_VehicleSpeed from SWC_Gateway.
SWC_WindowControl sends Sig_WindowPosition to SWC_Gateway.

### 3.4 SWC_Gateway

SWC_Gateway routes application signals to and from the vehicle network and now also
derives the vehicle speed previously produced by the speed monitor.

PPort NetworkTx provides the interface IF_NetworkTx of kind SenderReceiver.
PPort VehicleSpeed provides the interface IF_VehicleSpeed of kind SenderReceiver.
RPort NetworkRx requires the interface IF_NetworkRx of kind SenderReceiver.
Runnable Re_Gateway_Main executes every 10 ms.

SWC_Gateway sends BcmStatus_PDU to Com.
SWC_Gateway publishes Sig_VehicleSpeed to SWC_DoorControl.

### 3.5 SWC_PowerMode

SWC_PowerMode derives the ECU power mode from the ignition line.

PPort PowerModeStatus provides the interface IF_PowerModeStatus of kind ModeSwitch.
Runnable Re_PowerMode_Main executes every 50 ms.

SWC_PowerMode provides Sig_IgnitionStatus to SWC_LightControl.

### 3.6 SWC_MirrorControl

SWC_MirrorControl is new in Rev B. It manages the electric mirror adjustment, folding
and heating.

PPort MirrorStatus provides the interface IF_MirrorStatus of kind SenderReceiver.
RPort MirrorCommand requires the interface IF_MirrorCommand of kind ClientServer.
Runnable Re_MirrorControl_Main executes every 50 ms.

SWC_MirrorControl sends Sig_MirrorPosition to SWC_Gateway.
SWC_MirrorControl requires Sig_VehicleSpeed from SWC_Gateway.

### 3.7 SWC_DiagnosticHandler

SWC_DiagnosticHandler implements the application part of the diagnostic services.

PPort DiagnosticData provides the interface IF_DiagnosticData of kind ClientServer.
Runnable Re_DiagnosticHandler_Main executes every 100 ms.

SWC_DiagnosticHandler calls Dem for event reporting.
SWC_DiagnosticHandler requires Sig_DoorLockState from SWC_DoorControl.

## 5 Signal Catalogue

| Signal | CAN ID | Length | Cycle | Producer | Consumer |
| --- | --- | --- | --- | --- | --- |
| Sig_DoorLockState | 0x120 | 1 byte | 100 ms | SWC_DoorControl | SWC_Gateway |
| Sig_VehicleSpeed | 0x0A1 | 2 bytes | 10 ms | SWC_Gateway | SWC_DoorControl |
| Sig_IgnitionStatus | 0x0B2 | 1 byte | 50 ms | SWC_PowerMode | SWC_LightControl |
| Sig_IndicatorRequest | 0x133 | 1 byte | 20 ms | SWC_LightControl | SWC_Gateway |
| Sig_WindowPosition | 0x141 | 2 bytes | 20 ms | SWC_WindowControl | SWC_Gateway |
| Sig_AmbientLight | 0x152 | 1 byte | 500 ms | SWC_Gateway | SWC_LightControl |
| Sig_MirrorPosition | 0x163 | 2 bytes | 100 ms | SWC_MirrorControl | SWC_Gateway |

## 6 Basic Software Configuration

Com handles signal packing and unpacking for CAN FD frames.
PduR routes PDUs between CanIf, Com and Dcm.
CanIf provides the hardware abstraction for the CAN controller.
CanTp performs segmentation for diagnostic messages.
Dcm implements the UDS diagnostic server.
Dem manages the event memory and diagnostic trouble codes.
NvM stores the persistent configuration.
Fee provides the flash emulation for NvM.
EcuM controls the startup and shutdown sequence.
BswM arbitrates the mode requests.
Os provides the task scheduling.
WdgM supervises the alive counters.
Rte generates the component connections.
CryIf and Csm are added in Rev B for the SecOC key handling.
SecOC provides authentication for the safety relevant PDUs.

## 9 Open Points

The mirror heating current limit is to be confirmed. SWC_SpeedMonitor has been removed
and its responsibility moved into SWC_Gateway.
