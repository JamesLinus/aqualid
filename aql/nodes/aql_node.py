
# Copyright (c) 2011-2013 The developers of Aqualid project - http://aqualid.googlecode.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom
# the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE
# AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

__all__ = (
  'Node',
)

import os
import binascii
import itertools

from aql.utils import simpleObjectSignature, Chdir
from aql.util_types import toSequence, AqlException

from aql.values import ValueBase, pickleable

#//===========================================================================//

class   ErrorNodeDependencyInvalid( AqlException ):
  def   __init__( self, dep ):
    msg = "Invalid node dependency: %s" % (dep,)
    super(ErrorNodeDependencyInvalid, self).__init__( msg )

class   ErrorNoTargets( AqlException ):
  def   __init__( self, node ):
    msg = "Node targets are not built or set yet: %s" % (node.getBuildStr( brief = False ))
    super(ErrorNoTargets, self).__init__( msg )

class   ErrorNoImplicitDeps( AqlException ):
  def   __init__( self, node ):
    msg = "Node implicit dependencies are not built or set yet: %s" % (node.getBuildStr( brief = False ))
    super(ErrorNoImplicitDeps, self).__init__( msg )

class   ErrorNodeNotInitialized( AqlException ):
  def   __init__( self, node ):
    msg = "Node is not initialized yet: %s" % (node, )
    super(ErrorNodeNotInitialized, self).__init__( msg )

#//===========================================================================//

def   _actualDeps( vfile, dep_keys ):
  values = vfile.getValues( dep_keys )
  
  if values is None:
    # if __debug__:
    #   print( "ideps are None")
    return False
  
  for key, value in zip(dep_keys, values):
    if not value:
      # if __debug__:
      #   print( "idep '%s' is false" % (value,))
      return False
    
    actual_value = value.getActual()
    if value != actual_value:
      # if __debug__:
      #   print( "idep '%s' changed to '%s'" % (value, actual_value))
      vfile.replaceValue( key, actual_value )
      return False
  
  return True

#//===========================================================================//

def   _actualValues( values ):
  if values is None:
    return False
  
  for value in values:
    if not value.isActual():
      return False
      
  return True

#//===========================================================================//

@pickleable
class   NodeValue (ValueBase):
  
  __slots__ = (
    'targets',
    'itargets',
    'idep_keys',
  )
  
  #//-------------------------------------------------------//
  
  def   __new__( cls, name, signature = None, targets = None, itargets = None, idep_keys = None ):
    
    self = super(NodeValue,cls).__new__(cls, name, signature )
    
    self.targets    = targets
    self.itargets   = itargets
    self.idep_keys  = idep_keys
    
    return self
  
  #//-------------------------------------------------------//
  
  def   __eq__( self, other):
    return (type(self) == type(other)) and (self.__getnewargs__() == other.__getnewargs__())
  
  #//-------------------------------------------------------//
  
  def   get(self):
    return self.name
  
  #//-------------------------------------------------------//
  
  def     __getnewargs__(self):
    return self.name, self.signature, self.targets, self.itargets, self.idep_keys
  
  #//-------------------------------------------------------//
  
  def   __bool__( self ):
    return (self.signature is not None) and (self.targets is not None)
  
  #//-------------------------------------------------------//

#//===========================================================================//

#noinspection PyAttributeOutsideInit
class Node (object):
  
  __slots__ = \
  (
    'builder',
    'builder_data',
    'options',
    
    'name',
    'signature',
    
    'cwd',
    'sources',
    'source_values',
    'dep_nodes',
    'dep_values',
    
    'targets',
    'itargets',
    'ideps',
  )
  
  #//-------------------------------------------------------//
  
  def   __init__( self, builder, sources, cwd = None ):
    
    self.builder = builder
    self.options = getattr( builder, 'options', None )
    self.builder_data = None
    
    if cwd is None:
      self.cwd = os.path.abspath( os.getcwd() )
    else:
      self.cwd = cwd
    
    self.sources = toSequence( sources )
    self.source_values = None
    self.dep_nodes = set()
    self.dep_values = []

    self.name = None
    self.signature = None
    
    self.targets = None
    self.itargets = None
    self.ideps = None
  
  #//=======================================================//
  
  def   depends( self, dependencies ):
    
    dep_nodes = self.dep_nodes
    dep_values = self.dep_values
    
    for value in toSequence( dependencies ):
      if isinstance( value, Node ):
        dep_nodes.add( value )
      
      elif isinstance( value, ValueBase ):
        dep_values.append( value )
      
      else:
        raise ErrorNodeDependencyInvalid( value )
    
    dep_values.sort( key = lambda v: v.name )
  
  #//=======================================================//
  
  def   getDepNodes(self):
    return self.dep_nodes
  
  #//=======================================================//
  
  def   getDepValues(self):
    dep_nodes = self.dep_nodes
    dep_values = self.dep_values
    
    if not dep_nodes:
      return dep_values
    
    for node in dep_nodes:
      dep_values += toSequence( node.getTargetValues() )
    
    dep_nodes.clear()
    dep_values.sort( key = lambda v: v.name )
    
    return dep_values
  
  #//=======================================================//
  
  def   initiate(self):
    
    if self.source_values is None:
      self.builder = self.builder.initiate()
      self.__setSourceValues()
      self.targets = self.builder.getTargetValues( self )
  
  #//=======================================================//
  
  def   __setSourceValues(self):
    values = []
    
    makeValue = self.builder.makeValue
    
    with Chdir(self.cwd):
      for src in self.sources:
        
        if isinstance( src, Node ):
          values += src.getTargetValues()
        
        elif isinstance( src, ValueBase ):
          values.append( src )
        
        else:
          value = makeValue( src, use_cache = True )
          values.append( value )
      
    self.sources = None
    self.source_values = tuple(values)
  
  #//=======================================================//
  
  def   getSources(self):
    if __debug__:
      if self.source_values is None:
        raise ErrorNodeNotInitialized( self )
    
    return tuple( src.get() for src in self.source_values )
  
  #//=======================================================//
  
  def   getSourceValues(self):
    if self.source_values is None:
      raise ErrorNodeNotInitialized( self )
    
    return self.source_values
  
  #//=======================================================//
  
  def   getSourceNodes(self):
    return tuple( node for node in self.sources if isinstance(node,Node) )
  
  #//=======================================================//
  
  def   __initiateIds(self):
    
    if __debug__:
      if self.source_values is None:
        raise ErrorNodeNotInitialized( self )
    
    if self.name is None:
      self.__setName()
      self.__setSignature()
    
  #//=======================================================//
  
  def   __setName(self ):
    
    targets = self.targets
    if targets:
      names = sorted( value.valueId() for value in targets )
    else:
      sources = sorted( self.getSourceValues(), key = lambda v: v.name )
      names = [ self.builder.name ]
      names += [ value.name for value in sources ]
    
    self.name = simpleObjectSignature( names )
  
  #//=======================================================//
  
  def   __setSignature( self ):
    
    sign  = [ self.builder.signature ]
    
    # if __debug__:
    #   srcs = tuple( src.name for src in self.getSourceValues())
    #   print("%s: sources: %s" % (self.getName(), srcs) )
    
    for value in self.getSourceValues():
      if value:
        sign.append( value.signature )
      else:
        sign = None
        break
    
    # if __debug__:
    #   deps = tuple( dep.name for dep in self.getDepValues())
    #   print("%s: deps: %s" % (self.getName(), deps) )
    
    if sign is not None:
      deps = self.getDepValues()
      
      for value in deps:
        if value:
          sign.append( value.name )
          sign.append( value.signature )
        else:
          sign = None
          break
    
    # if __debug__:
    #   print("%s: sig: %s (%s)" % (self.getName(), sign, type(sign)) )
    #   print("%s: sig: %s" % (self.getName(), tuple(map(id, sign))) )
    #   print("%s: dump sig: %s" % (self.getName(), dumpData( sign ) ) )
    
    if sign is not None:
      sign = simpleObjectSignature( sign )
    
    # if __debug__:
    #   print("%s: sig: %s" % (self.getName(), sign) )
    
    self.signature = sign
  
  #//=======================================================//
  
  def   shrink(self):
    
    self.cwd = None
    self.dep_nodes = None
    self.dep_values = None
    self.sources = None
    self.source_values = None
    
    self.name = None
    self.signature = None
    self.builder = None
    self.builder_data = None
    self.options = None
    self.ideps = None
  
  #//=======================================================//
  
  def   getName(self):
    return binascii.hexlify( self.name )
  
  #//=======================================================//
  
  def   save( self, vfile ):
    if __debug__:
      if self.itargets is None:
        raise ErrorNoTargets( self )
      if self.ideps is None:
        raise ErrorNoImplicitDeps( self )
    
    idep_keys = vfile.addValues( self.ideps )
    
    node_value = NodeValue( name = self.name, signature = self.signature,
                            targets = self.targets, itargets = self.itargets, idep_keys = idep_keys )
    
    vfile.addValue( node_value )
  
  #//=======================================================//
  
  def   load( self, vfile ):
    
    self.__initiateIds()
    
    node_value = NodeValue( name = self.name )
    
    node_value = vfile.findValue( node_value )
    if node_value:
      node_targets = node_value.targets
      if node_targets is not None:
        self.targets = node_targets
      
      self.itargets = node_value.itargets
  
  #//=======================================================//
  
  def   build(self):
    output = self.builder.build( self )
    return output
  
  #//=======================================================//
  
  def   prebuild(self):
    return self.builder.prebuild( self )
  
  #//=======================================================//
  
  def   prebuildFinished(self, prebuild_nodes ):
    return self.builder.prebuildFinished( self, prebuild_nodes )
  
  #//=======================================================//
  
  def   clear( self, vfile ):
    """
    Cleans produced values
    """
    self.load( vfile )
    
    node_value = NodeValue( name = self.name )
    
    vfile.removeValues( [ node_value ] )
    
    try:
      self.builder.clear( self )
    except Exception:
      pass
    
  #//=======================================================//
  
  def   removeTargets(self):
    targets = itertools.chain( toSequence( self.targets ), toSequence( self.itargets ) )
    
    for value in targets:
      value.remove()
  
  #//=======================================================//
  
  def   isActual( self, vfile ):
    
    self.__initiateIds()
    
    if not self.signature:
      # if __debug__:
      #   print( "Sources signature is False" )
      return False
    
    node_value = NodeValue( name = self.name )
    
    node_value = vfile.findValue( node_value )
    
    if node_value is None:
      return False
    
    if self.signature != node_value.signature:
      # if __debug__:
      #   print( "Sources signature is changed: %s - %s" % (self.signature, node_value.signature) )
      return False
    
    targets   = node_value.targets
    itargets  = node_value.itargets
    idep_keys = node_value.idep_keys
    
    if not (_actualDeps( vfile, idep_keys ) and _actualValues( targets ) and _actualValues( itargets )):
      # if __debug__:
      #   print( "targets/itargets/ideps are not actual: %s" % (self.getName(),))
      return False
    
    self.targets  = targets
    self.itargets = itargets
    
    return True
    
  #//=======================================================//
  
  def   get(self):
    return self.getTargets()
  
  #//=======================================================//
  
  def   getTargets(self):
    return tuple( target.get() for target in toSequence( self.targets ) )
  
  #//=======================================================//
  
  def   getTargetValues(self):
    return toSequence( self.targets )
  
  #//=======================================================//
  
  def   getSideEffectValues(self):
    return toSequence( self.itargets )
  
  #//=======================================================//
  
  def   setTargets( self, targets, itargets = None, ideps = None, valuesMaker = None ):
    
    self.__initiateIds()
    
    if valuesMaker is None:
      valuesMaker = self.builder.makeValues
    
    self.targets  = valuesMaker( targets,   use_cache = False )
    self.itargets = valuesMaker( itargets,  use_cache = False )
    self.ideps    = valuesMaker( ideps,     use_cache = True )
    
  #//=======================================================//
  
  def   setFileTargets( self, targets, itargets = None, ideps = None ):
    self.setTargets( targets = targets, itargets = itargets, ideps = ideps,
                     valuesMaker = self.builder.makeFileValues )
  
  #//=======================================================//
  
  @staticmethod
  def   __makeArgsStr( args, brief ):
    args = [ str(arg) for arg in toSequence(args) ]
    
    if not brief or (len(args) < 3):
      return ' '.join( args )
    
    wish_size = 128
    
    args_str = [ args.pop(0) ]
    last = args.pop()
    
    size = len(args_str[0]) + len(last)
    
    for arg in args:
      size += len(arg)
      
      if size > wish_size:
        args_str.append('...')
        break
      
      args_str.append( arg )
      
    args_str.append( last )
    
    return ' '.join( args_str )
  
  #//=======================================================//
  
  def   getBuildStr( self, brief = True ):
    
    args = self.builder.getBuildStrArgs( self, brief = brief )
    
    args    = iter(args)
    name    = next(args, self.builder.__class__.__name__ )
    sources = next(args, None )
    targets = next(args, None )
    
    build_str  = str(name)
    sources = self.__makeArgsStr( sources, brief )
    targets = self.__makeArgsStr( targets, brief )
    
    if sources:
      build_str += ": " + sources
    if targets:
      build_str += " => " + targets
    
    return build_str
  
  #//-------------------------------------------------------//
  
  def   getClearStr( self, brief = True ):
    
    args = self.builder.getBuildStrArgs( self, brief = brief )
    
    args    = iter(args)
    name    = next(args, None )
    sources = next(args, None )
    targets = next(args, None )
    
    return self.__makeArgsStr( targets, brief )
  
  #//=======================================================//
  
  def   split( self, builder ):
    nodes = []
    
    cwd = self.cwd
    options = self.options
    
    dep_values = self.getDepValues()
    for src_value in self.getSourceValues():
      node = Node( builder, src_value, cwd )
      node.dep_values = dep_values
      nodes.append( node )
    
    return nodes
  
  #//=======================================================//
  
