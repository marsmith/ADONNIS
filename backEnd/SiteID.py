degree_sign= u'\N{DEGREE SIGN}'

class SiteID(object):
    '''
    Description
    ---------------------------------------------------------------------------
    Represents a USGS groundwater site identifcation number (8 to 10 digits long)
    There are one to two components for every SiteID:
     (value)        | (extension)
        00010000        --
        10010000        12

    Watersheds are a national level number
    These are not included in the main ID portion but will become important later on
    Values are 8 digits long
    Extensions may be None, 01 to 99. 

    Class Variables
    ---------------------------------------------------------------------------
    fullID [number] : Raw number in integer form
    watershed [number]: Watershed component
    value [number] : Value component
    extension [number]: Extension component (default= None)
    id [number] The actually used Id portion (value + extension)
    Usage
    ---------------------------------------------------------------------------
    >>> siteIDObj = SiteID("99876543")
    >>> siteIDObj2 = SiteID("9987654313")
    >>> print(siteIDObj)
    >>> print(siteIDObj < siteIDObj2)
    99876543
    True
    '''

    def __init__(self,stringg):
        '''
        Construct a net SiteID object based on a string.
        The length of the string must be in range [8,10] (inclusive)
        '''

        assert(len(stringg) >= 8)
        self.value = int(stringg[0:8])
        self.id = int(stringg)
        self.watershed = 0
        self.fullID = int(int(self.watershed) + self.id)

        if len(stringg) > 8:
            self.extension = int(stringg[8:])
            #assert(self.extension <= 99 and self.extension > 0)
            
            
        else:
            self.extension = None
    

    def __str__(self):
        '''
        Returns a string version of the SiteID. Preserves all digits!
        i.e. A SiteID of 00454950 will NOT become "4595"

        Returns [str]
        '''
        if self.extension is None:
            return str("%08d"%self.id)
        else:
            
            return str("%08d%02d" %(self.value,self.extension))
    def __lt__(self,other):
        '''
        Performs a '<' comparison between the calling SiteID and other

        other [number or SiteID]: The other side of the '<' to compare to

        Returns [bool]: True if self is less than other. False otherwise.
        '''
        if isinstance(other,int):
            return self.fullID < other
        elif isinstance(other,SiteID):
            if self.watershed == other.watershed:
                if self.value == other.value:
                    if self.extension is None and other.extension is None:
                        return False
                    else:
                        if self.extension is None:
                            return False
                        else:
                            return True
                else:
                    return self.value < other.value
            else:
                return self.watershed < other.watershed
        else:
            raise RuntimeError("ERROR: SiteID __lt__ secondary argument not compatible!")
    def __le__(self,other):
        '''
        Performs a '<=' comparison between the calling SiteID and other

        other [number or SiteID]: The other side of the '<=' to compare to

        Returns [bool]: True if self is less than or equal to other. False otherwise.
        '''
        return self < other or self.__eq__(other)
    def __ge__(self,other):
        '''
        Performs a '>=' comparison between the calling SiteID and other

        other [number or SiteID]: The other side of the '>=' to compare to

        Returns [bool]: True if self is greater than or equal to other. False otherwise.
        '''
        return self > other or self.__eq__(other)
    def __gt__(self,other):
        '''
        Performs a '>' comparison between the calling SiteID and other

        other [number or SiteID]: The other side of the '>' to compare to

        Returns [bool]: True if self is greater than to other. False otherwise.
        '''
        return not self <= other
    def __eq__(self,other):
        '''
        Performs a '==' comparison between the calling SiteID and other

        other [number or SiteID]: The other side of the '==' to compare to

        Returns [bool]: True if self is equal to other. False otherwise.
        '''
        if isinstance(other,int):
            return self.fullID == other
        else:
            return self.fullID == other.fullID

    def __add__(self, other):
        '''
        Performs addition operation between SiteID and other

        other [Number or SiteID]: The second operand.

        Returns [Number or SiteID]: If other is Number, we will calculate a new SiteID object
        based on the distance traveled.

        If other is SiteID, we will do nothing
        '''
        if type(self) is SiteID and type(other) is SiteID:
            if self.watershed != other.watershed:
                # Warning! Adding two different watershed ID's may proove bad
                raise RuntimeWarning("WARNING! Adding two different watersheded ID's")                      
            return SiteID("{0}".format(self.fullID + other.fullID))          
        
        elif type(self) is SiteID:  
            n = SiteID(str(self))
            n.watershed = self.watershed
            n.extension = self.extension          
            if int(other) != other and int(other) < 1:                
                e = int(other * 100)
                
                if not n.extension is None:
                    n.extension += e
                    # We have an extension; make sure not to go over
                    if n.extension > 99:
                        n.extension = None
                        n.value += 1 # Increment the value up by one
                else:
                    n.extension = e   
                                  
            else:
                n.value += int(other)
                # We do not need to add an extension
                if not n.extension is None:
                    n.extension = None  

            if not n.extension is None:
                n.id = int(str(n.value) + str(n.extension)) 
            else:
                n.id = n.value

            n.fullID = n.id # Additional tagon since the watershed change
            return n

        elif type(other) is SiteID:
            return other.fullID + int(self) #?
        else:
            return int(self) + int(other)

    def __sub__(self, other):
        '''
        Performs subtraction between SiteID (self) and other

        other [Number or SiteID]: The second operand

        Returns [Number or SiteID]: If other is Number, then we will calculate a new SiteID
        based on that distance.

        If other is a SiteID, we will return the distance that would result in the difference in SiteID number 
        '''
        if type(self) is SiteID and type(other) is SiteID:
            if self.watershed != other.watershed:
                # Warning! Subtracting two different watershed ID's may proove bad
                raise RuntimeWarning("WARNING! Subtracting two different watersheded ID's")     
            else:
                # Need to find the difference in value
                inty = self.value - other.value
                e1 = 0.0
                if not self.extension is None:
                    e1 = self.extension / 100
                e2 = 0.0
                if not other.extension is None:
                    e2 = other.extension / 100
            return inty + e1 - e2
        
        elif type(self) is SiteID:
            # Does the current site have extensions
            n = SiteID(str(self))
            n.watershed = self.watershed
            n.extension = self.extension
            if int(other) != other and int(other) < 1: 
                e = int(other * 100)                
                if not n.extension is None:
                    # We have an extension already
                    if e == 0:
                        n.extension -= 1
                    else:
                        n.extension -= e
                else:
                    # We dont have an extension already
                    n.value -= 1
                    if e == 0:
                        n.extension = 99
                    else:
                        n.extension = 100 - e
                if n.extension <= 0:
                    n.extension = None
                    n.value -= 1
                                       
            else:
                n.value -= int(other)
                # We do not need to add an extension
                if not n.extension is None:
                    n.extension = None

            if not n.extension is None:
                n.id = int(str(n.value) + str(n.extension)) 
            else:
                n.id = n.value

            n.fullID = n.id
            return n
 

        elif type(other) is SiteID:
            return abs(other.fullID - int(self))
        else:
            return abs(int(self) - int(other))



    __repr__ = __str__