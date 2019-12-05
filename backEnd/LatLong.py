#!/usr/bin/python3.6


import numpy

degree_sign= u'\N{DEGREE SIGN}'

class LatLong(object):
    '''
    Description
    ---------------------------------------------------------------------------
    Represents a Latitude and Longitudinal coordinates in
    decimal degrees. Takes decimal degree latitude and longitudinal
    values and separates into constituent parts (degrees, minutes and seconds)

    Class Variables
    ---------------------------------------------------------------------------
    dLat [number] : Degrees Latitude
    mLat [number] : Minutes Latitude
    sLat [number] : Seconds Latitude
    dLong [number] : Degrees Longitude
    mLong [number] : Minutes Longitude
    sLong [number] : Seconds Longitude
    srcLat [number] : The raw float decimal number latitude
    srcLong [number] : The raw float decimal number longitude

    Usage
    ---------------------------------------------------------------------------
    >>> latLong1 = LatLong(-75.651190010722587,43.800854964303937)
    >>> print(latLong)
    -76.0° 20.0' 55.715961398686886", 43.0° 48.0' 3.07787149417436"
    
    '''
    def __init__(self,decimalDegreesLat,decimalDegreesLong):
        '''
        Constructs a new LatLong Object.

        decimalDegreesLat: Raw decimal value of latitude (ex.-75.651190010722587 )        
        decimalDegreesLong: Raw decimal value of longitude (ex. 43.800854964303937 )
        
        '''
        self.dLat = numpy.floor(decimalDegreesLat)
        self.mLat = numpy.floor(60 * numpy.abs(decimalDegreesLat - self.dLat))
        self.sLat = 3600 * numpy.abs(decimalDegreesLat - self.dLat) - 60 * self.mLat
        
        self.dLong = numpy.floor(decimalDegreesLong)
        self.mLong = numpy.floor(60 * numpy.abs(decimalDegreesLong - self.dLong))
        self.sLong = 3600 * numpy.abs(decimalDegreesLong - self.dLong) - 60 * self.mLong
        self.srcLat = decimalDegreesLat
        self.srcLong = decimalDegreesLong
    def __str__(self):
        ''' 
        Returns a string representation of the LatLong object.
        '''
        return "{0}{1} {2}\' {3}\", {4}{5} {6}\' {7}\"".format(
            self.dLat,degree_sign,self.mLat,self.sLat,
            self.dLong,degree_sign,self.mLong,self.sLong
        )
    def __eq__(self,other):
        '''
        Returns True if both objects are equal. False otherwise.
        other[LatLong]: The other LatLong object to compare self to.
        Raises RuntimeError if 'other' is not of type LatLong
        '''
        if isinstance(other,LatLong):
            return self.srcLat == other.srcLat and self.srcLong == other.srcLong
        else:
            raise RuntimeError("LatLong.__eq__ failed! Argument of invalid type")
    __repr__ = __str__