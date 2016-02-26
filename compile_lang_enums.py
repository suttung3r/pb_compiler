from enum import Enum, unique

@unique
class SUPPORTED_LANGUAGES(Enum):
  C = 0,
  CPP = 1,
  PYTHON = 2,
  RUST = 3,
  NONE = -1
