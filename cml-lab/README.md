# BRKOPS-2585 CML Lab - OSPF Demo

4 Cat8000v routers in full mesh topology for the BRKOPS-2585 Cisco Live demo.

## Topology Diagram

```
                    External Connector (bridge1)
                           |
            +--------------+--------------+
            |              |              |
    +-------+---+   +------+----+   +-----+-----+   +-----------+
    |  Router-1 |---|  Router-2 |---|  Router-3 |---|  Router-4 |
    | Cat8000v  |   | Cat8000v  |   | Cat8000v  |   | Cat8000v  |
    |198.18.1.201|   |198.18.1.202|   |198.18.1.203|   |198.18.1.204|
    +-----+-----+   +-----+-----+   +-----+-----+   +-----+-----+
          |               |               |               |
          +---------------+---------------+---------------+
                        Full Mesh (6 Links)

    Links:
    - R1 <-> R2 (10.1.12.0/30)
    - R1 <-> R3 (10.1.13.0/30)
    - R1 <-> R4 (10.1.14.0/30)
    - R2 <-> R3 (10.1.23.0/30)
    - R2 <-> R4 (10.1.24.0/30)
    - R3 <-> R4 (10.1.34.0/30)
```

## IP Addressing

### Management Network (via External Connector bridge1)

| Router   | Interface        | IP Address       | Gateway     |
|----------|------------------|------------------|-------------|
| Router-1 | GigabitEthernet1 | 198.18.1.201/24  | 198.18.1.1  |
| Router-2 | GigabitEthernet1 | 198.18.1.202/24  | 198.18.1.1  |
| Router-3 | GigabitEthernet1 | 198.18.1.203/24  | 198.18.1.1  |
| Router-4 | GigabitEthernet1 | 198.18.1.204/24  | 198.18.1.1  |

### Inter-Router Links (OSPF Network)

| Link  | Router A     | Router A IP   | Router B     | Router B IP   |
|-------|--------------|---------------|--------------|---------------|
| R1-R2 | Router-1 Gi2 | 10.1.12.1/30  | Router-2 Gi2 | 10.1.12.2/30  |
| R1-R3 | Router-1 Gi3 | 10.1.13.1/30  | Router-3 Gi2 | 10.1.13.2/30  |
| R1-R4 | Router-1 Gi4 | 10.1.14.1/30  | Router-4 Gi2 | 10.1.14.2/30  |
| R2-R3 | Router-2 Gi3 | 10.1.23.1/30  | Router-3 Gi3 | 10.1.23.2/30  |
| R2-R4 | Router-2 Gi4 | 10.1.24.1/30  | Router-4 Gi3 | 10.1.24.2/30  |
| R3-R4 | Router-3 Gi4 | 10.1.34.1/30  | Router-4 Gi4 | 10.1.34.2/30  |

### Loopbacks (Router IDs)

| Router   | Loopback0 IP     | OSPF Router-ID |
|----------|------------------|----------------|
| Router-1 | 10.255.255.1/32  | 10.255.255.1   |
| Router-2 | 10.255.255.2/32  | 10.255.255.2   |
| Router-3 | 10.255.255.3/32  | 10.255.255.3   |
| Router-4 | 10.255.255.4/32  | 10.255.255.4   |

## Features

- **OSPF Routing**: All routers in Area 0, point-to-point network type
- **Model Driven Telemetry (MDT)**: Streaming to Splunk at 198.18.134.22:57400
  - CPU utilization (5-second average)
  - Interface statistics
  - Memory statistics
  - OSPF operational data (on-change)
- **Syslog**: Forwarding to 198.18.134.22:514
- **SNMP**: Community strings public (RO) / private (RW)
- **NETCONF/YANG**: Enabled for programmatic management

## dCloud Environment

- **CML Instance**: https://198.18.130.201
- **CML Credentials**: admin / C1sco12345
- **Splunk/Telemetry Target**: 198.18.134.22
- **Telemetry gRPC Port**: 57400
- **Syslog Port**: 514
- **SNMP Trap Port**: 162

## Credentials

- **Router Enable/Login**: admin / cisco

## Files

| File                        | Purpose                    |
|-----------------------------|----------------------------|
| `brkops-ospf-demo.yaml`     | CML topology definition    |
| `configs/router-1.cfg`      | Router-1 startup config    |
| `configs/router-2.cfg`      | Router-2 startup config    |
| `configs/router-3.cfg`      | Router-3 startup config    |
| `configs/router-4.cfg`      | Router-4 startup config    |

## Deployment

### Option 1: CML Web UI

1. Log into CML at https://198.18.130.201
2. Click "Import" and select `brkops-ospf-demo.yaml`
3. Start the lab
4. Wait for all nodes to boot (Cat8000v takes several minutes)

### Option 2: BRKOPS Platform Admin UI

1. Navigate to Admin Panel > CML Labs
2. Click "Build Demo Lab" to create the predefined topology
3. Click "Start Lab" to boot all routers

### Option 3: CML API / MCP Tools

Use the `create_full_lab_topology` MCP tool with the YAML content.

## Verification Commands

Run on each router after lab starts:

```
! Check OSPF neighbors (should see 3 neighbors)
show ip ospf neighbor

! Check OSPF routes
show ip route ospf

! Check telemetry subscriptions
show telemetry ietf subscription all

! Check syslog config
show logging

! Check SNMP config
show snmp host
```

## Expected OSPF Neighbor Output

Each router should show 3 FULL adjacencies:

```
Router-1# show ip ospf neighbor

Neighbor ID     Pri   State           Dead Time   Address         Interface
10.255.255.2      0   FULL/  -        00:00:39    10.1.12.2       GigabitEthernet2
10.255.255.3      0   FULL/  -        00:00:35    10.1.13.2       GigabitEthernet3
10.255.255.4      0   FULL/  -        00:00:37    10.1.14.2       GigabitEthernet4
```
