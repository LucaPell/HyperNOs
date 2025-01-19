import sys

sys.path.append("..")

import numpy as np
import torch
from loss_fun_with_physics import (
    DarcyResidualAutograd,
    DarcyResidualFiniteDiff,
    HelmholtzResidualAutograd,
    HelmholtzResidualFiniteDiff,
    PoissonResidualAutograd,
    PoissonResidualFiniteDiff,
    SpatialDerivativesAutograd,
    SpatialDerivativesFiniteDiff,
)


#########################################
# Derivative with torch.autograd
#########################################
#### Test first-order derivatives in 1D
def test_first_order_1d_autograd():
    x = SpatialDerivativesAutograd().get_grid_1d([1, 10])  # batch_size, resolution_grid
    u = x**2

    u_x = SpatialDerivativesAutograd().first_order_1d(u, x)

    expected_u_x = 2 * x

    assert torch.allclose(u_x, expected_u_x, atol=1e-6)


#### Test second-order derivatives in 1D
def test_second_order_1d_autograd():
    x = SpatialDerivativesAutograd().get_grid_1d([1, 10])  # batch_size, resolution_grid
    u = x**3

    u_x, u_xx = SpatialDerivativesAutograd().second_order_1d(u, x)

    expected_u_x = 3 * x**2
    expected_u_xx = 6 * x

    assert torch.allclose(u_x, expected_u_x, atol=1e-6)
    assert torch.allclose(u_xx, expected_u_xx, atol=1e-6)


#### Test first-order derivatives in 2D
def test_first_order_2d_autograd():
    X, Y = SpatialDerivativesAutograd().get_grid_2d(
        [1, 10, 10]
    )  # batch_size, resolution_grid_x, resolution_grid_y
    u = X**2 + Y**2

    u_x, u_y = SpatialDerivativesAutograd().first_order_2d(u, X, Y)

    expected_u_x = 2 * X
    expected_u_y = 2 * Y

    assert torch.allclose(u_x, expected_u_x, atol=1e-6)
    assert torch.allclose(u_y, expected_u_y, atol=1e-6)


#### Test second-order derivatives in 2D
def test_second_order_2d_autograd():
    X, Y = SpatialDerivativesAutograd().get_grid_2d(
        [1, 10, 10]
    )  # batch_size, resolution_grid_x, resolution_grid_y
    u = X**3 + Y**3

    u_x, u_y, u_xx, u_yy = SpatialDerivativesAutograd().second_order_2d(u, X, Y)

    expected_u_x = 3 * X**2
    expected_u_y = 3 * Y**2
    expected_u_xx = 6 * X
    expected_u_yy = 6 * Y

    assert torch.allclose(u_x, expected_u_x, atol=1e-6)
    assert torch.allclose(u_y, expected_u_y, atol=1e-6)
    assert torch.allclose(u_xx, expected_u_xx, atol=1e-6)
    assert torch.allclose(u_yy, expected_u_yy, atol=1e-6)


#### Test Poisson equation residual
def test_poisson_residual_autograd():
    X, Y = SpatialDerivativesAutograd().get_grid_2d(
        [1, 10, 10]
    )  # batch_size, resolution_grid_x, resolution_grid_y
    u = X**2 + Y**2

    # For u = x^2 + y^2, lap(u) = 4
    rhs = torch.ones_like(u) * 4
    residual = PoissonResidualAutograd()(u, X, Y, rhs)

    assert torch.allclose(residual, torch.zeros_like(residual), atol=1e-6)


#### Test DarcyResidual
def test_darcy_residual_autograd():
    X, Y = SpatialDerivativesAutograd().get_grid_2d(
        [1, 10, 10]
    )  # batch_size, resolution_grid_x, resolution_grid_y
    u = X**2 + Y**2

    a = torch.ones_like(u)
    rhs = torch.ones_like(u)
    residual = DarcyResidualAutograd(rhs)(u, X, Y, a)

    # For u = x^2 + y^2 and a = 1, div(a grad(u)) = 4
    # Residual should be div(a grad(u)) + rhs = 4 + 1 = 5
    expected_residual = torch.ones_like(u) * 5

    assert torch.allclose(residual, expected_residual, atol=1e-6)


#### Test HelmholtzResidual
def test_helmholtz_residual_autograd():
    X, Y = SpatialDerivativesAutograd().get_grid_2d(
        [1, 10, 10]
    )  # batch_size, resolution_grid_x, resolution_grid_y
    u = torch.sin(X) * torch.cos(Y)

    k = torch.tensor(2.0)
    residual = HelmholtzResidualAutograd()(u, X, Y, k)

    # For u = sin(x) * cos(y), lap(u) = -2u
    # Residual should be lap(u) + k²u = -2u + 4u = 2u
    expected_residual = 2 * u

    assert torch.allclose(residual, expected_residual, atol=1e-6)


#########################################
# Derivative with finite differences
#########################################
#### Test first-order derivatives in 1D
def test_first_order_1d_finitediff():
    x = SpatialDerivativesFiniteDiff().get_grid_1d(
        [1, 10]
    )  # batch_size, resolution_grid
    u = x**2

    u_x = SpatialDerivativesFiniteDiff().first_order_1d(u)

    expected_u_x = 2 * x

    assert torch.allclose(u_x[1:-1], expected_u_x[1:-1], atol=1e-2)


#### Test second-order derivatives in 1D
def test_second_order_1d_finitediff():
    x = SpatialDerivativesFiniteDiff().get_grid_1d(
        [1, 10]
    )  # batch_size, resolution_grid
    u = x**3

    u_xx = SpatialDerivativesFiniteDiff().second_order_1d(u)

    expected_u_xx = 6 * x

    assert torch.allclose(u_xx[1:-1], expected_u_xx[1:-1], atol=1e-2)


#### Test first-order derivatives in 2D
def test_first_order_2d_finitediff():
    X, Y = SpatialDerivativesFiniteDiff().get_grid_2d(
        [1, 10, 10]
    )  # batch_size, resolution_grid_x, resolution_grid_y
    u = X**2 + Y**2

    u_x, u_y = SpatialDerivativesFiniteDiff().first_order_2d(u)

    expected_u_x = 2 * X
    expected_u_y = 2 * Y

    assert torch.allclose(u_x[1:-1], expected_u_x[1:-1], atol=1e-2)
    assert torch.allclose(u_y[1:-1], expected_u_y[1:-1], atol=1e-2)


#### Test second-order derivatives in 2D
def test_second_order_2d_finitediff():
    X, Y = SpatialDerivativesFiniteDiff().get_grid_2d(
        [1, 10, 10]
    )  # batch_size, resolution_grid_x, resolution_grid_y
    u = X**3 + Y**3

    u_xx, u_yy = SpatialDerivativesFiniteDiff().second_order_2d(u)

    expected_u_xx = 6 * X
    expected_u_yy = 6 * Y

    assert torch.allclose(u_xx[1:-1], expected_u_xx[1:-1], atol=1e-2)
    assert torch.allclose(u_yy[1:-1], expected_u_yy[1:-1], atol=1e-2)


#### Test Poisson equation residual
def test_poisson_residual_finitediff():
    X, Y = SpatialDerivativesFiniteDiff().get_grid_2d(
        [1, 10, 10]
    )  # batch_size, resolution_grid_x, resolution_grid_y
    u = X**2 + Y**2

    # For u = x^2 + y^2, lap(u) = 4
    rhs = torch.ones_like(u) * 4
    residual = PoissonResidualFiniteDiff()(u, rhs)

    assert torch.allclose(
        residual[:, 1:-1, 1:-1], torch.zeros_like(residual[:, 1:-1, 1:-1]), atol=1e-2
    )


#### Test DarcyResidual
def test_darcy_residual_finitediff():
    X, Y = SpatialDerivativesFiniteDiff().get_grid_2d(
        [1, 20, 10]
    )  # batch_size, resolution_grid_x, resolution_grid_y
    u = X**2 + Y**2

    a = torch.ones_like(u)
    rhs = torch.ones_like(u)
    residual = DarcyResidualFiniteDiff(rhs)(u, a)

    # For u = x^2 + y^2 and a = 1, div(a grad(u)) = 4
    # Residual should be div(a grad(u)) + rhs = 4 + 1 = 5
    expected_residual = torch.ones_like(u) * 5

    assert torch.allclose(
        residual[:, 2:-2, 2:-2], expected_residual[:, 2:-2, 2:-2], atol=1e-2
    )


#### Test HelmholtzResidual
def test_helmholtz_residual_finitediff():
    X, Y = SpatialDerivativesFiniteDiff().get_grid_2d(
        [1, 10, 10]
    )  # batch_size, resolution_grid_x, resolution_grid_y
    u = torch.sin(X) * torch.cos(Y)

    k = torch.tensor(2.0)
    residual = HelmholtzResidualFiniteDiff()(u, k)

    # For u = sin(x) * cos(y), lap(u) = -2u
    # Residual should be lap(u) + k²u = -2u + 4u = 2u
    expected_residual = 2 * u

    assert torch.allclose(
        residual[:, 1:-1, 1:-1], expected_residual[:, 1:-1, 1:-1], atol=1e-2
    )
