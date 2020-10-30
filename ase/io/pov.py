"""
Module for povray file format support.

See http://www.povray.org/ for details on the format.
"""
from typing import Dict, Any

import numpy as np

from ase.io.utils import PlottingVariables
from ase.constraints import FixAtoms
from ase import Atoms
from subprocess import check_call, DEVNULL
from os import unlink
from pathlib import Path

def pa(array):
    """Povray array syntax"""
    return '<' + ', '.join(f"{x:>6.2f}" for x in tuple(array)) + '>'

def pc(array):
    """Povray color syntax"""
    if isinstance(array, str):
        return 'color ' + array
    if isinstance(array, float):
        return f'rgb <{array:.2f}>*3'.format(array)
    l = len(array)
    if l > 2 and l < 6:
        return f"rgb{'' if l == 3 else 't' if l == 4 else 'ft'} <" +\
                ', '.join(f"{x:.2f}" for x in tuple(array)) + '>'

def get_bondpairs(atoms, radius=1.1):
    """Get all pairs of bonding atoms

    Return all pairs of atoms which are closer than radius times the
    sum of their respective covalent radii.  The pairs are returned as
    tuples::

      (a, b, (i1, i2, i3))

    so that atoms a bonds to atom b displaced by the vector::

        _     _     _
      i c + i c + i c ,
       1 1   2 2   3 3

    where c1, c2 and c3 are the unit cell vectors and i1, i2, i3 are
    integers."""

    from ase.data import covalent_radii
    from ase.neighborlist import NeighborList
    cutoffs = radius * covalent_radii[atoms.numbers]
    nl = NeighborList(cutoffs=cutoffs, self_interaction=False)
    nl.update(atoms)
    bondpairs = []
    for a in range(len(atoms)):
        indices, offsets = nl.get_neighbors(a)
        bondpairs.extend([(a, a2, offset)
                          for a2, offset in zip(indices, offsets)])
    return bondpairs


def set_high_bondorder_pairs(bondpairs, high_bondorder_pairs=None):
    """Set high bondorder pairs

    Modify bondpairs list (from get_bondpairs((atoms)) to include high
    bondorder pairs.

    Parameters:
    -----------
    bondpairs: List of pairs, generated from get_bondpairs(atoms)
    high_bondorder_pairs: Dictionary of pairs with high bond orders
                          using the following format:
                          { ( a1, b1 ): ( offset1, bond_order1, bond_offset1),
                            ( a2, b2 ): ( offset2, bond_order2, bond_offset2),
                            ...
                          }
                          offset, bond_order, bond_offset are optional.
                          However, if they are provided, the 1st value is
                          offset, 2nd value is bond_order,
                          3rd value is bond_offset """

    if high_bondorder_pairs is None:
        high_bondorder_pairs = dict()
    bondpairs_ = []
    for pair in bondpairs:
        (a, b) = (pair[0], pair[1])
        if (a, b) in high_bondorder_pairs.keys():
            bondpair = [a, b] + [item for item in high_bondorder_pairs[(a, b)]]
            bondpairs_.append(bondpair)
        elif (b, a) in high_bondorder_pairs.keys():
            bondpair = [a, b] + [item for item in high_bondorder_pairs[(b, a)]]
            bondpairs_.append(bondpair)
        else:
            bondpairs_.append(pair)
    return bondpairs_


class POVRAY:
    material_styles_dict = dict(
            simple='finish {phong 0.7}',
            pale=('finish {ambient 0.5 diffuse 0.85 roughness 0.001 '
                  'specular 0.200 }'),
            intermediate=('finish {ambient 0.3 diffuse 0.6 specular 0.1 '
                          'roughness 0.04}'),
            vmd=('finish {ambient 0.0 diffuse 0.65 phong 0.1 phong_size 40.0 '
                 'specular 0.5 }'),
            jmol=('finish {ambient 0.2 diffuse 0.6 specular 1 roughness 0.001 '
                  'metallic}'),
            ase2=('finish {ambient 0.05 brilliance 3 diffuse 0.6 metallic '
                  'specular 0.7 roughness 0.04 reflection 0.15}'),
            ase3=('finish {ambient 0.15 brilliance 2 diffuse 0.6 metallic '
                  'specular 1.0 roughness 0.001 reflection 0.0}'),
            glass=('finish {ambient 0.05 diffuse 0.3 specular 1.0 '
                   'roughness 0.001}'),
            glass2=('finish {ambient 0.01 diffuse 0.3 specular 1.0 '
                    'reflection 0.25 roughness 0.001}'),
        )

    def __init__(self, pvars, constraints=tuple(), isosurface = None, display = False,
                pause = True, transparent = True, canvas_width = None, canvas_height
                = None, camera_dist = 50., image_plane = None, camera_type =
                'orthographic', point_lights = [], area_light = [(2., 3., 40.),
                'White', .7, .7, 3, 3], background = 'White', textures = None,
                transmittances = None, depth_cueing = False, cue_density = 5e-3,
                celllinewidth = 0.05, bondlinewidth = 0.10, bondatoms = [],
                exportconstraints = False, colors = None):
        """
        # x, y is the image plane, z is *out* of the screen
        pvars: PlottingVariables
            plotting variables (a subset of attributes are taken)
        constraints: Atoms.constraints
            constraints to be visualized
        isosurface: POVRAYIsosurface
            composite object to write/render POVRAY isosurfaces in addition to atoms
        display: bool
            display while rendering
        pause: bool
            pause when done rendering (only if display)
        transparent: bool
            make background transparent
        canvas_width: int
            width of canvas in pixels
        canvas_height: int
            height of canvas in pixels
        camera_dist: float
            distance from camera to front atom
        image_plane: float
            distance from front atom to image plane
        camera_type: str
            if 'orthographic' perspective, ultra_wide_angle
        point_lights: list of 2-element sequences 
            like [[loc1, color1], [loc2, color2],...]
        area_light: 3-element sequence of location (3-tuple), color (str), width (float), height (float), Nlamps_x (int), Nlamps_y (int)
            example [(2., 3., 40.), 'White', .7, .7, 3, 3]
        background: str
            color specification, e.g., 'White'
        textures: list of str
            length of atoms list of texture names
        transmittances: list of floats
            length of atoms list of transmittances of the atoms
        depth_cueing: bool
            whether or not to use depth cueing a.k.a. fog
            use with care - in particular adjust the camera_distance to be closer
        cue_density: float
            if there is depth_cueing, how dense is it (how dense is the fog)
        celllinewidth: float
            radius of the cylinders representing the cell (Ang.)
        bondlinewidth: float
            radius of the cylinders representing bonds (Ang.)
        bondatoms: list of lists (polymorphic)
            [[atom1, atom2], ... ] pairs of bonding atoms
             For bond order > 1 = [[atom1, atom2, offset,
                                    bond_order, bond_offset],
                                   ... ]
             bond_order: 1, 2, 3 for single, double,
                          and triple bond
             bond_offset: vector for shifting bonds from
                           original position. Coordinates are
                           in Angstrom unit.
        exportconstraints: bool
            honour FixAtoms and mark?"""

        # attributes copied from plotting variables
        self.cell = pvars.cell
        self.diameters = pvars.d
        if colors is None:
            self.colors = pvars.colors
        else:
            self.colors = colors
        self.image_width = pvars.w
        self.image_height = pvars.h

        # attributes from initialization
        self.area_light = area_light
        self.background = background
        self.bondatoms = bondatoms
        self.bondlinewidth = bondlinewidth
        self.camera_dist = camera_dist
        self.camera_type = camera_type
        self.celllinewidth = celllinewidth
        self.cue_density = cue_density
        self.depth_cueing = depth_cueing
        self.display = display
        self.exportconstraints  = exportconstraints
        self.isosurface = isosurface
        self.pause = pause
        self.point_lights = point_lights
        self.textures = textures
        self.transmittances = transmittances
        self.transparent = transparent

        # calculations based on passed inputs

        z0 = pvars.positions[:, 2].max() 
        self.offset = (pvars.w / 2, pvars.h / 2, z0)
        self.positions = pvars.positions - self.offset

        if pvars.cell_vertices is not None:
            self.cell_vertices = pvars.cell_vertices - self.offset
            self.cell_vertices.shape = (2, 2, 2, 3)
        else:
            self.cell_vertices = None

        ratio = float(pvars.w) / pvars.h
        if canvas_width is None:
            if canvas_height is None:
                self.canvas_width = min(pvars.w * 15, 640)
                self.canvas_height = pvars.h
            else:
                self.canvas_width = canvas_height * ratio
                self.canvas_height = canvas_height
        elif canvas_height is None:
            self.canvas_width = canvas_width
            self.canvas_height = self.canvas_width / ratio
        else:
            raise RuntimeError("Can't set *both* width and height!")

        # Distance to image plane from camera
        if image_plane is None:
            if self.camera_type == 'orthographic':
                self.image_plane = 1 - self.camera_dist
            else:
                self.image_plane = 0
        self.image_plane += self.camera_dist

        self.constrainatoms = []
        for c in constraints:
            if isinstance(c, FixAtoms):
#                self.constrainatoms.extend(c.index) # is this list-like?
                for n, i in enumerate(c.index):
                    self.constrainatoms += [i]


    def write_ini(self, path):
        """Write ini file."""

        ini_path = path.with_suffix('.ini')
        ini_str = f"""Input_File_Name={ini_path.with_suffix('.pov').name}
Output_to_File=True
Output_File_Type=N
Output_Alpha={'on' if self.transparent else 'off'}
; if you adjust Height, and width, you must preserve the ratio
; Width / Height = {self.canvas_width/self.canvas_height:f}
Width={self.canvas_width}
Height={self.canvas_height}
Antialias=True
Antialias_Threshold=0.1
Display={self.display}
Pause_When_Done={self.pause}
Verbose=False
"""
        with open(ini_path, 'w') as _:
            _.write(ini_str)
        return ini_path

    def write_pov(self, path):
        """Write pov file."""

        point_lights = '\n'.join(f"light_source {{{pa(loc)} {pc(rgb)}}}" 
            for loc,rgb in self.point_lights)

        area_light = ''
        if self.area_light is not None:
            loc, color, width, height, nx, ny = self.area_light
            area_light += f"""\nlight_source {{{pa(loc)} {pc(color)}
  area_light <{width:.2f}, 0, 0>, <0, {height:.2f}, 0>, {nx:n}, {ny:n}
  adaptive 1 jitter}}"""

        fog = ''
        if self.depth_cueing and (self.cue_density >= 1e-4):
            # same way vmd does it
            if self.cue_density > 1e4:
                # larger does not make any sense
                dist = 1e-4
            else:
                dist = 1. / self.cue_density
            fog += f'fog {{fog_type 1 distance {dist:.4f} color {pc(self.background)}}}'

        material_styles_dict_keys = '\n'.join(f'#declare {key} = {value}' #semicolon?
            for key, value in self.__class__.material_styles_dict.items())


        # Draw unit cell
        cell_vertices = ''
        if self.cell_vertices is not None:
            for c in range(3):
                for j in ([0, 0], [1, 0], [1, 1], [0, 1]):
                    parts = []
                    for i in range(2):
                        j.insert(c, i)
                        parts.append(self.cell_vertices[tuple(j)])
                        del j[c]

                    distance = np.linalg.norm(parts[1] - parts[0])
                    if distance < 1e-12:
                        continue

                    cell_vertices += f'cylinder {{{pa(parts[0])}, {pa(parts[1])}, '\
                                     f'Rcell pigment {{Black}}}}\n' 
                                     # all strings are f-strings for consistency
            cell_vertices = cell_vertices.strip('\n')

        # Draw atoms
        a = 0
        atoms = ''
        for loc, dia, color in zip(self.positions, self.diameters, self.colors):
            tex = 'ase3'
            trans = 0.
            if self.textures is not None:
                tex = self.textures[a]
            if self.transmittances is not None:
                trans = self.transmittances[a]
            atoms += f'atom({pa(loc)}, {dia/2.:.2f}, {pc(color)}, '\
                     f'{trans}, {tex}) // #{a:n}\n'
            a += 1
        atoms = atoms.strip('\n')

        # Draw atom bonds
        bondatoms = ''
        for pair in self.bondatoms:
            # Make sure that each pair has 4 componets: a, b, offset,
            #                                           bond_order, bond_offset
            # a, b: atom index to draw bond
            # offset: original meaning to make offset for mid-point.
            # bond_oder: if not supplied, set it to 1 (single bond).
            #            It can be  1, 2, 3, corresponding to single,
            #            double, triple bond
            # bond_offset: displacement from original bond position.
            #              Default is (bondlinewidth, bondlinewidth, 0)
            #              for bond_order > 1.
            if len(pair) == 2:
                a, b = pair
                offset = (0, 0, 0)
                bond_order = 1
                bond_offset = (0, 0, 0)
            elif len(pair) == 3:
                a, b, offset = pair
                bond_order = 1
                bond_offset = (0, 0, 0)
            elif len(pair) == 4:
                a, b, offset, bond_order = pair
                bond_offset = (self.bondlinewidth, self.bondlinewidth, 0)
            elif len(pair) > 4:
                a, b, offset, bond_order, bond_offset = pair
            else:
                raise RuntimeError('Each list in bondatom must have at least '
                                   '2 entries. Error at %s' % pair)

            if len(offset) != 3:
                raise ValueError('offset must have 3 elements. '
                                 'Error at %s' % pair)
            if len(bond_offset) != 3:
                raise ValueError('bond_offset must have 3 elements. '
                                 'Error at %s' % pair)
            if bond_order not in [0, 1, 2, 3]:
                raise ValueError('bond_order must be either 0, 1, 2, or 3. '
                                 'Error at %s' % pair)

            # Up to here, we should have all a, b, offset, bond_order,
            # bond_offset for all bonds.

            # Rotate bond_offset so that its direction is 90 degree off the bond
            # Utilize Atoms object to rotate
            if bond_order > 1 and np.linalg.norm(bond_offset) > 1.e-9:
                tmp_atoms = Atoms('H3')
                tmp_atoms.set_cell(self.cell)
                tmp_atoms.set_positions([
                    self.positions[a],
                    self.positions[b],
                    self.positions[b] + np.array(bond_offset),
                ])
                tmp_atoms.center()
                tmp_atoms.set_angle(0, 1, 2, 90)
                bond_offset = tmp_atoms[2].position - tmp_atoms[1].position

            R = np.dot(offset, self.cell)
            mida = 0.5 * (self.positions[a] + self.positions[b] + R)
            midb = 0.5 * (self.positions[a] + self.positions[b] - R)
            if self.textures is not None:
                texa = self.textures[a]
                texb = self.textures[b]
            else:
                texa = texb = 'ase3'

            if self.transmittances is not None:
                transa = self.transmittances[a]
                transb = self.transmittances[b]
            else:
                transa = transb = 0.

            # draw bond, according to its bond_order.
            # bond_order == 0: No bond is plotted
            # bond_order == 1: use original code
            # bond_order == 2: draw two bonds, one is shifted by bond_offset/2,
            #                  and another is shifted by -bond_offset/2.
            # bond_order == 3: draw two bonds, one is shifted by bond_offset,
            #                  and one is shifted by -bond_offset, and the
            #                  other has no shift.
            # To shift the bond, add the shift to the first two coordinate in
            # write statement.

            posa = self.positions[a]; posb = self.positions[b]
            cola = self.colors[a]; colb = self.colors[b]

            if bond_order == 1:
                draw_tuples = (posa, mida, cola, transa, texa),\
                              (posb, midb, colb, transb, texb)  

            elif bond_order == 2:
                bs = [x / 2 for x in bond_offset]
                draw_tuples = (posa-bs, mida-bs, cola, transa, texa),\
                              (posb-bs, midb-bs, colb, transb, texb),\
                              (posa+bs, mida+bs, cola, transa, texa),\
                              (posb+bs, midb+bs, colb, transb, texb)

            elif bond_order == 3:
                bs = bond_offset
                draw_tuples = (posa   , mida   , cola, transa, texa),\
                              (posb   , midb   , colb, transb, texb),\
                              (posa+bs, mida+bs, cola, transa, texa),\
                              (posb+bs, midb+bs, colb, transb, texb),\
                              (posa-bs, mida-bs, cola, transa, texa),\
                              (posb-bs, midb-bs, colb, transb, texb)

            bondatoms += ''.join(f'cylinder {{{pa(p)}, '
                       f'{pa(m)}, Rbond texture{{pigment '
                       f'{{color {pc(c)} '
                       f'transmit {tr}}} finish{{{tx}}}}}}}\n'
                       for p, m, c, tr, tx in
                       draw_tuples)

        bondatoms = bondatoms.strip('\n') 

        # Draw constraints if requested
        constraints = ''
        if self.exportconstraints:
            for a in self.constrainatoms:
                dia = self.diameters[a]
                loc = self.positions[a]
                trans = 0.0
                if self.transmittances is not None:
                    trans = self.transmittances[a]
                constraints += f'constrain({pa(loc)}, {dia/2.:.2f}, Black, '\
                f'{trans}, {tex}) // #{a:n} \n' 
        constraints = constraints.strip('\n')

        pov = f"""#include "colors.inc"
#include "finish.inc"

global_settings {{assumed_gamma 1 max_trace_level 6}}
background {{{pc(self.background)}{' transmit 1.0' if self.transparent else ''}}}
camera {{{self.camera_type}
  right {self.image_width:.2f}*x up {self.image_height:.2f}*y   
  direction {self.image_plane:.2f}*z
  location <0,0,{self.camera_dist:.2f}> look_at <0,0,0>}}
{point_lights}
{area_light if area_light != '' else '// no area light'}
{fog if fog != '' else '// no fog'}
{material_styles_dict_keys}
#declare Rcell = {self.celllinewidth:.3f};
#declare Rbond = {self.bondlinewidth:.3f};

#macro atom(LOC, R, COL, TRANS, FIN)
  sphere{{LOC, R texture{{pigment{{color COL transmit TRANS}} finish{{FIN}}}}}}
#end
#macro constrain(LOC, R, COL, TRANS FIN)
union{{torus{{R, Rcell rotate 45*z texture{{pigment{{color COL transmit TRANS}} finish{{FIN}}}}}}
     torus{{R, Rcell rotate -45*z texture{{pigment{{color COL transmit TRANS}} finish{{FIN}}}}}}
     translate LOC}}
#end

{cell_vertices if cell_vertices != '' else '// no cell vertices'} 
{atoms}
{bondatoms}
{constraints if constraints != '' else '// no constraints'}
""" 

        pov_path = path.with_suffix('.pov')
        with open(pov_path, 'w') as _:
            _.write(pov)

        return pov_path

    def write(self, filename):
        path = Path(filename).with_suffix('')
        self.write_ini(path)
        self.write_pov(path)
        if self.isosurface is not None:
            with open(path.with_suffix('.pov'), 'a') as _:
                _.write(self.isosurface.format_mesh())
        self.path = path
        return self

    def render(self, povray_executable='povray', stderr=None, clean_up=False):
        pov_path = self.path.with_suffix('.pov')
        cmd = [povray_executable, pov_path.as_posix()]
        if stderr != '-':
            if stderr is None:
                status = check_call(cmd, stderr=DEVNULL)
            else:
                with open(stderr, 'w') as stderr:
                    status = check_call(cmd, stderr=stderr)
        else:
            status = check_call(cmd)

        if clean_up:
            unlink(self.path.with_suffix('.ini'))
            unlink(self.path.with_suffix('.pov'))

        return self.path.with_suffix('.png')
       


class POVRAYIsosurface:
    def __init__(self, density_grid, cut_off, cell, cell_origin,
                              closed_edges=False, gradient_ascending=False,
                              color=(0.85, 0.80, 0.25, 0.2), material='ase3'):
        """
        density_grid: 3D float ndarray
            A regular grid on that spans the cell. The first dimension corresponds
            to the first cell vector and so on.
        cut_off: float
            The density value of the isosurface.
        cell: 2D float ndarray or ASE cell object
            The 3 vectors which give the cell's repetition
        cell_origin: 4 float tuple
            The cell origin as returned by the PlottingVariables instance (used in the POVRAY object)
        closed_edges: bool
            Setting this will fill in isosurface edges at the cell boundaries.
            Filling in the edges can help with visualizing highly porous structures.
        gradient_ascending: bool
            Lets you pick the area you want to enclose, i.e., should the denser
            or less dense area be filled in.
        color: povray color string, float, or float tuple
            1 float is interpreted as grey scale, a 3 float tuple is rgb, 4 float
            tuple is rgbt, and 5 float tuple is rgbft, where t is transmission
            fraction and f is filter fraction. Named Povray colors are set in
            colors.inc (http://wiki.povray.org/content/Reference:Colors.inc)
        material: string
            Can be a finish macro defined by POVRAY.material_styles or a full Povray
            material {...} specification. Using a full material specification will
            override the color parameter.
        """

        self.cut_off = cut_off
        self.color = color
        self.material = material

        if gradient_ascending:
            self.gradient_direction = 'ascent'
            cv = 2 * cut_off
        else:
            self.gradient_direction = 'descent'
            cv = 0

        if closed_edges:
            shape_old = density_grid.shape
            # since well be padding, we need to keep the data at origin
            cell_origin += -(1.0 / np.array(shape_old)) @ cell
            density_grid = np.pad(density_grid, pad_width=(1,), mode='constant', constant_values=cv)
            shape_new = density_grid.shape
            s = np.array(shape_new) / np.array(shape_old)
            cell = cell @ np.diag(s)

        self.cell = cell
        self.cell_origin = cell_origin
        self.density_grid = density_grid
        self.spacing = tuple(1.0 / np.array(self.density_grid.shape))


    @staticmethod
    def wrapped_triples_section(triple_list,
                                triple_format="<{:f}, {:f}, {:f}>".format,
                                triples_per_line=4):

        triples = [triple_format(*x) for x in triple_list]
        n = len(triples)
        s = ''
        tpl = triples_per_line
        c = 0

        while c < n - tpl:
            c += tpl
            s += '\n     '
            s += ', '.join(triples[c-tpl:c])
        s += '\n    '
        s += ', '.join(triples[c:])
        return s

    @staticmethod
    def compute_mesh(density_grid, cut_off, spacing, gradient_direction):
        """

        Import statement is in this method and not file header since few users will use isosurface rendering. 

        Returns scaled_verts, faces, normals, values. See skimage docs.

        """

        from skimage import measure
        return measure.marching_cubes_lewiner(
                density_grid,
                level=cut_off,
                spacing=spacing,
                gradient_direction=gradient_direction,
                allow_degenerate=False)


    def format_mesh(self):

        """Returns a formatted data output for POVRAY files

        Example:
        material = '''
          material { // This material looks like pink jelly
            texture {
              pigment { rgbt <0.8, 0.25, 0.25, 0.5> }
              finish{ diffuse 0.85 ambient 0.99 brilliance 3 specular 0.5 roughness 0.001
                reflection { 0.05, 0.98 fresnel on exponent 1.5 }
                conserve_energy
              }
            }
            interior { ior 1.3 }
          }
          photons {
              target
              refraction on
              reflection on
              collect on
          }'''
        """  # noqa: E501

        scaled_verts, faces, normals, values = self.__class__.compute_mesh(
            self.density_grid,
            self.cut_off,
            self.spacing,
            self.gradient_direction)

        # The verts are scaled by default, this is the super easy way of
        # distributing them in real space but it's easier to do affine
        # transformations/rotations on a unit cube so I leave it like that
        # verts = scaled_verts.dot(self.cell)
        verts = scaled_verts

        if self.material in POVRAY.material_styles_dict.keys():
            material = f"""material {{
        texture {{
          pigment {{ {pc(self.color)} }}
          finish {{ {self.material} }}
        }}
      }}"""
        else:
            material == self.material

        # Start writing the mesh2
        vertex_vectors = self.__class__.wrapped_triples_section(triple_list=verts,
                triple_format="<{:f}, {:f}, {:f}>".format, triples_per_line=4)

        face_indices = self.__class__.wrapped_triples_section(triple_list=faces,
                triple_format="<{:n}, {:n}, {:n}>".format, triples_per_line=5)

        cell = self.cell
        cell_or = self.cell_origin
        mesh2 = f"""\n\nmesh2 {{
    vertex_vectors {{  {len(verts):n},
    {vertex_vectors}
    }}
    face_indices {{ {len(faces):n},
    {face_indices}
    }}
{material if material != '' else '// no material'}
  matrix < {cell[0][0]:f}, {cell[0][1]:f}, {cell[0][2]:f},
           {cell[1][0]:f}, {cell[1][1]:f}, {cell[1][2]:f},
           {cell[2][0]:f}, {cell[2][1]:f}, {cell[2][2]:f},
           {cell_or[0]:f}, {cell_or[1]:f}, {cell_or[2]:f}>
    }}
    """
        return mesh2

def write_pov(filename, atoms, plotting_var_settings={}, povray_settings={}, run_povray=False, isosurface_data = None):

    if isinstance(atoms, list):
        assert len(atoms) == 1
        atoms = atoms[0]

    pvars = PlottingVariables(atoms, scale=1.0, **plotting_var_settings)
    pov_obj = POVRAY(pvars, atoms.constraints, **povray_settings)
    #note pov_obj.cell_vertices != pvars.cell_vertices
    if isosurface_data is not None:
        isosurface = POVRAYIsosurface(cell=pov_obj.cell, cell_origin=pov_obj.cell_vertices[0,0,0],**isosurface_data)
        pov_obj.isosurface = isosurface

    pov_obj.write(filename)
    if run_povray:
        pov_obj.render()

if __name__ == '__main__':
    from ase.build import molecule
    H2 = molecule('H2')
    write_pov('H2.pov', H2, run_povray=True)

    from ase.io import read
    from ase.calculators.vasp import VaspChargeDensity
    zno = read('CONTCAR')
    vchg = VaspChargeDensity('CHGCAR')
    pvars = PlottingVariables(zno, scale=1.0)
    pov_obj = POVRAY(pvars)
    pov_obj.isosurface = POVRAYIsosurface(vchg.chg[0], 0.15, cell=zno.cell,cell_origin=pov_obj.cell_vertices[0,0,0])
    pov_obj.write('zno').render(clean_up=True)
