--[[{
    "name": "Basic handler function (LuaDocument)",
    "info": "Basic example of a handler function with a LuaDocument argument"
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

--@ LuaScriptFunctionArguments=LuaDocument
--@ LuaScriptFunction=handler

function handler(document)

    -- Read or write the document using any functions of LuaDocument.
    local ref = document:getReference()
    document:appendContent("Hello world")

    -- Create any new documents that are intended to be routed out of this processor.
    local newdocument = LuaDocument:new(ref..":"..create_uuid())
    
    -- Return all created documents to be routed based on the RouteReturnedTo property.
    -- By default 'document' is routed based on RouteTo property,
    --     unless it is explicitly returned.
    -- Any other documents that are not returned are discarded.
    return newdocument

end