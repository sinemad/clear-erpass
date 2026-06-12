"""ClearPass attribute name → human-readable label translation table.

Add entries here as new attributes are encountered in the wild. Unknown
attributes are flagged in the graph so they show up as a visible punch list.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Translation table: ClearPass attribute name → short human label
# ---------------------------------------------------------------------------

ATTR_LABELS: dict[str, str] = {
    # ── Authentication ──────────────────────────────────────────────────────
    "Authentication:Status": "Auth Status",
    "Authentication:Protocol": "Auth Protocol",
    "Authentication:Inner-Protocol": "Inner Protocol",
    "Authentication:EAP-Type": "EAP Type",
    "Authentication:Username": "Username",
    "Authentication:MAC-Address": "Client MAC",
    "Authentication:Host-Name": "Host Name",
    "Authentication:Service-Type": "Service Type",
    "Authentication:Source": "Auth Source",
    "Authentication:Method": "Auth Method",

    # ── Aruba short-form VSA (no namespace) ─────────────────────────────────
    "Aruba-User-Role": "User Role",
    "Aruba-AirGroup-Version": "AirGroup Version",
    "Aruba-AirGroup-Shared-Role": "AirGroup Shared Role",
    "Aruba-AirGroup-Shared-Group": "AirGroup Shared Group",
    "Aruba-Device-Type": "Device Type",

    # ── RADIUS IETF ─────────────────────────────────────────────────────────
    "RADIUS:IETF:NAS-Port-Type": "Connection Type",
    "RADIUS:IETF:Called-Station-Id": "Called Station ID",
    "RADIUS:IETF:Calling-Station-Id": "Client MAC",
    "RADIUS:IETF:NAS-IP-Address": "NAS IP Address",
    "RADIUS:IETF:NAS-Identifier": "NAS Identifier",
    "RADIUS:IETF:Service-Type": "RADIUS Service Type",
    "RADIUS:IETF:User-Name": "RADIUS Username",
    "RADIUS:IETF:Framed-IP-Address": "Framed IP",
    "RADIUS:IETF:NAS-Port": "NAS Port",
    "RADIUS:IETF:Acct-Status-Type": "Accounting Status",
    "RADIUS:IETF:Class": "RADIUS Class",

    # ── Aruba RADIUS VSA (full namespace) ───────────────────────────────────
    "RADIUS:Aruba:Aruba-Essid-Name": "SSID Name",
    "RADIUS:Aruba:Aruba-Port-Id": "Port ID",
    "RADIUS:Aruba:Aruba-Device-Type": "Device Type",
    "RADIUS:Aruba:Aruba-AP-Group": "AP Group",
    "RADIUS:Aruba:Aruba-Location-Id": "Location ID",
    "RADIUS:Aruba:Aruba-AP-Name": "AP Name",
    "RADIUS:Aruba:Aruba-User-Role": "User Role",
    "RADIUS:Aruba:Aruba-MPSK-Passphrase": "MPSK Passphrase",

    # ── Active Directory ─────────────────────────────────────────────────────
    "AD:memberOf": "AD Group Member",
    "AD:displayName": "AD Display Name",
    "AD:department": "AD Department",
    "AD:title": "AD Job Title",
    "AD:company": "AD Company",
    "AD:userAccountControl": "AD Account Control",
    "AD:mail": "AD Email",
    "AD:sAMAccountName": "AD Username",
    "AD:userPrincipalName": "AD UPN",
    "AD:distinguishedName": "AD Distinguished Name",
    "AD:msNPAllowDialin": "AD Dial-in Permission",
    "AD:description": "AD Description",
    "AD:physicalDeliveryOfficeName": "AD Office",
    "AD:telephoneNumber": "AD Phone",
    "AD:mobile": "AD Mobile",
    "AD:employeeID": "AD Employee ID",
    "AD:manager": "AD Manager",

    # ── Endpoint ─────────────────────────────────────────────────────────────
    "Endpoint:Category": "Device Category",
    "Endpoint:Family": "Device Family",
    "Endpoint:Name": "Device Name",
    "Endpoint:Device-Name": "Device Name",
    "Endpoint:OS-Type": "Operating System",
    "Endpoint:OS-Version": "OS Version",
    "Endpoint:IP-Address": "Endpoint IP",
    "Endpoint:MAC-Address": "Endpoint MAC",
    "Endpoint:Status": "Endpoint Status",
    "Endpoint:BYODRegStatus": "BYOD Registration",
    "Endpoint:DeviceProfile": "Device Profile",
    "Endpoint:Network": "Network Segment",
    "Endpoint:Source": "Endpoint Source",
    "Endpoint:Enabled": "Endpoint Enabled",
    "Endpoint:Updated-At": "Last Updated",
    "Endpoint:Added-At": "First Seen",

    # ── Host / posture ───────────────────────────────────────────────────────
    "Host:Name": "Host Name",
    "Host:FQDN": "FQDN",
    "Host:OS-Version": "Host OS Version",
    "Host:CheckType": "Posture Check Type",
    "Host:Domain": "Host Domain",

    # ── Connection / NAD ────────────────────────────────────────────────────
    "Connection:Protocol": "Connection Protocol",
    "Connection:Client-IP-Address": "Client IP",
    "Connection:Server-IP-Address": "Server IP",
    "Connection:Server-Port": "Server Port",
    "Connection:NAD-IP-Address": "NAD IP",
    "Connection:NAS-Port-Type": "NAS Port Type",

    # ── Certificate ─────────────────────────────────────────────────────────
    "Certificate:Subject-CN": "Cert Subject CN",
    "Certificate:Subject-O": "Cert Organization",
    "Certificate:Subject-OU": "Cert OU",
    "Certificate:Issuer-CN": "Cert Issuer",
    "Certificate:Serial-Number": "Cert Serial",
    "Certificate:Expiry-Date": "Cert Expiry",
    "Certificate:SAN-Email": "Cert Email SAN",
    "Certificate:SAN-DNS": "Cert DNS SAN",
    "Certificate:SAN-UPN": "Cert UPN SAN",
    "Certificate:Template": "Cert Template",

    # ── Local User ──────────────────────────────────────────────────────────
    "LocalUser:Name": "Local Username",
    "LocalUser:Email": "Local Email",
    "LocalUser:Role": "Local User Role",
    "LocalUser:Enabled": "Account Enabled",
    "LocalUser:Title": "User Title",
    "LocalUser:Company": "Company",
    "LocalUser:Department": "Department",
    "LocalUser:Phone": "Phone",

    # ── Guest User ──────────────────────────────────────────────────────────
    "GuestUser:UserName": "Guest Username",
    "GuestUser:Email": "Guest Email",
    "GuestUser:Sponsor": "Sponsor",
    "GuestUser:Enabled": "Guest Enabled",
    "GuestUser:Role": "Guest Role",

    # ── ClearPass internal (Tips) ────────────────────────────────────────────
    "Tips:Role": "ClearPass Role",
    "Tips:Posture": "Posture Status",

    # ── TACACS ──────────────────────────────────────────────────────────────
    "TACACS:service": "TACACS Service",
    "TACACS:protocol": "TACACS Protocol",
    "TACACS:cmd": "TACACS Command",
    "TACACS:cmd-arg": "TACACS Command Arg",
}

# ---------------------------------------------------------------------------
# Operator display mapping
# ---------------------------------------------------------------------------

_OP_DISPLAY: dict[str, str] = {
    "EQUALS": "=",
    "NOT_EQUALS": "≠",
    "CONTAINS": "contains",
    "NOT_CONTAINS": "not contains",
    "STARTS_WITH": "starts with",
    "ENDS_WITH": "ends with",
    "MATCHES_REGEX": "matches",
    "GREATER_THAN": ">",
    "LESS_THAN": "<",
    "GREATER_THAN_OR_EQUALS": "≥",
    "LESS_THAN_OR_EQUALS": "≤",
    "BELONGS_TO": "in",
    "EXISTS": "exists",
    "NOT_EXISTS": "not exists",
}

_OPERATORS = sorted(_OP_DISPLAY.keys(), key=len, reverse=True)  # longest first to avoid partial matches


def translate_attribute(attr: str) -> tuple[str, bool]:
    """Return ``(human_label, is_translated)``.

    ``is_translated=False`` means the attribute is not in the table and should
    be flagged in the UI so a translation can be added later.
    """
    if attr in ATTR_LABELS:
        return ATTR_LABELS[attr], True

    # Graceful fallback: strip namespace prefix and clean up
    for prefix in ("RADIUS:IETF:", "RADIUS:Aruba:", "Authentication:",
                   "Endpoint:", "Certificate:", "LocalUser:", "GuestUser:",
                   "Connection:", "Host:", "AD:", "Tips:", "TACACS:"):
        if attr.startswith(prefix):
            remainder = attr[len(prefix):]
            # Convert-case: "NAS-Port-Type" → "NAS Port Type"
            human = remainder.replace("-", " ").replace("_", " ").strip()
            return human, False

    return attr, False


def humanize_condition(condition: str) -> tuple[str, str, str, bool]:
    """Parse ``"Attr OPERATOR Value"`` into human-readable parts.

    Returns ``(human_attr, op_display, value, is_fully_translated)``.

    ``is_fully_translated=False`` signals the UI to flag this condition for
    a translation addition.
    """
    for op in _OPERATORS:
        marker = f" {op} "
        idx = condition.find(marker)
        if idx != -1:
            attr = condition[:idx].strip()
            value = condition[idx + len(marker):].strip()
            human_attr, translated = translate_attribute(attr)
            op_sym = _OP_DISPLAY.get(op, op)
            return human_attr, op_sym, value, translated

    # Single-token operators (EXISTS, NOT_EXISTS)
    for op in ("EXISTS", "NOT_EXISTS"):
        if condition.strip().endswith(f" {op}") or condition.strip() == op:
            attr = condition.replace(f" {op}", "").strip()
            human_attr, translated = translate_attribute(attr)
            return human_attr, _OP_DISPLAY.get(op, op), "", translated

    # No operator found — return as-is, no flagging needed
    return condition, "", "", True


def make_question_label(condition_str: str) -> tuple[str, bool]:
    """Convert a ClearPass condition expression to a question label.

    Returns ``(label, needs_translation)`` where ``needs_translation=True``
    means at least one attribute was not in the translation table.
    """
    if not condition_str:
        return "Condition?", False

    # Handle AND-joined conditions (show first + count)
    parts = [p.strip() for p in condition_str.split(" AND ") if p.strip()]
    extra = len(parts) - 1

    h_attr, op_sym, value, translated = humanize_condition(parts[0])

    if op_sym and value:
        label = f'{h_attr} {op_sym} "{value}"'
    elif op_sym:
        label = f"{h_attr} {op_sym}"
    else:
        label = h_attr

    if extra > 0:
        label += f"  (+{extra} more)"

    return label + "?", not translated
