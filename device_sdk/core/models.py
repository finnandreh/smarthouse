from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class DeviceDescriptor:
    """Canonical device identity and capability description used by SDK clients."""

    id: str
    house: str
    type: str
    protocol: str
    capabilities: List[str] = field(default_factory=list)

    def to_registry_payload(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "house": self.house,
            "type": self.type,
            "protocol": self.protocol,
            "capabilities": self.capabilities,
        }
