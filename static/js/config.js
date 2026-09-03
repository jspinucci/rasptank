const CONFIG = {
    // A1
    deadzone: 0.15,
    minTorque: 0.45,

    // A2 (light smoothing)
    smoothingAccel: 0.20,

    // A3/A4 (mild steering curve)
    steeringExpoStrength: 1.0,
    steeringDualRateBlend: 1.0,

    // A5 (mild throttle curve)
    throttleCurveStrength: 0.50,

    // A6 (mild traction control)
    slipLimit: 0.10,

    // A7 (mild turn compensation)
    turnCompStrength: 0.40,

    // A8 (mild torque bias)
    torqueBiasStrength: 0.20,
    maxTurn: 1.0,

    // A9 (mild inertia)
    inertiaMass: 0.05,
    inertiaDrag: 0.10
};
