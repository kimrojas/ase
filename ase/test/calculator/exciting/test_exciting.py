"""Test file for exciting ASE calculator."""

import logging
import os
import xml.etree.ElementTree as ET

import numpy as np
import pytest

import ase


LOGGER = logging.getLogger(__name__)


try:
    __import__('excitingtools')
    import ase.calculators.exciting.exciting as exciting
    from ase.calculators.exciting.runner import ExcitingRunner

except ModuleNotFoundError:
    MESSAGE = "exciting tests are skipped if excitingtools not installed."
    LOGGER.info(MESSAGE)


LDA_VWN_AR_INFO_OUT = """
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+ Starting initialization                                                      +
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

 Lattice vectors (cartesian) :
     15.0000000000      0.0000000000      0.0000000000
      0.0000000000     15.0000000000      0.0000000000
      0.0000000000      0.0000000000     15.0000000000

 Reciprocal lattice vectors (cartesian) :
      0.4188790205      0.0000000000      0.0000000000
      0.0000000000      0.4188790205      0.0000000000
      0.0000000000      0.0000000000      0.4188790205

 Unit cell volume                           :    3375.0000000000
 Brillouin zone volume                      :       0.0734963595

 Species :    1 (Ar)
     parameters loaded from                 :    Ar.xml
     name                                   :    argon
     nuclear charge                         :     -18.00000000
     electronic charge                      :      18.00000000
     atomic mass                            :   72820.74920000
     muffin-tin radius                      :       6.00000000
     # of radial points in muffin-tin       :    1000

     atomic positions (lattice) :
       1 :   0.00000000  0.00000000  0.00000000

 Total number of atoms per unit cell        :       1

 Spin treatment                             :    spin-unpolarised

 Number of Bravais lattice symmetries       :      48
 Number of crystal symmetries               :      48

 k-point grid                               :       1    1    1
 Total number of k-points                   :       1
 k-point set is reduced with crystal symmetries

 R^MT_min * |G+k|_max (rgkmax)              :      10.00000000
 Species with R^MT_min                      :       1 (Ar)
 Maximum |G+k| for APW functions            :       1.66666667
 Maximum |G| for potential and density      :       7.50000000
 Polynomial order for pseudochg. density    :       9

 G-vector grid sizes                        :      36    36    36
 Total number of G-vectors                  :   23871

 Maximum angular momentum used for
     APW functions                          :       8
     computing H and O matrix elements      :       4
     potential and density                  :       4
     inner part of muffin-tin               :       2

 Total nuclear charge                       :     -18.00000000
 Total electronic charge                    :      18.00000000
 Total core charge                          :      10.00000000
 Total valence charge                       :       8.00000000

 Effective Wigner radius, r_s               :       3.55062021

 Number of empty states                     :       5
 Total number of valence states             :      10

 Maximum Hamiltonian size                   :     263
 Maximum number of plane-waves              :     251
 Total number of local-orbitals             :      12

 Exchange-correlation type                  :     100
     libxc; exchange: Slater exchange; correlation: Vosko, Wilk & Nusair (VWN5)

 Smearing scheme                            :    Gaussian
 Smearing width                             :       0.00100000

 Using multisecant Broyden potential mixing

++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+ Ending initialization                                                        +
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+ SCF iteration number :    1                                                  +
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 Total energy                               :      -527.82493279
 _______________________________________________________________
 Fermi energy                               :        -0.20111449
 Kinetic energy                             :       530.56137212
 Coulomb energy                             :     -1029.02167746
 Exchange energy                            :       -27.93377198
 Correlation energy                         :        -1.43085548
 Sum of eigenvalues                         :      -305.07886015
 Effective potential energy                 :      -835.64023227
 Coulomb potential energy                   :      -796.81322609
 xc potential energy                        :       -38.82700618
 Hartree energy                             :       205.65681157
 Electron-nuclear energy                    :     -1208.12684923
 Nuclear-nuclear energy                     :       -26.55163980
 Madelung energy                            :      -630.61506441
 Core-electron kinetic energy               :         0.00000000

 DOS at Fermi energy (states/Ha/cell)       :         0.00000000

 Electron charges :
     core                                   :        10.00000000
     core leakage                           :         0.00000000
     valence                                :         8.00000000
     interstitial                           :         0.00183897
     charge in muffin-tin spheres :
                  atom     1    Ar          :        17.99816103
     total charge in muffin-tins            :        17.99816103
     total charge                           :        18.00000000

 Estimated fundamental gap                  :         0.36071248
        valence-band maximum at    1      0.0000  0.0000  0.0000
     conduction-band minimum at    1      0.0000  0.0000  0.0000

++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
| Convergency criteria checked for the last 2 iterations                       +
| Convergence targets achieved. Performing final SCF iteration                 +
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 Total energy                               :      -527.81796101
 _______________________________________________________________
 Fermi energy                               :        -0.20044598
 Kinetic energy                             :       530.57303096
 Coulomb energy                             :     -1029.02642037
 Exchange energy                            :       -27.93372809
 Correlation energy                         :        -1.43084350
 Sum of eigenvalues                         :      -305.07413840
 Effective potential energy                 :      -835.64716936
 Coulomb potential energy                   :      -796.82023455
 xc potential energy                        :       -38.82693481
 Hartree energy                             :       205.65454603
 Electron-nuclear energy                    :     -1208.12932661
 Nuclear-nuclear energy                     :       -26.55163980
 Madelung energy                            :      -630.61630310
 Core-electron kinetic energy               :         0.00000000

 DOS at Fermi energy (states/Ha/cell)       :         0.00000000

 Electron charges :
     core                                   :        10.00000000
     core leakage                           :         0.00000000
     valence                                :         8.00000000
     interstitial                           :         0.00184037
     charge in muffin-tin spheres :
                  atom     1    Ar          :        17.99815963
     total charge in muffin-tins            :        17.99815963
     total charge                           :        18.00000000

 Estimated fundamental gap                  :         0.36095838
        valence-band maximum at    1      0.0000  0.0000  0.0000
     conduction-band minimum at    1      0.0000  0.0000  0.0000

++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+ Self-consistent loop stopped                                                 +
| EXCITING NITROGEN-14 stopped                                                 =
"""


@pytest.fixture
def excitingtools():
    """If we cannot import excitingtools we skip tests with this fixture."""
    return pytest.importorskip('excitingtools')


@pytest.fixture
def nitrogen_trioxide_atoms():
    """Pytest fixture that creates ASE Atoms cell for other tests."""
    return ase.Atoms('NO3',
                     cell=[[2, 2, 0], [0, 4, 0], [0, 0, 6]],
                     positions=[(0, 0, 0), (1, 3, 0),
                                (0, 0, 1), (0.5, 0.5, 0.5)],
                     pbc=True)


def test_exciting_profile_init(excitingtools):
    """Test initializing an ExcitingProfile object."""
    exciting_root = 'testdir/nowhere/'
    species_path = 'testdir/species/'
    # A fake exciting root should cause a FileNotFoundError when the init
    # method tries to query what exciting version is present.
    with pytest.raises(FileNotFoundError):
        exciting.ExcitingProfile(
            exciting_root=exciting_root, species_path=species_path)


def test_ground_state_template_init(excitingtools):
    """Test initialization of the ExcitingGroundStateTemplate class."""
    gs_template_obj = exciting.ExcitingGroundStateTemplate()
    assert gs_template_obj.name == 'exciting'
    assert len(gs_template_obj.implemented_properties) == 2
    assert 'energy' in gs_template_obj.implemented_properties


def test_ground_state_template_write_input(
        tmp_path, nitrogen_trioxide_atoms, excitingtools):
    """Test the write input method of ExcitingGroundStateTemplate.

    Args:
        tmp_path: This tells pytest to create a temporary directory
             in which we will store the exciting input file.
        nitrogen_trioxide_atoms: pytest fixture to create ASE Atoms
            unit cell composed of NO3.
    """
    expected_path = os.path.join(tmp_path, 'input.xml')

    gs_template_obj = exciting.ExcitingGroundStateTemplate()
    assert nitrogen_trioxide_atoms.cell is not None
    gs_template_obj.write_input(
        directory=tmp_path, atoms=nitrogen_trioxide_atoms,
        parameters={
            "title": None,
            "species_path": tmp_path,
            "ground_state_input": {
                "rgkmax": 8.0,
                "do": "fromscratch",
                "ngridk": [6, 6, 6],
                "xctype": "GGA_PBE_SOL",
                "vkloff": [0, 0, 0]},
        })
    # Let's assert the file we just wrote exists.
    os.path.exists(expected_path)
    # Let's assert it's what we expect.
    element_tree = ET.parse(expected_path)
    # Ensure the coordinates of the atoms in the unit cell is correct.
    # We could test the other parts of the input file related coming from
    # the ASE Atoms object like species data but this is tested already in
    # test/io/exciting/test_exciting.py.
    expected_coords = [
        [0, 0, 0], [1.0, 3.0, 0], [0, 0, 1.], [0.5, 0.5, 0.5]]
    coords_list = element_tree.findall('./structure/species/atom')

    for i in range(len(coords_list)):
        coords_vect_float = [
            float(x) for x in coords_list[i].get('coord').split()]
        assert len(coords_vect_float) == len(expected_coords[i])
        assert all([np.round(a - b, 14) == 0 for a, b in zip(
            coords_vect_float, expected_coords[i])])

    # Ensure that the exciting calculator properites (e.g. functional type have
    # been set).
    assert element_tree.findall('input') is not None
    assert element_tree.getroot().tag == 'input'
    assert element_tree.getroot()[2].attrib['xctype'] == 'GGA_PBE_SOL'
    assert element_tree.getroot()[2].attrib['rgkmax'] == '8.0'


def test_grond_state_template_read_results(
        tmp_path, excitingtools):
    """Test the read result method of ExcitingGroundStateTemplate."""
    # ASE doesn't want us to store any other files for test, so instead
    # we copy an example exciting INFO.out file into the global variable
    # LDA_VWN_AR_INFO_OUT.
    output_file_path = os.path.join(tmp_path, 'info.xml')
    with open(output_file_path, "w", encoding="utf8") as xml_file:
        xml_file.write(LDA_VWN_AR_INFO_OUT)
    assert os.path.exists(output_file_path)  # Ensure file has been written.

    gs_template_obj = exciting.ExcitingGroundStateTemplate()
    results = gs_template_obj.read_results(tmp_path)
    final_scl_iteration = list(results["scl"].keys())[-1]
    assert np.round(float(results["scl"][
        final_scl_iteration]["Hartree energy"]) - 205.65454603, 6) == 0.


def test_ground_state_template_execute(tmpdir, excitingtools):
    """Test ExcitingGroundStateTemplate execute method when no runner given."""
    # If we don't pass a binary runner in the init() of the
    # ExcitingGroundStateTemplate we expect the method to fail.
    with pytest.raises(ValueError):
        exciting.ExcitingGroundStateTemplate().execute(directory=tmpdir)


def test_get_total_energy_and_bandgap(excitingtools):
    """Test getter methods for energy/bandgap results."""
    # Create a fake results dictionary that has two SCL cycles
    # and only contains values for the total energy and bandgap.
    results_dict = {
        'scl': {
            '1':
                {
                    'Total energy': '-240.3',
                    'Estimated fundamental gap': 2.0,
                },
            '2':
                {
                    'Total energy': '-242.3',
                    'Estimated fundamental gap': 3.1,
                }
        }

    }
    results_obj = exciting.ExcitingGroundStateResults(results_dict)
    assert np.round(results_obj.total_energy() + 242.3, 7) == 0
    assert np.round(results_obj.band_gap() - 3.1, 7) == 0


def test_ground_state_calculator_init(tmpdir, excitingtools):
    """Test initiliazation of the ExcitingGroundStateCalculator"""
    ground_state_input_dict = {
        "rgkmax": 8.0,
        "do": "fromscratch",
        "ngridk": [6, 6, 6],
        "xctype": "GGA_PBE_SOL",
        "vkloff": [0, 0, 0]}
    calc_obj = exciting.ExcitingGroundStateCalculator(
        runner=ExcitingRunner("exciting_serial", ['./'], 1, 600, tmpdir, ['']),
        ground_state_input=ground_state_input_dict, directory=tmpdir)
    assert calc_obj.parameters["ground_state_input"]["rgkmax"] == 8.0
