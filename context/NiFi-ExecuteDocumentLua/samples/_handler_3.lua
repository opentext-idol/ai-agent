--[[{
    "name": "Basic handler function (LuaFlowFile,LuaProcessorSession)",
    "info": "Basic example of a handler function with LuaFlowFile and LuaProcessorSession arguments, for FlowFiles not in IDOL FlowFileDocument format"
}]]
--@ LuaScriptFunctionArguments=LuaFlowFile
--@ LuaScriptFunction=handler

function handler(flowfile, session)

    -- Read or write the FlowFile using any functions of LuaFlowFile.
    -- LuaFlowFile exposes the raw FlowFile surface (attributes and content),
    -- for FlowFiles that are not in IDOL FlowFileDocument format.
    local ref = flowfile:getAttribute("filename")

    -- Create any new FlowFiles that are intended to be routed out of this processor.
    local newflowfile1 = session:createFlowFile(flowfile)
    local newflowfile2 = session:createFlowFile()

    -- Transfer or remove FlowFiles from the session explicitly if required.
    session:transfer(newflowfile1, "success")
    session:remove(flowfile)

    -- Return FlowFiles to be routed based on the RouteReturnedTo property.
    -- By default 'flowfile' is routed based on RouteTo property,
    --     unless it is explicitly returned, transferred or removed.
    -- Any FlowFiles that are not returned, transferred or removed result in a failure.
    return newflowfile2

end
