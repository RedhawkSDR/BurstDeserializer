/*
 * This file is protected by Copyright. Please refer to the COPYRIGHT file distributed with this
 * source distribution.
 *
 * This file is part of REDHAWK Basic Components BurstDeserializer.
 *
 * REDHAWK Basic Components BurstDeserializer is free software: you can redistribute it and/or modify it under the terms of
 * the GNU Lesser General Public License as published by the Free Software Foundation, either
 * version 3 of the License, or (at your option) any later version.
 *
 * REDHAWK Basic Components BurstDeserializer is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
 * without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
 * PURPOSE.  See the GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License along with this
 * program.  If not, see http://www.gnu.org/licenses/.
 */
#ifndef BURSTDESERIALIZER_IMPL_H
#define BURSTDESERIALIZER_IMPL_H

#include "BurstDeserializer_base.h"

class BurstDeserializer_i : public BurstDeserializer_base
{
    ENABLE_LOGGING

	void updateSri(unsigned int complex_offset,
			bulkio::InDoublePort::dataTransfer* tmp);

public:
        BurstDeserializer_i(const char *uuid, const char *label);
        ~BurstDeserializer_i();
        int serviceFunction();
private:
        struct StateStruct {
        	std::vector<std::string> outputIDs;
        	BULKIO::StreamSRI SRI;
        	bool adjustXStart;
        	size_t streamCount;
        };
		typedef std::map<std::string, StateStruct> state_type;

        void transposeChanged(const bool *oldValue, const bool *newValue);
        template<typename T>
        void demuxData(std::vector<double>& input, std::vector<T>& output, size_t colNum,size_t subsize);
        std::string getStreamID(state_type::iterator state);
        void updateState(bool subsizeRefresh, StateStruct& state, bool thisTranspose, bulkio::InDoublePort::dataTransfer* tmp);
        void pushTransposed(size_t numElements, unsigned int complex_offset, state_type::iterator state, bulkio::InDoublePort::dataTransfer* tmp);
        void pushUnTransposed(unsigned int complex_offset, state_type::iterator state, bulkio::InDoublePort::dataTransfer* tmp);

        bool flushStreams;
		state_type activeStreams;
};

#endif
