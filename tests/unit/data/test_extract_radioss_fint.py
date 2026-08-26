from io import StringIO

import pytest

from scripts.extract_radioss_fint import animation_number, parse_vtk_stream


def test_parses_dynamic_node_count_and_sums_selected_internal_forces() -> None:
    vtk = StringIO(
        """# vtk DataFile Version 3.0
TIME 1 1 double
0.5
POINT_DATA 3
SCALARS NODE_ID int 1
LOOKUP_TABLE default
10
20
30
VECTORS Internal_Forces float
1 2 3
4 5 6
7 8 9
"""
    )

    assert parse_vtk_stream(vtk, {10, 30}) == pytest.approx((0.5, 8.0, 10.0, 12.0))


def test_animation_number_rejects_unexpected_name() -> None:
    assert animation_number("coupon_xA011") == 11
    with pytest.raises(ValueError, match="numeric suffix"):
        animation_number("coupon_x.vtk")
