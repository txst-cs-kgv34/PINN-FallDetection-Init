"""Azure Kinect joint definitions and the documented segment-mass CoM model."""

import numpy as np

NAMES = [
    "pelvis",
    "spine_navel",
    "spine_chest",
    "neck",
    "clavicle_left",
    "shoulder_left",
    "elbow_left",
    "wrist_left",
    "hand_left",
    "handtip_left",
    "thumb_left",
    "clavicle_right",
    "shoulder_right",
    "elbow_right",
    "wrist_right",
    "hand_right",
    "handtip_right",
    "thumb_right",
    "hip_left",
    "knee_left",
    "ankle_left",
    "foot_left",
    "hip_right",
    "knee_right",
    "ankle_right",
    "foot_right",
    "head",
    "nose",
    "eye_left",
    "ear_left",
    "eye_right",
    "ear_right",
]
PARENTS = [
    -1,
    0,
    1,
    2,
    2,
    4,
    5,
    6,
    7,
    8,
    7,
    2,
    11,
    12,
    13,
    14,
    15,
    14,
    0,
    18,
    19,
    20,
    0,
    22,
    23,
    24,
    3,
    26,
    26,
    26,
    26,
    26,
]
LIMBS = {
    "upper_arm_left": (5, 6),
    "forearm_left": (6, 7),
    "upper_arm_right": (12, 13),
    "forearm_right": (13, 14),
    "thigh_left": (18, 19),
    "shank_left": (19, 20),
    "thigh_right": (22, 23),
    "shank_right": (23, 24),
}
LEFT = {4, 5, 6, 7, 8, 9, 10, 18, 19, 20, 21}
RIGHT = {11, 12, 13, 14, 15, 16, 17, 22, 23, 24, 25}
COLORS = ["#176D8A", "#D07326", "#6774AD", "#24865D", "#A14568"]
SOURCES = {
    "joints": "https://learn.microsoft.com/en-us/previous-versions/azure/kinect-dk/body-joints",
    "axes": "https://learn.microsoft.com/en-us/previous-versions/azure/kinect-dk/coordinate-systems",
    "parameters": "https://www.has-motion.com/wiki/doku.php?id=visual3d:documentation:definitions:adjusted_zatsiorsky-seluyanov_s_segment_inertia_parameters",
    "paper": "https://doi.org/10.1016/0021-9290(95)00178-6",
}


def segment_model(sex="male"):
    if sex not in ("male", "female"):
        raise ValueError("sex must be male or female for the adult coefficient model")
    # Male mass fractions and proximal fractions as listed in the cited Visual3D
    # implementation table. HEAD, HAND, FOOT and NECK are SDK landmark proxies.
    # The shank fraction in that table is 0.4395; other implementations use
    # 0.4459. This difference is explicitly quantified, not silently reconciled.
    s = [
        dict(
            name="head",
            mass_fraction=0.0694,
            a=[26],
            b=[26],
            fraction=0.0,
            mapping="SDK HEAD point proxy; no vertex/neck anatomical head segment",
        ),
        dict(
            name="trunk",
            mass_fraction=0.4346,
            a=[3],
            b=[18, 22],
            fraction=0.5138,
            mapping="NECK to midpoint(HIP_LEFT,HIP_RIGHT); NECK approximates proximal trunk landmark",
        ),
    ]
    for side, upper, fore, hand, thigh, shank, foot in [
        ("left", (5, 6), (6, 7), 8, (18, 19), (19, 20), (20, 21)),
        ("right", (12, 13), (13, 14), 15, (22, 23), (23, 24), (24, 25)),
    ]:
        for name, pair, mass, fraction in [
            ("upper_arm", upper, 0.0271, 0.5772),
            ("forearm", fore, 0.0162, 0.4574),
            ("thigh", thigh, 0.1416, 0.4095),
            ("shank", shank, 0.0433, 0.4395),
        ]:
            s.append(
                dict(
                    name=f"{name}_{side}",
                    mass_fraction=mass,
                    a=[pair[0]],
                    b=[pair[1]],
                    fraction=fraction,
                    mapping="SDK joint centers approximate anatomical endpoints",
                )
            )
        s.append(
            dict(
                name="hand_" + side,
                mass_fraction=0.0061,
                a=[hand],
                b=[hand],
                fraction=0.0,
                mapping="SDK HAND point proxy, not published wrist-to-finger CoM fraction",
            )
        )
        s.append(
            dict(
                name="foot_" + side,
                mass_fraction=0.0137,
                a=[foot[0]],
                b=[foot[1]],
                fraction=0.5,
                mapping="ANKLE/FOOT midpoint proxy; heel and toe landmarks unavailable",
            )
        )
    if sex == "female":
        # Female source coefficients; HEAD/HAND/FOOT retain the same SDK proxies.
        female = {
            "head": (0.0668, 0.0),
            "trunk": (0.4257, 0.4964),
            "upper_arm": (0.0255, 0.5754),
            "forearm": (0.0138, 0.4559),
            "hand": (0.0056, 0.0),
            "thigh": (0.1478, 0.3612),
            "shank": (0.0481, 0.4352),
            "foot": (0.0129, 0.5),
        }
        for segment in s:
            base = segment["name"].removesuffix("_left").removesuffix("_right")
            segment["mass_fraction"], segment["fraction"] = female[base]
    total = sum(segment["mass_fraction"] for segment in s)
    for segment in s:
        segment["reported_mass_fraction"] = segment["mass_fraction"]
        # Rounded female source fractions sum to 0.9999. Normalize to conserve mass.
        # Male coefficients remain numerically unchanged for regression compatibility.
        if sex == "female":
            segment["mass_fraction"] /= total
    return s


def com_proxy(x, segments):
    positions = np.stack(
        [
            (1 - s["fraction"]) * x[:, s["a"]].mean(1)
            + s["fraction"] * x[:, s["b"]].mean(1)
            for s in segments
        ],
        1,
    )
    weights = np.array([s["mass_fraction"] for s in segments])
    return (positions * weights[None, :, None]).sum(1), positions


def sensitivity(x, segments, base, sex="male"):
    variants = {}
    # Alternative landmark mappings, not confidence intervals or accuracy bounds.
    q = [dict(s) for s in segments]
    q[1]["a"] = [5, 12]
    variants["trunk_shoulder_midpoint"] = com_proxy(x, q)[0]
    q = [dict(s) for s in segments]
    q[0].update(a=[3], b=[26], fraction=0.5)
    variants["head_neck_midpoint"] = com_proxy(x, q)[0]
    q = [dict(s) for s in segments]
    for s in q:
        if s["name"].startswith("foot"):
            s["fraction"] = 1.0
    variants["foot_point"] = com_proxy(x, q)[0]
    if sex == "male":
        q = [dict(s) for s in segments]
        for s in q:
            if s["name"].startswith("shank"):
                s["fraction"] = 0.4459
        variants["shank_fraction_0p4459"] = com_proxy(x, q)[0]
    return {
        k: float(np.linalg.norm(v - base, axis=1).max()) for k, v in variants.items()
    }
