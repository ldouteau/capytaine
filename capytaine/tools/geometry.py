#!/usr/bin/env python
#  -*- coding: utf-8 -*-
"""
Freely adapted from meshmagick.
"""

from abc import ABC, abstractmethod

import numpy as np


###########################################
#  DECORATOR FOR INPLACE TRANSFORMATIONS  #
###########################################

def inplace_transformation(inplace_function):
    """Decorator for methods transforming 3D objects:
    * Add the optional argument `inplace` to return a new object instead of doing the transformation in place.
    * If the object has properties cached in an "__internals__" dict, they are deleted.
    """
    def enhanced_inplace_function(self, *args, inplace=True, name=None, **kwargs):
        if not inplace:
            object3d = self.copy(name=name)
        else:
            object3d = self
        inplace_function(object3d, *args, **kwargs)
        if hasattr(object3d, '__internals__'):
            object3d.__internals__.clear()
        return object3d
    return enhanced_inplace_function


##############################
#  ABSTRACT 3D OBJECT CLASS  #
##############################

class Abstract3DObject(ABC):
    """Abstract class for 3d objects that can be transformed in 3d.
    The child classes have to define `mirror`, `rotate` and `translate`,
    then more routines such as `translate_x` and `translated` are automatically available."""

    @abstractmethod
    def translate(self, vector):
        pass

    @abstractmethod
    def rotate(self, axis, angle):
        pass

    @abstractmethod
    def mirror(self, plane):
        pass

    @inplace_transformation
    def translate_x(self, tx):
        return self.translate((tx, 0., 0.))

    @inplace_transformation
    def translate_y(self, ty):
        return self.translate((0., ty, 0.))

    @inplace_transformation
    def translate_z(self, tz):
        return self.translate((0., 0., tz))

    @inplace_transformation
    def rotate_x(self, thetax):
        return self.rotate(Ox_axis, thetax)

    @inplace_transformation
    def rotate_y(self, thetay):
        return self.rotate(Oy_axis, thetay)

    @inplace_transformation
    def rotate_z(self, thetaz):
        return self.rotate(Oz_axis, thetaz)

    @inplace_transformation
    def rotate_angles(self, angles):
        thetax, thetay, thetaz = angles
        self.rotate(Ox_axis, thetax)
        self.rotate(Oy_axis, thetay)
        self.rotate(Oz_axis, thetaz)
        return self

    def translated(self, *args, **kwargs):
        return self.translate(*args, inplace=False, **kwargs)

    def rotated(self, *args, **kwargs):
        return self.rotate(*args, inplace=False, **kwargs)

    def mirrored(self, *args, **kwargs):
        return self.mirror(*args, inplace=False, **kwargs)

    def translated_x(self, *args, **kwargs):
        return self.translate_x(*args, inplace=False, **kwargs)

    def translated_y(self, *args, **kwargs):
        return self.translate_y(*args, inplace=False, **kwargs)

    def translated_z(self, *args, **kwargs):
        return self.translate_z(*args, inplace=False, **kwargs)

    def rotated_x(self, *args, **kwargs):
        return self.rotate_x(*args, inplace=False, **kwargs)

    def rotated_y(self, *args, **kwargs):
        return self.rotate_y(*args, inplace=False, **kwargs)

    def rotated_z(self, *args, **kwargs):
        return self.rotate_z(*args, inplace=False, **kwargs)

    def rotated_angles(self, *args, **kwargs):
        return self.rotate_angles(*args, inplace=False, **kwargs)


######################
#  HELPER FUNCTIONS  #
######################

def test_orthogonal_vectors(vec1, vec2) -> bool:
    return np.isclose(np.linalg.norm(np.asarray(vec1) @ np.asarray(vec2)), 0.0, atol=1e-6)


def test_parallel_vectors(vec1, vec2) -> bool:
    return np.isclose(np.linalg.norm(np.cross(vec1, vec2)), 0.0, atol=1e-6)


################
#  AXIS CLASS  #
################

class Axis(Abstract3DObject):
    def __init__(self, vector=(1, 0, 0), point=(0, 0, 0)):
        assert len(vector) == 3, "Vector of an axis should be given as a 3-ple of values."
        assert len(point) == 3, "Point of an axis should be given as a 3-ple of values."
        vector = np.array(vector, np.float)
        self.vector = vector / np.linalg.norm(vector)
        self.point = np.array(point, np.float)

    def __repr__(self):
        return f"Axis(vector={self.vector}, point={self.point})"

    def __contains__(self, other_point):
        if len(other_point) == 3:
            other_point = np.asarray(other_point, dtype=np.float)
            return test_parallel_vectors(other_point - self.point, self.vector)
        else:
            raise NotImplementedError

    def __eq__(self, other):
        if isinstance(self, Axis):
            return self.point in other and test_parallel_vectors(self.vector, other.vector)
        else:
            return NotImplemented

    def is_orthogonal_to(self, item):
        if isinstance(item, Plane):
            return test_parallel_vectors(self.vector, item.normal)
        elif len(item) == 3:  # The item is supposed to be a vector given as a 3-ple
            return test_orthogonal_vectors(self.vector, item)
        else:
            raise NotImplementedError

    ################################
    #  Transformation of the axis  #
    ################################

    def copy(self, name=None):
        return Axis(vector=self.vector.copy(), point=self.point.copy())

    @inplace_transformation
    def translate(self, vector):
        self.point += vector
        return self

    @inplace_transformation
    def rotate(self, axis, angle):
        rot_matrix = axis.rotation_matrix(angle)
        self.point = rot_matrix @ self.point
        self.vector = rot_matrix @ self.vector
        return self

    @inplace_transformation
    def mirror(self, plane):
        self.point -= 2 * (self.point @ plane.normal - plane.c) * plane.normal
        self.vector -= 2 * (self.vector @ plane.normal) * plane.normal
        return self

    ###########
    #  Other  #
    ###########

    def rotation_matrix(self, theta):
        """Rotation matrix around the vector according to Rodrigues' formula."""
        ux, uy, uz = self.vector
        W = np.array([[0, -uz, uy],
                      [uz, 0, -ux],
                      [-uy, ux, 0]])
        return np.identity(3) + np.sin(theta)*W + 2*np.sin(theta/2)**2 * (W @ W)


Ox_axis = Axis(vector=(1, 0, 0), point=(0, 0, 0))
Oy_axis = Axis(vector=(0, 1, 0), point=(0, 0, 0))
Oz_axis = Axis(vector=(0, 0, 1), point=(0, 0, 0))


#################
#  PLANE CLASS  #
#################

class Plane(Abstract3DObject):
    def __init__(self, normal=(0.0, 0.0, 1.0), point=(0.0, 0.0, 0.0)):
        normal = np.asarray(normal, dtype=np.float)
        self.normal = normal / np.linalg.norm(normal)
        self.point = np.asarray(point, dtype=np.float)

    def __repr__(self):
        return f"Plane(normal={self.normal}, point={self.point})"

    def __contains__(self, other):
        if isinstance(other, Axis):
            return other.point in self and test_orthogonal_vectors(self.normal, other.vector)
        elif len(other) == 3:
            return test_orthogonal_vectors(other - self.point, self.normal)
        else:
            raise NotImplementedError

    def __eq__(self, other):
        if isinstance(other, Plane):
            return other.point in self and test_parallel_vectors(self.normal, other.normal)
        else:
            return NotImplemented

    def is_orthogonal_to(self, other):
        if isinstance(other, Axis):
            return test_parallel_vectors(self.normal, other.vector)
        elif isinstance(other, Plane):
            return test_orthogonal_vectors(self.normal, other.normal)
        elif len(other) == 3:  # The other is supposed to be a vector given as a 3-ple
            return test_parallel_vectors(self.normal, other)
        else:
            raise NotImplementedError

    @property
    def c(self):
        """Distance from plane to origin."""
        return np.linalg.norm(self.normal @ self.point)

    #################################
    #  Transformation of the plane  #
    #################################

    def copy(self, name=None):
        return Plane(normal=self.normal.copy(), point=self.point.copy())

    @inplace_transformation
    def translate(self, vector):
        self.point = self.point + np.asarray(vector)
        return self

    @inplace_transformation
    def rotate(self, axis, angle):
        rot_matrix = axis.rotation_matrix(angle)
        self.point = rot_matrix @ self.point
        self.normal = rot_matrix @ self.normal
        return self

    @inplace_transformation
    def mirror(self, plane):
        self.point -= 2 * (self.point @ plane.normal - plane.c) * plane.normal
        self.normal -= 2 * (self.vector @ plane.normal) * plane.normal
        return self

    ###########
    #  Other  #
    ###########

    def distance_to_point(self, points):
        """
        Return the orthogonal distance of points with respect to the plane

        Parameters
        ----------
        points : ndarray
            Array of points coordinates

        Returns
        -------
        dist : ndarray
            Array of distances of points with respect to the plane
        """
        return np.dot(points, self.normal) - self.c

    def get_edge_intersection(self, p0, p1):
        """
        Returns the coordinates of the intersection point between the plane and the edge P0P1.

        Parameters
        ----------
        p0 : ndarray
            Coordinates of point p0
        p1 : ndarray
            Coordinates of point P1

        Returns
        -------
        I : ndarray
            Coordinates of intersection point
        """
        assert len(p0) == 3 and len(p1) == 3

        p0n = np.dot(p0, self.normal)
        p1n = np.dot(p1, self.normal)
        t = (p0n - self.c) / (p0n - p1n)
        if t < 0. or t > 1.:
            raise RuntimeError('Intersection is outside the edge')
        return (1-t) * p0 + t * p1


yOz_Plane = Plane(normal=(1, 0, 0), point=(0, 0, 0))
xOz_Plane = Plane(normal=(0, 1, 0), point=(0, 0, 0))
xOy_Plane = Plane(normal=(0, 0, 1), point=(0, 0, 0))

