# =============================================================================
# BRKOPS-2585 Config Builder
# Parse IOS running configs and build per-device commands dynamically.
# Pure functions - no CML client dependency.
# =============================================================================

import re
import secrets
import string
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger()


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class InterfaceConfig:
    name: str
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    description: Optional[str] = None
    shutdown: bool = False
    ospf_process_id: Optional[int] = None
    ospf_area: Optional[int] = None
    ospf_network_type: Optional[str] = None
    acl_in: Optional[str] = None
    acl_out: Optional[str] = None


@dataclass
class OSPFNetworkStatement:
    network: str
    wildcard: str
    area: int


@dataclass
class OSPFProcessConfig:
    process_id: int
    router_id: Optional[str] = None
    network_statements: List[OSPFNetworkStatement] = field(default_factory=list)
    passive_interfaces: List[str] = field(default_factory=list)


@dataclass
class UserConfig:
    username: str
    privilege: Optional[int] = None
    secret_type: Optional[int] = None
    secret_hash: Optional[str] = None


@dataclass
class AccessListRule:
    sequence: Optional[int] = None
    action: str = "permit"
    protocol: str = "ip"
    source: str = "any"
    destination: str = "any"
    extras: str = ""


@dataclass
class AccessListConfig:
    name: str
    acl_type: str = "extended"
    rules: List[AccessListRule] = field(default_factory=list)


@dataclass
class ParsedConfig:
    hostname: str = "Router"
    interfaces: Dict[str, InterfaceConfig] = field(default_factory=dict)
    ospf_processes: Dict[int, OSPFProcessConfig] = field(default_factory=dict)
    users: Dict[str, UserConfig] = field(default_factory=dict)
    enable_secret_exists: bool = False
    enable_secret_type: Optional[int] = None
    access_lists: Dict[str, AccessListConfig] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ConfigChangeResult:
    commands: List[str] = field(default_factory=list)
    rollback_commands: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    affected_interfaces: List[Dict] = field(default_factory=list)
    ospf_process_id: Optional[int] = None


# =============================================================================
# Regex Patterns
# =============================================================================

RE_HOSTNAME = re.compile(r'^hostname\s+(\S+)')
RE_INTERFACE = re.compile(r'^interface\s+(\S+)')
RE_IP_ADDRESS = re.compile(r'^\s+ip\s+address\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)')
RE_DESCRIPTION = re.compile(r'^\s+description\s+(.*)')
RE_SHUTDOWN = re.compile(r'^\s+shutdown')
RE_OSPF_INTERFACE = re.compile(r'^\s+ip\s+ospf\s+(\d+)\s+area\s+(\d+)')
RE_OSPF_NETWORK_TYPE = re.compile(r'^\s+ip\s+ospf\s+network\s+(\S+)')
RE_ROUTER_OSPF = re.compile(r'^router\s+ospf\s+(\d+)')
RE_ROUTER_ID = re.compile(r'^\s+router-id\s+(\S+)')
RE_NETWORK_STMT = re.compile(r'^\s+network\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+area\s+(\d+)')
RE_PASSIVE_INTF = re.compile(r'^\s+passive-interface\s+(\S+)')
RE_ENABLE_SECRET = re.compile(r'^enable\s+(?:algorithm-type\s+\S+\s+)?secret\s+(\d+)\s+(\S+)')
RE_USERNAME = re.compile(r'^username\s+(\S+)\s+(?:privilege\s+(\d+)\s+)?(?:algorithm-type\s+\S+\s+)?secret\s+(\d+)\s+(\S+)')
RE_ACL_NAMED = re.compile(r'^ip\s+access-list\s+(extended|standard)\s+(\S+)')
RE_ACL_GROUP = re.compile(r'^\s+ip\s+access-group\s+(\S+)\s+(in|out)')


# =============================================================================
# Config Cleaner
# =============================================================================

def _clean_config_output(raw: str) -> str:
    """Strip CLI preamble, prompts, and trailing garbage from show run output."""
    lines = raw.split('\n')
    cleaned = []
    in_config = False
    for line in lines:
        # Skip common CLI preamble lines
        stripped = line.strip()
        if stripped.startswith('Building configuration') or stripped.startswith('Current configuration'):
            in_config = True
            continue
        if stripped.startswith('!') and not in_config:
            in_config = True
        if in_config:
            # Stop at trailing prompt
            if re.match(r'^\S+[#>]', stripped) and not stripped.startswith('!'):
                break
            cleaned.append(line)
    return '\n'.join(cleaned) if cleaned else raw


# =============================================================================
# Parser
# =============================================================================

def parse_running_config(raw_config: str) -> ParsedConfig:
    """
    Parse a Cisco IOS running config into structured data.
    Handles both interface-level OSPF and router-level network statements.
    """
    config = _clean_config_output(raw_config)
    parsed = ParsedConfig()

    current_section = "top"
    current_interface: Optional[InterfaceConfig] = None
    current_ospf: Optional[OSPFProcessConfig] = None
    current_acl: Optional[AccessListConfig] = None

    for line in config.split('\n'):
        # Top-level matchers
        m = RE_HOSTNAME.match(line)
        if m:
            parsed.hostname = m.group(1)
            current_section = "top"
            current_interface = None
            current_ospf = None
            current_acl = None
            continue

        m = RE_INTERFACE.match(line)
        if m:
            iface_name = m.group(1)
            current_interface = InterfaceConfig(name=iface_name)
            parsed.interfaces[iface_name] = current_interface
            current_section = "interface"
            current_ospf = None
            current_acl = None
            continue

        m = RE_ROUTER_OSPF.match(line)
        if m:
            pid = int(m.group(1))
            current_ospf = parsed.ospf_processes.get(pid, OSPFProcessConfig(process_id=pid))
            parsed.ospf_processes[pid] = current_ospf
            current_section = "router_ospf"
            current_interface = None
            current_acl = None
            continue

        m = RE_ACL_NAMED.match(line)
        if m:
            acl_type = m.group(1)
            acl_name = m.group(2)
            current_acl = AccessListConfig(name=acl_name, acl_type=acl_type)
            parsed.access_lists[acl_name] = current_acl
            current_section = "acl"
            current_interface = None
            current_ospf = None
            continue

        # Enable secret (top-level)
        m = RE_ENABLE_SECRET.match(line)
        if m:
            parsed.enable_secret_exists = True
            parsed.enable_secret_type = int(m.group(1))
            continue

        # Username (top-level)
        m = RE_USERNAME.match(line)
        if m:
            uname = m.group(1)
            priv = int(m.group(2)) if m.group(2) else None
            stype = int(m.group(3))
            shash = m.group(4)
            parsed.users[uname] = UserConfig(
                username=uname, privilege=priv,
                secret_type=stype, secret_hash=shash,
            )
            continue

        # Section-specific matchers
        if current_section == "interface" and current_interface:
            m = RE_IP_ADDRESS.match(line)
            if m:
                current_interface.ip_address = m.group(1)
                current_interface.subnet_mask = m.group(2)
                continue

            m = RE_DESCRIPTION.match(line)
            if m:
                current_interface.description = m.group(1).strip()
                continue

            if RE_SHUTDOWN.match(line):
                current_interface.shutdown = True
                continue

            m = RE_OSPF_INTERFACE.match(line)
            if m:
                current_interface.ospf_process_id = int(m.group(1))
                current_interface.ospf_area = int(m.group(2))
                continue

            m = RE_OSPF_NETWORK_TYPE.match(line)
            if m:
                current_interface.ospf_network_type = m.group(1)
                continue

            m = RE_ACL_GROUP.match(line)
            if m:
                acl_name = m.group(1)
                direction = m.group(2)
                if direction == "in":
                    current_interface.acl_in = acl_name
                else:
                    current_interface.acl_out = acl_name
                continue

        elif current_section == "router_ospf" and current_ospf:
            m = RE_ROUTER_ID.match(line)
            if m:
                current_ospf.router_id = m.group(1)
                continue

            m = RE_NETWORK_STMT.match(line)
            if m:
                current_ospf.network_statements.append(OSPFNetworkStatement(
                    network=m.group(1),
                    wildcard=m.group(2),
                    area=int(m.group(3)),
                ))
                continue

            m = RE_PASSIVE_INTF.match(line)
            if m:
                current_ospf.passive_interfaces.append(m.group(1))
                continue

        elif current_section == "acl" and current_acl:
            stripped = line.strip()
            if stripped and not stripped.startswith('!'):
                # Parse ACL rule (simplified)
                parts = stripped.split()
                if parts and parts[0] in ("permit", "deny"):
                    rule = AccessListRule(action=parts[0])
                    if len(parts) > 1:
                        rule.protocol = parts[1]
                    if len(parts) > 2:
                        rule.source = parts[2]
                    if len(parts) > 3:
                        rule.destination = ' '.join(parts[3:])
                    current_acl.rules.append(rule)
                elif parts and parts[0].isdigit():
                    # Numbered ACL entry
                    rule = AccessListRule(sequence=int(parts[0]))
                    if len(parts) > 1:
                        rule.action = parts[1]
                    if len(parts) > 2:
                        rule.protocol = parts[2]
                    if len(parts) > 3:
                        rule.source = parts[3]
                    if len(parts) > 4:
                        rule.destination = ' '.join(parts[4:])
                    current_acl.rules.append(rule)

        # Section exit on '!' or unindented line (except section headers)
        stripped = line.strip()
        if stripped == '!' or (stripped == 'end'):
            if current_section != "top":
                current_section = "top"
                current_interface = None
                current_ospf = None
                current_acl = None

    return parsed


# =============================================================================
# Helpers
# =============================================================================

def _ip_to_int(ip: str) -> int:
    """Convert dotted-decimal IP to integer."""
    parts = ip.split('.')
    return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])


def _ip_in_network(ip: str, network: str, wildcard: str) -> bool:
    """Check if an IP address falls within a network/wildcard pair."""
    ip_int = _ip_to_int(ip)
    net_int = _ip_to_int(network)
    wild_int = _ip_to_int(wildcard)
    # In OSPF wildcard: 0 bits must match, 1 bits are don't-care
    return (ip_int & ~wild_int) == (net_int & ~wild_int)


def get_ospf_interfaces(parsed: ParsedConfig, process_id: Optional[int] = None) -> Dict[str, int]:
    """
    Get mapping of interface_name -> area for all OSPF-participating interfaces.
    Works for both interface-level and network-statement style configs.

    Returns:
        Dict mapping interface name to its OSPF area
    """
    result = {}

    # Check interface-level OSPF config
    for iface_name, iface in parsed.interfaces.items():
        if iface.ospf_process_id is not None and iface.ospf_area is not None:
            if process_id is None or iface.ospf_process_id == process_id:
                result[iface_name] = iface.ospf_area

    # Check network-statement style (match interface IPs to network statements)
    for pid, ospf in parsed.ospf_processes.items():
        if process_id is not None and pid != process_id:
            continue
        for stmt in ospf.network_statements:
            for iface_name, iface in parsed.interfaces.items():
                if iface.ip_address and _ip_in_network(iface.ip_address, stmt.network, stmt.wildcard):
                    if iface_name not in result:
                        result[iface_name] = stmt.area

    return result


def generate_secure_password(length: int = 20) -> str:
    """Generate a cryptographically secure password meeting complexity requirements."""
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.isupper() for c in password) and
            any(c.islower() for c in password) and
            any(c.isdigit() for c in password) and
            any(c in "!@#$%&*" for c in password)):
            return password


# =============================================================================
# OSPF Area Change Builder
# =============================================================================

def _generate_interface_ospf_commands(
    interfaces: List[Dict],
    ospf_process_id: int,
    new_area: int,
) -> Tuple[List[str], List[str]]:
    """
    Generate interface-level OSPF commands from interface metadata.

    Args:
        interfaces: List of interface metadata dicts with 'name' and 'current_area'
        ospf_process_id: OSPF process ID
        new_area: Target OSPF area number

    Returns:
        Tuple of (commands, rollback_commands)
    """
    commands = []
    rollback = []
    for iface in interfaces:
        commands.append(f"interface {iface['name']}")
        commands.append(f" ip ospf {ospf_process_id} area {new_area}")
        rollback.append(f"interface {iface['name']}")
        rollback.append(f" ip ospf {ospf_process_id} area {iface['current_area']}")
    return commands, rollback


def build_ospf_area_change(
    parsed: ParsedConfig,
    new_area: int,
    ospf_process_id: Optional[int] = None,
    target_interfaces: Optional[List[str]] = None,
    config_strategy: str = "dual",
) -> ConfigChangeResult:
    """
    Build commands to change OSPF area on a device.
    Detects config style (per-interface vs network-statement) and generates appropriate commands.

    Args:
        parsed: Parsed running config
        new_area: Target OSPF area number
        ospf_process_id: Specific process ID (None = first/only process)
        target_interfaces: Limit to specific interfaces (None = all OSPF interfaces)

    Returns:
        ConfigChangeResult with commands, rollback_commands, and warnings
    """
    result = ConfigChangeResult()

    # Determine which OSPF process to modify
    if ospf_process_id is not None:
        ospf = parsed.ospf_processes.get(ospf_process_id)
    elif parsed.ospf_processes:
        pid = next(iter(parsed.ospf_processes))
        ospf = parsed.ospf_processes[pid]
        ospf_process_id = pid
    else:
        # No OSPF process found, check interface-level config
        ospf = None
        for iface in parsed.interfaces.values():
            if iface.ospf_process_id is not None:
                ospf_process_id = iface.ospf_process_id
                break

    if ospf_process_id is None:
        result.warnings.append("No OSPF process found in running config")
        return result

    result.ospf_process_id = ospf_process_id

    # Detect config style and build commands
    uses_network_statements = ospf and len(ospf.network_statements) > 0
    uses_interface_level = any(
        iface.ospf_process_id is not None
        for iface in parsed.interfaces.values()
    )

    # Determine what to generate based on strategy
    generate_network_commands = False
    generate_interface_commands = False

    if config_strategy == "dual":
        generate_network_commands = uses_network_statements
        generate_interface_commands = True  # Always try to generate
    elif config_strategy == "network_only":
        generate_network_commands = uses_network_statements
        generate_interface_commands = False
    elif config_strategy == "interface_only":
        generate_network_commands = False
        generate_interface_commands = True

    # Generate network statement commands
    if generate_network_commands and ospf:
        # Network-statement style (typical CML baseline)
        result.commands.append(f"router ospf {ospf_process_id}")
        result.rollback_commands.append(f"router ospf {ospf_process_id}")

        for stmt in ospf.network_statements:
            # Check if this statement maps to a target interface
            if target_interfaces:
                matches_target = False
                for iface_name in target_interfaces:
                    iface = parsed.interfaces.get(iface_name)
                    if iface and iface.ip_address and _ip_in_network(iface.ip_address, stmt.network, stmt.wildcard):
                        matches_target = True
                        break
                if not matches_target:
                    continue

            if stmt.area == new_area:
                result.warnings.append(
                    f"Network {stmt.network} {stmt.wildcard} already in area {new_area}, skipping"
                )
                continue

            # Map this network statement to affected interfaces
            for iface_name, iface in parsed.interfaces.items():
                if iface.ip_address and _ip_in_network(iface.ip_address, stmt.network, stmt.wildcard):
                    result.affected_interfaces.append({
                        "name": iface_name,
                        "ip_address": iface.ip_address,
                        "subnet_mask": iface.subnet_mask,
                        "description": iface.description,
                        "network_statement": f"{stmt.network} {stmt.wildcard}",
                        "current_area": stmt.area,
                        "new_area": new_area,
                        "ospf_network_type": iface.ospf_network_type,
                    })

            # Remove old, add new
            result.commands.append(f" no network {stmt.network} {stmt.wildcard} area {stmt.area}")
            result.commands.append(f" network {stmt.network} {stmt.wildcard} area {new_area}")
            # Rollback: reverse the change
            result.rollback_commands.append(f" no network {stmt.network} {stmt.wildcard} area {new_area}")
            result.rollback_commands.append(f" network {stmt.network} {stmt.wildcard} area {stmt.area}")

    # Generate interface-level commands (NEW - for dual mode and interface_only mode)
    if generate_interface_commands and result.affected_interfaces:
        iface_cmds, iface_rollback = _generate_interface_ospf_commands(
            result.affected_interfaces,
            ospf_process_id,
            new_area
        )
        result.commands.extend(iface_cmds)
        result.rollback_commands.extend(iface_rollback)

    # Special handling for interface_only mode - remove network statements
    if config_strategy == "interface_only" and ospf and len(ospf.network_statements) > 0:
        result.commands.insert(0, f"router ospf {ospf_process_id}")
        for stmt in ospf.network_statements:
            result.commands.append(f" no network {stmt.network} {stmt.wildcard} area {stmt.area}")

    # Legacy path: Per-interface style detection (only if interface commands weren't generated)
    if not generate_interface_commands and uses_interface_level:
        # Per-interface style (ip ospf X area Y on each interface)
        for iface_name, iface in parsed.interfaces.items():
            if iface.ospf_process_id is None or iface.ospf_area is None:
                continue
            if ospf_process_id is not None and iface.ospf_process_id != ospf_process_id:
                continue
            if target_interfaces and iface_name not in target_interfaces:
                continue

            if iface.ospf_area == new_area:
                result.warnings.append(
                    f"Interface {iface_name} already in area {new_area}, skipping"
                )
                continue

            old_area = iface.ospf_area
            result.affected_interfaces.append({
                "name": iface_name,
                "ip_address": iface.ip_address,
                "subnet_mask": iface.subnet_mask,
                "description": iface.description,
                "current_area": old_area,
                "new_area": new_area,
                "ospf_network_type": iface.ospf_network_type,
            })
            result.commands.append(f"interface {iface_name}")
            result.commands.append(f" ip ospf {iface.ospf_process_id} area {new_area}")
            result.rollback_commands.append(f"interface {iface_name}")
            result.rollback_commands.append(f" ip ospf {iface.ospf_process_id} area {old_area}")

    if not result.commands:
        result.warnings.append("No OSPF configuration found to modify")

    # Clean up empty command lists (only had the router ospf header)
    if result.commands == [f"router ospf {ospf_process_id}"]:
        result.commands = []
        result.rollback_commands = []
        result.warnings.append("No OSPF changes needed (all statements already in target area)")

    return result


# =============================================================================
# Credential Rotation Builder
# =============================================================================

def build_credential_rotation(
    parsed: ParsedConfig,
    new_password: Optional[str] = None,
    username: str = "admin",
) -> ConfigChangeResult:
    """
    Build commands to rotate device credentials (enable secret + username).

    Args:
        parsed: Parsed running config
        new_password: Explicit password (None = generate random)
        username: Username to rotate (default: admin)

    Returns:
        ConfigChangeResult with commands, rollback, and warnings
    """
    result = ConfigChangeResult()

    if new_password is None:
        new_password = generate_secure_password()

    result.warnings.append(f"Generated password: {new_password}")

    # Enable secret
    if parsed.enable_secret_exists:
        result.commands.append(f"enable algorithm-type sha256 secret 0 {new_password}")
        result.rollback_commands.append("! WARNING: Cannot reverse hashed password. Manual reset required.")
    else:
        result.commands.append(f"enable algorithm-type sha256 secret 0 {new_password}")
        result.rollback_commands.append("no enable secret")

    # Username
    user = parsed.users.get(username)
    if user:
        priv = user.privilege if user.privilege is not None else 15
        result.commands.append(
            f"username {username} privilege {priv} algorithm-type sha256 secret 0 {new_password}"
        )
        result.rollback_commands.append(
            f"! WARNING: Cannot reverse hashed password for user '{username}'. Manual reset required."
        )
    else:
        result.commands.append(
            f"username {username} privilege 15 algorithm-type sha256 secret 0 {new_password}"
        )
        result.rollback_commands.append(f"no username {username}")
        result.warnings.append(f"User '{username}' not found in config, creating new user")

    result.warnings.append("Rollback for credential rotation requires manual password reset")

    return result


# =============================================================================
# Security ACL Builder
# =============================================================================

def build_security_acl(
    parsed: ParsedConfig,
    acl_name: str,
    rules: List[Dict],
    target_interfaces: Optional[List[str]] = None,
    direction: str = "in",
) -> ConfigChangeResult:
    """
    Build commands to apply a security ACL.

    Args:
        parsed: Parsed running config
        acl_name: Name for the ACL
        rules: List of rule dicts with keys: action, protocol, source, destination, extras
        target_interfaces: Interfaces to apply ACL (None = all active GigabitEthernet)
        direction: "in" or "out"

    Returns:
        ConfigChangeResult with commands, rollback, and warnings
    """
    result = ConfigChangeResult()

    # Build ACL
    result.commands.append(f"ip access-list extended {acl_name}")
    result.rollback_commands.append(f"no ip access-list extended {acl_name}")

    for rule in rules:
        action = rule.get("action", "deny")
        protocol = rule.get("protocol", "tcp")
        source = rule.get("source", "any")
        destination = rule.get("destination", "any")
        extras = rule.get("extras", "")
        line = f" {action} {protocol} {source} {destination}"
        if extras:
            line += f" {extras}"
        result.commands.append(line)

    # Always add permit any at the end
    result.commands.append(" permit ip any any")

    # Determine target interfaces
    if target_interfaces is None:
        target_interfaces = [
            name for name, iface in parsed.interfaces.items()
            if name.startswith("GigabitEthernet") and not iface.shutdown and iface.ip_address
        ]

    if not target_interfaces:
        result.warnings.append("No active GigabitEthernet interfaces found for ACL application")

    # Apply ACL to interfaces
    for iface_name in target_interfaces:
        iface = parsed.interfaces.get(iface_name)
        existing_acl = None
        if iface:
            existing_acl = iface.acl_in if direction == "in" else iface.acl_out

        result.commands.append(f"interface {iface_name}")
        result.commands.append(f" ip access-group {acl_name} {direction}")

        # Rollback: remove ACL binding, restore previous if existed
        result.rollback_commands.append(f"interface {iface_name}")
        result.rollback_commands.append(f" no ip access-group {acl_name} {direction}")
        if existing_acl:
            result.rollback_commands.append(f" ip access-group {existing_acl} {direction}")
            result.warnings.append(
                f"Interface {iface_name} had existing ACL '{existing_acl}' ({direction}), will be replaced"
            )

    return result


# =============================================================================
# Builder Registry - Dynamic dispatch for config generation
# =============================================================================

def _build_ospf(parsed: ParsedConfig, params: dict) -> ConfigChangeResult:
    """Wrapper for OSPF area change builder."""
    return build_ospf_area_change(
        parsed,
        new_area=params.get("new_area", 10),
        ospf_process_id=params.get("ospf_process_id"),
        config_strategy=params.get("config_strategy", "dual"),
    )


def _build_credentials(parsed: ParsedConfig, params: dict) -> ConfigChangeResult:
    """Wrapper for credential rotation builder."""
    return build_credential_rotation(
        parsed,
        new_password=params.get("new_password"),
        username=params.get("username", "admin"),
    )


def _build_security(parsed: ParsedConfig, params: dict) -> ConfigChangeResult:
    """Wrapper for security ACL builder."""
    cve_id = params.get("cve_id", "SEC")
    acl_name = f"{cve_id}-BLOCK"
    rules = params.get("acl_rules", [
        {"action": "deny", "protocol": "tcp", "source": "any", "destination": "any eq 445", "extras": "log"},
        {"action": "deny", "protocol": "udp", "source": "any", "destination": "any eq 445", "extras": "log"},
    ])
    return build_security_acl(parsed, acl_name=acl_name, rules=rules)


BUILDER_REGISTRY: Dict[str, Callable[[ParsedConfig, dict], ConfigChangeResult]] = {
    "modify_ospf_area": _build_ospf,
    "modify_ospf_config": _build_ospf,
    "change_area": _build_ospf,
    "ospf_configuration_change": _build_ospf,
    "rotate_credentials": _build_credentials,
    "credential_rotation": _build_credentials,
    "apply_security_patch": _build_security,
    "security_remediation": _build_security,
    "security_advisory": _build_security,
}


def build_config_for_action(action: str, parsed: ParsedConfig, params: dict) -> Optional[ConfigChangeResult]:
    """
    Registry dispatch. Returns None if no builder registered (LLM fallback).

    Args:
        action: Action name from intent parsing
        parsed: Parsed running config
        params: Parameters from intent

    Returns:
        ConfigChangeResult or None if no builder matches
    """
    builder = BUILDER_REGISTRY.get(action.lower())
    return builder(parsed, params) if builder else None
