#!/usr/bin/env python
#
# This file is protected by Copyright. Please refer to the COPYRIGHT file distributed with this 
# source distribution.
# 
# This file is part of REDHAWK Basic Components BurstDeserializer.
# 
# REDHAWK Basic Components BurstDeserializer is free software: you can redistribute it and/or modify it under the terms of 
# the GNU Lesser General Public License as published by the Free Software Foundation, either 
# version 3 of the License, or (at your option) any later version.
# 
# REDHAWK Basic Components BurstDeserializer is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; 
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License along with this 
# program.  If not, see http://www.gnu.org/licenses/.

import unittest
import ossie.utils.testing
import os
from bulkio import BULKIO__POA, BULKIO
from bulkio import BULKIO__POA as _BULKIO__POA
from omniORB import any
from ossie.utils.bulkio import bulkio_data_helpers
from ossie.utils import sb
import time

class MyDataSink(sb.DataSink):
    """subclass sb.DataSink to use MyArraySink
    """
    def getPort(self, portName):
        if str(portName) == "xmlIn":
            return sb.DataSink.getPort(self, portName)
        try:
            self._sinkPortType = self.getPortType(portName)

            # Set up output array sink
            self._sink = StreamSink(eval(self._sinkPortType))

            if self._sink != None:
                self._sinkPortObject = self._sink.getPort()
                return self._sinkPortObject
            else:
                return None
            pass
        except Exception, e:
            print self.className + ":getPort(): failed " + str(e)
        return None

class StreamSink(bulkio_data_helpers.ProbeSink):
    def __init__(self, porttype):
        bulkio_data_helpers.ProbeSink.__init__(self, porttype)
        self.finished={}
        self.last=time.time()
    
    def stop(self):
        pass
        
    def pushSRI(self, H):
        """
        Stores the SteramSRI object regardless that there is no need for it

        Input:
            <H>    The StreamSRI object containing the information required to
                   generate the header file
        """
        self.sri = H
        self.valid_streams[H.streamID] = H
        self.received_data[H.streamID] = []
        self.last = time.time()

    def pushPacket(self, data, ts, EOS, stream_id):
        """
        Appends the data to the end of the array.

        Input:
            <data>        The actual data to append to the array
            <ts>          The timestamp
            <EOS>         Flag indicating if this is the End Of the Stream
            <stream_id>   The unique stream id
        """
        self.last = time.time()
        self.port_lock.acquire()
        try:
            if not self.valid_streams.has_key(stream_id):
                log.warn("the received packet has the invalid stream ID: "+stream_id+". Valid stream IDs are:"+str(self.valid_streams.keys()))
            self.received_data[stream_id].extend(data)
            if EOS:
                self.finished[stream_id] = self.valid_streams[stream_id], self.received_data[stream_id]
                del self.valid_streams[stream_id]
                del self.received_data[stream_id]
                self.gotEOS = True
            else:
                self.gotEOS = False
        finally:
            self.port_lock.release()
    
    def getData(self,timeout=1.0):
        while True:
            if time.time()-self.last>timeout:
                self._done()
                break
            time.sleep(.1)

        return self.finished.copy()
    
    def _done(self):
        self.port_lock.acquire()
        try:
           for stream_id in self.valid_streams.keys():
                self.finished[stream_id] = self.valid_streams[stream_id], self.received_data[stream_id]
        finally:
           self.port_lock.release() 
        
        
class ResourceTests(ossie.utils.testing.ScaComponentTestCase):
    """Test for all resource implementations in BurstDeserializer"""

    def setUp(self):
        """Set up the unit test - this is run before every method that starts with test
        """
        ossie.utils.testing.ScaComponentTestCase.setUp(self)
        self.src = sb.DataSource()
        self.sink= sb.probeBULKIO()
        self.sink = MyDataSink()
        #self.sink = StreamSink(BULKIO__POA.dataDouble)
        
        #setup my components
        self.setupComponent()
        
        self.comp.start()
        self.src.start()
        self.sink.start()
        
        #do the connections
        self.src.connect(self.comp)
        self.comp.connect(self.sink)
        
    def tearDown(self):
        """Finish the unit test - this is run after every method that starts with test
        """
        self.comp.stop()
        #######################################################################
        # Simulate regular component shutdown
        self.comp.releaseObject()
        self.sink.stop()      
        ossie.utils.testing.ScaComponentTestCase.tearDown(self)

    def setupComponent(self):
        #######################################################################
        # Launch the resource with the default execparams
        execparams = self.getPropertySet(kinds=("execparam",), modes=("readwrite", "writeonly"), includeNil=False)
        execparams = dict([(x.id, any.from_any(x.value)) for x in execparams])
        execparams["DEBUG_LEVEL"]=4
        self.launch(execparams=execparams)

        #######################################################################
        # Verify the basic state of the resource
        self.assertNotEqual(self.comp, None)
        self.assertEqual(self.comp.ref._non_existent(), False)

        self.assertEqual(self.comp.ref._is_a("IDL:CF/Resource:1.0"), True)

        #######################################################################
        # Validate that query returns all expected parameters
        # Query of '[]' should return the following set of properties
        expectedProps = []
        expectedProps.extend(self.getPropertySet(kinds=("configure", "execparam"), modes=("readwrite", "readonly"), includeNil=True))
        expectedProps.extend(self.getPropertySet(kinds=("allocate",), action="external", includeNil=True))
        props = self.comp.query([])
        props = dict((x.id, any.from_any(x.value)) for x in props)
        # Query may return more than expected, but not less
        for expectedProp in expectedProps:
            self.assertEquals(props.has_key(expectedProp.id), True)

        #######################################################################
        # Verify that all expected ports are available
        for port in self.scd.get_componentfeatures().get_ports().get_uses():
            port_obj = self.comp.getPort(str(port.get_usesname()))
            self.assertNotEqual(port_obj, None)
            self.assertEqual(port_obj._non_existent(), False)
            self.assertEqual(port_obj._is_a("IDL:CF/Port:1.0"),  True)

        for port in self.scd.get_componentfeatures().get_ports().get_provides():
            port_obj = self.comp.getPort(str(port.get_providesname()))
            self.assertNotEqual(port_obj, None)
            self.assertEqual(port_obj._non_existent(), False)
            self.assertEqual(port_obj._is_a(port.get_repid()),  True)

    def pushData(self,inData, numPushes = 1, streamID='test_stream',eos=False):
        """The main engine for all the test cases - push data, and get output
           As applicable
        """
        #data processing is asynchronos - so wait until the data is all processed
        
        count=0
        startIndex=0
        numElements = len(inData)/numPushes
        for i in xrange(numPushes):
            endIndex = startIndex+numElements
            pushData =inData[startIndex:endIndex]
            if pushData:
                #need to use this lower method or it forces an SRI push
                self.src._pushPacketAllConnectedPorts(pushData,
                                                      self.src._startTime,
                                                      eos,
                                                      streamID)
            startIndex = endIndex
        out=[]
    
    def getData(self):
        sink = self.sink._sink
        return sink.getData()

    def main(self,inData, numPushes = 1, streamID='test_stream',eos=False):
        self.pushData(inData, numPushes, streamID, eos)
        return self.getData()
    
    def mainTestCase(self,yUnit=BULKIO.UNITS_TIME, numPushes=1,cx=0):
        #need to create a specific sri here to set the subsize appropraitely
        streamID = "a_test_stream"
        subsize=10
        numCols=30
        xdelta = .01
        ydelta = subsize*xdelta        
        
        sri = BULKIO.StreamSRI(1, .1, xdelta, BULKIO.UNITS_TIME, subsize, 0.0, ydelta, yUnit, cx,
                                                     streamID, True, [])
        self.src._pushSRIAllConnectedPorts(sri)
        inSignalLen = subsize*numCols
        if cx:
            inSignal = [float(x) for x in xrange(inSignalLen*2)]
        else:
            inSignal = [float(x) for x in xrange(inSignalLen)]
        outData = self.main(inSignal,streamID=sri.streamID,numPushes=numPushes)
        
        keys=outData.keys()
        keys.sort()
        
        if self.comp.transpose:
            self.assertEqual(len(outData),subsize)
        else:
            self.assertEqual(len(outData),numCols)
        for i in xrange(subsize):
            key = "%s_%s"%(sri.streamID,i)
            outSri, outSig = outData[key]

            if self.comp.transpose:                
                if cx:
                    inSigReal= inSignal[2*i::2*subsize]
                    inSigIm = inSignal[(2*i+1)::2*subsize]
                    exepectedSig = []
                    for vals in zip(inSigReal,inSigIm):
                        exepectedSig.extend(vals)
                else:
                    exepectedSig = inSignal[i::subsize]
                self.assertTrue(outSri.xdelta == sri.ydelta)
                self.assertTrue(outSri.xunits == sri.yunits)
                if yUnit==BULKIO.UNITS_TIME:
                    self.assertAlmostEqual(outSri.xstart, sri.xstart+sri.xdelta*i)
                else:
                    self.assertAlmostEqual(outSri.xstart, sri.ystart)
                    
            else:
                if cx:
                    exepectedSig = inSignal[i*2*subsize:(i+1)*2*subsize]
                else:
                    exepectedSig = inSignal[i*subsize:(i+1)*subsize]
                self.assertTrue(outSri.xdelta == sri.xdelta)
                self.assertTrue(outSri.xunits == sri.xunits)
                if yUnit==BULKIO.UNITS_TIME:
                    self.assertAlmostEqual(outSri.xstart, sri.xstart+sri.ydelta*i)
                else:
                    self.assertAlmostEqual(outSri.xstart, sri.xstart)
                
            self.assertTrue(outSri.subsize == 0)
            self.assertTrue(outSri.ydelta == 0)
            self.assertTrue(outSri.ystart == 0)
            self.assertTrue(outSri.yunits == BULKIO.UNITS_NONE)
            self.assertTrue(exepectedSig==outSig)

    def testTimeTime(self):
        self.comp.transpose=False
        self.mainTestCase()

    def testTimeFrequency(self):
        self.comp.transpose=False
        self.mainTestCase(yUnit=BULKIO.UNITS_FREQUENCY)

    def testTransposeTimeTime(self):
        self.comp.transpose=True
        self.mainTestCase()

    def testTransposeTimeFrequency(self):
        self.comp.transpose=True
        self.mainTestCase(yUnit=BULKIO.UNITS_FREQUENCY)

    def testTimeTimeCx(self):
        self.comp.transpose=False        
        self.mainTestCase(cx=1)

    def testTimeFrequencyCx(self):
        self.comp.transpose=False
        self.mainTestCase(yUnit=BULKIO.UNITS_FREQUENCY,cx=1)

    def testTransposeTimeTimeCx(self):
        self.comp.transpose=True
        self.mainTestCase(cx=1)

    def testTransposeTimeFrequencyCx(self):
        self.comp.transpose=True
        self.mainTestCase(yUnit=BULKIO.UNITS_FREQUENCY,cx=1)
    
    def testTimeTime2(self):
        self.comp.transpose=False
        self.mainTestCase(numPushes=2)

    def testTimeFrequency2(self):
        self.comp.transpose=False
        self.mainTestCase(yUnit=BULKIO.UNITS_FREQUENCY,numPushes=2)

    def testTransposeTimeTime2(self):
        self.comp.transpose=True
        self.mainTestCase(numPushes=2)

    def testTransposeTimeFrequency2(self):
        self.comp.transpose=True
        self.mainTestCase(yUnit=BULKIO.UNITS_FREQUENCY,numPushes=2)
    
    def testNoSubsize(self):
        inSignal = [float(x) for x in xrange(1024)]
        streamID = 'nosubsize'
        outData = self.main(inSignal)
        self.assertTrue(len(outData)==1)
        outSri, outSig = outData.values()[0]
        self.assertTrue(inSignal==outSig)
    
    def testMultiStream(self):
        """Test that two streams work well together
        """
        subsize=10
        numCols=30
        xdelta = .01
        ydelta = subsize*xdelta
        yUnit = BULKIO.UNITS_FREQUENCY
        cx=0

        inSignalLen = subsize*numCols

        inSignal = [float(x) for x in xrange(inSignalLen)]
        streams = ('stream_a', 'stream_b')
        for streamID in streams:
                
            sri = BULKIO.StreamSRI(1, .1, xdelta, BULKIO.UNITS_TIME, subsize, 0.0, ydelta, yUnit, cx,
                                                         streamID, True, [])
            self.src._pushSRIAllConnectedPorts(sri)
            self.pushData(inSignal, 1, streamID,False)

        outData = self.getData()
        
        self.assertTrue(len(outData)==subsize*len(streams))        
        for i in xrange(subsize):
            exepectedSig = inSignal[i::subsize]
            for streamID in streams:
                key = "%s_%s"%(streamID,i)
                outSri, outSig = outData[key]

                self.assertTrue(outSri.xdelta == sri.ydelta)
                self.assertTrue(outSri.xunits == sri.yunits)
                self.assertAlmostEqual(outSri.xstart, sri.ystart)
                                    
                self.assertTrue(outSri.subsize == 0)
                self.assertTrue(outSri.ydelta == 0)
                self.assertTrue(outSri.ystart == 0)
                self.assertTrue(outSri.yunits == BULKIO.UNITS_NONE)
                self.assertTrue(exepectedSig==outSig)

    # TODO Add additional tests here
    #
    # See:
    #   ossie.utils.bulkio.bulkio_helpers,
    #   ossie.utils.bluefile.bluefile_helpers
    # for modules that will assist with testing resource with BULKIO ports

if __name__ == "__main__":
    ossie.utils.testing.main("../BurstDeserializer.spd.xml") # By default tests all implementations
