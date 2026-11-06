"""One revision for geometry and quantities. The preview and the gated planning output both use it."""
import hashlib, json

# Bump when the geometry or takeoff math changes, so the same inputs then get a new revision.
# 2: the warning surface is capped at the ramp length.
MODEL_VERSION = 2


def revision(basis_version, inputs, assumptions) -> str:
    """Hash everything the quantities depend on: the dimensions, the assumptions actually used and the
    version of the geometry and takeoff code. Same basis, same revision."""
    fingerprint = dict(basis_version=basis_version, inputs=inputs, assumptions=assumptions)
    return hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()[:8]
