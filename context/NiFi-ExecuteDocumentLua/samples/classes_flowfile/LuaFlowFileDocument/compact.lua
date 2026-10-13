--[[{
    "name": "Stripping parts marked for removal from a FlowFile document"
}]]

function handler(ffdocument, session)

    local deleteParts = function(action)
        action:deletePart()
    end
    
    -- Mark all files for removal in the FlowFile document
    ffdocument:append({
        onContentFile = deleteParts,
        onContentFilename = deleteParts})
    
    -- Remove parts marked for removal
    ffdocument:compact()
    
    -- note: calling append and then compact is equivalent to just calling modify

end