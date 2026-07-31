import copy
import re
from typing import Any, Dict, List
from epics import caget
import os
import slac_db.config
import yaml


def get_magnet_metadata(
    magnet_names: List[str] = [], method: callable = None, **kwargs
):
    # return a data structure of the form:
    # {
    #  mag-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  mag-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    if magnet_names and method:
        # Add any additional metadata fields here
        additional_fields = ["Element", "Effective Length (m)"]
        device_elements = method(magnet_names, additional_fields)
        # change field names and values to be in different format
        # if needed
        for magnet in device_elements:
            if "Effective Length (m)" in device_elements[magnet]:
                if device_elements[magnet]["Effective Length (m)"] == "":
                    device_elements[magnet]["Effective Length (m)"] = 0.0
                device_elements[magnet]["l_eff"] = round(
                    float(device_elements[magnet]["Effective Length (m)"]), 3
                )
                del device_elements[magnet]["Effective Length (m)"]
        return device_elements
    else:
        return {}


def get_screen_metadata(basic_screen_data: dict):
    # return a data structure of the form:
    # {
    #  scr-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  scr-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    from meme.names import list_pvs

    metadata = {}
    for mad_name, info in basic_screen_data.items():
        metadata[mad_name] = {}
        ctrl_name = info["controls_information"]["control_name"]
        flags = list_pvs(ctrl_name + "%INSTALLED")
        hardware = {}
        for i in flags:
            name = re.search("(?<=^" + ctrl_name + ":).*(?=INSTALLED)", i)
            if name is None:
                continue
            name = name.group(0)
            status = caget(i)
            if status is not None:
                hardware[name] = status

        metadata[mad_name]["hardware"] = hardware
    return metadata


def get_wire_metadata(basic_wire_data: dict) -> Dict[str, Dict[str, Any]]:
    """Load wire and area metadata, merge into per-wire dict.

    Args:
        basic_wire_data: {wire_name: {"metadata": {"area": ...}, ...}}

    Returns: {wire_name: {field: value, ...}}
    """
    here = slac_db.config.package_data()

    with open(os.path.join(here, "wire_area_metadata.yaml"), "r") as f:
        area_raw = yaml.safe_load(f)

    with open(os.path.join(here, "wire_metadata.yaml"), "r") as f:
        wire_raw = yaml.safe_load(f)

    result = {}
    for wire_name, info in basic_wire_data.items():
        area_name = info["metadata"]["area"]
        if area_name not in area_raw:
            continue
        entry = copy.deepcopy(area_raw[area_name])
        wire_overrides = wire_raw.get(wire_name, {})
        if wire_overrides:
            entry.update(wire_overrides)
        result[wire_name] = entry

    return result


def get_lblm_metadata(lblm_names: List[str] = []):
    # return a data structure of the form:
    # {
    #  lblm-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  lblm-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    if lblm_names:
        raise NotImplementedError("No method of getting additional metadata for lblms.")
    return {}


def get_bpm_metadata(bpm_names: List[str] = []):
    # return a data structure of the form:
    # {
    #  bpm-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  bpm-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    if bpm_names:
        raise NotImplementedError("No method of getting additional metadata for bpms.")
    return {}


def get_tcav_metadata(tcav_names: List[str] = [], method: callable = None, **kwargs):
    # return a data structure of the form:
    # {
    #  tcav-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  tcav-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    if tcav_names and method:
        # Add any additional metadata fields here
        additional_fields = [
            "Element",
            "Effective Length (m)",
            "Rf Frequency (MHz)",
        ]
        device_elements = method(tcav_names, additional_fields)
        # change field names and values to be in different format
        # if needed
        for tcav in device_elements:
            if "Effective Length (m)" in device_elements[tcav]:
                if device_elements[tcav]["Effective Length (m)"] == "":
                    device_elements[tcav]["Effective Length (m)"] = 0.0
                device_elements[tcav]["l_eff"] = round(
                    float(device_elements[tcav]["Effective Length (m)"]), 3
                )
                del device_elements[tcav]["Effective Length (m)"]

            if "Rf Frequency (MHz)" in device_elements[tcav]:
                if device_elements[tcav]["Rf Frequency (MHz)"] == "":
                    device_elements[tcav]["Rf Frequency (MHz)"] = 0.0
                device_elements[tcav]["rf_freq"] = float(
                    device_elements[tcav]["Rf Frequency (MHz)"]
                )
                del device_elements[tcav]["Rf Frequency (MHz)"]

        return device_elements
    else:
        return {}


def get_klystron_metadata() -> Dict[str, Dict[str, str]]:
    """Load klystron_metadata.yaml and return per-station accessor overrides.

    Returns a dict keyed by station name (e.g. 'K24_1') whose values are flat
    dicts mapping accessor_name -> cs_address for every PV override defined in
    klystron_metadata.yaml.

    Beamcode-specific sub-dicts (keys 'beamcode1', 'beamcode2') are expanded
    with a suffix, e.g. phase_act_pvname under beamcode1 becomes accessor
    'phase_actual_beamcode1'.

    The _pvname suffix is stripped and the remainder is used as the accessor
    name, with underscores replacing the trailing '_pvname':
        ampl_act_pvname  -> energy_gain (maps to lcls-live ampl_act)
        ampl_des_pvname  -> energy_gain_des
        phase_act_pvname -> phase_actual
        phase_des_pvname -> phase_desired
    Top-level empty-string values (e.g. accelerate_pvname: '') are stored as
    accessor_name -> '' so callers know the PV is absent.
    """
    _PV_FIELD_TO_ACCESSOR = {
        "ampl_act_pvname":   "energy_gain",
        "ampl_des_pvname":   "energy_gain_des",
        "phase_act_pvname":  "phase_actual",
        "phase_des_pvname":  "phase_desired",
        "accelerate_pvname": "accelerate",
        "swrd_pvname":       "swrd",
        "stat_pvname":       "stat",
        "hdsc_pvname":       "hdsc",
        "dsta_pvname":       "dsta",
    }

    here = slac_db.config.package_data()
    yaml_path = os.path.join(here, "klystron_metadata.yaml")
    with open(yaml_path) as f:
        raw = yaml.safe_load(f)

    result = {}
    for station, fields in raw.items():
        overrides = {}
        for key, val in fields.items():
            if key == "description":
                continue
            if key in ("beamcode1", "beamcode2"):
                bc = key  # e.g. "beamcode1"
                for pv_field, pv_val in val.items():
                    accessor = _PV_FIELD_TO_ACCESSOR.get(pv_field)
                    if accessor is not None:
                        overrides[f"{accessor}_{bc}"] = pv_val
            elif key in _PV_FIELD_TO_ACCESSOR:
                overrides[_PV_FIELD_TO_ACCESSOR[key]] = val or ""
            else:
                # passthrough (e.g. in_use)
                overrides[key] = val
        result[station] = overrides
    return result


def get_pmt_metadata(pmt_names: List[str] = []):
    # return a data structure of the form:
    # {
    #  pmt-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  pmt-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    pmt_metadata = {}

    here = slac_db.config.package_data()
    yaml_path = os.path.join(here, "pmt_metadata.yaml")

    with open(yaml_path, "r") as f:
        pmt_metadata = yaml.safe_load(f)

    return pmt_metadata
