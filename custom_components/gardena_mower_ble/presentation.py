"""Model-aware labels without inventing capacities or clock semantics."""

from automower_ble.error_codes import ErrorCodes


def describe_error(code, platform=None):
    if type(code) is not int:
        return "Unknown error"
    if code == 0:
        return "No error"
    if platform == "P14" and code == 38:
        return "Connection to MCU lost"
    try:
        return ErrorCodes(code).name.replace("_", " ").title()
    except ValueError:
        return f"Unknown error ({code})"


def model_label(upstream_name, capabilities):
    if upstream_name and not upstream_name.startswith("Unknown Model"):
        return upstream_name
    if capabilities.platform == "unknown":
        return upstream_name
    return (
        f"{capabilities.platform} "
        f"(type {capabilities.device_type}, variant {capabilities.variant})"
    )
