## -*-Pyth-*-
 # #############################################################################
 # FiPy - a finite volume PDE solver in Python
 # 
 # FILE: "meshVariable.py"
 #                                     created: 5/4/07 {12:40:38 PM}
 #                                 last update: 5/4/07 {12:40:38 PM}
 # Author: Jonathan Guyer <guyer@nist.gov>
 # Author: Daniel Wheeler <daniel.wheeler@nist.gov>
 # Author: James Warren   <jwarren@nist.gov>
 #   mail: NIST
 #    www: <http://www.ctcms.nist.gov/fipy/>
 #  
 # ========================================================================
 # This software was developed at the National Institute of Standards
 # and Technology by employees of the Federal Government in the course
 # of their official duties.  Pursuant to title 17 Section 105 of the
 # United States Code this software is not subject to copyright
 # protection and is in the public domain.  FiPy is an experimental
 # system.  NIST assumes no responsibility whatsoever for its use by
 # other parties, and makes no guarantees, expressed or implied, about
 # its quality, reliability, or any other characteristic.  We would
 # appreciate acknowledgement if the software is used.
 # 
 # This software can be redistributed and/or modified freely
 # provided that any derivative works bear some notice that they are 
 # derived from it, and any modified versions bear some notice that
 # they have been modified.
 # ========================================================================
 # 
 # #############################################################################
 ##

__docformat__ = 'restructuredtext'

from fipy.meshes.meshIterator import MeshIterator
from fipy.variables.variable import Variable
from fipy.tools import numerix

class _MeshVariable(Variable):
    """
    .. attention:: This class is abstract. Always create one of its subclasses.
    
    Abstract base class for a `Variable` that is defined on a mesh
    """
    def __init__(self, mesh, name='', value=0., rank=None, elementshape=None, 
                 unit=None, cached=1):
        """
        :Parameters:
          - `mesh`: the mesh that defines the geometry of this `Variable`
          - `name`: the user-readable name of the `Variable`
          - `value`: the initial value
          - `rank`: the rank (number of dimensions) of each element of this 
            `Variable`. Default: 0
          - `elementshape`: the shape of each element of this variable
             Default: `rank * (mesh.getDim(),)`
          - `unit`: the physical units of the `Variable`
        """
        if elementshape is None:
            if rank is not None:
                elementshape = rank * (mesh.getDim(),)
            else:
                elementshape = ()
        else:
            if rank is not None and len(elementshape) != rank:
                raise DimensionError, 'len(elementshape) != rank'
        self.elementshape = elementshape
        
        if value is None:
            array = None
        else:
            array = numerix.zeros(self.elementshape 
                                  + self._getShapeFromMesh(mesh),'d')
                                  
        if isinstance(value, _MeshVariable):
            mesh = mesh or value.mesh
            
        self.mesh = mesh

        Variable.__init__(self, name=name, value=value, unit=unit, 
                          array=array, cached=cached)
                  
    def getMesh(self):
        return self.mesh
        
    def __repr__(self):
        s = Variable.__repr__(self)
        if len(self.name) == 0:
            s = s[:-1] + ', mesh=' + `self.mesh` + s[-1]
        return s

    def __getitem__(self, index):
        """    
        "Evaluate" the `_MeshVariable` and return the specified element
        """
        if isinstance(index, MeshIterator):
            assert index.getMesh() == self.getMesh()
            return self.take(index)
        else:
            return Variable.__getitem__(self, index)

    def __setitem__(self, index, value):
        if isinstance(index, MeshIterator):
            assert index.getMesh() == self.getMesh()
            self.put(indices=index, value=value)
        else:
            Variable.__setitem__(self, index, value)
        
    def _getOpShape(self, baseClass, other):
        """
        Determine the shape from the base class or from the inputs
        """
        mesh = self.getMesh() or other.getMesh()
        
        return (baseClass._getShapeFromMesh(mesh) 
                or Variable._getOpShape(self, baseClass, other))

    def _getShapeFromMesh(mesh):
        """
        Return the shape of this `MeshVariable` type, given a particular mesh.
        Return `None` if unknown or independent of the mesh.
        """
        return None
    _getShapeFromMesh = staticmethod(_getShapeFromMesh)

    def getShape(self):
        """
            >>> from fipy.meshes.grid2D import Grid2D
            >>> from fipy.variables.cellVariable import CellVariable
            >>> mesh = Grid2D(nx=2, ny=3)
            >>> var = CellVariable(mesh=mesh)
            >>> var.getShape()
            (6,)
            >>> var.getArithmeticFaceValue().getShape()
            (17,)
            >>> var.getGrad().getShape()
            (2, 6)
            >>> var.getFaceGrad().getShape()
            (2, 17)
        """
        return (Variable.getShape(self) 
                or (self.elementshape + self._getShapeFromMesh(self.getMesh())) 
                or ())

    def _OperatorVariableClass(self, baseClass=None):
        baseClass = Variable._OperatorVariableClass(self, baseClass=baseClass)
                                     
        class _MeshOperatorVariable(baseClass):
            def __init__(self, op, var, opShape=None, canInline=True,
                         *args, **kwargs):
                mesh = reduce(lambda a, b: a or b, 
                              [getattr(v, "mesh", None) for v in var])
                opShape = reduce(lambda a, b: a or b, 
                                 [opShape] + [getattr(v, "opShape", None) for v in var])
                elementshape = reduce(lambda a, b: a or b, 
                                      [getattr(v, "elementshape", None) for v in var])

                baseClass.__init__(self, mesh=mesh, op=op, var=var, 
                                   opShape=opShape, canInline=canInline,
                                   elementshape=elementshape,
                                   *args, **kwargs)
                                 
            def getRank(self):
                return len(self.opShape) - 1
                
        return _MeshOperatorVariable
                          
    def getRank(self):
        return len(self.elementshape)
        
    def setValue(self, value, unit = None, array = None, where = None):
        if where is not None:
            shape = numerix.getShape(where)
            if shape != self.getShape() \
              and shape == self._getShapeFromMesh(mesh=self.getMesh()):
                for dim in self.elementshape:
                    where = numerix.repeat(where[numerix.newaxis, ...], repeats=dim, axis=0)
        
        return Variable.setValue(self, value=value, unit=unit, array=array, where=where)

    def dot(self, other):
        return self._BinaryOperatorVariable(lambda a,b: numerix.dot(a,b), other, 
                                            canInline=False)

    def __getstate__(self):
        """
        Used internally to collect the necessary information to ``pickle`` the 
        `_MeshVariable` to persistent storage.
        """
        return {
            'mesh': self.mesh,
            'name': self.name,
            'value': self.getValue(),
            'unit': self.getUnit(),
            'cached': self._cached
        }


