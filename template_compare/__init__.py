"""Compare a design PDF with a template PDF.

``render``, ``spans`` and ``bands`` are imported from ``original/comp.py`` and used
as written. The markup drawing is adapted from ``build`` in ``original/markup2.py``.
The side by side drawing is adapted from ``draw_pair`` in ``original/v3.py``.
Trim detection, element detection, matching, measurement, the service, and the
optional model step are new.
"""

from template_compare.engine import compare

__all__ = ["compare"]
__version__ = "1.0.0"
