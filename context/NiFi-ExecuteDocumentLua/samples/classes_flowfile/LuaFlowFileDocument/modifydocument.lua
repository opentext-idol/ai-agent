--[[{
    "name": "Modifying a FlowFile using a LuaDocument handler"
}]]

function handler(ffdocument, session)

    local luaDocumentHander = function(document)
        document:appendContent("Hello world")
        return true
    end

    local result = ffdocument:modifyDocument(luaDocumentHander)
    
    if not result then
        session:remove(ffdocument)
    end

end