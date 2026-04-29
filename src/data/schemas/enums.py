"""Enumerations shared across the unified CAE data schema."""

from enum import Enum


class SourceTool(str, Enum):
    """CAE simulation tools supported by the platform."""

    MOLDEX3D = "moldex3d"
    ANIFORM = "aniform"
    DIGIMAT = "digimat"
    ABAQUS = "abaqus"
    SIMUTENCE = "simutence"
    CADFIL = "cadfil"


class SimulationType(str, Enum):
    """Types of CAE simulation analyses."""

    STRUCTURAL = "structural"
    FLOW = "flow"
    THERMAL = "thermal"
    FORMING = "forming"
    CURING = "curing"
    WINDING = "winding"
    MICROMECHANICS = "micromechanics"
    HOMOGENIZATION = "homogenization"
    PROCESS = "process"
    COUPLED = "coupled"
    DYNAMIC = "dynamic"
    FATIGUE = "fatigue"


class MaterialSystem(str, Enum):
    """Composite material system classifications."""

    CFRP = "cfrp"
    GFRP = "gfrp"
    SMC = "smc"
    BMC = "bmc"
    PREPREG = "prepreg"
    DRY_FIBER = "dry_fiber"
    THERMOPLASTIC = "thermoplastic"
    THERMOSET = "thermoset"
    SHORT_FIBER = "short_fiber"
    LONG_FIBER = "long_fiber"
    WOVEN = "woven"
    UNIDIRECTIONAL = "unidirectional"
    NCF = "ncf"  # Non-crimp fabric
    OTHER = "other"


class MeshType(str, Enum):
    """Types of geometric discretization."""

    STRUCTURED = "structured"
    UNSTRUCTURED = "unstructured"
    POINT_CLOUD = "point_cloud"
    SURFACE = "surface"
    RVE = "rve"  # Representative Volume Element


class ElementType(str, Enum):
    """Finite element types."""

    # 3D solid elements
    TET4 = "tet4"
    TET10 = "tet10"
    HEX8 = "hex8"
    HEX20 = "hex20"
    WEDGE6 = "wedge6"
    WEDGE15 = "wedge15"
    # 2D shell/plate elements
    TRI3 = "tri3"
    TRI6 = "tri6"
    QUAD4 = "quad4"
    QUAD8 = "quad8"
    # 1D elements
    BEAM2 = "beam2"
    BEAM3 = "beam3"
    # Special
    COHESIVE = "cohesive"
    CONTINUUM_SHELL = "continuum_shell"


class BCType(str, Enum):
    """Boundary condition types."""

    DISPLACEMENT = "displacement"
    FORCE = "force"
    PRESSURE = "pressure"
    TEMPERATURE = "temperature"
    HEAT_FLUX = "heat_flux"
    CONVECTION = "convection"
    SYMMETRY = "symmetry"
    CONTACT = "contact"
    INLET = "inlet"
    OUTLET = "outlet"
    WALL = "wall"


class UnitSystem(str, Enum):
    """Unit system. All data in the unified schema is stored in SI."""

    SI = "si"
    MM_TON_S = "mm_ton_s"  # Abaqus common: mm, tonne, s, MPa
    CGS = "cgs"
