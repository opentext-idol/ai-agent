--[[{
    "name": "Creating a new FlowFile document"
}]]

function handler(ffdocument, session)

    local ref = ffdocument:getReference()

    -- With only idol.reference attribute
    local newffdocument1 = session:create(ref..":"..create_uuid())
    
    -- Also with idol.reference.action and parent FlowFile specified
    local newffdocument2 = session:create(ref..":"..create_uuid(), "add", ffdocument)
    
    return newffdocument1, newffdocument2

end