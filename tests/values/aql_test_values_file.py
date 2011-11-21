﻿import sys
import os.path
import timeit

sys.path.insert( 0, os.path.normpath(os.path.join( os.path.dirname( __file__ ), '..') ))

from aql_tests import testcase, skip, runTests
from aql_temp_file import Tempfile
from aql_value import Value, NoContent
from aql_str_value import StringValue
from aql_value_pickler import ValuePickler, pickleable
from aql_values_file import ValuesFile


#//===========================================================================//

@testcase
def test_value_pickler(self):
  
  with Tempfile() as tmp:
    vfile = ValuesFile( tmp.name )
    vfile.selfTest()
    
    value1 = StringValue( "target_url1", "http://aql.org/download" )
    value2 = StringValue( "target_url2", "http://aql.org/download2" )
    value3 = StringValue( "target_url3", "http://aql.org/download3" )
    
    values = [ value1, value2, value3 ]
    
    vfile.addValues( values ); vfile.selfTest()
    
    s_values = vfile.findValues( values )
    
    self.assertEqual( values, s_values )
    
    print("values: %s" % str(values) )
    print("s_values: %s" % str(s_values) )

#//===========================================================================//

if __name__ == "__main__":
  runTests()
