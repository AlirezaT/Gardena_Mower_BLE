"""Independently worded help following app 9.2.0's verified error branches.

Informational messages are not movement instructions. No action is executed here.
The manufacturer app/manual remains authoritative for physical service procedures.
"""

TITLES = {
    1: "Outside working area", 2: "No loop signal",
    4: "Front loop sensor problem", 5: "Rear loop sensor problem",
    6: "Left loop sensor problem", 7: "Right loop sensor problem",
    9: "Mower trapped", 10: "Mower upside down", 11: "Battery low",
    12: "Battery empty", 13: "No drive", 14: "Mower temporarily lifted",
    15: "Mower lifted", 16: "Stuck in charging station", 17: "Charging station blocked",
    18: "Rear collision sensor error", 19: "Front collision sensor error",
    20: "Right drive wheel blocked", 21: "Left drive wheel blocked",
    26: "Invalid sub-device combination", 27: "Settings reset", 28: "Electronic problem",
    29: "Slope too steep", 30: "Charging system error", 31: "Stop button problem",
    32: "Tilt sensor problem", 33: "Mower tilted", 35: "Left wheel motor overload",
    36: "Right wheel motor overload", 37: "Charging current too high",
    48: "No response from charger", 49: "Ultrasonic sensor problem",
    50: "Guide wire not found", 53: "GPS module error",
    56: "Guide calibration successful", 57: "Guide calibration failed",
    58: "Temporary battery problem", 66: "Invalid battery",
    69: "Alarm: mower switched off", 70: "Alarm: mower stopped",
    71: "Alarm: mower lifted", 72: "Alarm: mower tilted",
    75: "Charging station communication successful", 76: "Connection not changed",
    78: "Wheels slipping", 80: "Cutting system imbalance", 81: "Safety function",
    88: "Angle sensor problem", 89: "Invalid system configuration",
    90: "No power at charging station", 92: "Invalid map", 93: "No position",
    105: "Lift sensor problem", 106: "Collision sensor problem", 109: "Loop sensor problem",
    110: "Collision", 118: "Charging system problem", 119: "ZoneProtect battery depleted",
    123: "Destination unreachable", 124: "Destination blocked",
    125: "Battery needs replacement", 126: "Battery needs replacement",
    127: "Battery problem", 129: "Edge cutting disc blocked",
    130: "Edge cutting disc imbalance", 134: "Invalid software configuration",
    135: "Anti-collision radar error", 143: "Accessory port power issue",
    144: "Boundary wire issue", 1000001: "Mower locked", 1000002: "Safety stop",
    1000003: "Mower locked",
}
TITLE_ALIASES = {
    22: 20, 23: 21, 25: 24, 34: 29, 51: 50, 52: 50, 67: 66, 112: 80,
    **{code: 40 for code in range(41, 48)},
    **{code: 58 for code in (*range(59, 66), 68)},
}
TITLES.update({24: "Cutting system blocked", 40: "Cutting height blocked"})
TITLES.update({code: TITLES[source] for code, source in TITLE_ALIASES.items()})

RESTART = "Use the mower's physical power button to switch it off, wait briefly, then restart as described in its manual. If the fault returns, contact authorised support."
SAFE = "Before inspecting wheels, blades, the body or electrical connections, stop and fully switch off the mower; follow the model's maintenance instructions. Do not bypass safety devices."
HELP = {
    1: "Check left/right boundary connections, island-wire direction, required edge clearances and slope limits. Nearby metal or buried cables can interfere with the loop; review the installation if the fault repeats.",
    2: "Check the station LED first. With a green LED, review initial pairing and whether Eco mode prevented a start away from the station. Otherwise inspect station power, low-voltage cable, boundary connections, damage, island direction and nearby interference. Pairing or a manual start must be a separate supervised action, not an automatic recovery.",
    9: "Clear obstructions. Repeated trapping at the same narrow or angled location calls for an installation review.",
    10: "With the mower stopped, return it upright to level lawn inside the working area.",
    12: "Check that the guide is intact and connected. A mower left in a secondary area may need to be returned to the main charging station.",
    13: "Free the mower and check traction. Review guide routing across slopes and exclude terrain steeper than the model's permitted limit.",
    14: "Place every wheel on the lawn. Remove obstructions and accumulated grass beneath the housing using the safe maintenance procedure.",
    16: "Clear anything preventing the mower from leaving the charging station.",
    17: "Clear the station approach, inspect and clean the charging contacts as instructed, and check that the station is level.",
    18: "Check that the outer body can move freely on the chassis and remove trapped debris. Only remove covers as permitted by the model's manual.",
    20: "Inspect the affected drive wheel and safely remove the obstruction.",
    24: "With power off, clear the cutting-system obstruction. Move a mower standing in water to a dry location and address the drainage problem before using it again.",
    29: "Exclude the excessive slope from the work area using the installation method specified for this model.",
    33: "Return the stopped mower upright to the lawn. Repeated tilting requires checking guide routing and slopes.",
    35: "Free the affected wheel. If wet grass is causing poor traction, wait for the lawn to dry.",
    37: "Verify that the correct power supply is fitted and that the station is undamaged. Use the manual's restart procedure; seek service if the fault recurs.",
    38: "Restart using the physical controls and check for an approved firmware update. Persistent communication faults need authorised service.",
    39: "Switch off the mower, inspect the cutting system and check that the blades can move freely. Safely remove any obstruction.",
    40: "Switch off the mower and inspect the height-adjustment mechanism and blade disc for obstructions.",
    48: "Check station power and its LED. If pairing is faulty, a separately supervised new-loop procedure may be needed with the mower docked; do not regenerate the loop automatically.",
    50: "Inspect guide connections at the station and boundary junction, including fully seated couplers. Locate and repair damaged wire using the approved connectors.",
    53: "Allow the connection to recover. For recurring faults, dock the mower and follow the restart procedure.",
    57: "Check the guide-to-boundary clearance near the station starting point; the reviewed app specifies at least 60 cm. Confirm the installation requirement in your model's manual.",
    58: "Follow the restart procedure. Allow an overheated mower to cool in shade; observe the manual's cold-weather and winter-storage limits.",
    69: "Acknowledge the alarm by entering your own mower PIN through the physical controls. Do not bypass the alarm or change security settings as a workaround.",
    76: "Inspect the boundary/guide connections and confirm a healthy station LED before a separately requested retry.",
    78: "Review traction and guide routing across slopes; exclude terrain beyond the model's rated slope limit.",
    80: "With power off, inspect blade and screw wear, damage and correct installation. Replace parts only using the model's approved maintenance procedure.",
    81: "Follow the physical restart procedure once. If the safety fault returns, stop using the mower and obtain authorised service.",
    90: "Check station mains power, the correct undamaged power supply and clean charging contacts. Do not work on live electrical connections.",
    110: "Clear obstacles. If none are present, inspect wheel movement and body freedom on the chassis and clean accumulated debris according to the manual.",
    119: "Check the ZoneProtect accessory itself: charge its battery through its USB port as instructed. The reviewed app identifies flashing orange as charging and steady orange as charged. If overheated, let the accessory cool before reuse.",
    123: "Review the work-area installation: it must contain a reachable guide or boundary route. Check whether a stay-out zone blocks access. Only change zones deliberately after reviewing their purpose.",
    124: "Remove the obstacle preventing access to the destination.",
    125: "The battery may be reaching end of life. Arrange replacement with the correct approved battery and follow the service instructions.",
    126: "Arrange replacement of the mower battery using the approved part and service procedure.",
    127: "Stop using the mower and arrange prompt battery replacement through the approved service procedure.",
    129: "Fully switch off the mower before inspecting the edge disc. Follow the safe handling procedure and remove trapped grass or foreign objects.",
    134: "Contact authorised support about the required software configuration/update.",
    135: "Check whether radar is actually fitted and correctly seated. If deliberately removed, review the accessory setting in the app; otherwise check the installation and approved firmware. This advice does not enable radar on unsupported models.",
    143: "With the product switched off, inspect and reconnect the accessory connector according to the manual, then restart. Seek service if the power fault returns.",
    144: "Inspect the boundary connection at the station, all splices and the wire for damage; repair only with approved connectors.",
}
for _code in (4, 5, 6, 7, 26, 28, 30, 32, 49, 66, 88, 89, 92, 93, 105, 106, 109, 118):
    HELP[_code] = RESTART
BODY_ALIASES = {
    15: 14, 19: 18, 21: 20, 22: 20, 23: 20, 25: 24, 34: 29,
    36: 35, 41: 40, 51: 50, 52: 50, 67: 66, 70: 69, 71: 69, 72: 69,
    112: 80, 130: 80, **{code: 58 for code in (*range(59, 66), 68)},
}
HELP.update({code: HELP[source] for code, source in BODY_ALIASES.items()})
ACKNOWLEDGE_CODES = frozenset((1, 9, 10, 12, 13, 15, 16, 17, 18, 19, 20, 21,
    22, 23, 24, 25, 26, 29, 31, 32, 33, 34, 35, 36, 38, 39, 50, 51, 52, 53,
    69, 70, 71, 72, 78, 81, 89, 105, 106, 109, 110, 123, 124, 126, 129, 134))


def error_title(code, capabilities):
    """App title branches; unverified guide arrangements retain generic wording."""
    if code in (51, 52) and 3 in capabilities.wire_ids:
        return f"Guide wire {code - 49} not found"
    return TITLES.get(code)


def error_guidance(code, capabilities):
    """Return conservative, model-aware human guidance; never execute recovery."""
    if type(code) is not int or code == 0:
        return ()
    if capabilities.platform == "unknown":
        return ("Use the manufacturer app/manual for this unrecognised model and error code.",)
    if code in (1000001, 1000003):
        keypad = "symbol sequence" if capabilities.platform in ("P005", "P005GA") else "PIN"
        return (f"Use the physical keypad to enter your own {keypad} and confirm with OK. If the PIN is unknown, use the manufacturer's ownership-verification recovery process.",)
    if code == 1000002:
        control = "Play and the desired operating mode" if capabilities.generation == 3 else "the desired operating mode"
        return (f"A physical safety stop requires local attention. After checking the area is safe, select {control} and confirm on the mower. Do not bypass STOP or PIN checks.",)
    steps = [HELP[code]] if code in HELP else []
    if code == 2 and capabilities.generation == 3:
        steps.append("On generation 3, the app also offers loop setup through the mower's Security menu; this remains a separate supervised operation.")
    if code in ACKNOWLEDGE_CODES and not (code == 12 and capabilities.generation == 3):
        steps.append("After resolving the cause and checking the area is safe, acknowledge the error on the mower and select an operating mode." if capabilities.generation == 3 else "After resolving the cause and checking the area is safe, use the physical STOP control, then select an operating mode on the mower.")
    if steps:
        return (SAFE, *steps)
    if code in (11, 27, 56, 75):
        return ("Status/information message; review the mower and app. No automatic corrective action is required by this integration.",)
    return ("No specific reviewed recovery procedure is available for this code. Consult the manufacturer app or authorised support.",)
