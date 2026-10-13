--[[{
    "name": "Removing a FlowFile from the session"
}]]

function handler(ffdocument, session)

    local ref = ffdocument:getReference()
    
    local newffdocument = session:create(ref..":"..create_uuid())
    
    -- remove original FlowFile
    session:remove(ffdocument)

    return newffdocument

end