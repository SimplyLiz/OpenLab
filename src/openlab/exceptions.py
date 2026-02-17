"""BioLab exceptions — merged from DNASyn."""


class BioLabError(Exception):
    """Base exception for BioLab."""


class ImportError_(BioLabError):
    """Raised when a file import fails."""


class ParseError(BioLabError):
    """Raised when a parser cannot process input."""


class NCBIError(BioLabError):
    """Raised when an NCBI fetch fails."""


class GeneNotFoundError(BioLabError):
    """Raised when a gene lookup fails."""


class HypothesisNotFoundError(BioLabError):
    """Raised when a hypothesis lookup fails."""
