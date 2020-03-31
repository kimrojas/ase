import pytest
import numpy as np
from ase.outputs import Properties, all_properties


@pytest.mark.parametrize('name', list(all_properties))
def test_print_props(name):
    print(all_properties[name])

natoms = 7


@pytest.fixture
def forceprop(natoms):
    props = Properties()
    props.setvalue('forces', np.zeros((natoms, 3)))
    return props


def test_props(forceprop, natoms):
    print(forceprop)
    assert forceprop['forces'].shape == (natoms, 3)
    assert forceprop['natoms'] == natoms

def test_props_set_twice(forceprop, natoms):
    with pytest.raises(ValueError):
        # Cannot set same thing twice.
        # Programmatically we could allow that, but we would have to
        # invalidate implicitly set quantities like natoms.
        forceprop.setvalue('forces', np.zeros((natoms, 3)))


def test_props_set_consistent(forceprop, natoms):
    forceprop.setvalue('stresses', np.zeros((natoms, 6)))
    assert forceprop['stresses'].shape == (natoms, 6)


def test_props_set_inconsistent(forceprop, natoms):
    # Setting stresses for particular number of atoms different from
    # existing number of atoms must be an error:
    with pytest.raises(ValueError):
        forceprop.setvalue('stresses', np.zeros((natoms + 2, 6)))


@pytest.fixture
def props():
    return Properties()


@pytest.mark.parametrize('val', [np.zeros(7), np.zeros((2, 3))])
def test_array_badvalue(props, val):
    with pytest.raises(ValueError):
        props.setvalue('stress', val)


@pytest.mark.parametrize('val', [5])
def test_array_badtype(props, val):
    with pytest.raises(TypeError):
        props.setvalue('stress', val)


@pytest.mark.parametrize(
    'val', [np.arange(6).astype(float), np.arange(6), range(6)]
)
def test_array_good(props, val):
    props.setvalue('stress', val)
    assert props['stress'].shape == (6,)
    assert props['stress'].dtype == float


@pytest.mark.parametrize('val', [np.zeros(3), range(3), np.zeros(1), 1j, None])
def test_float_badtype(props, val):
    with pytest.raises(TypeError):
        props.setvalue('energy', val)


@pytest.mark.parametrize('val', ['hello'])
def test_float_badvalue(props, val):
    with pytest.raises(ValueError):
        props.setvalue('energy', val)


@pytest.mark.parametrize('val', [4.0, 42, np.nan, '42.0'])
def test_float_good(props, val):
    props.setvalue('energy', val)
