"""Model-aware labels without inventing capacities or clock semantics."""

from automower_ble.error_codes import ErrorCodes
from .error_help import error_title


def describe_error(code, platform=None, capabilities=None):
    if type(code) is not int:
        return "Unknown error"
    if code == 0:
        return "No error"
    if platform == "P14" and code == 38:
        return "Connection to MCU lost"
    if capabilities is not None and capabilities.platform != "unknown":
        title = error_title(code, capabilities)
        if title:
            return title
    try:
        return ErrorCodes(code).name.replace("_", " ").title()
    except ValueError:
        return f"Unknown error ({code})"


def model_label(upstream_name, capabilities):
    if upstream_name and not upstream_name.startswith("Unknown Model"):
        return upstream_name
    if capabilities.platform == "unknown":
        return upstream_name
    family = {14: "SILENO city/life", 18: "SILENO life", 29: "SILENO minimo",
              43: "SILENO flex"}.get(capabilities.device_type)
    if capabilities.platform == "P14" and capabilities.brand == "gardena":
        family = {34: "SILENO pro", 35: "SILENO max", 36: "SILENO pro",
                  37: "SILENO max"}.get(capabilities.device_type)
    return (
        f"{family or capabilities.platform} "
        f"(type {capabilities.device_type}, variant {capabilities.variant})"
    )
