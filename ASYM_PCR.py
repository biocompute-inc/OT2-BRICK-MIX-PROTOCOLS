import json
from opentrons import protocol_api, types

metadata = {
    "protocolName": "ASYM PCR",
    "created": "2025-12-31T01:43:59.024Z",
    "internalAppBuildDate": "Tue, 16 Dec 2025 16:02:03 GMT",
    "lastModified": "2025-12-31T01:48:38.792Z",
    "protocolDesigner": "8.7.1",
    "source": "Protocol Designer",
}

requirements = {"robotType": "OT-2", "apiLevel": "2.27"}

def run(protocol: protocol_api.ProtocolContext) -> None:
    # Load Modules:
    thermocycler_module_1 = protocol.load_module("thermocyclerModuleV1", "7")

    # Load Labware:
    tip_rack_1 = protocol.load_labware(
        "opentrons_96_tiprack_10ul",
        location="2",
        namespace="opentrons",
        version=1,
    )

    # Load Pipettes:
    pipette_left = protocol.load_instrument("p10_single", "left")

    # PROTOCOL STEPS

    # Step 1: thermocycler
    thermocycler_module_1.open_lid()
    thermocycler_module_1.set_lid_temperature(103)

    # Step 2: thermocycler
    thermocycler_module_1.close_lid()
    thermocycler_module_1.execute_profile(
        [
            {"temperature": 94, "hold_time_seconds": 300},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 94, "hold_time_seconds": 30},
            {"temperature": 60, "hold_time_seconds": 30},
            {"temperature": 72, "hold_time_seconds": 60},
            {"temperature": 75, "hold_time_seconds": 600},
        ],
        1,
        block_max_volume=50,
    )
    thermocycler_module_1.set_block_temperature(25)
    thermocycler_module_1.deactivate_lid()

DESIGNER_APPLICATION = """{"robot":{"model":"OT-2 Standard"},"designerApplication":{"name":"opentrons/protocol-designer","version":"8.7.0","data":{"pipetteTiprackAssignments":{"9d8c5031-e5d5-4092-9f97-6a7bf21d1bb7":["opentrons/opentrons_96_tiprack_10ul/1"]},"dismissedWarnings":{"form":[],"timeline":[]},"ingredients":{},"ingredLocations":{},"savedStepForms":{"__INITIAL_DECK_SETUP_STEP__":{"stepType":"manualIntervention","id":"__INITIAL_DECK_SETUP_STEP__","labwareLocationUpdate":{"5c748670-825b-4d33-ab3d-88bae2767ef8:opentrons/opentrons_96_tiprack_10ul/1":"2"},"pipetteLocationUpdate":{"9d8c5031-e5d5-4092-9f97-6a7bf21d1bb7":"left"},"moduleLocationUpdate":{"bd0fe333-50b1-40b3-aec6-6801f4a20be7:thermocyclerModuleType":"7"},"trashBinLocationUpdate":{"a8c43487-62ac-4808-b8ef-323a02a2eded:trashBin":"cutout12"},"wasteChuteLocationUpdate":{},"stagingAreaLocationUpdate":{},"gripperLocationUpdate":{}},"4dc74a53-d9ce-4825-ae2e-7d5bf79f2d34":{"id":"4dc74a53-d9ce-4825-ae2e-7d5bf79f2d34","stepType":"thermocycler","stepName":"thermocycler","stepDetails":"","stepNumber":0,"blockIsActive":false,"blockIsActiveHold":false,"blockTargetTemp":null,"blockTargetTempHold":null,"lidIsActive":true,"lidIsActiveHold":false,"lidOpen":true,"lidOpenHold":null,"lidTargetTemp":"103","lidTargetTempHold":null,"moduleId":"bd0fe333-50b1-40b3-aec6-6801f4a20be7:thermocyclerModuleType","orderedProfileItems":[],"profileItemsById":{},"profileTargetLidTemp":null,"profileVolume":null,"thermocyclerFormType":"thermocyclerState"},"a7bae2af-fc34-4cae-b256-905f2edcb1f9":{"id":"a7bae2af-fc34-4cae-b256-905f2edcb1f9","stepType":"thermocycler","stepName":"thermocycler","stepDetails":"","stepNumber":0,"blockIsActive":false,"blockIsActiveHold":true,"blockTargetTemp":null,"blockTargetTempHold":"25","lidIsActive":false,"lidIsActiveHold":false,"lidOpen":false,"lidOpenHold":false,"lidTargetTemp":null,"lidTargetTempHold":null,"moduleId":"bd0fe333-50b1-40b3-aec6-6801f4a20be7:thermocyclerModuleType","orderedProfileItems":["261b6065-7358-4bf4-938d-456cc8dd2dbb","d7eab2f4-cf39-4218-bf89-c1867c4cb100","064b17f3-7df8-4524-a778-2d3f6bbdd3e6"],"profileItemsById":{"261b6065-7358-4bf4-938d-456cc8dd2dbb":{"durationMinutes":"05","durationSeconds":"00","id":"261b6065-7358-4bf4-938d-456cc8dd2dbb","temperature":"94","title":"1","type":"profileStep"},"d7eab2f4-cf39-4218-bf89-c1867c4cb100":{"id":"d7eab2f4-cf39-4218-bf89-c1867c4cb100","title":"","steps":[{"durationMinutes":"00","durationSeconds":"30","id":"c98d6282-9e12-45fa-a74e-447c3613d26f","temperature":"94","title":"2","type":"profileStep"},{"durationMinutes":"00","durationSeconds":"30","id":"8739266b-ec49-4b17-8ea5-293bebca1570","temperature":"60","title":"3","type":"profileStep"},{"durationMinutes":"01","durationSeconds":"00","id":"d1bff6e2-97ec-43c0-9069-37ea58261975","temperature":"72","title":"4","type":"profileStep"}],"type":"profileCycle","repetitions":"30"},"064b17f3-7df8-4524-a778-2d3f6bbdd3e6":{"durationMinutes":"10","durationSeconds":"00","id":"064b17f3-7df8-4524-a778-2d3f6bbdd3e6","temperature":"75","title":"5","type":"profileStep"}},"profileTargetLidTemp":"103","profileVolume":"50","thermocyclerFormType":"thermocyclerProfile"}},"orderedStepIds":["4dc74a53-d9ce-4825-ae2e-7d5bf79f2d34","a7bae2af-fc34-4cae-b256-905f2edcb1f9"],"pipettes":{"9d8c5031-e5d5-4092-9f97-6a7bf21d1bb7":{"pipetteName":"p10_single"}},"modules":{"bd0fe333-50b1-40b3-aec6-6801f4a20be7:thermocyclerModuleType":{"model":"thermocyclerModuleV1"}},"labware":{"5c748670-825b-4d33-ab3d-88bae2767ef8:opentrons/opentrons_96_tiprack_10ul/1":{"displayName":"Opentrons OT-2 96 Tip Rack 10 µL","labwareDefURI":"opentrons/opentrons_96_tiprack_10ul/1"}}}},"metadata":{"protocolName":"ASYM PCR","author":"","description":"","source":"Protocol Designer","created":1767145439024,"lastModified":1767145718792}}"""
