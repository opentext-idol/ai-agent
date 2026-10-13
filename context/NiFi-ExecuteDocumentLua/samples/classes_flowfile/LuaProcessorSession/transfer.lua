--[[{
    "name": "Transferring a FlowFile from the session"
}]]

function handler(ffdocument, session)

    local ref = ffdocument:getReference()
    
    local newffdocument = session:create(ref..":"..create_uuid())
    
    session:transfer(newffdocument, "success")
    
    -- transfer original back to input queue to be processed again
    session:transfer(ffdocument)

end