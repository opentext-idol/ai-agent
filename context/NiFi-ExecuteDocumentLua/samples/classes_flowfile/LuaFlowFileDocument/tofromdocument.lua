--[[{
    "name": "Converting LuaFlowFileDocument to and from LuaDocument"
}]]

function handler(ffdocument, session)

    local document = ffdocument:getAsLuaDocument()
    
    -- Updates to document are not mirrored by ffdocument
    -- The ffdocument must be updated after changes are completed
    
    ffdocument:setFromLuaDocument(document)

end