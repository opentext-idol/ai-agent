--[[{
    "name": "Basic handler function (LuaFlowFileDocument,LuaProcessorSession)",
    "info": "Basic example of a handler function with LuaFlowFileDocument and LuaProcessorSession arguments"
}]]
--@ LuaScriptFunctionArguments=LuaFlowFileDocument,LuaProcessorSession
--@ LuaScriptFunction=handler

function handler(ffdocument, session)

    -- Read or write the document using any functions of LuaFlowFileDocument.
    local ref = ffdocument:getReference()
    ffdocument:modifyDocument(
        function(document)
            -- Similar to handler with only LuaDocument argument.
            -- documents or boolean may be returned and are returned by modifyDocument.
            document:appendContent("Hello world")
        end)

    -- Create any new FlowFile documents that are intended to be routed out of this processor.
    local newffdocument1 = session:create(ref..":"..create_uuid())
    local newffdocument2 = session:create(ref..":"..create_uuid())

    -- Transfer or remove FlowFile documents from the session explicitly if required
    session:transfer(newffdocument1, "success")
    session:remove(ffdocument)

    -- Return FlowFile documents to be routed based on the RouteReturnedTo property.
    -- By default 'ffdocument' is routed based on RouteTo property,
    --     unless it is explicitly returned, transferred or removed.
    -- Any FlowFile documents that are not returned, transferred or removed result in a failure.
    return newffdocument2

end