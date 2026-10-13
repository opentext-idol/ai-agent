--[[{
    "name": "Basic handler function (LuaFlowFileDocument,LuaProcessorSession)",
    "info": "Basic example of a handler function with LuaFlowFileDocument and LuaProcessorSession arguments"
}]]

-- BEGIN COPYRIGHT NOTICE
-- Copyright 2026 Open Text.
--
-- The only warranties for products and services of Open Text and its affiliates and licensors
-- ("Open Text") are as may be set forth in the express warranty statements accompanying such
-- products and services. Nothing herein should be construed as constituting an additional warranty.
-- Open Text shall not be liable for technical or editorial errors or omissions contained herein.
-- The information contained herein is subject to change without notice.
--
-- END COPYRIGHT NOTICE

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