--[[{
    "name": "Getting and setting attributes on a FlowFile"
}]]

function handler(ffdocument, session)

    local reference = ffdocument:getReference()             -- idol.reference
    local referenceAction = ffdocument:getReferenceAction() -- idol.reference.action

    local state = ffdocument:getAttribute("luahandlerstate")
    
    if state ~= "done" then
        
        ffdocument:setAttributes( { luahandlerstate = "done" } )
        
    end

end